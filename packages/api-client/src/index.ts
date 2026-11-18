import createClient from "openapi-fetch";
import { createAgentsAndSkillsDomainClient } from "./domains/agentsAndSkills";
import { createAiModelsHubDomainClient } from "./domains/aiModelsHub";
import {
  createAuditFinopsDomainClient,
  type ListAuditLedgerParams,
} from "./domains/auditFinops";
import { createAuthAndShellDomainClient } from "./domains/authAndShell";
import { createAutonomousSupervisionDomainClient } from "./domains/autonomousSupervision";
import { createAutonomyContractsDomainClient } from "./domains/autonomyContracts";
import { createBootstrapAndOntologyDomainClient } from "./domains/bootstrapAndOntology";
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
  type ApiWorkflowDefinitionV2,
  type SaveWorkflowV2Options,
} from "./domains/workflowsV2";
import { createWorkflowTriggersDomainClient } from "./domains/workflowTriggers";
import type { paths } from "./generated/schema";
import {
  buildKnownOrgUsersQuery,
  buildOrgUnitsQuery,
  createRequestJson,
  OrciaProblemError,
  registerDefaultAccessTokenProvider,
  type ListKnownOrgUsersParams,
  type ListOrgUnitsParams,
  type OrciaApiClientOptions,
} from "./helpers";

export type * from "./generated/schema";
export type { PopularUsageItemResponse, UserProfileSummaryResponse } from "./generated/user_profile";
export {
  buildKnownOrgUsersQuery,
  buildOrgUnitsQuery,
  createAgentsAndSkillsDomainClient,
  createAiModelsHubDomainClient,
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
  createWorkflowsV2DomainClient,
  createWorkflowTriggersDomainClient,
  OrciaProblemError,
  registerDefaultAccessTokenProvider,
  type ApiImpactAssessmentResult,
  type ApiWorkflowDefinitionV2,
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
  type SaveWorkflowV2Options,
  type WritableScopeOptionItem,
  type OrciaApiClientOptions,
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
  const aiModelsHubClient = createAiModelsHubDomainClient(requestJson);
  const auditFinopsClient = createAuditFinopsDomainClient(requestJson);
  return {
    ...createAuthAndShellDomainClient(requestJson),
    ...createAutonomousSupervisionDomainClient(requestJson),
    ...createAutonomyContractsDomainClient(requestJson),
    ...createCatalogAndPermissionsDomainClient(requestJson),
    ...createCodegraphMcpDomainClient(requestJson),
    ...createBootstrapAndOntologyDomainClient(requestJson),
    ...createEpics1To7OperationsDomainClient(requestJson),
    ...createAgentsAndSkillsDomainClient(requestJson),
    ...createFinopsDomainClient(requestJson),
    ...createOntologyPromotionsDomainClient(requestJson),
    ...createReflexiveExecutionDomainClient(requestJson, options.baseUrl),
    ...createWorkflowsV2DomainClient(requestJson),
    ...createWorkflowTriggersDomainClient(requestJson),
    ...auditFinopsClient,
    ...aiModelsHubClient,
    aiModelsHub: aiModelsHubClient,
    auditFinops: auditFinopsClient,
  };
}
