"""Additional domain error classes (packs v2) for `apps/api/src/orcia_api/errors`."""

from __future__ import annotations

from orcia_core.packs.errors import (
    PACK_DOMAIN_ERROR_CLASSES,
    EntityReferencedByPackDraftError,
    PackActivationInvalidError,
    PackBundleNotFoundError,
    PackClosureIncompleteError,
    PackEntityCollisionError,
    PackExecutableHookForbiddenError,
    PackInvalidArchiveError,
    PackPiiOrInfraLeakError,
    PackScopeEscalationForbiddenError,
    PackSlotBindingInvalidError,
    PackSlotUnboundError,
    PackSystemDeleteForbiddenError,
    PackVersionConflictError,
    ResourcePinnedByActiveRunsError,
)

__all__ = [
    "EntityReferencedByPackDraftError",
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
