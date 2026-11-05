import createClient from "openapi-fetch";
import { createAgentsAndSkillsDomainClient } from "./domains/agentsAndSkills";
import { createAuthAndShellDomainClient } from "./domains/authAndShell";
import { createBootstrapAndOntologyDomainClient } from "./domains/bootstrapAndOntology";
import { createCatalogAndPermissionsDomainClient } from "./domains/catalogAndPermissions";
import type { paths } from "./generated/schema";
import { createRequestJson, OrciaProblemError, type OrciaApiClientOptions } from "./helpers";

export type * from "./generated/schema";
export {
  createAgentsAndSkillsDomainClient,
  createAuthAndShellDomainClient,
  createBootstrapAndOntologyDomainClient,
  createCatalogAndPermissionsDomainClient,
  OrciaProblemError,
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
    fetch: options.fetchImpl ?? globalThis.fetch,
  });
}

export function createOrciaApiClient(options: OrciaApiClientOptions) {
  const requestJson = createRequestJson(options);
  return {
    ...createAuthAndShellDomainClient(requestJson),
    ...createCatalogAndPermissionsDomainClient(requestJson),
    ...createBootstrapAndOntologyDomainClient(requestJson),
    ...createAgentsAndSkillsDomainClient(requestJson),
  };
}
