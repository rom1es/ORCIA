import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaAlertBanner } from "./DesignSystemControls";
import { OrciaPasswordInput } from "./OrciaPasswordInput";
import {
  LoginTwoFactorStepPanel,
  type LoginTwoFactorLabels,
  type LoginTwoFactorStepState,
} from "./LoginTwoFactorStepPanel";

export type UiLoginViewMode = "LOCAL" | "SSO" | "BI_MODE";

export interface Rfc9457LoginError {
  readonly errorCode: string;
  readonly detail: string;
  readonly traceId?: string;
}

export interface BiModeLoginLabels {
  readonly title: string;
  readonly subtitle: string;
  readonly subtitleLocal?: string;
  readonly subtitleSso?: string;
  readonly primarySsoCta: string;
  readonly ssoUnconfiguredWarning?: string;
  readonly localAccordionToggle: string;
  readonly emailLabel: string;
  readonly passwordLabel: string;
  readonly showPasswordLabel?: string;
  readonly hidePasswordLabel?: string;
  readonly totpLabel: string;
  readonly submitLocalCta: string;
  readonly errorBannerTitle: string;
  readonly twoFactor?: LoginTwoFactorLabels;
}

export interface BiModeLoginViewProps {
  readonly labels: BiModeLoginLabels;
  readonly authMode?: UiLoginViewMode;
  readonly showInlineTotpField?: boolean;
  readonly ssoButtonLabel?: string;
  readonly oidcConfigured?: boolean;
  readonly defaultAccordionOpen?: boolean;
  readonly isSubmitting?: boolean;
  readonly error?: Rfc9457LoginError | null;
  readonly twoFactorStep?: LoginTwoFactorStepState | null;
  readonly onTriggerOidcSso?: () => void;
  readonly onSubmitLocalLogin?: (credentials: {
    email: string;
    password: string;
    totpCode: string;
  }) => void;
  readonly onSubmitTwoFactor?: (code: string) => void | Promise<void>;
  readonly onResendTwoFactor?: () => void | Promise<void>;
  readonly onCancelTwoFactor?: () => void;
}

