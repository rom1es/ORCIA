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
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export function createBootstrapAndOntologyDomainClient(requestJson: RequestJsonFn) {
  return {
    getAccostageStatus(): Promise<AccostageStatusResponse> {
      return requestJson<AccostageStatusResponse>("/api/v1/bootstrap/accostage-status");
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
  };
}
