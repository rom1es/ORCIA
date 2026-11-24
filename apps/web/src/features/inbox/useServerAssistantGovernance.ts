import {
  createOrciaApiClient,
  type AssembledLayerPreviewSchemaItem,
  type AssistantGovernanceViewResponse,
} from "@orcia/api-client";
import type { UiAssembledLayerItem } from "@orcia/ui";
import { useCallback, useEffect, useState } from "react";
import { normalizeWebLocale, resolveDictionaryForFlag } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import {
  DEFAULT_ASSISTANT_GOVERNANCE_PREFS,
  type SavedAssistantGovernancePrefs,
} from "./assistantFoldersAndPrefsStore";

function mapAssembledLayer(item: AssembledLayerPreviewSchemaItem): UiAssembledLayerItem {
  return {
    layerNumber: item.layer_number,
    layerCode: item.layer_code,
    label: item.label,
    immutable: item.immutable,
    originBadge: item.origin_badge,
    content: item.content,
    sha256: item.sha256,
  };
}

function errorDetail(err: unknown, locale: string): string {
  const normalized = normalizeWebLocale(locale);
  const flowCopy = resolveDictionaryForFlag(undefined, normalized).featureInboxAssistant.assistantFlow;
  return formatRfc9457ErrorToBanner(err, normalized, flowCopy.governanceErrorContext).fullText;
}

export function useServerAssistantGovernance(params: {
  readonly workspaceId: string;
  readonly locale: string;
  readonly onFeedback: (message: string) => void;
}) {
  const { workspaceId, locale, onFeedback } = params;
  const normalizedLocale = normalizeWebLocale(locale);
  const flowCopy = resolveDictionaryForFlag(undefined, normalizedLocale).featureInboxAssistant.assistantFlow;
  const [governancePrefs, setGovernancePrefs] = useState<SavedAssistantGovernancePrefs>(
    DEFAULT_ASSISTANT_GOVERNANCE_PREFS,
  );
  const [assembledLayers, setAssembledLayers] = useState<readonly UiAssembledLayerItem[]>([]);
  const [canEditWorkspaceLayer, setCanEditWorkspaceLayer] = useState<boolean>(false);
  const [mcpFrozenByUpperLayer, setMcpFrozenByUpperLayer] = useState<boolean>(false);
  const [mcpIdeConfigJson, setMcpIdeConfigJson] = useState<string>("{}");
  const [governanceSaveMessage, setGovernanceSaveMessage] = useState<string | null>(null);

  const applyView = useCallback((view: AssistantGovernanceViewResponse) => {
    setGovernancePrefs({
      responseTone: view.user_preferences.response_tone,
      favoriteFormat: view.user_preferences.favorite_format,
      defaultHat: view.user_preferences.default_hat,
      personalInstructions: view.user_preferences.personal_instructions,
      workspaceInstructions: view.workspace_settings.workspace_instructions,
      mcpExposeAssistant: view.workspace_settings.mcp_expose_assistant,
    });
    setAssembledLayers((view.assembled_layers ?? []).map(mapAssembledLayer));
    setCanEditWorkspaceLayer(Boolean(view.can_edit_workspace_layer));
    setMcpFrozenByUpperLayer(Boolean(view.workspace_settings.mcp_frozen_by_upper_layer));
    setMcpIdeConfigJson(view.workspace_settings.mcp_ide_config_json || "{}");
  }, []);

  const refreshGovernance = useCallback(async (): Promise<void> => {
    if (!workspaceId) return;
    try {
      const view = await createOrciaApiClient({ baseUrl: "" }).getAssistantGovernance(
        workspaceId,
      );
      applyView(view);
    } catch (err: unknown) {
      onFeedback(errorDetail(err, locale));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, applyView]);

  useEffect(() => {
    void refreshGovernance();
  }, [refreshGovernance]);

  const saveUserPreferences = useCallback(
    async (payload: {
      responseTone: SavedAssistantGovernancePrefs["responseTone"];
      favoriteFormat: SavedAssistantGovernancePrefs["favoriteFormat"];
      defaultHat: string;
      personalInstructions: string;
    }): Promise<void> => {
      if (!workspaceId) return;
      try {
        await createOrciaApiClient({ baseUrl: "" }).updateAssistantUserPreferences({
          workspace_id: workspaceId,
          response_tone: payload.responseTone,
          favorite_format: payload.favoriteFormat,
          default_hat: payload.defaultHat,
          personal_instructions: payload.personalInstructions,
        });
        await refreshGovernance();
        setGovernanceSaveMessage(flowCopy.personalPrefsSavedBanner);
      } catch (err: unknown) {
        onFeedback(errorDetail(err, locale));
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [workspaceId, locale, refreshGovernance],
  );

  const saveWorkspaceSettings = useCallback(
    async (payload: {
      workspaceInstructions: string;
      mcpExposeAssistant: boolean;
    }): Promise<void> => {
      if (!workspaceId) return;
      try {
        await createOrciaApiClient({ baseUrl: "" }).updateAssistantWorkspaceSettings({
          workspace_id: workspaceId,
          workspace_instructions: payload.workspaceInstructions,
          mcp_expose_assistant: payload.mcpExposeAssistant,
        });
        await refreshGovernance();
        setGovernanceSaveMessage(flowCopy.workspaceSettingsSavedBanner);
      } catch (err: unknown) {
        onFeedback(errorDetail(err, locale));
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [workspaceId, locale, refreshGovernance],
  );

  return {
    governancePrefs,
    assembledLayers,
    canEditWorkspaceLayer,
    mcpFrozenByUpperLayer,
    mcpIdeConfigJson,
    governanceSaveMessage,
    setGovernanceSaveMessage,
    refreshGovernance,
    saveUserPreferences,
    saveWorkspaceSettings,
  };
}
