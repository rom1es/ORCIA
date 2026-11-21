import { AssistantSpeedSelectorAndStreamView } from "@orcia/ui";
import React from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import {
  buildAssistantCitationCardPreview,
  buildInboxStreamSlots,
  InboxBottomPanelsAndInspector,
  InboxTopSection,
} from "./InboxActiveTraceAndTurns";
import { InboxDisabledBanner } from "./InboxDisabledBanner";
import { InboxNotificationsCenterView } from "./InboxNotificationsCenterView";
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
    hasActiveEmbeddingModel, hasActiveChatModel, ragReindex, assistantInputBlocked,
    prefillPrompt, setPrefillPrompt, activeFolderId, activeFolder,
    governancePrefs, setGovernancePrefs, foldersPanelOpen, setFoldersPanelOpen,
    savedConversationsOpen, setSavedConversationsOpen, savedConversations,
    activeConversationId, activeConversation, promptTelemetryLog,
    governanceOpen, setGovernanceOpen, governanceFeedback, setGovernanceFeedback,
    foldersController, inspector, reflexive, streaming,
    modelOptions, agentOptions, skillOptions, orciaDocuments, ragCitations, autocompleteSuggestions,
    selectActiveConversationAndPersist, selectActiveFolderAndPersist,
    handleFeedbackTurn, handleSendTurnWithReflexive, handleStopAll, handleDeleteConversation,
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

  const citationCardPreview = buildAssistantCitationCardPreview({
    isGenerating: streaming.isGenerating,
    replyText: latestTurnInActiveConv?.assistantReply ?? streaming.streamedText ?? "",
    activeSources: latestTurnInActiveConv?.usedSources ?? ragCitations,
    activeFolderTitle: activeFolder?.title ?? null,
    isFr,
    onInspectCitationUri: inspector.openInspectCitationUri,
  });

  const handleSaveDraftAction = (content: string) => {
    const excerpt = content.slice(0, 42).replace(/\s+/g, " ").trim();
    setGovernanceFeedback(
      isFr
        ? `✅ Brouillon « ${excerpt || "Réponse"} » enregistré dans votre Espace.`
        : `✅ Draft "${excerpt || "Reply"}" saved to your Workspace.`,
    );
  };

  const showActiveReflexiveSlot = Boolean(
    reflexive.status &&
      (reflexive.events.length > 0 || reflexive.pendingWritePreview) &&
      (streaming.isGenerating ||
        reflexive.status !== "COMPLETED" ||
        latestTurnInActiveConv?.reflexiveExecutionId !== reflexive.executionId),
  );

  const { activeReflexiveNode, previousTurnsNode } = buildInboxStreamSlots({
    showActiveReflexiveSlot,
    reflexiveStatus: reflexive.status,
    reflexiveEvents: reflexive.events,
    pendingWritePreview: reflexive.pendingWritePreview,
    activeConversation,
    isFr,
    isGenerating: streaming.isGenerating,
    ragCitations,
    traceLabels: dictionary.executionTrace,
    onInspectLines: inspector.openInspectTarget,
    onInspectCitationUri: inspector.openInspectCitationUri,
    onSynthesizeNow: () => void reflexive.synthesizeNow(),
    onApproveWrite: (id) => void reflexive.approveWrite(id),
    onRejectWrite: (id) => void reflexive.rejectWrite(id),
    onSendTurn: handleSendTurnWithReflexive,
    onSaveDraft: handleSaveDraftAction,
    onContinueInProcess: () => navigateToRoute("/processes"),
    onFeedbackTurn: handleFeedbackTurn,
  });

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
          selectActiveConversationAndPersist(null);
          reflexive.clearExecution();
          streaming.resetStreamState("");
        }}
        onToggleSavedConversations={() => setSavedConversationsOpen((prev) => !prev)}
        onToggleFoldersPanel={() => setFoldersPanelOpen((prev) => !prev)}
        onToggleGovernanceModal={() => setGovernanceOpen((prev) => !prev)}
        onOpenHelpSection={openHelpSection}
        onResumeConversation={(convId) => {
          const target = savedConversations.find((c) => c.id === convId);
          if (!target) return;
          selectActiveConversationAndPersist(target.id);
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
          modelOptions={modelOptions}
          agentOptions={agentOptions}
          skillOptions={skillOptions}
          orciaDocuments={orciaDocuments}
          ragCitations={ragCitations}
          autocompleteSuggestions={autocompleteSuggestions}
          prefillPrompt={prefillPrompt}
          onPrefillConsumed={() => setPrefillPrompt(null)}
          activeFolderTitle={activeFolder?.title ?? null}
          activeFolderNotes={activeFolder?.pinnedNotesMarkdown ?? null}
          onClearActiveFolder={() => selectActiveFolderAndPersist("")}
          reflexiveTraceSlot={activeReflexiveNode}
          previousTurnsSlot={previousTurnsNode}
          welcomeTitle={isFr ? "Par quoi voulez-vous commencer ?" : "Where would you like to start?"}
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
            if (latestTurnInActiveConv) {
              handleFeedbackTurn(latestTurnInActiveConv.turnId, fb);
            }
          }}
          labels={dictionary.assistantSpeedStream}
          disabled={assistantInputBlocked}
          disabledReasonBanner={disabledReasonBannerNode}
          onOpenFoldersFromPlus={() => setFoldersPanelOpen((prev) => !prev)}
          onStopGeneration={handleStopAll}
          onSaveDraftFromResponse={handleSaveDraftAction}
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
          promptTelemetryLog,
          folders: foldersController.folders,
          authorIdentity: authorEmail,
          dictionary,
          setGovernancePrefs,
          setGovernanceOpen,
          setGovernanceFeedback,
          selectActiveFolderAndPersist,
          createFolder: foldersController.createFolder,
          savePinnedNotes: foldersController.savePinnedNotes,
          changeVisibility: foldersController.changeVisibility,
          onOpenHelpSection: openHelpSection,
          onSendCollaborativeMessage: (message) =>
            streaming.setStreamedText(
              isFr
                ? `💬 Message ajouté à la discussion : ${message}`
                : `💬 Message added to thread: ${message}`,
            ),
          onNavigateToProcesses: () => navigateToRoute("/processes"),
          onSaveDraftAction: handleSaveDraftAction,
          citationCardPreview,
        }}
      />
    </div>
  );
}
