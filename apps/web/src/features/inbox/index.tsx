import { AssistantSpeedSelectorAndStreamView } from "@orcia/ui";
import React from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { formatI18nTemplate } from "../../i18n";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import {
  buildAssistantCitationCardPreview,
  buildInboxStreamSlots,
  InboxBottomPanelsAndInspector,
  InboxTopSection,
} from "./InboxActiveTraceAndTurns";
import { InboxDisabledBanner } from "./InboxDisabledBanner";
import { InboxNotificationsCenterView } from "./InboxNotificationsCenterView";
import { citationMapToRagItems } from "./inboxCitationHelpers";
import {
  ASSISTANT_REFLEXIVE_STORAGE_KEY,
  useInboxPanelController,
} from "./useInboxPanelController";
import { usePermissionBrokerTickets } from "./usePermissionBrokerTickets";

export { ASSISTANT_REFLEXIVE_STORAGE_KEY };

export interface InboxFeaturePanelProps {
  readonly mode?: "assistant" | "notifications";
}

export function InboxFeaturePanel({ mode = "assistant" }: InboxFeaturePanelProps = {}) {
  if (mode === "notifications") {
    return <InboxNotificationsCenterView />;
  }
  return <AssistantInboxFeatureContent />;
}

function AssistantInboxFeatureContent() {
  const { navigateToRoute, openHelpSection } = useShellNavigation();
  const ctrl = useInboxPanelController();
  const {
    dictionary, isFr, authorEmail, activeWorkspaceId,
    hasActiveEmbeddingModel, hasActiveChatModel, supportsTools, ragReindex, assistantInputBlocked,
    prefillPrompt, setPrefillPrompt, activeFolderId, activeFolder,
    governancePrefs, governance, foldersPanelOpen, setFoldersPanelOpen,
    savedConversationsOpen, setSavedConversationsOpen, savedConversations,
    activeConversationId, activeConversation, promptTelemetryLog,
    governanceOpen, setGovernanceOpen, governanceFeedback, setGovernanceFeedback,
    foldersController, threads, inspector, streaming,
    modelOptions, agentOptions, skillOptions, orciaDocuments, autocompleteSuggestions,
    selectActiveConversationAndPersist, selectActiveFolderAndPersist,
    handleFeedbackTurn, handleSendTurnWithReflexive, handleDeepenTurn, handleStopAll, handleDeleteConversation,
  } = ctrl;

  const broker = usePermissionBrokerTickets({
    workspaceId: activeWorkspaceId,
    isFr,
    onFeedback: setGovernanceFeedback,
  });

  const disabledReasonBannerNode = (
    <InboxDisabledBanner
      hasActiveChatModel={hasActiveChatModel}
      hasActiveEmbeddingModel={hasActiveEmbeddingModel}
      isReindexing={ragReindex.isReindexing}
      isReindexFailed={ragReindex.isReindexFailed}
      progressPercentage={ragReindex.progressPercentage}
      errorMessage={ragReindex.errorMessage}
      noChatLabels={dictionary.assistantNoChatModel}
      ragNoticeLabels={dictionary.assistantRagNotice}
      onRelaunchReindex={() => {
        void ragReindex.relaunchReindex();
      }}
      onNavigateAiModels={() => navigateToRoute("/settings/ai-models")}
    />
  );

  const latestTurnInActiveConv =
    activeConversation?.turns[activeConversation.turns.length - 1] ?? null;

  const activeCitationMap = streaming.citationMap ?? latestTurnInActiveConv?.citationMap ?? null;
  const activeRagCitations =
    latestTurnInActiveConv?.usedSources ?? citationMapToRagItems(activeCitationMap);

  const citationCardPreview = buildAssistantCitationCardPreview({
    isGenerating: streaming.isGenerating,
    replyText: latestTurnInActiveConv?.assistantReply ?? streaming.streamedText ?? "",
    citationMap: activeCitationMap,
    activeFolderTitle: activeFolder?.title ?? null,
    isFr,
    onInspectCitationUri: inspector.openInspectCitationUri,
    onRequestRestrictedAccess: () => navigateToRoute("/permissions"),
  });

  const showActiveReflexiveSlot = Boolean(
    streaming.activeTraceStatus &&
      (streaming.traceEvents.length > 0 || streaming.pendingWritePreview) &&
      (streaming.isGenerating ||
        streaming.activeTraceStatus !== "COMPLETED" ||
        latestTurnInActiveConv?.reflexiveExecutionId !== streaming.activeTurnId),
  );

  const { activeReflexiveNode, previousTurnsNode } = buildInboxStreamSlots({
    showActiveReflexiveSlot,
    reflexiveStatus: streaming.activeTraceStatus,
    reflexiveEvents: streaming.traceEvents,
    toolCallSteps: streaming.toolCallSteps,
    approvalProposal: streaming.approvalProposal,
    approvalBusy: streaming.approvalBusy,
    pendingWritePreview: streaming.pendingWritePreview,
    activeConversation,
    isFr,
    isGenerating: streaming.isGenerating,
    supportsTools,
    dictionary,
    onInspectLines: inspector.openInspectTarget,
    onInspectCitationUri: inspector.openInspectCitationUri,
    onSynthesizeNow: () => void streaming.synthesizeNow(),
    onApproveProposal: (id, anchor) => void streaming.approveProposal(id, anchor),
    onRejectProposal: (id, rationale) => void streaming.rejectProposal(id, rationale),
    onOpenProcess: () => navigateToRoute("/processes"),
    onSendTurn: handleSendTurnWithReflexive,
    onDeepenTurn: handleDeepenTurn,
    onContinueInProcess: () => navigateToRoute("/processes"),
    onFeedbackTurn: handleFeedbackTurn,
  });

  const handleDeepenActive =
    supportsTools && !streaming.isGenerating && (latestTurnInActiveConv || streaming.activeTurnId)
      ? () => {
          if (latestTurnInActiveConv) {
            handleDeepenTurn(latestTurnInActiveConv);
          } else if (streaming.activeTurnId) {
            handleSendTurnWithReflexive({
              userPrompt: streaming.activeUserPrompt,
              requestedSpeed: "SPEED_2_AGENT_TOOLS",
              deepAuditPillActive: false,
              parentTurnId: streaming.activeTurnId,
            });
          }
        }
      : undefined;

  return (
    <div className="space-y-4" data-testid="inbox-feature-panel">
      <InboxTopSection
        isFr={isFr}
        governanceFeedback={governanceFeedback}
        savedConversations={savedConversations}
        activeConversationId={activeConversationId}
        foldersCount={foldersController.folders.length}
        savedConversationsOpen={savedConversationsOpen}
        foldersPanelOpen={foldersPanelOpen}
        dictionary={dictionary}
        broker={broker}
        onNewConversation={() => {
          threads.startNewThread();
          streaming.resetStreamState("");
        }}
        onToggleSavedConversations={() => setSavedConversationsOpen((prev) => !prev)}
        onToggleFoldersPanel={() => setFoldersPanelOpen((prev) => !prev)}
        onToggleGovernanceModal={() => {
          setGovernanceOpen((prev) => {
            const next = !prev;
            if (next) void governance.refreshGovernance();
            return next;
          });
        }}
        onOpenHelpSection={openHelpSection}
        onResumeConversation={(convId) => {
          const target = savedConversations.find((c) => c.id === convId);
          if (!target) return;
          selectActiveConversationAndPersist(target.id);
          void threads.loadThreadMessages(target.id);
          const latestTurn = target.turns[target.turns.length - 1];
          streaming.resetStreamState(latestTurn?.assistantReply ?? "");
          setSavedConversationsOpen(false);
        }}
        onDeleteConversation={handleDeleteConversation}
      />

      <div className="orcia-bento-card space-y-3">
        <AssistantSpeedSelectorAndStreamView
          workspaceId={activeWorkspaceId}
          userId={authorEmail}
          hat={governancePrefs.defaultHat}
          supportsTools={supportsTools}
          lowEvidence={Boolean(streaming.lowEvidence || latestTurnInActiveConv?.lowEvidence)}
          modelOptions={modelOptions}
          agentOptions={agentOptions}
          skillOptions={skillOptions}
          orciaDocuments={orciaDocuments}
          ragCitations={activeRagCitations}
          autocompleteSuggestions={autocompleteSuggestions}
          prefillPrompt={prefillPrompt}
          onPrefillConsumed={() => setPrefillPrompt(null)}
          activeFolderTitle={activeFolder?.title ?? null}
          activeFolderNotes={activeFolder?.pinnedNotesMarkdown ?? null}
          onClearActiveFolder={() => selectActiveFolderAndPersist("")}
          reflexiveTraceSlot={activeReflexiveNode}
          previousTurnsSlot={previousTurnsNode}
          welcomeTitle={dictionary.featureInboxAssistant.assistantFlow.welcomeTitle}
          showWelcomeHero={
            !showActiveReflexiveSlot &&
            (!activeConversation || activeConversation.turns.length === 0)
          }
          hideTechnicalCacheHeader={true}
          hideLegacySpeedPills={true}
          hideDuplicateCompletedStream={Boolean(
            !streaming.isGenerating &&
              activeConversation &&
              activeConversation.turns.length > 0,
          )}
          cacheHit={streaming.cacheHit}
          cacheLookupMs={streaming.cacheLookupMs}
          nodes1To4DeterministicMs={streaming.nodes1To4Ms}
          ttftMs={streaming.ttftMs}
          stepProgress={streaming.stepProgress}
          streamedText={streaming.streamedText}
          activeUserPrompt={streaming.activeUserPrompt}
          isGenerating={streaming.isGenerating}
          initialElapsedSeconds={streaming.initialElapsedSeconds}
          generationStopped={streaming.generationStopped}
          errorMessage={streaming.errorMessage}
          errorKind={streaming.errorKind}
          reconnectCtaLabel={dictionary.assistantStreamErrors.reconnectCta}
          onReconnect={() => {
            useAuthSessionStore.getState().setAuthSession({
              isAuthenticated: false,
              isHydrating: false,
              accessToken: null,
            });
            navigateToRoute("/login");
          }}
          currentTurnFeedback={latestTurnInActiveConv?.userFeedback ?? null}
          onFeedbackLastTurn={(fb) => {
            if (latestTurnInActiveConv) handleFeedbackTurn(latestTurnInActiveConv.turnId, fb);
          }}
          onDeepenLastTurn={handleDeepenActive}
          labels={dictionary.assistantSpeedStream}
          disabled={assistantInputBlocked}
          disabledReasonBanner={disabledReasonBannerNode}
          onOpenFoldersFromPlus={() => setFoldersPanelOpen((prev) => !prev)}
          onStopGeneration={handleStopAll}
          onContinueInProcessFromResponse={() => navigateToRoute("/processes")}
          onInspectCitation={(src) => inspector.openInspectCitationUri(src.uri, src.title)}
          onSendTurn={(payload) => {
            if (assistantInputBlocked) return;
            handleSendTurnWithReflexive(payload);
          }}
        />
      </div>

      <InboxBottomPanelsAndInspector
        inspector={inspector}
        labels={dictionary.sourceLineInspector}
        auxiliaryProps={{
          isFr,
          activeWorkspaceId,
          activeFolderId,
          foldersPanelOpen,
          governanceOpen,
          governancePrefs,
          canEditWorkspaceLayer: governance.canEditWorkspaceLayer,
          mcpFrozenByUpperLayer: governance.mcpFrozenByUpperLayer,
          mcpIdeConfigJson: governance.mcpIdeConfigJson,
          assembledLayers: governance.assembledLayers,
          promptTelemetryLog,
          folders: foldersController.folders,
          authorIdentity: authorEmail,
          dictionary,
          setGovernanceOpen,
          setGovernanceFeedback,
          onSaveUserPreferences: governance.saveUserPreferences,
          onSaveWorkspaceSettings: governance.saveWorkspaceSettings,
          selectActiveFolderAndPersist,
          createFolder: foldersController.createFolder,
          savePinnedNotes: foldersController.savePinnedNotes,
          changeVisibility: foldersController.changeVisibility,
          onOpenHelpSection: openHelpSection,
          onSendCollaborativeMessage: (message) =>
            streaming.setStreamedText(
              formatI18nTemplate(
                dictionary.featureInboxAssistant.assistantFlow.collaborativeMessageAddedTemplate,
                { message },
              ),
            ),
          onLaunchProcessFromFolder: (folderId, targetWorkflowUri) => {
            void foldersController.launchProcess(folderId, targetWorkflowUri).then((launchedRunId) => {
              if (launchedRunId) navigateToRoute("/processes");
            });
          },
          onNavigateToProcesses: () => navigateToRoute("/processes"),
          citationCardPreview,
        }}
      />
    </div>
  );
}
