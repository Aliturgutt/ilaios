"""Adapters between proven domain chains and ILAIOS platform contracts."""

from .desktop_video_runtime import DesktopPromptVideoRuntime
from .product_proof import (
    AcceptanceManifest,
    DesktopGoalRequest,
    GovernedVideoProductProof,
    ProductProofError,
)
from .product_runtime import DurableVideoProductRuntime, ProductRuntimeError
from .video import VideoChainAdapter, VideoIntegrationError, VideoIntegrationResult
from .video_runtime import DeterministicLocalVideoRuntime, VideoRuntimeError
from .web_factory import GovernedWebFactory, WebsiteAcceptance, WebsiteFile

__all__ = [
    "AcceptanceManifest",
    "DesktopGoalRequest",
    "DesktopPromptVideoRuntime",
    "DeterministicLocalVideoRuntime",
    "DurableVideoProductRuntime",
    "GovernedVideoProductProof",
    "GovernedWebFactory",
    "ProductProofError",
    "ProductRuntimeError",
    "VideoChainAdapter",
    "VideoIntegrationError",
    "VideoIntegrationResult",
    "VideoRuntimeError",
    "WebsiteAcceptance",
    "WebsiteFile",
]
