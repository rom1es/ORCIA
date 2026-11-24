import { handleVitestAuthPolicyRoute } from "../vitestAuthPolicyMockHandlers";
import { handleVitestAutonomousSupervisionRoute } from "../vitestAutonomousSupervisionMockHandlers";
import { handleVitestConnectorsRoute } from "../vitestConnectorsMockHandlers";
import { handleVitestIamRoute } from "../vitestIamMockHandlers";
import { handleVitestOntologyRoute } from "../vitestOntologyMockHandlers";
import { handleVitestPacksAndWizardsRoute } from "../vitestPacksAndWizardsMockHandlers";
import { tryHandleVitestReflexiveEndpoint } from "../vitestReflexiveBackend";
import { handleAiModelsAndToolsRoute } from "./aiModelsAndToolsMockHandlers";
import { handleAssistantAndInboxRoute } from "./assistantAndInboxMockHandlers";
import { handleAuthAndBootstrapRoute } from "./authAndBootstrapMockHandlers";
import { handleAutonomyTriggersAndWorkflowsV2Route } from "./autonomyTriggersAndWorkflowsV2Handlers";
import { handleFinopsAndGatesRoute } from "./finopsAndGatesMockHandlers";
import { backendState, jsonResponse, parseJsonBody, problemResponse } from "./mockBackendState";
import { validateRequestAgainstOpenApi } from "./openApiRequestValidator";
import { handleOrchestrationRunsRoute } from "./orchestrationRunsMockHandlers";
import { handleOrgUnitsMutationsRoute } from "./orgUnitsMutationsHandlers";
import { handleOrgUnitsReadAndInviteRoute } from "./orgUnitsReadAndInviteHandlers";
import { syncSetupOrgUnitsFromMock } from "./orgUnitsScopeHelpers";
import { handleWorkspacesAndCatalogRoute } from "./workspacesAndCatalogMockHandlers";

export async function vitestFetchTransport(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const rawUrl =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;
  const parsedUrl = new URL(rawUrl, "http://127.0.0.1:8000");
  const path = parsedUrl.pathname;
  const method = (init?.method ?? "GET").toUpperCase();
  const { body, hasRawBody, isMultipart } = parseJsonBody(init);
  const reqHeaders = new Headers(init?.headers);
  const capturedHeadersObj: Record<string, string> = {};
  reqHeaders.forEach((v, k) => {
    capturedHeadersObj[k.toLowerCase()] = v;
  });

  backendState.recordedCalls.push({
    method,
    path,
    body,
    headers: capturedHeadersObj,
  });

  // Fail-Closed OpenAPI 3.1 contract validation (path, method, UUID, required, extra="forbid", security)
  const securityFailureResponse = validateRequestAgainstOpenApi({
    method,
    parsedUrl,
    body,
    hasRawBody,
    isMultipart,
    headers: reqHeaders,
  });
  if (securityFailureResponse) {
    return securityFailureResponse;
  }

  const authResp = handleAuthAndBootstrapRoute({ path, method, body });
  if (authResp) return authResp;

  const orgReadResp = handleOrgUnitsReadAndInviteRoute({ path, method, parsedUrl, body, reqHeaders });
  if (orgReadResp) return orgReadResp;

  const orgMutResp = handleOrgUnitsMutationsRoute({ path, method, body, reqHeaders });
  if (orgMutResp) return orgMutResp;

  const wsCatResp = handleWorkspacesAndCatalogRoute({ path, method, parsedUrl, body, reqHeaders });
  if (wsCatResp) return wsCatResp;

  const authPolicyResp = handleVitestAuthPolicyRoute({
    method,
    path,
    body,
    reqHeaders,
    jsonResponse,
    problemResponse,
  });
  if (authPolicyResp !== null) return authPolicyResp;

  const iamResp = handleVitestIamRoute({
    method,
    path,
    parsedUrl,
    body,
    reqHeaders,
    firstAdmin: backendState.firstAdmin,
    orgUnits: backendState.orgUnits,
    syncSetupOrgUnits: syncSetupOrgUnitsFromMock,
    jsonResponse,
    problemResponse,
  });
  if (iamResp !== null) return iamResp;

  const hasActiveEmbeddingModel = backendState.aiModelMappings.some(
    (m) => m.usage === "embedding" && m.is_active !== false && (m.scope_level ?? "GLOBAL") === "GLOBAL",
  );

  const connResp = handleVitestConnectorsRoute({
    method,
    path,
    parsedUrl,
    body,
    reqHeaders,
    firstAdmin: backendState.firstAdmin,
    orgUnits: backendState.orgUnits,
    hasActiveEmbeddingModel,
    jsonResponse,
    problemResponse: (status, title, detail, errorCode) =>
      problemResponse(status, errorCode, title, detail, path),
  });
  if (connResp !== null) return connResp;

  const assistantResp = await handleAssistantAndInboxRoute({ path, method, parsedUrl, body, init });
  if (assistantResp) return assistantResp;

  const toolsResp = handleAiModelsAndToolsRoute({ path, method, parsedUrl, body });
  if (toolsResp) return toolsResp;

  const orchResp = handleOrchestrationRunsRoute({ path, method, body });
  if (orchResp) return orchResp;

  const autoResp = handleAutonomyTriggersAndWorkflowsV2Route({ path, method, body });
  if (autoResp) return autoResp;

  const finopsGatesResp = handleFinopsAndGatesRoute({ path, method, body });
  if (finopsGatesResp) return finopsGatesResp;

  const setupWorkspaces = Array.isArray(
    (backendState.platformSetupState as Record<string, unknown> | null)?.workspaces,
  )
    ? ((backendState.platformSetupState as Record<string, unknown>).workspaces as Array<
        Record<string, unknown>
      >)
    : [];
  const ontologyResp = handleVitestOntologyRoute({
    path,
    method,
    parsedUrl,
    body,
    orgUnits: backendState.orgUnits,
    workspaces: setupWorkspaces,
    jsonResponse,
    problemResponse,
  });
  if (ontologyResp) return ontologyResp;

  const packsAndWizardsResp = handleVitestPacksAndWizardsRoute({
    path,
    method,
    parsedUrl,
    body,
    reqHeaders,
    jsonResponse,
    problemResponse,
  });
  if (packsAndWizardsResp) return packsAndWizardsResp;

  const supervisionResp = handleVitestAutonomousSupervisionRoute(
    path,
    method,
    body,
    jsonResponse,
    parsedUrl.searchParams,
  );
  if (supervisionResp) return supervisionResp;

  const reflexiveResp = await tryHandleVitestReflexiveEndpoint({
    path,
    parsedUrl,
    method,
    body,
    ...(init ? { init } : {}),
  });
  if (reflexiveResp) return reflexiveResp;

  throw new Error(
    `[vitestFetchTransport FAIL-CLOSED] Route non gérée par les handlers Vitest : ${method} ${path}`,
  );
}
