import {
  createOrciaApiClient,
  type RunBlackboardStateResponse,
  type WorkflowAsCodeDefinitionSchemaItem,
} from "@orcia/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useI18n } from "../../i18n";
import { extractLocalizedApiError } from "../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import {
  derivePendingGovernanceFromBlackboard,
  type PendingAnchorRequirement,
  type PendingArbitrationState,
} from "./cockpitGovernanceHelpers";

export interface UseCockpitGovernanceControllerOptions {
  readonly runId: string;
  readonly workflow?: WorkflowAsCodeDefinitionSchemaItem | null;
  readonly initialBlackboard?: RunBlackboardStateResponse | null;
  readonly authorName: string;
  readonly refreshSignal?: number;
  readonly onGovernanceStateChanged?: () => void;
}

export function useCockpitGovernanceController({
  runId,
  workflow = null,
  initialBlackboard = null,
  authorName,
  refreshSignal = 0,
  onGovernanceStateChanged,
}: UseCockpitGovernanceControllerOptions) {
  const { dictionary, locale, isFr } = useI18n();
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "", locale }), [locale]);

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const authDisplayName = useAuthSessionStore((s) => s.displayName);
  const authEmail = useAuthSessionStore((s) => s.email);
  const resolvedAuthorName = authDisplayName?.trim() || authEmail?.trim() || authorName;

  const initialDerived = useMemo(
    () =>
      initialBlackboard
        ? derivePendingGovernanceFromBlackboard(initialBlackboard, workflow)
        : null,
    [initialBlackboard, workflow],
  );

  const [stepStatus, setStepStatus] = useState<string>(
    initialDerived?.stepStatus ?? "PENDING",
  );
  const [anchorText, setAnchorText] = useState<string>("");
  const [signatureText, setSignatureText] = useState<string>(resolvedAuthorName);
  const [pendingAnchor, setPendingAnchor] = useState<PendingAnchorRequirement | null>(
    initialDerived?.pendingAnchor ?? null,
  );
  const [pendingArbitration, setPendingArbitration] =
    useState<PendingArbitrationState | null>(initialDerived?.pendingArbitration ?? null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const applyBlackboard = useCallback(
    (bb: RunBlackboardStateResponse) => {
      const derived = derivePendingGovernanceFromBlackboard(bb, workflow);
      setStepStatus(derived.stepStatus);
      setPendingAnchor(derived.pendingAnchor);
      setPendingArbitration(derived.pendingArbitration);
    },
    [workflow],
  );

  const hydrateFromRun = useCallback(
    async (targetRunId: string) => {
      try {
        const bb = await apiClient.getRunBlackboardState(targetRunId);
        applyBlackboard(bb);
      } catch (err) {
        setErrorBanner(extractLocalizedApiError(err, locale).errorMessage);
      }
    },
    [apiClient, applyBlackboard, locale],
  );

  useEffect(() => {
    if (initialBlackboard && initialBlackboard.run_id === runId) {
      applyBlackboard(initialBlackboard);
    }
  }, [applyBlackboard, initialBlackboard, runId]);

  useEffect(() => {
    if (isHydrating || !isAuthenticated || !runId) return;
    let cancelled = false;
    void apiClient
      .getRunBlackboardState(runId)
      .then((bb) => {
        if (!cancelled) {
          applyBlackboard(bb);
        }
      })
      .catch((err) => {
        if (!cancelled) setErrorBanner(extractLocalizedApiError(err, locale).errorMessage);
      });
    return () => {
      cancelled = true;
    };
  }, [apiClient, applyBlackboard, isAuthenticated, isHydrating, locale, refreshSignal, runId]);

  const handleSignAnchor = async (sectionKey: string, content: string) => {
    if (!pendingAnchor) return;
    setErrorBanner(null);
    try {
      await apiClient.signHumanAnchor({
        run_id: runId,
        step_key: pendingAnchor.stepKey,
        section_key: sectionKey,
        content_text: content,
        signature_text: signatureText.trim() || resolvedAuthorName,
        author_type: "HUMAN",
      });
      setAnchorText("");
      await hydrateFromRun(runId);
      onGovernanceStateChanged?.();
    } catch (err) {
      setErrorBanner(extractLocalizedApiError(err, locale).errorMessage);
    }
  };

  const handleResolveArbitration = async (optionKey: string, justification: string) => {
    if (!pendingArbitration) return;
    setErrorBanner(null);
    try {
      const cleanJustification =
        justification.trim() ||
        dictionary.categoryAControllers.cockpit.defaultArbitrationJustification;
      await apiClient.resolveHumanArbitration(runId, pendingArbitration.stepKey, {
        arbitration_id: pendingArbitration.arbitrationId,
        selected_option_key: optionKey,
        human_justification: cleanJustification,
      });
      await hydrateFromRun(runId);
      onGovernanceStateChanged?.();
    } catch (err) {
      setErrorBanner(extractLocalizedApiError(err, locale).errorMessage);
    }
  };

  return {
    dictionary,
    isFr,
    resolvedAuthorName,
    serverRunId: runId,
    stepStatus,
    anchorText,
    setAnchorText,
    signatureText,
    setSignatureText,
    pendingAnchor,
    pendingArbitration,
    errorBanner,
    setErrorBanner,
    handleSignAnchor,
    handleResolveArbitration,
  };
}
