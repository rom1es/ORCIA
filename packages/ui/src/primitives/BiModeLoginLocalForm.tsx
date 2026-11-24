import React from "react";
import { OrciaPasswordInput } from "./OrciaPasswordInput";
import type { BiModeLoginLabels } from "./BiModeLoginView";

export interface BiModeLoginLocalFormProps {
  readonly labels: BiModeLoginLabels;
  readonly email: string;
  readonly password: string;
  readonly totpCode: string;
  readonly inlineTotpVisible: boolean;
  readonly isSubmitting: boolean;
  readonly onEmailChange: (val: string) => void;
  readonly onPasswordChange: (val: string) => void;
  readonly onTotpChange: (val: string) => void;
  readonly onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
}

export function BiModeLoginLocalForm({
  labels,
  email,
  password,
  totpCode,
  inlineTotpVisible,
  isSubmitting,
  onEmailChange,
  onPasswordChange,
  onTotpChange,
  onSubmit,
}: BiModeLoginLocalFormProps): React.ReactElement {
  return (
    <form
      data-testid="login-local-form"
      data-allow-password-manager="true"
      onSubmit={onSubmit}
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
          onChange={(e) => onEmailChange(e.target.value)}
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
          onChange={onPasswordChange}
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
            onChange={(e) => onTotpChange(e.target.value)}
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
}
