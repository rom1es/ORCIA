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
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type FederatedSearchResponse = components["schemas"]["TwoSpeedSearchResponse"];
export type UserPreferencesResponse = components["schemas"]["UserPreferencesResponse"];
export type UserPreferencesPatchRequest = components["schemas"]["UserPreferencesUpdateRequest"];
export type ContextualHelpResolveResponse = components["schemas"]["ContextualHelpResolveResponse"];
export type ThreeSpeedTurnRequest = components["schemas"]["ThreeSpeedTurnRequest"];
export type ThreeSpeedTurnResponse = components["schemas"]["ThreeSpeedTurnResponse"];
export type AssistantWorkspaceOverviewResponse =
  components["schemas"]["AssistantWorkspaceOverviewResponse"];
export type CreateAssistantFolderRequest =
  components["schemas"]["CreateOrUpdateAssistantFolderRequest"];
export type AssistantFolderResponse = components["schemas"]["AssistantFolderSchemaItem"];
export type CompileStarlarkMechanismRequest =
  components["schemas"]["CompileStarlarkMechanismRequest"];
export type StarlarkMechanismResponse = components["schemas"]["GeneratedStarlarkMechanismResponse"];
export type TestAndDiscoverConnectorRequest =
  components["schemas"]["RemoteServiceTestAndDiscoverRequest"];
export type ConnectorTestBenchReportResponse =
  components["schemas"]["RemoteServiceTestAndDiscoverResponse"];
export type ValidateHelpArticleRequest = components["schemas"]["ValidateHelpArticleRequest"];
export type HelpArticleValidationResponse = components["schemas"]["ValidateHelpArticleResponse"];
export type InstalledBusinessPackItemResponse =
  components["schemas"]["InstalledBusinessPackItemResponse"];
export type InstalledBusinessPackListResponse =
  components["schemas"]["InstalledBusinessPackListResponse"];

