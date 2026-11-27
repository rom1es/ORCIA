import { backendState, jsonResponse } from "./mockBackendState";
import { handleVitestEpic31ComposerRoute } from "./vitestEpic31ComposerMock";
import {
  checkAndUnlinkDraftMembership,
  EPIC31_TRACE_ID,
  epic31MockStore,
  isEpic31Observer,
  resetVitestEpic31PackState,
  seedMockDraftPackForEntity,
} from "./vitestEpic31MockState";
import { handleVitestEpic31WorkspacePackRoute } from "./vitestEpic31WorkspacePacksMock";

export {
  checkAndUnlinkDraftMembership,
  resetVitestEpic31PackState,
  seedMockDraftPackForEntity,
};

export function listMockImportedPacks(): Array<Record<string, unknown>> {
  return epic31MockStore.importedPacks;
}

export function handleVitestEpic31PackRoute(params: {
  readonly path: string;
  readonly method: string;
  readonly parsedUrl: URL;
  readonly body: Record<string, unknown>;
  readonly rawInit?: RequestInit;
  readonly reqHeaders: Headers;
  readonly problemResponse: (
    status: number,
    errorCode: string,
    title: string,
    detail: string,
    instance: string,
  ) => Response;
}): Response | null {
  const { path, method, parsedUrl, body, rawInit, reqHeaders, problemResponse } = params;

  const wsResp = handleVitestEpic31WorkspacePackRoute({
    path,
    method,
    body,
    reqHeaders,
    problemResponse,
  });
  if (wsResp) return wsResp;

  const composerResp = handleVitestEpic31ComposerRoute({
    path,
    method,
    parsedUrl,
    body,
    reqHeaders,
    problemResponse,
  });
  if (composerResp) return composerResp;

  if (path === "/api/v1/packs/import" && method === "POST") {
    if (isEpic31Observer(reqHeaders)) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Read-only", "Observer denied", path);
    }
    let filename = "custom-pack.zip";
    if (typeof FormData !== "undefined" && rawInit?.body instanceof FormData) {
      const f = rawInit.body.get("file");
      if (f && typeof f === "object" && "name" in f) {
        filename = String((f as File).name);
      }
    }
    if (filename.endsWith(".sh") || filename.endsWith(".py") || filename.includes("hook")) {
      return problemResponse(
        422,
        "ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN",
        "Executable forbidden",
        "Executable hooks are forbidden in declarative packs.",
        path,
      );
    }
    const slug =
      filename
        .replace(/\.(zip|ya?ml)$/i, "")
        .toLowerCase()
        .replace(/[^a-z0-9-]+/g, "-") || "imported-pack";
    const bundleId = `0195f000-0000-7000-8000-00000000i0${epic31MockStore.importedPacks.length + 1}`;
    const created = {
      id: `orcia-pack-${slug}`,
      bundle_id: bundleId,
      slug,
      name: `Imported ${slug}`,
      version: "1.0.0",
      description: `Imported pack ${slug}`,
      rbac_namespace: slug,
      bundle_sha256: "c".repeat(64),
      archive_sha256: "c".repeat(64),
      bundle_kind: "CUSTOM",
      scope_type: "WORKSPACE",
      scope_id: "0195f000-0000-7000-8000-000000000311",
      status: "PUBLISHED",
      agents_count: 1,
      skills_count: 0,
      gates_count: 0,
      vsm_count: 0,
      workflows_count: 0,
      agents_slugs: ["imported-agent"],
      skills_slugs: [],
      gates_slugs: [],
      declared_slots: [],
      required_connectors: [],
      connector_health: [],
      quick_actions: [],
    };
    epic31MockStore.importedPacks = [
      ...epic31MockStore.importedPacks.filter((p) => p.slug !== slug),
      created,
    ];
    return jsonResponse({
      bundle_id: bundleId,
      pack_id: created.id,
      slug,
      name: created.name,
      version: "1.0.0",
      bundle_kind: "CUSTOM",
      scope_type: "WORKSPACE",
      scope_id: created.scope_id,
      status: "PUBLISHED",
      archive_sha256: created.archive_sha256,
      cas_object_key: `cas/${created.archive_sha256}`,
      idempotent_noop: false,
      counts: {
        agents: 1,
        skills: 0,
        instructions: 0,
        workflows: 0,
        vsm: 0,
        ontology_terms: 0,
        dna_mechanisms: 0,
        policies: 0,
        help_articles: 0,
      },
      trace_id: EPIC31_TRACE_ID,
    });
  }

  const delBundleMatch = /^\/api\/v1\/packs\/([^/]+)$/.exec(path);
  if (delBundleMatch && method === "DELETE") {
    const bundleId = decodeURIComponent(delBundleMatch[1] ?? "");
    if (bundleId.includes("sdlc") || bundleId.includes("orcia-docs")) {
      return problemResponse(403, "ERR_PACK_SYSTEM_DELETE_FORBIDDEN", "System pack", "Cannot delete system pack.", path);
    }
    const found = epic31MockStore.importedPacks.find((p) => p.bundle_id === bundleId || p.id === bundleId);
    epic31MockStore.importedPacks = epic31MockStore.importedPacks.filter(
      (p) => p.bundle_id !== bundleId && p.id !== bundleId,
    );
    return jsonResponse({
      bundle_id: bundleId,
      slug: String(found?.slug ?? "custom"),
      version: "1.0.0",
      deleted: true,
      trace_id: EPIC31_TRACE_ID,
    });
  }

  const delWfMatch = /^\/api\/v1\/workflows\/v2\/([^/]+)$/.exec(path);
  if (delWfMatch && method === "DELETE") {
    const wfId = decodeURIComponent(delWfMatch[1] ?? "");
    const unlink = parsedUrl.searchParams.get("unlink_from_draft_packs") === "true";
    const blocked = checkAndUnlinkDraftMembership({
      entityType: "WORKFLOW_V2",
      entityId: wfId,
      unlinkFromDraftPacks: unlink,
      path,
    });
    if (blocked) return blocked;
    backendState.workflowsV2.delete(wfId);
    return jsonResponse({
      entity_type: "WORKFLOW_V2",
      deleted_id: wfId,
      deleted_uuid: wfId,
      unlinked_draft_packs: [],
      trace_id: EPIC31_TRACE_ID,
    });
  }

  return null;
}
