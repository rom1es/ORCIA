import type { MockOrganizationalUnit } from "./mockBackendState";
import { backendState, jsonResponse, problemResponse } from "./mockBackendState";
import {
  computeOrgSubtreeAndAncestors,
  countAttachedWorkspacesForUnit,
  isMockUserKnown,
  resolveMockOrgActor,
  syncSetupOrgUnitsFromMock,
} from "./orgUnitsScopeHelpers";

function unknownUserErr(userId: string, path: string): Response {
  return problemResponse(
    422,
    "ERR_ORG_UNIT_UNKNOWN_USER",
    "Utilisateur inconnu",
    `L'utilisateur '${userId}' n'est pas un compte connu et actif de la plateforme.`,
    path,
  );
}

function handleCreateOrgUnit(body: Record<string, unknown>, path: string): Response {
  const name = String(body.name ?? "").trim();
  const kind: "BU" | "TEAM" = String(body.kind ?? "BU").toUpperCase() === "TEAM" ? "TEAM" : "BU";
  const rawSlug = typeof body.slug === "string" ? body.slug.trim().toLowerCase() : "";
  const slug = (rawSlug || name.toLowerCase()).replace(/[^a-z0-9-]+/g, "-").replace(/^-|-$/g, "");
  if (backendState.orgUnits.some((u) => u.slug === slug)) {
    return problemResponse(409, "ERR_ORG_UNIT_DUPLICATE_SLUG", "Identifiant court d'unité déjà utilisé", `L'identifiant court '${slug}' est déjà utilisé.`, path);
  }
  const rawParent =
    typeof body.parent_id === "string" && body.parent_id.trim() && body.parent_id.trim() !== "scope-global"
      ? body.parent_id.trim()
      : null;
  if (rawParent) {
    const parentUnit = backendState.orgUnits.find((u) => u.id === rawParent);
    if (!parentUnit) {
      return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Ressource introuvable", `Unité parente introuvable : '${rawParent}'.`, path);
    }
    if (kind === "BU" && parentUnit.kind === "TEAM") {
      return problemResponse(422, "ERR_ORG_UNIT_INVALID_PARENT_KIND", "Rattachement hiérarchique invalide", "Une Direction ou un Pôle (BU) ne peut pas être rattaché sous une Équipe.", path);
    }
  }
  const rawMembers = Array.isArray(body.member_user_ids)
    ? body.member_user_ids.map((m) => String(m).trim()).filter(Boolean)
    : [];
  if (kind === "BU" && rawMembers.length > 0) {
    return problemResponse(422, "ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN", "Membres interdits sur une Direction (BU)", "Une Direction (BU) ou un Pôle (Sous-BU) ne peut pas comporter de membres directs. Les membres doivent être rattachés à une Équipe.", path);
  }
  for (const m of rawMembers) if (!isMockUserKnown(m)) return unknownUserErr(m, path);

  const rawLead = typeof body.lead_user_id === "string" && body.lead_user_id.trim() ? body.lead_user_id.trim() : null;
  const rawLeadIds = Array.isArray(body.lead_user_ids)
    ? body.lead_user_ids.map((l) => String(l).trim()).filter(Boolean)
    : rawLead ? [rawLead] : [];
  for (const l of rawLeadIds) if (!isMockUserKnown(l)) return unknownUserErr(l, path);

  const rawOntologyLeads = Array.isArray(body.ontology_lead_user_ids)
    ? body.ontology_lead_user_ids.map((l) => String(l).trim()).filter(Boolean)
    : [];
  if (kind === "TEAM" && rawOntologyLeads.length > 0) {
    return problemResponse(422, "ERR_ORG_UNIT_ONTOLOGY_LEAD_ONLY_BU", "Référents Glossaire réservés aux Directions (BU)", "Seule une Direction ou Sous-BU (BU) peut désigner des Référents Glossaire.", path);
  }

  backendState.orgUnitSeq += 1;
  const id = `org-${backendState.orgUnitSeq}`;
  const created: MockOrganizationalUnit = {
    id,
    slug,
    name,
    kind,
    parent_id: rawParent,
    billing_enabled: body.billing_enabled !== undefined ? Boolean(body.billing_enabled) : true,
    lead_user_id: rawLeadIds[0] ?? null,
    lead_user_ids: rawLeadIds,
    ontology_lead_user_ids: kind === "BU" ? rawOntologyLeads : [],
    member_user_ids: kind === "BU" ? [] : rawMembers,
  };
  backendState.orgUnits = [...backendState.orgUnits, created];
  syncSetupOrgUnitsFromMock();
  return jsonResponse({
    ...created,
    attached_workspaces_count: 0,
    can_edit: true,
    can_create_child: created.kind === "BU",
    can_delete: true,
    can_manage_members: created.kind === "TEAM",
    can_manage_ontology_leads: created.kind === "BU",
    can_invite_users: true,
  });
}

