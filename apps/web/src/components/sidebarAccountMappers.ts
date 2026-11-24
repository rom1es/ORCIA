import {
  OrciaProblemError,
  type McpPersonalTokenMetadataItem,
  type UserAccountProfileResponse,
  type UserPassthroughConnectorItemResponse,
} from "@orcia/api-client";
import type {
  UiLocalePreference,
  UiPersonalMcpTokenItem,
  UiThemePreference,
  UiUserAccountProfileView,
  UiUserPassthroughConnectorView,
} from "@orcia/ui";

const SUPPORTED_LOCALES = new Set<string>(["fr", "en"]);

export function parseUiLocalePreference(raw: unknown): UiLocalePreference | null {
  return typeof raw === "string" && SUPPORTED_LOCALES.has(raw) ? (raw as UiLocalePreference) : null;
}

export function extractUiErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof OrciaProblemError) {
    return err.problem.detail || err.problem.title || fallback;
  }
  if (err instanceof Error && err.message.trim().length > 0) {
    return err.message;
  }
  return fallback;
}

export function applyZeroMsDomPreferences(
  theme: UiThemePreference,
  locale: UiLocalePreference,
): void {
  if (typeof document !== "undefined") {
    const resolvedTheme =
      theme === "system" &&
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-color-scheme: dark)").matches
        ? "dark"
        : theme;
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.lang = locale;
  }
  if (typeof window !== "undefined" && typeof window.localStorage?.setItem === "function") {
    window.localStorage.setItem("orcia_theme", theme);
    window.localStorage.setItem("orcia_locale", locale);
  }
}

export function mapAccountProfileDto(
  profRes: UserAccountProfileResponse,
): UiUserAccountProfileView {
  return {
    principalId: profRes.principal_id,
    displayName: profRes.display_name,
    email: profRes.email,
    roles: profRes.roles,
    teams: profRes.teams.map((t) => ({
      id: t.id,
      slug: t.slug,
      name: t.name,
      unitType: t.unit_type,
      billingEnabled: t.billing_enabled,
      isLead: t.is_lead,
    })),
    billingOrgUnits: profRes.billing_org_units.map((b) => ({
      id: b.id,
      slug: b.slug,
      name: b.name,
      unitType: b.unit_type,
      billingEnabled: b.billing_enabled,
      isLead: b.is_lead,
    })),
  };
}

export function mapPassthroughConnectorsDto(
  items: readonly UserPassthroughConnectorItemResponse[],
): readonly UiUserPassthroughConnectorView[] {
  return items.map((c) => ({
    connectorId: c.connector_id,
    connectorName: c.connector_name,
    connectorKind: c.connector_kind,
    baseUrl: c.base_url,
    authMode: c.auth_mode,
    connected: c.connected,
    externalAuthorLogin: c.external_author_login,
    secretStatus: {
      configured: c.secret_status.configured,
      fingerprint: c.secret_status.fingerprint,
      updatedAtIso: c.secret_status.updated_at_iso,
    },
  }));
}

export function mapMcpTokensDto(
  tokens: readonly McpPersonalTokenMetadataItem[],
): readonly UiPersonalMcpTokenItem[] {
  return tokens.map((t) => ({
    tokenId: t.token_id,
    label: t.label,
    tokenPrefix: t.token_prefix,
    tokenSha256: t.token_sha256,
    expiresInDays: t.expires_in_days,
    rpmLimit: t.rpm_limit,
    targetKind: t.target_kind,
    targetSlug: t.target_slug,
    mcpEndpointUri: t.mcp_endpoint_uri,
    ideJsonSnippet: t.ide_json_snippet,
    revoked: t.revoked,
    createdAtIso: t.created_at_iso ?? null,
    expiresAtIso: t.expires_at_iso ?? null,
  }));
}
