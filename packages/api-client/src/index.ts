import createClient from "openapi-fetch";
import { createAgentsAndSkillsDomainClient } from "./domains/agentsAndSkills";
import { createAiModelsHubDomainClient } from "./domains/aiModelsHub";
import {
  createAuditFinopsDomainClient,
  type ListAuditLedgerParams,
} from "./domains/auditFinops";
import { createAuthAndShellDomainClient } from "./domains/authAndShell";
import { createAutonomyContractsDomainClient } from "./domains/autonomyContracts";
import { createBootstrapAndOntologyDomainClient } from "./domains/bootstrapAndOntology";
import { createCatalogAndPermissionsDomainClient } from "./domains/catalogAndPermissions";
import { createCodegraphMcpDomainClient } from "./domains/codegraphMcp";
import { createEpics1To7OperationsDomainClient } from "./domains/epics1To7Operations";
import { createFinopsDomainClient } from "./domains/finops";
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
export {
  buildKnownOrgUsersQuery,
  buildOrgUnitsQuery,
  createAgentsAndSkillsDomainClient,
  createAiModelsHubDomainClient,
  createAuditFinopsDomainClient,
  createAuthAndShellDomainClient,
  createAutonomyContractsDomainClient,
  createBootstrapAndOntologyDomainClient,
  createCatalogAndPermissionsDomainClient,
  createCodegraphMcpDomainClient,
  createEpics1To7OperationsDomainClient,
  createFinopsDomainClient,
  createWorkflowTriggersDomainClient,
  OrciaProblemError,
  registerDefaultAccessTokenProvider,
  type ListAuditLedgerParams,
  type ListKnownOrgUsersParams,
  type ListOrgUnitsParams,
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
    ...createAutonomyContractsDomainClient(requestJson),
    ...createCatalogAndPermissionsDomainClient(requestJson),
    ...createCodegraphMcpDomainClient(requestJson),
    ...createBootstrapAndOntologyDomainClient(requestJson),
    ...createEpics1To7OperationsDomainClient(requestJson),
    ...createAgentsAndSkillsDomainClient(requestJson),
    ...createFinopsDomainClient(requestJson),
    ...createWorkflowTriggersDomainClient(requestJson),
    ...auditFinopsClient,
    ...aiModelsHubClient,
    aiModelsHub: aiModelsHubClient,
    auditFinops: auditFinopsClient,
  };
}
