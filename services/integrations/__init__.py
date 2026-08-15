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
from .video import VideoChainAdapter, VideoIntegrationError, VideoIntegrationResult
from .video_runtime import DeterministicLocalVideoRuntime, VideoRuntimeError
from .web_deployment import (
    WebDeploymentReceipt,
    WebDeploymentReceiptError,
    validate_web_deployment_receipt,
)
from .web_factory import (
    GovernedWebFactory,
    WebsiteAcceptance,
    WebsiteFile,
    WebsiteSpec,
    derive_website_spec,
)
from .web_product_runtime import (
    DurableWebProductRuntime,
    WebProductFinalizationPending,
    WebProductRuntimeError,
)
from .web_project import WebProjectArtifact, WebProjectFile, materialize_next_project

__all__ = [
    "AcceptanceManifest",
    "DesktopGoalRequest",
    "DesktopPromptVideoRuntime",
    "DeterministicLocalVideoRuntime",
    "DurableVideoProductRuntime",
    "DurableWebProductRuntime",
    "GovernedVideoProductProof",
    "GovernedWebFactory",
    "ProductFinalizationPending",
    "ProductProofError",
    "ProductRuntimeError",
    "VideoChainAdapter",
    "VideoIntegrationError",
    "VideoIntegrationResult",
    "VideoRuntimeError",
    "WebDeploymentReceipt",
    "WebDeploymentReceiptError",
    "WebProductFinalizationPending",
    "WebProductRuntimeError",
    "WebProjectArtifact",
    "WebProjectFile",
    "WebsiteAcceptance",
    "WebsiteFile",
    "WebsiteSpec",
    "derive_website_spec",
    "materialize_next_project",
    "validate_web_deployment_receipt",
]
