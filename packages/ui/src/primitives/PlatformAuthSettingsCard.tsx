import React from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaAlertBanner } from "./DesignSystemControls";
import { OrciaSpinner } from "./OrciaSpinner";
import {
  SecretField,
  type SecretFieldLabels,
  type UiSecretInputValue,
  type UiSecretStatus,
} from "./SecretField";

export type UiPlatformAuthMode = "LOCAL" | "SSO";
export type UiPlatformTwoFactorMode = "NONE" | "EMAIL_OTP" | "TOTP";

export interface PlatformAuthSettingsDraft {
  readonly authMode: UiPlatformAuthMode;
  readonly twoFactorMode: UiPlatformTwoFactorMode;
  readonly oidcIssuerUrl: string;
  readonly oidcClientId: string;
  readonly oidcRedirectUri: string;
  readonly oidcScopes: string;
  readonly ssoButtonLabel: string;
  readonly oidcClientSecretStatus: UiSecretStatus;
  readonly oidcClientSecretInput: UiSecretInputValue;
  readonly smtpConnectorConfigured: boolean;
  readonly smtpConnectorName: string | null;
}

export interface PlatformAuthOidcDiscoveryFeedback {
  readonly reachable: boolean;
  readonly authorizationEndpoint?: string | null;
  readonly tokenEndpoint?: string | null;
  readonly detail?: string | null;
  readonly errorCode?: string | null;
}

export interface PlatformAuthSettingsCardLabels {
  readonly heading: string;
  readonly subtitle: string;
  readonly authModeGroupLabel: string;
  readonly authModeLocalTitle: string;
  readonly authModeLocalDescription: string;
  readonly authModeSsoTitle: string;
  readonly authModeSsoDescription: string;
  readonly twoFactorGroupLabel: string;
  readonly twoFactorNoneTitle: string;
  readonly twoFactorNoneDescription: string;
  readonly twoFactorEmailOtpTitle: string;
  readonly twoFactorEmailOtpDescription: string;
  readonly twoFactorTotpTitle: string;
  readonly twoFactorTotpDescription: string;
  readonly smtpConfiguredBadge: string;
  readonly smtpMissingBadge: string;
  readonly smtpConfigureCta: string;
  readonly oidcSectionTitle: string;
  readonly oidcIssuerUrlLabel: string;
  readonly oidcClientIdLabel: string;
  readonly oidcRedirectUriLabel: string;
  readonly oidcScopesLabel: string;
  readonly ssoButtonLabelField: string;
  readonly testOidcCta: string;
  readonly testingOidcLabel: string;
  readonly oidcDiscoverySuccessPrefix: string;
  readonly oidcDiscoveryFailurePrefix: string;
  readonly saveCta: string;
  readonly savingLabel: string;
  readonly readOnlyNotice: string;
}

export interface PlatformAuthSettingsCardProps {
  readonly value: PlatformAuthSettingsDraft;
  readonly labels: PlatformAuthSettingsCardLabels;
  readonly secretFieldLabels: SecretFieldLabels;
  readonly isSaving?: boolean;
  readonly isTestingOidc?: boolean;
  readonly readOnly?: boolean;
  readonly saveFeedback?: { readonly kind: "success" | "error"; readonly message: string } | null;
  readonly oidcTestResult?: PlatformAuthOidcDiscoveryFeedback | null;
  readonly onChange: (next: PlatformAuthSettingsDraft) => void;
  readonly onSave: () => void | Promise<void>;
  readonly onTestOidc: () => void | Promise<void>;
  readonly onNavigateToConnectors?: () => void;
}

