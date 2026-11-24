import createClient from "openapi-fetch";
import { createAgentsAndSkillsDomainClient } from "./domains/agentsAndSkills";
import { createAiModelsHubDomainClient } from "./domains/aiModelsHub";
import {
  createAssistantGovernanceAndThreadsDomainClient,
  type AssembledLayerPreviewSchemaItem,
  type AssistantGovernanceViewResponse,
  type AssistantThreadMessageSchemaItem,
  type AssistantThreadMessagesListResponse,
  type UpdateUserLayerPreferencesRequest,
  type UpdateWorkspaceLayerSettingsRequest,
  type UserLayerPreferencesSchemaItem,
  type WorkspaceLayerSettingsSchemaItem,
} from "./domains/assistantGovernanceAndThreads";
import {
  createAuditFinopsDomainClient,
  type ListAuditLedgerParams,
} from "./domains/auditFinops";
import { createAuthAndShellDomainClient } from "./domains/authAndShell";
import { createAutonomousSupervisionDomainClient } from "./domains/autonomousSupervision";
import { createAutonomyContractsDomainClient } from "./domains/autonomyContracts";
import {
  createAssistantStreamingDomainClient,
  streamAssistantTurnByIdSse,
  streamReflexiveExecutionTraceSse,
  streamWorkspaceEventsSse,
  type AssistantTurnSseOptions,
  type ReflexiveTraceSseOptions,
  type WorkspaceEventsSseOptions,
} from "./domains/assistantStreaming";
import {
  createBootstrapAndOntologyDomainClient,
  type DemoWorkspaceProvisionResponse,
  type WizardAdvanceStepRequest,
  type WizardSessionRequest,
  type WizardSessionResponse,
  type WizardSessionsListResponse,
  type WizardStepBackRequest,
} from "./domains/bootstrapAndOntology";
import { createCatalogAndPermissionsDomainClient } from "./domains/catalogAndPermissions";
import { createCodegraphMcpDomainClient } from "./domains/codegraphMcp";
import { createEpics1To7OperationsDomainClient } from "./domains/epics1To7Operations";
import { createFinopsDomainClient } from "./domains/finops";
import {
  createOntologyPromotionsDomainClient,
  type OntologyConceptWithPermissionsItem,
  type OntologyConceptsListResponse,
  type OntologyPromotionCreateRequest,
  type OntologyPromotionDecideRequest,
  type OntologyPromotionDecideResponse,
  type OntologyPromotionProposalDetailItem,
  type OntologyPromotionsListResponse,
  type WritableScopeOptionItem,
} from "./domains/ontologyPromotions";
import {
  createReflexiveExecutionDomainClient,
  type InspectSourceLinesParams,
} from "./domains/reflexiveExecution";
import {
  createWorkflowsV2DomainClient,
  type ApiImpactAssessmentResult,
  type ApiValueStreamMapSpec,
  type ApiWorkflowDefinitionV2,
  type DeclarativePacksListResponse,
  type DeclarativePackSummaryResponse,
  type SaveWorkflowV2Options,
} from "./domains/workflowsV2";
import { createWorkflowTriggersDomainClient } from "./domains/workflowTriggers";
import {
  createWorkspaceGovernanceDomainClient,
  type ExceptionWaiverResponseItem,
  type RegisterExceptionWaiverInput,
  type WorkspaceFiveTabsStatePayload,
} from "./domains/workspaceGovernance";
import type { paths } from "./generated/schema";
import {
  buildKnownOrgUsersQuery,
  buildOrgUnitsQuery,
  createRequestBinary,
  createRequestJson,
  createRequestSse,
  OrciaClientError,
  OrciaProblemError,
  registerDefaultAccessTokenProvider,
  registerDefaultAccessTokenRefreshedHandler,
  type BinaryDownloadResult,
  type ListKnownOrgUsersParams,
  type ListOrgUnitsParams,
  type OrciaApiClientConfig,
  type OrciaApiClientOptions,
  type OrciaClientErrorParams,
  type SseEventHandler,
  type SseRequestParams,
} from "./helpers";

