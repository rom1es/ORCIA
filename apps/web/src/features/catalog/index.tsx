import {
  AgentExecutionTrace,
  AgentsAndSkillsManagerView,
  CatalogExplorerPanel,
  OrciaAlertBanner,
  RemoteServiceTestBenchAndMcpExposureView,
  SourceLineInspectorDrawer,
} from "@orcia/ui";
import React, { useCallback, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import {
  type AlertFeedback,
  type AlertFeedbackInput,
  normalizeAlertFeedback,
} from "../shared/alertFeedback";
import { useReflexiveExecutionController } from "../shared/useReflexiveExecutionController";
import { useSourceLineInspector } from "../shared/useSourceLineInspector";
import {
  AGENTS_AND_SKILLS_STORAGE_KEY,
  ASSISTANT_PREFILL_PROMPT_STORAGE_KEY,
  consumeAssistantPrefillPrompt,
  readCachedAgentsAndSkills,
  resetCachedAgentsAndSkillsForTest,
  writeAssistantPrefillPrompt,
} from "./packAgentsCatalog";
import { useCatalogRemoteTestBench } from "./useCatalogRemoteTestBench";
import { useManagedAgentsAndSkills } from "./useManagedAgentsAndSkills";

export {
  AGENTS_AND_SKILLS_STORAGE_KEY,
  ASSISTANT_PREFILL_PROMPT_STORAGE_KEY,
  consumeAssistantPrefillPrompt,
  readCachedAgentsAndSkills,
  resetCachedAgentsAndSkillsForTest,
  writeAssistantPrefillPrompt,
};

export const CATALOG_SANDBOX_REFLEXIVE_STORAGE_KEY =
  "orcia.reflexive_exec.catalog_sandbox.v1";

export interface CatalogFeaturePanelProps {
  readonly catalogMode?: "catalog" | "agents";
}

export function CatalogFeaturePanel({
  catalogMode = "agents",
}: CatalogFeaturePanelProps = {}) {
  const { dictionary, isFr, locale } = useI18n();
  const catCopy = dictionary.featureAdminCatalogSettings.catalog;
  const { catalogItems, datasources, packs, workspaces } = usePlatformSetup();
  const { activeScopeId, navigateToRoute } = useShellNavigation();
  const authEmail = useAuthSessionStore((s) => s.email);
  const activeWorkspaceId = resolveEffectiveWorkspaceId(activeScopeId, workspaces, authEmail);
  const activeWorkspaceObj =
    workspaces.find((w) => w.workspaceId === activeWorkspaceId) ?? workspaces[0];
  const [pinnedAssistantMcpExposed, setPinnedAssistantMcpExposed] =
    useState<boolean>(false);
  const [catalogActionFeedback, setCatalogActionFeedbackRaw] = useState<
    AlertFeedback | null
  >(null);
  const setCatalogActionFeedback = useCallback((next: AlertFeedbackInput) => {
    setCatalogActionFeedbackRaw(normalizeAlertFeedback(next));
  }, []);

  const activeWorkspaceSlug =
    activeWorkspaceObj?.slug || activeWorkspaceObj?.workspaceId || "global";
  const remoteBench = useCatalogRemoteTestBench({
    datasources,
    workspaceSlug: activeWorkspaceSlug,
    isFr,
    setFeedback: setCatalogActionFeedback,
  });

  const inspector = useSourceLineInspector({
    locale,
    workspaceId: activeWorkspaceId,
    onFeedback: setCatalogActionFeedback,
  });

  const sandboxReflexive = useReflexiveExecutionController({
    storageKey: CATALOG_SANDBOX_REFLEXIVE_STORAGE_KEY,
    locale,
    onFeedback: setCatalogActionFeedback,
  });

  const managed = useManagedAgentsAndSkills(packs, setCatalogActionFeedback, locale, catCopy);

  const handleExecuteAgentWithTrace = (agentId: string, prompt: string) => {
    managed.handleExecuteAgent(agentId, prompt);
    const targetAgent = managed.agents.find((a) => a.agentId === agentId);
    const isComplex = targetAgent?.thinkingLevel === "complex";
    void sandboxReflexive.startExecution({
      actor_slug: targetAgent?.slug || "assistant",
      objective: prompt,
      effort_level: isComplex ? "high" : "medium",
      effort_mode: isComplex ? "approfondi" : "standard",
      allow_sub_agent_delegation: true,
      initial_resources: ["docs/product/capabilities.yaml"],
      ...(activeWorkspaceId ? { workspace_id: activeWorkspaceId } : {}),
    });
  };

  const feedbackBanner = catalogActionFeedback ? (
    <OrciaAlertBanner
      testId="catalog-action-feedback-banner"
      tone={catalogActionFeedback.tone}
      role={catalogActionFeedback.tone === "crimson" ? "alert" : "status"}
    >
      {catalogActionFeedback.message}
    </OrciaAlertBanner>
  ) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {catalogMode === "catalog" ? feedbackBanner : null}

      {catalogMode === "catalog" ? (
        <>
          <CatalogExplorerPanel
            activePersona="marc"
            items={[...catalogItems]}
            runLockTriplets={[]}
            labels={dictionary.catalogExplorer}
          />
          {catalogItems.length === 0 && (
            <div
              data-testid="catalog-setup-guidance-card"
              className="orcia-bento-card flex flex-wrap items-center justify-between gap-3"
            >
              <div>
                <strong>{catCopy.emptySetupTitle}</strong>
              </div>
              <button
                type="button"
                data-testid="catalog-go-settings-btn"
                onClick={() => navigateToRoute("/settings")}
                className="orcia-ds-btn orcia-ds-btn-secondary"
              >
                {catCopy.openAdminBtn}
              </button>
            </div>
          )}
        </>
      ) : (
        <AgentsAndSkillsManagerView
          agents={managed.agents}
          skills={managed.skills}
          labels={dictionary.agentsAndSkillsManager}
          alertSlot={feedbackBanner}
          onCreateAgent={managed.handleCreateAgent}
          onDuplicateAgent={managed.handleDuplicateAgent}
          onToggleAgentEnabled={managed.handleToggleAgentEnabled}
          onToggleAgentMcpExposure={managed.handleToggleAgentMcpExposure}
          onUpdateAgentDetails={managed.handleUpdateAgentDetails}
          onToggleAgentSkill={managed.handleToggleAgentSkill}
          onUpdateAgentThinkingLevel={managed.handleUpdateAgentThinkingLevel}
          onUpdateAgentVisibility={managed.handleUpdateAgentVisibility}
          onDeleteAgent={managed.handleDeleteAgent}
          onExecuteAgent={handleExecuteAgentWithTrace}
          renderAgentSandboxSlot={() =>
            sandboxReflexive.status &&
            (sandboxReflexive.events.length > 0 ||
              sandboxReflexive.pendingWritePreview) ? (
              <AgentExecutionTrace
                status={sandboxReflexive.status}
                events={sandboxReflexive.events}
                pendingWritePreview={sandboxReflexive.pendingWritePreview}
                labels={dictionary.executionTrace}
                defaultCollapsedWhenCompleted={false}
                onInspectLines={inspector.openInspectTarget}
                onSynthesizeNow={() => {
                  void sandboxReflexive.synthesizeNow();
                }}
                onApproveWrite={(previewId) => {
                  void sandboxReflexive.approveWrite(previewId);
                }}
                onRejectWrite={(previewId) => {
                  void sandboxReflexive.rejectWrite(previewId);
                }}
              />
            ) : null
          }
          onUseAgentInAssistant={(agent) => {
            writeAssistantPrefillPrompt(`${agent.handle} `);
            navigateToRoute("/assistant");
          }}
          onCreateSkill={managed.handleCreateSkill}
          onUpdateSkillVisibility={managed.handleUpdateSkillVisibility}
          onDeleteSkill={managed.handleDeleteSkill}
          onExecuteSkill={managed.handleExecuteSkill}
          onUseSkillInAssistant={(skill) => {
            writeAssistantPrefillPrompt(`${skill.commandHandle} `);
            navigateToRoute("/assistant");
          }}
          onLoadPackTemplates={managed.handleLoadPackTemplates}
          onOpenMcpTestBench={remoteBench.handleRunRemoteTestBench}
          pinnedAssistantMcpExposed={pinnedAssistantMcpExposed}
          onTogglePinnedAssistantMcp={(next) => {
            setPinnedAssistantMcpExposed(next);
            setCatalogActionFeedback(
              next ? catCopy.pinnedMcpEnabledBanner : catCopy.pinnedMcpDisabledBanner,
            );
          }}
          onOpenAssistantSettings={() => navigateToRoute("/assistant")}
          onOpenAssistant={() => navigateToRoute("/assistant")}
          connectionsContent={
            <RemoteServiceTestBenchAndMcpExposureView
              endpointUrl={datasources[0]?.uri ?? ""}
              steps={remoteBench.testBenchSteps}
              discoveredCapabilities={remoteBench.discoveredCapabilities}
              canActivate={
                remoteBench.canActivateConnector || datasources.length > 0
              }
              mcpExposed={remoteBench.mcpExposed}
              isTesting={remoteBench.isTesting}
              isSavingMcp={remoteBench.isSavingMcp}
              exposedToolNames={Array.from(
                new Set([
                  ...remoteBench.exposedToolNames,
                  ...catalogItems.map((item) => item.resourceId),
                ]),
              )}
              labels={dictionary.remoteServiceTestBench}
              onRunTestBench={remoteBench.handleRunRemoteTestBench}
              onActivateService={remoteBench.handleActivateRemoteService}
              onToggleMcpExposure={remoteBench.handleToggleMcp}
            />
          }
        />
      )}

      <SourceLineInspectorDrawer
        open={inspector.inspectorState.open}
        onOpenChange={inspector.setInspectorOpen}
        resourceUri={inspector.inspectorState.resourceUri}
        displayFilename={inspector.inspectorState.displayFilename}
        fileBadgeCode={inspector.inspectorState.fileBadgeCode}
        startLine={inspector.inspectorState.startLine}
        endLine={inspector.inspectorState.endLine}
        totalLines={inspector.inspectorState.totalLines}
        lines={inspector.inspectorState.lines}
        isLoading={inspector.inspectorState.isLoading}
        redacted={inspector.inspectorState.redacted}
        redactedReason={inspector.inspectorState.redactedReason}
        permissionRequestHint={inspector.inspectorState.permissionRequestHint}
        errorMessage={inspector.inspectorState.errorMessage}
        copiedFeedback={inspector.inspectorState.copiedFeedback}
        labels={dictionary.sourceLineInspector}
        onCopySlice={inspector.copyCurrentSlice}
      />
    </div>
  );
}
