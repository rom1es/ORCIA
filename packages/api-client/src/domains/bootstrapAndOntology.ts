import type {
  AccostageStatusResponse,
  InitDatasourceRequest,
  InitDatasourceResponse,
  InitOrganizationRequest,
  InitOrganizationResponse,
  InitUserRequest,
  InitUserResponse,
  InitWorkspaceRequest,
  InitWorkspaceResponse,
  LlmConnectionTestRequest,
  LlmConnectionTestResponse,
  PlatformSetupStatePutRequest,
  PlatformSetupStateResponse,
  ProgressiveLlmEndpointRequest,
  SystemBootstrapStateResponse,
  WelcomeSetupFirstAdminRequest,
  WelcomeSetupFirstAdminResponse,
} from "../generated/bootstrap";
import type {
  DbDdlIndexRequest,
  DocVsCodeAuditRequest,
  DocVsCodeAuditResponse,
  HybridRagSearchRequest,
  HybridRagSearchResponse,
  KbDocumentSchemaItem,
  OntologyAndRagStateResponse,
  OntologyConceptSchemaItem,
  OntologyPromoteRequest,
  OntologyPromotionProposalSchemaItem,
  OntologyResolveRequest,
  OntologyResolveResponse,
  OntologyUpsertConceptRequest,
  WhatIfSimulationRequest,
  WhatIfSimulationResponse,
} from "../generated/ontology_and_rag";
import type { components } from "../generated/schema";
import { buildPersonaQuery, createRequestSse, type createRequestJson } from "../helpers";
import {
  createAssistantStreamingDomainClient,
  streamAssistantTurnSse,
  streamReflexiveExecutionTraceSse,
  streamWorkspaceEventsSse,
  type ActiveBackgroundTurnStatusResponse,
  type AssistantFolderResponse,
  type AssistantThreadResponse,
  type AssistantTurnSseOptions,
  type AssistantWorkspaceOverviewResponse,
  type ConfigureAssistantFolderSharingRequest,
  type ConfigureAssistantFolderSharingResponse,
  type CreateAssistantFolderRequest,
  type CreateAssistantThreadRequest,
  type RecordAssistantTurnFeedbackRequest,
  type ReflexiveTraceSseOptions,
  type SendCollaborativeThreadTurnRequest,
  type SendCollaborativeThreadTurnResponse,
  type StopActiveBackgroundTurnRequest,
  type ThreeSpeedTurnRequest,
  type ThreeSpeedTurnResponse,
  type WorkspaceEventsSseOptions,
} from "./assistantStreaming";

type RequestJsonFn = ReturnType<typeof createRequestJson>;
type RequestSseFn = ReturnType<typeof createRequestSse>;

export {
  createAssistantStreamingDomainClient,
  streamAssistantTurnSse,
  streamReflexiveExecutionTraceSse,
  streamWorkspaceEventsSse,
  type ActiveBackgroundTurnStatusResponse,
  type AssistantFolderResponse,
  type AssistantThreadResponse,
  type AssistantTurnSseOptions,
  type AssistantWorkspaceOverviewResponse,
  type ConfigureAssistantFolderSharingRequest,
  type ConfigureAssistantFolderSharingResponse,
  type CreateAssistantFolderRequest,
  type CreateAssistantThreadRequest,
  type RecordAssistantTurnFeedbackRequest,
  type ReflexiveTraceSseOptions,
  type SendCollaborativeThreadTurnRequest,
  type SendCollaborativeThreadTurnResponse,
  type StopActiveBackgroundTurnRequest,
  type ThreeSpeedTurnRequest,
  type ThreeSpeedTurnResponse,
  type WorkspaceEventsSseOptions,
};

