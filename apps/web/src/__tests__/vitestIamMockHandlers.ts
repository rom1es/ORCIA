export interface MockIamAccountItem {
  id: string;
  principal_id: string;
  display_name: string;
  email: string | null;
  account_kind: "HUMAN" | "SERVICE_PRINCIPAL";
  auth_source: "LOCAL_BOOTSTRAP" | "OIDC_FEDERATED" | "SERVICE_TOKEN";
  roles: string[];
  team_ids: string[];
  status: "ACTIVE" | "INVITED" | "DISABLED";
  created_at_iso: string;
  updated_at_iso: string;
}

export interface MockIamGrantItem {
  id: string;
  subject_type: "ROLE" | "USER" | "SERVICE_PRINCIPAL";
  subject_id: string;
  scope_path: string;
  verb: string;
  effect: "ALLOW" | "DENY" | "INHERITANCE_BLOCK";
  inheritance_block: boolean;
  resource_kind: string;
  conditions: Record<string, unknown>;
  hidden_when_unauthorized: boolean;
  granted_by_user_id: string;
  created_at_iso: string;
}

interface MockOrgUnitRef {
  id: string;
  slug: string;
  kind: "BU" | "TEAM";
  member_user_ids: string[];
}

const VALID_ROLES = new Set([
  "PLATFORM_ADMIN",
  "SECOPS",
  "BU_LEAD",
  "TEAM_LEAD",
  "CONTRIBUTOR",
  "OBSERVER",
]);

let iamAccounts: MockIamAccountItem[] = [];
let iamAccountSeq = 0;
let iamGrants: MockIamGrantItem[] = [];
let iamGrantSeq = 0;

export function resetVitestIamMockState(): void {
  iamAccounts = [];
  iamAccountSeq = 0;
  iamGrants = [];
  iamGrantSeq = 0;
}

export function getVitestIamAccounts(): readonly MockIamAccountItem[] {
  return iamAccounts;
}

function ensureDay0AdminSeeded(
  firstAdmin: { email: string; displayName: string } | null,
): void {
  const targetEmail = (firstAdmin?.email ?? "admin@orcia.local").trim().toLowerCase();
  const targetName =
    firstAdmin?.displayName?.trim() || "Administrateur Plateforme (Jour 0)";
  const already = iamAccounts.some((a) => a.principal_id.toLowerCase() === targetEmail);
  if (!already) {
    if (firstAdmin && targetEmail !== "admin@orcia.local") {
      iamAccounts = iamAccounts.filter((a) => a.principal_id !== "admin@orcia.local");
    }
    iamAccountSeq += 1;
    const nowIso = "2026-11-11T12:00:00Z";
    iamAccounts = [
      {
        id: `acc-${iamAccountSeq}`,
        principal_id: targetEmail,
        display_name: targetName,
        email: targetEmail,
        account_kind: "HUMAN",
        auth_source: "LOCAL_BOOTSTRAP",
        roles: ["PLATFORM_ADMIN", "SECOPS"],
        team_ids: [],
        status: "ACTIVE",
        created_at_iso: nowIso,
        updated_at_iso: nowIso,
      },
      ...iamAccounts,
    ];
  }
}

function syncTeamMemberships(
  principalId: string,
  desiredTeamIds: readonly string[],
  orgUnits: MockOrgUnitRef[],
  removeAll = false,
): void {
  const desired = removeAll ? new Set<string>() : new Set(desiredTeamIds);
  for (const unit of orgUnits) {
    if (unit.kind !== "TEAM") continue;
    const shouldHave = desired.has(unit.id) || desired.has(unit.slug);
    const has = unit.member_user_ids.includes(principalId);
    if (shouldHave && !has) {
      unit.member_user_ids = [...unit.member_user_ids, principalId];
    } else if (!shouldHave && has) {
      unit.member_user_ids = unit.member_user_ids.filter((m) => m !== principalId);
    }
  }
}

