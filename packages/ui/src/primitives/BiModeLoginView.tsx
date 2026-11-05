import React, { useState } from "react";

export interface Rfc9457LoginError {
  readonly errorCode: string;
  readonly detail: string;
  readonly traceId?: string;
}

export interface BiModeLoginLabels {
  readonly title: string;
  readonly subtitle: string;
  readonly primarySsoCta: string;
  readonly localAccordionToggle: string;
  readonly emailLabel: string;
  readonly passwordLabel: string;
  readonly totpLabel: string;
  readonly submitLocalCta: string;
  readonly errorBannerTitle: string;
}

export interface BiModeLoginViewProps {
  readonly labels: BiModeLoginLabels;
  readonly defaultAccordionOpen?: boolean;
  readonly error?: Rfc9457LoginError | null;
  readonly onTriggerOidcSso?: () => void;
  readonly onSubmitLocalLogin?: (credentials: {
    email: string;
    password: string;
    totpCode: string;
  }) => void;
}

export function BiModeLoginView({
  labels,
  defaultAccordionOpen = false,
  error = null,
  onTriggerOidcSso,
  onSubmitLocalLogin,
}: BiModeLoginViewProps) {
  const [accordionOpen, setAccordionOpen] = useState(defaultAccordionOpen);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");

  return (
    <section
      data-testid="bi-mode-login-view"
      data-allow-password-manager="true"
      style={{
        maxWidth: "460px",
        margin: "24px auto",
        padding: "24px",
        borderRadius: "12px",
        border: "1px solid var(--orcia-border-subtle)",
        backgroundColor: "var(--orcia-surface-elevated)",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <header>
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>{labels.title}</h1>
        <p
          style={{
            margin: "6px 0 0 0",
            fontSize: "0.8125rem",
            color: "var(--orcia-text-secondary)",
          }}
        >
          {labels.subtitle}
        </p>
      </header>

      {error ? (
        <div
          role="alert"
          data-testid="login-rfc9457-error"
          style={{
            padding: "10px 12px",
            borderRadius: "8px",
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-secondary)",
            fontSize: "0.8125rem",
          }}
        >
          <strong>{labels.errorBannerTitle}</strong> —{" "}
          <code style={{ fontFamily: "var(--orcia-font-mono)" }}>
            {error.errorCode}
          </code>
          <div>{error.detail}</div>
          {error.traceId ? (
            <div
              style={{
                fontSize: "0.7rem",
                fontFamily: "var(--orcia-font-mono)",
                color: "var(--orcia-text-muted)",
              }}
            >
              trace_id={error.traceId}
            </div>
          ) : null}
        </div>
      ) : null}

      <button
        type="button"
        data-testid="login-sso-oidc-btn"
        onClick={onTriggerOidcSso}
        style={{
          padding: "10px 16px",
          borderRadius: "8px",
          fontSize: "0.875rem",
          fontWeight: 600,
          cursor: "pointer",
          border: "1px solid var(--orcia-action-primary)",
          backgroundColor: "var(--orcia-action-primary)",
          color: "var(--orcia-surface-elevated)",
        }}
      >
        🔐 {labels.primarySsoCta}
      </button>

      <div
        style={{
          borderTop: "1px solid var(--orcia-border-subtle)",
          paddingTop: "12px",
        }}
      >
        <button
          type="button"
          data-testid="login-local-accordion-toggle"
          aria-expanded={accordionOpen}
          onClick={() => setAccordionOpen((prev) => !prev)}
          style={{
            width: "100%",
            textAlign: "left",
            padding: "8px 10px",
            borderRadius: "8px",
            fontSize: "0.8125rem",
            fontWeight: 600,
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-secondary)",
            color: "var(--orcia-text-primary)",
            cursor: "pointer",
          }}
        >
          {accordionOpen ? "▾" : "▸"} {labels.localAccordionToggle}
        </button>

        {accordionOpen ? (
          <form
            data-testid="login-local-form"
            data-allow-password-manager="true"
            onSubmit={(e) => {
              e.preventDefault();
              onSubmitLocalLogin?.({ email, password, totpCode });
            }}
            style={{
              marginTop: "12px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
            }}
          >
            <label style={{ fontSize: "0.75rem", fontWeight: 600 }}>
              {labels.emailLabel}
              <input
                type="email"
                name="username"
                autoComplete="username"
                data-allow-password-manager="true"
                data-testid="login-local-email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{
                  display: "block",
                  width: "100%",
                  marginTop: "4px",
                  padding: "6px 10px",
                  borderRadius: "6px",
                  border: "1px solid var(--orcia-border-subtle)",
                }}
              />
            </label>

            <label style={{ fontSize: "0.75rem", fontWeight: 600 }}>
              {labels.passwordLabel}
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                data-allow-password-manager="true"
                data-testid="login-local-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{
                  display: "block",
                  width: "100%",
                  marginTop: "4px",
                  padding: "6px 10px",
                  borderRadius: "6px",
                  border: "1px solid var(--orcia-border-subtle)",
                }}
              />
            </label>

            <label style={{ fontSize: "0.75rem", fontWeight: 600 }}>
              {labels.totpLabel}
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                data-testid="login-local-totp"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                style={{
                  display: "block",
                  width: "100%",
                  marginTop: "4px",
                  padding: "6px 10px",
                  borderRadius: "6px",
                  border: "1px solid var(--orcia-border-subtle)",
                  fontFamily: "var(--orcia-font-mono)",
                }}
              />
            </label>

            <button
              type="submit"
              data-testid="login-local-submit"
              style={{
                padding: "8px 12px",
                borderRadius: "8px",
                fontSize: "0.8125rem",
                fontWeight: 600,
                border: "1px solid var(--orcia-border-subtle)",
                backgroundColor: "var(--orcia-surface-secondary)",
                color: "var(--orcia-text-primary)",
                cursor: "pointer",
              }}
            >
              {labels.submitLocalCta}
            </button>
          </form>
        ) : null}
      </div>
    </section>
  );
}
