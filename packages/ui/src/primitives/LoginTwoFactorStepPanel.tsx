import React, { useState } from "react";

export type UiLoginChallengeKind = "EMAIL_OTP" | "TOTP" | "TOTP_ENROLL";

export interface LoginTwoFactorStepState {
  readonly challengeToken: string;
  readonly challengeKind: UiLoginChallengeKind;
  readonly maskedDestination?: string | null;
  readonly totpProvisioningUri?: string | null;
  readonly totpManualKey?: string | null;
  readonly expiresInSeconds?: number;
}

export interface LoginTwoFactorLabels {
  readonly emailOtpHeading: string;
  readonly emailOtpDescriptionPrefix: string;
  readonly emailOtpTtlNotice: string;
  readonly totpHeading: string;
  readonly totpDescription: string;
  readonly totpEnrollHeading: string;
  readonly totpEnrollDescription: string;
  readonly totpManualKeyLabel: string;
  readonly totpProvisioningUriLabel: string;
  readonly copyManualKeyCta: string;
  readonly copiedManualKeyFeedback: string;
  readonly codeInputLabel: string;
  readonly codeInputPlaceholder: string;
  readonly verifyCodeCta: string;
  readonly resendCodeCta: string;
  readonly resendDoneMessage: string;
  readonly backToLoginCta: string;
}

export interface LoginTwoFactorStepPanelProps {
  readonly step: LoginTwoFactorStepState;
  readonly labels: LoginTwoFactorLabels;
  readonly isSubmitting?: boolean;
  readonly onSubmitCode?: (code: string) => void | Promise<void>;
  readonly onResendCode?: () => void | Promise<void>;
  readonly onBack?: () => void;
}

