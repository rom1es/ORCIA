import { createOrciaApiClient, OrciaProblemError } from "@orcia/api-client";
import {
  PlatformAuthSettingsCard,
  type PlatformAuthOidcDiscoveryFeedback,
  type PlatformAuthSettingsDraft,
} from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import { resolveWebApiBaseUrl } from "../../../stores/authSessionStore";
import { useI18n } from "../../../i18n";

export interface SettingsAuthenticationSectionProps {
  readonly canMutate: boolean;
  readonly onNavigateToConnectors: () => void;
}

const DEFAULT_DRAFT: PlatformAuthSettingsDraft = {
  authMode: "LOCAL",
  twoFactorMode: "NONE",
  oidcIssuerUrl: "",
  oidcClientId: "",
  oidcRedirectUri: "",
  oidcScopes: "openid profile email",
  ssoButtonLabel: "",
  oidcClientSecretStatus: {
    configured: false,
    fingerprint: null,
    updatedAt: "",
    updatedBy: "",
  },
  oidcClientSecretInput: { action: "keep" },
  smtpConnectorConfigured: false,
  smtpConnectorName: null,
};

function resolveProblemText(err: unknown, fallback: string): string {
  if (err instanceof OrciaProblemError) {
    return `${err.problem.detail} (${err.problem.error_code})`;
  }
  if (err instanceof Error && err.message.trim()) {
    return err.message;
  }
  return fallback;
}

export function SettingsAuthenticationSection({
  canMutate,
  onNavigateToConnectors,
}: SettingsAuthenticationSectionProps): React.ReactElement {
  const { dictionary, locale } = useI18n();
  const copy = dictionary.authSettings;

  const [draft, setDraft] = useState<PlatformAuthSettingsDraft>(DEFAULT_DRAFT);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isTestingOidc, setIsTestingOidc] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{
    readonly kind: "success" | "error";
    readonly message: string;
  } | null>(null);
  const [oidcTestResult, setOidcTestResult] =
    useState<PlatformAuthOidcDiscoveryFeedback | null>(null);

  const loadSettings = useCallback(async () => {
    setIsLoading(true);
    try {
      const client = createOrciaApiClient({
        baseUrl: resolveWebApiBaseUrl(),
        locale,
      });
      const res = await client.getPlatformAuthSettings();
      setDraft({
        authMode: res.auth_mode,
        twoFactorMode: res.two_factor_mode,
        oidcIssuerUrl: res.oidc_issuer_url ?? "",
        oidcClientId: res.oidc_client_id ?? "",
        oidcRedirectUri: res.oidc_redirect_uri ?? "",
        oidcScopes: res.oidc_scopes ?? "openid profile email",
        ssoButtonLabel: res.sso_button_label ?? "",
        oidcClientSecretStatus: {
          configured: res.oidc_client_secret_configured ?? false,
          fingerprint: res.oidc_client_secret_fingerprint ?? null,
          updatedAt: res.updated_at_iso ?? "",
          updatedBy: res.updated_by ?? "",
        },
        oidcClientSecretInput: { action: "keep" },
        smtpConnectorConfigured: res.smtp_connector_configured ?? false,
        smtpConnectorName: res.smtp_connector_name ?? null,
      });
    } catch (err: unknown) {
      setFeedback({
        kind: "error",
        message: resolveProblemText(err, copy.loadErrorMessage),
      });
    } finally {
      setIsLoading(false);
    }
  }, [locale, copy.loadErrorMessage]);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const handleSave = async (): Promise<void> => {
    setIsSaving(true);
    setFeedback(null);
    try {
      const client = createOrciaApiClient({
        baseUrl: resolveWebApiBaseUrl(),
        locale,
      });
      const secretAction = draft.oidcClientSecretInput.action;
      const res = await client.updatePlatformAuthSettings({
        auth_mode: draft.authMode,
        two_factor_mode: draft.authMode === "SSO" ? "NONE" : draft.twoFactorMode,
        oidc_issuer_url: draft.oidcIssuerUrl.trim() || null,
        oidc_client_id: draft.oidcClientId.trim() || null,
        oidc_redirect_uri: draft.oidcRedirectUri.trim() || null,
        oidc_scopes: draft.oidcScopes.trim() || "openid profile email",
        sso_button_label: draft.ssoButtonLabel.trim() || null,
        oidc_client_secret:
          secretAction === "set" ? (draft.oidcClientSecretInput.plaintextValue ?? null) : null, // pragma: allowlist secret
        clear_oidc_client_secret: secretAction === "clear", // pragma: allowlist secret
      });
      setDraft((prev) => ({
        ...prev,
        authMode: res.auth_mode,
        twoFactorMode: res.two_factor_mode,
        oidcIssuerUrl: res.oidc_issuer_url ?? "",
        oidcClientId: res.oidc_client_id ?? "",
        oidcRedirectUri: res.oidc_redirect_uri ?? "",
        oidcScopes: res.oidc_scopes ?? "openid profile email",
        ssoButtonLabel: res.sso_button_label ?? "",
        oidcClientSecretStatus: {
          configured: res.oidc_client_secret_configured ?? false,
          fingerprint: res.oidc_client_secret_fingerprint ?? null,
          updatedAt: res.updated_at_iso ?? "",
          updatedBy: res.updated_by ?? "",
        },
        oidcClientSecretInput: { action: "keep" },
        smtpConnectorConfigured: res.smtp_connector_configured ?? false,
        smtpConnectorName: res.smtp_connector_name ?? null,
      }));
      setFeedback({
        kind: "success",
        message: copy.saveSuccessMessage,
      });
    } catch (err: unknown) {
      setFeedback({
        kind: "error",
        message: resolveProblemText(err, copy.saveErrorMessage),
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestOidc = async (): Promise<void> => {
    setIsTestingOidc(true);
    setOidcTestResult(null);
    try {
      const client = createOrciaApiClient({
        baseUrl: resolveWebApiBaseUrl(),
        locale,
      });
      const res = await client.testOidcDiscovery({
        issuer_url: draft.oidcIssuerUrl.trim(),
      });
      setOidcTestResult({
        reachable: res.ok ?? true,
        authorizationEndpoint: res.authorization_endpoint,
        tokenEndpoint: res.token_endpoint,
        detail: null,
        errorCode: null,
      });
    } catch (err: unknown) {
      setOidcTestResult({
        reachable: false,
        detail: resolveProblemText(err, copy.testOidcErrorMessage),
        errorCode: err instanceof OrciaProblemError ? err.problem.error_code : null,
      });
    } finally {
      setIsTestingOidc(false);
    }
  };

  if (isLoading) {
    return (
      <div
        data-testid="settings-authentication-loading"
        className="orcia-bento-card text-xs"
        style={{ color: "var(--color-muted-foreground)" }}
      >
        {copy.card.testingOidcLabel}
      </div>
    );
  }

  return (
    <PlatformAuthSettingsCard
      value={draft}
      labels={copy.card}
      secretFieldLabels={copy.secretField}
      isSaving={isSaving}
      isTestingOidc={isTestingOidc}
      readOnly={!canMutate}
      saveFeedback={feedback}
      oidcTestResult={oidcTestResult}
      onChange={setDraft}
      onSave={handleSave}
      onTestOidc={handleTestOidc}
      onNavigateToConnectors={onNavigateToConnectors}
    />
  );
}
