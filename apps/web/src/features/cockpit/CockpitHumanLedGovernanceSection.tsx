import { createOrciaApiClient } from "@orcia/api-client";
import {
  ArbitrationTieBreakCard,
  type ArbitrationTieBreakOptionView,
  HumanLedAnchorCard,
  StatusBadge,
} from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useI18n } from "../../i18n";

const DEFAULT_WORKFLOW_URI = "orcia://workflows/claims-engineering-delivery";
const DEFAULT_STEP_KEY = "frame-architecture-intent";
const DEFAULT_SECTION_KEY = "human_architecture_intent";
const DEFAULT_FALLBACK_WORKSPACE_ID = "0192c4e0-0000-7000-8000-000000000201";

const DEFAULT_ARBITRATION_OPTIONS: ArbitrationTieBreakOptionView[] = [
  {
    optionKey: "OPT_A_SPOT_15M",
    title: "Option A — Taux Spot 15 min",
    pros: ["Compatible API partenaire v3", "Latence minimale"],
    cons: ["Fenêtre client 15 min"],
    siImpact: "1 microservice impacté",
    finopsImpact: "0.02 USD / run",
    recommended: true,
  },
  {
    optionKey: "OPT_B_LOCK_48H",
    title: "Option B — Taux Bloqué 48h",
    pros: ["Confort client 48h"],
    cons: ["Incompatible API v3"],
    siImpact: "3 systèmes centraux impactés",
    finopsImpact: "0.18 USD / run",
    recommended: false,
  },
];

export interface CockpitHumanLedGovernanceSectionProps {
  readonly workspaceId?: string;
  readonly authorName: string;
  readonly refreshSignal?: number;
}

