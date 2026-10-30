import React, { useState } from "react";
import {
  ChunkValidationCard,
  CognitiveReviewBriefingGrid,
  type UiChunkDecisionAction,
  type UiChunkValidationItem,
} from "@orcia/ui";
import { usePersonaContext } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

const INITIAL_CHUNKS: UiChunkValidationItem[] = [
  {
    chunkKey: "section-1",
    sectionTitle: "1. Architecture & Périmètre Sécurité",
    sectionIndex: 0,
    contentMarkdown:
      "Isolation hors processus des Gates Déterministes et orthogonalité des familles LLM.",
    wordCount: 620,
    humanAuthoredRequired: true,
    status: "PENDING",
  },
  {
    chunkKey: "section-2",
    sectionTitle: "2. Contraintes d'Ontologie & KBs",
    sectionIndex: 1,
    contentMarkdown:
      "Aucun conflit détecté sur les axiomes N1..N4 et zéro alerte [STALE_WARNING].",
    wordCount: 540,
    humanAuthoredRequired: false,
    status: "PENDING",
  },
];

export function GatesFeaturePanel() {
  const { dictionary } = useI18n();
  const {
    activePersona,
    brokerActionBanner,
    triggerPermissionDeniedStep,
    triggerConfusedDeputyCheck,
  } = usePersonaContext();

  const [hypothesesInspected, setHypothesesInspected] =
    useState<boolean>(false);
  const [chunks, setChunks] =
    useState<UiChunkValidationItem[]>(INITIAL_CHUNKS);
  const [gateApprovedBanner, setGateApprovedBanner] = useState<string | null>(
    null
  );

  const isReadOnly = activePersona === "claire";
  const retainedHypotheses = [
    "L'artefact respecte les invariants du PRD (Step 1) et de l'Architecture (Step 2).",
    "Les données PII ont été pseudonymisées via PiiReversibleScrubber.",
  ];

  const handleDecideChunk = (
    chunkKey: string,
    action: UiChunkDecisionAction,
    coEditedContent?: string
  ) => {
    setChunks((prev) =>
      prev.map((item) => {
        if (item.chunkKey !== chunkKey) {
          return item;
        }
        if (action === "APPROVE") {
          return { ...item, status: "APPROVED" };
        }
        if (action === "CO_EDIT") {
          return {
            ...item,
            status: "CO_EDITED",
            contentMarkdown: coEditedContent ?? item.contentMarkdown,
          };
        }
        return { ...item, status: "CHALLENGED" };
      })
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <CognitiveReviewBriefingGrid
        executiveSummary="Synthèse consolidée par la Lentille 5 (Agentic Gate >= 0.85, 0 conflit d'ontologie)."
        keyElementsAndTransverse={[
          "Alignement Step 1 (PRD) : PASS",
          "Fact Verification (Ontologie N1..N4) : 0.94 >= 0.80",
        ]}
        decisionsTaken={[
          "Activation de la politique risk_or_exception_based",
          "Validation section par section requise sur l'ancre humaine",
        ]}
        retainedHypotheses={retainedHypotheses}
        hypothesesInspected={hypothesesInspected}
        onInspectHypotheses={() => setHypothesesInspected(true)}
        readOnly={isReadOnly}
        labels={dictionary.humanGates.briefing}
      />

      <ChunkValidationCard
        chunks={chunks}
        totalWordCount={chunks.reduce((acc, c) => acc + c.wordCount, 0)}
        reviewDurationMs={8000}
        hypothesesInspected={hypothesesInspected}
        retainedHypotheses={retainedHypotheses}
        readOnly={isReadOnly}
        onDecideChunk={handleDecideChunk}
        onFinalizeGate={({ fastApprovalWarning }) =>
          setGateApprovedBanner(
            fastApprovalWarning
              ? "PASS (fast_approval_warning: true)"
              : "PASS (fast_approval_warning: false)"
          )
        }
        labels={dictionary.humanGates.chunkValidation}
      />

      {gateApprovedBanner && (
        <div
          data-testid="human-gate-finalized-banner"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-gate-emerald-bg)",
            color: "var(--color-gate-emerald)",
            border: "1px solid var(--color-gate-emerald)",
          }}
        >
          {gateApprovedBanner}
        </div>
      )}

      <section
        data-testid="permission-broker-simulator-panel"
        className="orcia-bento-card"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        <div>
          <strong style={{ fontSize: "15px" }}>
            {dictionary.permissionBroker.simulatorTitle}
          </strong>
          <p
            style={{
              margin: "4px 0 0 0",
              color: "var(--color-muted-foreground)",
              fontSize: "var(--font-size-body)",
            }}
          >
            {dictionary.permissionBroker.simulatorSubtitle}
          </p>
        </div>

        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="simulate-permission-denied-git-btn"
            onClick={() => triggerPermissionDeniedStep("git")}
            style={{
              backgroundColor: "var(--color-arbitration-amber)",
              color: "var(--color-primary-foreground)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              padding: "7px 12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {dictionary.permissionBroker.simulateGitDenialLabel}
          </button>

          <button
            type="button"
            data-testid="simulate-permission-denied-confluence-btn"
            onClick={() => triggerPermissionDeniedStep("confluence")}
            style={{
              backgroundColor: "var(--color-surface-hover)",
              color: "var(--color-foreground)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "7px 12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {dictionary.permissionBroker.simulateConfluenceDenialLabel}
          </button>

          <button
            type="button"
            data-testid="simulate-permission-denied-jira-btn"
            onClick={() => triggerPermissionDeniedStep("jira")}
            style={{
              backgroundColor: "var(--color-surface-hover)",
              color: "var(--color-foreground)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "7px 12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {dictionary.permissionBroker.simulateJiraDenialLabel}
          </button>

          <button
            type="button"
            data-testid="simulate-confused-deputy-btn"
            onClick={triggerConfusedDeputyCheck}
            style={{
              backgroundColor: "var(--color-stale-bg)",
              color: "var(--color-stale-crimson)",
              border: "1px solid var(--color-stale-crimson)",
              borderRadius: "var(--radius-sm)",
              padding: "7px 12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {dictionary.permissionBroker.simulateConfusedDeputyLabel}
          </button>
        </div>

        {brokerActionBanner && (
          <div
            data-testid="permission-broker-action-banner"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--font-size-mono)",
              padding: "8px 10px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-arbitration-bg)",
              border: "1px solid var(--color-arbitration-amber)",
              wordBreak: "break-all",
            }}
          >
            {brokerActionBanner}
          </div>
        )}
      </section>
    </div>
  );
}
