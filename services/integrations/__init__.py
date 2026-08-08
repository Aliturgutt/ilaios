"""Adapters between proven domain chains and ILAIOS platform contracts."""

from .product_proof import (
    AcceptanceManifest,
    DesktopGoalRequest,
    GovernedVideoProductProof,
    ProductProofError,
)
from .video import VideoChainAdapter, VideoIntegrationError, VideoIntegrationResult
from .web_factory import GovernedWebFactory, WebsiteAcceptance

__all__ = [
    "AcceptanceManifest",
    "DesktopGoalRequest",
    "GovernedVideoProductProof",
    "GovernedWebFactory",
    "ProductProofError",
    "VideoChainAdapter",
    "VideoIntegrationError",
    "VideoIntegrationResult",
    "WebsiteAcceptance",
]
