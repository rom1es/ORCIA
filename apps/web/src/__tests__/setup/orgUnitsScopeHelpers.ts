import { useAuthSessionStore } from "../../stores/authSessionStore";
import { getVitestIamAccounts, syncVitestIamRolesWithOrgUnits } from "../vitestIamMockHandlers";
import type { MockOrganizationalUnit } from "./mockBackendState";
import { backendState } from "./mockBackendState";

const MOCK_KNOWN_ORG_USERS = [
  { principal_id: "claire.admin@orcia.fr", display_name: "Claire Admin", email: "claire.admin@orcia.fr" },
  { principal_id: "vp.produit@orcia.fr", display_name: "VP Produit", email: "vp.produit@orcia.fr" },
  { principal_id: "marc.lead@orcia.fr", display_name: "Marc Lead", email: "marc.lead@orcia.fr" },
  { principal_id: "alice@orcia.fr", display_name: "Alice Développeuse", email: "alice@orcia.fr" },
  { principal_id: "bob@orcia.fr", display_name: "Bob Ingénieur", email: "bob@orcia.fr" },
  { principal_id: "romain@orcia.fr", display_name: "Romain Esnault", email: "romain@orcia.fr" },
];

export function hydrateMockOrgUnitsFromSetup(rawUnits: unknown): MockOrganizationalUnit[] {
  if (!Array.isArray(rawUnits)) return [];
  return rawUnits.map((raw, index) => {
    const item = raw as Record<string, unknown>;
    const id = String(item.id ?? `org-${index + 1}`);
    const name = String(item.name ?? id);
    const slug = String(
      item.slug ?? name.toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-|-$/g, ""),
    );
    const rawLevel = String(item.level ?? item.kind ?? "BU").toUpperCase();
    const kind: "BU" | "TEAM" = rawLevel === "TEAM" ? "TEAM" : "BU";
    const rawParent = item.parentId ?? item.parent_id ?? null;
    const parent_id =
      typeof rawParent === "string" && rawParent.trim() && rawParent !== "scope-global"
        ? rawParent.trim()
        : null;
    const billing_enabled =
      item.billingEnabled !== undefined
        ? Boolean(item.billingEnabled)
        : item.billing_enabled !== undefined
          ? Boolean(item.billing_enabled)
          : true;
    const rawLead = item.leadUserId ?? item.lead_user_id ?? null;
    const lead_user_id = typeof rawLead === "string" && rawLead.trim() ? rawLead.trim() : null;
    const rawLeadIds = item.leadUserIds ?? item.lead_user_ids ?? [];
    const lead_user_ids =
      Array.isArray(rawLeadIds) && rawLeadIds.length > 0
        ? rawLeadIds.map((l) => String(l).trim()).filter(Boolean)
        : lead_user_id
          ? [lead_user_id]
          : [];
    const rawOntologyLeads = item.ontologyLeadUserIds ?? item.ontology_lead_user_ids ?? [];
    const ontology_lead_user_ids =
      kind === "BU" && Array.isArray(rawOntologyLeads)
        ? rawOntologyLeads.map((l) => String(l).trim()).filter(Boolean)
        : [];
    const rawMembers = item.memberUserIds ?? item.member_user_ids ?? [];
    const member_user_ids = Array.isArray(rawMembers)
      ? rawMembers.map((m) => String(m).trim()).filter(Boolean)
      : [];
    return {
      id,
      slug,
      name,
      kind,
      parent_id,
      billing_enabled,
      lead_user_id: lead_user_ids[0] ?? lead_user_id,
      lead_user_ids,
      ontology_lead_user_ids,
      member_user_ids: kind === "BU" ? [] : member_user_ids,
    };
  });
}

export function syncSetupOrgUnitsFromMock(): void {
  const mapped = backendState.orgUnits.map((u) => ({
    id: u.id,
    name: u.name,
    slug: u.slug,
    level: u.kind,
    parentId: u.parent_id ?? "scope-global",
    billingEnabled: u.billing_enabled,
    leadUserId: u.lead_user_id,
    leadUserIds: u.lead_user_ids ?? (u.lead_user_id ? [u.lead_user_id] : []),
    ontologyLeadUserIds: u.kind === "BU" ? (u.ontology_lead_user_ids ?? []) : [],
    memberUserIds: u.kind === "BU" ? [] : u.member_user_ids,
  }));
  if (backendState.platformSetupState) {
    backendState.platformSetupState = {
      ...backendState.platformSetupState,
      org_units: mapped,
    };
  } else if (mapped.length > 0) {
    backendState.platformSetupState = {
      org_units: mapped,
      rbac_grants: [],
      llm_tiers: [],
      workspaces: [],
      datasources: [],
      packs: [],
      workflows: [],
      runs: [],
      catalog_items: [],
      ontology_concepts: [],
      audit_events: [],
    };
  }
  syncVitestIamRolesWithOrgUnits(backendState.orgUnits);
}

export function countAttachedWorkspacesForUnit(unitId: string): {
  readonly count: number;
  readonly names: readonly string[];
} {
  const rawWs = backendState.platformSetupState?.workspaces;
  if (!Array.isArray(rawWs)) return { count: 0, names: [] };
  const matched = rawWs
    .map((w) => w as Record<string, unknown>)
    .filter((w) => String(w.ownerOrgUnitId ?? "") === unitId);
  return {
    count: matched.length,
    names: matched.map((w) => String(w.name ?? w.workspaceId ?? "")).filter(Boolean),
  };
}