export function createBootstrapAndOntologyDomainClient(requestJson: RequestJsonFn) {
  return {
    getAccostageStatus(): Promise<AccostageStatusResponse> {
      return requestJson<AccostageStatusResponse>("/api/v1/bootstrap/accostage-status");
    },
    getPlatformSetupState(): Promise<PlatformSetupStateResponse> {
      return requestJson<PlatformSetupStateResponse>("/api/v1/bootstrap/platform-setup-state");
    },
    savePlatformSetupState(
      payload: PlatformSetupStatePutRequest,
    ): Promise<PlatformSetupStateResponse> {
      return requestJson<PlatformSetupStateResponse>(
        "/api/v1/bootstrap/platform-setup-state",
        "PUT",
        payload,
      );
    },
    createWelcomeSetupFirstAdmin(
      payload: WelcomeSetupFirstAdminRequest,
    ): Promise<WelcomeSetupFirstAdminResponse> {
      return requestJson<WelcomeSetupFirstAdminResponse>(
        "/api/v1/bootstrap/welcome-setup/first-admin",
        "POST",
        payload,
      );
    },
    registerProgressiveLlmEndpoint(
      payload: ProgressiveLlmEndpointRequest,
    ): Promise<AccostageStatusResponse> {
      return requestJson<AccostageStatusResponse>(
        "/api/v1/bootstrap/welcome-setup/progressive-llm",
        "POST",
        payload,
      );
    },
    getSystemBootstrapState(personaKey?: string): Promise<SystemBootstrapStateResponse> {
      return requestJson<SystemBootstrapStateResponse>(
        `/api/v1/bootstrap/state${buildPersonaQuery(personaKey)}`,
      );
    },
    executeInitOrganization(
      payload: InitOrganizationRequest,
      personaKey?: string,
    ): Promise<InitOrganizationResponse> {
      return requestJson<InitOrganizationResponse>(
        `/api/v1/bootstrap/init-organization${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeInitWorkspace(
      payload: InitWorkspaceRequest,
      personaKey?: string,
    ): Promise<InitWorkspaceResponse> {
      return requestJson<InitWorkspaceResponse>(
        `/api/v1/bootstrap/init-workspace${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeInitDatasource(
      payload: InitDatasourceRequest,
      personaKey?: string,
    ): Promise<InitDatasourceResponse> {
      return requestJson<InitDatasourceResponse>(
        `/api/v1/bootstrap/init-datasource${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeInitUser(payload: InitUserRequest, personaKey?: string): Promise<InitUserResponse> {
      return requestJson<InitUserResponse>(
        `/api/v1/bootstrap/init-user${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    getOntologyAndRagState(fixture = false): Promise<OntologyAndRagStateResponse> {
      return requestJson<OntologyAndRagStateResponse>(
        `/api/v1/ontology-rag/state?fixture=${fixture ? "true" : "false"}`,
      );
    },
    resolveOntologyHierarchy(
      payload: OntologyResolveRequest,
      fixture = false,
    ): Promise<OntologyResolveResponse> {
      return requestJson<OntologyResolveResponse>(
        `/api/v1/ontology-rag/ontology/resolve?fixture=${fixture ? "true" : "false"}`,
        "POST",
        payload,
      );
    },
    upsertOntologyConcept(
      payload: OntologyUpsertConceptRequest,
      fixture = false,
    ): Promise<OntologyConceptSchemaItem> {
      return requestJson<OntologyConceptSchemaItem>(
        `/api/v1/ontology-rag/ontology/concepts?fixture=${fixture ? "true" : "false"}`,
        "POST",
        payload,
      );
    },
    simulateOntologyWhatIf(
      payload: WhatIfSimulationRequest,
      fixture = false,
    ): Promise<WhatIfSimulationResponse> {
      return requestJson<WhatIfSimulationResponse>(
        `/api/v1/ontology-rag/ontology/what-if?fixture=${fixture ? "true" : "false"}`,
        "POST",
        payload,
      );
    },
    promoteOntologyProposal(
      payload: OntologyPromoteRequest,
      fixture = false,
    ): Promise<OntologyPromotionProposalSchemaItem> {
      return requestJson<OntologyPromotionProposalSchemaItem>(
        `/api/v1/ontology-rag/ontology/promote?fixture=${fixture ? "true" : "false"}`,
        "POST",
        payload,
      );
    },
    searchHybridRag(
      payload: HybridRagSearchRequest,
      fixture = false,
    ): Promise<HybridRagSearchResponse> {
      return requestJson<HybridRagSearchResponse>(
        `/api/v1/ontology-rag/rag/search?fixture=${fixture ? "true" : "false"}`,
        "POST",
        payload,
      );
    },
    indexDbDdlSchema(
      payload: DbDdlIndexRequest,
      fixture = false,
    ): Promise<KbDocumentSchemaItem> {
      return requestJson<KbDocumentSchemaItem>(
        `/api/v1/ontology-rag/rag/index-db-ddl?fixture=${fixture ? "true" : "false"}`,
        "POST",
        payload,
      );
    },
    auditDocVsCode(
      payload: DocVsCodeAuditRequest,
      fixture = false,
    ): Promise<DocVsCodeAuditResponse> {
      return requestJson<DocVsCodeAuditResponse>(
        `/api/v1/ontology-rag/tripartite/audit-doc-vs-code?fixture=${fixture ? "true" : "false"}`,
        "POST",
        payload,
      );
    },
    searchFederated(
      query: string,
      scope: "CONTEXTUAL" | "GLOBAL" = "CONTEXTUAL",
      workspaceId?: string | null,
      screenRoute = "/spaces",
    ): Promise<FederatedSearchResponse> {
      const params = new URLSearchParams({
        q: query,
        scope,
        screen_route: screenRoute,
      });
      if (workspaceId) {
        params.set("workspace_id", workspaceId);
      }
      return requestJson<FederatedSearchResponse>(`/api/v1/search?${params.toString()}`);
    },
    getUserPreferences(personaKey?: string): Promise<UserPreferencesResponse> {
      return requestJson<UserPreferencesResponse>(
        `/api/v1/users/me/preferences${buildPersonaQuery(personaKey)}`,
      );
    },
    updateUserPreferences(
      payload: UserPreferencesPatchRequest,
      personaKey?: string,
    ): Promise<UserPreferencesResponse> {
      return requestJson<UserPreferencesResponse>(
        `/api/v1/users/me/preferences${buildPersonaQuery(personaKey)}`,
        "PATCH",
        payload,
      );
    },
    resolveContextualHelp(
      route: string,
      lang: "fr" | "en" = "fr",
      pack = "core",
    ): Promise<ContextualHelpResolveResponse> {
      const params = new URLSearchParams({ route, lang, pack });
      return requestJson<ContextualHelpResolveResponse>(
        `/api/v1/help/resolve?${params.toString()}`,
      );
    },
    executeAssistantTurn(payload: ThreeSpeedTurnRequest): Promise<ThreeSpeedTurnResponse> {
      return requestJson<ThreeSpeedTurnResponse>(
        "/api/v1/assistant/three-speed/turn",
        "POST",
        payload,
      );
    },
    listAssistantFolders(workspaceId: string): Promise<AssistantWorkspaceOverviewResponse> {
      return requestJson<AssistantWorkspaceOverviewResponse>(
        `/api/v1/assistant/workspaces/${encodeURIComponent(workspaceId)}/overview`,
      );
    },
    createAssistantFolder(
      payload: CreateAssistantFolderRequest,
    ): Promise<AssistantFolderResponse> {
      return requestJson<AssistantFolderResponse>("/api/v1/assistant/folders", "POST", payload);
    },
    compileDnaStarlark(
      workspaceId: string,
      payload: CompileStarlarkMechanismRequest,
    ): Promise<StarlarkMechanismResponse> {
      return requestJson<StarlarkMechanismResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/dna-mechanisms/compile`,
        "POST",
        payload,
      );
    },
    runRemoteServiceTestBench(
      payload: TestAndDiscoverConnectorRequest,
    ): Promise<ConnectorTestBenchReportResponse> {
      return requestJson<ConnectorTestBenchReportResponse>(
        "/api/v1/settings/connectors/test-and-discover",
        "POST",
        payload,
      );
    },
    validateHelpArticle(
      payload: ValidateHelpArticleRequest,
    ): Promise<HelpArticleValidationResponse> {
      return requestJson<HelpArticleValidationResponse>(
        "/api/v1/pack-builder/processes/validate-help-article",
        "POST",
        payload,
      );
    },
    listInstalledBusinessPacks(): Promise<InstalledBusinessPackListResponse> {
      return requestJson<InstalledBusinessPackListResponse>(
        "/api/v1/pack-builder/installed-packs",
      );
    },
  };
}
