"""Additional domain error classes (packs v2) for `apps/api/src/orcia_api/errors`."""

from __future__ import annotations

from orcia_core.packs.errors import (
    PACK_DOMAIN_ERROR_CLASSES,
    EntityReferencedByPackDraftError,
    PackClosureIncompleteError,
    PackEntityCollisionError,
    PackExecutableHookForbiddenError,
    PackInvalidArchiveError,
    PackPiiOrInfraLeakError,
    PackSlotUnboundError,
    PackVersionConflictError,
    ResourcePinnedByActiveRunsError,
)

__all__ = [
    "EntityReferencedByPackDraftError",
    "PACK_DOMAIN_ERROR_CLASSES",
    "PackClosureIncompleteError",
    "PackEntityCollisionError",
    "PackExecutableHookForbiddenError",
    "PackInvalidArchiveError",
    "PackPiiOrInfraLeakError",
    "PackSlotUnboundError",
    "PackVersionConflictError",
    "ResourcePinnedByActiveRunsError",
]
