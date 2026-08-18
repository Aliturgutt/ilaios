#!/usr/bin/env python3
"""Minimal CONNECT-only allowlist proxy for the ILAIOS browser sandbox.

This process is the only dual-homed member of the BrowserQA Docker topology.
It accepts exact HTTPS origins, resolves them itself, rejects any resolution that
is not globally routable, and tunnels bytes only after policy validation.
"""
from __future__ import annotations

import ipaddress
import json
import os
import selectors
import socket
import socketserver
from urllib.parse import urlsplit

_MAX_HEADER_BYTES = 16 * 1024
_IO_TIMEOUT_SECONDS = 30.0


def _allowed_authorities() -> frozenset[tuple[str, int]]:
    raw = os.environ.get("ILAIOS_ALLOWED_ORIGINS_JSON", "")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SystemExit("invalid allowlist policy") from error
    if not isinstance(parsed, list) or not parsed:
        raise SystemExit("empty allowlist policy")
    authorities: set[tuple[str, int]] = set()
    for item in parsed:
        if not isinstance(item, str):
            raise SystemExit("invalid allowlist origin")
        url = urlsplit(item)
        if url.scheme.lower() != "https" or not url.hostname:
            raise SystemExit("Docker browser egress accepts HTTPS origins only")
        if url.username or url.password or url.query or url.fragment:
            raise SystemExit("invalid allowlist origin components")
        if url.path not in {"", "/"}:
            raise SystemExit("allowlist must contain origins only")
        try:
            port = url.port or 443
        except ValueError as error:
            raise SystemExit("invalid allowlist origin port") from error
        authorities.add((url.hostname.lower().encode("idna").decode("ascii"), port))
    return frozenset(authorities)


def _parse_authority(value: str) -> tuple[str, int]:
    try:
        parsed = urlsplit(f"//{value}")
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError
        port = parsed.port or 443
    except ValueError as error:
        raise ValueError("invalid CONNECT authority") from error
    return parsed.hostname.lower().encode("idna").decode("ascii"), port


def _global_addresses(host: str, port: int) -> tuple[tuple[int, tuple[object, ...]], ...]:
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise OSError("destination resolution failed") from error
    candidates: list[tuple[int, tuple[object, ...]]] = []
    observed: set[tuple[int, str]] = set()
    for family, socktype, proto, _canonname, sockaddr in records:
        del socktype, proto
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        address = str(sockaddr[0])
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise OSError("destination resolved to a non-global address")
        key = (family, address)
        if key in observed:
            continue
        observed.add(key)
        candidates.append((family, tuple(sockaddr)))
    if not candidates:
        raise OSError("destination has no globally routable address")
    return tuple(candidates)


def _connect_global(host: str, port: int) -> socket.socket:
    last_error: OSError | None = None
    for family, sockaddr in _global_addresses(host, port):
        outbound = socket.socket(family, socket.SOCK_STREAM)
        outbound.settimeout(8.0)
        try:
            outbound.connect(sockaddr)
            outbound.settimeout(_IO_TIMEOUT_SECONDS)
            return outbound
        except OSError as error:
            last_error = error
            outbound.close()
    raise OSError("destination connection failed") from last_error


def _read_headers(stream: socket.socket) -> bytes:
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = stream.recv(4096)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > _MAX_HEADER_BYTES:
            raise ValueError("proxy request headers are too large")
    return bytes(data)


def _relay(left: socket.socket, right: socket.socket) -> None:
    selector = selectors.DefaultSelector()
    selector.register(left, selectors.EVENT_READ, right)
    selector.register(right, selectors.EVENT_READ, left)
    try:
        while selector.get_map():
            events = selector.select(timeout=_IO_TIMEOUT_SECONDS)
            if not events:
                return
            for key, _mask in events:
                source = key.fileobj
                destination = key.data
                if not isinstance(source, socket.socket) or not isinstance(
                    destination, socket.socket
                ):
                    return
                chunk = source.recv(65536)
                if not chunk:
                    try:
                        destination.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass
                    selector.unregister(source)
                    continue
                destination.sendall(chunk)
    finally:
        selector.close()


class _ProxyHandler(socketserver.BaseRequestHandler):
    allowed: frozenset[tuple[str, int]] = frozenset()

    def handle(self) -> None:
        client = self.request
        if not isinstance(client, socket.socket):
            return
        client.settimeout(_IO_TIMEOUT_SECONDS)
        outbound: socket.socket | None = None
        try:
            headers = _read_headers(client)
            first_line = headers.split(b"\r\n", 1)[0].decode("ascii", errors="strict")
            parts = first_line.split(" ")
            if len(parts) != 3 or parts[0] != "CONNECT" or not parts[2].startswith("HTTP/"):
                client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n")
                return
            host, port = _parse_authority(parts[1])
            if (host, port) not in self.allowed:
                client.sendall(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
                return
            outbound = _connect_global(host, port)
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            _relay(client, outbound)
        except (OSError, UnicodeError, ValueError):
            try:
                client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
        finally:
            if outbound is not None:
                outbound.close()


class _ThreadingProxy(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = False


def _parse_port() -> int:
    raw = os.environ.get("ILAIOS_PROXY_PORT", "18080")
    try:
        port = int(raw)
    except ValueError as error:
        raise SystemExit("invalid proxy port") from error
    if port < 1024 or port > 65535:
        raise SystemExit("invalid proxy port")
    return port


def main() -> None:
    allowed = _allowed_authorities()
    _ProxyHandler.allowed = allowed
    with _ThreadingProxy(("0.0.0.0", _parse_port()), _ProxyHandler) as server:
        server.serve_forever(poll_interval=0.25)


if __name__ == "__main__":
    main()