export function CockpitHumanLedGovernanceSection({
  workspaceId,
  authorName,
  refreshSignal = 0,
}: CockpitHumanLedGovernanceSectionProps) {
  const { dictionary, locale } = useI18n();
  const isFr = locale === "fr";
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const [serverRunId, setServerRunId] = useState<string | null>(null);
  const [stepStatus, setStepStatus] = useState<string>("PENDING");
  const [anchorText, setAnchorText] = useState<string>("");
  const [signatureText, setSignatureText] = useState<string>(authorName);
  const [signedSha256, setSignedSha256] = useState<string | null>(null);
  const [pendingArbitrationId, setPendingArbitrationId] = useState<string | null>(null);
  const [resolvedOptionKey, setResolvedOptionKey] = useState<string | null>(null);
  const [resolvedJustification, setResolvedJustification] = useState<string | null>(null);
  const [committedSnapshotId, setCommittedSnapshotId] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const effectiveWorkspaceId = workspaceId?.trim() || DEFAULT_FALLBACK_WORKSPACE_ID;

  const hydrateFromRun = useCallback(
    async (runId: string) => {
      try {
        const bb = await apiClient.getRunBlackboardState(runId, "marc");
        setServerRunId(bb.run_id);
        const step =
          bb.step_executions.find((s) => s.step_key === DEFAULT_STEP_KEY) ??
          bb.step_executions[0];
        if (step) {
          setStepStatus(step.status);
          const draft = (step.draft_artifact ?? {}) as Record<string, unknown>;
          const anchors = (draft.human_anchors ?? {}) as Record<
            string,
            { content_text?: string; content_sha256?: string }
          >;
          const anchorEntry = anchors[DEFAULT_SECTION_KEY];
          if (anchorEntry?.content_text) {
            setAnchorText(anchorEntry.content_text);
          }
          if (anchorEntry?.content_sha256) {
            setSignedSha256(anchorEntry.content_sha256);
          }
          if (typeof draft.pending_arbitration_id === "string") {
            setPendingArbitrationId(draft.pending_arbitration_id);
          }
          const resolution = draft.arbitration_resolution as
            | {
                selected_option_key?: string;
                human_justification?: string | null;
              }
            | undefined;
          if (resolution?.selected_option_key) {
            setResolvedOptionKey(resolution.selected_option_key);
            setResolvedJustification(resolution.human_justification ?? null);
          }
          if (step.committed_snapshot_id) {
            setCommittedSnapshotId(step.committed_snapshot_id);
          }
        }
        const firstSnap = bb.active_snapshots[0];
        if (firstSnap?.id) {
          setCommittedSnapshotId(firstSnap.id);
        }
      } catch (err) {
        setErrorBanner(err instanceof Error ? err.message : String(err));
      }
    },
    [apiClient],
  );

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const state = await apiClient.getOrchestrationState("marc");
        if (cancelled) return;
        const latestRun =
          state.runs && state.runs.length > 0
            ? state.runs[state.runs.length - 1]
            : undefined;
        if (latestRun?.id) {
          await hydrateFromRun(latestRun.id);
        }
      } catch (err) {
        if (!cancelled) {
          setErrorBanner(err instanceof Error ? err.message : String(err));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiClient, hydrateFromRun, refreshSignal]);

  const ensureServerRun = async (): Promise<string> => {
    if (serverRunId) {
      return serverRunId;
    }
    const created = await apiClient.instantiateWorkflowRun(
      {
        workflow_uri: DEFAULT_WORKFLOW_URI,
        workspace_id: effectiveWorkspaceId,
      },
      "marc",
    );
    const nextRunId = created.run.id;
    setServerRunId(nextRunId);
    return nextRunId;
  };

  const handleSignAnchor = async (sectionKey: string, content: string) => {
    setErrorBanner(null);
    try {
      const runId = await ensureServerRun();
      const res = await apiClient.signHumanAnchor(
        {
          run_id: runId,
          step_key: DEFAULT_STEP_KEY,
          section_key: sectionKey,
          content_text: content,
          signature_text: signatureText.trim() || authorName,
          author_type: "HUMAN",
        },
        "marc",
      );
      setSignedSha256(res.signature.content_sha256);
      setStepStatus(res.step_execution.status);
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : String(err));
    }
  };

  const handleRequestArbitration = async (): Promise<string | null> => {
    setErrorBanner(null);
    try {
      const runId = await ensureServerRun();
      const res = await apiClient.requestHumanArbitration(
        runId,
        DEFAULT_STEP_KEY,
        {
          question_title: dictionary.arbitrationTieBreak.defaultQuestionTitle,
          context_summary: dictionary.arbitrationTieBreak.defaultContextSummary,
          tie_break_policy: "PAUSE_AND_ESCALATE",
          options_matrix: DEFAULT_ARBITRATION_OPTIONS.map((opt) => ({
            option_key: opt.optionKey,
            title: opt.title,
            pros: opt.pros,
            cons: opt.cons,
            si_impact: opt.siImpact,
            finops_impact: opt.finopsImpact,
            recommended: Boolean(opt.recommended),
            ontology_concept_key: null,
          })),
        },
        "marc",
      );
      setPendingArbitrationId(res.arbitration.id);
      setStepStatus(res.step_execution.status);
      return res.arbitration.id;
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : String(err));
      return null;
    }
  };

  const handleResolveArbitration = async (optionKey: string, justification: string) => {
    setErrorBanner(null);
    try {
      const runId = await ensureServerRun();
      let arbId = pendingArbitrationId;
      if (!arbId) {
        arbId = await handleRequestArbitration();
      }
      if (!arbId) {
        return;
      }
      const cleanJustification =
        justification.trim() ||
        (isFr
          ? "Décision humaine motivée enregistrée depuis le Cockpit."
          : "Justified human decision recorded from the Cockpit.");
      const res = await apiClient.resolveHumanArbitration(
        runId,
        DEFAULT_STEP_KEY,
        {
          arbitration_id: arbId,
          selected_option_key: optionKey,
          human_justification: cleanJustification,
        },
        "marc",
      );
      setResolvedOptionKey(res.arbitration.selected_option_key ?? optionKey);
      setResolvedJustification(res.arbitration.human_justification ?? cleanJustification);
      setStepStatus(res.step_execution.status);
      setCommittedSnapshotId(
        res.committed_snapshot?.id ?? res.step_execution.committed_snapshot_id ?? null,
      );
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <section
      data-testid="cockpit-human-led-governance-section"
      data-run-id={serverRunId ?? ""}
      data-step-status={stepStatus}
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
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
        <div>
          <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700 }}>
            {isFr
              ? "Gouvernance Human-Led : Ancrage obligatoire & Arbitrage"
              : "Human-Led Governance: Mandatory Anchor & Arbitration"}
          </h2>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {isFr
              ? "Signez l'intention d'architecture (≥ 30 caractères) puis départagez les options en attente."
              : "Sign the architecture intent (≥ 30 characters) then resolve pending option tie-breaks."}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            type="button"
            data-testid="cockpit-request-arbitration-btn"
            onClick={() => void handleRequestArbitration()}
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-bg)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isFr ? "Escalader en arbitrage humain" : "Escalate to human arbitration"}
          </button>
          <StatusBadge
            label={stepStatus}
            tone={stepStatus === "COMMITTED" ? "emerald" : "amber"}
            monospace
          />
        </div>
      </div>

      {errorBanner && (
        <div
          data-testid="cockpit-human-led-error-banner"
          role="alert"
          style={{
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-arbitration-bg)",
            color: "var(--color-arbitration-amber)",
            fontSize: "13px",
          }}
        >
          {errorBanner}
        </div>
      )}

      <HumanLedAnchorCard
        testId="cockpit-human-led-anchor-card"
        justificationTestId="cockpit-human-anchor-textarea"
        signatureTestId="cockpit-human-anchor-signature-input"
        sectionKey={DEFAULT_SECTION_KEY}
        sectionTitle={dictionary.humanAnchor.defaultSectionTitle}
        authorName={authorName}
        value={anchorText}
        signatureLabel={isFr ? "Signature de l'auteur" : "Author signature"}
        signatureValue={signatureText}
        signaturePlaceholder={authorName}
        labels={dictionary.humanAnchor}
        onChange={setAnchorText}
        onSignatureChange={setSignatureText}
        onSignAnchor={(secKey, content) => void handleSignAnchor(secKey, content)}
      />

      {signedSha256 && (
        <div
          data-testid="cockpit-human-anchor-signed-badge"
          style={{
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-gate-emerald-bg)",
            color: "var(--color-gate-emerald)",
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            fontWeight: 600,
          }}
        >
          {isFr
            ? `✓ Ancrage humain signé (SHA-256 : ${signedSha256.slice(0, 16)}…)`
            : `✓ Human anchor signed (SHA-256: ${signedSha256.slice(0, 16)}…)`}
        </div>
      )}

      <ArbitrationTieBreakCard
        testId="cockpit-arbitration-tiebreak-card"
        arbitrationId={pendingArbitrationId ?? "cockpit-arb"}
        stepKey={DEFAULT_STEP_KEY}
        questionTitle={dictionary.arbitrationTieBreak.defaultQuestionTitle}
        contextSummary={dictionary.arbitrationTieBreak.defaultContextSummary}
        tieBreakPolicy="PAUSE_AND_ESCALATE"
        options={DEFAULT_ARBITRATION_OPTIONS}
        selectedOptionKey={resolvedOptionKey}
        labels={dictionary.arbitrationTieBreak}
        onSelectOption={(optKey, justification) =>
          void handleResolveArbitration(optKey, justification)
        }
      />

      {resolvedOptionKey && (
        <div
          data-testid="cockpit-arbitration-resolved-summary"
          data-selected-option={resolvedOptionKey}
          data-committed-snapshot-id={committedSnapshotId ?? ""}
          style={{
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-bg)",
            fontSize: "13px",
          }}
        >
          <strong>{resolvedOptionKey}</strong>
          {resolvedJustification ? ` — ${resolvedJustification}` : ""}
        </div>
      )}
    </section>
  );
}
