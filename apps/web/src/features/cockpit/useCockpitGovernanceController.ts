import { createOrciaApiClient } from "@orcia/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useI18n } from "../../i18n";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import {
  DEFAULT_ARBITRATION_OPTIONS,
  DEFAULT_FALLBACK_WORKSPACE_ID,
  DEFAULT_STEP_KEY,
  DEFAULT_WORKFLOW_URI,
  extractGovernanceStateFromBlackboard,
} from "./cockpitGovernanceHelpers";

export interface UseCockpitGovernanceControllerOptions {
  readonly workspaceId?: string;
  readonly authorName: string;
  readonly refreshSignal?: number;
  readonly activeRunId?: string | null;
}

const toErrMsg = (err: unknown): string => (err instanceof Error ? err.message : String(err));

export function useCockpitGovernanceController({
  workspaceId,
  authorName,
  refreshSignal = 0,
  activeRunId = null,
}: UseCockpitGovernanceControllerOptions) {
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
        setErrorBanner(toErrMsg(err));
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
    if (isHydrating || !isAuthenticated) return;
    setErrorBanner(null);
    let cancelled = false;
    void apiClient
      .getOrchestrationState()
      .then(async (state) => {
        if (cancelled) return;
        const scopedRuns = (state.runs ?? []).filter((r) => r.workspace_id === effectiveWorkspaceId);
        const latestRun = scopedRuns[scopedRuns.length - 1];
        if (latestRun?.id) {
          await hydrateFromRun(latestRun.id);
          return;
        }
        setServerRunId(null);
        setStepStatus("PENDING");
        setSignedSha256(null);
        setPendingArbitrationId(null);
        setResolvedOptionKey(null);
        setResolvedJustification(null);
        setCommittedSnapshotId(null);
      })
      .catch((err) => {
        if (!cancelled) setErrorBanner(toErrMsg(err));
      });
    return () => {
      cancelled = true;
    };
  }, [apiClient, effectiveWorkspaceId, hydrateFromRun, refreshSignal, isHydrating, isAuthenticated, accessToken]);

  const ensureServerRun = async (): Promise<string> => {
    if (serverRunId) return serverRunId;
    const created = await apiClient.instantiateWorkflowRun({
      workflow_uri: DEFAULT_WORKFLOW_URI,
      workspace_id: effectiveWorkspaceId,
    });
    setServerRunId(created.run.id);
    return created.run.id;
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
      setErrorBanner(toErrMsg(err));
    }
  };

  const handleRequestArbitration = async (): Promise<string | null> => {
    setErrorBanner(null);
    try {
      const runId = await ensureServerRun();
      const res = await apiClient.requestHumanArbitration(runId, DEFAULT_STEP_KEY, {
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
      });
      setPendingArbitrationId(res.arbitration.id);
      setStepStatus(res.step_execution.status);
      return res.arbitration.id;
    } catch (err) {
      setErrorBanner(toErrMsg(err));
      return null;
    }
  };

  const handleResolveArbitration = async (optionKey: string, justification: string) => {
    setErrorBanner(null);
    try {
      const runId = await ensureServerRun();
      const arbId = pendingArbitrationId ?? (await handleRequestArbitration());
      if (!arbId) return;
      const cleanJustification =
        justification.trim() ||
        (isFr
          ? "Décision humaine motivée enregistrée depuis le Cockpit."
          : "Justified human decision recorded from the Cockpit.");
      const res = await apiClient.resolveHumanArbitration(runId, DEFAULT_STEP_KEY, {
        arbitration_id: arbId,
        selected_option_key: optionKey,
        human_justification: cleanJustification,
      });
      setResolvedOptionKey(res.arbitration.selected_option_key ?? optionKey);
      setResolvedJustification(res.arbitration.human_justification ?? cleanJustification);
      setStepStatus(res.step_execution.status);
      setCommittedSnapshotId(
        res.committed_snapshot?.id ?? res.step_execution.committed_snapshot_id ?? null,
      );
    } catch (err) {
      setErrorBanner(toErrMsg(err));
    }
  };

  return {
    dictionary, isFr, resolvedAuthorName, serverRunId, stepStatus,
    anchorText, setAnchorText, signatureText, setSignatureText,
    signedSha256, pendingArbitrationId, resolvedOptionKey, resolvedJustification,
    committedSnapshotId, hasStaleWarning, errorBanner, setErrorBanner,
    hydrateFromRun, handleSignAnchor, handleRequestArbitration, handleResolveArbitration,
  };
}
