import type { ProcessPendingRunItemResponse } from "@orcia/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { useOptionalPlatformSetup } from "../../components/platformSetupStore";
import {
  isHttp403Error,
  resolveAutonomousScopeTarget,
} from "./autonomousRunsScopeHelper";
import {
  loadPersistedWorkflowsV2,
  savePersistedWorkflowV2,
  type WorkflowDefinitionV2Item,
} from "./processStudioV2Data";
import {
  createProcessesApiClient,
  mapApiWorkflowV2ToUiItem,
} from "./studio/studioLabelsAndMappers";

export function useProcessesHubData(params: {
  readonly activeScopeId: string;
  readonly activeWorkspaceId: string;
  readonly navigateToRoute: (route: string) => void;
}) {
  const { activeScopeId, activeWorkspaceId, navigateToRoute } = params;
  const { locale, dictionary } = useI18n();
  const setupCtx = useOptionalPlatformSetup();
  const hubCopy = dictionary.processStudioUi.hub;

  const effectivePendingScopeParam =
    activeScopeId === "scope-global" || !activeWorkspaceId
      ? "scope-global"
      : activeWorkspaceId;
  const autoScopeTarget = useMemo(
    () =>
      resolveAutonomousScopeTarget(
        activeScopeId,
        setupCtx?.scopes ?? [],
        setupCtx?.workspaces ?? [],
      ),
    [activeScopeId, setupCtx?.scopes, setupCtx?.workspaces],
  );

  const [workflows, setWorkflows] = useState<WorkflowDefinitionV2Item[]>(() =>
    loadPersistedWorkflowsV2(locale),
  );
  const [pendingRuns, setPendingRuns] = useState<ProcessPendingRunItemResponse[]>([]);
  const [autonomousCount, setAutonomousCount] = useState<number>(0);
  const [isLoadingPendingRuns, setIsLoadingPendingRuns] = useState<boolean>(true);
  const [launchingWorkflowId, setLaunchingWorkflowId] = useState<string | null>(null);
  const [hubErrorBanner, setHubErrorBanner] = useState<string | null>(null);
  const [vsmSummary, setVsmSummary] = useState<{
    id: string;
    title: string;
    subtitle: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    const apiClient = createProcessesApiClient(locale);
    setIsLoadingPendingRuns(true);

    const fetchAutonomousCount = async (): Promise<number> => {
      try {
        const res = autoScopeTarget.exactWorkspaceId
          ? await apiClient.listWorkspaceAutonomousRuns(autoScopeTarget.exactWorkspaceId)
          : await apiClient.listAutonomousRuns(
              autoScopeTarget.orgScopeId ? { scopeId: autoScopeTarget.orgScopeId } : undefined,
            );
        return Array.isArray(res?.runs) ? res.runs.length : 0;
      } catch (err: unknown) {
        if (!isHttp403Error(err)) {
          console.warn("[orcia/processes] autonomous supervision count unavailable:", err);
        }
        return 0;
      }
    };

    Promise.all([
      apiClient.listWorkflowsV2(),
      apiClient.listValueStreamMaps(),
      apiClient.listProcessPendingRuns({ workspaceId: effectivePendingScopeParam }),
      fetchAutonomousCount(),
    ])
      .then(([wfRes, vsmRes, pendingRes, autoCount]) => {
        if (cancelled) return;
        const firstVsm = Array.isArray(vsmRes?.items) ? vsmRes.items[0] : undefined;
        if (firstVsm?.id) {
          setVsmSummary({
            id: firstVsm.id,
            title: firstVsm.title,
            subtitle: firstVsm.subtitle,
          });
        }
        setPendingRuns(Array.isArray(pendingRes?.items) ? pendingRes.items : []);
        setAutonomousCount(autoCount);
        if (!Array.isArray(wfRes?.items) || wfRes.items.length === 0) return;
        setWorkflows((prev) =>
          wfRes.items.map((apiWf) => {
            const existing = prev.find((p) => p.id === apiWf.id || p.slug === apiWf.slug);
            const uiItem = mapApiWorkflowV2ToUiItem(apiWf, existing, locale);
            savePersistedWorkflowV2(uiItem);
            return uiItem;
          }),
        );
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const formatted = formatRfc9457ErrorToBanner(
          err,
          locale,
          hubCopy.catalogResourceLabel,
        );
        setHubErrorBanner(formatted.fullText);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingPendingRuns(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    locale,
    effectivePendingScopeParam,
    autoScopeTarget.exactWorkspaceId,
    autoScopeTarget.orgScopeId,
    hubCopy.catalogResourceLabel,
  ]);

  const handleLaunchWorkflow = useCallback(
    async (wfId: string) => {
      const matched = workflows.find((w) => w.id === wfId);
      setLaunchingWorkflowId(wfId);
      setHubErrorBanner(null);
      try {
        const res = await createProcessesApiClient(locale).startWorkflowV2Run(wfId, {
          inputs: { objective: matched?.title ?? wfId },
          iteration: 1,
          reentry_mode: "initial",
          ...(activeWorkspaceId ? { workspace_id: activeWorkspaceId } : {}),
        });
        if (res?.run?.run_id) {
          navigateToRoute(`/processes/runs/${res.run.run_id}`);
        }
      } catch (err: unknown) {
        const formatted = formatRfc9457ErrorToBanner(
          err,
          locale,
          matched?.title ?? hubCopy.catalogResourceLabel,
        );
        setHubErrorBanner(formatted.fullText);
      } finally {
        setLaunchingWorkflowId(null);
      }
    },
    [workflows, locale, activeWorkspaceId, navigateToRoute, hubCopy.catalogResourceLabel],
  );

  return {
    workflows,
    setWorkflows,
    pendingRuns,
    autonomousCount,
    isLoadingPendingRuns,
    launchingWorkflowId,
    hubErrorBanner,
    vsmSummary,
    handleLaunchWorkflow,
  };
}
