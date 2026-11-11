import {
  AgentExecutionTrace,
  AgentsAndSkillsManagerView,
  CatalogExplorerPanel,
  RemoteServiceTestBenchAndMcpExposureView,
  SourceLineInspectorDrawer,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
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

export function CatalogFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { catalogItems, datasources, packs, workspaces } = usePlatformSetup();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";
  const activeWorkspaceId = workspaces[0]?.workspaceId ?? "";
  const [pinnedAssistantMcpExposed, setPinnedAssistantMcpExposed] =
    useState<boolean>(false);
  const [catalogActionFeedback, setCatalogActionFeedback] = useState<
    string | null
  >(null);

  const remoteBench = useCatalogRemoteTestBench({
    datasources,
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

  const managed = useManagedAgentsAndSkills(packs, setCatalogActionFeedback);

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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {catalogActionFeedback && (
        <div
          data-testid="catalog-action-feedback-banner"
          role="status"
          className="orcia-bento-card text-xs font-medium"
        >
          {catalogActionFeedback}
        </div>
      )}

      <AgentsAndSkillsManagerView
        agents={managed.agents}
        skills={managed.skills}
        labels={dictionary.agentsAndSkillsManager}
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
            next
              ? "🔌 Assistant de l'Espace (@assistant) exposé en MCP."
              : "🔌 Exposition MCP de l'Assistant de l'Espace désactivée.",
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
            exposedToolNames={catalogItems.map((item) => item.resourceId)}
            labels={dictionary.remoteServiceTestBench}
            onRunTestBench={remoteBench.handleRunRemoteTestBench}
            onActivateService={remoteBench.handleActivateRemoteService}
            onToggleMcpExposure={remoteBench.handleToggleMcp}
          />
        }
      />

      {catalogItems.length === 0 && (
        <div
          data-testid="catalog-setup-guidance-card"
          className="orcia-bento-card"
          style={{ display: "none" }}
        >
          <div>
            <strong>
              {isFr
                ? "Aucun Pack métier ni modèle de processus personnalisé"
                : "No custom Business Pack or process template yet"}
            </strong>
          </div>
          <button
            type="button"
            data-testid="catalog-go-settings-btn"
            onClick={() => navigateToRoute("/settings")}
          >
            {isFr ? "Ouvrir la Configuration" : "Open Configuration"}
          </button>
        </div>
      )}

      <div
        data-testid="catalog-explorer-panel-wrapper"
        style={{ display: "none" }}
      >
        <CatalogExplorerPanel
          activePersona="marc"
          items={[...catalogItems]}
          runLockTriplets={[]}
          labels={dictionary.catalogExplorer}
        />
      </div>

      <div
        data-testid="remote-service-test-bench-wrapper"
        style={{ display: "none" }}
      >
        <RemoteServiceTestBenchAndMcpExposureView
          endpointUrl={datasources[0]?.uri ?? ""}
          steps={remoteBench.testBenchSteps}
          discoveredCapabilities={remoteBench.discoveredCapabilities}
          canActivate={
            remoteBench.canActivateConnector || datasources.length > 0
          }
          mcpExposed={remoteBench.mcpExposed}
          exposedToolNames={catalogItems.map((item) => item.resourceId)}
          labels={dictionary.remoteServiceTestBench}
          onRunTestBench={remoteBench.handleRunRemoteTestBench}
          onActivateService={remoteBench.handleActivateRemoteService}
          onToggleMcpExposure={remoteBench.handleToggleMcp}
        />
      </div>

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
