import { getActiveVitestSmtpConnectorName } from "./vitestConnectorsMockHandlers";

export interface MockAuthPolicyState {
  authMode: "LOCAL" | "SSO";
  twoFactorMode: "NONE" | "EMAIL_OTP" | "TOTP";
  oidcIssuerUrl: string | null;
  oidcClientId: string | null;
  oidcClientSecretConfigured: boolean;
  oidcClientSecretFingerprint: string | null;
  oidcScopes: string;
  oidcRedirectUri: string | null;
  ssoButtonLabel: string | null;
  bootEpoch: string;
  updatedBy: string | null;
  updatedAtIso: string;
}

interface PendingChallenge {
  readonly email: string;
  readonly displayName: string;
  readonly roles: string[];
  readonly kind: "EMAIL_OTP" | "TOTP" | "TOTP_ENROLL";
  code: string;
}

const TRACE_ID = "0195f000000070008000000000000999";

let policyState: MockAuthPolicyState = defaultPolicyState();
let challengeSeq = 0;
let totpEnrolledEmails = new Set<string>();
let challenges = new Map<string, PendingChallenge>();
let oidcPendingStates = new Map<string, { email: string; displayName: string; roles: string[] }>();

function defaultPolicyState(): MockAuthPolicyState {
  return {
    authMode: "LOCAL",
    twoFactorMode: "NONE",
    oidcIssuerUrl: null,
    oidcClientId: null,
    oidcClientSecretConfigured: false,
    oidcClientSecretFingerprint: null,
    oidcScopes: "openid profile email",
    oidcRedirectUri: null,
    ssoButtonLabel: null,
    bootEpoch: "vitest-boot-epoch-1",
    updatedBy: null,
    updatedAtIso: "2026-11-15T10:00:00Z",
  };
}

export function resetVitestAuthPolicyMockState(): void {
  policyState = defaultPolicyState();
  challengeSeq = 0;
  totpEnrolledEmails = new Set<string>();
  challenges = new Map<string, PendingChallenge>();
  oidcPendingStates = new Map<string, { email: string; displayName: string; roles: string[] }>();
}

export function getVitestBootEpoch(): string {
  return policyState.bootEpoch;
}

export function rotateVitestBootEpoch(nextEpoch?: string): string {
  policyState = {
    ...defaultPolicyState(),
    bootEpoch: nextEpoch ?? `vitest-boot-epoch-${Date.now()}`,
  };
  return policyState.bootEpoch;
}

export function seedVitestPlatformAuthPolicy(overrides: Partial<MockAuthPolicyState>): void {
  policyState = { ...policyState, ...overrides };
}

export function markVitestUserTotpEnrolled(email: string): void {
  totpEnrolledEmails.add(email.trim().toLowerCase());
}

export function getVitestLastChallengeCode(challengeToken: string): string | null {
  return challenges.get(challengeToken)?.code ?? null;
}

function maskEmail(email: string): string {
  const [local = "", domain = ""] = email.split("@");
  if (!domain) return email;
  const visible = local.length <= 2 ? local[0] ?? "*" : `${local.slice(0, 2)}***`;
  return `${visible}@${domain}`;
}

function isUnsafeUrl(raw: string | null | undefined): boolean {
  if (!raw) return false;
  const low = raw.toLowerCase();
  return low.includes("169.254.169.254") || low.includes("metadata.google.internal");
}

function buildSettingsPayload(): Record<string, unknown> {
  const smtpName = getActiveVitestSmtpConnectorName();
  return {
    auth_mode: policyState.authMode,
    two_factor_mode: policyState.twoFactorMode,
    oidc_issuer_url: policyState.oidcIssuerUrl,
    oidc_client_id: policyState.oidcClientId,
    oidc_client_secret_configured: policyState.oidcClientSecretConfigured,
    oidc_client_secret_fingerprint: policyState.oidcClientSecretFingerprint,
    oidc_scopes: policyState.oidcScopes,
    oidc_redirect_uri: policyState.oidcRedirectUri,
    sso_button_label: policyState.ssoButtonLabel,
    smtp_connector_configured: smtpName !== null,
    smtp_connector_name: smtpName,
    boot_epoch: policyState.bootEpoch,
    updated_by: policyState.updatedBy,
    updated_at_iso: policyState.updatedAtIso,
    trace_id: TRACE_ID,
  };
}

