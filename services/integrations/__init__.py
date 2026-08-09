"""Adapters between proven domain chains and ILAIOS platform contracts."""

from .product_proof import (
    AcceptanceManifest,
    DesktopGoalRequest,
    GovernedVideoProductProof,
    ProductProofError,
)
from .video import VideoChainAdapter, VideoIntegrationError, VideoIntegrationResult
from .video_runtime import DeterministicLocalVideoRuntime, VideoRuntimeError
from .web_factory import GovernedWebFactory, WebsiteAcceptance

__all__ = [
    "AcceptanceManifest",
    "DesktopGoalRequest",
    "DeterministicLocalVideoRuntime",
    "GovernedVideoProductProof",
    "GovernedWebFactory",
    "ProductProofError",
    "VideoChainAdapter",
    "VideoIntegrationError",
    "VideoIntegrationResult",
    "VideoRuntimeError",
    "WebsiteAcceptance",
]
