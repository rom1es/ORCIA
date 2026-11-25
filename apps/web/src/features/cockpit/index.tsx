import { createOrciaApiClient } from "@orcia/api-client";
import {
  ORCIA_MODULE_ICON_NAMES,
  OrciaAlertBanner,
  OrciaDataCard,
  OrciaPageHeader,
  ProgressiveDay0AccostageBanner,
  StreamlinedCockpitView,
} from "@orcia/ui";
import React, { useMemo, useState } from "react";
import { buildUnifiedAccostageMilestones } from "../../components/platformSetupAccostage";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { buildShellDisabledMenuKeys } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import {
  isPlatformAdministratorSession,
  useAuthSessionStore,
} from "../../stores/authSessionStore";
import { buildCockpitWorkflowPreviewGraph } from "./cockpitWorkflowPreview";
import { CockpitHumanLedGovernanceSection } from "./CockpitHumanLedGovernanceSection";
import { CockpitRunsSection } from "./CockpitRunsSection";
import { CockpitUpstreamChallengePanel } from "./CockpitUpstreamChallengePanel";
import { useCockpitGovernancePoll } from "./useCockpitGovernancePoll";

export { buildCockpitWorkflowPreviewGraph };

export function CockpitFeaturePanel() {
  const { dictionary, isFr } = useI18n();
  const {
    activeScopeId,
    navigateToRoute,
    disabledMenuKeys: shellDisabledMenuKeys,
  } = useShellNavigation();
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const authEmail = useAuthSessionStore((s) => s.email);
  const authDisplayName = useAuthSessionStore((s) => s.displayName);
  const roles = useAuthSessionStore((s) => s.roles);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const {
    platformAdmin,
    llmTiers,
    workspaces,
    workflows,
    runs,
    scopes,
    accostageCounts,
    accostageSummary,
    completedSetupStepsCount,
    launchRun,
  } = usePlatformSetup();

  const [selectedWsId, setSelectedWsId] = useState<string>("");
  const [selectedWfKey, setSelectedWfKey] = useState<string>("");
  const [runTitle, setRunTitle] = useState<string>("");
  const [runRefreshSignal, setRunRefreshSignal] = useState<number>(0);
  const [challengeError, setChallengeError] = useState<string | null>(null);

  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);

  const availableWorkspaces = useMemo(() => {
    const scoped =
      activeScopeNode?.level === "WORKSPACE"
        ? workspaces.filter((ws) => ws.workspaceId === activeScopeId)
        : activeScopeNode?.level === "TEAM"
          ? workspaces.filter(
              (ws) => !ws.ownerOrgUnitId || ws.ownerOrgUnitId === activeScopeId,
            )
          : workspaces;
    return scoped.length > 0 ? scoped : workspaces;
  }, [activeScopeId, activeScopeNode?.level, workspaces]);

  const scopedRuns =
    activeScopeNode?.level === "WORKSPACE"
      ? runs.filter((r) => r.workspaceId === activeScopeId)
      : activeScopeNode?.level === "TEAM"
        ? runs.filter((r) =>
            availableWorkspaces.some((ws) => ws.workspaceId === r.workspaceId),
          )
        : runs;

  const { pendingGovernance, challengeTarget } = useCockpitGovernancePoll({
    activeScopeId,
    activeScopeLevel: activeScopeNode?.level,
    availableWorkspaces,
    isAuthenticated,
    isHydrating,
    runRefreshSignal,
  });

  const canConfigurePlatform = isPlatformAdministratorSession({ roles, readOnlyObserver });
  const milestones = buildUnifiedAccostageMilestones({
    isFr,
    summary: accostageSummary,
    roles,
    readOnlyObserver,
    visibleMilestoneKeys: accostageCounts?.visibleMilestoneKeys,
  });
  const realPlatformAdminDisplayName =
    accostageCounts?.platformAdminDisplayName ?? platformAdmin?.displayName ?? null;
  const realPlatformAdminEmail = platformAdmin?.email ?? null;

  const handleLaunchRun = (event: React.FormEvent) => {
    event.preventDefault();
    const targetWs =
      availableWorkspaces.find((w) => w.workspaceId === selectedWsId) ??
      availableWorkspaces[0];
    if (!targetWs || !runTitle.trim()) {
      return;
    }
    const wfKey = selectedWfKey || workflows[0]?.workflowKey || "assistant-agent";
    const workflowUri = wfKey.includes("://")
      ? wfKey
      : wfKey === "assistant-agent"
        ? "orcia://system/workflows/assistant-agent"
        : `orcia://workflows/${wfKey}`;
    launchRun({
      workspaceId: targetWs.workspaceId,
      workspaceName: targetWs.name,
      title: runTitle.trim(),
      workflowKey: wfKey,
    });
    setRunTitle("");
    void (async () => {
      try {
        await createOrciaApiClient({ baseUrl: "" }).instantiateWorkflowRun({
          workflow_uri: workflowUri,
          workspace_id: targetWs.workspaceId,
        });
        setRunRefreshSignal((n) => n + 1);
      } catch (err: unknown) {
        console.warn("[orcia/cockpit] failed to instantiate workflow run:", err);
      }
    })();
  };

  const showGovernanceSection = pendingGovernance !== null;
  const currentUserId = authEmail?.trim() || platformAdmin?.email || "";
  const resolvedAuthorName =
    authDisplayName?.trim() ||
    authEmail?.trim() ||
    platformAdmin?.displayName ||
    dictionary.humanAnchor.defaultAuthorName;

  const effectiveDisabledMenuKeys =
    shellDisabledMenuKeys ??
    buildShellDisabledMenuKeys({
      isFr,
      adminCreated: accostageSummary.adminCreated,
      day0AdminMissingReason: dictionary.firstBootAdminModal.day0DisabledAdminMissingReason,
      llmTiers,
      workspaces,
      hasModels: accostageSummary.hasModels,
      hasWorkspaces: workspaces.length > 0 || accostageSummary.hasWorkspaces,
    });

  return (
    <div
      data-testid="cockpit-empty-first-panel"
      style={{ display: "flex", flexDirection: "column", gap: "16px", minWidth: 0 }}
    >
      <OrciaPageHeader
        testId="cockpit-page-header"
        icon={ORCIA_MODULE_ICON_NAMES.cockpit}
        title={dictionary.fourZoneShell.menuEntries.cockpit}
        subtitle={dictionary.modulePages.cockpit.subtitle}
      />

      {/* Major Block 1: Onboarding */}
      <OrciaDataCard testId="cockpit-block-accostage">
        <ProgressiveDay0AccostageBanner
          completedCount={completedSetupStepsCount}
          totalCount={6}
          defaultCompact={showGovernanceSection}
          canConfigurePlatform={canConfigurePlatform}
          adminCreated={accostageSummary.adminCreated}
          adminDisplayName={realPlatformAdminDisplayName}
          adminEmail={realPlatformAdminEmail}
          milestones={milestones}
          labels={dictionary.progressiveAccostage}
          onNavigateMilestone={(href) => navigateToRoute(href)}
        />
      </OrciaDataCard>

      {/* Major Block 2: Overview & Process Launch */}
      <section
        data-testid="cockpit-block-decisions"
        className="flex flex-col gap-4"
        style={{ minWidth: 0 }}
      >
        <StreamlinedCockpitView
          decisions={scopedRuns.map((r) => ({
            decisionId: `dec-${r.runId}`,
            kind: "REVIEW_BRIEFING" as const,
            runId: r.runId,
            stepExecutionId: r.currentStepKey,
            title: r.title,
            summary: `${r.workspaceName} · ${r.currentStepKey}`,
          }))}
          currentUserId={currentUserId}
          labels={dictionary.streamlinedCockpit}
          disabledMenuKeys={effectiveDisabledMenuKeys}
          onNavigateModule={(href) => navigateToRoute(href)}
        />

        <CockpitRunsSection
          isFr={isFr}
          workspaces={workspaces}
          availableWorkspaces={availableWorkspaces}
          workflows={workflows}
          scopedRuns={scopedRuns}
          selectedWsId={selectedWsId}
          selectedWfKey={selectedWfKey}
          runTitle={runTitle}
          onSelectWsId={setSelectedWsId}
          onSelectWfKey={setSelectedWfKey}
          onChangeRunTitle={setRunTitle}
          onLaunchRun={handleLaunchRun}
          onNavigateToWorkspaces={() => navigateToRoute("/spaces")}
        />

        {challengeError && (
          <OrciaAlertBanner tone="crimson" role="alert" testId="cockpit-challenge-error-banner">
            {challengeError}
          </OrciaAlertBanner>
        )}

        {challengeTarget && (
          <CockpitUpstreamChallengePanel
            runId={challengeTarget.runId}
            isOpen={true}
            initialStaleWarning={challengeTarget.hasStaleWarning}
            onError={setChallengeError}
            onReplayCompleted={() => setRunRefreshSignal((n) => n + 1)}
          />
        )}
      </section>

      {/* Major Block 3: Human-Led Governance & Arbitration (mounted only on pending PG18 action) */}
      {pendingGovernance && (
        <div data-testid="cockpit-block-governance" style={{ minWidth: 0 }}>
          <CockpitHumanLedGovernanceSection
            runId={pendingGovernance.runId}
            workflow={pendingGovernance.workflow}
            initialBlackboard={pendingGovernance.initialBlackboard}
            authorName={resolvedAuthorName}
            refreshSignal={runRefreshSignal}
            onGovernanceStateChanged={() => setRunRefreshSignal((n) => n + 1)}
          />
        </div>
      )}
    </div>
  );
}
