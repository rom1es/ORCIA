"""OpenAPI 3.1 HTTP Transport Schemas for Declarative Packs & Process Studio v2 (`TASK-05`).

All `*Request` and `*Response` schemas reside exclusively in `apps/api/src/orcia_api/schemas/`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from orcia_connectors.bounded_workflow_v2 import (
    BoundedWorkflowRunState,
    HitlSignalPayload,
)
from orcia_connectors.protocol import ConnectorHealthStatus
from orcia_core.packs.loader import QuickActionSpec, RequiredConnectorSpec
from orcia_core.workflows.schemas_v2 import (
    ImpactAssessmentResult,
    ValueStreamMapSpec,
    WorkflowDefinitionV2,
)


class ConnectorRequirementHealthItemResponse(BaseModel):
    connector_type: str
    required_scopes: list[str]
    used_for: str
    health: ConnectorHealthStatus


class DeclarativePackSummaryResponse(BaseModel):
    id: str
    slug: str
    name: str
    version: str
    description: str
    rbac_namespace: str
    bundle_sha256: str
    agents_count: int
    skills_count: int
    gates_count: int
    vsm_count: int
    workflows_count: int
    agents_slugs: list[str] = Field(default_factory=list)
    skills_slugs: list[str] = Field(default_factory=list)
    gates_slugs: list[str] = Field(default_factory=list)
    required_connectors: list[RequiredConnectorSpec] = Field(default_factory=list)
    connector_health: list[ConnectorRequirementHealthItemResponse] = Field(default_factory=list)
    quick_actions: list[QuickActionSpec] = Field(default_factory=list)


class DeclarativePacksListResponse(BaseModel):
    packs: list[DeclarativePackSummaryResponse]


class VsmListResponse(BaseModel):
    items: list[ValueStreamMapSpec]


class WorkflowsV2ListResponse(BaseModel):
    items: list[WorkflowDefinitionV2]


class SaveWorkflowV2Request(BaseModel):
    workflow: WorkflowDefinitionV2
    publish: bool = False


class SaveWorkflowV2Response(BaseModel):
    workflow: WorkflowDefinitionV2
    forked_as_draft: bool


class WhatIfSimulationRequest(BaseModel):
    sample_inputs: dict[str, Any] = Field(default_factory=dict)
    sample_artifact_markdown: str | None = None


classWhatIfSimulationResponse = ImpactAssessmentResult


class StartWorkflowV2RunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    iteration: int = 1
    reentry_mode: str = "initial"
    correction_remarks: str | None = None
    auto_approve_checkpoints: bool = False


class WorkflowV2RunResponse(BaseModel):
    run: BoundedWorkflowRunState


class HitlSignalRequest(HitlSignalPayload):
    pass


__all__ = [
    "ConnectorRequirementHealthItemResponse",
    "DeclarativePackSummaryResponse",
    "DeclarativePacksListResponse",
    "HitlSignalRequest",
    "SaveWorkflowV2Request",
    "SaveWorkflowV2Response",
    "StartWorkflowV2RunRequest",
    "VsmListResponse",
    "WhatIfSimulationRequest",
    "WorkflowV2RunResponse",
    "WorkflowsV2ListResponse",
]
