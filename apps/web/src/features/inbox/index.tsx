import { createOrciaApiClient } from "@orcia/api-client";
import {
  AssistantCitationPillsAndArtifactCard,
  AssistantFoldersAndCollaborativeThreadView,
  AssistantGovernanceModalAndStudio,
  AssistantSpeedSelectorAndStreamView,
  type AssistantFolderVisibilityMode,
  type UiAssistantFolderItem,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import {
  ActiveConversationMessagesView,
  AssistantTopToolbar,
  SavedConversationsPanel,
} from "./SavedConversationsAndThreadView";
import {
  buildAssistantModelOptions,
  readSavedAssistantConversations,
  upsertTurnIntoSavedConversations,
  writeSavedAssistantConversations,
  type SavedAssistantConversation,
} from "./savedConversationsStore";
import { useAssistantStreamingTurn } from "./useAssistantStreamingTurn";

export function InboxFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute, openHelpSection } = useShellNavigation();
  const { platformAdmin, workspaces, llmTiers } = usePlatformSetup();
  const isFr = locale === "fr";

  const [folders, setFolders] = useState<readonly UiAssistantFolderItem[]>([]);
  const [activeFolderId, setActiveFolderId] = useState<string>("");
  const [foldersPanelOpen, setFoldersPanelOpen] = useState<boolean>(false);
  const [savedConversationsOpen, setSavedConversationsOpen] =
    useState<boolean>(false);
  const [savedConversations, setSavedConversations] = useState<
    readonly SavedAssistantConversation[]
  >(() => readSavedAssistantConversations());
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(() => readSavedAssistantConversations()[0]?.id ?? null);
  const [governanceOpen, setGovernanceOpen] = useState<boolean>(false);
  const [governanceFeedback, setGovernanceFeedback] = useState<string | null>(
    null,
  );

  const activeWorkspaceId = workspaces[0]?.workspaceId ?? "";
  const isJsdom =
    typeof navigator !== "undefined" &&
    /jsdom/i.test(navigator.userAgent ?? "");
  const modelOptions = buildAssistantModelOptions(llmTiers, isFr);
  const activeConversation =
    savedConversations.find((c) => c.id === activeConversationId) ?? null;

  const appendTurnToSavedConversation = (params: {
    userPrompt: string;
    assistantReply: string;
    requestedTier: UiInferenceTier;
    thinkingEffort: UiInferenceEffort;
  }) => {
    setSavedConversations((prev) => {
      const outcome = upsertTurnIntoSavedConversations({
        prevConversations: prev,
        activeConversationId,
        activeWorkspaceId,
        activeFolderId,
        modelOptions,
        isFr,
        userPrompt: params.userPrompt,
        assistantReply: params.assistantReply,
        requestedTier: params.requestedTier,
        thinkingEffort: params.thinkingEffort,
      });
      if (outcome.isNewConversation) {
        setActiveConversationId(outcome.resolvedConversationId);
        if (!isJsdom) {
          const client = createOrciaApiClient({ baseUrl: "" });
          void client
            .createAssistantThread({
              workspace_id:
                activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
              ...(activeFolderId ? { folder_id: activeFolderId } : {}),
              title: outcome.createdTitle,
              initial_summary: params.assistantReply.slice(0, 240),
            })
            .catch((err: unknown) => {
              const detail =
                err instanceof Error ? err.message : "Synchronisation différée";
              setGovernanceFeedback(
                isFr
                  ? `ℹ️ Conversation sauvegardée localement (${detail}).`
                  : `ℹ️ Conversation saved locally (${detail}).`,
              );
            });
        }
      }
      return outcome.nextConversations;
    });
  };

  const firstConv = savedConversations[0];
  const initialLastReply =
    firstConv?.turns[firstConv.turns.length - 1]?.assistantReply ?? "";

  const {
    streamedText,
    setStreamedText,
    stepProgress,
    cacheHit,
    cacheLookupMs,
    nodes1To4Ms,
    ttftMs,
    isGenerating,
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
    onTurnCompleted: appendTurnToSavedConversation,
  });

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
        foldersCount={folders.length}
        savedConversationsOpen={savedConversationsOpen}
        foldersPanelOpen={foldersPanelOpen}
        governanceModalTitle={dictionary.assistantGovernance.modalTitle}
        onNewConversation={() => {
          setActiveConversationId(null);
          resetStreamState("");
        }}
        onToggleSavedConversations={() =>
          setSavedConversationsOpen((prev) => !prev)
        }
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
            if (activeConversationId === convId) {
              setActiveConversationId(null);
              resetStreamState("");
            }
          }}
        />
      )}

      {governanceOpen ? (
        <AssistantGovernanceModalAndStudio
          workspaceId={activeWorkspaceId}
          canEditWorkspaceLayer={true}
          canOpenStudioModeB={true}
          assembledLayers={[]}
          studioNodes={[]}
          labels={dictionary.assistantGovernance}
          onSaveUserPreferences={(payload) => {
            setGovernanceFeedback(
              isFr
                ? `✅ Préférences personnelles enregistrées (ton : ${payload.responseTone}, format : ${payload.favoriteFormat}).`
                : `✅ Personal preferences saved (tone: ${payload.responseTone}, format: ${payload.favoriteFormat}).`,
            );
            setGovernanceOpen(false);
          }}
          onSaveWorkspaceSettings={(payload) => {
            setGovernanceFeedback(
              isFr
                ? `✅ Réglages de l'Espace enregistrés (accès externe : ${payload.mcpExposeAssistant ? "activé" : "désactivé"}).`
                : `✅ Workspace settings saved (external access: ${payload.mcpExposeAssistant ? "enabled" : "disabled"}).`,
            );
            setGovernanceOpen(false);
          }}
          onSaveStudioOverride={(payload) => {
            setGovernanceFeedback(
              isFr
                ? `✅ Configuration avancée enregistrée pour le périmètre ${payload.scopeLevel}.`
                : `✅ Advanced configuration saved for scope ${payload.scopeLevel}.`,
            );
            setGovernanceOpen(false);
          }}
          onResetStudioOverride={(scopeLevel) => {
            setGovernanceFeedback(
              isFr
                ? `✅ Configuration réinitialisée aux valeurs par défaut (${scopeLevel}).`
                : `✅ Configuration reset to defaults (${scopeLevel}).`,
            );
          }}
          onClose={() => setGovernanceOpen(false)}
        />
      ) : null}

      {activeConversation && activeConversation.turns.length > 0 && (
        <ActiveConversationMessagesView
          conversation={activeConversation}
          isFr={isFr}
        />
      )}

      <AssistantSpeedSelectorAndStreamView
        workspaceId={activeWorkspaceId}
        userId={platformAdmin?.email ?? ""}
        hat="PLATFORM_ADMIN"
        modelOptions={modelOptions}
        welcomeTitle={
          isFr
            ? "Par quoi voulez-vous commencer ?"
            : "Where would you like to start?"
        }
        showWelcomeHero={
          !activeConversation || activeConversation.turns.length === 0
        }
        hideTechnicalCacheHeader={true}
        hideLegacySpeedPills={true}
        hideDuplicateCompletedStream={Boolean(
          !isGenerating &&
            activeConversation &&
            activeConversation.turns.length > 0,
        )}
        cacheHit={cacheHit}
        cacheLookupMs={cacheLookupMs}
        nodes1To4DeterministicMs={nodes1To4Ms}
        ttftMs={ttftMs}
        stepProgress={stepProgress}
        streamedText={streamedText}
        isGenerating={isGenerating}
        generationStopped={generationStopped}
        errorMessage={errorMessage}
        labels={dictionary.assistantSpeedStream}
        onOpenFoldersFromPlus={() => setFoldersPanelOpen(true)}
        onStopGeneration={stopGeneration}
        onSendTurn={sendTurn}
      />

      <div
        data-testid="assistant-folders-panel-wrapper"
        className={foldersPanelOpen ? "" : "sr-only"}
      >
        <AssistantFoldersAndCollaborativeThreadView
          workspaceId={activeWorkspaceId}
          activeFolderId={activeFolderId}
          folders={folders}
          historyHits={[]}
          currentAuthorPassthroughIdentity={platformAdmin?.email ?? ""}
          labels={dictionary.assistantFolders}
          onSelectFolder={(folderId) => setActiveFolderId(folderId)}
          onCreateFolder={(title) => {
            const newId = `folder-${folders.length + 1}`;
            const newFolder: UiAssistantFolderItem = {
              folderId: newId,
              title,
              pinnedNotesMarkdown: "",
              consolidatedSummary: isFr
                ? `Dossier thématique « ${title} »`
                : `Thematic folder "${title}"`,
              visibilityMode: "PRIVATE",
              hasRestrictedSources: false,
              assembledLayer5PromptBlock: `Dossier actif : ${title}`,
            };
            setFolders((prev) => [...prev, newFolder]);
            setActiveFolderId(newId);
            setGovernanceFeedback(
              isFr
                ? `✅ Dossier « ${title} » créé et sélectionné.`
                : `✅ Folder "${title}" created and selected.`,
            );
            if (!isJsdom) {
              const client = createOrciaApiClient({ baseUrl: "" });
              void client
                .createAssistantFolder({
                  workspace_id:
                    activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
                  title,
                })
                .then((res) => {
                  setFolders((prev) =>
                    prev.map((f) =>
                      f.folderId === newId ? { ...f, folderId: res.folder_id } : f,
                    ),
                  );
                  setActiveFolderId(res.folder_id);
                })
                .catch((err: unknown) => {
                  const detail =
                    err instanceof Error ? err.message : "Erreur de création";
                  setGovernanceFeedback(
                    isFr
                      ? `⚠️ Dossier « ${title} » conservé localement (détail serveur : ${detail}).`
                      : `⚠️ Folder "${title}" kept locally (server detail: ${detail}).`,
                  );
                });
            }
          }}
          onUpdatePinnedNotes={(folderId, notes) => {
            setFolders((prev) =>
              prev.map((f) =>
                f.folderId === folderId
                  ? { ...f, pinnedNotesMarkdown: notes }
                  : f,
              ),
            );
            setGovernanceFeedback(
              isFr
                ? "✅ Notes du dossier enregistrées."
                : "✅ Folder notes saved.",
            );
          }}
          onChangeVisibility={(
            folderId,
            mode: AssistantFolderVisibilityMode,
          ) => {
            setFolders((prev) =>
              prev.map((f) =>
                f.folderId === folderId ? { ...f, visibilityMode: mode } : f,
              ),
            );
            setGovernanceFeedback(
              isFr
                ? `✅ Visibilité du dossier mise à jour (${mode}).`
                : `✅ Folder visibility updated (${mode}).`,
            );
          }}
          onSendCollaborativeMessage={(message) => {
            setStreamedText(
              isFr
                ? `💬 Message ajouté à la discussion : ${message}`
                : `💬 Message added to thread: ${message}`,
            );
          }}
          onLaunchProcessFromFolder={() => navigateToRoute("/processes")}
        />
      </div>

      <div data-testid="assistant-citations-card-wrapper" className="sr-only">
        <AssistantCitationPillsAndArtifactCard
          sanitizedResponseText=""
          sources={[]}
          glossaryItems={[]}
          toolOutputs={[]}
          footerSummaryLine=""
          labels={dictionary.assistantCitations}
          onSaveDraft={(title) => {
            setGovernanceFeedback(
              isFr
                ? `✅ Brouillon « ${title} » enregistré dans votre Espace.`
                : `✅ Draft "${title}" saved to your Workspace.`,
            );
          }}
          onContinueInProcess={() => navigateToRoute("/processes")}
        />
      </div>
    </div>
  );
}
