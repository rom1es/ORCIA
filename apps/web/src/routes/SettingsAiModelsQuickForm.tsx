import {
  OrciaAlertBanner,
  type InferenceTierAndEffortLabels,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import React from "react";
import type { ConfiguredLlmTierMapping, LlmAuthMode } from "../components/platformSetupStore";
import {
  AI_PROVIDER_PRESETS,
  GOOGLE_GEMINI_NATIVE_ENDPOINT,
  GOOGLE_GEMINI_OPENAI_ENDPOINT,
  type ConnectionTestFeedback,
} from "./settingsAiModelsPresets";

export interface SettingsAiModelsQuickFormProps {
  readonly isFr: boolean;
  readonly selectedTier: UiInferenceTier;
  readonly selectedEffort: UiInferenceEffort;
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
  readonly testResult: ConnectionTestFeedback | null;
  readonly setTestResult: (val: ConnectionTestFeedback | null) => void;
  readonly isGeminiActive: boolean;
  readonly geminiProtocolMode: "native" | "openai";
  readonly recommendedModels: readonly string[];
  readonly onQuickSubmit: () => void;
  readonly onEvaluateTest: () => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "13px",
};

const primaryBtnStyle: React.CSSProperties = {
  padding: "7px 14px",
  borderRadius: "var(--radius-sm)",
  border: "none",
  backgroundColor: "var(--color-primary-cobalt)",
  color: "var(--color-primary-foreground)",
  fontWeight: 600,
  cursor: "pointer",
};

const secondaryBtnStyle: React.CSSProperties = {
  padding: "7px 12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontWeight: 600,
  fontSize: "12px",
  cursor: "pointer",
};

export function SettingsAiModelsQuickForm({
  isFr,
  selectedTier,
  selectedEffort,
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
  testResult,
  setTestResult,
  isGeminiActive,
  geminiProtocolMode,
  recommendedModels,
  onQuickSubmit,
  onEvaluateTest,
}: SettingsAiModelsQuickFormProps): React.ReactElement {
  return (
    <details
      style={{
        borderTop: "1px solid var(--color-border)",
        paddingTop: "12px",
        marginTop: "8px",
      }}
    >
      <summary
        style={{
          fontSize: "12px",
          fontWeight: 600,
          cursor: "pointer",
          color: "var(--color-muted-foreground)",
          marginBottom: "10px",
        }}
      >
        {isFr ? "⚙ Configuration directe / rapide" : "⚙ Direct / quick configuration"}
      </summary>

      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px", fontSize: "12px", marginBottom: "10px" }}>
        {AI_PROVIDER_PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            data-testid={`llm-provider-preset-${preset.id}`}
            onClick={() => {
              setModelFamily(preset.familyValue);
              setEndpointUrl(preset.defaultEndpointUrl);
              setAuthMode(preset.defaultAuthMode);
              setPrimaryModel(preset.samplePrimaryModel);
              setSecondaryModel(preset.sampleSecondaryModel);
              setTestResult(null);
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

      {isGeminiActive && (
        <div
          data-testid="google-gemini-protocol-mode-selector"
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: "8px",
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-bg-elevated)",
            fontSize: "12px",
            marginBottom: "10px",
          }}
        >
          <span style={{ fontWeight: 600 }}>
            {isFr ? "Protocole Google Gemini :" : "Google Gemini protocol:"}
          </span>
          <button
            type="button"
            data-testid="google-gemini-mode-native-btn"
            aria-pressed={geminiProtocolMode === "native"}
            onClick={() => {
              setEndpointUrl(GOOGLE_GEMINI_NATIVE_ENDPOINT);
              setTestResult(null);
            }}
            style={{
              ...secondaryBtnStyle,
              backgroundColor:
                geminiProtocolMode === "native"
                  ? "var(--color-action-primary-subtle)"
                  : "var(--color-surface-card)",
            }}
          >
            Mode B
          </button>
          <button
            type="button"
            data-testid="google-gemini-mode-openai-btn"
            aria-pressed={geminiProtocolMode === "openai"}
            onClick={() => {
              setEndpointUrl(GOOGLE_GEMINI_OPENAI_ENDPOINT);
              setTestResult(null);
            }}
            style={{
              ...secondaryBtnStyle,
              backgroundColor:
                geminiProtocolMode === "openai"
                  ? "var(--color-action-primary-subtle)"
                  : "var(--color-surface-card)",
            }}
          >
            Mode A
          </button>
        </div>
      )}

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
          <span style={{ fontWeight: 600 }}>Fournisseur IA</span>
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
          <span style={{ fontWeight: 600 }}>Identifiant du modèle principal</span>
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
            style={inputStyle}
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>Modèle de secours</span>
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
            style={inputStyle}
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>URL Endpoint</span>
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
          <span style={{ fontWeight: 600 }}>Mode auth</span>
          <select
            data-testid="llm-auth-mode-select"
            value={authMode}
            onChange={(e) => setAuthMode(e.target.value as LlmAuthMode)}
            style={inputStyle}
          >
            <option value="api_key">Clé d'API</option>
            <option value="env_var">Variable d'environnement</option>
            <option value="none_local">Sans clé (Local)</option>
          </select>
        </label>

        {authMode === "api_key" && (
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>Clé d'API</span>
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
            🔌 Tester la connexion
          </button>
          <button type="submit" data-testid="save-llm-tier-btn" style={primaryBtnStyle}>
            Enregistrer le niveau
          </button>
        </div>
      </form>

      {testResult !== null && (
        <OrciaAlertBanner
          tone={testResult.ok ? "emerald" : "crimson"}
          role={testResult.ok ? "status" : "alert"}
          testId="llm-connection-test-result"
          data-ok={testResult.ok ? "true" : "false"}
          className="mt-2"
        >
          {testResult.message}
        </OrciaAlertBanner>
      )}

      {recommendedModels.length > 0 && (
        <div style={{ display: "none" }}>
          {recommendedModels.map((mod) => (
            <button
              key={mod}
              type="button"
              data-testid={`ai-model-quick-chip-${mod}`}
              onClick={() => setPrimaryModel(mod)}
            >
              {mod}
            </button>
          ))}
        </div>
      )}
    </details>
  );
}
