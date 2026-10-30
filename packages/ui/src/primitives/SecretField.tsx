import { useState } from "react";

export type UiSecretAction = "keep" | "set" | "clear";

export interface UiSecretInputValue {
  readonly action: UiSecretAction;
  readonly plaintextValue?: string;
}

export interface UiSecretStatus {
  readonly configured: boolean;
  readonly fingerprint: string | null;
  readonly updatedAt: string;
  readonly updatedBy: string;
}

export interface SecretFieldLabels {
  readonly fieldLabel: string;
  readonly configuredBadge: string;
  readonly unconfiguredBadge: string;
  readonly fingerprintPrefix: string;
  readonly replaceSecretCta: string;
  readonly cancelReplaceCta: string;
  readonly clearSecretCta: string;
  readonly saveNewSecretCta: string;
  readonly inputPlaceholder: string;
}

export interface SecretFieldProps {
  readonly status: UiSecretStatus;
  readonly labels: SecretFieldLabels;
  readonly readOnly?: boolean;
  readonly onSecretAction: (input: UiSecretInputValue) => void;
}

export function SecretField({
  status,
  labels,
  readOnly = false,
  onSecretAction,
}: SecretFieldProps) {
  const [isReplacing, setIsReplacing] = useState(false);
  const [draftValue, setDraftValue] = useState("");

  const handleConfirmSet = () => {
    const trimmed = draftValue.trim();
    if (!trimmed) {
      return;
    }
    onSecretAction({ action: "set", plaintextValue: trimmed });
    setDraftValue("");
    setIsReplacing(false);
  };

  const handleClear = () => {
    setDraftValue("");
    setIsReplacing(false);
    onSecretAction({ action: "clear" });
  };

  return (
    <div
      data-testid="secret-field-container"
      style={{
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--color-surface-elevated)",
        padding: "0.75rem 1rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.625rem",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "0.75rem",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
          <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
            {labels.fieldLabel}
          </span>
          <span
            data-testid="secret-field-status-badge"
            style={{
              fontSize: "0.75rem",
              padding: "0.125rem 0.5rem",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-surface-canvas)",
              color: "var(--color-text-secondary)",
            }}
          >
            {status.configured ? labels.configuredBadge : labels.unconfiguredBadge}
          </span>
          {status.configured && status.fingerprint ? (
            <code
              data-testid="secret-field-fingerprint"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                color: "var(--color-text-secondary)",
              }}
            >
              {labels.fingerprintPrefix}: {status.fingerprint}
            </code>
          ) : null}
        </div>

        {!readOnly ? (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <button
              type="button"
              data-testid="secret-field-replace-toggle-btn"
              onClick={() => {
                setDraftValue("");
                setIsReplacing((prev) => !prev);
              }}
              style={{
                minHeight: "36px",
                padding: "0.25rem 0.625rem",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border-strong)",
                backgroundColor: "var(--color-surface-canvas)",
                cursor: "pointer",
              }}
            >
              {isReplacing ? labels.cancelReplaceCta : labels.replaceSecretCta}
            </button>
            {status.configured ? (
              <button
                type="button"
                data-testid="secret-field-clear-btn"
                onClick={handleClear}
                style={{
                  minHeight: "36px",
                  padding: "0.25rem 0.625rem",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border-subtle)",
                  backgroundColor: "var(--color-surface-canvas)",
                  cursor: "pointer",
                }}
              >
                {labels.clearSecretCta}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      {isReplacing && !readOnly ? (
        <div
          data-testid="secret-field-replace-form"
          style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
        >
          <input
            type="password"
            data-testid="secret-field-write-only-input"
            aria-label={labels.fieldLabel}
            value={draftValue}
            placeholder={labels.inputPlaceholder}
            onChange={(e) => setDraftValue(e.target.value)}
            style={{
              flex: 1,
              minHeight: "38px",
              padding: "0.375rem 0.625rem",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border-strong)",
              fontFamily: "var(--font-mono)",
            }}
          />
          <button
            type="button"
            data-testid="secret-field-commit-set-btn"
            onClick={handleConfirmSet}
            style={{
              minHeight: "38px",
              padding: "0.375rem 0.75rem",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border-strong)",
              backgroundColor: "var(--color-action-primary)",
              color: "var(--color-surface-elevated)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {labels.saveNewSecretCta}
          </button>
        </div>
      ) : null}
    </div>
  );
}
