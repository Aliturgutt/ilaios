"""Adapters between proven domain chains and ILAIOS platform contracts."""

from .product_proof import (
    AcceptanceManifest,
    DesktopGoalRequest,
    GovernedVideoProductProof,
    ProductProofError,
)
from .video import VideoChainAdapter, VideoIntegrationError, VideoIntegrationResult

__all__ = [
    "AcceptanceManifest",
    "DesktopGoalRequest",
    "GovernedVideoProductProof",
    "ProductProofError",
    "VideoChainAdapter",
    "VideoIntegrationError",
    "VideoIntegrationResult",
]