export function BiModeLoginView({
  labels,
  authMode = "BI_MODE",
  showInlineTotpField,
  ssoButtonLabel,
  oidcConfigured = true,
  defaultAccordionOpen = false,
  isSubmitting = false,
  error = null,
  twoFactorStep = null,
  onTriggerOidcSso,
  onSubmitLocalLogin,
  onSubmitTwoFactor,
  onResendTwoFactor,
  onCancelTwoFactor,
}: BiModeLoginViewProps): React.ReactElement {
  const [accordionOpen, setAccordionOpen] = useState(defaultAccordionOpen);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");

  const inlineTotpVisible = showInlineTotpField ?? authMode === "BI_MODE";
  const resolvedSsoCta = ssoButtonLabel?.trim() || labels.primarySsoCta;

  const resolvedSubtitle =
    twoFactorStep && labels.twoFactor
      ? twoFactorStep.challengeKind === "EMAIL_OTP"
        ? labels.twoFactor.emailOtpHeading
        : twoFactorStep.challengeKind === "TOTP_ENROLL"
          ? labels.twoFactor.totpEnrollHeading
          : labels.twoFactor.totpHeading
      : authMode === "LOCAL"
        ? (labels.subtitleLocal ?? labels.subtitle)
        : authMode === "SSO"
          ? (labels.subtitleSso ?? labels.subtitle)
          : labels.subtitle;

  const handleLocalSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    onSubmitLocalLogin?.({ email, password, totpCode });
  };

  const renderLocalForm = (): React.ReactElement => (
    <form
      data-testid="login-local-form"
      onSubmit={handleLocalSubmit}
      className="space-y-3 text-left"
    >
      <div className="space-y-1">
        <label
          htmlFor="login-local-email"
          className="block text-xs font-medium"
          style={{ color: "var(--color-text-primary)" }}
        >
          {labels.emailLabel}
        </label>
        <input
          id="login-local-email"
          data-testid="login-local-email"
          type="email"
          required
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border px-3 py-2 text-sm"
          style={{
            borderColor: "var(--color-border-strong)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-text-primary)",
          }}
        />
      </div>

      <div className="space-y-1">
        <label
          htmlFor="login-local-password"
          className="block text-xs font-medium"
          style={{ color: "var(--color-text-primary)" }}
        >
          {labels.passwordLabel}
        </label>
        <OrciaPasswordInput
          id="login-local-password"
          testId="login-local-password"
          toggleTestId="login-local-password-toggle-visibility"
          maskMode="password"
          autoComplete="current-password"
          required={true}
          value={password}
          onChange={setPassword}
          showPasswordLabel={labels.showPasswordLabel ?? labels.passwordLabel}
          hidePasswordLabel={labels.hidePasswordLabel ?? labels.passwordLabel}
          inputClassName="rounded-md py-2 text-sm"
          inputStyle={{
            borderColor: "var(--color-border-strong)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-text-primary)",
          }}
        />
      </div>

      {inlineTotpVisible && (
        <div className="space-y-1">
          <label
            htmlFor="login-local-totp"
            className="block text-xs font-medium"
            style={{ color: "var(--color-text-primary)" }}
          >
            {labels.totpLabel}
          </label>
          <input
            id="login-local-totp"
            data-testid="login-local-totp"
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={totpCode}
            onChange={(e) => setTotpCode(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm font-mono"
            style={{
              borderColor: "var(--color-border-strong)",
              backgroundColor: "var(--color-surface-card)",
              color: "var(--color-text-primary)",
            }}
          />
        </div>
      )}

      <button
        type="submit"
        data-testid="login-local-submit"
        disabled={isSubmitting}
        className="orcia-ds-btn orcia-ds-btn-primary w-full justify-center py-2 text-sm font-medium"
      >
        {labels.submitLocalCta}
      </button>
    </form>
  );

  return (
    <div
      data-testid="bi-mode-login-view"
      data-allow-password-manager="true"
      data-auth-mode={authMode}
      className="mx-auto w-full max-w-md rounded-xl border p-6 shadow-sm space-y-5"
      style={{
        borderColor: "var(--color-border)",
        backgroundColor: "var(--color-surface-card)",
        color: "var(--color-text-primary)",
      }}
    >
      <header className="space-y-2">
        <div data-testid="login-brand-header" className="inline-flex items-center gap-2">
          <span
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-xs font-bold"
            style={{
              backgroundColor: "var(--color-action-primary)",
              color: "var(--color-bg-surface)",
            }}
          >
            O
          </span>
          <span className="text-sm font-bold tracking-tight">ORCIA</span>
        </div>
        <h1 className="text-xl font-bold tracking-tight">{labels.title}</h1>
        <p
          data-testid="login-mode-subtitle"
          className="text-sm"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {resolvedSubtitle}
        </p>
      </header>

      {error && (
        <OrciaAlertBanner
          tone="crimson"
          role="alert"
          testId="login-rfc9457-error"
          title={labels.errorBannerTitle}
          code={error.errorCode}
        >
          <p>{error.detail}</p>
          {error.traceId && (
            <p className="font-mono text-[10px]" style={{ color: "var(--color-text-secondary)" }}>
              trace_id: {error.traceId}
            </p>
          )}
        </OrciaAlertBanner>
      )}

      {twoFactorStep && labels.twoFactor ? (
        <LoginTwoFactorStepPanel
          step={twoFactorStep}
          labels={labels.twoFactor}
          isSubmitting={isSubmitting}
          onSubmitCode={onSubmitTwoFactor}
          onResendCode={onResendTwoFactor}
          onBack={onCancelTwoFactor}
        />
      ) : authMode === "LOCAL" ? (
        renderLocalForm()
      ) : authMode === "SSO" ? (
        <div className="space-y-3">
          {!oidcConfigured && labels.ssoUnconfiguredWarning && (
            <div
              role="status"
              data-testid="login-sso-unconfigured-banner"
              className="rounded-lg border p-3 text-xs"
              style={{
                borderColor: "var(--color-status-warning)",
                backgroundColor: "var(--color-surface-elevated)",
                color: "var(--color-text-secondary)",
              }}
            >
              {labels.ssoUnconfiguredWarning}
            </div>
          )}
          <button
            type="button"
            data-testid="login-sso-oidc-btn"
            disabled={isSubmitting || !oidcConfigured}
            onClick={() => onTriggerOidcSso?.()}
            className="orcia-ds-btn orcia-ds-btn-primary w-full justify-center gap-2 py-2.5 text-sm font-medium"
          >
            <OrciaIcon name="settings.auth" size={16} />
            <span>{resolvedSsoCta}</span>
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <button
            type="button"
            data-testid="login-sso-oidc-btn"
            disabled={isSubmitting}
            onClick={() => onTriggerOidcSso?.()}
            className="orcia-ds-btn orcia-ds-btn-primary w-full justify-center gap-2 py-2.5 text-sm font-medium"
          >
            <OrciaIcon name="settings.auth" size={16} />
            <span>{resolvedSsoCta}</span>
          </button>

          <div className="border-t pt-3" style={{ borderColor: "var(--color-border-subtle)" }}>
            <button
              type="button"
              data-testid="login-local-accordion-toggle"
              aria-expanded={accordionOpen}
              onClick={() => setAccordionOpen((prev) => !prev)}
              className="orcia-ds-btn orcia-ds-btn-secondary w-full justify-between px-3 py-2 text-xs font-medium"
            >
              <span>{labels.localAccordionToggle}</span>
              <span>{accordionOpen ? "▾" : "▸"}</span>
            </button>
            {accordionOpen && <div className="mt-3">{renderLocalForm()}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
