import { jsonResponse } from "./mockBackendState";
import {
  DEFAULT_SDLC_SLOTS,
  EPIC31_TRACE_ID,
  epic31MockStore,
  getEpic31WsState,
  isEpic31Observer,
  type MockWsPackState,
} from "./vitestEpic31MockState";

export function handleVitestEpic31WorkspacePackRoute(params: {
  readonly path: string;
  readonly method: string;
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
  const { path, method, body, reqHeaders, problemResponse } = params;

  const wsListMatch = /^\/api\/v1\/workspaces\/([^/]+)\/packs$/.exec(path);
  if (wsListMatch && method === "GET") {
    const wsId = decodeURIComponent(wsListMatch[1] ?? "");
    const st = getEpic31WsState(wsId);
    const allBase = [
      {
        bundle_id: "0195f000-0000-7000-8000-00000000b001",
        pack_id: "orcia-pack-sdlc",
        slug: "sdlc",
        name: "Pack Ingénierie Logicielle & SDLC",
        version: "1.0.0",
        bundle_kind: "SYSTEM",
        scope_type: "GLOBAL",
        scope_id: "global",
        status: "PUBLISHED",
        archive_sha256: "a".repeat(64),
        description: "Pack déclaratif SDLC",
        declared_slots: DEFAULT_SDLC_SLOTS,
      },
      {
        bundle_id: "0195f000-0000-7000-8000-00000000b002",
        pack_id: "orcia-pack-docs",
        slug: "orcia-docs",
        name: "Pack Documentation & Aide ORCIA",
        version: "1.0.0",
        bundle_kind: "SYSTEM",
        scope_type: "GLOBAL",
        scope_id: "global",
        status: "PUBLISHED",
        archive_sha256: "b".repeat(64),
        description: "Pack documentation",
        declared_slots: [],
      },
      ...epic31MockStore.importedPacks.map((p) => ({
        bundle_id: String(p.bundle_id),
        pack_id: String(p.id),
        slug: String(p.slug),
        name: String(p.name),
        version: String(p.version),
        bundle_kind: "CUSTOM",
        scope_type: "WORKSPACE",
        scope_id: wsId,
        status: "PUBLISHED",
        archive_sha256: String(p.archive_sha256),
        description: String(p.description),
        declared_slots: [],
      })),
    ];
    return jsonResponse({
      workspace_id: wsId,
      packs: allBase.map((p) => {
        const entry = st[p.slug] ?? { is_active: false, priority_order: null, slot_bindings: [] };
        const missingSlots = p.declared_slots
          .filter(
            (s) =>
              s.required &&
              !entry.slot_bindings.some((b) => b.slot_key === s.slot_key && b.is_effective_bound),
          )
          .map((s) => s.slot_key);
        return {
          ...p,
          is_active: entry.is_active,
          priority_order: entry.priority_order,
          slot_bindings: entry.slot_bindings,
          missing_slots: missingSlots,
          readiness_ok: missingSlots.length === 0,
        };
      }),
      trace_id: EPIC31_TRACE_ID,
    });
  }

  const wsActivateMatch = /^\/api\/v1\/workspaces\/([^/]+)\/packs\/([^/]+)\/activate$/.exec(path);
  if (wsActivateMatch && method === "POST") {
    if (isEpic31Observer(reqHeaders)) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Read-only", "Observer denied", path);
    }
    const wsId = decodeURIComponent(wsActivateMatch[1] ?? "");
    const slug = decodeURIComponent(wsActivateMatch[2] ?? "");
    const st = getEpic31WsState(wsId);
    const cur = st[slug] ?? { is_active: false, priority_order: null, slot_bindings: [] };
    if (slug === "sdlc" && !cur.slot_bindings.some((b) => b.slot_key === "git_repo" && b.is_effective_bound)) {
      return new Response(
        JSON.stringify({
          type: "https://orcia.io/problems/pack-slot-unbound",
          title: "Required slot unbound",
          status: 422,
          detail: "Required pack slot(s) unbound for sdlc: git_repo",
          instance: path,
          error_code: "ERR_PACK_SLOT_UNBOUND",
          trace_id: EPIC31_TRACE_ID,
          missing_slots: ["git_repo"],
        }),
        { status: 422, headers: { "Content-Type": "application/problem+json" } },
      );
    }
    const maxPrio = Math.max(0, ...Object.values(st).map((x) => x.priority_order ?? 0));
    cur.is_active = true;
    cur.priority_order = cur.priority_order ?? maxPrio + 1;
    st[slug] = cur;
    return jsonResponse({
      activation_id: "0195f000-0000-7000-8000-00000000a001",
      workspace_id: wsId,
      pack_bundle_id: "0195f000-0000-7000-8000-00000000b001",
      pack_slug: slug,
      version: "1.0.0",
      priority_order: cur.priority_order,
      is_active: true,
      activated_at_iso: "2026-11-26T12:00:00Z",
      trace_id: EPIC31_TRACE_ID,
    });
  }

  const wsDeactivateMatch = /^\/api\/v1\/workspaces\/([^/]+)\/packs\/([^/]+)\/deactivate$/.exec(path);
  if (wsDeactivateMatch && method === "DELETE") {
    if (isEpic31Observer(reqHeaders)) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Read-only", "Observer denied", path);
    }
    const wsId = decodeURIComponent(wsDeactivateMatch[1] ?? "");
    const slug = decodeURIComponent(wsDeactivateMatch[2] ?? "");
    const st = getEpic31WsState(wsId);
    const cur = st[slug] ?? { is_active: false, priority_order: null, slot_bindings: [] };
    cur.is_active = false;
    cur.priority_order = null;
    st[slug] = cur;
    return jsonResponse({
      workspace_id: wsId,
      pack_bundle_id: "0195f000-0000-7000-8000-00000000b001",
      pack_slug: slug,
      is_active: false,
      trace_id: EPIC31_TRACE_ID,
    });
  }

  const wsReorderMatch = /^\/api\/v1\/workspaces\/([^/]+)\/packs\/reorder$/.exec(path);
  if (wsReorderMatch && method === "PUT") {
    if (isEpic31Observer(reqHeaders)) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Read-only", "Observer denied", path);
    }
    const wsId = decodeURIComponent(wsReorderMatch[1] ?? "");
    const st = getEpic31WsState(wsId);
    const slugs = Array.isArray(body.ordered_pack_slugs) ? (body.ordered_pack_slugs as string[]) : [];
    const out = slugs.map((s, idx) => {
      if (st[s]) st[s]!.priority_order = idx + 1;
      return {
        pack_slug: s,
        pack_bundle_id: `0195f000-0000-7000-8000-00000000b00${idx + 1}`,
        priority_order: idx + 1,
      };
    });
    return jsonResponse({ workspace_id: wsId, packs: out, trace_id: EPIC31_TRACE_ID });
  }

  const wsSlotsMatch = /^\/api\/v1\/workspaces\/([^/]+)\/packs\/([^/]+)\/slots$/.exec(path);
  if (wsSlotsMatch && method === "PUT") {
    if (isEpic31Observer(reqHeaders)) {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Read-only", "Observer denied", path);
    }
    const wsId = decodeURIComponent(wsSlotsMatch[1] ?? "");
    const slug = decodeURIComponent(wsSlotsMatch[2] ?? "");
    const st = getEpic31WsState(wsId);
    const cur = st[slug] ?? { is_active: false, priority_order: null, slot_bindings: [] };
    const bindings = Array.isArray(body.bindings) ? (body.bindings as Array<Record<string, unknown>>) : [];
    cur.slot_bindings = bindings.map((b) => {
      const targetKind = String(b.target_kind ?? "UNBOUND") as MockWsPackState["slot_bindings"][number]["target_kind"];
      const targetId = b.target_id ? String(b.target_id) : null;
      const bound = targetKind !== "UNBOUND" && Boolean(targetId);
      return {
        slot_key: String(b.slot_key ?? ""),
        target_kind: targetKind,
        target_id: targetId,
        target_display_name: targetId,
        target_uri: targetId ? `git://org/${targetId}` : null,
        target_enabled: true,
        is_effective_bound: bound,
      };
    });
    st[slug] = cur;
    return jsonResponse({ workspace_id: wsId, pack_slug: slug, slot_bindings: cur.slot_bindings, trace_id: EPIC31_TRACE_ID });
  }

  return null;
}
