"""Declarative packs domain errors (`AD-19`, `Story 31.1`, `31.2`)."""

from __future__ import annotations

from orcia_core.packs._error_catalog import PACKS_ERROR_CATALOG
from orcia_kernel.errors import OrciaDomainError


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
    """Raised (`HTTP 422`) when a required pack connector slot is unbound at execution."""

    error_code = "ERR_PACK_SLOT_UNBOUND"
    http_status = 422
    type_slug = "pack-slot-unbound"


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


class ResourcePinnedByActiveRunsError(OrciaDomainError):
    """Raised (`HTTP 409`) when deleting a pack or bound slot pinned by active run locks."""

    error_code = "ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS"
    http_status = 409
    type_slug = "resource-pinned-by-active-runs"


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


PACK_DOMAIN_ERROR_CLASSES: tuple[type[OrciaDomainError], ...] = (
    PackExecutableHookForbiddenError,
    PackInvalidArchiveError,
    PackVersionConflictError,
    PackSlotUnboundError,
    PackClosureIncompleteError,
    PackPiiOrInfraLeakError,
    ResourcePinnedByActiveRunsError,
    EntityReferencedByPackDraftError,
    PackBundleNotFoundError,
    PackSystemDeleteForbiddenError,
    PackScopeEscalationForbiddenError,
)

__all__ = [
    "EntityReferencedByPackDraftError",
    "PACKS_ERROR_CATALOG",
    "PACK_DOMAIN_ERROR_CLASSES",
    "PackBundleNotFoundError",
    "PackClosureIncompleteError",
    "PackExecutableHookForbiddenError",
    "PackInvalidArchiveError",
    "PackPiiOrInfraLeakError",
    "PackScopeEscalationForbiddenError",
    "PackSlotUnboundError",
    "PackSystemDeleteForbiddenError",
    "PackVersionConflictError",
    "ResourcePinnedByActiveRunsError",
]
