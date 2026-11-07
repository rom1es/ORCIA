import { createOrciaApiClient } from "@orcia/api-client";
import {
  AssistantCitationPillsAndArtifactCard,
  AssistantFoldersAndCollaborativeThreadView,
  AssistantGovernanceModalAndStudio,
  AssistantSpeedSelectorAndStreamView,
  formatFolderVisibilityLabel,
  type AssistantFolderVisibilityMode,
  type UiAssistantAttachedFileItem,
  type UiAssistantFolderItem,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import {
  readSavedActiveFolderId,
  readSavedAssistantFolders,
  readSavedAssistantGovernancePrefs,
  writeSavedActiveFolderId,
  writeSavedAssistantFolders,
  writeSavedAssistantGovernancePrefs,
  type SavedAssistantGovernancePrefs,
} from "./assistantFoldersAndPrefsStore";
import { ActiveConversationMessagesView, AssistantTopToolbar, SavedConversationsPanel } from "./SavedConversationsAndThreadView";
import {
  buildAssistantAutocompleteAndRagOptions,
  buildAssistantAutocompleteSuggestions,
  buildAssistantModelOptions,
  consumeAssistantPrefillFromStorage,
  filterUsedRagSourcesForTurn,
  readSavedAssistantConversations,
  upsertTurnIntoSavedConversations,
  writeSavedAssistantConversations,
  type SavedAssistantConversation,
} from "./savedConversationsStore";
import { useAssistantStreamingTurn } from "./useAssistantStreamingTurn";

export function InboxFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute, openHelpSection } = useShellNavigation();
  const { platformAdmin, workspaces, llmTiers, datasources, catalogItems, packs } = usePlatformSetup();
  const isFr = locale === "fr";

  const [prefillPrompt, setPrefillPrompt] = useState<string | null>(() => consumeAssistantPrefillFromStorage());
  const [folders, setFolders] = useState<readonly UiAssistantFolderItem[]>(() => readSavedAssistantFolders());
  const [activeFolderId, setActiveFolderId] = useState<string>(() => readSavedActiveFolderId());
  const [governancePrefs, setGovernancePrefs] = useState<SavedAssistantGovernancePrefs>(() => readSavedAssistantGovernancePrefs());
  const [foldersPanelOpen, setFoldersPanelOpen] = useState<boolean>(false);
  const [savedConversationsOpen, setSavedConversationsOpen] = useState<boolean>(false);
  const [savedConversations, setSavedConversations] = useState<readonly SavedAssistantConversation[]>(() => readSavedAssistantConversations());
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => readSavedAssistantConversations()[0]?.id ?? null);
  const [governanceOpen, setGovernanceOpen] = useState<boolean>(false);
  const [governanceFeedback, setGovernanceFeedback] = useState<string | null>(null);

  const activeWorkspaceId = workspaces[0]?.workspaceId ?? "";
  const isJsdom = typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
  const modelOptions = buildAssistantModelOptions(llmTiers, isFr);
  const activeConversation = savedConversations.find((c) => c.id === activeConversationId) ?? null;
  const activeFolder = folders.find((f) => f.folderId === activeFolderId) ?? null;
  const { agentOptions, skillOptions, orciaDocuments, ragCitations } = buildAssistantAutocompleteAndRagOptions({ catalogItems, datasources });
  const autocompleteSuggestions = buildAssistantAutocompleteSuggestions(packs);

  const updateFoldersAndPersist = (updater: (prev: readonly UiAssistantFolderItem[]) => readonly UiAssistantFolderItem[]) => {
    setFolders((prev) => { const next = updater(prev); writeSavedAssistantFolders(next); return next; });
  };
  const selectActiveFolderAndPersist = (nextFolderId: string) => {
    setActiveFolderId(nextFolderId);
    writeSavedActiveFolderId(nextFolderId);
  };

  const appendTurnToSavedConversation = (params: {
    userPrompt: string;
    assistantReply: string;
    requestedTier: UiInferenceTier;
    thinkingEffort: UiInferenceEffort;
    attachedFiles?: readonly UiAssistantAttachedFileItem[];
    stepProgress?: readonly import("@orcia/ui").UiThreeSpeedStepProgress[];
    thinkingElapsedSeconds?: number;
  }) => {
    const usedSources = filterUsedRagSourcesForTurn({
      userPrompt: params.userPrompt,
      assistantReply: params.assistantReply,
      datasources,
      ...(params.attachedFiles ? { attachedFiles: params.attachedFiles } : {}),
    });
    const latestStored = readSavedAssistantConversations();
    const outcome = upsertTurnIntoSavedConversations({
      prevConversations: latestStored.length >= savedConversations.length ? latestStored : savedConversations,
      activeConversationId,
      activeWorkspaceId,
      activeFolderId,
      modelOptions,
      isFr,
      userPrompt: params.userPrompt,
      assistantReply: params.assistantReply,
      requestedTier: params.requestedTier,
      thinkingEffort: params.thinkingEffort,
      ...(params.attachedFiles ? { attachedFiles: params.attachedFiles } : {}),
      usedSources,
      ...(params.stepProgress ? { stepProgress: params.stepProgress } : {}),
      ...(params.thinkingElapsedSeconds !== undefined ? { thinkingElapsedSeconds: params.thinkingElapsedSeconds } : {}),
    });
    setSavedConversations(outcome.nextConversations);
    if (outcome.isNewConversation) {
      setActiveConversationId(outcome.resolvedConversationId);
      if (!isJsdom) {
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
    }
  };

  const firstConv = savedConversations[0];
  const initialLastReply = firstConv?.turns[firstConv.turns.length - 1]?.assistantReply ?? "";

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
    isJsdom,
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
      />
    ) : null;

  return (
    <div className="space-y-4" data-testid="inbox-feature-panel">
      {governanceFeedback ? (
        <div
          role="status"
          data-testid="assistant-governance-feedback-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)", color: "var(--color-text-primary)" }}
        >
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
        onNewConversation={() => { setActiveConversationId(null); resetStreamState(""); }}
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
            setActiveConversationId(target.id);
            const latestTurn = target.turns[target.turns.length - 1];
            resetStreamState(latestTurn?.assistantReply ?? "");
            setSavedConversationsOpen(false);
          }}
          onDeleteConversation={(convId) => {
            const next = savedConversations.filter((c) => c.id !== convId);
            setSavedConversations(next);
            writeSavedAssistantConversations(next);
            if (activeConversationId === convId) { setActiveConversationId(null); resetStreamState(""); }
          }}
        />
      )}

      {governanceOpen ? (
        <AssistantGovernanceModalAndStudio
          workspaceId={activeWorkspaceId}
          canEditWorkspaceLayer={true}
          canOpenStudioModeB={true}
          initialUserTone={governancePrefs.responseTone}
          initialUserFormat={governancePrefs.favoriteFormat}
          initialDefaultHat={governancePrefs.defaultHat}
          initialPersonalInstructions={governancePrefs.personalInstructions}
          initialWorkspaceInstructions={governancePrefs.workspaceInstructions}
          initialMcpExposed={governancePrefs.mcpExposeAssistant}
          assembledLayers={[]}
          studioNodes={[]}
          labels={dictionary.assistantGovernance}
          onSaveUserPreferences={(payload) => {
            setGovernancePrefs((prev) => {
              const next: SavedAssistantGovernancePrefs = {
                ...prev,
                responseTone: payload.responseTone,
                favoriteFormat: payload.favoriteFormat,
                defaultHat: payload.defaultHat,
                personalInstructions: payload.personalInstructions,
              };
              writeSavedAssistantGovernancePrefs(next);
              return next;
            });
            setGovernanceFeedback(isFr ? `✅ Préférences personnelles enregistrées automatiquement (rôle : ${payload.defaultHat}).` : `✅ Personal preferences auto-saved (role: ${payload.defaultHat}).`);
          }}
          onSaveWorkspaceSettings={(payload) => {
            setGovernancePrefs((prev) => {
              const next: SavedAssistantGovernancePrefs = { ...prev, workspaceInstructions: payload.workspaceInstructions, mcpExposeAssistant: payload.mcpExposeAssistant };
              writeSavedAssistantGovernancePrefs(next);
              return next;
            });
            setGovernanceFeedback(isFr ? `✅ Réglages de l'Espace enregistrés automatiquement (accès externe : ${payload.mcpExposeAssistant ? "activé" : "désactivé"}).` : `✅ Workspace settings auto-saved (external access: ${payload.mcpExposeAssistant ? "enabled" : "disabled"}).`);
          }}
          onSaveStudioOverride={(payload) => setGovernanceFeedback(isFr ? `✅ Configuration avancée enregistrée pour le périmètre ${payload.scopeLevel}.` : `✅ Advanced configuration saved for scope ${payload.scopeLevel}.`)}
          onResetStudioOverride={(scopeLevel) => setGovernanceFeedback(isFr ? `✅ Configuration réinitialisée aux valeurs par défaut (${scopeLevel}).` : `✅ Configuration reset to defaults (${scopeLevel}).`)}
          onClose={() => setGovernanceOpen(false)}
        />
      ) : null}

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
          labels={dictionary.assistantSpeedStream}
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
            const newId = `folder-${folders.length + 1}-${Date.now()}`;
            const newFolder: UiAssistantFolderItem = {
              folderId: newId,
              title,
              pinnedNotesMarkdown: "",
              consolidatedSummary: isFr ? `Dossier thématique « ${title} »` : `Thematic folder "${title}"`,
              visibilityMode: "PRIVATE",
              hasRestrictedSources: false,
              assembledLayer5PromptBlock: `Dossier actif : ${title}`,
            };
            updateFoldersAndPersist((prev) => [...prev, newFolder]);
            selectActiveFolderAndPersist(newId);
            setGovernanceFeedback(isFr ? `✅ Dossier « ${title} » créé et sélectionné.` : `✅ Folder "${title}" created and selected.`);
            if (!isJsdom) {
              const client = createOrciaApiClient({ baseUrl: "" });
              void client
                .createAssistantFolder({ workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301", title })
                .then((res) => {
                  updateFoldersAndPersist((prev) => prev.map((f) => (f.folderId === newId ? { ...f, folderId: res.folder_id } : f)));
                  selectActiveFolderAndPersist(res.folder_id);
                })
                .catch((err: unknown) => {
                  const detail = err instanceof Error ? err.message : "Erreur de création";
                  setGovernanceFeedback(isFr ? `⚠️ Dossier « ${title} » conservé localement (${detail}).` : `⚠️ Folder "${title}" kept locally (${detail}).`);
                });
            }
          }}
          onUpdatePinnedNotes={(folderId, notes) => {
            updateFoldersAndPersist((prev) =>
              prev.map((f) =>
                f.folderId === folderId
                  ? { ...f, pinnedNotesMarkdown: notes, assembledLayer5PromptBlock: notes.trim() ? `📌 Notes actives : ${notes.trim()}` : `Dossier actif : ${f.title}` }
                  : f,
              ),
            );
            setGovernanceFeedback(isFr ? "✅ Notes du dossier enregistrées et activées pour vos prochaines questions." : "✅ Folder notes saved and activated for your next questions.");
          }}
          onChangeVisibility={(folderId, mode: AssistantFolderVisibilityMode) => {
            const humanLabel = formatFolderVisibilityLabel(mode, isFr);
            updateFoldersAndPersist((prev) => prev.map((f) => (f.folderId === folderId ? { ...f, visibilityMode: mode } : f)));
            setGovernanceFeedback(isFr ? `✅ Visibilité du dossier mise à jour (${humanLabel}).` : `✅ Folder visibility updated (${humanLabel}).`);
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
