import {
  AssistantCitationPillsAndArtifactCard,
  AssistantFoldersAndCollaborativeThreadView,
  AssistantGovernanceModalAndStudio,
  formatFolderVisibilityLabel,
  type AssistantFolderVisibilityMode,
  type UiAssembledLayerItem,
  type UiAssistantFolderItem,
  type UiAssistantPromptTelemetryRecord,
} from "@orcia/ui";
import React from "react";
import type { TranslationDictionary } from "../../i18n/types";
import type { SavedAssistantGovernancePrefs } from "./assistantFoldersAndPrefsStore";
import type { BuiltCitationCardPreview } from "./inboxCitationHelpers";

export interface InboxAuxiliaryPanelsProps {
  readonly isFr: boolean;
  readonly activeWorkspaceId: string;
  readonly activeFolderId: string;
  readonly foldersPanelOpen: boolean;
  readonly governanceOpen: boolean;
  readonly governancePrefs: SavedAssistantGovernancePrefs;
  readonly canEditWorkspaceLayer: boolean;
  readonly mcpFrozenByUpperLayer: boolean;
  readonly mcpIdeConfigJson: string;
  readonly assembledLayers: readonly UiAssembledLayerItem[];
  readonly promptTelemetryLog: readonly UiAssistantPromptTelemetryRecord[];
  readonly folders: readonly UiAssistantFolderItem[];
  readonly authorIdentity: string;
  readonly dictionary: TranslationDictionary;
  readonly setGovernanceOpen: (open: boolean) => void;
  readonly setGovernanceFeedback: (msg: string | null) => void;
  readonly onSaveUserPreferences: (payload: {
    responseTone: SavedAssistantGovernancePrefs["responseTone"];
    favoriteFormat: SavedAssistantGovernancePrefs["favoriteFormat"];
    defaultHat: string;
    personalInstructions: string;
  }) => Promise<void>;
  readonly onSaveWorkspaceSettings: (payload: {
    workspaceInstructions: string;
    mcpExposeAssistant: boolean;
  }) => Promise<void>;
  readonly selectActiveFolderAndPersist: (folderId: string) => void;
  readonly createFolder: (title: string) => Promise<UiAssistantFolderItem | null>;
  readonly savePinnedNotes: (folder: UiAssistantFolderItem, notes: string) => Promise<boolean>;
  readonly changeVisibility: (folder: UiAssistantFolderItem, mode: AssistantFolderVisibilityMode) => Promise<boolean>;
  readonly onOpenHelpSection: (sectionId: string) => void;
  readonly onSendCollaborativeMessage: (message: string) => void;
  readonly onLaunchProcessFromFolder: (folderId: string, targetWorkflowUri: string) => void;
  readonly onNavigateToProcesses: () => void;
  readonly citationCardPreview?: BuiltCitationCardPreview | null;
}

export function InboxAuxiliaryPanels({
  isFr,
  activeWorkspaceId,
  activeFolderId,
  foldersPanelOpen,
  governanceOpen,
  governancePrefs,
  canEditWorkspaceLayer,
  mcpFrozenByUpperLayer,
  mcpIdeConfigJson,
  assembledLayers,
  promptTelemetryLog,
  folders,
  authorIdentity,
  dictionary,
  setGovernanceOpen,
  setGovernanceFeedback,
  onSaveUserPreferences,
  onSaveWorkspaceSettings,
  selectActiveFolderAndPersist,
  createFolder,
  savePinnedNotes,
  changeVisibility,
  onOpenHelpSection,
  onSendCollaborativeMessage,
  onLaunchProcessFromFolder,
  onNavigateToProcesses,
  citationCardPreview = null,
}: InboxAuxiliaryPanelsProps): React.JSX.Element {
  return (
    <>
      {governanceOpen ? (
        <AssistantGovernanceModalAndStudio
          workspaceId={activeWorkspaceId}
          canEditWorkspaceLayer={canEditWorkspaceLayer}
          initialUserTone={governancePrefs.responseTone}
          initialUserFormat={governancePrefs.favoriteFormat}
          initialDefaultHat={governancePrefs.defaultHat}
          initialPersonalInstructions={governancePrefs.personalInstructions}
          initialWorkspaceInstructions={governancePrefs.workspaceInstructions}
          initialMcpExposed={governancePrefs.mcpExposeAssistant}
          mcpFrozenByUpperLayer={mcpFrozenByUpperLayer}
          mcpIdeConfigJson={mcpIdeConfigJson}
          assembledLayers={assembledLayers}
          promptTelemetryLog={promptTelemetryLog}
          labels={dictionary.assistantGovernance}
          onSaveUserPreferences={(payload) => {
            void onSaveUserPreferences(payload);
          }}
          onSaveWorkspaceSettings={(payload) => {
            void onSaveWorkspaceSettings(payload);
          }}
          onCopyMcpConfig={(jsonText) => {
            if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
              void navigator.clipboard.writeText(jsonText).catch((err: unknown) => {
                console.warn("[orcia:assistant.copyMcp]", err instanceof Error ? err.message : String(err));
              });
            }
            setGovernanceFeedback(
              isFr
                ? "✅ Configuration éditeur copiée dans le presse-papiers."
                : "✅ Editor configuration copied to clipboard.",
            );
          }}
          onClose={() => setGovernanceOpen(false)}
        />
      ) : null}

      <div data-testid="assistant-folders-panel-wrapper" className={foldersPanelOpen ? "" : "sr-only"}>
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
          onLaunchProcessFromFolder={onLaunchProcessFromFolder}
        />
      </div>

      {citationCardPreview ? (
        <div data-testid="assistant-citations-card-wrapper">
          <AssistantCitationPillsAndArtifactCard
            sanitizedResponseText={citationCardPreview.sanitizedResponseText}
            strippedPhantomTags={citationCardPreview.strippedPhantomTags}
            sources={citationCardPreview.sources}
            glossaryItems={citationCardPreview.glossaryItems}
            toolOutputs={citationCardPreview.toolOutputs}
            footerSummaryLine={citationCardPreview.footerSummaryLine}
            artifactTitle={citationCardPreview.artifactTitle}
            artifactContent={citationCardPreview.artifactContent}
            labels={dictionary.assistantCitations}
            onInspectSource={citationCardPreview.onInspectSource}
            onRequestRestrictedAccess={citationCardPreview.onRequestRestrictedAccess}
            onContinueInProcess={onNavigateToProcesses}
          />
        </div>
      ) : null}
    </>
  );
}