export type * from "./generated/schema";
export type { PopularUsageItemResponse, UserProfileSummaryResponse } from "./generated/user_profile";
export {
  buildKnownOrgUsersQuery,
  buildOrgUnitsQuery,
  createAgentsAndSkillsDomainClient,
  createAiModelsHubDomainClient,
  createAssistantGovernanceAndThreadsDomainClient,
  createAssistantStreamingDomainClient,
  createAuditFinopsDomainClient,
  createAuthAndShellDomainClient,
  createAutonomousSupervisionDomainClient,
  createAutonomyContractsDomainClient,
  createBootstrapAndOntologyDomainClient,
  createCatalogAndPermissionsDomainClient,
  createCodegraphMcpDomainClient,
  createEpics1To7OperationsDomainClient,
  createFinopsDomainClient,
  createOntologyPromotionsDomainClient,
  createReflexiveExecutionDomainClient,
  createRequestSse,
  createWorkflowsV2DomainClient,
  createWorkflowTriggersDomainClient,
  createWorkspaceGovernanceDomainClient,
  OrciaClientError,
  OrciaProblemError,
  registerDefaultAccessTokenProvider,
  registerDefaultAccessTokenRefreshedHandler,
  streamAssistantTurnByIdSse,
  streamReflexiveExecutionTraceSse,
  streamWorkspaceEventsSse,
  type ApiImpactAssessmentResult,
  type ApiValueStreamMapSpec,
  type ApiWorkflowDefinitionV2,
  type AssembledLayerPreviewSchemaItem,
  type AssistantGovernanceViewResponse,
  type AssistantThreadMessageSchemaItem,
  type AssistantThreadMessagesListResponse,
  type AssistantTurnSseOptions,
  type UpdateUserLayerPreferencesRequest,
  type UpdateWorkspaceLayerSettingsRequest,
  type UserLayerPreferencesSchemaItem,
  type WorkspaceLayerSettingsSchemaItem,
  type BinaryDownloadResult,
  type DeclarativePacksListResponse,
  type DeclarativePackSummaryResponse,
  type DemoWorkspaceProvisionResponse,
  type ExceptionWaiverResponseItem,
  type InspectSourceLinesParams,
  type ListAuditLedgerParams,
  type ListKnownOrgUsersParams,
  type ListOrgUnitsParams,
  type OntologyConceptWithPermissionsItem,
  type OntologyConceptsListResponse,
  type OntologyPromotionCreateRequest,
  type OntologyPromotionDecideRequest,
  type OntologyPromotionDecideResponse,
  type OntologyPromotionProposalDetailItem,
  type OntologyPromotionsListResponse,
  type ReflexiveTraceSseOptions,
  type RegisterExceptionWaiverInput,
  type SaveWorkflowV2Options,
  type SseEventHandler,
  type SseRequestParams,
  type WizardAdvanceStepRequest,
  type WizardSessionRequest,
  type WizardSessionResponse,
  type WizardSessionsListResponse,
  type WizardStepBackRequest,
  type WorkspaceEventsSseOptions,
  type WorkspaceFiveTabsStatePayload,
  type WritableScopeOptionItem,
  type OrciaApiClientConfig,
  type OrciaApiClientOptions,
  type OrciaClientErrorParams,
};

export function createOrciaOpenApiFetchClient(options: OrciaApiClientOptions) {
  const headers: Record<string, string> = {
    Accept: "application/json, application/problem+json",
    "Accept-Language": options.locale ?? "fr",
  };
  if (options.traceId) {
    headers["X-Trace-Id"] = options.traceId;
  }
  if (options.accessToken) {
    headers.Authorization = `Bearer ${options.accessToken}`;
  }
  return createClient<paths>({
    baseUrl: options.baseUrl,
    headers,
    credentials: "include",
    fetch: options.fetchImpl ?? globalThis.fetch,
  });
}

export function createOrciaApiClient(options: OrciaApiClientOptions) {
  const requestJson = createRequestJson(options);
  const requestBinary = createRequestBinary(options);
  const requestSse = createRequestSse(options);
  const aiModelsHubClient = createAiModelsHubDomainClient(requestJson);
  const auditFinopsClient = createAuditFinopsDomainClient(requestJson);
  return {
    ...createAuthAndShellDomainClient(requestJson),
    ...createAutonomousSupervisionDomainClient(requestJson),
    ...createAutonomyContractsDomainClient(requestJson),
    ...createCatalogAndPermissionsDomainClient(requestJson),
    ...createCodegraphMcpDomainClient(requestJson),
    ...createBootstrapAndOntologyDomainClient(requestJson, requestSse),
    ...createEpics1To7OperationsDomainClient(requestJson),
    ...createAgentsAndSkillsDomainClient(requestJson),
    ...createAssistantGovernanceAndThreadsDomainClient(requestJson),
    ...createFinopsDomainClient(requestJson),
    ...createOntologyPromotionsDomainClient(requestJson),
    ...createReflexiveExecutionDomainClient(requestJson, options.baseUrl),
    ...createWorkflowsV2DomainClient(requestJson, requestBinary),
    ...createWorkflowTriggersDomainClient(requestJson),
    ...createWorkspaceGovernanceDomainClient(requestJson),
    ...auditFinopsClient,
    ...aiModelsHubClient,
    aiModelsHub: aiModelsHubClient,
    auditFinops: auditFinopsClient,
  };
}
