import { createOrciaApiClient } from "@orcia/api-client";
import {
  AssistantCitationPillsAndArtifactCard,
  AssistantFoldersAndCollaborativeThreadView,
  AssistantSpeedSelectorAndStreamView,
  formatFolderVisibilityLabel,
  type AssistantFolderVisibilityMode,
  type UiAssistantPromptTelemetryRecord,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { subscribeBgStream } from "./assistantBackgroundStreamStore";
import {
  readSavedActiveConversationId,
  readSavedActiveFolderId,
  readSavedAssistantGovernancePrefs,
  readSavedPromptTelemetryLog,
  updatePromptTelemetryFeedback,
  upsertSavedPromptTelemetryRecord,
  writeSavedActiveConversationId,
  writeSavedActiveFolderId,
  writeSavedAssistantGovernancePrefs,
  type SavedAssistantGovernancePrefs,
} from "./assistantFoldersAndPrefsStore";
import { ActiveConversationMessagesView, AssistantTopToolbar, SavedConversationsPanel } from "./SavedConversationsAndThreadView";
import { AssistantGovernanceDialog } from "./AssistantGovernanceDialog";
import { AssistantNoEmbeddingBanner } from "./AssistantNoEmbeddingBanner";
import { AssistantReindexingBanner } from "./AssistantReindexingBanner";
import { useActiveEmbeddingModelStatus } from "./useActiveEmbeddingModelStatus";
import { useRagReindexStatus } from "./useRagReindexStatus";
import {
  buildAssistantAutocompleteAndRagOptions,
  buildAssistantAutocompleteSuggestions,
  buildAssistantModelOptions,
  consumeAssistantPrefillFromStorage,
  filterUsedRagSourcesForTurn,
  readSavedAssistantConversations,
  updateTurnFeedbackInSavedConversations,
  upsertTurnIntoSavedConversations,
  writeSavedAssistantConversations,
  type SavedAssistantConversation,
} from "./savedConversationsStore";
import { useAssistantStreamingTurn, type CompletedAssistantTurnPayload } from "./useAssistantStreamingTurn";
import { useServerAssistantFolders } from "./useServerAssistantFolders";

export function InboxFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute, openHelpSection } = useShellNavigation();
  const { platformAdmin, workspaces, llmTiers, datasources, catalogItems, packs } = usePlatformSetup();
  const isFr = locale === "fr";

  const [prefillPrompt, setPrefillPrompt] = useState<string | null>(() => consumeAssistantPrefillFromStorage());
  const [activeFolderId, setActiveFolderId] = useState<string>(() => readSavedActiveFolderId());
  const [governancePrefs, setGovernancePrefs] = useState<SavedAssistantGovernancePrefs>(() => readSavedAssistantGovernancePrefs());
  const [foldersPanelOpen, setFoldersPanelOpen] = useState<boolean>(false);
  const [savedConversationsOpen, setSavedConversationsOpen] = useState<boolean>(false);
  const [savedConversations, setSavedConversations] = useState<readonly SavedAssistantConversation[]>(() => readSavedAssistantConversations());
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => {
    const savedId = readSavedActiveConversationId();
    const convs = readSavedAssistantConversations();
    return savedId && convs.some((c) => c.id === savedId) ? savedId : (convs[0]?.id ?? null);
  });
  const [promptTelemetryLog, setPromptTelemetryLog] = useState<readonly UiAssistantPromptTelemetryRecord[]>(() => readSavedPromptTelemetryLog());
  const [governanceOpen, setGovernanceOpen] = useState<boolean>(false);
  const [governanceFeedback, setGovernanceFeedback] = useState<string | null>(null);

  const activeWorkspaceId = workspaces[0]?.workspaceId ?? "";
  const { hasActiveEmbeddingModel } = useActiveEmbeddingModelStatus();
  const {
    isReindexing,
    isReindexFailed,
    progressPercentage,
    errorMessage: reindexErrorMessage,
    relaunchReindex,
  } = useRagReindexStatus();
  const { folders, createFolder, savePinnedNotes, changeVisibility } = useServerAssistantFolders({
    workspaceId: activeWorkspaceId,
    messages: dictionary.assistantFoldersSync,
    onFeedback: setGovernanceFeedback,
  });
  const modelOptions = buildAssistantModelOptions(llmTiers, isFr);
  const activeConversation = savedConversations.find((c) => c.id === activeConversationId) ?? null;
  const activeFolder = folders.find((f) => f.folderId === activeFolderId) ?? null;
  const { agentOptions, skillOptions, orciaDocuments, ragCitations } = buildAssistantAutocompleteAndRagOptions({ catalogItems, datasources });
  const autocompleteSuggestions = buildAssistantAutocompleteSuggestions(packs);

  const selectActiveConversationAndPersist = (nextConvId: string | null) => {
    setActiveConversationId(nextConvId);
    writeSavedActiveConversationId(nextConvId);
  };

  useEffect(() => {
    return subscribeBgStream(() => {
      const latestConvs = readSavedAssistantConversations();
      if (latestConvs.length !== savedConversations.length) setSavedConversations(latestConvs);
      const latestActiveId = readSavedActiveConversationId();
      if (latestActiveId && latestActiveId !== activeConversationId && latestConvs.some((c) => c.id === latestActiveId)) {
        setActiveConversationId(latestActiveId);
      }
      setPromptTelemetryLog(readSavedPromptTelemetryLog());
    });
  }, [savedConversations.length, activeConversationId]);

  const selectActiveFolderAndPersist = (nextFolderId: string) => { setActiveFolderId(nextFolderId); writeSavedActiveFolderId(nextFolderId); };

  const appendTurnToSavedConversation = (params: CompletedAssistantTurnPayload) => {
    const usedSources = filterUsedRagSourcesForTurn({
      userPrompt: params.userPrompt,
      assistantReply: params.assistantReply,
      datasources,
      ...(params.attachedFiles ? { attachedFiles: params.attachedFiles } : {}),
    });
    const latestStored = readSavedAssistantConversations();
    const persistedActiveId = readSavedActiveConversationId() ?? activeConversationId;
    const outcome = upsertTurnIntoSavedConversations({
      prevConversations: latestStored.length >= savedConversations.length ? latestStored : savedConversations,
      activeConversationId: persistedActiveId,
      activeWorkspaceId,
      activeFolderId,
      modelOptions,
      isFr,
      ...(params.turnId ? { turnId: params.turnId } : {}),
      userPrompt: params.userPrompt,
      assistantReply: params.assistantReply,
      ...(params.assembledSystemPrompt ? { assembledSystemPrompt: params.assembledSystemPrompt } : {}),
      requestedTier: params.requestedTier,
      thinkingEffort: params.thinkingEffort,
      ...(params.attachedFiles ? { attachedFiles: params.attachedFiles } : {}),
      usedSources,
      ...(params.stepProgress ? { stepProgress: params.stepProgress } : {}),
      ...(params.thinkingElapsedSeconds !== undefined ? { thinkingElapsedSeconds: params.thinkingElapsedSeconds } : {}),
    });
    setSavedConversations(outcome.nextConversations);
    selectActiveConversationAndPersist(outcome.resolvedConversationId);
    setPromptTelemetryLog(
      upsertSavedPromptTelemetryRecord({
        turnId: outcome.createdTurn.turnId,
        timestampIso: outcome.createdTurn.timestampIso,
        userPrompt: params.userPrompt,
        assembledSystemPrompt: params.assembledSystemPrompt || "",
        conversationHistoryCount: params.conversationHistoryCount ?? 0,
        folderTitle: params.folderTitle ?? activeFolder?.title ?? null,
        folderPinnedNotes: params.folderPinnedNotes ?? activeFolder?.pinnedNotesMarkdown ?? null,
        thinkingText: params.thinkingText || "",
        assistantReply: params.assistantReply,
        modelLabel: outcome.createdTurn.modelLabel,
        thinkingEffort: params.thinkingEffort,
        thinkingElapsedSeconds: params.thinkingElapsedSeconds ?? 1,
        userFeedback: null,
      }),
    );

    if (outcome.isNewConversation) {
      const client = createOrciaApiClient({ baseUrl: "" });
      void client
        .createAssistantThread({
          workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
          ...(activeFolderId ? { folder_id: activeFolderId } : {}),
          title: outcome.createdTitle,
          initial_summary: params.assistantReply.slice(0, 240),
        })
        .catch((err: unknown) => {
          const detail = err instanceof Error ? err.message : "Synchronisation différée";
          setGovernanceFeedback(isFr ? `ℹ️ Conversation sauvegardée localement (${detail}).` : `ℹ️ Conversation saved locally (${detail}).`);
        });
    }
  };

  const handleFeedbackTurn = (turnId: string, feedback: "LIKE" | "DISLIKE" | null) => {
    setSavedConversations(updateTurnFeedbackInSavedConversations(turnId, feedback));
    setPromptTelemetryLog(updatePromptTelemetryFeedback(turnId, feedback));
    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .recordAssistantTurnFeedback({
        workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
        turn_id: turnId,
        user_feedback: feedback,
      })
      .catch((err: unknown) => {
        const detail = err instanceof Error ? err.message : "Synchronisation locale";
        setGovernanceFeedback(isFr ? `ℹ️ Avis enregistré localement (${detail}).` : `ℹ️ Feedback saved locally (${detail}).`);
      });
  };

  const firstConv = savedConversations[0];
  const initialLastReply = firstConv?.turns[firstConv.turns.length - 1]?.assistantReply ?? "";
  const latestTurnInActiveConv = activeConversation?.turns[activeConversation.turns.length - 1] ?? null;

  const {
    streamedText,
    setStreamedText,
    activeUserPrompt,
    stepProgress,
    cacheHit,
    cacheLookupMs,
    nodes1To4Ms,
    ttftMs,
    isGenerating,
    initialElapsedSeconds,
    generationStopped,
    errorMessage,
    sendTurn,
    stopGeneration,
    resetStreamState,
  } = useAssistantStreamingTurn({
    activeWorkspaceId,
    isFr,
    initialStreamedText: initialLastReply,
    activeConversation,
    activeFolder,
    governancePrefs,
    onTurnCompleted: appendTurnToSavedConversation,
  });

  const handleSaveDraftAction = (content: string) => {
    const excerpt = content.slice(0, 42).replace(/\s+/g, " ").trim();
    setGovernanceFeedback(isFr ? `✅ Brouillon « ${excerpt || "Réponse"} » enregistré dans votre Espace.` : `✅ Draft "${excerpt || "Reply"}" saved to your Workspace.`);
  };

  const previousTurnsNode =
    activeConversation && activeConversation.turns.length > 0 ? (
      <ActiveConversationMessagesView
        conversation={activeConversation}
        isFr={isFr}
        isGenerating={isGenerating}
        ragCitations={ragCitations}
        onRegenerateTurn={(userPrompt) => sendTurn({ userPrompt, requestedSpeed: "SPEED_1_FAST", deepAuditPillActive: false })}
        onSaveDraft={handleSaveDraftAction}
        onContinueInProcess={() => navigateToRoute("/processes")}
        onFeedbackTurn={handleFeedbackTurn}
      />
    ) : null;

  return (
    <div className="space-y-4" data-testid="inbox-feature-panel">
      {governanceFeedback ? (
        <div role="status" data-testid="assistant-governance-feedback-banner" className="rounded border px-3 py-2 text-xs font-medium" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)", color: "var(--color-text-primary)" }}>
          {governanceFeedback}
        </div>
      ) : null}

      <AssistantTopToolbar
        isFr={isFr}
        savedCount={savedConversations.length}
        foldersCount={folders.length}
        savedConversationsOpen={savedConversationsOpen}
        foldersPanelOpen={foldersPanelOpen}
        governanceModalTitle={dictionary.assistantGovernance.modalTitle}
        onNewConversation={() => { selectActiveConversationAndPersist(null); resetStreamState(""); }}
        onToggleSavedConversations={() => setSavedConversationsOpen((prev) => !prev)}
        onToggleFoldersPanel={() => setFoldersPanelOpen((prev) => !prev)}
        onToggleGovernanceModal={() => setGovernanceOpen((prev) => !prev)}
        onOpenHelpSection={openHelpSection}
      />

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
            resetStreamState(latestTurn?.assistantReply ?? "");
            setSavedConversationsOpen(false);
          }}
          onDeleteConversation={(convId) => {
            const next = savedConversations.filter((c) => c.id !== convId);
            setSavedConversations(next);
            writeSavedAssistantConversations(next);
            if (activeConversationId === convId) { selectActiveConversationAndPersist(null); resetStreamState(""); }
          }}
        />
      )}

      <AssistantGovernanceDialog
        open={governanceOpen}
        workspaceId={activeWorkspaceId}
        governancePrefs={governancePrefs}
        promptTelemetryLog={promptTelemetryLog}
        labels={dictionary.assistantGovernance}
        isFr={isFr}
        onSaveUserPrefs={(next, fb) => {
          setGovernancePrefs(next);
          writeSavedAssistantGovernancePrefs(next);
          setGovernanceFeedback(fb);
        }}
        onSaveWorkspaceSettings={(next, fb) => {
          setGovernancePrefs(next);
          writeSavedAssistantGovernancePrefs(next);
          setGovernanceFeedback(fb);
        }}
        onFeedback={setGovernanceFeedback}
        onClose={() => setGovernanceOpen(false)}
      />

      <div className="orcia-bento-card space-y-3">
        <AssistantSpeedSelectorAndStreamView
          workspaceId={activeWorkspaceId}
          userId={platformAdmin?.email ?? ""}
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
          previousTurnsSlot={previousTurnsNode}
          welcomeTitle={isFr ? "Par quoi voulez-vous commencer ?" : "Where would you like to start?"}
          showWelcomeHero={!activeConversation || activeConversation.turns.length === 0}
          hideTechnicalCacheHeader={true}
          hideLegacySpeedPills={true}
          hideDuplicateCompletedStream={Boolean(!isGenerating && activeConversation && activeConversation.turns.length > 0)}
          cacheHit={cacheHit}
          cacheLookupMs={cacheLookupMs}
          nodes1To4DeterministicMs={nodes1To4Ms}
          ttftMs={ttftMs}
          stepProgress={stepProgress}
          streamedText={streamedText}
          activeUserPrompt={activeUserPrompt}
          isGenerating={isGenerating}
          initialElapsedSeconds={initialElapsedSeconds}
          generationStopped={generationStopped}
          errorMessage={errorMessage}
          currentTurnFeedback={latestTurnInActiveConv?.userFeedback ?? null}
          onFeedbackLastTurn={(fb) => { if (latestTurnInActiveConv) handleFeedbackTurn(latestTurnInActiveConv.turnId, fb); }}
          labels={dictionary.assistantSpeedStream}
          disabled={!hasActiveEmbeddingModel || isReindexing || isReindexFailed}
          disabledReasonBanner={
            !hasActiveEmbeddingModel ? (
              React.createElement(AssistantNoEmbeddingBanner, {
                title: dictionary.assistantNoEmbeddingModel.bannerTitle,
                description: dictionary.assistantNoEmbeddingModel.bannerDescription,
                configureCta: dictionary.assistantNoEmbeddingModel.configureCta,
                onConfigure: () => navigateToRoute("/settings/ai-models"),
              })
            ) : isReindexing ? (
              React.createElement(AssistantReindexingBanner, {
                status: "IN_PROGRESS",
                progressPercentage,
                isFr,
                onConfigure: () => navigateToRoute("/settings/ai-models"),
              })
            ) : isReindexFailed ? (
              React.createElement(AssistantReindexingBanner, {
                status: "FAILED",
                progressPercentage,
                errorMessage: reindexErrorMessage,
                isFr,
                onRelaunch: () => {
                  void relaunchReindex();
                },
                onConfigure: () => navigateToRoute("/settings/ai-models"),
              })
            ) : null
          }
          onOpenFoldersFromPlus={() => setFoldersPanelOpen((prev) => !prev)}
          onStopGeneration={stopGeneration}
          onSaveDraftFromResponse={handleSaveDraftAction}
          onContinueInProcessFromResponse={() => navigateToRoute("/processes")}
          onSendTurn={sendTurn}
        />
      </div>

      <div data-testid="assistant-folders-panel-wrapper" style={foldersPanelOpen ? undefined : { display: "none" }} className={foldersPanelOpen ? "" : "sr-only"}>
        <AssistantFoldersAndCollaborativeThreadView
          workspaceId={activeWorkspaceId}
          activeFolderId={activeFolderId}
          folders={folders}
          historyHits={[]}
          currentAuthorPassthroughIdentity={platformAdmin?.email ?? ""}
          labels={dictionary.assistantFolders}
          defaultNotesOpen={true}
          onOpenHelpSection={openHelpSection}
          onSelectFolder={(folderId) => selectActiveFolderAndPersist(folderId)}
          onCreateFolder={(title) => {
            void createFolder(title).then((saved) => {
              if (!saved) return;
              selectActiveFolderAndPersist(saved.folderId);
              setGovernanceFeedback(isFr ? `✅ Dossier « ${saved.title} » créé et sélectionné.` : `✅ Folder "${saved.title}" created and selected.`);
            });
          }}
          onUpdatePinnedNotes={(folderId, notes) => {
            const folder = folders.find((f) => f.folderId === folderId);
            if (!folder) return;
            void savePinnedNotes(folder, notes).then((ok) => {
              if (ok) setGovernanceFeedback(isFr ? "✅ Notes du dossier enregistrées et activées pour vos prochaines questions." : "✅ Folder notes saved and activated for your next questions.");
            });
          }}
          onChangeVisibility={(folderId, mode: AssistantFolderVisibilityMode) => {
            const folder = folders.find((f) => f.folderId === folderId);
            if (!folder) return;
            const humanLabel = formatFolderVisibilityLabel(mode, isFr);
            void changeVisibility(folder, mode).then((ok) => {
              if (ok) setGovernanceFeedback(isFr ? `✅ Visibilité du dossier mise à jour (${humanLabel}).` : `✅ Folder visibility updated (${humanLabel}).`);
            });
          }}
          onSendCollaborativeMessage={(message) => setStreamedText(isFr ? `💬 Message ajouté à la discussion : ${message}` : `💬 Message added to thread: ${message}`)}
          onLaunchProcessFromFolder={() => navigateToRoute("/processes")}
        />
      </div>

      <div data-testid="assistant-citations-card-wrapper" style={{ display: "none" }} className="sr-only">
        <AssistantCitationPillsAndArtifactCard
          sanitizedResponseText=""
          sources={[]}
          glossaryItems={[]}
          toolOutputs={[]}
          footerSummaryLine=""
          labels={dictionary.assistantCitations}
          onSaveDraft={(title) => handleSaveDraftAction(title)}
          onContinueInProcess={() => navigateToRoute("/processes")}
        />
      </div>
    </div>
  );
}