function buildMockTokenPayload(params: {
  accessToken: string;
  expiresInSeconds: number;
  userId: string;
  email: string;
  displayName: string;
  roles: string[];
  requiresTwoFactor?: boolean;
  challengeToken?: string;
  challengeKind?: "EMAIL_OTP" | "TOTP" | "TOTP_ENROLL";
  maskedDestination?: string | null;
  totpProvisioningUri?: string | null;
  totpManualKey?: string | null;
}): Record<string, unknown> {
  return {
    access_token: params.accessToken,
    token_type: "Bearer",
    expires_in_seconds: params.expiresInSeconds,
    user_id: params.userId,
    email: params.email,
    display_name: params.displayName,
    platform_role: params.roles[0] ?? "CONTRIBUTOR",
    human_profile_archetype: "BUILDER",
    primary_org_unit_id: "org-global",
    roles: params.roles,
    must_change_password: false,
    requires_two_factor: Boolean(params.requiresTwoFactor),
    ...(params.challengeToken ? { challenge_token: params.challengeToken } : {}),
    ...(params.challengeKind ? { challenge_kind: params.challengeKind } : {}),
    ...(params.maskedDestination !== undefined ? { masked_destination: params.maskedDestination } : {}),
    ...(params.totpProvisioningUri !== undefined ? { totp_provisioning_uri: params.totpProvisioningUri } : {}),
    ...(params.totpManualKey !== undefined ? { totp_manual_key: params.totpManualKey } : {}),
    trace_id: TRACE_ID,
  };
}

export function evaluateVitestLocalLoginPolicy(params: {
  email: string;
  displayName: string;
  roles: string[];
  path: string;
  jsonResponse: (data: unknown, status?: number) => Response;
  problemResponse: (status: number, errorCode: string, title: string, detail: string, instance: string) => Response;
}): Response | null {
  const { email, displayName, roles, path, jsonResponse, problemResponse } = params;
  if (policyState.authMode === "SSO") {
    return problemResponse(403, "ERR_LOCAL_AUTH_DISABLED", "Connexion locale désactivée", "La politique impose le SSO.", path);
  }
  if (policyState.twoFactorMode === "NONE") return null;

  if (policyState.twoFactorMode === "EMAIL_OTP") {
    if (!getActiveVitestSmtpConnectorName()) {
      return problemResponse(
        422,
        "ERR_AUTH_SMTP_CONNECTOR_REQUIRED",
        "Connecteur SMTP requis",
        "Configurez et activez un connecteur SMTP_MAIL pour la vérification par e-mail.",
        path,
      );
    }
    challengeSeq += 1;
    const token = `vitest-chal-${challengeSeq}`;
    challenges.set(token, { email, displayName, roles, kind: "EMAIL_OTP", code: "123456" });
    return jsonResponse(
      buildMockTokenPayload({
        accessToken: "",
        expiresInSeconds: 300,
        userId: "usr-vitest-1",
        email,
        displayName,
        roles,
        requiresTwoFactor: true,
        challengeToken: token,
        challengeKind: "EMAIL_OTP",
        maskedDestination: maskEmail(email),
        totpProvisioningUri: null,
        totpManualKey: null,
      }),
    );
  }

  const kind: "TOTP" | "TOTP_ENROLL" = totpEnrolledEmails.has(email.trim().toLowerCase()) ? "TOTP" : "TOTP_ENROLL";
  challengeSeq += 1;
  const token = `vitest-chal-${challengeSeq}`;
  challenges.set(token, { email, displayName, roles, kind, code: "654321" });
  return jsonResponse(
    buildMockTokenPayload({
      accessToken: "",
      expiresInSeconds: 300,
      userId: "usr-vitest-1",
      email,
      displayName,
      roles,
      requiresTwoFactor: true,
      challengeToken: token,
      challengeKind: kind,
      maskedDestination: null,
      totpProvisioningUri:
        kind === "TOTP_ENROLL"
          ? `otpauth://totp/ORCIA:${encodeURIComponent(email)}?secret=JBSWY3DPEHPK3PXP&issuer=ORCIA`
          : null,
      totpManualKey: kind === "TOTP_ENROLL" ? "JBSW Y3DP EHPK 3PXP" : null,
    }),
  );
}