function handlePatchOrgUnit(
  target: MockOrganizationalUnit,
  body: Record<string, unknown>,
  reqHeaders: Headers,
  path: string,
): Response {
  const nextName = typeof body.name === "string" && body.name.trim() ? body.name.trim() : target.name;
  let nextParentId = target.parent_id;
  if ("parent_id" in body) {
    const candidate =
      typeof body.parent_id === "string" && body.parent_id.trim() && body.parent_id.trim() !== "scope-global"
        ? body.parent_id.trim()
        : null;
    if (candidate === target.id) {
      return problemResponse(422, "ERR_ORG_UNIT_HIERARCHY_CYCLE", "Cycle hiérarchique détecté", "Une unité ne peut pas être rattachée à elle-même ou à l'une de ses sous-unités.", path);
    }
    if (candidate) {
      const parentUnit = backendState.orgUnits.find((u) => u.id === candidate);
      if (!parentUnit) {
        return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Ressource introuvable", `Unité parente introuvable : '${candidate}'.`, path);
      }
      if (target.kind === "BU" && parentUnit.kind === "TEAM") {
        return problemResponse(422, "ERR_ORG_UNIT_INVALID_PARENT_KIND", "Rattachement hiérarchique invalide", "Une Direction ou un Pôle (BU) ne peut pas être rattaché sous une Équipe.", path);
      }
      let cursor: MockOrganizationalUnit | undefined = parentUnit;
      const seen = new Set<string>([target.id]);
      while (cursor) {
        if (seen.has(cursor.id)) {
          return problemResponse(422, "ERR_ORG_UNIT_HIERARCHY_CYCLE", "Cycle hiérarchique détecté", "Une unité ne peut pas être rattachée à elle-même ou à l'une de ses sous-unités.", path);
        }
        seen.add(cursor.id);
        cursor = cursor.parent_id ? backendState.orgUnits.find((u) => u.id === cursor?.parent_id) : undefined;
      }
    }
    nextParentId = candidate;
  }

  let nextLeadUserId = target.lead_user_id;
  let nextLeadUserIds = target.lead_user_ids ?? (target.lead_user_id ? [target.lead_user_id] : []);
  if ("lead_user_ids" in body && Array.isArray(body.lead_user_ids)) {
    const rawLeads = body.lead_user_ids.map((l) => String(l).trim()).filter(Boolean);
    for (const l of rawLeads) if (!isMockUserKnown(l)) return unknownUserErr(l, path);
    nextLeadUserIds = rawLeads;
    nextLeadUserId = rawLeads[0] ?? null;
  } else if ("lead_user_id" in body) {
    const rawLead = typeof body.lead_user_id === "string" && body.lead_user_id.trim() ? body.lead_user_id.trim() : null;
    if (rawLead && !isMockUserKnown(rawLead)) return unknownUserErr(rawLead, path);
    nextLeadUserId = rawLead;
    nextLeadUserIds = rawLead ? [rawLead] : [];
  }

  let nextMemberUserIds = target.kind === "BU" ? [] : target.member_user_ids;
  if ("member_user_ids" in body && Array.isArray(body.member_user_ids)) {
    const rawMembers = body.member_user_ids.map((m) => String(m).trim()).filter(Boolean);
    if (target.kind === "BU" && rawMembers.length > 0) {
      return problemResponse(422, "ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN", "Membres interdits sur une Direction (BU)", "Une Direction (BU) ou un Pôle (Sous-BU) ne peut pas comporter de membres directs. Les membres doivent être rattachés à une Équipe.", path);
    }
    for (const m of rawMembers) if (!isMockUserKnown(m)) return unknownUserErr(m, path);
    nextMemberUserIds = rawMembers;
  }

  let nextOntologyLeadUserIds = target.kind === "BU" ? (target.ontology_lead_user_ids ?? []) : [];
  if ("ontology_lead_user_ids" in body && Array.isArray(body.ontology_lead_user_ids)) {
    const rawOnto = body.ontology_lead_user_ids.map((l) => String(l).trim()).filter(Boolean);
    if (target.kind === "TEAM" && rawOnto.length > 0) {
      return problemResponse(422, "ERR_ORG_UNIT_ONTOLOGY_LEAD_ONLY_BU", "Référents Glossaire réservés aux Directions (BU)", "Seule une Direction ou Sous-BU (BU) peut désigner des Référents Glossaire.", path);
    }
    nextOntologyLeadUserIds = target.kind === "BU" ? rawOnto : [];
  }

  const { activeHat: patchHat, candidates: patchCandidates, hasSessionUser: patchHasUser } = resolveMockOrgActor(reqHeaders);
  if (patchHasUser && (patchHat === "BU_LEAD" || patchHat === "BU_DIRECTOR" || patchHat === "TEAM_LEAD")) {
    const patchScope = computeOrgSubtreeAndAncestors(patchCandidates, patchHat);
    if (!patchScope.managed.has(target.id)) {
      return problemResponse(403, "ERR_SCOPE_ACCESS_DENIED", "Hors périmètre de délégation", "Cette unité n'appartient pas à votre périmètre de délégation.", path);
    }
    if (nextLeadUserIds.length === 0) {
      return problemResponse(422, "ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN", "Dernier responsable requis", "Impossible de retirer le dernier responsable de cette unité.", path);
    }
  }

  const updated: MockOrganizationalUnit = {
    ...target,
    name: nextName,
    parent_id: nextParentId,
    billing_enabled: body.billing_enabled !== undefined ? Boolean(body.billing_enabled) : target.billing_enabled,
    lead_user_id: nextLeadUserId,
    lead_user_ids: nextLeadUserIds,
    ontology_lead_user_ids: target.kind === "BU" ? nextOntologyLeadUserIds : [],
    member_user_ids: target.kind === "BU" ? [] : nextMemberUserIds,
  };
  backendState.orgUnits = backendState.orgUnits.map((u) => (u.id === target.id ? updated : u));
  syncSetupOrgUnitsFromMock();
  return jsonResponse({
    ...updated,
    attached_workspaces_count: countAttachedWorkspacesForUnit(updated.id).count,
  });
}

