"""Guard external publication with final-product, OAuth, and durable side-effect evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .finished_product import FinishedVideoProduct
from .publication_ledger import PublicationSideEffectLedger
from .publishing_execution import (
    PlatformPublisher,
    PlatformPublishingObservation,
    PublishingExecutionStatus,
)
from .publishing_package_preparation import PlatformPublishingPackage


class GuardedPublishingError(RuntimeError):
    """Raised when a social publication cannot safely proceed."""


@dataclass(frozen=True, slots=True)
class PublicationAuthorization:
    platform: str
    account_id: str
    oauth_authorization_ref: str
    scopes: tuple[str, ...]

    def __post_init__(self) -> None:
        for name, value in (
            ("platform", self.platform),
            ("account_id", self.account_id),
            ("oauth_authorization_ref", self.oauth_authorization_ref),
        ):
            _text(name, value)
        if not self.scopes:
            raise GuardedPublishingError("publication authorization requires OAuth scopes")
        if len(self.scopes) != len(set(self.scopes)):
            raise GuardedPublishingError("publication authorization scopes must be unique")
        for scope in self.scopes:
            _text("OAuth scope", scope)


class PublicationAuthorityAwarePublisher(PlatformPublisher, Protocol):
    """Publisher that is explicitly bound to one OAuth account reference."""

    @property
    def account_id(self) -> str: ...

    @property
    def oauth_authorization_ref(self) -> str: ...

    @property
    def required_oauth_scopes(self) -> tuple[str, ...]: ...


@dataclass(frozen=True, slots=True)
class GuardedPublicationResult:
    package_id: str
    platform: str
    account_id: str
    final_product_id: str
    observation: PlatformPublishingObservation
    oauth_authorization_ref: str


class DurablePublishingCoordinator:
    """Perform at most one external publish attempt for one immutable package ID."""

    def __init__(self, ledger: PublicationSideEffectLedger) -> None:
        self._ledger = ledger

    def publish(
        self,
        *,
        package: PlatformPublishingPackage,
        product: FinishedVideoProduct,
        authorization: PublicationAuthorization,
        publisher: PublicationAuthorityAwarePublisher,
    ) -> GuardedPublicationResult:
        self._validate_authority(package, product, authorization, publisher)
        self._ledger.prepare(package=package, product=product)
        self._ledger.submitting(package.package_id)
        try:
            observation = publisher.publish(package)
        except Exception as exc:  # noqa: BLE001
            self._ledger.ambiguous(
                package_id=package.package_id,
                observed_status=f"publisher exception: {exc.__class__.__name__}",
            )
            raise GuardedPublishingError(
                "publication became ambiguous; reconcile durable platform state before repost"
            ) from exc

        try:
            self._validate_observation(package, observation)
        except GuardedPublishingError as exc:
            self._ledger.ambiguous(
                package_id=package.package_id,
                observed_status="publisher returned conflicting publication identity",
            )
            raise GuardedPublishingError(
                "publisher response identity is ambiguous; reconcile before repost"
            ) from exc

        if observation.status is PublishingExecutionStatus.SUCCEEDED:
            if observation.platform_post_id is None:
                self._ledger.ambiguous(
                    package_id=package.package_id,
                    observed_status="success response missing platform_post_id",
                )
                raise GuardedPublishingError(
                    "publication success is ambiguous without platform_post_id"
                )
            self._ledger.published(
                package_id=package.package_id,
                external_post_id=observation.platform_post_id,
                published_url=observation.published_url,
            )
        else:
            self._ledger.failed(
                package_id=package.package_id,
                observed_status=observation.error_code or "publisher_rejected",
            )
        return GuardedPublicationResult(
            package_id=package.package_id,
            platform=package.platform,
            account_id=package.account_id,
            final_product_id=product.product_id,
            observation=observation,
            oauth_authorization_ref=authorization.oauth_authorization_ref,
        )

    @staticmethod
    def _validate_authority(
        package: PlatformPublishingPackage,
        product: FinishedVideoProduct,
        authorization: PublicationAuthorization,
        publisher: PublicationAuthorityAwarePublisher,
    ) -> None:
        if package.media_sha256_hex != product.final_sha256:
            raise GuardedPublishingError("package is not bound to exact finished product SHA")
        normalized_platform = authorization.platform.strip().lower()
        if normalized_platform != package.platform:
            raise GuardedPublishingError("OAuth authorization platform does not match package")
        if authorization.account_id != package.account_id:
            raise GuardedPublishingError("OAuth authorization account does not match package")
        if publisher.platform.strip().lower() != package.platform:
            raise GuardedPublishingError("publisher adapter platform does not match package")
        if publisher.account_id != package.account_id:
            raise GuardedPublishingError("publisher adapter account does not match package")
        if publisher.oauth_authorization_ref != authorization.oauth_authorization_ref:
            raise GuardedPublishingError("publisher OAuth reference does not match authorization")
        missing_scopes = set(publisher.required_oauth_scopes) - set(authorization.scopes)
        if missing_scopes:
            raise GuardedPublishingError(
                "publication authorization is missing required OAuth scopes: "
                + ", ".join(sorted(missing_scopes))
            )

    @staticmethod
    def _validate_observation(
        package: PlatformPublishingPackage,
        observation: PlatformPublishingObservation,
    ) -> None:
        if observation.package_id != package.package_id:
            raise GuardedPublishingError("publisher observation package_id mismatch")
        if observation.platform != package.platform:
            raise GuardedPublishingError("publisher observation platform mismatch")
        if observation.account_id != package.account_id:
            raise GuardedPublishingError("publisher observation account_id mismatch")


def _text(name: str, value: str) -> None:
    if not value or not value.strip() or value != value.strip():
        raise GuardedPublishingError(f"{name} must be non-blank normalized text")
