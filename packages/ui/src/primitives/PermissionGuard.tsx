import type { ReactNode } from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";

export type UiPermissionVerb = "create" | "read" | "update" | "delete" | "execute" | "grant";
export type UiPermissionFallbackMode = "passive-lock" | "disabled" | "hidden";

export interface PermissionGuardLabels {
  readonly passiveLockBadge: string;
  readonly passiveLockDescription: string;
  readonly requestAccessCta: string;
  readonly disabledHint: string;
}

export interface PermissionGuardProps {
  readonly scopePath: string;
  readonly verb: UiPermissionVerb;
  readonly allowedVerbs: readonly UiPermissionVerb[];
  readonly fallbackMode?: UiPermissionFallbackMode;
  readonly hiddenWhenUnauthorized?: boolean;
  readonly resourceTitle?: string;
  readonly labels: PermissionGuardLabels;
  readonly onRequestAccess?: (scopePath: string, verb: UiPermissionVerb) => void;
  readonly children: ReactNode;
}

export function PermissionGuard({
  scopePath,
  verb,
  allowedVerbs,
  fallbackMode = "passive-lock",
  hiddenWhenUnauthorized = false,
  resourceTitle,
  labels,
  onRequestAccess,
  children,
}: PermissionGuardProps) {
  const isAuthorized = allowedVerbs.includes(verb);

  if (isAuthorized) {
    return <>{children}</>;
  }

  if (hiddenWhenUnauthorized || fallbackMode === "hidden") {
    return null;
  }

  if (fallbackMode === "disabled") {
    const disabledReason = `${labels.disabledHint} (${verb})`;
    return (
      <div
        data-testid="permission-guard-disabled"
        aria-disabled="true"
        title={disabledReason}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          opacity: 0.55,
          pointerEvents: "none",
        }}
      >
        {children}
        <DisabledButtonAlertIndicator
          disabled={true}
          reason={disabledReason}
          testIdSuffix="permission-guard-disabled"
        />
      </div>
    );
  }

  return (
    <section
      data-testid="permission-guard-passive-lock"
      aria-label={labels.passiveLockBadge}
      style={{
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--color-surface-elevated)",
        padding: "0.875rem 1rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "0.75rem",
      }}
    >
      <div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            fontWeight: 600,
            color: "var(--color-text-primary)",
          }}
        >
          <span data-testid="passive-lock-badge">{labels.passiveLockBadge}</span>
          {resourceTitle ? <span>— {resourceTitle}</span> : null}
        </div>
        <p
          style={{
            margin: "0.25rem 0 0",
            fontSize: "0.8125rem",
            color: "var(--color-text-secondary)",
          }}
        >
          {labels.passiveLockDescription} (
          <code style={{ fontFamily: "var(--font-mono)" }}>
            {scopePath} :: {verb}
          </code>
          )
        </p>
      </div>
      {onRequestAccess ? (
        <button
          type="button"
          data-testid="permission-guard-request-access-btn"
          onClick={() => onRequestAccess(scopePath, verb)}
          style={{
            minHeight: "44px",
            padding: "0.5rem 0.875rem",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border-strong)",
            backgroundColor: "var(--color-surface-canvas)",
            color: "var(--color-text-primary)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {labels.requestAccessCta}
        </button>
      ) : null}
    </section>
  );
}
