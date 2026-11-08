import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";
import { StatusBadge } from "../primitives/StatusBadge";
import type {
  UiOntologyConceptView,
  UiOntologyExplorerLabels,
  UiOntologyLevel,
  UiStaleAlertView,
  UiTripartiteEdgeView,
} from "./types";

export interface OntologyAndKbExplorerPanelProps {
  concepts: UiOntologyConceptView[];
  tripartiteEdges: UiTripartiteEdgeView[];
  staleAlerts: UiStaleAlertView[];
  labels: UiOntologyExplorerLabels;
}

const ONTOLOGY_COLUMNS: UiOntologyLevel[] = [
  "1_ENTERPRISE",
  "2_DOMAIN",
  "3_TEAM",
  "3_WORKSPACE",
  "4_RUN_EPHEMERAL",
];

const PROFILE_KEYS = [
  "EXECUTIVE",
  "PM_BUSINESS",
  "ARCHITECT",
  "TECH_LEAD",
  "DEVELOPER",
  "SECOPS",
] as const;

export function OntologyAndKbExplorerPanel({
  concepts,
  tripartiteEdges,
  staleAlerts,
  labels,
}: OntologyAndKbExplorerPanelProps) {
  const [selectedProfile, setSelectedProfile] = useState<string>("TECH_LEAD");
  const [selectedConcept, setSelectedConcept] = useState<UiOntologyConceptView | null>(
    concepts[0] ?? null,
  );
  const [statusBanner, setStatusBanner] = useState<string | null>(null);
  const [ragQuery, setRagQuery] = useState<string>("");

  useEffect(() => {
    setSelectedConcept((prev) => {
      if (prev && concepts.some((c) => c.conceptKey === prev.conceptKey)) {
        return concepts.find((c) => c.conceptKey === prev.conceptKey) ?? null;
      }
      return concepts[0] ?? null;
    });
  }, [concepts]);

  const normalizedQuery = ragQuery.trim().toLowerCase();
  const filteredEdges = normalizedQuery
    ? tripartiteEdges.filter(
        (e) =>
          e.sourceUri.toLowerCase().includes(normalizedQuery) ||
          e.targetUri.toLowerCase().includes(normalizedQuery) ||
          e.relationType.toLowerCase().includes(normalizedQuery),
      )
    : tripartiteEdges;

  return (
    <section
      data-testid="ontology-kb-explorer-panel"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div>
          <strong style={{ fontSize: "15px" }}>{labels.panelTitle}</strong>
          <p
            style={{
              margin: "4px 0 0 0",
              color: "var(--color-muted-foreground)",
              fontSize: "var(--font-size-body)",
            }}
          >
            {labels.panelSubtitle}
          </p>
        </div>

        <label
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "var(--font-size-body)",
          }}
        >
          <span>{labels.profileSelectorLabel}</span>
          <select
            data-testid="ontology-profile-selector"
            value={selectedProfile}
            onChange={(e) => setSelectedProfile(e.target.value)}
            style={{
              backgroundColor: "var(--color-surface-card)",
              color: "var(--color-foreground)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 8px",
              fontFamily: "var(--font-mono)",
              fontSize: "var(--font-size-mono)",
            }}
          >
            {PROFILE_KEYS.map((prof) => (
              <option key={prof} value={prof}>
                {prof}
              </option>
            ))}
          </select>
        </label>
      </div>

      {concepts.length === 0 ? (
        <div
          data-testid="ontology-kb-empty-state"
          style={{
            padding: "20px",
            borderRadius: "var(--radius-md)",
            border: "1px dashed var(--color-border)",
            color: "var(--color-muted-foreground)",
            textAlign: "center",
            fontSize: "var(--font-size-body)",
          }}
        >
          {labels.emptyStateMessage}
        </div>
      ) : (
        <>
          <div
            data-testid="ontology-columns-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "12px",
            }}
          >
            {ONTOLOGY_COLUMNS.map((lvl) => {
              const colConcepts = concepts.filter((c) => c.level === lvl);
              return (
                <div
                  key={lvl}
                  data-testid={`ontology-column-${lvl}`}
                  style={{
                    padding: "10px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border)",
                    backgroundColor: "var(--color-surface-hover)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <StatusBadge label={labels.columns[lvl]} tone="cyan" monospace />
                  {colConcepts.map((c) => (
                    <div
                      key={c.conceptKey}
                      data-testid={`ontology-card-${c.conceptKey}`}
                      style={{
                        padding: "8px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-ontology-cyan)",
                        backgroundColor: "var(--color-ontology-bg)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "6px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "6px" }}>
                        <strong style={{ fontSize: "13px" }}>{c.canonicalTerm}</strong>
                        {c.immutable && <StatusBadge label="IMMUTABLE" tone="crimson" monospace />}
                      </div>
                      <span
                        data-testid={`ontology-translation-${c.conceptKey}`}
                        style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}
                      >
                        {c.profileTranslations[selectedProfile] ?? c.definitionText}
                      </span>
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                        <button
                          type="button"
                          data-testid={`what-if-btn-${c.conceptKey}`}
                          onClick={() => {
                            setSelectedConcept(c);
                            setStatusBanner(
                              c.immutable
                                ? labels.immutableConflictBanner
                                : `${labels.promotedBannerPrefix} ${c.canonicalTerm} (Templates: ${c.impactedTemplates.length}, Workflows: ${c.impactedWorkflows.length}, Runs: ${c.impactedRuns.length})`,
                            );
                          }}
                          style={{
                            backgroundColor: "var(--color-ontology-cyan)",
                            color: "var(--color-primary-foreground)",
                            border: "none",
                            borderRadius: "var(--radius-sm)",
                            padding: "4px 8px",
                            fontSize: "11px",
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          {labels.whatIfButtonLabel}
                        </button>
                        {!c.immutable && (
                          <button
                            type="button"
                            data-testid={`promote-btn-${c.conceptKey}`}
                            onClick={() =>
                              setStatusBanner(
                                `${labels.promoteButtonLabel} : ${c.canonicalTerm} -> 3_WORKSPACE`,
                              )
                            }
                            style={{
                              backgroundColor: "var(--color-surface-card)",
                              color: "var(--color-foreground)",
                              border: "1px solid var(--color-ontology-cyan)",
                              borderRadius: "var(--radius-sm)",
                              padding: "4px 8px",
                              fontSize: "11px",
                              fontWeight: 600,
                              cursor: "pointer",
                            }}
                          >
                            {labels.promoteButtonLabel}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>

          {selectedConcept && (
            <div
              data-testid="what-if-impact-drawer"
              style={{
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-ontology-cyan)",
                backgroundColor: "var(--color-ontology-bg)",
                fontFamily: "var(--font-mono)",
                fontSize: "var(--font-size-mono)",
              }}
            >
              What-If ({selectedConcept.canonicalTerm}): Templates=
              {selectedConcept.impactedTemplates.join(", ") || "0"} | Workflows=
              {selectedConcept.impactedWorkflows.join(", ") || "0"} | Runs=
              {selectedConcept.impactedRuns.join(", ") || "0"}
            </div>
          )}

          {statusBanner && (
            <div
              data-testid="ontology-action-banner"
              style={{
                padding: "8px 10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-ontology-cyan)",
                fontFamily: "var(--font-mono)",
                fontSize: "var(--font-size-mono)",
              }}
            >
              {statusBanner}
            </div>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "12px",
            }}
          >
            <div
              data-testid="tripartite-graph-section"
              style={{
                padding: "10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <strong>
                {labels.tripartiteTitle} · {labels.hybridRagTitle}
              </strong>
              <input
                type="search"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="hybrid-rag-search-input"
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                placeholder={labels.hybridRagSearchPlaceholder}
                style={{
                  padding: "6px 8px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface-card)",
                  color: "var(--color-foreground)",
                }}
              />
              {filteredEdges.map((edge) => (
                <div
                  key={edge.edgeKey}
                  data-testid={`tripartite-edge-${edge.edgeKey}`}
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--font-size-mono)",
                    color: "var(--color-muted-foreground)",
                  }}
                >
                  {edge.sourceUri} —[{edge.relationType}]→ {edge.targetUri}
                </div>
              ))}
            </div>

            <div
              data-testid="stale-alerts-section"
              style={{
                padding: "10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-stale-crimson)",
                backgroundColor: "var(--color-stale-bg)",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
                <strong>{labels.staleAlertsTitle}</strong>
                <StatusBadge label={labels.docObsoleteBadgeLabel} tone="crimson" monospace />
              </div>
              {staleAlerts.map((alert) => (
                <div
                  key={alert.alertKey}
                  data-testid={`stale-alert-${alert.alertKey}`}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "8px",
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--font-size-mono)",
                    color: "var(--color-stale-crimson)",
                  }}
                >
                  <span>
                    {alert.diagnosticMarker} {alert.sourceUri} (Jira:{" "}
                    {alert.justifyingJiraKey ?? "TTL"}, Runs: {alert.impactedRunIds.join(", ")})
                  </span>
                  <button
                    type="button"
                    data-testid={`stale-alert-replay-btn-${alert.alertKey}`}
                    onClick={() =>
                      setStatusBanner(`${labels.docObsoleteBadgeLabel} -> ${alert.sourceUri}`)
                    }
                    style={{
                      backgroundColor: "var(--color-surface-card)",
                      color: "var(--color-stale-crimson)",
                      border: "1px solid var(--color-stale-crimson)",
                      borderRadius: "var(--radius-sm)",
                      padding: "2px 6px",
                      fontSize: "10px",
                      cursor: "pointer",
                    }}
                  >
                    <OrciaIcon name="regenerate" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
