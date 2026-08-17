"""User-controlled presentation policy for finished Video Factory products.

Captions are a presentation option, not an unconditional acceptance criterion.
Negative intent is evaluated before positive keywords because phrases such as
``altyazı istemiyorum`` contain the positive word ``altyazı``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class CaptionDelivery(str, Enum):
    NONE = "none"
    BURNED = "burned"
    SIDECAR = "sidecar"
    BOTH = "both"


@dataclass(frozen=True, slots=True)
class CaptionPolicy:
    enabled: bool = False
    language: str | None = None
    delivery: CaptionDelivery = CaptionDelivery.NONE

    def __post_init__(self) -> None:
        if not self.enabled and self.delivery is not CaptionDelivery.NONE:
            raise ValueError("disabled captions must use delivery=none")
        if self.enabled and self.delivery is CaptionDelivery.NONE:
            raise ValueError("enabled captions require a delivery mode")
        if self.language is not None and not self.language.strip():
            raise ValueError("caption language must not be blank")

    @property
    def burn_in(self) -> bool:
        return self.enabled and self.delivery in {
            CaptionDelivery.BURNED,
            CaptionDelivery.BOTH,
        }

    @property
    def deliver_sidecar(self) -> bool:
        return self.enabled and self.delivery in {
            CaptionDelivery.SIDECAR,
            CaptionDelivery.BOTH,
        }


_NEGATIVE_PATTERNS = (
    r"\baltyaz[ıi]s[ıi]z\b",
    r"\baltyaz[ıi]\s+(?:olmas[ıi]n|istemiyorum|isteme|yok|kapal[ıi])\b",
    r"\bno\s+(?:subtitles?|captions?)\b",
    r"\bwithout\s+(?:subtitles?|captions?)\b",
    r"\b(?:subtitles?|captions?)\s+(?:off|disabled)\b",
)
_POSITIVE_PATTERNS = (
    r"\baltyaz[ıi]\b",
    r"\bsubtitles?\b",
    r"\bcaptions?\b",
)
_BURNED_PATTERNS = (
    r"\bg[oö]m[uü]l[uü]\b",
    r"\bvideoya\s+g[oö]m",
    r"\bburn(?:ed|t)[ -]?in\b",
    r"\bhardcoded\b",
)
_SIDECAR_PATTERNS = (
    r"\bsidecar\b",
    r"\bsrt\b",
    r"\bvtt\b",
    r"\bharici\s+altyaz[ıi]\b",
)
_BOTH_PATTERNS = (
    r"\bikisi\s+de\b",
    r"\bher\s+ikisi\b",
    r"\bboth\b",
)


def infer_caption_policy(objective: str, *, default_enabled: bool = False) -> CaptionPolicy:
    """Infer explicit caption intent without making subtitles mandatory.

    Default is OFF. When a caller opts into a product-level default, an explicit
    negative user instruction still wins. An unspecified positive request uses
    sidecar delivery so the editor can keep captions independently selectable.
    """

    normalized = " ".join(objective.casefold().split())
    if _matches_any(normalized, _NEGATIVE_PATTERNS):
        return CaptionPolicy()

    explicitly_requested = _matches_any(normalized, _POSITIVE_PATTERNS)
    if not explicitly_requested and not default_enabled:
        return CaptionPolicy()

    language = _caption_language(normalized)
    if _matches_any(normalized, _BOTH_PATTERNS):
        delivery = CaptionDelivery.BOTH
    else:
        burned = _matches_any(normalized, _BURNED_PATTERNS)
        sidecar = _matches_any(normalized, _SIDECAR_PATTERNS)
        if burned and sidecar:
            delivery = CaptionDelivery.BOTH
        elif burned:
            delivery = CaptionDelivery.BURNED
        else:
            delivery = CaptionDelivery.SIDECAR
    return CaptionPolicy(enabled=True, language=language, delivery=delivery)


def _caption_language(text: str) -> str | None:
    language_patterns = (
        ("tr", (r"\bt[uü]rk[cç]e\s+altyaz", r"\bturkish\s+(?:subtitle|caption)")),
        ("en", (r"\bingilizce\s+altyaz", r"\benglish\s+(?:subtitle|caption)")),
        ("de", (r"\balmanca\s+altyaz", r"\bgerman\s+(?:subtitle|caption)")),
        ("fr", (r"\bfrans[ıi]zca\s+altyaz", r"\bfrench\s+(?:subtitle|caption)")),
        ("es", (r"\bispanyolca\s+altyaz", r"\bspanish\s+(?:subtitle|caption)")),
    )
    for code, patterns in language_patterns:
        if _matches_any(text, patterns):
            return code
    return None


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
