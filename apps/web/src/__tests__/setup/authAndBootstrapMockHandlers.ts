import { useAuthSessionStore } from "../../stores/authSessionStore";
import { evaluateVitestLocalLoginPolicy, getVitestBootEpoch } from "../vitestAuthPolicyMockHandlers";
import { getVitestIamAccounts } from "../vitestIamMockHandlers";
import { backendState, jsonResponse, problemResponse } from "./mockBackendState";
import { hydrateMockOrgUnitsFromSetup } from "./orgUnitsScopeHelpers";

export function handleAuthAndBootstrapRoute(params: {
  path: string;
  method: string;
  body: Record<string, unknown>;
}): Response | null {
  const { path, method, body } = params;

  if (path === "/api/v1/bootstrap/accostage-status" && method === "GET") {
    const setupState = backendState.platformSetupState as Record<string, unknown> | null;
    const rawOrgUnits = Array.isArray(setupState?.org_units) ? setupState.org_units : backendState.orgUnits;
    const realOrgUnitsCount = rawOrgUnits.filter((u) => {
      const rec = u as Record<string, unknown>;
      const lvl = String(rec.level ?? rec.kind ?? "BU").toUpperCase();
      return lvl === "BU" || lvl === "TEAM";
    }).length;
    const workspacesCount = Array.isArray(setupState?.workspaces)
      ? setupState.workspaces.length
      : backendState.workspaces.length;
    const modelsCount = Array.isArray(setupState?.llm_tiers)
      ? setupState.llm_tiers.length
      : backendState.aiModelMappings.length;
    const sourcesCount = Array.isArray(setupState?.datasources) ? setupState.datasources.length : 0;
    const adminCreated = Boolean(backendState.firstAdmin);
    if (backendState.firstAdmin) {
      return jsonResponse({
        completed_count: Math.min(6, 1 + (modelsCount > 0 ? 1 : 0) + (workspacesCount > 0 ? 1 : 0)),
        total_count: 6,
        badge_label: "Accostage",
        llm_tier_mode: modelsCount >= 2 ? "FULL_ORTHOGONAL_AD10" : modelsCount === 1 ? "QUICK_TRIAL_SINGLE_FAMILY" : "UNCONFIGURED",
        distinct_families: [],
        assistant_trial_enabled: modelsCount >= 1,
        agentic_gates_ad10_enabled: modelsCount >= 2,
        amber_warning_badge: null,
        completed_milestone_keys: [],
        first_admin_initialized: true,
        first_admin_email: backendState.firstAdmin.email,
        first_admin_display_name: backendState.firstAdmin.displayName,
        admin_created: adminCreated,
        users_count: 1,
        org_units_count: realOrgUnitsCount,
        workspaces_count: workspacesCount,
        models_count: modelsCount,
        sources_count: sourcesCount,
        boot_epoch: getVitestBootEpoch(),
        trace_id: "0195f000000070008000000000009001",
      });
    }
    return jsonResponse({
      completed_count: 1,
      total_count: 6,
      badge_label: "Accostage",
      llm_tier_mode: "UNCONFIGURED",
      distinct_families: [],
      assistant_trial_enabled: false,
      agentic_gates_ad10_enabled: false,
      amber_warning_badge: null,
      completed_milestone_keys: [],
      first_admin_initialized: false,
      first_admin_email: null,
      first_admin_display_name: null,
      admin_created: false,
      users_count: 0,
      org_units_count: realOrgUnitsCount,
      workspaces_count: workspacesCount,
      models_count: modelsCount,
      sources_count: sourcesCount,
      boot_epoch: getVitestBootEpoch(),
      trace_id: "0195f000000070008000000000009002",
    });
  }

  if (path === "/api/v1/bootstrap/welcome-setup/first-admin" && method === "POST") {
    const email = String(body.email ?? "admin@orcia.local");
    const displayName = String(body.display_name ?? email);
    backendState.firstAdmin = { email, displayName };
    return jsonResponse({
      first_admin_initialized: true,
      first_admin_email: email,
      first_admin_display_name: displayName,
      access_token: "mock-first-admin-access-token",
      token_type: "bearer",
    });
  }

  if (path === "/api/v1/auth/login/local" && method === "POST") {
    const email = String(body.email ?? "admin@orcia.local").toLowerCase();
    const isMockFirstAdmin = backendState.firstAdmin && backendState.firstAdmin.email.toLowerCase() === email;
    const iamUser = getVitestIamAccounts().find(
      (a) => a.principal_id.toLowerCase() === email || a.email?.toLowerCase() === email,
    );
    const displayName = iamUser?.display_name ?? (isMockFirstAdmin ? backendState.firstAdmin!.displayName : "Romain Admin");
    const roles = iamUser?.roles ?? ["PLATFORM_ADMIN"];
    const policyGate = evaluateVitestLocalLoginPolicy({
      email,
      displayName,
      roles,
      path,
      jsonResponse,
      problemResponse,
    });
    if (policyGate !== null) return policyGate;
    return jsonResponse({
      access_token: "mock-access-token",
      token_type: "bearer",
      roles,
      user_id: iamUser?.id ?? "0195f000-0000-7000-8000-000000000001",
      email,
      display_name: displayName,
      platform_role: roles[0] ?? "PLATFORM_ADMIN",
      requires_two_factor: false,
      must_change_password: false,
      issued_at_iso: "2026-11-14T12:00:00Z",
    });
  }

  if (path === "/api/v1/auth/me" && method === "GET") {
    const targetEmail = backendState.firstAdmin?.email ?? useAuthSessionStore.getState().email ?? "admin@orcia.local";
    const targetDisplayName = backendState.firstAdmin?.displayName ?? useAuthSessionStore.getState().displayName ?? "Administrateur Plateforme";
    const matchedAccount = getVitestIamAccounts().find(
      (a) => a.principal_id.toLowerCase() === targetEmail.toLowerCase() || (a.email && a.email.toLowerCase() === targetEmail.toLowerCase()),
    );
    const storeRoles = useAuthSessionStore.getState().roles;
    const resolvedRoles = matchedAccount?.roles ?? (storeRoles.length > 0 ? storeRoles : ["PLATFORM_ADMIN"]);
    const activeHat = useAuthSessionStore.getState().activeHat || (resolvedRoles.includes("PLATFORM_ADMIN") ? "PLATFORM_ADMIN" : resolvedRoles[0] || "CONTRIBUTOR");
    return jsonResponse({
      user_id: "0195f000-0000-7000-8000-000000000001",
      email: targetEmail,
      display_name: targetDisplayName,
      roles: resolvedRoles,
      active_hat: activeHat,
      access_mode: "READ_WRITE",
      must_change_password: false,
      workspaces: [],
    });
  }

  if (path === "/api/v1/auth/session" && method === "GET") {
    if ((globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__) {
      return jsonResponse({ authenticated: false, session: null, trace_id: "01a1dead000000000000000000000001" });
    }
    const targetEmail = backendState.firstAdmin?.email ?? useAuthSessionStore.getState().email ?? "admin@orcia.local";
    const targetDisplayName = backendState.firstAdmin?.displayName ?? useAuthSessionStore.getState().displayName ?? "Administrateur Plateforme";
    const matchedAccount = getVitestIamAccounts().find(
      (a) => a.principal_id.toLowerCase() === targetEmail.toLowerCase() || (a.email && a.email.toLowerCase() === targetEmail.toLowerCase()),
    );
    const storeRoles = useAuthSessionStore.getState().roles;
    const resolvedRoles = matchedAccount?.roles ?? (storeRoles.length > 0 ? storeRoles : ["PLATFORM_ADMIN"]);
    const platformRole = resolvedRoles.includes("PLATFORM_ADMIN") ? "PLATFORM_ADMIN" : resolvedRoles[0] || "CONTRIBUTOR";
    return jsonResponse({
      authenticated: true,
      session: {
        access_token: "mock-refreshed-token",
        token_type: "Bearer",
        expires_in_seconds: 900,
        roles: resolvedRoles,
        platform_role: platformRole,
        human_profile_archetype: "Tech Lead",
        primary_org_unit_id: "0192c4e0-0000-7000-8000-000000000001",
        user_id: "0195f000-0000-7000-8000-000000000001",
        email: targetEmail,
        display_name: targetDisplayName,
        must_change_password: false,
        requires_two_factor: false,
        trace_id: "01a1dead000000000000000000000002",
      },
      trace_id: "01a1dead000000000000000000000002",
    });
  }

  if (path === "/api/v1/auth/refresh" && method === "POST") {
    if ((globalThis as Record<string, unknown>).__ORCIA_MOCK_REFRESH_FAILS__) {
      return problemResponse(401, "ERR_AUTH_TOKEN_EXPIRED", "Session expirée", "Le jeton de rafraîchissement est absent ou invalide.", path);
    }
    return jsonResponse({
      access_token: "mock-refreshed-token",
      token_type: "bearer",
      roles: ["PLATFORM_ADMIN"],
      user_id: "0195f000-0000-7000-8000-000000000001",
      email: backendState.firstAdmin?.email ?? "admin@orcia.local",
      display_name: backendState.firstAdmin?.displayName ?? "Administrateur Plateforme",
      must_change_password: false,
      issued_at_iso: "2026-11-14T12:00:00Z",
    });
  }

  if (path === "/api/v1/auth/logout" && method === "POST") {
    return jsonResponse({ message: "Successfully logged out" });
  }

  if (path === "/api/v1/auth/change-password" && method === "POST") {
    if (body?.current_password === "WrongCurrentPassword123" || body?.current_password === "wrong") { // pragma: allowlist secret
      return jsonResponse(
        {
          type: "https://orcia.fr/errors/auth-current-password-invalid",
          title: "Mot de passe actuel incorrect",
          status: 422,
          detail: "Le mot de passe actuel saisi est incorrect. Vérifiez votre saisie puis réessayez.",
          error_code: "ERR_AUTH_CURRENT_PASSWORD_INVALID",
        },
        422,
      );
    }
    return jsonResponse({ message: "Password updated successfully" });
  }

  if (path === "/api/v1/bootstrap/platform-setup-state" && method === "PUT") {
    backendState.platformSetupState = body;
    if (Array.isArray(body.org_units) && (body.org_units.length > 0 || backendState.orgUnits.length === 0)) {
      backendState.orgUnits = hydrateMockOrgUnitsFromSetup(body.org_units);
      backendState.orgUnitSeq = Math.max(backendState.orgUnitSeq, backendState.orgUnits.length);
    }
    return jsonResponse(body);
  }

  if (path === "/api/v1/bootstrap/platform-setup-state" && method === "GET") {
    return jsonResponse(
      backendState.platformSetupState ?? {
        org_units: [],
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
      },
    );
  }

  return null;
}
