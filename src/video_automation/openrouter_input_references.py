"""Fail-closed OpenRouter native reference-image request shaping.

This module only validates and translates already-authorized provider-fetchable
HTTPS reference URLs. It does not publish private assets, select providers, or
bypass the canonical ILAIOS routing/governance authorities.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


class NativeReferenceRoutingError(ValueError):
    """Raised when provider-native reference data is unsafe or malformed."""


_MAX_NATIVE_REFERENCES = 20
_ALLOWED_ROLES = frozenset(
    {
        "style",
        "subject",
        "product",
        "environment",
        "logo",
        "storyboard",
        "other",
    }
)


def build_openrouter_input_references(
    item: Mapping[str, object],
) -> list[dict[str, object]]:
    """Translate governed native references to OpenRouter ``input_references``.

    OpenRouter's provider payload does not carry ILAIOS roles. Roles remain local
    evidence and are validated here so an unexpected role cannot silently broaden
    the provider request.
    """

    raw = item.get("native_reference_images")
    if raw is None:
        return []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise NativeReferenceRoutingError("native_reference_images must be a list")
    if not raw:
        return []
    if len(raw) > _MAX_NATIVE_REFERENCES:
        raise NativeReferenceRoutingError("native reference image count exceeds 20")

    output: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise NativeReferenceRoutingError("native reference entry must be an object")
        url = entry.get("url")
        role = entry.get("role")
        sha256_hex = entry.get("sha256")
        if not isinstance(url, str):
            raise NativeReferenceRoutingError("native reference url must be text")
        _require_https("native reference url", url)
        if url in seen_urls:
            raise NativeReferenceRoutingError("duplicate native reference url")
        seen_urls.add(url)
        if not isinstance(role, str) or role not in _ALLOWED_ROLES:
            raise NativeReferenceRoutingError("native reference role is unsupported")
        if not isinstance(sha256_hex, str) or not _is_sha256(sha256_hex):
            raise NativeReferenceRoutingError("native reference sha256 is invalid")
        output.append(
            {
                "type": "image_url",
                "image_url": {"url": url},
            }
        )
    return output


def _require_https(name: str, value: str) -> None:
    if not value or value != value.strip() or not value.startswith("https://"):
        raise NativeReferenceRoutingError(f"{name} must be a trimmed HTTPS URL")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
