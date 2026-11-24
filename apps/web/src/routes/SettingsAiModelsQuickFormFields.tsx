import React from "react";
import type { LlmAuthMode } from "../components/platformSetupStore";
import type { AiModelsHubDictionary } from "../i18n/locales/ai_models_hub_labels";
import type { RoutesAndWizardsDictionary } from "../i18n/locales/routes_and_wizards_labels";
import { resolvePrimaryModelPlaceholder } from "./settingsAiModelsPresets";

export interface SettingsAiModelsQuickFormFieldsProps {
  readonly copy: RoutesAndWizardsDictionary["aiModelsQuickForm"];
  readonly hubLabels: AiModelsHubDictionary;
  readonly modelFamily: string;
  readonly setModelFamily: (val: string) => void;
  readonly primaryModel: string;
  readonly setPrimaryModel: (val: string) => void;
  readonly secondaryModel: string;
  readonly setSecondaryModel: (val: string) => void;
  readonly endpointUrl: string;
  readonly setEndpointUrl: (val: string) => void;
  readonly authMode: LlmAuthMode;
  readonly setAuthMode: (val: LlmAuthMode) => void;
  readonly apiKeyInput: string;
  readonly setApiKeyInput: (val: string) => void;
  readonly onQuickSubmit: () => void;
  readonly onEvaluateTest: () => void;
  readonly inputStyle: React.CSSProperties;
  readonly primaryBtnStyle: React.CSSProperties;
  readonly secondaryBtnStyle: React.CSSProperties;
}

export function SettingsAiModelsQuickFormFields({
  copy,
  hubLabels,
  modelFamily,
  setModelFamily,
  primaryModel,
  setPrimaryModel,
  secondaryModel,
  setSecondaryModel,
  endpointUrl,
  setEndpointUrl,
  authMode,
  setAuthMode,
  apiKeyInput,
  setApiKeyInput,
  onQuickSubmit,
  onEvaluateTest,
  inputStyle,
  primaryBtnStyle,
  secondaryBtnStyle,
}: SettingsAiModelsQuickFormFieldsProps): React.ReactElement {
  return (
    <form
      data-testid="configure-llm-tier-form"
      autoComplete="off"
      data-lpignore="true"
      data-1p-ignore="true"
      data-bwignore="true"
      data-form-type="other"
      onSubmit={(e) => {
        e.preventDefault();
        onQuickSubmit();
      }}
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "10px",
        alignItems: "end",
      }}
    >
      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
        <span style={{ fontWeight: 600 }}>{copy.providerLabel}</span>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="llm-family-input"
          value={modelFamily}
          onChange={(e) => setModelFamily(e.target.value)}
          style={inputStyle}
        />
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
        <span style={{ fontWeight: 600 }}>{copy.primaryModelLabel}</span>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="llm-primary-model-input"
          value={primaryModel}
          onChange={(e) => setPrimaryModel(e.target.value)}
          placeholder={resolvePrimaryModelPlaceholder(modelFamily, hubLabels)}
          style={inputStyle}
        />
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
        <span style={{ fontWeight: 600 }}>{copy.secondaryModelLabel}</span>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="llm-secondary-model-input"
          value={secondaryModel}
          onChange={(e) => setSecondaryModel(e.target.value)}
          placeholder={hubLabels.fallbackModelPlaceholder}
          style={inputStyle}
        />
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
        <span style={{ fontWeight: 600 }}>{copy.endpointUrlLabel}</span>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="llm-endpoint-url-input"
          value={endpointUrl}
          onChange={(e) => setEndpointUrl(e.target.value)}
          style={inputStyle}
        />
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
        <span style={{ fontWeight: 600 }}>{copy.authModeLabel}</span>
        <select
          data-testid="llm-auth-mode-select"
          value={authMode}
          onChange={(e) => setAuthMode(e.target.value as LlmAuthMode)}
          style={inputStyle}
        >
          <option value="api_key">{copy.authApiKeyOption}</option>
          <option value="env_var">{copy.authEnvVarOption}</option>
          <option value="none_local">{copy.authNoneLocalOption}</option>
        </select>
      </label>

      {authMode === "api_key" && (
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{copy.apiKeyLabel}</span>
          <input
            type="text"
            className="orcia-masked-secret-input"
            spellCheck={false}
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="llm-api-key-input"
            value={apiKeyInput}
            onChange={(e) => setApiKeyInput(e.target.value)}
            style={{ ...inputStyle, WebkitTextSecurity: "disc" } as React.CSSProperties}
          />
        </label>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", gridColumn: "1 / -1", marginTop: "4px" }}>
        <button
          type="button"
          data-testid="test-llm-connection-btn"
          onClick={onEvaluateTest}
          style={secondaryBtnStyle}
        >
          {copy.testConnectionCta}
        </button>
        <button type="submit" data-testid="save-llm-tier-btn" style={primaryBtnStyle}>
          {copy.saveTierCta}
        </button>
      </div>
    </form>
  );
}
