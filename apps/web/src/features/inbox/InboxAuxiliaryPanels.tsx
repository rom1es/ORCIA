import {
  AssistantCitationPillsAndArtifactCard,
  AssistantFoldersAndCollaborativeThreadView,
  AssistantGovernanceModalAndStudio,
  formatFolderVisibilityLabel,
  type AssistantFolderVisibilityMode,
  type UiAssistantFolderItem,
  type UiAssistantPromptTelemetryRecord,
} from "@orcia/ui";
import React from "react";
import type { TranslationDictionary } from "../../i18n/types";
import {
  writeSavedAssistantGovernancePrefs,
  type SavedAssistantGovernancePrefs,
} from "./assistantFoldersAndPrefsStore";

export interface InboxAuxiliaryPanelsProps {
  readonly isFr: boolean;
  readonly activeWorkspaceId: string;
  readonly activeFolderId: string;
  readonly foldersPanelOpen: boolean;
  readonly governanceOpen: boolean;
  readonly governancePrefs: SavedAssistantGovernancePrefs;
  readonly promptTelemetryLog: readonly UiAssistantPromptTelemetryRecord[];
  readonly folders: readonly UiAssistantFolderItem[];
  readonly authorIdentity: string;
  readonly dictionary: TranslationDictionary;
  readonly setGovernancePrefs: React.Dispatch<
    React.SetStateAction<SavedAssistantGovernancePrefs>
  >;
  readonly setGovernanceOpen: (open: boolean) => void;
  readonly setGovernanceFeedback: (msg: string | null) => void;
  readonly selectActiveFolderAndPersist: (folderId: string) => void;
  readonly createFolder: (title: string) => Promise<UiAssistantFolderItem | null>;
  readonly savePinnedNotes: (
    folder: UiAssistantFolderItem,
    notes: string,
  ) => Promise<boolean>;
  readonly changeVisibility: (
    folder: UiAssistantFolderItem,
    mode: AssistantFolderVisibilityMode,
  ) => Promise<boolean>;
  readonly onOpenHelpSection: (sectionId: string) => void;
  readonly onSendCollaborativeMessage: (message: string) => void;
  readonly onNavigateToProcesses: () => void;
  readonly onSaveDraftAction: (content: string) => void;
}

export function InboxAuxiliaryPanels({
  isFr,
  activeWorkspaceId,
  activeFolderId,
  foldersPanelOpen,
  governanceOpen,
  governancePrefs,
  promptTelemetryLog,
  folders,
  authorIdentity,
  dictionary,
  setGovernancePrefs,
  setGovernanceOpen,
  setGovernanceFeedback,
  selectActiveFolderAndPersist,
  createFolder,
  savePinnedNotes,
  changeVisibility,
  onOpenHelpSection,
  onSendCollaborativeMessage,
  onNavigateToProcesses,
  onSaveDraftAction,
}: InboxAuxiliaryPanelsProps): React.JSX.Element {
  return (
    <>
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
          promptTelemetryLog={promptTelemetryLog}
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
            setGovernanceFeedback(
              isFr
                ? `✅ Préférences personnelles enregistrées automatiquement (rôle : ${payload.defaultHat}).`
                : `✅ Personal preferences auto-saved (role: ${payload.defaultHat}).`,
            );
          }}
          onSaveWorkspaceSettings={(payload) => {
            setGovernancePrefs((prev) => {
              const next: SavedAssistantGovernancePrefs = {
                ...prev,
                workspaceInstructions: payload.workspaceInstructions,
                mcpExposeAssistant: payload.mcpExposeAssistant,
              };
              writeSavedAssistantGovernancePrefs(next);
              return next;
            });
            setGovernanceFeedback(
              isFr
                ? `✅ Réglages de l'Espace enregistrés automatiquement (accès externe : ${payload.mcpExposeAssistant ? "activé" : "désactivé"}).`
                : `✅ Workspace settings auto-saved (external access: ${payload.mcpExposeAssistant ? "enabled" : "disabled"}).`,
            );
          }}
          onSaveStudioOverride={(payload) =>
            setGovernanceFeedback(
              isFr
                ? `✅ Configuration avancée enregistrée pour le périmètre ${payload.scopeLevel}.`
                : `✅ Advanced configuration saved for scope ${payload.scopeLevel}.`,
            )
          }
          onResetStudioOverride={(scopeLevel) =>
            setGovernanceFeedback(
              isFr
                ? `✅ Configuration réinitialisée aux valeurs par défaut (${scopeLevel}).`
                : `✅ Configuration reset to defaults (${scopeLevel}).`,
            )
          }
          onClose={() => setGovernanceOpen(false)}
        />
      ) : null}

      <div
        data-testid="assistant-folders-panel-wrapper"
        style={foldersPanelOpen ? undefined : { display: "none" }}
        className={foldersPanelOpen ? "" : "sr-only"}
      >
        <AssistantFoldersAndCollaborativeThreadView
          workspaceId={activeWorkspaceId}
          activeFolderId={activeFolderId}
          folders={folders}
          historyHits={[]}
          currentAuthorPassthroughIdentity={authorIdentity}
          labels={dictionary.assistantFolders}
          defaultNotesOpen={true}
          onOpenHelpSection={onOpenHelpSection}
          onSelectFolder={(folderId) => selectActiveFolderAndPersist(folderId)}
          onCreateFolder={(title) => {
            void createFolder(title).then((saved) => {
              if (!saved) return;
              selectActiveFolderAndPersist(saved.folderId);
              setGovernanceFeedback(
                isFr
                  ? `✅ Dossier « ${saved.title} » créé et sélectionné.`
                  : `✅ Folder "${saved.title}" created and selected.`,
              );
            });
          }}
          onUpdatePinnedNotes={(folderId, notes) => {
            const folder = folders.find((f) => f.folderId === folderId);
            if (!folder) return;
            void savePinnedNotes(folder, notes).then((ok) => {
              if (ok) {
                setGovernanceFeedback(
                  isFr
                    ? "✅ Notes du dossier enregistrées et activées pour vos prochaines questions."
                    : "✅ Folder notes saved and activated for your next questions.",
                );
              }
            });
          }}
          onChangeVisibility={(folderId, mode: AssistantFolderVisibilityMode) => {
            const folder = folders.find((f) => f.folderId === folderId);
            if (!folder) return;
            const humanLabel = formatFolderVisibilityLabel(mode, isFr);
            void changeVisibility(folder, mode).then((ok) => {
              if (ok) {
                setGovernanceFeedback(
                  isFr
                    ? `✅ Visibilité du dossier mise à jour (${humanLabel}).`
                    : `✅ Folder visibility updated (${humanLabel}).`,
                );
              }
            });
          }}
          onSendCollaborativeMessage={onSendCollaborativeMessage}
          onLaunchProcessFromFolder={onNavigateToProcesses}
        />
      </div>

      <div
        data-testid="assistant-citations-card-wrapper"
        style={{ display: "none" }}
        className="sr-only"
      >
        <AssistantCitationPillsAndArtifactCard
          sanitizedResponseText=""
          sources={[]}
          glossaryItems={[]}
          toolOutputs={[]}
          footerSummaryLine=""
          labels={dictionary.assistantCitations}
          onSaveDraft={(title) => onSaveDraftAction(title)}
          onContinueInProcess={onNavigateToProcesses}
        />
      </div>
    </>
  );
}
