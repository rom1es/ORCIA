import { createOrciaApiClient } from "@orcia/api-client";
import {
  ArbitrationTieBreakCard,
  HumanLedAnchorCard,
  OrciaAlertBanner,
  StatusBadge,
} from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import { useI18n } from "../../i18n";
import {
  DEFAULT_ARBITRATION_OPTIONS,
  DEFAULT_FALLBACK_WORKSPACE_ID,
  DEFAULT_SECTION_KEY,
  DEFAULT_STEP_KEY,
  DEFAULT_WORKFLOW_URI,
  extractGovernanceStateFromBlackboard,
} from "./cockpitGovernanceHelpers";
import { CockpitUpstreamChallengePanel } from "./CockpitUpstreamChallengePanel";

export interface CockpitHumanLedGovernanceSectionProps {
  readonly workspaceId?: string;
  readonly authorName: string;
  readonly refreshSignal?: number;
  readonly activeRunId?: string | null;
}

export function CockpitHumanLedGovernanceSection({
  workspaceId,
  authorName,
  refreshSignal = 0,
  activeRunId = null,
}: CockpitHumanLedGovernanceSectionProps) {
  const { dictionary, locale } = useI18n();
  const isFr = locale === "fr";
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const accessToken = useAuthSessionStore((s) => s.accessToken);
  const authDisplayName = useAuthSessionStore((s) => s.displayName);
  const authEmail = useAuthSessionStore((s) => s.email);
  const resolvedAuthorName = authDisplayName?.trim() || authEmail?.trim() || authorName;

  const [serverRunId, setServerRunId] = useState<string | null>(null);
  const [stepStatus, setStepStatus] = useState<string>("PENDING");
  const [anchorText, setAnchorText] = useState<string>("");
  const [signatureText, setSignatureText] = useState<string>(resolvedAuthorName);
  const [signedSha256, setSignedSha256] = useState<string | null>(null);
  const [pendingArbitrationId, setPendingArbitrationId] = useState<string | null>(null);
  const [resolvedOptionKey, setResolvedOptionKey] = useState<string | null>(null);
  const [resolvedJustification, setResolvedJustification] = useState<string | null>(null);
  const [committedSnapshotId, setCommittedSnapshotId] = useState<string | null>(null);
  const [hasStaleWarning, setHasStaleWarning] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const effectiveWorkspaceId = workspaceId?.trim() || DEFAULT_FALLBACK_WORKSPACE_ID;

  const hydrateFromRun = useCallback(
    async (runId: string) => {
      try {
        const bb = await apiClient.getRunBlackboardState(runId);
        const h = extractGovernanceStateFromBlackboard(bb);
        setServerRunId(h.runId);
        setStepStatus(h.stepStatus);
        if (h.anchorText) setAnchorText(h.anchorText);
        if (h.signedSha256) setSignedSha256(h.signedSha256);
        if (h.pendingArbitrationId) setPendingArbitrationId(h.pendingArbitrationId);
        if (h.resolvedOptionKey) {
          setResolvedOptionKey(h.resolvedOptionKey);
          setResolvedJustification(h.resolvedJustification);
        }
        if (h.committedSnapshotId) setCommittedSnapshotId(h.committedSnapshotId);
        setHasStaleWarning(h.hasStaleWarning);
      } catch (err) {
        setErrorBanner(err instanceof Error ? err.message : String(err));
      }
    },
    [apiClient],
  );

  useEffect(() => {
    if (activeRunId && isAuthenticated) {
      setServerRunId(activeRunId);
      void hydrateFromRun(activeRunId);
    }
  }, [activeRunId, hydrateFromRun, isAuthenticated]);

  useEffect(() => {
    if (isHydrating || !isAuthenticated) {
      return;
    }
    setErrorBanner(null);
    let cancelled = false;
    void (async () => {
      try {
        const state = await apiClient.getOrchestrationState();
        if (cancelled) return;
        const scopedRuns = (state.runs ?? []).filter(
          (r) => r.workspace_id === effectiveWorkspaceId,
        );
        const latestRun =
          scopedRuns.length > 0 ? scopedRuns[scopedRuns.length - 1] : undefined;
        if (latestRun?.id) {
          await hydrateFromRun(latestRun.id);
        } else {
          setServerRunId(null);
          setStepStatus("PENDING");
          setSignedSha256(null);
          setPendingArbitrationId(null);
          setResolvedOptionKey(null);
          setResolvedJustification(null);
          setCommittedSnapshotId(null);
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
  }, [
    apiClient,
    effectiveWorkspaceId,
    hydrateFromRun,
    refreshSignal,
    isHydrating,
    isAuthenticated,
    accessToken,
  ]);

  const ensureServerRun = async (): Promise<string> => {
    if (serverRunId) {
      return serverRunId;
    }
    const created = await apiClient.instantiateWorkflowRun({
      workflow_uri: DEFAULT_WORKFLOW_URI,
      workspace_id: effectiveWorkspaceId,
    });
    const nextRunId = created.run.id;
    setServerRunId(nextRunId);
    return nextRunId;
  };

  const handleSignAnchor = async (sectionKey: string, content: string) => {
    setErrorBanner(null);
    try {
      const runId = await ensureServerRun();
      const res = await apiClient.signHumanAnchor({
        run_id: runId,
        step_key: DEFAULT_STEP_KEY,
        section_key: sectionKey,
        content_text: content,
        signature_text: signatureText.trim() || resolvedAuthorName,
        author_type: "HUMAN",
      });
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
        <OrciaAlertBanner
          tone="crimson"
          role="alert"
          testId="cockpit-human-led-error-banner"
        >
          {errorBanner}
        </OrciaAlertBanner>
      )}

      <HumanLedAnchorCard
        testId="cockpit-human-led-anchor-card"
        justificationTestId="cockpit-human-anchor-textarea"
        signatureTestId="cockpit-human-anchor-signature-input"
        sectionKey={DEFAULT_SECTION_KEY}
        sectionTitle={dictionary.humanAnchor.defaultSectionTitle}
        authorName={resolvedAuthorName}
        value={anchorText}
        signatureLabel={isFr ? "Signature de l'auteur" : "Author signature"}
        signatureValue={signatureText}
        signaturePlaceholder={resolvedAuthorName}
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

      <CockpitUpstreamChallengePanel
        runId={serverRunId}
        isOpen={Boolean(signedSha256 && serverRunId)}
        initialStaleWarning={hasStaleWarning}
        onError={setErrorBanner}
        onReplayCompleted={() => {
          if (serverRunId) {
            void hydrateFromRun(serverRunId);
          }
        }}
      />

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
