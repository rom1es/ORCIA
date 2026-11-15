import {
  AssistantGovernanceModalAndStudio,
  type AssistantGovernanceModalAndStudioLabels,
  type UiAssistantPromptTelemetryRecord,
} from "@orcia/ui";
import React from "react";
import type { SavedAssistantGovernancePrefs } from "./assistantFoldersAndPrefsStore";

export interface AssistantGovernanceDialogProps {
  readonly open: boolean;
  readonly workspaceId: string;
  readonly governancePrefs: SavedAssistantGovernancePrefs;
  readonly promptTelemetryLog: readonly UiAssistantPromptTelemetryRecord[];
  readonly labels: AssistantGovernanceModalAndStudioLabels;
  readonly isFr: boolean;
  readonly onSaveUserPrefs: (prefs: SavedAssistantGovernancePrefs, feedback: string) => void;
  readonly onSaveWorkspaceSettings: (prefs: SavedAssistantGovernancePrefs, feedback: string) => void;
  readonly onFeedback: (msg: string) => void;
  readonly onClose: () => void;
}

export function AssistantGovernanceDialog(props: AssistantGovernanceDialogProps): React.JSX.Element | null {
  const {
    open,
    workspaceId,
    governancePrefs,
    promptTelemetryLog,
    labels,
    isFr,
    onSaveUserPrefs,
    onSaveWorkspaceSettings,
    onFeedback,
    onClose,
  } = props;

  if (!open) return null;

  return (
    <AssistantGovernanceModalAndStudio
      workspaceId={workspaceId}
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
      labels={labels}
      onSaveUserPreferences={(payload) => {
        const next: SavedAssistantGovernancePrefs = {
          ...governancePrefs,
          responseTone: payload.responseTone,
          favoriteFormat: payload.favoriteFormat,
          defaultHat: payload.defaultHat,
          personalInstructions: payload.personalInstructions,
        };
        const fb = isFr
          ? `✅ Préférences personnelles enregistrées automatiquement (rôle : ${payload.defaultHat}).`
          : `✅ Personal preferences auto-saved (role: ${payload.defaultHat}).`;
        onSaveUserPrefs(next, fb);
      }}
      onSaveWorkspaceSettings={(payload) => {
        const next: SavedAssistantGovernancePrefs = {
          ...governancePrefs,
          workspaceInstructions: payload.workspaceInstructions,
          mcpExposeAssistant: payload.mcpExposeAssistant,
        };
        const fb = isFr
          ? `✅ Réglages de l'Espace enregistrés automatiquement (accès externe : ${payload.mcpExposeAssistant ? "activé" : "désactivé"}).`
          : `✅ Workspace settings auto-saved (external access: ${payload.mcpExposeAssistant ? "enabled" : "disabled"}).`;
        onSaveWorkspaceSettings(next, fb);
      }}
      onSaveStudioOverride={(payload) =>
        onFeedback(
          isFr
            ? `✅ Configuration avancée enregistrée pour le périmètre ${payload.scopeLevel}.`
            : `✅ Advanced configuration saved for scope ${payload.scopeLevel}.`,
        )
      }
      onResetStudioOverride={(scopeLevel) =>
        onFeedback(
          isFr
            ? `✅ Configuration réinitialisée aux valeurs par défaut (${scopeLevel}).`
            : `✅ Configuration reset to defaults (${scopeLevel}).`,
        )
      }
      onClose={onClose}
    />
  );
}