export function getAllMockKnownOrgUsers() {
  const iamAccounts = getVitestIamAccounts()
    .filter((a) => a.account_kind === "HUMAN" && a.status !== "DISABLED")
    .map((a) => ({
      principal_id: a.principal_id,
      display_name: a.display_name,
      email: a.email,
    }));
  const byKey = new Map<string, { principal_id: string; display_name: string; email: string | null }>();
  for (const u of [...MOCK_KNOWN_ORG_USERS, ...iamAccounts]) {
    const k = u.principal_id.toLowerCase().trim();
    if (!byKey.has(k)) {
      byKey.set(k, u);
    }
  }
  return Array.from(byKey.values()).sort((a, b) => a.display_name.localeCompare(b.display_name));
}

export function isMockUserKnown(val: string): boolean {
  const needle = val.trim().toLowerCase();
  return getAllMockKnownOrgUsers().some(
    (u) =>
      u.principal_id.toLowerCase() === needle ||
      (u.email && u.email.toLowerCase() === needle),
  );
}

export function resolveMockOrgActor(reqHeaders: Headers) {
  const session = useAuthSessionStore.getState();
  const headerHat = reqHeaders.get("x-orcia-active-hat")?.trim().toUpperCase();
  const activeHat =
    headerHat ||
    (session.activeHat ? String(session.activeHat).toUpperCase() : "") ||
    (session.roles?.[0] ? String(session.roles[0]).toUpperCase() : "") ||
    "PLATFORM_ADMIN";
  const candidates = new Set<string>();
  if (session.email) candidates.add(session.email.toLowerCase());
  if (session.displayName) candidates.add(session.displayName.toLowerCase());
  const hasSessionUser = Boolean(
    session.email || session.activeHat || (session.roles && session.roles.length > 0),
  );
  return { activeHat, candidates, hasSessionUser };
}

export function computeOrgSubtreeAndAncestors(actorCandidates: Set<string>, activeHat: string) {
  const byId = new Map(backendState.orgUnits.map((u) => [u.id, u]));
  const isLead = (u: MockOrganizationalUnit) => {
    const leads = u.lead_user_ids ?? (u.lead_user_id ? [u.lead_user_id] : []);
    return leads.some((id) => actorCandidates.has(id.toLowerCase()));
  };
  const isOntologyLead = (u: MockOrganizationalUnit) =>
    (u.ontology_lead_user_ids ?? []).some((id) => actorCandidates.has(id.toLowerCase()));
  const isMember = (u: MockOrganizationalUnit) =>
    u.member_user_ids.some((id) => actorCandidates.has(id.toLowerCase()));

  const collectDescendants = (seeds: Set<string>) => {
    const result = new Set(seeds);
    let changed = true;
    while (changed) {
      changed = false;
      for (const u of backendState.orgUnits) {
        if (u.parent_id && result.has(u.parent_id) && !result.has(u.id)) {
          result.add(u.id);
          changed = true;
        }
      }
    }
    return result;
  };
  const collectAncestors = (seeds: Set<string>) => {
    const result = new Set<string>();
    for (const id of seeds) {
      let cur = byId.get(id)?.parent_id ?? null;
      const guard = new Set<string>([id]);
      while (cur && !guard.has(cur)) {
        guard.add(cur);
        result.add(cur);
        cur = byId.get(cur)?.parent_id ?? null;
      }
    }
    return result;
  };

  if (activeHat === "BU_LEAD" || activeHat === "BU_DIRECTOR") {
    const directBus = new Set(
      backendState.orgUnits.filter((u) => u.kind === "BU" && isLead(u)).map((u) => u.id),
    );
    const managed = collectDescendants(directBus);
    const rootLedBus = new Set(
      Array.from(directBus).filter((id) => {
        const p = byId.get(id)?.parent_id;
        return !p || !managed.has(p);
      }),
    );
    return { managed, rootLedBus, visible: new Set([...managed, ...collectAncestors(managed)]) };
  }
  if (activeHat === "TEAM_LEAD") {
    const managed = new Set(
      backendState.orgUnits.filter((u) => u.kind === "TEAM" && isLead(u)).map((u) => u.id),
    );
    return {
      managed,
      rootLedBus: new Set<string>(),
      visible: new Set([...managed, ...collectAncestors(managed)]),
    };
  }
  if (activeHat === "ONTOLOGY_LEAD") {
    const ledBus = new Set(
      backendState.orgUnits.filter((u) => u.kind === "BU" && isOntologyLead(u)).map((u) => u.id),
    );
    return {
      managed: new Set<string>(),
      rootLedBus: new Set<string>(),
      visible: new Set([...collectDescendants(ledBus), ...collectAncestors(ledBus)]),
    };
  }
  if (activeHat === "CONTRIBUTOR") {
    const teams = new Set(
      backendState.orgUnits.filter((u) => u.kind === "TEAM" && isMember(u)).map((u) => u.id),
    );
    return {
      managed: new Set<string>(),
      rootLedBus: new Set<string>(),
      visible: new Set([...teams, ...collectAncestors(teams)]),
    };
  }
  return {
    managed: new Set(backendState.orgUnits.map((u) => u.id)),
    rootLedBus: new Set<string>(),
    visible: new Set(backendState.orgUnits.map((u) => u.id)),
  };
}
