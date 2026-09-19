"""Machine-readable contracts for ILAIOS UI design decisions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UIDesignSpec:
    schema_version: str
    component: str
    category: str
    placement: str
    desktop_size: str
    compact_behavior: str
    interactions: tuple[str, ...]
    accessibility: tuple[str, ...]
    quality_gates: tuple[str, ...]
    confidence: float
    evidence: tuple[str, ...]
    brand_policy: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "component": self.component,
            "category": self.category,
            "placement": self.placement,
            "desktop_size": self.desktop_size,
            "compact_behavior": self.compact_behavior,
            "interactions": list(self.interactions),
            "accessibility": list(self.accessibility),
            "quality_gates": list(self.quality_gates),
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "brand_policy": self.brand_policy,
        }