export function PlatformAuthSettingsCard({
  value,
  labels,
  secretFieldLabels,
  isSaving = false,
  isTestingOidc = false,
  readOnly = false,
  saveFeedback = null,
  oidcTestResult = null,
  onChange,
  onSave,
  onTestOidc,
  onNavigateToConnectors,
}: PlatformAuthSettingsCardProps): React.ReactElement {
  const twoFactorOptions: readonly {
    key: UiPlatformTwoFactorMode;
    title: string;
    description: string;
  }[] = [
    { key: "NONE", title: labels.twoFactorNoneTitle, description: labels.twoFactorNoneDescription },
    {
      key: "EMAIL_OTP",
      title: labels.twoFactorEmailOtpTitle,
      description: labels.twoFactorEmailOtpDescription,
    },
    { key: "TOTP", title: labels.twoFactorTotpTitle, description: labels.twoFactorTotpDescription },
  ];

  return (
    <section
      data-testid="settings-authentication-section"
      className="rounded-xl border p-5 space-y-6"
      style={{
        borderColor: "var(--color-border)",
        backgroundColor: "var(--color-surface-card)",
        color: "var(--color-text-primary)",
      }}
    >
      <header className="space-y-1">
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <OrciaIcon name="settings.auth" size={18} />
          <span>{labels.heading}</span>
        </h2>
        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
          {labels.subtitle}
        </p>
      </header>

      {readOnly && (
        <div
          className="rounded-lg border px-3 py-2 text-xs"
          style={{
            borderColor: "var(--color-border)",
            backgroundColor: "var(--color-surface-elevated)",
            color: "var(--color-text-secondary)",
          }}
        >
          {labels.readOnlyNotice}
        </div>
      )}

      <div className="space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wide">{labels.authModeGroupLabel}</div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {(["LOCAL", "SSO"] as const).map((modeKey) => {
            const active = value.authMode === modeKey;
            const title = modeKey === "LOCAL" ? labels.authModeLocalTitle : labels.authModeSsoTitle;
            const description =
              modeKey === "LOCAL" ? labels.authModeLocalDescription : labels.authModeSsoDescription;
            return (
              <button
                key={modeKey}
                type="button"
                role="radio"
                aria-checked={active}
                disabled={readOnly}
                data-testid={`auth-mode-option-${modeKey}`}
                onClick={() => onChange({ ...value, authMode: modeKey })}
                className="rounded-lg border p-3.5 text-left transition-colors space-y-1"
                style={{
                  borderColor: active ? "var(--color-primary-cobalt)" : "var(--color-border)",
                  backgroundColor: active
                    ? "var(--color-sidebar-active-bg)"
                    : "var(--color-surface-card)",
                }}
              >
                <div className="flex items-center justify-between gap-2 text-sm font-semibold">
                  <span>{title}</span>
                  <span>{active ? "●" : "○"}</span>
                </div>
                <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
                  {description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {value.authMode === "LOCAL" ? (
        <div data-testid="auth-local-2fa-config" className="space-y-3 border-t mt-6 pt-5" style={{ borderColor: "var(--color-border-subtle)" }}>
          <div className="block mb-3 text-xs font-semibold uppercase tracking-wide">{labels.twoFactorGroupLabel}</div>
          <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
            {twoFactorOptions.map((opt) => {
              const active = value.twoFactorMode === opt.key;
              return (
                <button
                  key={opt.key}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  disabled={readOnly}
                  data-testid={`two-factor-mode-option-${opt.key}`}
                  onClick={() => onChange({ ...value, twoFactorMode: opt.key })}
                  className="rounded-lg border p-3 text-left transition-colors space-y-1"
                  style={{
                    borderColor: active ? "var(--color-primary-cobalt)" : "var(--color-border)",
                    backgroundColor: active
                      ? "var(--color-sidebar-active-bg)"
                      : "var(--color-surface-card)",
                  }}
                >
                  <div className="flex items-center justify-between gap-1 text-xs font-semibold">
                    <span>{opt.title}</span>
                    <span>{active ? "●" : "○"}</span>
                  </div>
                  <p className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                    {opt.description}
                  </p>
                </button>
              );
            })}
          </div>

          {value.twoFactorMode === "EMAIL_OTP" && (
            <OrciaAlertBanner
              tone={value.smtpConnectorConfigured ? "emerald" : "amber"}
              role="status"
              testId="auth-smtp-status-badge"
              action={
                onNavigateToConnectors ? (
                  <button
                    type="button"
                    data-testid="auth-goto-connectors-btn"
                    onClick={onNavigateToConnectors}
                    className="orcia-ds-btn orcia-ds-btn-secondary px-2.5 py-1 text-xs"
                  >
                    {labels.smtpConfigureCta}
                  </button>
                ) : undefined
              }
            >
              {value.smtpConnectorConfigured
                ? `${labels.smtpConfiguredBadge}${value.smtpConnectorName ? ` · ${value.smtpConnectorName}` : ""}`
                : labels.smtpMissingBadge}
            </OrciaAlertBanner>
          )}
        </div>
      ) : (
        <div data-testid="auth-oidc-sso-config" className="space-y-4 border-t mt-6 pt-5" style={{ borderColor: "var(--color-border-subtle)" }}>
          <div className="block mb-3 text-xs font-semibold uppercase tracking-wide">{labels.oidcSectionTitle}</div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="space-y-1 text-xs">
              <span className="font-medium">{labels.oidcIssuerUrlLabel}</span>
              <input
                type="url"
                disabled={readOnly}
                autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"
                data-testid="auth-oidc-issuer-input"
                value={value.oidcIssuerUrl}
                onChange={(e) => onChange({ ...value, oidcIssuerUrl: e.target.value })}
                placeholder="https://idp.entreprise.com/realms/orcia"
                className="w-full rounded-md border px-2.5 py-1.5 text-xs font-mono"
                style={{ borderColor: "var(--color-border-strong)", backgroundColor: "var(--color-surface-card)" }}
              />
            </label>
            <label className="space-y-1 text-xs">
              <span className="font-medium">{labels.oidcClientIdLabel}</span>
              <input
                type="text"
                disabled={readOnly}
                autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"
                data-testid="auth-oidc-client-id-input"
                value={value.oidcClientId}
                onChange={(e) => onChange({ ...value, oidcClientId: e.target.value })}
                className="w-full rounded-md border px-2.5 py-1.5 text-xs font-mono"
                style={{ borderColor: "var(--color-border-strong)", backgroundColor: "var(--color-surface-card)" }}
              />
            </label>
            <label className="space-y-1 text-xs">
              <span className="font-medium">{labels.oidcRedirectUriLabel}</span>
              <input
                type="url"
                disabled={readOnly}
                autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"
                data-testid="auth-oidc-redirect-uri-input"
                value={value.oidcRedirectUri}
                onChange={(e) => onChange({ ...value, oidcRedirectUri: e.target.value })}
                placeholder="https://orcia.entreprise.com/login"
                className="w-full rounded-md border px-2.5 py-1.5 text-xs font-mono"
                style={{ borderColor: "var(--color-border-strong)", backgroundColor: "var(--color-surface-card)" }}
              />
            </label>
            <label className="space-y-1 text-xs">
              <span className="font-medium">{labels.oidcScopesLabel}</span>
              <input
                type="text"
                disabled={readOnly}
                autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"
                data-testid="auth-oidc-scopes-input"
                value={value.oidcScopes}
                onChange={(e) => onChange({ ...value, oidcScopes: e.target.value })}
                className="w-full rounded-md border px-2.5 py-1.5 text-xs font-mono"
                style={{ borderColor: "var(--color-border-strong)", backgroundColor: "var(--color-surface-card)" }}
              />
            </label>
          </div>

          <label className="block space-y-1 text-xs">
            <span className="font-medium">{labels.ssoButtonLabelField}</span>
            <input
              type="text"
              disabled={readOnly}
              autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"
              data-testid="auth-sso-button-label-input"
              value={value.ssoButtonLabel}
              onChange={(e) => onChange({ ...value, ssoButtonLabel: e.target.value })}
              className="w-full rounded-md border px-2.5 py-1.5 text-xs"
              style={{ borderColor: "var(--color-border-strong)", backgroundColor: "var(--color-surface-card)" }}
            />
          </label>

          <SecretField
            status={value.oidcClientSecretStatus}
            labels={secretFieldLabels}
            readOnly={readOnly}
            onSecretAction={(oidcClientSecretInput) => onChange({ ...value, oidcClientSecretInput })}
          />

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={readOnly || isTestingOidc}
              data-testid="auth-test-oidc-btn"
              onClick={() => void onTestOidc()}
              className="orcia-ds-btn orcia-ds-btn-secondary inline-flex items-center gap-1.5 px-3 py-1.5 text-xs"
            >
              {isTestingOidc && <OrciaSpinner size="xs" />}
              <span>{isTestingOidc ? labels.testingOidcLabel : labels.testOidcCta}</span>
            </button>
            {oidcTestResult && (
              <div
                data-testid="auth-oidc-discovery-result"
                className="text-xs font-mono"
                style={{
                  color: oidcTestResult.reachable
                    ? "var(--color-status-success)"
                    : "var(--color-status-error)",
                }}
              >
                {oidcTestResult.reachable
                  ? `${labels.oidcDiscoverySuccessPrefix} (${oidcTestResult.authorizationEndpoint ?? ""})`
                  : `${labels.oidcDiscoveryFailurePrefix} ${oidcTestResult.errorCode ?? ""} ${oidcTestResult.detail ?? ""}`}
              </div>
            )}
          </div>
        </div>
      )}

      {saveFeedback && (
        <OrciaAlertBanner
          tone={saveFeedback.kind === "success" ? "emerald" : "crimson"}
          role={saveFeedback.kind === "error" ? "alert" : "status"}
          testId="auth-save-feedback"
        >
          {saveFeedback.message}
        </OrciaAlertBanner>
      )}

      {!readOnly && (
        <div className="flex justify-end border-t pt-3" style={{ borderColor: "var(--color-border-subtle)" }}>
          <button
            type="button"
            disabled={isSaving}
            data-testid="auth-save-settings-btn"
            onClick={() => void onSave()}
            className="orcia-ds-btn orcia-ds-btn-primary inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium"
          >
            {isSaving && <OrciaSpinner size="xs" />}
            <span>{isSaving ? labels.savingLabel : labels.saveCta}</span>
          </button>
        </div>
      )}
    </section>
  );
}
