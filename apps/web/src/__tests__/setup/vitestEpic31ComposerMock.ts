import { jsonResponse } from "./mockBackendState";
import {
  EPIC31_TRACE_ID,
  epic31MockStore,
  isEpic31Observer,
  type MockEpic31DraftPack,
} from "./vitestEpic31MockState";

function serializeDraftDetail(d: MockEpic31DraftPack) {
  return {
    bundle_id: d.bundle_id,
    pack_id: d.pack_id,
    slug: d.slug,
    name: d.name,
    version: d.version,
    description: d.description,
    author: d.author,
    maintainers: [],
    license: d.license,
    bundle_kind: "CUSTOM",
    scope_type: d.scope_type,
    scope_id: d.scope_id,
    status: d.status,
    source_origin: "ORCIA_COMPOSER",
    archive_sha256: "b".repeat(64),
    cas_object_key: null,
    declared_slots: [],
    quick_actions: [],
    members: d.members,
    closure: {
      complete: d.missing_dependencies.length === 0,
      missing_dependencies: d.missing_dependencies,
      non_active_dependencies: [],
      prose_lint_warnings: [],
      auto_included_count: 0,
    },
    trace_id: EPIC31_TRACE_ID,
  };
}

export function handleVitestEpic31ComposerRoute(params: {
  readonly path: string;
  readonly method: string;
  readonly parsedUrl: URL;
  readonly body: Record<string, unknown>;
  readonly reqHeaders: Headers;
  readonly problemResponse: (
    status: number,
    errorCode: string,
    title: string,
    detail: string,
    instance: string,
  ) => Response;
}): Response | null {
  const { path, method, parsedUrl, body, reqHeaders, problemResponse } = params;

  if (path === "/api/v1/packs/composer" && method === "GET") {
    return jsonResponse({
      drafts: epic31MockStore.draftPacks.map(serializeDraftDetail),
      trace_id: EPIC31_TRACE_ID,
    });
  }
  if (path === "/api/v1/packs/composer" && method === "POST") {
    if (isEpic31Observer(reqHeaders)) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Read-only", "Observer denied", path);
    }
    const bundleId = `0195f000-0000-7000-8000-00000000d0${epic31MockStore.draftPacks.length + 1}`;
    const created: MockEpic31DraftPack = {
      bundle_id: bundleId,
      pack_id: `orcia-pack-${String(body.slug ?? "custom")}`,
      slug: String(body.slug ?? "custom"),
      name: String(body.name ?? "Custom Pack"),
      version: String(body.version ?? "0.1.0"),
      description: String(body.description ?? ""),
      author: String(body.author ?? ""),
      license: String(body.license ?? "Apache-2.0"),
      scope_type: (body.scope_type as MockEpic31DraftPack["scope_type"]) ?? "WORKSPACE",
      scope_id: String(body.scope_id ?? "0195f000-0000-7000-8000-000000000311"),
      status: "DRAFT",
      members: [],
      missing_dependencies: [],
    };
    epic31MockStore.draftPacks.push(created);
    return jsonResponse(serializeDraftDetail(created), 201);
  }

  const draftGetPatchDelMatch = /^\/api\/v1\/packs\/composer\/([^/]+)$/.exec(path);
  if (draftGetPatchDelMatch) {
    const draftId = decodeURIComponent(draftGetPatchDelMatch[1] ?? "");
    const existing = epic31MockStore.draftPacks.find((d) => d.bundle_id === draftId);
    if (!existing) return problemResponse(404, "ERR_PACK_BUNDLE_NOT_FOUND", "Not found", "Draft not found", path);
    if (method === "GET") return jsonResponse(serializeDraftDetail(existing));
    if (method === "PATCH") {
      if (isEpic31Observer(reqHeaders)) return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Read-only", "Observer denied", path);
      if (typeof body.name === "string") existing.name = body.name;
      if (typeof body.version === "string") existing.version = body.version;
      if (typeof body.description === "string") existing.description = body.description;
      return jsonResponse(serializeDraftDetail(existing));
    }
    if (method === "DELETE") {
      epic31MockStore.draftPacks = epic31MockStore.draftPacks.filter((d) => d.bundle_id !== draftId);
      return jsonResponse({ bundle_id: draftId, slug: existing.slug, version: existing.version, deleted: true, trace_id: EPIC31_TRACE_ID });
    }
  }

  const draftMembersMatch = /^\/api\/v1\/packs\/composer\/([^/]+)\/members$/.exec(path);
  if (draftMembersMatch && method === "PUT") {
    const draftId = decodeURIComponent(draftMembersMatch[1] ?? "");
    const existing = epic31MockStore.draftPacks.find((d) => d.bundle_id === draftId);
    if (!existing) return problemResponse(404, "ERR_PACK_BUNDLE_NOT_FOUND", "Not found", "Draft not found", path);
    const rawMembers = Array.isArray(body.members) ? (body.members as Array<Record<string, unknown>>) : [];
    existing.members = rawMembers.map((m, i) => ({
      id: `mem-${i}`,
      draft_bundle_id: draftId,
      entity_type: String(m.entity_type ?? "AGENT"),
      entity_id: String(m.entity_id ?? ""),
      entity_slug: String(m.entity_slug ?? m.entity_id ?? ""),
      title: String(m.entity_slug ?? m.entity_id ?? ""),
      lifecycle_status: "ACTIVE",
    }));
    return jsonResponse(serializeDraftDetail(existing));
  }

  const draftPublishMatch = /^\/api\/v1\/packs\/composer\/([^/]+)\/publish$/.exec(path);
  if (draftPublishMatch && method === "POST") {
    const draftId = decodeURIComponent(draftPublishMatch[1] ?? "");
    const existing = epic31MockStore.draftPacks.find((d) => d.bundle_id === draftId);
    if (!existing) return problemResponse(404, "ERR_PACK_BUNDLE_NOT_FOUND", "Not found", "Draft not found", path);
    const autoInc = parsedUrl.searchParams.get("auto_include_dependencies") === "true" || body.auto_include_dependencies === true;
    if (existing.missing_dependencies.length > 0 && !autoInc) {
      return new Response(
        JSON.stringify({
          type: "https://orcia.io/problems/pack-closure-incomplete",
          title: "Closure incomplete",
          status: 422,
          detail: "Missing dependencies detected.",
          instance: path,
          error_code: "ERR_PACK_CLOSURE_INCOMPLETE",
          trace_id: EPIC31_TRACE_ID,
          missing_dependencies: existing.missing_dependencies,
        }),
        { status: 422, headers: { "Content-Type": "application/problem+json" } },
      );
    }
    existing.missing_dependencies = [];
    existing.status = "PUBLISHED";
    return jsonResponse(serializeDraftDetail(existing));
  }

  const draftExportMatch = /^\/api\/v1\/packs\/composer\/([^/]+)\/export$/.exec(path);
  if (draftExportMatch && method === "POST") {
    const draftId = decodeURIComponent(draftExportMatch[1] ?? "");
    const existing = epic31MockStore.draftPacks.find((d) => d.bundle_id === draftId);
    if (!existing) return problemResponse(404, "ERR_PACK_BUNDLE_NOT_FOUND", "Not found", "Draft not found", path);
    if (existing.description.toLowerCase().includes("secret") || existing.description.includes("@")) {
      return new Response(
        JSON.stringify({
          type: "https://orcia.io/problems/pack-pii-or-infra-leak",
          title: "PII or infra leak",
          status: 422,
          detail: "Sensitive literal detected.",
          instance: path,
          error_code: "ERR_PACK_PII_OR_INFRA_LEAK",
          trace_id: EPIC31_TRACE_ID,
          leak_findings: [{ path: "apm.yml", kind: "PII_EMAIL", detail: "Email or secret literal found" }],
        }),
        { status: 422, headers: { "Content-Type": "application/problem+json" } },
      );
    }
    const zipBlob = new Blob(["PK\x05\x06" + "\x00".repeat(18)], { type: "application/zip" });
    return new Response(zipBlob, {
      status: 200,
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${existing.slug}-${existing.version}.zip"`,
      },
    });
  }

  return null;
}
