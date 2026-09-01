#!/usr/bin/env python3
"""Local-only live development monitor for ILAIOS.

Development tooling only. It is not an ILAIOS product runtime dependency.
Uses only the Python standard library and binds to 127.0.0.1 by default.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
FETCH_INTERVAL_SECONDS = 5.0
MAX_TEXT = 30_000
_fetch_lock = threading.Lock()
_last_fetch = 0.0


def _run(*args: str, timeout: float = 5.0) -> tuple[int, str]:
    try:
        cp = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return cp.returncode, cp.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def _git(*args: str, timeout: float = 5.0) -> str:
    return _run("git", *args, timeout=timeout)[1]


def _maybe_fetch() -> None:
    global _last_fetch
    now = time.monotonic()
    with _fetch_lock:
        if now - _last_fetch < FETCH_INTERVAL_SECONDS:
            return
        _last_fetch = now
    _run("git", "fetch", "--quiet", "origin", "master", timeout=8.0)


def _tail(path: Path, limit: int = 12_000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return data[-limit:]


def _latest_logs() -> list[dict[str, Any]]:
    evidence = ROOT / "dev" / "openclaw" / "evidence"
    if not evidence.exists():
        return []
    candidates: list[Path] = []
    for name in ("commands.log", "tests.log", "quality.log", "runtime.log", "decision.yaml"):
        candidates.extend(evidence.rglob(name))
    candidates = [p for p in candidates if p.is_file()]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for path in candidates[:8]:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        out.append(
            {
                "path": str(path.relative_to(ROOT)),
                "mtime": mtime,
                "text": _tail(path),
            }
        )
    return out


def _status() -> dict[str, Any]:
    _maybe_fetch()
    branch = _git("branch", "--show-current") or "unknown"
    head = _git("rev-parse", "--short", "HEAD")
    origin = _git("rev-parse", "--short", "origin/master")
    latest_commit = _git("log", "-1", "--pretty=format:%h  %s  (%cr)")
    status = _git("status", "--short")
    diff_names = _git("diff", "--name-status")
    diff_stat = _git("diff", "--stat")
    diff = _git("diff", "--no-ext-diff", "--unified=2", timeout=8.0)[:MAX_TEXT]
    remote_diff = ""
    if head and origin and head != origin:
        remote_diff = _git("diff", "--stat", "HEAD..origin/master")[:MAX_TEXT]
    return {
        "time": time.time(),
        "repo": str(ROOT),
        "branch": branch,
        "head": head,
        "origin": origin,
        "latest_commit": latest_commit,
        "synced": bool(head and origin and head == origin),
        "working_tree_clean": not bool(status.strip()),
        "status": status,
        "diff_names": diff_names,
        "diff_stat": diff_stat,
        "diff": diff,
        "remote_diff": remote_diff,
        "logs": _latest_logs(),
    }


HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>ILAIOS Live Development Monitor</title>
<style>
:root{color-scheme:dark;--bg:#07111f;--panel:#0c1728;--panel2:#111f34;--line:#24344d;--text:#e8eef8;--muted:#93a4bd;--ok:#4ade80;--warn:#fbbf24;--bad:#fb7185;--accent:#60a5fa}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}.top{height:58px;display:flex;align-items:center;gap:16px;padding:0 20px;border-bottom:1px solid var(--line);background:#091523;position:sticky;top:0;z-index:5}.brand{font:700 18px system-ui}.pill{padding:5px 9px;border:1px solid var(--line);border-radius:999px;color:var(--muted)}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.grid{display:grid;grid-template-columns:300px minmax(0,1fr) 360px;gap:12px;padding:12px;min-height:calc(100vh - 58px)}.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}.panel h2{font:600 13px system-ui;margin:0;padding:11px 13px;border-bottom:1px solid var(--line);background:var(--panel2)}.content{padding:12px}.kv{display:grid;grid-template-columns:110px 1fr;gap:6px 10px}.k{color:var(--muted)}pre{white-space:pre-wrap;word-break:break-word;margin:0;font-size:12px}.tabs{display:flex;border-bottom:1px solid var(--line);background:var(--panel2)}button{background:none;border:0;color:var(--muted);padding:11px 14px;cursor:pointer}button.active{color:var(--text);border-bottom:2px solid var(--accent)}.view{display:none;padding:12px;height:calc(100vh - 160px);overflow:auto}.view.active{display:block}.log{border-bottom:1px solid var(--line);padding:10px 0}.logpath{color:var(--accent);font-size:12px;margin-bottom:6px}.statusline{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px}.dot{width:9px;height:9px;border-radius:50%;display:inline-block;background:var(--warn);margin-right:7px}.dot.ok{background:var(--ok)}.dot.bad{background:var(--bad)}.small{font-size:12px;color:var(--muted)}@media(max-width:1100px){.grid{grid-template-columns:1fr}.view{height:480px}}
</style>
</head>
<body>
<div class="top"><div class="brand">ILAIOS · Live Development Monitor</div><span id="conn" class="pill">connecting…</span><span id="sync" class="pill">git…</span><span class="pill">local-only · 127.0.0.1</span></div>
<div class="grid">
  <section class="panel"><h2>Repository / Active State</h2><div class="content">
    <div class="statusline"><span><span id="cleanDot" class="dot"></span><b id="treeState">Loading</b></span><span id="branch" class="small"></span></div>
    <div class="kv"><div class="k">HEAD</div><div id="head">—</div><div class="k">origin/master</div><div id="origin">—</div><div class="k">Latest commit</div><div id="commit">—</div></div>
    <h3>Changed files</h3><pre id="files">No local changes</pre>
    <h3>Remote changes</h3><pre id="remote">Local HEAD matches origin/master</pre>
  </div></section>
  <section class="panel">
    <div class="tabs"><button class="active" data-tab="diff">Live Code Diff</button><button data-tab="logs">Test / Evidence Logs</button><button data-tab="stat">Diff Stat</button></div>
    <div id="diff" class="view active"><pre id="diffText">Waiting for changes…</pre></div>
    <div id="logs" class="view"><div id="logText">Waiting for evidence logs…</div></div>
    <div id="stat" class="view"><pre id="statText">Waiting for changes…</pre></div>
  </section>
  <section class="panel"><h2>Live Execution Feed</h2><div class="content"><div class="small">Refreshes every 1.5 s. OpenClaw evidence/test logs appear here as they are written.</div><div id="feed" style="margin-top:12px"></div></div></section>
</div>
<script>
for(const b of document.querySelectorAll('button[data-tab]')){b.onclick=()=>{document.querySelectorAll('button[data-tab]').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.getElementById(b.dataset.tab).classList.add('active')}}
const esc=s=>(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function tick(){try{const r=await fetch('/api/status',{cache:'no-store'});const d=await r.json();conn.textContent='LIVE';conn.className='pill ok';sync.textContent=d.synced?'HEAD = origin/master':'origin/master changed';sync.className='pill '+(d.synced?'ok':'warn');branch.textContent=d.branch;head.textContent=d.head||'—';origin.textContent=d.origin||'—';commit.textContent=d.latest_commit||'—';treeState.textContent=d.working_tree_clean?'Working tree clean':'Local changes detected';cleanDot.className='dot '+(d.working_tree_clean?'ok':'warn');files.textContent=d.diff_names||d.status||'No local changes';remote.textContent=d.remote_diff||'Local HEAD matches origin/master';diffText.textContent=d.diff||'Waiting for local code changes…';statText.textContent=d.diff_stat||'Waiting for local code changes…';logText.innerHTML=(d.logs||[]).map(x=>`<div class="log"><div class="logpath">${esc(x.path)}</div><pre>${esc(x.text)}</pre></div>`).join('')||'Waiting for evidence logs…';feed.innerHTML=(d.logs||[]).slice(0,5).map(x=>`<div class="log"><div class="logpath">${esc(x.path)}</div><pre>${esc((x.text||'').slice(-1800))}</pre></div>`).join('')||'<span class="small">No evidence activity yet.</span>';}
catch(e){conn.textContent='DISCONNECTED';conn.className='pill bad'}setTimeout(tick,1500)}tick();
</script>
</body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            data = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/status":
            data = json.dumps(_status(), ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(HTTPStatus.NOT_FOUND)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"} and os.environ.get("ILAIOS_MONITOR_ALLOW_REMOTE") != "1":
        raise SystemExit("Refusing non-loopback bind. Set ILAIOS_MONITOR_ALLOW_REMOTE=1 only if you intentionally accept the exposure risk.")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"ILAIOS Live Development Monitor: http://{args.host}:{args.port}", flush=True)
    print(f"Watching repository: {ROOT}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
