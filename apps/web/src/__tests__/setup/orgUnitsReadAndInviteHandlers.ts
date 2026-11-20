import { upsertVitestIamOrgInvitedUser } from "../vitestIamMockHandlers";
import type { MockOrganizationalUnit } from "./mockBackendState";
import { backendState, jsonResponse, problemResponse } from "./mockBackendState";
import {
  computeOrgSubtreeAndAncestors,
  countAttachedWorkspacesForUnit,
  getAllMockKnownOrgUsers,
  resolveMockOrgActor,
  syncSetupOrgUnitsFromMock,
} from "./orgUnitsScopeHelpers";

export function handleOrgUnitsReadAndInviteRoute(params: {
  path: string;
  method: string;
  parsedUrl: URL;
  body: Record<string, unknown>;
  reqHeaders: Headers;
}): Response | null {
  const { path, method, parsedUrl, body, reqHeaders } = params;

  if (path === "/api/v1/org-units/known-users" && method === "GET") {
    const qParam = parsedUrl.searchParams.get("q")?.trim()?.toLowerCase() ?? null;
    const limitParamRaw = parsedUrl.searchParams.get("limit");
    const limit = limitParamRaw ? parseInt(limitParamRaw, 10) : 10;
    let users = getAllMockKnownOrgUsers();
    if (qParam) {
      users = users.filter(
        (u) =>
          u.display_name.toLowerCase().includes(qParam) ||
          u.principal_id.toLowerCase().includes(qParam) ||
          (u.email && u.email.toLowerCase().includes(qParam)),
      );
    }
    return jsonResponse({ items: users.slice(0, limit), has_more: users.length > limit });
  }

  if (path === "/api/v1/org-units" && method === "GET") {
    const qParam = parsedUrl.searchParams.get("q")?.trim()?.toLowerCase() ?? null;
    const kindParam = parsedUrl.searchParams.get("kind")?.toUpperCase() ?? null;
    const limitParamRaw = parsedUrl.searchParams.get("limit");
    const limitParam = limitParamRaw ? parseInt(limitParamRaw, 10) : null;
    const { activeHat, candidates, hasSessionUser } = resolveMockOrgActor(reqHeaders);
    const scopeInfo = hasSessionUser ? computeOrgSubtreeAndAncestors(candidates, activeHat) : null;

    let units = backendState.orgUnits
      .map((u) => {
        const isBu = u.kind === "BU";
        let canEdit = true;
        let canCreateChild = isBu;
        let canDelete = true;
        let canManageMembers = !isBu;
        let canManageOntologyLeads = isBu;
        let canInviteUsers = true;
        if (hasSessionUser) {
          if (activeHat === "PLATFORM_ADMIN") {
            // full access
          } else if ((activeHat === "BU_LEAD" || activeHat === "BU_DIRECTOR") && scopeInfo) {
            const inManaged = scopeInfo.managed.has(u.id);
            canEdit = inManaged;
            canCreateChild = inManaged && isBu;
            canDelete = inManaged && !scopeInfo.rootLedBus.has(u.id);
            canManageMembers = inManaged && !isBu;
            canManageOntologyLeads = inManaged && isBu;
            canInviteUsers = inManaged;
          } else if (activeHat === "TEAM_LEAD" && scopeInfo) {
            const inManaged = scopeInfo.managed.has(u.id);
            canEdit = inManaged;
            canCreateChild = false;
            canDelete = false;
            canManageMembers = inManaged && !isBu;
            canManageOntologyLeads = false;
            canInviteUsers = false;
          } else {
            canEdit = false;
            canCreateChild = false;
            canDelete = false;
            canManageMembers = false;
            canManageOntologyLeads = false;
            canInviteUsers = false;
          }
        }
        return {
          ...u,
          lead_user_id: u.lead_user_id ?? (u.lead_user_ids?.[0] ?? null),
          lead_user_ids: u.lead_user_ids ?? (u.lead_user_id ? [u.lead_user_id] : []),
          ontology_lead_user_ids: isBu ? (u.ontology_lead_user_ids ?? []) : [],
          attached_workspaces_count: countAttachedWorkspacesForUnit(u.id).count,
          can_edit: u.can_edit ?? canEdit,
          can_create_child: u.can_create_child ?? canCreateChild,
          can_delete: u.can_delete ?? canDelete,
          can_manage_members: u.can_manage_members ?? canManageMembers,
          can_manage_ontology_leads: u.can_manage_ontology_leads ?? canManageOntologyLeads,
          can_invite_users: u.can_invite_users ?? canInviteUsers,
        };
      });

    if (kindParam) {
      units = units.filter((u) => ((u as unknown as { level?: string }).level || u.kind) === kindParam);
    }
    if (qParam) {
      units = units.filter(
        (u) => u.name.toLowerCase().includes(qParam) || (u.slug ? u.slug.toLowerCase().includes(qParam) : false),
      );
    }
    if (limitParam && limitParam > 0) units = units.slice(0, limitParam);

    return jsonResponse({
      org_units: units,
      known_users: getAllMockKnownOrgUsers(),
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/org-units/invite-user" && method === "POST") {
    const accessMode = (reqHeaders.get("x-orcia-access-mode") ?? "").toUpperCase();
    const { activeHat, candidates, hasSessionUser } = resolveMockOrgActor(reqHeaders);
    if (accessMode === "READ_ONLY_OBSERVER" || activeHat === "OBSERVER") {
      return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Mode observateur en lecture seule", "Les mutations sont refusées en mode observateur lecture seule.", path);
    }
    if (!["PLATFORM_ADMIN", "BU_LEAD", "BU_DIRECTOR"].includes(activeHat)) {
      return problemResponse(403, "ERR_SCOPE_ACCESS_DENIED", "Accès au périmètre refusé", "Seul un Administrateur Plateforme ou un Responsable de BU peut inviter dans son périmètre.", path);
    }
    const requestedRole = String(body.assignment_role ?? body.role ?? "").trim().toUpperCase();
    if (requestedRole === "PLATFORM_ADMIN" || requestedRole === "SECOPS") {
      return problemResponse(403, "ERR_PRIVILEGE_ESCALATION_FORBIDDEN", "Escalade de privilèges interdite", "L'attribution de PLATFORM_ADMIN ou SECOPS est interdite depuis Mon Organisation.", path);
    }
    const targetUnitId = String(body.target_org_unit_id ?? "").trim();
    const ROOT_ENTERPRISE_ID = "0192c4e0-0000-7000-8000-000000000001";
    const foundUnit = backendState.orgUnits.find((u) => u.id === targetUnitId);
    const targetUnit: MockOrganizationalUnit | undefined =
      foundUnit ??
      (targetUnitId === ROOT_ENTERPRISE_ID && activeHat === "PLATFORM_ADMIN"
        ? {
            id: ROOT_ENTERPRISE_ID,
            slug: "orcia-root",
            name: "Plateforme Globale ORCIA",
            kind: "TEAM",
            parent_id: null,
            billing_enabled: true,
            lead_user_id: null,
            lead_user_ids: [],
            ontology_lead_user_ids: [],
            member_user_ids: [],
          }
        : undefined);
    if (!targetUnit) {
      return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Unité introuvable", `Unité organisationnelle introuvable : '${targetUnitId}'.`, path);
    }
    if (hasSessionUser && (activeHat === "BU_LEAD" || activeHat === "BU_DIRECTOR")) {
      const scopeInfo = computeOrgSubtreeAndAncestors(candidates, activeHat);
      if (!scopeInfo.managed.has(targetUnit.id)) {
        return problemResponse(403, "ERR_SCOPE_ACCESS_DENIED", "Hors périmètre de délégation", "Cette unité n'appartient pas à votre périmètre BU.", path);
      }
    }
    const email = String(body.email ?? "").trim().toLowerCase();
    const displayName = String(body.display_name ?? email).trim();
    const account = upsertVitestIamOrgInvitedUser({
      email,
      displayName,
      role: requestedRole,
      targetUnitId: targetUnit.id,
      targetUnitKind: targetUnit.kind,
    });
    if (requestedRole === "TEAM_MEMBER" || requestedRole === "CONTRIBUTOR") {
      if (!targetUnit.member_user_ids.includes(email)) targetUnit.member_user_ids = [...targetUnit.member_user_ids, email];
    } else if (requestedRole === "TEAM_LEAD" || requestedRole === "BU_LEAD") {
      const leads = targetUnit.lead_user_ids ?? (targetUnit.lead_user_id ? [targetUnit.lead_user_id] : []);
      if (!leads.includes(email)) {
        targetUnit.lead_user_ids = [...leads, email];
        targetUnit.lead_user_id = targetUnit.lead_user_ids[0] ?? null;
      }
    } else if (requestedRole === "ONTOLOGY_LEAD") {
      const ontoLeads = targetUnit.ontology_lead_user_ids ?? [];
      if (!ontoLeads.includes(email)) targetUnit.ontology_lead_user_ids = [...ontoLeads, email];
    }
    syncSetupOrgUnitsFromMock();
    return jsonResponse({
      account_id: account.id,
      user_id: account.id,
      principal_id: account.principal_id,
      email: account.email ?? email,
      display_name: account.display_name,
      assignment_role: requestedRole,
      role: requestedRole,
      target_org_unit_id: targetUnit.id,
      temporary_password: "OrciaMock!2026", // pragma: allowlist secret
      auth_mode: "LOCAL",
      org_unit: {
        ...targetUnit,
        lead_user_id: targetUnit.lead_user_id ?? (targetUnit.lead_user_ids?.[0] ?? null),
        lead_user_ids: targetUnit.lead_user_ids ?? (targetUnit.lead_user_id ? [targetUnit.lead_user_id] : []),
        ontology_lead_user_ids: targetUnit.kind === "BU" ? (targetUnit.ontology_lead_user_ids ?? []) : [],
        attached_workspaces_count: countAttachedWorkspacesForUnit(targetUnit.id).count,
        can_edit: true,
        can_create_child: targetUnit.kind === "BU",
        can_delete: activeHat === "PLATFORM_ADMIN",
        can_manage_members: targetUnit.kind === "TEAM",
        can_manage_ontology_leads: targetUnit.kind === "BU",
        can_invite_users: true,
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  return null;
}
