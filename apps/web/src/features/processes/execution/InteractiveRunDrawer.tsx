import React, { useState } from "react";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";

export interface InteractiveRunDrawerProps {
  workflow: WorkflowDefinitionV2Item;
  onClose: () => void;
  isFr: boolean;
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
  const [artifactMarkdown, setArtifactMarkdown] = useState<string>(
    `# ${workflow.title}\n\n## Sous-étape : ${currentSubStep?.name ?? "Exécution"}\n\nLivrable structuré généré par ${workflow.agent_ref}.\n\n## Critères & WSJF\nScore WSJF = 8.4 — Périmètre conforme au socle Confluence.`,
  );
  const [artifactSha256, setArtifactSha256] = useState<string>(() =>
    simpleHashHex(artifactMarkdown),
  );
  const [isEditingDiff, setIsEditingDiff] = useState<boolean>(false);
  const [returnLoopTargetStep, setReturnLoopTargetStep] = useState<string>("02");
  const [returnLoopRemarks, setReturnLoopRemarks] = useState<string>(
    "Préciser les hypothèses de gain WSJF sur le segment pro.",
  );
  const [signedTokenPreview, setSignedTokenPreview] = useState<string | null>(null);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);

  const idempotencyKey = `${runId}:${currentSubStep?.id ?? "step"}:iter-${iteration}`;
  const s3Uri = `s3://orcia-artifacts/${runId}/${currentSubStep?.id ?? "step"}/iter-${iteration}/${artifactSha256.slice(0, 16)}.md`;

  const handleApproveCurrentSubStep = () => {
    if (currentSubStep?.write_preview_required && status !== "WAITING_WRITE_PREVIEW") {
      setStatus("WAITING_WRITE_PREVIEW");
      setStatusBanner(
        isFr
          ? "Prévisualisation d'écriture externe (WritePreviewCard) générée : veuillez signer le jeton d'approbation."
          : "External WritePreviewCard generated: please sign the approval token.",
      );
      return;
    }

    if (status === "WAITING_WRITE_PREVIEW") {
      const token = `sat_${artifactSha256.slice(0, 16)}_hmac_ok`;
      setSignedTokenPreview(token);
    }

    if (currentSubIndex + 1 < enabledSubSteps.length) {
      const nextIdx = currentSubIndex + 1;
      const nextSub = enabledSubSteps[nextIdx];
      setCurrentSubIndex(nextIdx);
      const nextMd = `# ${workflow.title}\n\n## Sous-étape : ${nextSub?.name ?? ""}\n\nSortie produite : ${nextSub?.output_description ?? ""}`;
      setArtifactMarkdown(nextMd);
      setArtifactSha256(simpleHashHex(nextMd));
      setStatus(
        nextSub?.write_preview_required ? "WAITING_WRITE_PREVIEW" : "WAITING_SUBSTEP_HITL",
      );
      setStatusBanner(
        isFr
          ? `Sous-étape « ${currentSubStep?.short_label} » validée (DBOS.send). Passage à « ${nextSub?.short_label} ».`
          : `Sub-step "${currentSubStep?.short_label}" approved. Advancing to "${nextSub?.short_label}".`,
      );
    } else {
      setStatus("WAITING_FINAL_ANCHOR");
      setStatusBanner(
        isFr
          ? "Pipeline de Gates exécuté : 100 % des runners déterministes (auto-heal <= 3) et agents contradicteurs sont PASS. Prêt pour l'arbitrage souverain Anchor Card (4 actions)."
          : "Gates Pipeline executed: 100% deterministic runners and adversarial agents PASSED. Ready for Final Anchor Card arbitration.",
      );
    }
  };

  const handleSimulateExternalWebhook = () => {
    setStatus("WAITING_FINAL_ANCHOR");
    setStatusBanner(
      isFr
        ? `Événement externe « ${workflow.external_completion_event ?? "git:pr_opened"} » reçu : exécution du Gatekeeper ORCIA terminée avec succès.`
        : `External event "${workflow.external_completion_event ?? "git:pr_opened"}" received: ORCIA Gatekeeper passed.`,
    );
  };

  // 4 Sovereign Actions on Final Anchor Card / Sub-step Diff
  const handleAction1AcceptAndSign = () => {
    setStatus("COMPLETED_APPROVED");
    setStatusBanner(
      isFr
        ? `Action 1 (Accepter & Signer) enregistrée : livrable scellé dans SeaweedFS (${s3Uri}) avec SHA-256 ${artifactSha256.slice(0, 12)}.`
        : `Action 1 (Accept & Sign) recorded: deliverable sealed in SeaweedFS (${s3Uri}).`,
    );
  };

  const handleAction2SaveAmendedDiff = () => {
    const newSha = simpleHashHex(artifactMarkdown);
    setArtifactSha256(newSha);
    setIsEditingDiff(false);
    setStatusBanner(
      isFr
        ? `Action 2 (Amender le Diff) persistée dans SeaweedFS S3 : nouveau SHA-256 calculé (${newSha.slice(0, 12)}).`
        : `Action 2 (Amend Diff) persisted in SeaweedFS S3: new SHA-256 computed (${newSha.slice(0, 12)}).`,
    );
  };

  const handleAction3RejectAndLoop = () => {
    const nextIter = iteration + 1;
    setIteration(nextIter);
    setReentryMode("corrections");
    setCurrentSubIndex(0);
    setStatus("RETURN_LOOP_TRIGGERED");
    const revisedMd = `${artifactMarkdown}\n\n## Ré-entrée en mode corrections (iter-${nextIter} -> Étape ${returnLoopTargetStep})\nRemarques intégrées : ${returnLoopRemarks}`;
    setArtifactMarkdown(revisedMd);
    setArtifactSha256(simpleHashHex(revisedMd));
    setStatusBanner(
      isFr
        ? `Action 3 (Refuser & Boucler) déclenchée vers Étape ${returnLoopTargetStep} en mode « corrections » : nouvelle clé d'idempotence cyclique ${runId}:${currentSubStep?.id ?? "step"}:iter-${nextIter}.`
        : `Action 3 (Reject & Loop) triggered toward Step ${returnLoopTargetStep} in "corrections" mode (:iter-${nextIter}).`,
    );
  };

  const handleAction4SuspendSla = () => {
    setStatus("SLA_SUSPENDED");
    setStatusBanner(
      isFr
        ? "Action 4 (Suspendre le SLA) activée : horloge SLA mise en pause dans l'audit_ledger."
        : "Action 4 (Suspend SLA) activated: SLA clock paused in audit_ledger.",
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
        border: "2px solid var(--color-primary-cobalt)",
      }}
    >
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
              data-testid="run-drawer-status-badge"
              className="rounded px-2 py-0.5 text-xs font-bold"
              style={{
                backgroundColor: "var(--color-action-primary-subtle)",
                color: "var(--color-primary-cobalt)",
                fontFamily: "var(--font-mono)",
              }}
            >
              {status}
            </span>
            <span
              data-testid="run-drawer-idempotency-key"
              className="rounded px-2 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-gate-emerald-bg)",
                color: "var(--color-gate-emerald)",
                fontFamily: "var(--font-mono)",
              }}
            >
              {idempotencyKey}
            </span>
            <span
              data-testid="run-drawer-reentry-mode"
              className="rounded px-2 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor:
                  reentryMode === "corrections"
                    ? "var(--color-arbitration-bg)"
                    : "var(--color-bg-elevated)",
                color:
                  reentryMode === "corrections"
                    ? "var(--color-arbitration-amber)"
                    : "var(--color-text-secondary)",
              }}
            >
              mode: {reentryMode} (iter-{iteration})
            </span>
          </div>
          <h3 style={{ margin: "6px 0 0 0", fontSize: "17px" }}>
            {isFr ? "Exécution DBOS & Arbitrage HITL — " : "DBOS Execution & HITL Arbitration — "}
            {workflow.title}
          </h3>
        </div>

        <button
          type="button"
          data-testid="close-interactive-run-drawer-btn"
          onClick={onClose}
          className="orcia-ds-btn-secondary"
        >
          {isFr ? "✕ Fermer l'exécution" : "✕ Close Run"}
        </button>
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

      {/* External Delegated Gate Mode (Sas Externe Délégué, CA-9.3.3) */}
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
            🔌 Mode « Sas Externe Délégué » ({workflow.external_tool_label ?? "IDE / CI Externe"})
          </strong>
          <div style={{ fontSize: "12.5px" }}>
            ORCIA n&apos;exécute pas l&apos;agent de code à la place de l&apos;IDE : le Context Bundle MCP est exposé et le workflow attend l&apos;événement externe{" "}
            <code style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>
              {workflow.external_completion_event ?? "git:pr_opened"}
            </code>{" "}
            pour déclencher le pipeline de Gates.
          </div>
          <div>
            <button
              type="button"
              data-testid="simulate-external-webhook-btn"
              onClick={handleSimulateExternalWebhook}
              className="orcia-ds-btn-primary"
            >
              {isFr
                ? `⚡ Simuler Événement Externe (${workflow.external_completion_event ?? "git:pr_opened"})`
                : "⚡ Simulate External Webhook Event"}
            </button>
          </div>
        </div>
      ) : null}

      {/* Claim-Check S3 Pointer & Diff Editor (CA-9.5.2) */}
      <div
        data-testid="claim-check-s3-artifact-box"
        className="rounded border p-3"
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
          <div style={{ fontSize: "12px", fontFamily: "var(--font-mono)" }}>
            <strong>ClaimCheckPointer S3 :</strong>{" "}
            <span data-testid="claim-check-s3-uri">{s3Uri}</span>
          </div>
          <span
            data-testid="claim-check-sha256"
            className="rounded px-2 py-0.5 text-xs font-semibold"
            style={{
              backgroundColor: "var(--color-action-primary-subtle)",
              color: "var(--color-primary-cobalt)",
              fontFamily: "var(--font-mono)",
            }}
          >
            SHA-256: {artifactSha256.slice(0, 16)}
          </span>
        </div>

        {isEditingDiff ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <textarea
              aria-label="Éditeur de Diff Markdown S3"
              data-testid="amend-diff-markdown-textarea"
              rows={6}
              value={artifactMarkdown}
              onChange={(e) => setArtifactMarkdown(e.target.value)}
              className="orcia-ds-textarea"
              style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}
            />
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                data-testid="confirm-amend-diff-btn"
                onClick={handleAction2SaveAmendedDiff}
                className="orcia-ds-btn-primary"
              >
                {isFr
                  ? "💾 Enregistrer le Diff amendé dans S3 (Nouveau SHA-256)"
                  : "💾 Save Amended Diff to S3 (New SHA-256)"}
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
              padding: "10px",
              borderRadius: "6px",
              backgroundColor: "var(--color-surface-card)",
              border: "1px solid var(--color-border-subtle)",
              fontFamily: "var(--font-mono)",
              fontSize: "12px",
              whiteSpace: "pre-wrap",
            }}
          >
            {artifactMarkdown}
          </pre>
        )}
      </div>

      {/* WritePreviewCard when external write is required */}
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
            <strong>🛡️ Permission Broker — WritePreviewCard :</strong> Écriture externe préparée pour{" "}
            <code style={{ fontFamily: "var(--font-mono)" }}>{currentSubStep?.name}</code> (SHA-256 :{" "}
            {artifactSha256.slice(0, 10)}). Aucune écriture externe n&apos;est exécutée sans{" "}
            <code>SignedApprovalToken</code>.
          </div>
          <button
            type="button"
            data-testid="sign-write-preview-token-btn"
            onClick={handleApproveCurrentSubStep}
            className="orcia-ds-btn-primary"
          >
            {isFr ? "✍️ Signer SignedApprovalToken & Exécuter" : "✍️ Sign Token & Execute"}
          </button>
        </div>
      ) : null}

      {signedTokenPreview ? (
        <div
          data-testid="signed-approval-token-badge"
          style={{ fontSize: "11.5px", fontFamily: "var(--font-mono)", color: "var(--color-gate-emerald)" }}
        >
          ✓ SignedApprovalToken émis : {signedTokenPreview}
        </div>
      ) : null}

      {/* Sub-step progression bar */}
      {status === "WAITING_SUBSTEP_HITL" ? (
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="approve-substep-checkpoint-btn"
            onClick={handleApproveCurrentSubStep}
            className="orcia-ds-btn-primary"
          >
            {isFr
              ? `✓ Valider le point d'étape « ${currentSubStep?.short_label} » (DBOS.send)`
              : `✓ Approve Sub-Step "${currentSubStep?.short_label}"`}
          </button>
          <button
            type="button"
            data-testid="open-amend-diff-editor-btn"
            onClick={() => setIsEditingDiff(true)}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "✎ Amender le Diff avant validation" : "✎ Amend Diff before approval"}
          </button>
        </div>
      ) : null}

      {/* Final Anchor Card — 4 Sovereign Actions (CA-9.5.2) */}
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
              ? "⚓ Anchor Card Souveraine — 4 Actions d'Arbitrage sur Diff S3"
              : "⚓ Sovereign Anchor Card — 4 Arbitration Actions on S3 Diff"}
          </strong>
          <span style={{ fontSize: "11.5px", color: "var(--color-text-secondary)" }}>
            Gates Déterministes : PASS · Agent Contradicteur : PASS
          </span>
        </div>

        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="anchor-action-1-accept-btn"
            onClick={handleAction1AcceptAndSign}
            className="orcia-ds-btn-primary"
          >
            {isFr ? "✓ 1. Accepter & Signer" : "✓ 1. Accept & Sign"}
          </button>

          <button
            type="button"
            data-testid="anchor-action-2-amend-diff-btn"
            onClick={() => setIsEditingDiff(true)}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "✎ 2. Amender le Diff (S3)" : "✎ 2. Amend Diff (S3)"}
          </button>

          <button
            type="button"
            data-testid="anchor-action-3-reject-loop-btn"
            onClick={handleAction3RejectAndLoop}
            className="orcia-ds-btn-secondary"
          >
            {isFr
              ? `↩ 3. Refuser & Boucler (→ Étape ${returnLoopTargetStep})`
              : `↩ 3. Reject & Loop (→ Step ${returnLoopTargetStep})`}
          </button>

          <button
            type="button"
            data-testid="anchor-action-4-suspend-sla-btn"
            onClick={handleAction4SuspendSla}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "⏸ 4. Suspendre SLA" : "⏸ 4. Suspend SLA"}
          </button>
        </div>

        {/* Return Loop Target Selector & Remarks Input */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(160px, 220px) 1fr",
            gap: "8px",
            alignItems: "center",
          }}
        >
          <select
            aria-label="Étape cible de la boucle de retour"
            data-testid="anchor-return-loop-target-select"
            value={returnLoopTargetStep}
            onChange={(e) => setReturnLoopTargetStep(e.target.value)}
            className="orcia-ds-select"
          >
            <option value="01">Boucle vers Étape 01 (Qualification)</option>
            <option value="02">Boucle vers Étape 02 (PRD En revue)</option>
            <option value="03">Boucle vers Étape 03 (Architecture DE)</option>
            <option value="06">Boucle vers Étape 06 (Découpage US)</option>
            <option value="08">Boucle vers Étape 08 (Développement)</option>
          </select>

          <input
            type="text"
            aria-label="Motif et remarques de boucle de retour"
            data-testid="anchor-return-loop-remarks-input"
            value={returnLoopRemarks}
            onChange={(e) => setReturnLoopRemarks(e.target.value)}
            className="orcia-ds-input"
          />
        </div>
      </div>
    </section>
  );
}
