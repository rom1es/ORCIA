import {
  OrciaAlertBanner,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import React from "react";
import type { LlmAuthMode } from "../components/platformSetupStore";
import { resolveDictionaryForFlag } from "../i18n";
import { SettingsAiModelsQuickFormFields } from "./SettingsAiModelsQuickFormFields";
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
  onQuickSubmit,
  onEvaluateTest,
}: SettingsAiModelsQuickFormProps): React.ReactElement {
  const dict = resolveDictionaryForFlag(isFr);
  const copy = dict.routesAndWizards.aiModelsQuickForm;
  const hubLabels = dict.aiModelsHub;

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
        {copy.summaryLabel}
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
          <span style={{ fontWeight: 600 }}>{copy.geminiProtocolLabel}</span>
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
            {copy.geminiModeNative}
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
            {copy.geminiModeOpenai}
          </button>
        </div>
      )}

      <SettingsAiModelsQuickFormFields
        copy={copy}
        hubLabels={hubLabels}
        modelFamily={modelFamily}
        setModelFamily={setModelFamily}
        primaryModel={primaryModel}
        setPrimaryModel={setPrimaryModel}
        secondaryModel={secondaryModel}
        setSecondaryModel={setSecondaryModel}
        endpointUrl={endpointUrl}
        setEndpointUrl={setEndpointUrl}
        authMode={authMode}
        setAuthMode={setAuthMode}
        apiKeyInput={apiKeyInput}
        setApiKeyInput={setApiKeyInput}
        onQuickSubmit={onQuickSubmit}
        onEvaluateTest={onEvaluateTest}
        inputStyle={inputStyle}
        primaryBtnStyle={primaryBtnStyle}
        secondaryBtnStyle={secondaryBtnStyle}
      />

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
    </details>
  );
}