export type FederatedSearchResponse = components["schemas"]["TwoSpeedSearchResponse"];
export type UserPreferencesResponse = components["schemas"]["UserPreferencesResponse"];
export type UserPreferencesPatchRequest = components["schemas"]["UserPreferencesUpdateRequest"];
export type McpPersonalTokenCreatePayload = components["schemas"]["McpPersonalTokenCreateRequest"];
export type McpPersonalTokenIssuedResult = components["schemas"]["McpPersonalTokenIssuedResponse"];
export type McpPersonalTokenListResult = components["schemas"]["McpPersonalTokenListResponse"];
export type McpPersonalTokenItemResult = components["schemas"]["McpPersonalTokenMetadataItem"];
export type ContextualHelpResolveResponse = components["schemas"]["ContextualHelpResolveResponse"];
export type ContextualHelpRollbackRequest = components["schemas"]["ContextualHelpRollbackRequest"];
export type HelpArticleSchemaItem = components["schemas"]["HelpArticleSchemaItem"];
export type CompileStarlarkMechanismRequest =
  components["schemas"]["CompileStarlarkMechanismRequest"];
export type StarlarkMechanismResponse = components["schemas"]["GeneratedStarlarkMechanismResponse"];
export type TestAndDiscoverConnectorRequest =
  components["schemas"]["RemoteServiceTestAndDiscoverRequest"];
export type ConnectorTestBenchReportResponse =
  components["schemas"]["RemoteServiceTestAndDiscoverResponse"];
export type ValidateHelpArticleRequest = components["schemas"]["ValidateHelpArticleRequest"];
export type HelpArticleValidationResponse = components["schemas"]["ValidateHelpArticleResponse"];
export type { LlmConnectionTestRequest, LlmConnectionTestResponse };
export type InstalledBusinessPackItemResponse =
  components["schemas"]["InstalledBusinessPackItemResponse"];
export type InstalledBusinessPackListResponse =
  components["schemas"]["InstalledBusinessPackListResponse"];
export type WizardSessionResponse = components["schemas"]["WizardSessionResponse"];
export type WizardSessionsListResponse = components["schemas"]["WizardSessionsListResponse"];
export type WizardSessionRequest = components["schemas"]["WizardSessionRequest"];
export type WizardAdvanceStepRequest = components["schemas"]["WizardAdvanceStepRequest"];
export type WizardStepBackRequest = components["schemas"]["WizardStepBackRequest"];
export type DemoWorkspaceProvisionResponse =
  components["schemas"]["DemoWorkspaceProvisionResponse"];