function countActivePlatformAdmins(list: readonly MockIamAccountItem[]): number {
  return list.filter(
    (a) => a.status === "ACTIVE" && a.roles.includes("PLATFORM_ADMIN"),
  ).length;
}

export function handleVitestIamRoute(params: {
  readonly method: string;
  readonly path: string;
  readonly parsedUrl: URL;
  readonly body: Record<string, unknown>;
  readonly reqHeaders: Headers;
  readonly firstAdmin: { email: string; displayName: string } | null;
  readonly orgUnits: MockOrgUnitRef[];
  readonly syncSetupOrgUnits: () => void;
  readonly jsonResponse: (payload: unknown, status?: number) => Response;
  readonly problemResponse: (
    status: number,
    errorCode: string,
    title: string,
    detail: string,
    instance: string,
  ) => Response;
}): Response | null {
  const {
    method,
    path,
    parsedUrl,
    body,
    reqHeaders,
    firstAdmin,
    orgUnits,
    syncSetupOrgUnits,
    jsonResponse,
    problemResponse,
  } = params;

  const isObserver = (): boolean => {
    const mode = (reqHeaders.get("x-orcia-access-mode") ?? "").toUpperCase();
    const hat = (reqHeaders.get("x-orcia-active-hat") ?? "PLATFORM_ADMIN").toUpperCase();
    return mode === "READ_ONLY_OBSERVER" || hat === "OBSERVER";
  };

  if (path === "/api/v1/settings/iam/role-matrix" && method === "GET") {
    return jsonResponse({
      secret_visibility: "WRITE_ONLY_NEVER_READABLE", // pragma: allowlist secret
      roles: [
        { role: "PLATFORM_ADMIN", natural_scope: "GLOBAL", verbs: ["create", "read", "update", "delete", "execute", "grant"], summary_key: "platform_admin" },
        { role: "SECOPS", natural_scope: "GLOBAL", verbs: ["read", "update", "grant"], summary_key: "secops" },
        { role: "BU_LEAD", natural_scope: "BU", verbs: ["create", "read", "update", "execute", "grant"], summary_key: "bu_lead" },
        { role: "TEAM_LEAD", natural_scope: "TEAM", verbs: ["create", "read", "update", "execute", "grant"], summary_key: "team_lead" },
        { role: "CONTRIBUTOR", natural_scope: "WORKSPACE", verbs: ["create", "read", "update", "execute"], summary_key: "contributor" },
        { role: "OBSERVER", natural_scope: "WORKSPACE", verbs: ["read"], summary_key: "observer" },
      ],
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/settings/iam/accounts" && method === "GET") {
    ensureDay0AdminSeeded(firstAdmin);
    return jsonResponse({
      accounts: iamAccounts,
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/settings/iam/accounts" && method === "POST") {
    if (isObserver()) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    ensureDay0AdminSeeded(firstAdmin);
    const rawRoles = Array.isArray(body.roles) ? body.roles.map(String) : [];
    if (rawRoles.length === 0 || rawRoles.some((r) => !VALID_ROLES.has(r))) {
      return problemResponse(
        422,
        "ERR_IAM_INVALID_ROLE",
        "Rôle IAM non officiel",
        "Le rôle demandé n'appartient pas aux 6 rôles officiels de la plateforme.",
        path,
      );
    }
    const kind =
      String(body.account_kind ?? "HUMAN") === "SERVICE_PRINCIPAL"
        ? "SERVICE_PRINCIPAL"
        : "HUMAN";
    const displayName = String(body.display_name ?? "").trim();
    const email =
      typeof body.email === "string" && body.email.trim()
        ? body.email.trim().toLowerCase()
        : null;
    const principalId = String(body.principal_id ?? email ?? displayName)
      .trim()
      .toLowerCase();
    if (iamAccounts.some((a) => a.principal_id.toLowerCase() === principalId)) {
      return problemResponse(
        409,
        "ERR_IAM_DUPLICATE_PRINCIPAL",
        "Compte déjà enregistré",
        "Un compte portant cet identifiant ou e-mail existe déjà dans l'annuaire.",
        path,
      );
    }
    const teamIds = Array.isArray(body.team_ids) ? body.team_ids.map(String) : [];
    const status = (body.status as MockIamAccountItem["status"]) ?? "ACTIVE";
    iamAccountSeq += 1;
    const nowIso = "2026-11-11T12:05:00Z";
    const created: MockIamAccountItem = {
      id: `acc-${iamAccountSeq}`,
      principal_id: principalId,
      display_name: displayName,
      email,
      account_kind: kind,
      auth_source: kind === "SERVICE_PRINCIPAL" ? "SERVICE_TOKEN" : "OIDC_FEDERATED",
      roles: rawRoles,
      team_ids: teamIds,
      status,
      created_at_iso: nowIso,
      updated_at_iso: nowIso,
    };
    iamAccounts = [...iamAccounts, created];
    syncTeamMemberships(principalId, teamIds, orgUnits);
    syncSetupOrgUnits();
    const tempPassword = kind === "HUMAN" ? "OrciaPass123" : null; // pragma: allowlist secret
    return jsonResponse(
      { ...created, account: created, temporary_password: tempPassword },
      201,
    );
  }

  const tempPwdMatch =
    /^\/api\/v1\/settings\/iam\/accounts\/([^/]+)\/temporary-password$/.exec(path);
  if (tempPwdMatch && method === "POST") {
    if (isObserver()) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    const targetId = decodeURIComponent(tempPwdMatch[1] ?? "");
    const target = iamAccounts.find((a) => a.id === targetId);
    if (!target) {
      return problemResponse(
        404,
        "ERR_RESOURCE_NOT_FOUND",
        "Compte introuvable",
        "Compte introuvable.",
        path,
      );
    }
    return jsonResponse({
      account_id: target.id,
      temporary_password: "RegenPass123", // pragma: allowlist secret
      must_change_password: true,
      expires_at_iso: "2026-11-15T12:00:00Z",
    });
  }

  const accMatch = /^\/api\/v1\/settings\/iam\/accounts\/([^/]+)$/.exec(path);
  if (accMatch && (method === "PATCH" || method === "DELETE")) {
    if (isObserver()) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    ensureDay0AdminSeeded(firstAdmin);
    const targetId = decodeURIComponent(accMatch[1] ?? "");
    const target = iamAccounts.find((a) => a.id === targetId);
    if (!target) {
      return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Compte introuvable", "Compte introuvable.", path);
    }
    if (method === "PATCH") {
      let nextRoles = target.roles;
      if (Array.isArray(body.roles)) {
        nextRoles = body.roles.map(String);
        if (nextRoles.length === 0 || nextRoles.some((r) => !VALID_ROLES.has(r))) {
          return problemResponse(
            422,
            "ERR_IAM_INVALID_ROLE",
            "Rôle IAM non officiel",
            "Le rôle demandé n'appartient pas aux 6 rôles officiels de la plateforme.",
            path,
          );
        }
      }
      const nextStatus =
        typeof body.status === "string"
          ? (body.status as MockIamAccountItem["status"])
          : target.status;
      const nextTeams = Array.isArray(body.team_ids)
        ? body.team_ids.map(String)
        : target.team_ids;
      const updated: MockIamAccountItem = {
        ...target,
        display_name:
          typeof body.display_name === "string" && body.display_name.trim()
            ? body.display_name.trim()
            : target.display_name,
        email: "email" in body ? (body.email ? String(body.email).trim().toLowerCase() : null) : target.email,
        roles: nextRoles,
        team_ids: nextTeams,
        status: nextStatus,
        updated_at_iso: "2026-11-11T12:10:00Z",
      };
      const candidateList = iamAccounts.map((a) => (a.id === target.id ? updated : a));
      if (countActivePlatformAdmins(candidateList) < 1) {
        return problemResponse(
          422,
          "ERR_ADMIN_LOCKOUT_PREVENTED",
          "Protection anti-verrouillage administrateur",
          "Impossible de retirer ou désactiver le dernier Administrateur Plateforme actif.",
          path,
        );
      }
      iamAccounts = candidateList;
      syncTeamMemberships(updated.principal_id, nextTeams, orgUnits);
      syncSetupOrgUnits();
      return jsonResponse(updated);
    }

    const remaining = iamAccounts.filter((a) => a.id !== target.id);
    if (countActivePlatformAdmins(remaining) < 1) {
      return problemResponse(
        422,
        "ERR_ADMIN_LOCKOUT_PREVENTED",
        "Protection anti-verrouillage administrateur",
        "Impossible de supprimer le dernier Administrateur Plateforme actif.",
        path,
      );
    }
    iamAccounts = remaining;
    syncTeamMemberships(target.principal_id, [], orgUnits, true);
    syncSetupOrgUnits();
    return jsonResponse({
      deleted_id: target.id,
      deleted: true,
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/settings/iam/grants" && method === "GET") {
    return jsonResponse(iamGrants);
  }

  if (path === "/api/v1/settings/iam/grants" && method === "POST") {
    if (isObserver()) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    const actorPersona = String(body.actor_persona ?? "marc");
    if (actorPersona !== "karim") {
      return problemResponse(
        403,
        "ERR_SCOPE_ACCESS_DENIED",
        "Gouvernance SecOps requise",
        "Seul le rôle Responsable Sécurité (SecOps) peut créer des exceptions d'accès.",
        path,
      );
    }
    const verbs = Array.isArray(body.verbs) ? body.verbs.map(String) : ["read"];
    const effect = (body.effect as MockIamGrantItem["effect"]) ?? "ALLOW";
    const created: MockIamGrantItem[] = verbs.map((verb) => {
      iamGrantSeq += 1;
      return {
        id: `grant-${iamGrantSeq}`,
        subject_type:
          (body.subject_type as MockIamGrantItem["subject_type"]) ?? "ROLE",
        subject_id: String(body.subject_id ?? "TEAM_LEAD"),
        scope_path: String(body.scope_path ?? "GLOBAL"),
        verb,
        effect,
        inheritance_block: Boolean(body.inheritance_block) || effect === "INHERITANCE_BLOCK",
        resource_kind: String(body.resource_kind ?? "ALL"),
        conditions: {},
        hidden_when_unauthorized: true,
        granted_by_user_id: "karim",
        created_at_iso: "2026-11-11T12:15:00Z",
      };
    });
    iamGrants = [...iamGrants, ...created];
    return jsonResponse(created);
  }

  const grantMatch = /^\/api\/v1\/settings\/iam\/grants\/([^/]+)$/.exec(path);
  if (grantMatch && method === "DELETE") {
    if (isObserver()) {
      return problemResponse(
        403,
        "ERR_OBSERVER_MODE_READ_ONLY",
        "Mode observateur en lecture seule",
        "Les mutations sont refusées en mode observateur lecture seule.",
        path,
      );
    }
    const actorPersona = parsedUrl.searchParams.get("actor_persona") ?? "karim";
    if (actorPersona !== "karim") {
      return problemResponse(
        403,
        "ERR_SCOPE_ACCESS_DENIED",
        "Gouvernance SecOps requise",
        "Seul le rôle Responsable Sécurité (SecOps) peut supprimer des exceptions.",
        path,
      );
    }
    const targetId = decodeURIComponent(grantMatch[1] ?? "");
    iamGrants = iamGrants.filter((g) => g.id !== targetId);
    return jsonResponse({
      deleted_id: targetId,
      deleted: true,
      trace_id: "0195f000000070008000000000000999",
    });
  }

  return null;
}