export function handleOrgUnitsMutationsRoute(params: {
  path: string;
  method: string;
  body: Record<string, unknown>;
  reqHeaders: Headers;
}): Response | null {
  const { path, method, body, reqHeaders } = params;
  const isCreate = path === "/api/v1/org-units" && method === "POST";
  const orgIdMatch = /^\/api\/v1\/org-units\/([^/]+)$/.exec(path);
  const isItemMutation = Boolean(orgIdMatch) && (method === "PATCH" || method === "DELETE");
  if (!isCreate && !isItemMutation) return null;

  const accessMode = (reqHeaders.get("x-orcia-access-mode") ?? "").toUpperCase();
  const activeHat = (reqHeaders.get("x-orcia-active-hat") ?? "PLATFORM_ADMIN").toUpperCase();
  if (accessMode === "READ_ONLY_OBSERVER" || activeHat === "OBSERVER") {
    return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Mode observateur en lecture seule", "Les mutations sont refusées en mode observateur lecture seule.", path);
  }
  if (!["PLATFORM_ADMIN", "SECOPS", "BU_LEAD", "TEAM_LEAD"].includes(activeHat)) {
    return problemResponse(403, "ERR_SCOPE_ACCESS_DENIED", "Accès au périmètre refusé", "Votre rôle ne permet pas de modifier l'organigramme.", path);
  }
  if (isCreate) return handleCreateOrgUnit(body, path);

  const targetId = decodeURIComponent(orgIdMatch?.[1] ?? "");
  const target = backendState.orgUnits.find((u) => u.id === targetId);
  if (!target) {
    return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Ressource introuvable", `Unité introuvable : '${targetId}'.`, path);
  }
  if (method === "PATCH") return handlePatchOrgUnit(target, body, reqHeaders, path);

  const children = backendState.orgUnits.filter((u) => u.parent_id === target.id);
  const wsInfo = countAttachedWorkspacesForUnit(target.id);
  if (children.length > 0 || wsInfo.count > 0) {
    const parts: string[] = [];
    if (children.length > 0) parts.push(children.length > 1 ? `${children.length} sous-unités sont rattachées` : "1 sous-unité est rattachée");
    if (wsInfo.count > 0) parts.push(wsInfo.count > 1 ? `${wsInfo.count} Espaces de Travail sont rattachés` : "1 Espace de Travail est rattaché");
    return problemResponse(409, "ERR_ORG_UNIT_NOT_EMPTY", "Unité organisationnelle non vide", `Suppression refusée : ${parts.join(" et ")} à « ${target.name} ». Supprimez ou déplacez d'abord ces éléments.`, path);
  }
  backendState.orgUnits = backendState.orgUnits.filter((u) => u.id !== target.id);
  syncSetupOrgUnitsFromMock();
  return jsonResponse({ deleted_id: target.id, deleted: true, trace_id: "0195f000000070008000000000000999" });
}
