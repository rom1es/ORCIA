import {
  AgentExecutionTrace,
  AssistantSpeedSelectorAndStreamView,
  PermissionBrokerCard,
  SourceLineInspectorDrawer,
} from "@orcia/ui";
import React from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { AssistantNoEmbeddingBanner } from "./AssistantNoEmbeddingBanner";
import { AssistantReindexingBanner } from "./AssistantReindexingBanner";
import { InboxAuxiliaryPanels } from "./InboxAuxiliaryPanels";
import { InboxNotificationsCenterView } from "./InboxNotificationsCenterView";
import {
  ActiveConversationMessagesView,
  AssistantTopToolbar,
  SavedConversationsPanel,
} from "./SavedConversationsAndThreadView";
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
    dictionary,
    isFr,
    authorEmail,
    activeWorkspaceId,
    hasActiveEmbeddingModel,
    ragReindex,
    assistantInputBlocked,
    prefillPrompt,
    setPrefillPrompt,
    activeFolderId,
    activeFolder,
    governancePrefs,
    setGovernancePrefs,
    foldersPanelOpen,
    setFoldersPanelOpen,
    savedConversationsOpen,
    setSavedConversationsOpen,
    savedConversations,
    activeConversationId,
    activeConversation,
    promptTelemetryLog,
    governanceOpen,
    setGovernanceOpen,
    governanceFeedback,
    setGovernanceFeedback,
    foldersController,
    inspector,
    reflexive,
    streaming,
    modelOptions,
    agentOptions,
    skillOptions,
    orciaDocuments,
    ragCitations,
    autocompleteSuggestions,
    selectActiveConversationAndPersist,
    selectActiveFolderAndPersist,
    handleFeedbackTurn,
    handleSendTurnWithReflexive,
    handleStopAll,
    handleDeleteConversation,
  } = ctrl;

  const broker = usePermissionBrokerTickets({
    workspaceId: activeWorkspaceId,
    isFr,
    onFeedback: setGovernanceFeedback,
  });

  const disabledReasonBannerNode = !hasActiveEmbeddingModel ? (
    <AssistantNoEmbeddingBanner
      title={dictionary.assistantNoEmbeddingModel.bannerTitle}
      description={dictionary.assistantNoEmbeddingModel.bannerDescription}
      configureCta={dictionary.assistantNoEmbeddingModel.configureCta}
      onConfigure={() => navigateToRoute("/settings/ai-models")}
    />
  ) : ragReindex.isReindexing ? (
    <AssistantReindexingBanner
      status="IN_PROGRESS"
      progressPercentage={ragReindex.progressPercentage}
      isFr={isFr}
      onConfigure={() => navigateToRoute("/settings/ai-models")}
    />
  ) : ragReindex.isReindexFailed ? (
    <AssistantReindexingBanner
      status="FAILED"
      progressPercentage={ragReindex.progressPercentage}
      errorMessage={ragReindex.errorMessage}
      isFr={isFr}
      onRelaunch={() => {
        void ragReindex.relaunchReindex();
      }}
      onConfigure={() => navigateToRoute("/settings/ai-models")}
    />
  ) : null;

  const latestTurnInActiveConv =
    activeConversation?.turns[activeConversation.turns.length - 1] ?? null;

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

  const activeReflexiveNode = showActiveReflexiveSlot ? (
    <AgentExecutionTrace
      status={reflexive.status!}
      events={reflexive.events}
      pendingWritePreview={reflexive.pendingWritePreview}
      labels={dictionary.executionTrace}
      defaultCollapsedWhenCompleted={false}
      onInspectLines={inspector.openInspectTarget}
      onSynthesizeNow={() => {
        void reflexive.synthesizeNow();
      }}
      onApproveWrite={(previewId) => {
        void reflexive.approveWrite(previewId);
      }}
      onRejectWrite={(previewId) => {
        void reflexive.rejectWrite(previewId);
      }}
    />
  ) : null;

  const previousTurnsNode =
    activeConversation && activeConversation.turns.length > 0 ? (
      <ActiveConversationMessagesView
        conversation={activeConversation}
        isFr={isFr}
        isGenerating={streaming.isGenerating}
        ragCitations={ragCitations}
        traceLabels={dictionary.executionTrace}
        onInspectLines={inspector.openInspectTarget}
        onInspectCitation={(src) =>
          inspector.openInspectCitationUri(src.uri, src.title)
        }
        onSynthesizeNow={() => {
          void reflexive.synthesizeNow();
        }}
        onApproveWrite={(id) => {
          void reflexive.approveWrite(id);
        }}
        onRejectWrite={(id) => {
          void reflexive.rejectWrite(id);
        }}
        onRegenerateTurn={(userPrompt) =>
          handleSendTurnWithReflexive({
            userPrompt,
            requestedSpeed: "SPEED_1_FAST",
            deepAuditPillActive: false,
          })
        }
        onSaveDraft={handleSaveDraftAction}
        onContinueInProcess={() => navigateToRoute("/processes")}
        onFeedbackTurn={handleFeedbackTurn}
      />
    ) : null;

  return (
    <div className="space-y-4" data-testid="inbox-feature-panel">
      {governanceFeedback ? (
        <div
          role="status"
          data-testid="assistant-governance-feedback-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          {governanceFeedback}
        </div>
      ) : null}

      <AssistantTopToolbar
        isFr={isFr}
        savedCount={savedConversations.length}
        foldersCount={foldersController.folders.length}
        savedConversationsOpen={savedConversationsOpen}
        foldersPanelOpen={foldersPanelOpen}
        governanceModalTitle={dictionary.assistantGovernance.modalTitle}
        onNewConversation={() => {
          selectActiveConversationAndPersist(null);
          reflexive.clearExecution();
          streaming.resetStreamState("");
        }}
        onToggleSavedConversations={() =>
          setSavedConversationsOpen((prev) => !prev)
        }
        onToggleFoldersPanel={() => setFoldersPanelOpen((prev) => !prev)}
        onToggleGovernanceModal={() => setGovernanceOpen((prev) => !prev)}
        onOpenHelpSection={openHelpSection}
      />

      {broker.activeTicket ? (
        <PermissionBrokerCard
          ticket={broker.activeTicket}
          labels={dictionary.permissionBroker}
          onPauseStep={broker.pauseTicket}
          onReplayStep={broker.replayTicket}
        />
      ) : null}

      {savedConversationsOpen && (
        <SavedConversationsPanel
          conversations={savedConversations}
          activeConversationId={activeConversationId}
          isFr={isFr}
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
      )}

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
          welcomeTitle={
            isFr
              ? "Par quoi voulez-vous commencer ?"
              : "Where would you like to start?"
          }
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
          onInspectCitation={(src) =>
            inspector.openInspectCitationUri(src.uri, src.title)
          }
          onSendTurn={(payload) => {
            if (assistantInputBlocked) return;
            handleSendTurnWithReflexive(payload);
          }}
        />
      </div>

      <InboxAuxiliaryPanels
        isFr={isFr}
        activeWorkspaceId={activeWorkspaceId}
        activeFolderId={activeFolderId}
        foldersPanelOpen={foldersPanelOpen}
        governanceOpen={governanceOpen}
        governancePrefs={governancePrefs}
        promptTelemetryLog={promptTelemetryLog}
        folders={foldersController.folders}
        authorIdentity={authorEmail}
        dictionary={dictionary}
        setGovernancePrefs={setGovernancePrefs}
        setGovernanceOpen={setGovernanceOpen}
        setGovernanceFeedback={setGovernanceFeedback}
        selectActiveFolderAndPersist={selectActiveFolderAndPersist}
        createFolder={foldersController.createFolder}
        savePinnedNotes={foldersController.savePinnedNotes}
        changeVisibility={foldersController.changeVisibility}
        onOpenHelpSection={openHelpSection}
        onSendCollaborativeMessage={(message) =>
          streaming.setStreamedText(
            isFr
              ? `💬 Message ajouté à la discussion : ${message}`
              : `💬 Message added to thread: ${message}`,
          )
        }
        onNavigateToProcesses={() => navigateToRoute("/processes")}
        onSaveDraftAction={handleSaveDraftAction}
      />

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
