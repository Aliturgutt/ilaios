"""Adapters between proven domain chains and ILAIOS platform contracts."""

from .desktop_video_runtime import DesktopPromptVideoRuntime
from .product_proof import (
    AcceptanceManifest,
    DesktopGoalRequest,
    GovernedVideoProductProof,
    ProductProofError,
)
from .product_runtime import (
    DurableVideoProductRuntime,
    ProductFinalizationPending,
    ProductRuntimeError,
)
from .reference_aware_web_product_runtime import RecoverableWebProductRuntime
from .software_product_runtime import (
    DurableSoftwareProductRuntime,
    FinishedSoftwareBuilder,
    SoftwareProductFinalizationPending,
    SoftwareProductRuntimeError,
    SoftwareProductSecurityError,
    SoftwareProductValidationError,
)
from .software_product_runtime_recovery import RecoverableSoftwareProductRuntime
from .video import VideoChainAdapter, VideoIntegrationError, VideoIntegrationResult
from .video_runtime import DeterministicLocalVideoRuntime, VideoRuntimeError
from .web_factory import GovernedWebFactory, WebsiteAcceptance, WebsiteFile
from .web_vercel_delivery import (
    RequestsVercelDeploymentTransport,
    VercelDeploymentTransport,
    VercelWebDeploymentAdapter,
)

__all__ = [
    "AcceptanceManifest",
    "DesktopGoalRequest",
    "DesktopPromptVideoRuntime",
    "DeterministicLocalVideoRuntime",
    "DurableSoftwareProductRuntime",
    "DurableVideoProductRuntime",
    "FinishedSoftwareBuilder",
    "GovernedVideoProductProof",
    "GovernedWebFactory",
    "ProductFinalizationPending",
    "ProductProofError",
    "ProductRuntimeError",
    "RecoverableSoftwareProductRuntime",
    "RecoverableWebProductRuntime",
    "RequestsVercelDeploymentTransport",
    "SoftwareProductFinalizationPending",
    "SoftwareProductRuntimeError",
    "SoftwareProductSecurityError",
    "SoftwareProductValidationError",
    "VercelDeploymentTransport",
    "VercelWebDeploymentAdapter",
    "VideoChainAdapter",
    "VideoIntegrationError",
    "VideoIntegrationResult",
    "VideoRuntimeError",
    "WebsiteAcceptance",
    "WebsiteFile",
]
