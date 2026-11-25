import {
  createOrciaApiClient,
  type WorkspaceLayerSettingsSchemaItem,
} from "@orcia/api-client";
import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import type { WorkspaceFeedbackInput } from "./workspaceFeedbackTypes";

export interface WorkspaceMembersInstructionsCardProps {
  readonly isFr: boolean;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem;
  readonly onFeedback?: (feedback: WorkspaceFeedbackInput) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function WorkspaceMembersInstructionsCard({
  isFr,
  activeWorkspace,
  onFeedback,
}: WorkspaceMembersInstructionsCardProps): React.ReactElement {
  const locale = resolveLocaleForFlag(isFr);
  const tabsCopy = resolveDictionaryForFlag(isFr, locale).featureWorkspaces.detailTabs;
  const wsId = activeWorkspace.workspaceId;
  const isObserver = activeWorkspace.accessMode === "READ_ONLY_OBSERVER";

  const [instructionsByWs, setInstructionsByWs] = useState<Record<string, string>>({});
  const [wsSettings, setWsSettings] = useState<WorkspaceLayerSettingsSchemaItem | null>(null);
  const [canEditWorkspaceLayer, setCanEditWorkspaceLayer] = useState<boolean>(true);
  const [instructionsSavedWsId, setInstructionsSavedWsId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [errorAlert, setErrorAlert] = useState<string | null>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onFeedbackRef = useRef(onFeedback);
  onFeedbackRef.current = onFeedback;

  useEffect(() => {
    setErrorAlert(null);
    setInstructionsSavedWsId(null);
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    if (!wsId) return;

    let cancelled = false;
    const client = createOrciaApiClient({ baseUrl: "", locale });
    void client
      .getAssistantGovernance(wsId)
      .then((view) => {
        if (cancelled) return;
        setWsSettings(view.workspace_settings);
        setCanEditWorkspaceLayer(Boolean(view.can_edit_workspace_layer));
        setInstructionsByWs((prev) => ({
          ...prev,
          [wsId]: view.workspace_settings.workspace_instructions ?? "",
        }));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg = formatRfc9457ErrorToBanner(err, locale, tabsCopy.instructionsErrorContext)
          .fullText;
        if (onFeedbackRef.current) {
          setErrorAlert(null);
          onFeedbackRef.current({ tone: "crimson", message: msg });
        } else {
          setErrorAlert(msg);
        }
      });

    return () => {
      cancelled = true;
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
    };
  }, [wsId, locale, tabsCopy.instructionsErrorContext]);

  const persistInstructions = useCallback(
    async (targetWsId: string, rawText: string) => {
      if (!targetWsId || isObserver || !canEditWorkspaceLayer) return;
      const trimmed = rawText.trim();
      if (trimmed.length < 3) {
        if (onFeedbackRef.current) {
          setErrorAlert(null);
          onFeedbackRef.current({ tone: "crimson", message: tabsCopy.instructionsTooShortHint });
        } else {
          setErrorAlert(tabsCopy.instructionsTooShortHint);
        }
        return;
      }
      setIsSaving(true);
      setErrorAlert(null);
      const client = createOrciaApiClient({ baseUrl: "", locale });
      try {
        const updated = await client.updateAssistantWorkspaceSettings({
          workspace_id: targetWsId,
          workspace_instructions: trimmed,
          default_checked_sources: wsSettings?.default_checked_sources ?? [],
          recommended_agents: wsSettings?.recommended_agents ?? [],
          arbitration_policy: wsSettings?.arbitration_policy ?? "PAUSE_AND_ESCALATE",
          mcp_expose_assistant: wsSettings?.mcp_expose_assistant ?? true,
        });
        setWsSettings(updated);
        setInstructionsSavedWsId(targetWsId);
      } catch (err: unknown) {
        setInstructionsSavedWsId(null);
        const msg = formatRfc9457ErrorToBanner(err, locale, tabsCopy.instructionsErrorContext)
          .fullText;
        if (onFeedbackRef.current) {
          setErrorAlert(null);
          onFeedbackRef.current({ tone: "crimson", message: msg });
        } else {
          setErrorAlert(msg);
        }
      } finally {
        setIsSaving(false);
      }
    },
    [
      isObserver,
      canEditWorkspaceLayer,
      locale,
      tabsCopy.instructionsTooShortHint,
      tabsCopy.instructionsErrorContext,
      wsSettings,
    ],
  );

  const currentValue = instructionsByWs[wsId] ?? "";
  const isEditable = !isObserver && canEditWorkspaceLayer;

  return (
    <div
      data-testid="workspace-detail-members-content"
      style={{ display: "flex", flexDirection: "column", gap: "10px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div>
          <strong style={{ fontSize: "13px" }}>
            {formatI18nTemplate(tabsCopy.ownerTeamTemplate, {
              owner: activeWorkspace.ownerOrgUnitName ?? tabsCopy.defaultPlatformOwnerName,
            })}
          </strong>
          <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            {tabsCopy.instructionsHint}
          </p>
        </div>
        {instructionsSavedWsId === wsId && (
          <span
            data-testid="workspace-instructions-saved-badge"
            style={{
              fontSize: "11px",
              fontWeight: 700,
              padding: "3px 8px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-action-primary-subtle)",
              color: "var(--color-status-success)",
            }}
          >
            {tabsCopy.savedBadge}
          </span>
        )}
      </div>

      {!onFeedback && errorAlert ? (
        <div
          role="alert"
          data-testid="workspace-instructions-error-alert"
          className="rounded border border-status-danger/40 bg-status-danger/10 px-3 py-2 text-xs text-status-danger"
        >
          {errorAlert}
        </div>
      ) : null}

      <textarea
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        data-testid="workspace-instructions-textarea"
        rows={3}
        disabled={!isEditable}
        value={currentValue}
        onChange={(e) => {
          const val = e.target.value;
          setInstructionsByWs((prev) => ({ ...prev, [wsId]: val }));
          setInstructionsSavedWsId(null);
          setErrorAlert(null);
          if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
          }
          if (isEditable && val.trim().length >= 3) {
            debounceTimerRef.current = setTimeout(() => {
              void persistInstructions(wsId, val);
            }, 120);
          }
        }}
        placeholder={tabsCopy.instructionsPlaceholder}
        style={{ ...inputStyle, width: "100%", fontFamily: "var(--font-sans)" }}
      />

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          type="button"
          data-testid="workspace-instructions-save-btn"
          disabled={!isEditable || isSaving || currentValue.trim().length < 3}
          aria-busy={isSaving}
          onClick={() => {
            if (debounceTimerRef.current) {
              clearTimeout(debounceTimerRef.current);
              debounceTimerRef.current = null;
            }
            void persistInstructions(wsId, currentValue);
          }}
          className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
        >
          {isSaving ? tabsCopy.savingInstructionsBtn : tabsCopy.saveInstructionsBtn}
        </button>
      </div>
    </div>
  );
}
