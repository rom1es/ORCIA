"""Declarative packs domain errors (`AD-19`, `Story 31.1`, `31.2`)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from orcia_core.packs._error_catalog import PACKS_ERROR_CATALOG
from orcia_kernel.errors import OrciaDomainError, ResourcePinnedByActiveRunsError


class PackExecutableHookForbiddenError(OrciaDomainError):
    """Raised (`HTTP 422`) when a pack contains scripts, hooks directories, or hook keys."""

    error_code = "ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN"
    http_status = 422
    type_slug = "pack-executable-hook-forbidden"


class PackInvalidArchiveError(OrciaDomainError):
    """Raised (`HTTP 422`) on zip-slip, zip-bomb, corrupt manifest, or Starlark AST error."""

    error_code = "ERR_PACK_INVALID_ARCHIVE"
    http_status = 422
    type_slug = "pack-invalid-archive"


class PackVersionConflictError(OrciaDomainError):
    """Raised (`HTTP 409`) when importing a different SHA-256 under an existing SemVer."""

    error_code = "ERR_PACK_VERSION_CONFLICT"
    http_status = 409
    type_slug = "pack-version-conflict"


class PackSlotUnboundError(OrciaDomainError):
    """Raised (`HTTP 422`) when a required pack connector slot is unbound at activation/run."""

    error_code = "ERR_PACK_SLOT_UNBOUND"
    http_status = 422
    type_slug = "pack-slot-unbound"

    def __init__(
        self,
        *,
        pack_slug: str = "",
        missing_slots: Sequence[str] = (),
        detail_override: str | None = None,
        detail_code: str | None = None,
        detail_params: Mapping[str, object] | None = None,
        instance: str | None = None,
        permission_broker_hint: str | None = None,
    ) -> None:
        self.pack_slug = pack_slug
        self.missing_slots = tuple(missing_slots)
        merged_params = dict(detail_params) if detail_params is not None else {}
        if pack_slug and "pack_slug" not in merged_params:
            merged_params["pack_slug"] = pack_slug
        if missing_slots and "missing_slots" not in merged_params:
            merged_params["missing_slots"] = ", ".join(missing_slots)
        resolved_code = detail_code
        if resolved_code is None and detail_override is None and missing_slots:
            resolved_code = "ERR_PACK_SLOT_UNBOUND_DETAIL"
        super().__init__(
            detail_override=detail_override,
            detail_code=resolved_code,
            detail_params=merged_params or None,
            instance=instance,
            permission_broker_hint=permission_broker_hint,
        )


class PackActivationInvalidError(OrciaDomainError):
    """Raised (`HTTP 422`) on invalid activation, deactivation, or priority reorder inputs."""

    error_code = "ERR_PACK_ACTIVATION_INVALID"
    http_status = 422
    type_slug = "pack-activation-invalid"


class PackSlotBindingInvalidError(OrciaDomainError):
    """Raised (`HTTP 422`) when slot binding targets an unknown slot or invalid target."""

    error_code = "ERR_PACK_SLOT_BINDING_INVALID"
    http_status = 422
    type_slug = "pack-slot-binding-invalid"


class PackClosureIncompleteError(OrciaDomainError):
    """Raised (`HTTP 422`) when publishing/exporting a pack with unresolved dependencies."""

    error_code = "ERR_PACK_CLOSURE_INCOMPLETE"
    http_status = 422
    type_slug = "pack-closure-incomplete"


class PackPiiOrInfraLeakError(OrciaDomainError):
    """Raised (`HTTP 422`) when exported pack content contains PII, secrets, or tenant IDs."""

    error_code = "ERR_PACK_PII_OR_INFRA_LEAK"
    http_status = 422
    type_slug = "pack-pii-or-infra-leak"


class EntityReferencedByPackDraftError(OrciaDomainError):
    """Raised (`HTTP 409`) when deleting an entity referenced by `pack_draft_memberships`."""

    error_code = "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT"
    http_status = 409
    type_slug = "entity-referenced-by-pack-draft"


class PackBundleNotFoundError(OrciaDomainError):
    """Raised (`HTTP 404`) when a requested declarative pack bundle does not exist."""

    error_code = "ERR_PACK_BUNDLE_NOT_FOUND"
    http_status = 404
    type_slug = "pack-bundle-not-found"


class PackSystemDeleteForbiddenError(OrciaDomainError):
    """Raised (`HTTP 403`) when attempting to delete a built-in `SYSTEM` pack."""

    error_code = "ERR_PACK_SYSTEM_DELETE_FORBIDDEN"
    http_status = 403
    type_slug = "pack-system-delete-forbidden"


class PackScopeEscalationForbiddenError(OrciaDomainError):
    """Raised (`HTTP 403`) when importing a `SYSTEM` or `GLOBAL` pack from user API."""

    error_code = "ERR_PACK_SCOPE_ESCALATION_FORBIDDEN"
    http_status = 403
    type_slug = "pack-scope-escalation-forbidden"


class PackEntityCollisionError(OrciaDomainError):
    """Raised (`HTTP 409`) when strict disambiguation detects an ambiguous entity ref."""

    error_code = "ERR_PACK_ENTITY_AMBIGUOUS"
    http_status = 409
    type_slug = "pack-entity-ambiguous"

    def __init__(
        self,
        *,
        entity_ref: str = "",
        candidates: Sequence[str] = (),
        detail_override: str | None = None,
        detail_code: str | None = None,
        detail_params: Mapping[str, object] | None = None,
        instance: str | None = None,
        permission_broker_hint: str | None = None,
    ) -> None:
        self.entity_ref = entity_ref
        self.candidates = tuple(candidates)
        merged_params = dict(detail_params) if detail_params is not None else {}
        if entity_ref and "entity_ref" not in merged_params:
            merged_params["entity_ref"] = entity_ref
        if candidates and "candidates" not in merged_params:
            merged_params["candidates"] = ", ".join(candidates)
        super().__init__(
            detail_override=detail_override,
            detail_code=detail_code or ("ERR_PACK_ENTITY_AMBIGUOUS_DETAIL" if candidates else None),
            detail_params=merged_params or None,
            instance=instance,
            permission_broker_hint=permission_broker_hint,
        )


PACK_DOMAIN_ERROR_CLASSES: tuple[type[OrciaDomainError], ...] = (
    PackExecutableHookForbiddenError,
    PackInvalidArchiveError,
    PackVersionConflictError,
    PackSlotUnboundError,
    PackActivationInvalidError,
    PackSlotBindingInvalidError,
    PackClosureIncompleteError,
    PackPiiOrInfraLeakError,
    ResourcePinnedByActiveRunsError,
    EntityReferencedByPackDraftError,
    PackBundleNotFoundError,
    PackEntityCollisionError,
    PackSystemDeleteForbiddenError,
    PackScopeEscalationForbiddenError,
)

__all__ = [
    "EntityReferencedByPackDraftError",
    "PACKS_ERROR_CATALOG",
    "PACK_DOMAIN_ERROR_CLASSES",
    "PackActivationInvalidError",
    "PackBundleNotFoundError",
    "PackClosureIncompleteError",
    "PackEntityCollisionError",
    "PackExecutableHookForbiddenError",
    "PackInvalidArchiveError",
    "PackPiiOrInfraLeakError",
    "PackScopeEscalationForbiddenError",
    "PackSlotBindingInvalidError",
    "PackSlotUnboundError",
    "PackSystemDeleteForbiddenError",
    "PackVersionConflictError",
    "ResourcePinnedByActiveRunsError",
]