export function createBootstrapAndOntologyDomainClient(
  requestJson: RequestJsonFn,
  requestSse?: RequestSseFn,
) {
  const assistantStreamingClient = createAssistantStreamingDomainClient(
    requestSse ?? createRequestSse({ baseUrl: "" }),
    requestJson,
  );
  const fq = (fixture: boolean) => `?fixture=${fixture ? "true" : "false"}`;
  return {
    ...assistantStreamingClient,
    getAccostageStatus: () => requestJson<AccostageStatusResponse>("/api/v1/bootstrap/accostage-status"),
    getPlatformSetupState: () => requestJson<PlatformSetupStateResponse>("/api/v1/bootstrap/platform-setup-state"),
    savePlatformSetupState: (payload: PlatformSetupStatePutRequest) =>
      requestJson<PlatformSetupStateResponse>("/api/v1/bootstrap/platform-setup-state", "PUT", payload),
    createWelcomeSetupFirstAdmin: (payload: WelcomeSetupFirstAdminRequest) =>
      requestJson<WelcomeSetupFirstAdminResponse>("/api/v1/bootstrap/welcome-setup/first-admin", "POST", payload),
    registerProgressiveLlmEndpoint: (payload: ProgressiveLlmEndpointRequest) =>
      requestJson<AccostageStatusResponse>("/api/v1/bootstrap/welcome-setup/progressive-llm", "POST", payload),
    testLlmEndpointConnection: (payload: LlmConnectionTestRequest) =>
      requestJson<LlmConnectionTestResponse>("/api/v1/bootstrap/welcome-setup/llm-test", "POST", payload),
    getSystemBootstrapState: (personaKey?: string) =>
      requestJson<SystemBootstrapStateResponse>(`/api/v1/bootstrap/state${buildPersonaQuery(personaKey)}`),
    executeInitOrganization: (payload: InitOrganizationRequest, personaKey?: string) =>
      requestJson<InitOrganizationResponse>(`/api/v1/bootstrap/init-organization${buildPersonaQuery(personaKey)}`, "POST", payload),
    executeInitWorkspace: (payload: InitWorkspaceRequest, personaKey?: string) =>
      requestJson<InitWorkspaceResponse>(`/api/v1/bootstrap/init-workspace${buildPersonaQuery(personaKey)}`, "POST", payload),
    executeInitDatasource: (payload: InitDatasourceRequest, personaKey?: string) =>
      requestJson<InitDatasourceResponse>(`/api/v1/bootstrap/init-datasource${buildPersonaQuery(personaKey)}`, "POST", payload),
    executeInitUser: (payload: InitUserRequest, personaKey?: string) =>
      requestJson<InitUserResponse>(`/api/v1/bootstrap/init-user${buildPersonaQuery(personaKey)}`, "POST", payload),
    getOntologyAndRagState: (fixture = false) =>
      requestJson<OntologyAndRagStateResponse>(`/api/v1/ontology-rag/state${fq(fixture)}`),
    resolveOntologyHierarchy: (payload: OntologyResolveRequest, fixture = false) =>
      requestJson<OntologyResolveResponse>(`/api/v1/ontology-rag/ontology/resolve${fq(fixture)}`, "POST", payload),
    upsertOntologyConcept: (payload: OntologyUpsertConceptRequest, fixture = false) =>
      requestJson<OntologyConceptSchemaItem>(`/api/v1/ontology-rag/ontology/concepts${fq(fixture)}`, "POST", payload),
    simulateOntologyWhatIf: (payload: WhatIfSimulationRequest, fixture = false) =>
      requestJson<WhatIfSimulationResponse>(`/api/v1/ontology-rag/ontology/what-if${fq(fixture)}`, "POST", payload),
    promoteOntologyProposal: (payload: OntologyPromoteRequest, fixture = false) =>
      requestJson<OntologyPromotionProposalSchemaItem>(`/api/v1/ontology-rag/ontology/promote${fq(fixture)}`, "POST", payload),
    searchHybridRag: (payload: HybridRagSearchRequest, fixture = false) =>
      requestJson<HybridRagSearchResponse>(`/api/v1/ontology-rag/rag/search${fq(fixture)}`, "POST", payload),
    indexDbDdlSchema: (payload: DbDdlIndexRequest, fixture = false) =>
      requestJson<KbDocumentSchemaItem>(`/api/v1/ontology-rag/rag/index-db-ddl${fq(fixture)}`, "POST", payload),
    auditDocVsCode: (payload: DocVsCodeAuditRequest, fixture = false) =>
      requestJson<DocVsCodeAuditResponse>(`/api/v1/ontology-rag/tripartite/audit-doc-vs-code${fq(fixture)}`, "POST", payload),
    searchFederated(
      query: string,
      scope: "SCREEN" | "WORKSPACE" | "ALL_WORKSPACES" | "CONTEXTUAL" | "GLOBAL" = "ALL_WORKSPACES",
      workspaceId?: string | null,
      screenRoute = "/spaces",
      forceSemantic = true,
    ): Promise<FederatedSearchResponse> {
      const normalizedScope =
        scope === "GLOBAL"
          ? "ALL_WORKSPACES"
          : scope === "CONTEXTUAL"
            ? "WORKSPACE"
            : scope;
      const params = new URLSearchParams({
        q: query,
        scope: normalizedScope,
        screen_route: screenRoute,
        include_speed2: "true",
        force_semantic: forceSemantic ? "true" : "false",
      });
      if (workspaceId && workspaceId.trim().length > 0) {
        params.set("workspace_id", workspaceId);
      }
      return requestJson<FederatedSearchResponse>(`/api/v1/search?${params.toString()}`);
    },
    getUserPreferences: (personaKey?: string) =>
      requestJson<UserPreferencesResponse>(`/api/v1/users/me/preferences${buildPersonaQuery(personaKey)}`),
    updateUserPreferences: (payload: UserPreferencesPatchRequest, personaKey?: string) =>
      requestJson<UserPreferencesResponse>(`/api/v1/users/me/preferences${buildPersonaQuery(personaKey)}`, "PATCH", payload),
    listMcpTokens: (personaKey?: string) =>
      requestJson<McpPersonalTokenListResult>(`/api/v1/users/me/mcp-tokens${buildPersonaQuery(personaKey)}`),
    createMcpToken: (payload: McpPersonalTokenCreatePayload, personaKey?: string) =>
      requestJson<McpPersonalTokenIssuedResult>(`/api/v1/users/me/mcp-tokens${buildPersonaQuery(personaKey)}`, "POST", payload),
    revokeMcpToken: (tokenId: string, personaKey?: string) =>
      requestJson<McpPersonalTokenItemResult>(
        `/api/v1/users/me/mcp-tokens/${encodeURIComponent(tokenId)}${buildPersonaQuery(personaKey)}`,
        "DELETE",
      ),
    resolveContextualHelp(
      route: string,
      lang: "fr" | "en" = "fr",
      pack = "core",
    ): Promise<ContextualHelpResolveResponse> {
      const normalizedPack = pack === "orcia-core" ? "core" : pack;
      const params = new URLSearchParams({ route, lang, pack: normalizedPack });
      return requestJson<ContextualHelpResolveResponse>(
        `/api/v1/help/resolve?${params.toString()}`,
      );
    },
    rollbackContextualHelp: (payload: ContextualHelpRollbackRequest, personaKey?: string) =>
      requestJson<HelpArticleSchemaItem>(`/api/v1/help/rollback${buildPersonaQuery(personaKey)}`, "POST", payload),
    compileDnaStarlark(workspaceId: string, payload: CompileStarlarkMechanismRequest): Promise<StarlarkMechanismResponse> {
      return requestJson<StarlarkMechanismResponse>(`/api/v1/workspaces/${encodeURIComponent(workspaceId)}/dna-mechanisms/compile`, "POST", payload);
    },
    runRemoteServiceTestBench(payload: TestAndDiscoverConnectorRequest): Promise<ConnectorTestBenchReportResponse> {
      return requestJson<ConnectorTestBenchReportResponse>("/api/v1/settings/connectors/test-and-discover", "POST", payload);
    },
    validateHelpArticle(payload: ValidateHelpArticleRequest): Promise<HelpArticleValidationResponse> {
      return requestJson<HelpArticleValidationResponse>("/api/v1/pack-builder/processes/validate-help-article", "POST", payload);
    },
    listInstalledBusinessPacks(): Promise<InstalledBusinessPackListResponse> {
      return requestJson<InstalledBusinessPackListResponse>("/api/v1/pack-builder/installed-packs");
    },
    listWizardSessions(personaKey?: string): Promise<WizardSessionsListResponse> {
      return requestJson<WizardSessionsListResponse>(
        `/api/v1/wizards${buildPersonaQuery(personaKey)}`,
      );
    },
    getWizardSession(sessionId: string, personaKey?: string): Promise<WizardSessionResponse> {
      return requestJson<WizardSessionResponse>(
        `/api/v1/wizards/sessions/${encodeURIComponent(sessionId)}${buildPersonaQuery(personaKey)}`,
      );
    },
    startOrResumeWizard(payload: WizardSessionRequest): Promise<WizardSessionResponse> {
      return requestJson<WizardSessionResponse>("/api/v1/wizards/sessions", "POST", payload);
    },
    saveWizardStep(
      sessionId: string,
      payload: WizardAdvanceStepRequest,
    ): Promise<WizardSessionResponse> {
      return requestJson<WizardSessionResponse>(
        `/api/v1/wizards/sessions/${encodeURIComponent(sessionId)}/steps`,
        "POST",
        payload,
      );
    },
    stepBackWizard(
      sessionId: string,
      payload: WizardStepBackRequest,
    ): Promise<WizardSessionResponse> {
      return requestJson<WizardSessionResponse>(
        `/api/v1/wizards/sessions/${encodeURIComponent(sessionId)}/step-back`,
        "POST",
        payload,
      );
    },
    provisionWizardDemoWorkspace(personaKey?: string): Promise<DemoWorkspaceProvisionResponse> {
      const qs = personaKey ? `?actor_persona=${encodeURIComponent(personaKey)}` : "";
      return requestJson<DemoWorkspaceProvisionResponse>(
        `/api/v1/wizards/demo-workspace${qs}`,
        "POST",
      );
    },
  };
}
