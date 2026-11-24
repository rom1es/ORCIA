import React, { useEffect, useState } from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import { OntologyConceptCard } from "./OntologyConceptCard";
import {
  OntologyTripartiteAndStaleSection,
  type TripartiteAuditDraft,
} from "./OntologyTripartiteAndStaleSection";
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
  auditing?: boolean;
  onProposePromotion?: (concept: UiOntologyConceptView) => void;
  onAuditDocVsCode?: (draft: TripartiteAuditDraft) => Promise<void> | void;
}

const ONTOLOGY_COLUMNS: Exclude<UiOntologyLevel, "4_WORKSPACE">[] = [
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
  auditing = false,
  onProposePromotion,
  onAuditDocVsCode,
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
                {labels.profileDisplayLabels?.[prof] ?? prof}
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
            className="grid grid-cols-1 gap-3 md:grid-cols-2"
          >
            {ONTOLOGY_COLUMNS.map((lvl) => {
              const colConcepts = concepts.filter((c) =>
                lvl === "3_WORKSPACE"
                  ? c.level === "3_WORKSPACE" || c.level === "4_WORKSPACE"
                  : c.level === lvl,
              );
              const columnLabel =
                lvl === "3_WORKSPACE"
                  ? (labels.columns["4_WORKSPACE"] ?? labels.columns["3_WORKSPACE"])
                  : labels.columns[lvl];
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
                  <StatusBadge label={columnLabel} tone="cyan" monospace />
                  {colConcepts.map((c) => (
                    <OntologyConceptCard
                      key={c.conceptKey}
                      concept={c}
                      selectedProfile={selectedProfile}
                      labels={labels}
                      onSelectConcept={setSelectedConcept}
                      onStatusBanner={setStatusBanner}
                      onProposePromotion={onProposePromotion}
                    />
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
              {`${labels.impactPreviewPrefix ?? ""} (${selectedConcept.canonicalTerm}): ${labels.impactTemplatesLabel ?? "Templates"}=${selectedConcept.impactedTemplates.join(", ") || "0"} | ${labels.impactWorkflowsLabel ?? "Workflows"}=${selectedConcept.impactedWorkflows.join(", ") || "0"} | ${labels.impactRunsLabel ?? "Runs"}=${selectedConcept.impactedRuns.join(", ") || "0"}`}
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
        </>
      )}

      <OntologyTripartiteAndStaleSection
        ragQuery={ragQuery}
        onRagQueryChange={setRagQuery}
        filteredEdges={filteredEdges}
        staleAlerts={staleAlerts}
        labels={labels}
        auditing={auditing}
        onAuditDocVsCode={onAuditDocVsCode}
        onReplayAlert={(alert) =>
          setStatusBanner(`${labels.docObsoleteBadgeLabel} -> ${alert.sourceUri}`)
        }
      />
    </section>
  );
}
