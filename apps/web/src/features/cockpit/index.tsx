import {
  ArbitrationTieBreakCard,
  HumanLedAnchorCard,
  UpstreamChallengeRewindModal,
} from "@orcia/ui";
import type { Edge, Node } from "@xyflow/react";
import React, { useState } from "react";
import { useI18n } from "../../i18n";

export function buildCockpitWorkflowPreviewGraph(): {
  nodes: Node[];
  edges: Edge[];
} {
  return {
    nodes: [
      { id: "intent-router", position: { x: 0, y: 0 }, data: { label: "1. Intent Router" } },
      { id: "query-planner", position: { x: 200, y: 0 }, data: { label: "2. Query Planner & Ontology" } },
      { id: "parallel-fan-out", position: { x: 400, y: 0 }, data: { label: "3. Parallel Fan-Out" } },
      { id: "critical-triage", position: { x: 600, y: 0 }, data: { label: "4. Critical Triage & Axioms" } },
      { id: "profile-synthesizer", position: { x: 800, y: 0 }, data: { label: "5. Profile Adaptive Synthesizer" } },
    ],
    edges: [
      { id: "e-intent-planner", source: "intent-router", target: "query-planner" },
      { id: "e-planner-fanout", source: "query-planner", target: "parallel-fan-out" },
      { id: "e-fanout-triage", source: "parallel-fan-out", target: "critical-triage" },
      { id: "e-triage-synthesizer", source: "critical-triage", target: "profile-synthesizer" },
    ],
  };
}

export function CockpitFeaturePanel() {
  const { dictionary } = useI18n();
  const [customAnchorText, setCustomAnchorText] = useState<string | null>(null);
  const [isChallengeModalOpen, setIsChallengeModalOpen] = useState<boolean>(true);
  const anchorText = customAnchorText ?? dictionary.humanAnchor.defaultValue;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div className="orcia-bento-card">
        <HumanLedAnchorCard
          sectionKey="architecture-intent"
          sectionTitle={dictionary.humanAnchor.defaultSectionTitle}
          authorName={dictionary.humanAnchor.defaultAuthorName}
          value={anchorText}
          labels={dictionary.humanAnchor}
          onChange={setCustomAnchorText}
        />
      </div>

      <div className="orcia-bento-card">
        <ArbitrationTieBreakCard
          arbitrationId="arb-fx-rate-001"
          stepKey="frame-architecture-intent"
          questionTitle={dictionary.arbitrationTieBreak.defaultQuestionTitle}
          contextSummary={dictionary.arbitrationTieBreak.defaultContextSummary}
          tieBreakPolicy="PAUSE_AND_ESCALATE"
          options={[
            {
              optionKey: "OPT_A_SPOT_15M",
              title: "Option A — Taux Spot garanti 15 min",
              pros: ["Zéro couverture de change complexe", "Compatible API partenaire v3"],
              cons: ["Fenêtre de validation client réduite à 15 min"],
              siImpact: "1 microservice impacté",
              finopsImpact: "0.02 USD / run",
              recommended: true,
            },
            {
              optionKey: "OPT_B_LOCK_48H",
              title: "Option B — Garantie de taux bloquée 48h",
              pros: ["Confort utilisateur maximal sur 48h"],
              cons: ["Incompatible API partenaire v3", "Risque de change élevé"],
              siImpact: "3 systèmes centraux impactés",
              finopsImpact: "0.18 USD / run",
              recommended: false,
            },
          ]}
          labels={dictionary.arbitrationTieBreak}
        />
      </div>

      <div className="orcia-bento-card">
        <UpstreamChallengeRewindModal
          isOpen={isChallengeModalOpen}
          preview={{
            runId: "run-checkout-001",
            challengerStepKey: "delegate-sub-workflow",
            targetUpstreamStepKey: "frame-architecture-intent",
            challengedSectionKey: "fx_rate_guarantee_rule",
            targetProfileArchetype: "PM_PO",
            translatedSummary:
              "[Traduction Ontologique -> PM_PO] L'exigence de garantie de taux 48h du PRD bloque l'API partenaire v3 (max 15 min). 1 étape amont préservée (0 token reconsommé).",
            invalidatedDownstreamStepKeys: [
              "frame-architecture-intent",
              "delegate-sub-workflow",
              "human-final-signoff",
            ],
            invalidatedArtifactSections: [
              "frame-architecture-intent:fx_rate_guarantee_rule",
              "delegate-sub-workflow:dependent_on_fx_rate_guarantee_rule",
            ],
            invalidatedOntologyAxiomKeys: ["axiom-l1-strategic-asset-immutable-schema"],
            preservedUpstreamStepKeys: ["step-0-intake-validated"],
            upstreamTokensSaved: 1250,
          }}
          labels={dictionary.upstreamChallengeModal}
          onClose={() => setIsChallengeModalOpen(false)}
        />
      </div>
    </div>
  );
}
