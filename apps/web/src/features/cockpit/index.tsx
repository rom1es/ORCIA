import { createOrciaApiClient } from "@orcia/api-client";
import {
  ContextualInfoTriggerButton,
  ProgressiveDay0AccostageBanner,
  StreamlinedCockpitView,
} from "@orcia/ui";
import type { Edge, Node } from "@xyflow/react";
import React, { useEffect, useState } from "react";
import { writeAssistantPrefillPrompt } from "../../components/agentsAndSkillsBridgeStore";
import { buildUnifiedAccostageMilestones } from "../../components/platformSetupAccostage";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { buildShellDisabledMenuKeys } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import {
  isPlatformAdministratorSession,
  useAuthSessionStore,
} from "../../stores/authSessionStore";
import { CockpitHumanLedGovernanceSection } from "./CockpitHumanLedGovernanceSection";
import { CockpitRunsSection } from "./CockpitRunsSection";

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
  const { dictionary, locale } = useI18n();
  const {
    activeScopeId,
    navigateToRoute,
    openHelpSection,
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
  const [latestRunId, setLatestRunId] = useState<string | null>(null);
  const [hasServerGovernance, setHasServerGovernance] = useState<boolean>(false);

  const isFr = locale === "fr";
  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);
  const activeScopeName =
    activeScopeNode?.name ?? (isFr ? "Plateforme Globale ORCIA" : "Global Platform ORCIA");

  const scopedWorkspaces =
    activeScopeNode?.level === "WORKSPACE"
      ? workspaces.filter((ws) => ws.workspaceId === activeScopeId)
      : activeScopeNode?.level === "TEAM"
        ? workspaces.filter(
            (ws) => !ws.ownerOrgUnitId || ws.ownerOrgUnitId === activeScopeId,
          )
        : workspaces;
  const availableWorkspaces =
    scopedWorkspaces.length > 0 ? scopedWorkspaces : workspaces;

  const scopedRuns =
    activeScopeNode?.level === "WORKSPACE"
      ? runs.filter((r) => r.workspaceId === activeScopeId)
      : activeScopeNode?.level === "TEAM"
        ? runs.filter((r) =>
            availableWorkspaces.some((ws) => ws.workspaceId === r.workspaceId),
          )
        : runs;

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
        const res = await createOrciaApiClient({ baseUrl: "" }).instantiateWorkflowRun({
          workflow_uri: workflowUri,
          workspace_id: targetWs.workspaceId,
        });
        if (res?.run?.id) {
          setLatestRunId(res.run.id);
        }
        setRunRefreshSignal((n) => n + 1);
      } catch (err: unknown) {
        console.warn("[orcia/cockpit] failed to instantiate workflow run:", err);
      }
    })();
  };

  const governanceWorkspaceId =
    (activeScopeNode?.level === "WORKSPACE" ? activeScopeId : selectedWsId) ||
    scopedRuns[0]?.workspaceId ||
    undefined;

  useEffect(() => {
    if (isHydrating || !isAuthenticated) {
      setHasServerGovernance(false);
      return;
    }
    let cancelled = false;
    void createOrciaApiClient({ baseUrl: "" })
      .getOrchestrationState()
      .then((state) => {
        if (cancelled) return;
        const serverRuns = state.runs ?? [];
        const hasMatch = governanceWorkspaceId
          ? serverRuns.some((r) => r.workspace_id === governanceWorkspaceId)
          : serverRuns.length > 0;
        setHasServerGovernance(hasMatch || serverRuns.length > 0);
      })
      .catch((err: unknown) => {
        console.warn("[orcia/cockpit] failed to check orchestration state:", err);
        if (!cancelled) {
          setHasServerGovernance(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [governanceWorkspaceId, isAuthenticated, isHydrating, runRefreshSignal]);

  const showGovernanceSection =
    scopedRuns.length > 0 || runs.length > 0 || latestRunId !== null || hasServerGovernance;

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
      {/* Bloc majeur 1 : Accostage & Contexte actif */}
      <section
        data-testid="cockpit-block-accostage"
        className="flex flex-col gap-3 rounded-lg border p-3.5"
        style={{
          backgroundColor: "var(--color-bg-surface)",
          borderColor: "var(--color-border-subtle)",
        }}
      >
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <ContextualInfoTriggerButton
              sectionId="cockpit-decisions"
              label={
                isFr
                  ? "Comprendre le fonctionnement du Cockpit et des décisions"
                  : "Understand how the Cockpit and decisions work"
              }
              onOpenHelpSection={openHelpSection}
            />
          </div>
          <span
            data-testid="cockpit-active-scope-badge"
            className="max-w-full truncate rounded border px-2.5 py-0.5 text-xs font-medium"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          >
            {isFr ? `Contexte actif : ${activeScopeName}` : `Active context: ${activeScopeName}`}
          </span>
        </div>

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
      </section>

      {/* Bloc majeur 2 : Décisions & Lancement rapide de processus */}
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
          onOpenAssistant={(initialPrompt) => {
            if (initialPrompt.trim()) {
              writeAssistantPrefillPrompt(initialPrompt.trim());
            }
            navigateToRoute("/assistant");
          }}
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
      </section>

      {/* Bloc majeur 3 : Gouvernance Human-Led & Arbitrage (monté uniquement si run ou arbitrage actif) */}
      {showGovernanceSection && (
        <div data-testid="cockpit-block-governance" style={{ minWidth: 0 }}>
          <CockpitHumanLedGovernanceSection
            workspaceId={governanceWorkspaceId}
            authorName={resolvedAuthorName}
            refreshSignal={runRefreshSignal}
            activeRunId={latestRunId}
          />
        </div>
      )}
    </div>
  );
}
