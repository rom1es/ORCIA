"""Pydantic v2 HTTP Transport Schemas for Assistant (`AD-25`, `Story 26.7`)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from orcia_api.schemas.assistant_governance_and_three_speed import (
    ActiveBackgroundTurnStatusResponse as ActiveBackgroundTurnStatusResponse,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssembledLayerPreviewSchemaItem as AssembledLayerPreviewSchemaItem,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantActiveTurnsListResponse as AssistantActiveTurnsListResponse,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantGovernanceViewResponse as AssistantGovernanceViewResponse,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantThreadMessageSchemaItem as AssistantThreadMessageSchemaItem,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantThreadMessagesListResponse as AssistantThreadMessagesListResponse,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantTurnAcceptedResponse as AssistantTurnAcceptedResponse,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantTurnApproveRequest as AssistantTurnApproveRequest,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantTurnApproveResponse as AssistantTurnApproveResponse,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantTurnCreateRequest as AssistantTurnCreateRequest,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantTurnFeedbackRequest as AssistantTurnFeedbackRequest,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantTurnFeedbackResponse as AssistantTurnFeedbackResponse,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    AssistantTurnSynthesizeNowResponse as AssistantTurnSynthesizeNowResponse,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    ConversationTurnMessageItem as ConversationTurnMessageItem,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    UpdateUserLayerPreferencesRequest as UpdateUserLayerPreferencesRequest,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    UpdateWorkspaceLayerSettingsRequest as UpdateWorkspaceLayerSettingsRequest,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    UserLayerPreferencesSchemaItem as UserLayerPreferencesSchemaItem,
)
from orcia_api.schemas.assistant_governance_and_three_speed import (
    WorkspaceLayerSettingsSchemaItem as WorkspaceLayerSettingsSchemaItem,
)


class AssistantSaveAndLaunchRequest(BaseModel):
    """Request payload for `POST /api/v1/assistant/workflows/save-and-launch` (`FR-11`)."""

    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(..., min_length=1)
    manifest_yaml: str = Field(..., min_length=10)


class AssistantSaveAndLaunchResponse(BaseModel):
    """Response envelope for `POST /api/v1/assistant/workflows/save-and-launch` (`FR-11`)."""

    model_config = ConfigDict(extra="forbid")
    workflow_uri: str
    version: str
    run_id: str
    execution_regime: str
    run_status: str
    executed_step_keys: list[str]
    snapshot_count: int
