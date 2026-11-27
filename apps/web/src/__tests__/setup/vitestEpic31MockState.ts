import { useAuthSessionStore } from "../../stores/authSessionStore";

export const EPIC31_TRACE_ID = "0195f000000070008000000000000931";

export interface MockEpic31DraftPack {
  bundle_id: string;
  pack_id: string;
  slug: string;
  name: string;
  version: string;
  description: string;
  author: string;
  license: string;
  scope_type: "BU" | "TEAM" | "WORKSPACE";
  scope_id: string;
  status: "DRAFT" | "PUBLISHED";
  members: Array<{
    id: string;
    draft_bundle_id: string;
    entity_type: string;
    entity_id: string;
    entity_slug: string;
    title: string;
    lifecycle_status: string;
  }>;
  missing_dependencies: Array<{
    entity_type: string;
    entity_id: string;
    reason: string;
    referenced_by: string;
  }>;
}

export interface MockWsPackState {
  is_active: boolean;
  priority_order: number | null;
  slot_bindings: Array<{
    slot_key: string;
    target_kind: "UNBOUND" | "WORKSPACE_DATASOURCE" | "ENTERPRISE_CONNECTOR" | "INTERNAL";
    target_id: string | null;
    target_display_name: string | null;
    target_uri: string | null;
    target_enabled: boolean;
    is_effective_bound: boolean;
  }>;
}

export const DEFAULT_SDLC_SLOTS = [
  {
    slot_key: "git_repo",
    scheme: "git",
    connector_kind: "mcp:git-provider",
    source_nature: "SOURCE_CODE",
    required_access: ["read"],
    required: true,
    description_fr: "Dépôt Git principal",
    description_en: "Primary Git repository",
  },
  {
    slot_key: "wiki_space",
    scheme: "confluence",
    connector_kind: "mcp:atlassian-confluence",
    source_nature: "DOCUMENTATION",
    required_access: ["read"],
    required: false,
    description_fr: "Espace documentaire optionnel",
    description_en: "Optional documentation wiki",
  },
];

export const epic31MockStore: {
  importedPacks: Array<Record<string, unknown>>;
  draftPacks: MockEpic31DraftPack[];
  wsStateMap: Record<string, Record<string, MockWsPackState>>;
} = {
  importedPacks: [],
  draftPacks: [],
  wsStateMap: {},
};

export function resetVitestEpic31PackState(): void {
  epic31MockStore.importedPacks = [];
  epic31MockStore.draftPacks = [];
  epic31MockStore.wsStateMap = {};
}

export function isEpic31Observer(reqHeaders: Headers): boolean {
  const session = useAuthSessionStore.getState();
  return (
    (reqHeaders.get("x-orcia-access-mode") ?? "").toUpperCase() === "READ_ONLY_OBSERVER" ||
    Boolean(session.readOnlyObserver) ||
    (session.roles ?? []).map((r) => String(r).toUpperCase()).includes("OBSERVER")
  );
}

export function seedMockDraftPackForEntity(params: {
  bundleId?: string;
  slug: string;
  name: string;
  entityType: string;
  entityId: string;
  entitySlug: string;
  missingDependencies?: MockEpic31DraftPack["missing_dependencies"];
}): void {
  const bundleId =
    params.bundleId ?? `0195f000-0000-7000-8000-00000000d0${epic31MockStore.draftPacks.length + 1}`;
  epic31MockStore.draftPacks.push({
    bundle_id: bundleId,
    pack_id: `orcia-pack-${params.slug}`,
    slug: params.slug,
    name: params.name,
    version: "0.1.0",
    description: "",
    author: "Test Author",
    license: "Apache-2.0",
    scope_type: "WORKSPACE",
    scope_id: "0195f000-0000-7000-8000-000000000311",
    status: "DRAFT",
    members: [
      {
        id: `m-${params.entityId}`,
        draft_bundle_id: bundleId,
        entity_type: params.entityType,
        entity_id: params.entityId,
        entity_slug: params.entitySlug,
        title: params.entitySlug,
        lifecycle_status: "ACTIVE",
      },
    ],
    missing_dependencies: params.missingDependencies ?? [],
  });
}

export function checkAndUnlinkDraftMembership(params: {
  entityType: string;
  entityId: string;
  unlinkFromDraftPacks: boolean;
  path: string;
}): Response | null {
  const refs = epic31MockStore.draftPacks.filter(
    (d) =>
      d.status === "DRAFT" &&
      d.members.some((m) => m.entity_type === params.entityType && m.entity_id === params.entityId),
  );
  if (refs.length === 0) return null;
  if (!params.unlinkFromDraftPacks) {
    return new Response(
      JSON.stringify({
        type: "https://orcia.io/problems/entity-referenced-by-pack-draft",
        title: "Élément référencé par un pack en brouillon",
        status: 409,
        detail: `Referenced by draft pack(s): ${refs.map((r) => r.slug).join(", ")}`,
        instance: params.path,
        error_code: "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT",
        trace_id: EPIC31_TRACE_ID,
        draft_packs: refs.map((r) => ({
          bundle_id: r.bundle_id,
          slug: r.slug,
          name: r.name,
          version: r.version,
        })),
      }),
      { status: 409, headers: { "Content-Type": "application/problem+json" } },
    );
  }
  epic31MockStore.draftPacks = epic31MockStore.draftPacks.map((d) => ({
    ...d,
    members: d.members.filter(
      (m) => !(m.entity_type === params.entityType && m.entity_id === params.entityId),
    ),
  }));
  return null;
}

export function getEpic31WsState(wsId: string): Record<string, MockWsPackState> {
  if (!epic31MockStore.wsStateMap[wsId]) {
    epic31MockStore.wsStateMap[wsId] = {
      sdlc: { is_active: false, priority_order: null, slot_bindings: [] },
      "orcia-docs": { is_active: true, priority_order: 1, slot_bindings: [] },
    };
  }
  return epic31MockStore.wsStateMap[wsId]!;
}
