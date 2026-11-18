import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaButton, OrciaSelect, OrciaTextarea } from "./DesignSystemControls";
import type {
  UiAssistantTone,
  UserAccountDropdownAndSettingsLabels,
  UserAccountPreferencesPatch,
} from "./UserAccountDropdownTypes";

export interface UserSettingsPersonalizationTabProps {
  readonly defaultAssistantHat: string;
  readonly assistantTone: UiAssistantTone;
  readonly personalInstructions: string;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly isSaving?: boolean;
  readonly savedMessage?: string | null;
  readonly onUpdatePreferences: (patch: UserAccountPreferencesPatch) => void | Promise<void>;
  readonly onDirtyChange?: (dirty: boolean) => void;
  readonly onNavigateAssistantBehavior?: (redirectUri: string) => void;
}

const ASSISTANT_HAT_KEYS = [
  "ANALYST_PM_PO",
  "ARCHITECT",
  "TECH_LEAD_DEV",
  "SECURITY_COMPLIANCE",
  "BU_LEAD",
] as const;

const ASSISTANT_TONE_KEYS: readonly UiAssistantTone[] = [
  "balanced",
  "concise",
  "detailed",
];

export function UserSettingsPersonalizationTab({
  defaultAssistantHat,
  assistantTone,
  personalInstructions,
  labels,
  isSaving = false,
  savedMessage = null,
  onUpdatePreferences,
  onDirtyChange,
  onNavigateAssistantBehavior,
}: UserSettingsPersonalizationTabProps): React.ReactElement {
  const [draftHat, setDraftHat] = useState(defaultAssistantHat);
  const [draftTone, setDraftTone] = useState<UiAssistantTone>(assistantTone);
  const [draftInstructions, setDraftInstructions] = useState(personalInstructions);
  const [localSaved, setLocalSaved] = useState(false);

  useEffect(() => {
    setDraftHat(defaultAssistantHat);
  }, [defaultAssistantHat]);

  useEffect(() => {
    setDraftTone(assistantTone);
  }, [assistantTone]);

  useEffect(() => {
    setDraftInstructions(personalInstructions);
  }, [personalInstructions]);

  const handleSave = async (): Promise<void> => {
    await onUpdatePreferences({
      defaultAssistantHat: draftHat,
      assistantTone: draftTone,
      personalInstructions: draftInstructions,
    });
    onDirtyChange?.(false);
    setLocalSaved(true);
  };

  return (
    <div data-testid="user-settings-panel-PERSONALIZATION" className="space-y-4">
      <div
        className="rounded-lg border p-3 space-y-3"
        style={{
          borderColor: "var(--color-border-subtle)",
          backgroundColor: "var(--color-surface-card)",
        }}
      >
        <label className="flex flex-col gap-1.5 text-xs">
          <span className="font-semibold" style={{ color: "var(--color-text-primary)" }}>
            {labels.assistantHatLabel}
          </span>
          <OrciaSelect
            testId="settings-assistant-hat-select"
            value={draftHat}
            onChange={(e) => {
              setDraftHat(e.target.value);
              setLocalSaved(false);
              onDirtyChange?.(true);
            }}
          >
            {ASSISTANT_HAT_KEYS.map((hatKey) => (
              <option key={hatKey} value={hatKey}>
                {labels.assistantHatOptions[hatKey] ?? hatKey}
              </option>
            ))}
          </OrciaSelect>
        </label>

        <label className="flex flex-col gap-1.5 text-xs">
          <span className="font-semibold" style={{ color: "var(--color-text-primary)" }}>
            {labels.assistantToneLabel}
          </span>
          <OrciaSelect
            testId="settings-assistant-tone-select"
            value={draftTone}
            onChange={(e) => {
              setDraftTone(e.target.value as UiAssistantTone);
              setLocalSaved(false);
              onDirtyChange?.(true);
            }}
          >
            {ASSISTANT_TONE_KEYS.map((toneKey) => (
              <option key={toneKey} value={toneKey}>
                {labels.assistantToneOptions[toneKey]}
              </option>
            ))}
          </OrciaSelect>
        </label>

        <label className="flex flex-col gap-1.5 text-xs">
          <span className="font-semibold" style={{ color: "var(--color-text-primary)" }}>
            {labels.personalInstructionsLabel}
          </span>
          <OrciaTextarea
            testId="settings-personal-instructions-input"
            rows={4}
            value={draftInstructions}
            placeholder={labels.personalInstructionsPlaceholder}
            onChange={(e) => {
              setDraftInstructions(e.target.value);
              setLocalSaved(false);
              onDirtyChange?.(true);
            }}
          />
        </label>

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <OrciaButton
            variant="primary"
            size="sm"
            testId="settings-personalization-save-btn"
            disabled={isSaving}
            onClick={() => void handleSave()}
          >
            <OrciaIcon name="check" size={14} />
            <span>{isSaving ? labels.savingLabel : labels.savePersonalizationLabel}</span>
          </OrciaButton>

          {onNavigateAssistantBehavior && (
            <button
              type="button"
              data-testid="user-settings-assistant-redirect-link"
              onClick={() => onNavigateAssistantBehavior("/assistant")}
              className="text-xs font-medium hover:underline"
              style={{ color: "var(--color-action-primary)" }}
            >
              {labels.customizeAssistantRedirectCta}
            </button>
          )}
        </div>

        {(localSaved || savedMessage) && (
          <div
            data-testid="settings-personalization-saved-banner"
            className="rounded border px-2.5 py-1.5 text-xs"
            style={{
              backgroundColor: "var(--color-gate-emerald-bg)",
              borderColor: "var(--color-gate-emerald)",
              color: "var(--color-gate-emerald)",
            }}
          >
            {savedMessage ?? labels.personalizationSavedMessage}
          </div>
        )}
      </div>
    </div>
  );
}
