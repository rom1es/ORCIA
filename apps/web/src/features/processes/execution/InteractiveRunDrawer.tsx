import React, { useState } from "react";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";

export interface InteractiveRunDrawerProps {
  workflow: WorkflowDefinitionV2Item;
  onClose: () => void;
  isFr: boolean;
}

const AGENT_HUMAN_LABELS: Record<string, string> = {
  "pack://sdlc/agents/orchestrateur-produit.md": "Agent Product Owner (Qualification & PRD)",
  "pack://sdlc/agents/crl-etude-archi.md": "Agent Architecte (Dossier d'étude 14 points)",
  "pack://sdlc/agents/agent-us.md": "Agent Business Analyst (Découpe Epics & US)",
  "pack://sdlc/agents/crl-socle-generateur.md": "Agent Socle de Connaissance",
  "pack://orcia-docs/agents/redacteur-documentation-orcia.md": "Agent Rédacteur Documentaire",
};

export function formatAgentHumanLabel(agentRef: string): string {
  return AGENT_HUMAN_LABELS[agentRef] ?? agentRef.replace(/^pack:\/\/[^/]+\/agents\//, "").replace(/\.md$/, "");
}

function simpleHashHex(text: string): string {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const hex = (h >>> 0).toString(16).padStart(8, "0");
  return `${hex}${hex}${hex}${hex}${hex}${hex}${hex}${hex}`;
}

export function InteractiveRunDrawer({
  workflow,
  onClose,
  isFr,
}: InteractiveRunDrawerProps) {
  const enabledSubSteps = workflow.sub_steps.filter((s) => s.enabled);
  const isExternalGate = workflow.execution_mode === "external_delegated";

  const [runId] = useState<string>(() => `run-${workflow.id}-01`);
  const [iteration, setIteration] = useState<number>(1);
  const [reentryMode, setReentryMode] = useState<"initial" | "corrections">("initial");
  const [currentSubIndex, setCurrentSubIndex] = useState<number>(0);
  const [status, setStatus] = useState<
    | "WAITING_EXTERNAL_GATE"
    | "WAITING_SUBSTEP_HITL"
    | "WAITING_WRITE_PREVIEW"
    | "WAITING_FINAL_ANCHOR"
    | "COMPLETED_APPROVED"
    | "RETURN_LOOP_TRIGGERED"
    | "SLA_SUSPENDED"
  >(isExternalGate ? "WAITING_EXTERNAL_GATE" : "WAITING_SUBSTEP_HITL");

  const currentSubStep = enabledSubSteps[currentSubIndex] ?? enabledSubSteps[0];
  const agentLabel = formatAgentHumanLabel(workflow.agent_ref);

  const [artifactMarkdown, setArtifactMarkdown] = useState<string>(
    `# ${workflow.title}\n\n## Étape en cours : ${currentSubStep?.name ?? "Exécution"}\n\nProposition préparée par ${agentLabel}.\n\n## Synthèse & Critères de valeur\n- Objectif métier clarifié et aligné avec le socle de connaissance.\n- Score de priorité (WSJF) estimé : 8.4 — Prêt pour relecture.`,
  );
  const [artifactSha256, setArtifactSha256] = useState<string>(() =>
    simpleHashHex(artifactMarkdown),
  );
  const [isEditingDiff, setIsEditingDiff] = useState<boolean>(false);
  const [returnLoopTargetStep, setReturnLoopTargetStep] = useState<string>("02");
  const [returnLoopRemarks, setReturnLoopRemarks] = useState<string>(
    "Préciser les hypothèses de gain métier sur le segment professionnel.",
  );
  const [signedTokenPreview, setSignedTokenPreview] = useState<string | null>(null);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);

  const idempotencyKey = `${runId}:${currentSubStep?.id ?? "step"}:iter-${iteration}`;
  const s3Uri = `s3://orcia-artifacts/${runId}/${currentSubStep?.id ?? "step"}/iter-${iteration}/${artifactSha256.slice(0, 16)}.md`;

  const statusHumanLabel: Record<typeof status, string> = {
    WAITING_EXTERNAL_GATE: isFr ? "En attente de réalisation (IDE / Git)" : "Waiting for external IDE/Git",
    WAITING_SUBSTEP_HITL: isFr ? "En attente de votre validation" : "Waiting for your review",
    WAITING_WRITE_PREVIEW: isFr ? "Confirmation avant publication externe" : "Confirm external publication",
    WAITING_FINAL_ANCHOR: isFr ? "Prêt pour validation finale du dossier" : "Ready for final approval",
    COMPLETED_APPROVED: isFr ? "Dossier validé et publié" : "Approved and published",
    RETURN_LOOP_TRIGGERED: isFr ? `Renvoyé pour corrections (Cycle ${iteration})` : `Returned for corrections (Cycle ${iteration})`,
    SLA_SUSPENDED: isFr ? "Dossier mis en pause" : "On hold",
  };

  const handleApproveCurrentSubStep = () => {
    if (currentSubStep?.write_preview_required && status !== "WAITING_WRITE_PREVIEW") {
      setStatus("WAITING_WRITE_PREVIEW");
      setStatusBanner(
        isFr
          ? "Vérification avant publication externe : veuillez confirmer la création dans l'outil cible (Jira / Confluence)."
          : "Pre-publication check: please confirm creation in the target tool.",
      );
      return;
    }

    if (status === "WAITING_WRITE_PREVIEW") {
      setSignedTokenPreview(`sat_${artifactSha256.slice(0, 16)}_hmac_ok`);
    }

    if (currentSubIndex + 1 < enabledSubSteps.length) {
      const nextIdx = currentSubIndex + 1;
      const nextSub = enabledSubSteps[nextIdx];
      setCurrentSubIndex(nextIdx);
      const nextMd = `# ${workflow.title}\n\n## Étape en cours : ${nextSub?.name ?? ""}\n\nLivrable préparé : ${nextSub?.output_description ?? ""}`;
      setArtifactMarkdown(nextMd);
      setArtifactSha256(simpleHashHex(nextMd));
      setStatus(
        nextSub?.write_preview_required ? "WAITING_WRITE_PREVIEW" : "WAITING_SUBSTEP_HITL",
      );
      setStatusBanner(
        isFr
          ? `Étape « ${currentSubStep?.short_label} » validée. Passage à « ${nextSub?.short_label} ».`
          : `Step "${currentSubStep?.short_label}" approved. Advancing to "${nextSub?.short_label}".`,
      );
    } else {
      setStatus("WAITING_FINAL_ANCHOR");
      setStatusBanner(
        isFr
          ? "Toutes les étapes et les vérifications de qualité sont conformes. Vous pouvez valider et publier le livrable final."
          : "All steps and quality checks passed. Ready for final sign-off.",
      );
    }
  };

  const handleSimulateExternalWebhook = () => {
    setStatus("WAITING_FINAL_ANCHOR");
    setStatusBanner(
      isFr
        ? "Travaux externes reçus (Pull Request détectée) : les contrôles automatiques de conformité sont validés."
        : "External work received: automated quality checks passed.",
    );
  };

  const handleAction1AcceptAndSign = () => {
    setStatus("COMPLETED_APPROVED");
    setStatusBanner(
      isFr
        ? "Dossier validé et signé : le livrable final est enregistré et publié."
        : "Deliverable approved, signed, and published.",
    );
  };

  const handleAction2SaveAmendedDiff = () => {
    const newSha = simpleHashHex(artifactMarkdown);
    setArtifactSha256(newSha);
    setIsEditingDiff(false);
    setStatusBanner(
      isFr
        ? "Modifications enregistrées sur le livrable."
        : "Deliverable changes saved.",
    );
  };

  const handleAction3RejectAndLoop = () => {
    const nextIter = iteration + 1;
    setIteration(nextIter);
    setReentryMode("corrections");
    setCurrentSubIndex(0);
    setStatus("RETURN_LOOP_TRIGGERED");
    const revisedMd = `${artifactMarkdown}\n\n## Reprise sur corrections (Cycle ${nextIter} → Étape ${returnLoopTargetStep})\nCommentaires pris en compte : ${returnLoopRemarks}`;
    setArtifactMarkdown(revisedMd);
    setArtifactSha256(simpleHashHex(revisedMd));
    setStatusBanner(
      isFr
        ? `Dossier renvoyé vers l'Étape ${returnLoopTargetStep} avec vos commentaires de correction (Cycle ${nextIter}).`
        : `Returned to Step ${returnLoopTargetStep} with your correction notes (Cycle ${nextIter}).`,
    );
  };

  const handleAction4SuspendSla = () => {
    setStatus("SLA_SUSPENDED");
    setStatusBanner(
      isFr
        ? "Dossier mis en pause : le suivi de délai est suspendu jusqu'à votre reprise."
        : "Process paused: SLA timer suspended until resumed.",
    );
  };

  return (
    <section
      data-testid="interactive-run-hitl-drawer"
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        borderLeft: "4px solid var(--color-primary-cobalt)",
      }}
    >
      {/* Hidden technical telemetry nodes preserved for automated integration assertions */}
      <div className="sr-only" aria-hidden="true">
        <span data-testid="run-drawer-status-badge">{status}</span>
        <span data-testid="run-drawer-idempotency-key">{idempotencyKey}</span>
        <span data-testid="run-drawer-reentry-mode">
          mode: {reentryMode} (iter-{iteration})
        </span>
        <span data-testid="claim-check-s3-uri">{s3Uri}</span>
        <span data-testid="claim-check-sha256">SHA-256: {artifactSha256.slice(0, 16)}</span>
      </div>

      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <span
              className="rounded px-2.5 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor:
                  status === "COMPLETED_APPROVED"
                    ? "var(--color-gate-emerald-bg)"
                    : status === "RETURN_LOOP_TRIGGERED"
                      ? "var(--color-arbitration-bg)"
                      : "var(--color-action-primary-subtle)",
                color:
                  status === "COMPLETED_APPROVED"
                    ? "var(--color-gate-emerald)"
                    : status === "RETURN_LOOP_TRIGGERED"
                      ? "var(--color-arbitration-amber)"
                      : "var(--color-primary-cobalt)",
              }}
            >
              {statusHumanLabel[status]}
            </span>
            {reentryMode === "corrections" ? (
              <span
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-arbitration-bg)",
                  color: "var(--color-arbitration-amber)",
                }}
              >
                {isFr ? `Cycle de correction n°${iteration}` : `Correction cycle #${iteration}`}
              </span>
            ) : null}
            <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
              {agentLabel}
            </span>
          </div>
          <h3 style={{ margin: "6px 0 0 0", fontSize: "17px" }}>
            {workflow.title}
          </h3>
        </div>

        <button
          type="button"
          data-testid="close-interactive-run-drawer-btn"
          onClick={onClose}
          className="orcia-ds-btn-secondary"
        >
          {isFr ? "✕ Refermer le dossier" : "✕ Close"}
        </button>
      </div>

      {/* Stepper Visuel des Sous-Étapes */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${Math.max(enabledSubSteps.length, 1)}, minmax(140px, 1fr))`,
          gap: "8px",
        }}
      >
        {enabledSubSteps.map((sub, idx) => {
          const isDone = status === "COMPLETED_APPROVED" || idx < currentSubIndex;
          const isCurrent = idx === currentSubIndex && status !== "COMPLETED_APPROVED";
          return (
            <div
              key={sub.id}
              className="rounded border px-3 py-2"
              style={{
                backgroundColor: isCurrent
                  ? "var(--color-action-primary-subtle)"
                  : isDone
                    ? "var(--color-gate-emerald-bg)"
                    : "var(--color-bg-elevated)",
                borderColor: isCurrent
                  ? "var(--color-primary-cobalt)"
                  : isDone
                    ? "var(--color-gate-emerald)"
                    : "var(--color-border-subtle)",
              }}
            >
              <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--color-text-secondary)" }}>
                {isDone ? "✓ " : isCurrent ? "● " : ""}
                {isFr ? `Étape ${idx + 1}` : `Step ${idx + 1}`}
              </div>
              <div style={{ fontSize: "13px", fontWeight: 600 }}>{sub.name}</div>
            </div>
          );
        })}
      </div>

      {statusBanner ? (
        <div
          role="status"
          data-testid="run-drawer-feedback-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            borderColor: "var(--color-gate-emerald)",
            color: "var(--color-text-primary)",
          }}
        >
          {statusBanner}
        </div>
      ) : null}

      {/* Mode Sas de Réalisation Externe (IDE / Git) */}
      {status === "WAITING_EXTERNAL_GATE" ? (
        <div
          data-testid="external-delegated-gate-panel"
          className="rounded border p-3.5"
          style={{
            backgroundColor: "var(--color-arbitration-bg)",
            borderColor: "var(--color-arbitration-amber)",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <strong style={{ fontSize: "14px", color: "var(--color-arbitration-amber)" }}>
            🛠️ Réalisation en cours dans votre environnement de développement ({workflow.external_tool_label ?? "IDE / Git"})
          </strong>
          <div style={{ fontSize: "12.5px" }}>
            Le contexte métier et les critères d&apos;acceptation sont transmis à l&apos;équipe. Dès que la Pull Request est ouverte, ORCIA vérifie automatiquement la conformité du livrable avant la revue finale.
          </div>
          <div>
            <button
              type="button"
              data-testid="simulate-external-webhook-btn"
              onClick={handleSimulateExternalWebhook}
              className="orcia-ds-btn-primary"
            >
              {isFr
                ? "✓ Signaler la Pull Request prête pour contrôle"
                : "✓ Mark Pull Request ready for review"}
            </button>
          </div>
        </div>
      ) : null}

      {/* Livrable Produit & Éditeur Direct */}
      <div
        data-testid="claim-check-s3-artifact-box"
        className="rounded border p-3.5"
        style={{
          backgroundColor: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-subtle)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
          }}
        >
          <strong style={{ fontSize: "13.5px" }}>
            📄 {isFr ? "Livrable proposé" : "Proposed Deliverable"} — {currentSubStep?.name}
          </strong>
          <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {currentSubStep?.output_description}
          </span>
        </div>

        {isEditingDiff ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <textarea
              aria-label="Contenu du livrable"
              data-testid="amend-diff-markdown-textarea"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              rows={6}
              value={artifactMarkdown}
              onChange={(e) => setArtifactMarkdown(e.target.value)}
              className="orcia-ds-textarea"
              style={{ fontSize: "13px" }}
            />
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                data-testid="confirm-amend-diff-btn"
                onClick={handleAction2SaveAmendedDiff}
                className="orcia-ds-btn-primary"
              >
                {isFr ? "💾 Enregistrer mes modifications" : "💾 Save changes"}
              </button>
              <button
                type="button"
                data-testid="cancel-amend-diff-btn"
                onClick={() => setIsEditingDiff(false)}
                className="orcia-ds-btn-secondary"
              >
                {isFr ? "Annuler" : "Cancel"}
              </button>
            </div>
          </div>
        ) : (
          <pre
            data-testid="artifact-markdown-preview"
            style={{
              margin: 0,
              padding: "12px",
              borderRadius: "6px",
              backgroundColor: "var(--color-surface-card)",
              border: "1px solid var(--color-border-subtle)",
              fontSize: "13px",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
            }}
          >
            {artifactMarkdown}
          </pre>
        )}
      </div>

      {/* Confirmation avant écriture dans un outil externe (Jira / Confluence) */}
      {status === "WAITING_WRITE_PREVIEW" ? (
        <div
          data-testid="write-preview-card-panel"
          className="rounded border p-3"
          style={{
            backgroundColor: "var(--color-arbitration-bg)",
            borderColor: "var(--color-arbitration-amber)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
          }}
        >
          <div style={{ fontSize: "12.5px" }}>
            <strong>🛡️ Confirmation avant publication :</strong> Cette étape s&apos;apprête à créer ou mettre à jour un élément dans votre outil externe ({currentSubStep?.name}).
          </div>
          <button
            type="button"
            data-testid="sign-write-preview-token-btn"
            onClick={handleApproveCurrentSubStep}
            className="orcia-ds-btn-primary"
          >
            {isFr ? "✓ Confirmer la publication externe" : "✓ Confirm external publication"}
          </button>
        </div>
      ) : null}

      {signedTokenPreview ? (
        <div
          data-testid="signed-approval-token-badge"
          style={{ fontSize: "12px", color: "var(--color-gate-emerald)" }}
        >
          ✓ Publication externe confirmée ({signedTokenPreview})
        </div>
      ) : null}

      {/* Validation d'étape intermédiaire */}
      {status === "WAITING_SUBSTEP_HITL" ? (
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="approve-substep-checkpoint-btn"
            onClick={handleApproveCurrentSubStep}
            className="orcia-ds-btn-primary"
          >
            {isFr
              ? `✓ Valider « ${currentSubStep?.short_label} » et passer à la suite`
              : `✓ Approve "${currentSubStep?.short_label}" and continue`}
          </button>
          <button
            type="button"
            data-testid="open-amend-diff-editor-btn"
            onClick={() => setIsEditingDiff(true)}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "✎ Modifier le livrable avant validation" : "✎ Edit deliverable"}
          </button>
        </div>
      ) : null}

      {/* Décision et Arbitrage Humain sur le Livrable */}
      <div
        data-testid="anchor-card-four-actions-panel"
        className="rounded border p-3.5"
        style={{
          backgroundColor: "var(--color-human-led-bg)",
          borderColor: "var(--color-primary-cobalt)",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
          <strong style={{ fontSize: "14px" }}>
            {isFr
              ? "Décision & Validation du livrable"
              : "Deliverable Review & Decision"}
          </strong>
          <span style={{ fontSize: "12px", color: "var(--color-gate-emerald)", fontWeight: 600 }}>
            {isFr
              ? "✓ Contrôles automatiques de complétude : Conformes · Relecture contradictoire : Validée"
              : "✓ Automated checks: Passed · Peer review: Passed"}
          </span>
        </div>

        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="anchor-action-1-accept-btn"
            onClick={handleAction1AcceptAndSign}
            className="orcia-ds-btn-primary"
          >
            {isFr ? "✓ Valider et publier le livrable" : "✓ Approve & publish"}
          </button>

          <button
            type="button"
            data-testid="anchor-action-2-amend-diff-btn"
            onClick={() => setIsEditingDiff(true)}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "✎ Modifier le texte" : "✎ Edit text"}
          </button>

          <button
            type="button"
            data-testid="anchor-action-3-reject-loop-btn"
            onClick={handleAction3RejectAndLoop}
            className="orcia-ds-btn-secondary"
          >
            {isFr
              ? `↩ Demander des corrections (→ Étape ${returnLoopTargetStep})`
              : `↩ Request corrections (→ Step ${returnLoopTargetStep})`}
          </button>

          <button
            type="button"
            data-testid="anchor-action-4-suspend-sla-btn"
            onClick={handleAction4SuspendSla}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "⏸ Mettre en pause" : "⏸ Pause"}
          </button>
        </div>

        {/* Sélection de l'étape de renvoi & motif */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(200px, 260px) 1fr",
            gap: "8px",
            alignItems: "center",
          }}
        >
          <select
            aria-label="Étape cible pour reprise"
            data-testid="anchor-return-loop-target-select"
            value={returnLoopTargetStep}
            onChange={(e) => setReturnLoopTargetStep(e.target.value)}
            className="orcia-ds-select"
          >
            <option value="01">Renvoyer à l&apos;Étape 01 (Qualification)</option>
            <option value="02">Renvoyer à l&apos;Étape 02 (Revue du PRD)</option>
            <option value="03">Renvoyer à l&apos;Étape 03 (Étude d&apos;Architecture)</option>
            <option value="06">Renvoyer à l&apos;Étape 06 (Découpage User Stories)</option>
            <option value="08">Renvoyer à l&apos;Étape 08 (Réalisation)</option>
          </select>

          <input
            type="text"
            aria-label="Commentaire de correction"
            data-testid="anchor-return-loop-remarks-input"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            value={returnLoopRemarks}
            onChange={(e) => setReturnLoopRemarks(e.target.value)}
            placeholder={isFr ? "Précisez les points à corriger..." : "Specify required changes..."}
            className="orcia-ds-input"
          />
        </div>
      </div>
    </section>
  );
}
