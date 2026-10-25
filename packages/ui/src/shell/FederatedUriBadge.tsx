import React from "react";
import type { UiCatalogPermissionKey, UiFederatedScheme } from "./types";

export interface FederatedUriBadgeProps {
  uri: string;
  scheme: UiFederatedScheme;
  sha256Short: string;
  grantedPermissions: UiCatalogPermissionKey[];
  sourceMasked: boolean;
  maskedSourceLabel: string;
  openSourceLabel: string;
  testId?: string;
}

function getSchemeTokenStyle(scheme: UiFederatedScheme): {
  color: string;
  backgroundColor: string;
  borderColor: string;
} {
  switch (scheme) {
    case "git":
    case "jira":
      return {
        color: "var(--color-arbitration-amber)",
        backgroundColor: "var(--color-arbitration-bg)",
        borderColor: "var(--color-arbitration-amber)",
      };
    case "db":
      return {
        color: "var(--color-gate-emerald)",
        backgroundColor: "var(--color-gate-emerald-bg)",
        borderColor: "var(--color-gate-emerald)",
      };
    case "confluence":
      return {
        color: "var(--color-ontology-cyan)",
        backgroundColor: "var(--color-ontology-bg)",
        borderColor: "var(--color-ontology-cyan)",
      };
    case "nexus":
    case "orcia":
    default:
      return {
        color: "var(--color-primary-cobalt)",
        backgroundColor: "var(--color-ontology-bg)",
        borderColor: "var(--color-primary-cobalt)",
      };
  }
}

export function FederatedUriBadge({
  uri,
  scheme,
  sha256Short,
  grantedPermissions,
  sourceMasked,
  maskedSourceLabel,
  openSourceLabel,
  testId = "uri-badge",
}: FederatedUriBadgeProps) {
  const schemeStyle = getSchemeTokenStyle(scheme);

  return (
    <div
      data-testid={testId}
      data-uri-badge="true"
      data-uri-scheme={scheme}
      data-source-masked={String(sourceMasked)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "6px",
        padding: "4px 8px",
        borderRadius: "var(--radius-sm)",
        border: `1px solid ${schemeStyle.borderColor}`,
        backgroundColor: schemeStyle.backgroundColor,
        color: "var(--color-foreground)",
        fontFamily: "var(--font-mono)",
        fontSize: "var(--font-size-mono)",
        lineHeight: 1.35,
      }}
    >
      <span
        style={{
          fontWeight: 700,
          color: schemeStyle.color,
          textTransform: "lowercase",
        }}
      >
        {`${scheme}://`}
      </span>
      <span style={{ wordBreak: "break-all" }}>{uri}</span>
      <span
        style={{
          padding: "1px 5px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: "var(--color-surface-card)",
          border: "1px solid var(--color-border)",
          color: "var(--color-muted-foreground)",
        }}
      >
        {`cas/${sha256Short}`}
      </span>
      <span
        style={{
          padding: "1px 5px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: "var(--color-surface-card)",
          border: "1px solid var(--color-border)",
          color: schemeStyle.color,
          fontWeight: 600,
        }}
      >
        {grantedPermissions.join(" · ")}
      </span>
      <span
        style={{
          padding: "1px 5px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: sourceMasked
            ? "var(--color-arbitration-bg)"
            : "var(--color-gate-emerald-bg)",
          color: sourceMasked ? "var(--color-arbitration-amber)" : "var(--color-gate-emerald)",
          fontWeight: 600,
        }}
      >
        {sourceMasked ? maskedSourceLabel : openSourceLabel}
      </span>
    </div>
  );
}