export function handleVitestAuthPolicyRoute(params: {
  method: string;
  path: string;
  body: Record<string, unknown>;
  reqHeaders: Headers;
  jsonResponse: (data: unknown, status?: number) => Response;
  problemResponse: (
    status: number,
    errorCode: string,
    title: string,
    detail: string,
    instance: string,
  ) => Response;
}): Response | null {
  const { method, path, body, reqHeaders, jsonResponse, problemResponse } = params;
  const accessMode = reqHeaders.get("x-orcia-access-mode")?.toUpperCase();
  const isObserver = accessMode === "READ_ONLY_OBSERVER";

  if (path === "/api/v1/auth/public-config" && method === "GET") {
    const oidcReady = Boolean(
      policyState.oidcIssuerUrl && policyState.oidcClientId && policyState.oidcRedirectUri,
    );
    return jsonResponse({
      auth_mode: policyState.authMode,
      two_factor_mode: policyState.twoFactorMode,
      oidc_enabled: oidcReady,
      sso_button_label: policyState.ssoButtonLabel,
      boot_epoch: policyState.bootEpoch,
      trace_id: TRACE_ID,
    });
  }

  if (path === "/api/v1/settings/authentication") {
    if (method === "GET") return jsonResponse(buildSettingsPayload());
    if (method === "PUT") {
      if (isObserver) {
        return problemResponse(403, "ERR_OBSERVER_MODE_READ_ONLY", "Lecture seule", "Mutation interdite", path);
      }
      const nextAuthMode = (body.auth_mode === "SSO" ? "SSO" : "LOCAL") as "LOCAL" | "SSO";
      const nextTwoFactorMode = (["NONE", "EMAIL_OTP", "TOTP"].includes(String(body.two_factor_mode))
        ? String(body.two_factor_mode)
        : "NONE") as "NONE" | "EMAIL_OTP" | "TOTP";
      const issuer = body.oidc_issuer_url ? String(body.oidc_issuer_url).trim() : null;
      const clientId = body.oidc_client_id ? String(body.oidc_client_id).trim() : null;
      const redirectUri = body.oidc_redirect_uri ? String(body.oidc_redirect_uri).trim() : null;

      if (isUnsafeUrl(issuer) || isUnsafeUrl(redirectUri)) {
        return problemResponse(422, "ERR_UNSAFE_CONNECTOR_ENDPOINT_URL", "URL non sécurisée", "Metadata IP interdite", path);
      }
      if (nextAuthMode === "SSO" && (!issuer || !clientId || !redirectUri)) {
        return problemResponse(422, "ERR_SSO_CONFIG_INCOMPLETE", "Configuration OIDC incomplète", "Renseignez émetteur, Client ID et redirect URI.", path);
      }
      if (nextAuthMode === "LOCAL" && nextTwoFactorMode === "EMAIL_OTP" && !getActiveVitestSmtpConnectorName()) {
        return problemResponse(422, "ERR_AUTH_SMTP_CONNECTOR_REQUIRED", "Connecteur SMTP requis", "Activez un connecteur SMTP_MAIL dans Connecteurs.", path);
      }
      const newSecret = body.oidc_client_secret ? String(body.oidc_client_secret).trim() : "";
      policyState = {
        ...policyState,
        authMode: nextAuthMode,
        twoFactorMode: nextTwoFactorMode,
        oidcIssuerUrl: issuer,
        oidcClientId: clientId,
        oidcClientSecretConfigured: body.clear_oidc_client_secret ? false : newSecret.length > 0 || policyState.oidcClientSecretConfigured,
        oidcClientSecretFingerprint: body.clear_oidc_client_secret ? null : newSecret.length > 0 ? "sha256:vitest-oidc-secret" : policyState.oidcClientSecretFingerprint,
        oidcScopes: body.oidc_scopes ? String(body.oidc_scopes).trim() : "openid profile email",
        oidcRedirectUri: redirectUri,
        ssoButtonLabel: body.sso_button_label ? String(body.sso_button_label).trim() : null,
        updatedBy: "admin@orcia.test",
        updatedAtIso: new Date().toISOString(),
      };
      return jsonResponse(buildSettingsPayload());
    }
  }

  if (path === "/api/v1/settings/authentication/test-oidc" && method === "POST") {
    const issuerUrl = String(body.issuer_url ?? "").trim();
    if (isUnsafeUrl(issuerUrl)) {
      return problemResponse(422, "ERR_UNSAFE_CONNECTOR_ENDPOINT_URL", "URL non sécurisée", "Metadata IP interdite", path);
    }
    return jsonResponse({
      ok: true,
      issuer: issuerUrl,
      authorization_endpoint: `${issuerUrl.replace(/\/$/, "")}/authorize`,
      token_endpoint: `${issuerUrl.replace(/\/$/, "")}/token`,
      userinfo_endpoint: `${issuerUrl.replace(/\/$/, "")}/userinfo`,
      latency_ms: 14.2,
      trace_id: TRACE_ID,
    });
  }

  if (path === "/api/v1/auth/login/verify-2fa" && method === "POST") {
    const token = String(body.challenge_token ?? "");
    const code = String(body.code ?? "").trim();
    const pending = challenges.get(token);
    if (!pending || pending.code !== code) {
      return problemResponse(401, "ERR_AUTH_2FA_CHALLENGE_INVALID", "Code invalide", "Code 2FA incorrect ou expiré.", path);
    }
    if (pending.kind === "TOTP_ENROLL") totpEnrolledEmails.add(pending.email.trim().toLowerCase());
    challenges.delete(token);
    return jsonResponse(
      buildMockTokenPayload({ accessToken: "mock-2fa-access-token", expiresInSeconds: 900, userId: "usr-vitest-1", email: pending.email, displayName: pending.displayName, roles: pending.roles }),
    );
  }

  if (path === "/api/v1/auth/login/resend-2fa" && method === "POST") {
    const token = String(body.challenge_token ?? "");
    const pending = challenges.get(token);
    if (!pending || pending.kind !== "EMAIL_OTP") {
      return problemResponse(401, "ERR_AUTH_2FA_CHALLENGE_INVALID", "Challenge invalide", "Challenge introuvable.", path);
    }
    pending.code = "246810";
    return jsonResponse({
      sent: true,
      masked_destination: maskEmail(pending.email),
      expires_in_seconds: 300,
      trace_id: TRACE_ID,
    });
  }

  if (path === "/api/v1/auth/oidc/authorize" && method === "GET") {
    if (policyState.authMode !== "SSO") {
      return problemResponse(403, "ERR_SSO_AUTH_DISABLED", "SSO désactivé", "La politique impose la connexion locale.", path);
    }
    if (!policyState.oidcIssuerUrl || !policyState.oidcClientId || !policyState.oidcRedirectUri) {
      return problemResponse(422, "ERR_SSO_CONFIG_INCOMPLETE", "SSO incomplet", "Configuration OIDC manquante.", path);
    }
    const state = "vitest-oidc-state-0123456789";
    oidcPendingStates.set(state, { email: "sso.user@orcia.test", displayName: "SSO User", roles: ["CONTRIBUTOR"] });
    const authorizeUrl = `${policyState.oidcIssuerUrl.replace(/\/$/, "")}/authorize?client_id=${encodeURIComponent(
      policyState.oidcClientId,
    )}&redirect_uri=${encodeURIComponent(policyState.oidcRedirectUri)}&state=${state}`;
    return jsonResponse({ authorize_url: authorizeUrl, state, trace_id: TRACE_ID });
  }

  if (path === "/api/v1/auth/oidc/callback" && method === "POST") {
    if (policyState.authMode !== "SSO") {
      return problemResponse(403, "ERR_SSO_AUTH_DISABLED", "SSO désactivé", "La politique impose la connexion locale.", path);
    }
    const state = String(body.state ?? "");
    const pending = oidcPendingStates.get(state);
    if (!pending) {
      return problemResponse(401, "ERR_INVALID_CREDENTIALS", "State OIDC invalide", "Jeton state expiré ou inconnu.", path);
    }
    oidcPendingStates.delete(state);
    return jsonResponse(
      buildMockTokenPayload({
        accessToken: "mock-oidc-access-token",
        expiresInSeconds: 900,
        userId: "usr-oidc-1",
        email: pending.email,
        displayName: pending.displayName,
        roles: pending.roles,
      }),
    );
  }

  return null;
}
