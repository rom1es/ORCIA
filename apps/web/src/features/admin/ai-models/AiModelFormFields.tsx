import {
  EffortSelector,
  type InferenceTierAndEffortLabels,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import React from "react";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";
import {
  AI_PROVIDER_PRESETS,
  GOOGLE_GEMINI_NATIVE_ENDPOINT,
  GOOGLE_GEMINI_OPENAI_ENDPOINT,
} from "../../../routes/settingsAiModelsPresets";

export const aiModelInputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "13px",
  width: "100%",
};

export interface AiModelFormFieldsProps {
  readonly mode: "create" | "edit" | "rotate-key";
  readonly labels: AiModelsHubDictionary;
  readonly tierLabels: InferenceTierAndEffortLabels;
  readonly modelFamily: string;
  readonly setModelFamily: (val: string) => void;
  readonly displayName: string;
  readonly setDisplayName: (val: string) => void;
  readonly primaryModel: string;
  readonly setPrimaryModel: (val: string) => void;
  readonly fallbackModel: string;
  readonly setFallbackModel: (val: string) => void;
  readonly endpointUri: string;
  readonly setEndpointUri: (val: string) => void;
  readonly authMode: "api_key" | "env_var" | "none_local";
  readonly setAuthMode: (val: "api_key" | "env_var" | "none_local") => void;
  readonly envVarName: string;
  readonly setEnvVarName: (val: string) => void;
  readonly rawApiKey: string;
  readonly setRawApiKey: (val: string) => void;
  readonly selectedTier: UiInferenceTier;
  readonly setSelectedTier: (val: UiInferenceTier) => void;
  readonly selectedEffort: UiInferenceEffort;
  readonly setSelectedEffort: (val: UiInferenceEffort) => void;
  readonly isGemini: boolean;
  readonly recommendedModels: readonly string[];
}

export function AiModelFormFields({
  mode,
  labels,
  tierLabels,
  modelFamily,
  setModelFamily,
  displayName,
  setDisplayName,
  primaryModel,
  setPrimaryModel,
  fallbackModel,
  setFallbackModel,
  endpointUri,
  setEndpointUri,
  authMode,
  setAuthMode,
  envVarName,
  setEnvVarName,
  rawApiKey,
  setRawApiKey,
  selectedTier,
  setSelectedTier,
  selectedEffort,
  setSelectedEffort,
  isGemini,
  recommendedModels,
}: AiModelFormFieldsProps): React.ReactElement {
  return (
    <>
      {mode === "create" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "12px", fontWeight: 600 }}>{labels.providerLabel} :</span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {AI_PROVIDER_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                data-testid={`llm-provider-preset-${preset.id}`}
                onClick={() => {
                  setModelFamily(preset.familyValue);
                  setEndpointUri(preset.defaultEndpointUrl);
                  setAuthMode(preset.defaultAuthMode as "api_key" | "env_var" | "none_local");
                  setPrimaryModel(preset.samplePrimaryModel);
                  setFallbackModel(preset.sampleSecondaryModel);
                  setDisplayName(`${preset.label} (${selectedTier})`);
                }}
                style={{
                  padding: "3px 9px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor:
                    modelFamily.toLowerCase() === preset.familyValue.toLowerCase()
                      ? "var(--color-action-primary-subtle)"
                      : "var(--color-surface-card)",
                  color: "var(--color-foreground)",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {isGemini && (
        <div
          data-testid="google-gemini-protocol-mode-selector"
          style={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-bg-elevated)",
            fontSize: "12px",
          }}
        >
          <span style={{ fontWeight: 600 }}>{labels.geminiProtocolLabel} :</span>
          <button
            type="button"
            data-testid="google-gemini-mode-native-btn"
            aria-pressed={endpointUri === GOOGLE_GEMINI_NATIVE_ENDPOINT}
            onClick={() => setEndpointUri(GOOGLE_GEMINI_NATIVE_ENDPOINT)}
            className="orcia-ds-btn orcia-ds-btn-secondary"
          >
            {labels.geminiModeB}
          </button>
          <button
            type="button"
            data-testid="google-gemini-mode-openai-btn"
            aria-pressed={endpointUri === GOOGLE_GEMINI_OPENAI_ENDPOINT}
            onClick={() => setEndpointUri(GOOGLE_GEMINI_OPENAI_ENDPOINT)}
            className="orcia-ds-btn orcia-ds-btn-secondary"
          >
            {labels.geminiModeA}
          </button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
        <EffortSelector
          selectedTier={selectedTier}
          selectedEffort={selectedEffort}
          labels={tierLabels}
          onTierChange={setSelectedTier}
          onEffortChange={setSelectedEffort}
        />
      </div>

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
        <span style={{ fontWeight: 600 }}>{labels.displayNameLabel}</span>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="ai-model-display-name-input"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder={labels.displayNamePlaceholder}
          style={aiModelInputStyle}
        />
      </label>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{labels.primaryModelLabel}</span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="ai-model-primary-model-input"
            value={primaryModel}
            onChange={(e) => setPrimaryModel(e.target.value)}
            disabled={mode === "edit"}
            style={aiModelInputStyle}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{labels.fallbackModelLabel}</span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="ai-model-fallback-model-input"
            value={fallbackModel}
            onChange={(e) => setFallbackModel(e.target.value)}
            style={aiModelInputStyle}
          />
        </label>
      </div>

      {mode === "create" && recommendedModels.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
          {recommendedModels.map((mod) => (
            <button
              key={mod}
              type="button"
              data-testid={`ai-model-quick-chip-${mod}`}
              onClick={() => setPrimaryModel(mod)}
              style={{
                padding: "2px 7px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor:
                  primaryModel === mod
                    ? "var(--color-action-primary-subtle)"
                    : "var(--color-surface-card)",
                color: "var(--color-foreground)",
                fontSize: "10px",
                fontFamily: "var(--font-mono)",
                cursor: "pointer",
              }}
            >
              {mod}
            </button>
          ))}
        </div>
      )}

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
        <span style={{ fontWeight: 600 }}>{labels.endpointUriLabel}</span>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="ai-model-endpoint-uri-input"
          value={endpointUri}
          onChange={(e) => setEndpointUri(e.target.value)}
          style={aiModelInputStyle}
        />
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
        <span style={{ fontWeight: 600 }}>{labels.authModeLabel}</span>
        <select
          data-testid="ai-model-auth-mode-select"
          value={authMode}
          onChange={(e) => setAuthMode(e.target.value as "api_key" | "env_var" | "none_local")}
          style={aiModelInputStyle}
        >
          <option value="api_key">{labels.authModeApiKey}</option>
          <option value="env_var">{labels.authModeEnvVar}</option>
          <option value="none_local">{labels.authModeNoneLocal}</option>
        </select>
      </label>

      {authMode === "env_var" && (
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{labels.envVarNameLabel}</span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="ai-model-env-var-name-input"
            value={envVarName}
            onChange={(e) => setEnvVarName(e.target.value)}
            placeholder={labels.envVarNamePlaceholder}
            style={aiModelInputStyle}
          />
        </label>
      )}

      {mode === "create" && authMode === "api_key" && (
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>Clé d'API secrète</span>
          <input
            type="text"
            className="orcia-masked-secret-input"
            spellCheck={false}
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="ai-model-api-key-input"
            value={rawApiKey}
            onChange={(e) => setRawApiKey(e.target.value)}
            placeholder="Saisir la clé d'API secrète..."
            style={{ ...aiModelInputStyle, WebkitTextSecurity: "disc" } as React.CSSProperties}
          />
        </label>
      )}
    </>
  );
}
