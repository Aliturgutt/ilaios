"""Adapters between proven domain chains and ILAIOS platform contracts."""

from .video import VideoChainAdapter, VideoIntegrationError, VideoIntegrationResult

__all__ = ["VideoChainAdapter", "VideoIntegrationError", "VideoIntegrationResult"]
