import createClient from "openapi-fetch";
import { createAuthAndShellDomainClient } from "./domains/authAndShell";
import { createBootstrapAndOntologyDomainClient } from "./domains/bootstrapAndOntology";
import { createCatalogAndPermissionsDomainClient } from "./domains/catalogAndPermissions";
import { createEpics1To7OperationsDomainClient } from "./domains/epics1To7Operations";
import type { paths } from "./generated/schema";
import { createRequestJson, OrciaProblemError, type OrciaApiClientOptions } from "./helpers";

export type * from "./generated/schema";
export {
  createAuthAndShellDomainClient,
  createBootstrapAndOntologyDomainClient,
  createCatalogAndPermissionsDomainClient,
  createEpics1To7OperationsDomainClient,
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
    ...createEpics1To7OperationsDomainClient(requestJson),
  };
}
