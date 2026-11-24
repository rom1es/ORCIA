import React from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import type { UiOntologyConceptView, UiOntologyExplorerLabels } from "./types";

export interface OntologyConceptCardProps {
  concept: UiOntologyConceptView;
  selectedProfile: string;
  labels: UiOntologyExplorerLabels;
  onSelectConcept: (concept: UiOntologyConceptView) => void;
  onStatusBanner: (banner: string) => void;
  onProposePromotion?: (concept: UiOntologyConceptView) => void;
}

export function OntologyConceptCard({
  concept,
  selectedProfile,
  labels,
  onSelectConcept,
  onStatusBanner,
  onProposePromotion,
}: OntologyConceptCardProps): React.ReactElement {
  return (
    <div
      data-testid={`ontology-card-${concept.conceptKey}`}
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
        <strong style={{ fontSize: "13px" }}>{concept.canonicalTerm}</strong>
        {concept.immutable && labels.immutableRuleBadgeLabel ? (
          <StatusBadge label={labels.immutableRuleBadgeLabel} tone="crimson" />
        ) : null}
      </div>
      <span
        data-testid={`ontology-translation-${concept.conceptKey}`}
        style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}
      >
        {concept.profileTranslations[selectedProfile] ?? concept.definitionText}
      </span>
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        <button
          type="button"
          data-testid={`what-if-btn-${concept.conceptKey}`}
          onClick={() => {
            onSelectConcept(concept);
            onStatusBanner(
              concept.immutable
                ? labels.immutableConflictBanner
                : `${labels.promotedBannerPrefix} ${concept.canonicalTerm} (${labels.impactTemplatesLabel ?? "Templates"}: ${concept.impactedTemplates.length}, ${labels.impactWorkflowsLabel ?? "Workflows"}: ${concept.impactedWorkflows.length}, ${labels.impactRunsLabel ?? "Runs"}: ${concept.impactedRuns.length})`,
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
        {!concept.immutable &&
          concept.level !== "1_ENTERPRISE" &&
          (concept.canProposePromotion ?? true) && (
            <button
              type="button"
              data-testid={`promote-btn-${concept.conceptKey}`}
              onClick={() => {
                if (onProposePromotion) {
                  onProposePromotion(concept);
                }
                onStatusBanner(
                  `${labels.promoteButtonLabel} : ${concept.canonicalTerm} -> ${concept.nextPromotionLevel ?? "3_WORKSPACE"}`,
                );
              }}
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
  );
}
