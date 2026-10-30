import { StatusBadge } from "@orcia/ui";
import React, { useState } from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function InboxFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const copy = dictionary.modulePages.inbox;
  const inboxCopy = dictionary.inboxAndClaims;
  const isFr = locale === "fr";
  const [scopeFilter, setScopeFilter] = useState<"ALL" | "PERSONAL" | "TEAM">("ALL");

  return (
    <div className="orcia-bento-card" data-testid="inbox-feature-panel">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px",
          marginBottom: "14px",
          flexWrap: "wrap",
        }}
      >
        <span>{copy.subtitle}</span>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <StatusBadge
            testId="inbox-amber-counter"
            label={`${inboxCopy.amberCounterPrefix} 0`}
            tone="amber"
            pill
          />
          <StatusBadge
            testId="inbox-uri-badge"
            label={copy.uriBadgeExample}
            tone="cobalt"
            monospace
          />
        </div>
      </div>

      <div
        role="group"
        aria-label="Scope filters"
        style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}
      >
        {(["ALL", "PERSONAL", "TEAM"] as const).map((scopeKey) => {
          const label =
            scopeKey === "ALL"
              ? inboxCopy.filterAllLabel
              : scopeKey === "PERSONAL"
                ? inboxCopy.filterPersonalLabel
                : inboxCopy.filterTeamLabel;
          const active = scopeFilter === scopeKey;
          return (
            <button
              key={scopeKey}
              type="button"
              data-testid={`inbox-filter-${scopeKey.toLowerCase()}`}
              onClick={() => setScopeFilter(scopeKey)}
              style={{
                padding: "4px 12px",
                borderRadius: "var(--radius-full)",
                border: active
                  ? "1px solid var(--color-primary-cobalt)"
                  : "1px solid var(--color-border)",
                backgroundColor: active
                  ? "var(--color-sidebar-active-bg)"
                  : "var(--color-surface-card)",
                color: active ? "var(--color-primary-cobalt)" : "var(--color-foreground)",
                fontFamily: "var(--font-sans)",
                fontSize: "var(--font-size-mono)",
                fontWeight: active ? 600 : 500,
                cursor: "pointer",
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div
        data-testid="inbox-empty-state"
        style={{
          padding: "20px",
          borderRadius: "var(--radius-md)",
          border: "1px dashed var(--color-border)",
          backgroundColor: "var(--color-surface-bg)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <strong>
            {isFr
              ? "Aucune notification ni demande d'arbitrage en attente"
              : "No pending notification or arbitration request"}
          </strong>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {isFr
              ? "Les tâches d'arbitrage humain, signatures d'ancrage et Gates adaptatives apparaîtront ici lorsqu'un Workflow Run les déclenchera."
              : "Human arbitration tasks, anchor signatures, and adaptive Gates will appear here when triggered by an active Workflow Run."}
          </p>
        </div>
        <button
          type="button"
          data-testid="inbox-go-cockpit-btn"
          onClick={() => navigateToRoute("/cockpit")}
          style={{
            padding: "7px 14px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {isFr ? "Retour au Cockpit" : "Back to Cockpit"}
        </button>
      </div>
    </div>
  );
}