export function LoginTwoFactorStepPanel({
  step,
  labels,
  isSubmitting = false,
  onSubmitCode,
  onResendCode,
  onBack,
}: LoginTwoFactorStepPanelProps): React.ReactElement {
  const [code, setCode] = useState("");
  const [copiedKey, setCopiedKey] = useState(false);
  const [resentDone, setResentDone] = useState(false);

  const handleCopyManualKey = async (): Promise<void> => {
    if (!step.totpManualKey) {
      return;
    }
    try {
      await navigator.clipboard?.writeText(step.totpManualKey);
      setCopiedKey(true);
    } catch (err: unknown) {
      setCopiedKey(false);
      if (typeof console !== "undefined") {
        console.debug("[orcia:2fa-clipboard]", err instanceof Error ? err.message : String(err));
      }
    }
  };

  const handleResend = async (): Promise<void> => {
    if (!onResendCode) {
      return;
    }
    setResentDone(false);
    await onResendCode();
    setResentDone(true);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    const cleaned = code.replace(/\s+/g, "").trim();
    if (!cleaned) {
      return;
    }
    await onSubmitCode?.(cleaned);
  };

  const isEmailOtp = step.challengeKind === "EMAIL_OTP";
  const isTotpEnroll = step.challengeKind === "TOTP_ENROLL";

  return (
    <form
      data-testid="login-2fa-panel"
      autoComplete="off"
      data-lpignore="true"
      data-form-type="other"
      onSubmit={(e) => void handleSubmit(e)}
      className="space-y-4 text-left"
    >
      <div
        className="rounded-lg border p-3 text-xs leading-relaxed"
        style={{
          borderColor: "var(--color-border)",
          backgroundColor: "var(--color-surface-elevated)",
          color: "var(--color-text-secondary)",
        }}
      >
        {isEmailOtp ? (
          <div className="space-y-1">
            <p className="font-semibold" style={{ color: "var(--color-text-primary)" }}>
              {labels.emailOtpHeading}
            </p>
            <p data-testid="login-2fa-destination-info">
              {labels.emailOtpDescriptionPrefix}{" "}
              <strong style={{ color: "var(--color-text-primary)" }}>
                {step.maskedDestination ?? ""}
              </strong>
            </p>
            <p className="text-[11px]">{labels.emailOtpTtlNotice}</p>
          </div>
        ) : isTotpEnroll ? (
          <div data-testid="login-2fa-totp-enroll-box" className="space-y-2">
            <p className="font-semibold" style={{ color: "var(--color-text-primary)" }}>
              {labels.totpEnrollHeading}
            </p>
            <p>{labels.totpEnrollDescription}</p>
            {step.totpManualKey && (
              <div
                className="flex items-center justify-between gap-2 rounded border px-2.5 py-2"
                style={{
                  borderColor: "var(--color-border-strong)",
                  backgroundColor: "var(--color-surface-card)",
                }}
              >
                <div className="min-w-0">
                  <div className="text-[10px] uppercase tracking-wide">
                    {labels.totpManualKeyLabel}
                  </div>
                  <code
                    data-testid="login-2fa-totp-manual-key"
                    className="block break-all font-mono text-xs font-semibold"
                    style={{ color: "var(--color-text-primary)" }}
                  >
                    {step.totpManualKey}
                  </code>
                </div>
                <button
                  type="button"
                  data-testid="login-2fa-copy-key-btn"
                  onClick={() => void handleCopyManualKey()}
                  className="orcia-ds-btn orcia-ds-btn-secondary shrink-0 px-2 py-1 text-[11px]"
                >
                  {copiedKey ? labels.copiedManualKeyFeedback : labels.copyManualKeyCta}
                </button>
              </div>
            )}
            {step.totpProvisioningUri && (
              <div className="space-y-0.5">
                <div className="text-[10px] uppercase tracking-wide">
                  {labels.totpProvisioningUriLabel}
                </div>
                <a
                  href={step.totpProvisioningUri}
                  data-testid="login-2fa-totp-uri"
                  className="block break-all font-mono text-[10px] underline"
                  style={{ color: "var(--color-primary-cobalt)" }}
                >
                  {step.totpProvisioningUri}
                </a>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-1">
            <p className="font-semibold" style={{ color: "var(--color-text-primary)" }}>
              {labels.totpHeading}
            </p>
            <p>{labels.totpDescription}</p>
          </div>
        )}
      </div>

      <div className="space-y-1">
        <label
          htmlFor="login-2fa-code-input"
          className="block text-xs font-medium"
          style={{ color: "var(--color-text-primary)" }}
        >
          {labels.codeInputLabel}
        </label>
        <input
          id="login-2fa-code-input"
          data-testid="login-2fa-code-input"
          type="text"
          inputMode="numeric"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          maxLength={6}
          value={code}
          placeholder={labels.codeInputPlaceholder}
          onChange={(e) => setCode(e.target.value.replace(/[^0-9]/g, ""))}
          className="w-full rounded-md border px-3 py-2 text-center font-mono text-base tracking-[0.35em]"
          style={{
            borderColor: "var(--color-border-strong)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-text-primary)",
          }}
        />
      </div>

      <button
        type="submit"
        data-testid="login-2fa-submit-btn"
        disabled={isSubmitting || code.trim().length < 6}
        className="orcia-ds-btn orcia-ds-btn-primary w-full justify-center py-2 text-sm font-medium"
      >
        {labels.verifyCodeCta}
      </button>

      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
        {isEmailOtp && onResendCode ? (
          <button
            type="button"
            data-testid="login-2fa-resend-btn"
            disabled={isSubmitting}
            onClick={() => void handleResend()}
            className="underline"
            style={{ color: "var(--color-primary-cobalt)" }}
          >
            {resentDone ? labels.resendDoneMessage : labels.resendCodeCta}
          </button>
        ) : (
          <span />
        )}
        {onBack && (
          <button
            type="button"
            data-testid="login-2fa-back-btn"
            disabled={isSubmitting}
            onClick={onBack}
            className="underline"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {labels.backToLoginCta}
          </button>
        )}
      </div>
    </form>
  );
}
