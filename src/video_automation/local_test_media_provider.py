"""Deterministic local video provider for canonical M11 TEST MODE.

The provider exposes a pre-existing local media fixture through the canonical
provider contract. It performs no network access, paid provider call, polling,
retry, media generation, transcoding, download, or asset-store registration.

Media acquisition orchestration belongs to M12. Asset registration and
provenance persistence belong to M13.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .models import ProviderRequest, ProviderResult
from .providers import ProviderCapabilities, VideoGenerationProvider

_DEFAULT_PROVIDER_NAME = "local-test"
_DEFAULT_OPERATION = "video.generate"


class LocalTestMediaProviderError(ValueError):
    """Raised when a local TEST MODE media fixture is invalid."""


class LocalTestVideoProvider(VideoGenerationProvider):
    """Serve one deterministic local video fixture through the M03 contract."""

    def __init__(
        self,
        fixture_path: str | Path,
        *,
        provider_name: str = _DEFAULT_PROVIDER_NAME,
    ) -> None:
        path = Path(fixture_path)

        _require_non_blank("provider_name", provider_name)

        if not path.exists():
            raise LocalTestMediaProviderError(
                f"fixture_path does not exist: {path}"
            )

        if not path.is_file():
            raise LocalTestMediaProviderError(
                f"fixture_path must reference a file: {path}"
            )

        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise LocalTestMediaProviderError(
                f"fixture_path is not readable: {path}"
            ) from exc

        if not payload:
            raise LocalTestMediaProviderError(
                "fixture_path must not reference an empty file"
            )

        self._fixture_path = path.resolve()
        self._fixture_sha256 = sha256(payload).hexdigest()

        super().__init__(
            ProviderCapabilities(
                provider_name=provider_name,
                operations=(_DEFAULT_OPERATION,),
                is_paid=False,
                metadata={
                    "execution_mode": "test",
                    "media_type": "video",
                    "source": "local_fixture",
                },
            )
        )

    @property
    def fixture_path(self) -> Path:
        """Return the resolved immutable local fixture path."""

        return self._fixture_path

    @property
    def fixture_sha256(self) -> str:
        """Return the checksum captured when the provider was constructed."""

        return self._fixture_sha256

    def execute(self, request: ProviderRequest) -> ProviderResult:
        """Resolve one request to the configured local fixture.

        The provider validates the canonical provider name and operation through
        BaseProvider and verifies that the fixture has not disappeared or changed
        since construction.
        """

        try:
            self._validate_request(request)
        except ValueError as exc:
            return _failure(
                request,
                error_code="invalid_request",
                message=str(exc),
            )

        try:
            current_payload = self._fixture_path.read_bytes()
        except OSError:
            return _failure(
                request,
                error_code="fixture_unavailable",
                message="local test media fixture is no longer readable",
            )

        if not current_payload:
            return _failure(
                request,
                error_code="fixture_unavailable",
                message="local test media fixture is empty",
            )

        current_sha256 = sha256(current_payload).hexdigest()

        if current_sha256 != self._fixture_sha256:
            return _failure(
                request,
                error_code="fixture_changed",
                message="local test media fixture changed after provider initialization",
            )

        identity_material = "\n".join(
            (
                f"request_id={request.request_id}",
                f"job_id={request.job_id}",
                f"fixture_sha256={self._fixture_sha256}",
            )
        )
        identity_sha256 = sha256(identity_material.encode("utf-8")).hexdigest()

        return ProviderResult(
            request_id=request.request_id,
            provider_name=self.capabilities.provider_name,
            success=True,
            external_id=f"local-test-{identity_sha256[:24]}",
            metadata={
                "asset_path": str(self._fixture_path),
                "checksum_sha256": self._fixture_sha256,
                "execution_mode": "test",
                "media_type": "video",
                "source_reference": f"local://{self._fixture_path.name}",
            },
        )


def _failure(
    request: ProviderRequest,
    *,
    error_code: str,
    message: str,
) -> ProviderResult:
    return ProviderResult(
        request_id=request.request_id,
        provider_name=request.provider_name,
        success=False,
        error_code=error_code,
        error_message=message,
    )


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise LocalTestMediaProviderError(f"{name} must not be blank")

    if value != value.strip():
        raise LocalTestMediaProviderError(
            f"{name} must not contain surrounding whitespace"
        )
