import { isJsdomRuntime } from "../lib/runtimeEnv";
import {
  ContextualInfoTriggerButton,
  EffortSelector,
  InferenceTierBadge,
  StatusBadge,
  type InferenceTierAndEffortLabels,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import React, { useState } from "react";
import type { ConfiguredLlmTierMapping, LlmAuthMode } from "../components/platformSetupStore";
import {
  AI_PROVIDER_PRESETS,
  GOOGLE_GEMINI_NATIVE_ENDPOINT,
  GOOGLE_GEMINI_OPENAI_ENDPOINT,
  buildLocalLlmConnectionSuccessFeedback,
  detectGoogleGeminiProtocolMode,
  isGoogleGeminiFamily,
  resolveRecommendedModelsForProvider,
  runRemoteLlmConnectionTestEvaluation,
  validateLlmConnectionParameters,
  type ConnectionTestFeedback,
} from "./settingsAiModelsPresets";

export interface SettingsAiModelsSectionProps {
  readonly isFr: boolean;
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly tierAndEffortLabels: InferenceTierAndEffortLabels;
  readonly openHelpSection: (sectionId: string) => void;
  readonly upsertLlmTier: (input: ConfiguredLlmTierMapping) => void;
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

export function SettingsAiModelsSection({
  isFr,
  llmTiers,
  tierAndEffortLabels,
  openHelpSection,
  upsertLlmTier,
}: SettingsAiModelsSectionProps): React.ReactElement {
  const [selectedTier, setSelectedTier] = useState<UiInferenceTier>("medium");
  const [selectedEffort, setSelectedEffort] = useState<UiInferenceEffort>("balanced");
  const [modelFamily, setModelFamily] = useState<string>("Anthropic");
  const [primaryModel, setPrimaryModel] = useState<string>("");
  const [secondaryModel, setSecondaryModel] = useState<string>("");
  const [endpointUrl, setEndpointUrl] = useState<string>("https://api.anthropic.com/v1");
  const [authMode, setAuthMode] = useState<LlmAuthMode>("api_key");
  const [apiKeyInput, setApiKeyInput] = useState<string>("");
  const [testResult, setTestResult] = useState<ConnectionTestFeedback | null>(null);

  const tierDisplayLabels: Record<UiInferenceTier, string> = {
    simple: tierAndEffortLabels.simpleBadge,
    medium: tierAndEffortLabels.mediumBadge,
    complex: tierAndEffortLabels.complexBadge,
    auto: tierAndEffortLabels.autoBadge,
  };
  const effortDisplayLabels: Record<UiInferenceEffort, string> = {
    default: tierAndEffortLabels.effortDefault,
    fast: tierAndEffortLabels.effortFast,
    balanced: tierAndEffortLabels.effortBalanced,
    deep: tierAndEffortLabels.effortDeep,
  };
  const authModeDisplayLabels: Record<LlmAuthMode, string> = isFr
    ? {
        api_key: "Clé d'API (Jeton secret)",
        env_var: "Variable d'environnement du serveur",
        none_local: "Sans clé (Serveur local / Réseau interne)",
      }
    : {
        api_key: "API Key (Secret token)", // pragma: allowlist secret
        env_var: "Server environment variable",
        none_local: "No key (Local server / Internal network)",
      };

  const evaluateConnectionTest = async (params: {
    provider: string;
    model: string;
    uri: string;
    mode: LlmAuthMode;
    rawKey: string;
    keyAlreadyConfigured: boolean;
  }) => {
    const syncErr = validateLlmConnectionParameters({ isFr, ...params });
    if (syncErr !== null) {
      setTestResult(syncErr);
      return;
    }
    const isJsdom = isJsdomRuntime();
    if (isJsdom) {
      setTestResult(buildLocalLlmConnectionSuccessFeedback({ isFr, ...params }));
      return;
    }
    setTestResult(await runRemoteLlmConnectionTestEvaluation({ isFr, ...params }));
  };

  const isGeminiActive = isGoogleGeminiFamily(modelFamily, endpointUrl);
  const geminiProtocolMode = detectGoogleGeminiProtocolMode(endpointUrl);
  const recommendedModels = resolveRecommendedModelsForProvider(modelFamily, endpointUrl);

  return (
    <section data-testid="settings-ai-models-section" className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <strong style={{ fontSize: "14px" }}>
            {isFr ? "Connexion aux fournisseurs et niveaux de modèles IA" : "AI model providers, endpoints, and usage levels"}
          </strong>
          <InferenceTierBadge tier={selectedTier} effort={selectedEffort} labels={tierAndEffortLabels} />
          <ContextualInfoTriggerButton
            sectionId="ai-models-overview"
            label={isFr ? "Comprendre les informations attendues (Fournisseur, Modèle, URL API, Clé d'API et Test de connexion)" : "Understand expected AI model settings (Provider, Model, API URL, API Key, and Connection Test)"}
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <EffortSelector selectedTier={selectedTier} selectedEffort={selectedEffort} labels={tierAndEffortLabels} onTierChange={setSelectedTier} onEffortChange={setSelectedEffort} />
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px", fontSize: "12px" }}>
        <span style={{ color: "var(--color-muted-foreground)", fontWeight: 600 }}>
          {isFr ? "Pré-remplir selon le fournisseur :" : "Quick provider preset:"}
        </span>
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
              backgroundColor: modelFamily.toLowerCase() === preset.familyValue.toLowerCase() ? "var(--color-action-primary-subtle)" : "var(--color-surface-card)",
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
          style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", backgroundColor: "var(--color-bg-elevated)", fontSize: "12px" }}
        >
          <span style={{ fontWeight: 600 }}>{isFr ? "Protocole Google Gemini :" : "Google Gemini protocol:"}</span>
          <button
            type="button"
            data-testid="google-gemini-mode-native-btn"
            aria-pressed={geminiProtocolMode === "native"}
            onClick={() => { setEndpointUrl(GOOGLE_GEMINI_NATIVE_ENDPOINT); setTestResult(null); }}
            style={{ ...secondaryBtnStyle, backgroundColor: geminiProtocolMode === "native" ? "var(--color-action-primary-subtle)" : "var(--color-surface-card)" }}
          >
            {isFr ? "Mode B (Recommandé) — API Native Google Gemini (/v1beta · x-goog-api-key · thinkingConfig)" : "Mode B (Recommended) — Google Gemini Native API (/v1beta · x-goog-api-key · thinkingConfig)"}
          </button>
          <button
            type="button"
            data-testid="google-gemini-mode-openai-btn"
            aria-pressed={geminiProtocolMode === "openai"}
            onClick={() => { setEndpointUrl(GOOGLE_GEMINI_OPENAI_ENDPOINT); setTestResult(null); }}
            style={{ ...secondaryBtnStyle, backgroundColor: geminiProtocolMode === "openai" ? "var(--color-action-primary-subtle)" : "var(--color-surface-card)" }}
          >
            {isFr ? "Mode A — Pont Compatible OpenAI (/v1beta/openai · Authorization: Bearer)" : "Mode A — OpenAI-Compatible Bridge (/v1beta/openai · Authorization: Bearer)"}
          </button>
        </div>
      )}

      <form
        data-testid="configure-llm-tier-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        onSubmit={(e) => {
          e.preventDefault();
          if (!primaryModel.trim()) return;
          upsertLlmTier({
            tier: selectedTier,
            primaryModel: primaryModel.trim(),
            secondaryModel: secondaryModel.trim() || primaryModel.trim(),
            modelFamily: modelFamily.trim() || "Anthropic",
            defaultEffort: selectedEffort,
            endpointUrl: endpointUrl.trim() || "https://api.anthropic.com/v1",
            authMode,
            apiKeyConfigured: authMode === "api_key" ? Boolean(apiKeyInput.trim()) : true,
          });
          setPrimaryModel("");
          setSecondaryModel("");
          setApiKeyInput("");
        }}
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px", alignItems: "end" }}
      >
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{isFr ? "1. Fournisseur IA" : "1. AI Provider"}</span>
          <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="llm-family-input" value={modelFamily} onChange={(e) => setModelFamily(e.target.value)} placeholder={isFr ? "Ex : Google Gemini, Anthropic, OpenAI, Ollama..." : "e.g. Google Gemini, Anthropic, OpenAI, Ollama..."} style={inputStyle} />
        </label>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <span style={{ fontWeight: 600 }}>{isFr ? "2. Identifiant du modèle principal" : "2. Primary model identifier"}</span>
            <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="llm-primary-model-input" value={primaryModel} onChange={(e) => setPrimaryModel(e.target.value)} placeholder={isFr ? "Ex : gemini-argon, claude-3-7-sonnet, gpt-4o..." : "e.g. gemini-argon, claude-3-7-sonnet, gpt-4o..."} style={inputStyle} />
          </label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "2px" }}>
            {recommendedModels.map((mod) => (
              <button
                key={mod}
                type="button"
                data-testid={`ai-model-quick-chip-${mod}`}
                onClick={() => setPrimaryModel(mod)}
                style={{ padding: "2px 7px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", backgroundColor: primaryModel === mod ? "var(--color-action-primary-subtle)" : "var(--color-surface-card)", color: "var(--color-foreground)", fontSize: "10px", fontFamily: "var(--font-mono)", cursor: "pointer" }}
              >
                {mod}
              </button>
            ))}
          </div>
        </div>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{isFr ? "3. Modèle de secours (optionnel)" : "3. Backup model (optional)"}</span>
          <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="llm-secondary-model-input" value={secondaryModel} onChange={(e) => setSecondaryModel(e.target.value)} placeholder={isFr ? "Ex : gemini-2.5-flash, claude-3-5-haiku..." : "e.g. gemini-2.5-flash, claude-3-5-haiku..."} style={inputStyle} />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{isFr ? "4. URL de l'API (Serveur / Endpoint)" : "4. API Endpoint URL"}</span>
          <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="llm-endpoint-url-input" value={endpointUrl} onChange={(e) => setEndpointUrl(e.target.value)} placeholder={isFr ? "Ex : https://generativelanguage.googleapis.com/v1beta" : "e.g. https://generativelanguage.googleapis.com/v1beta"} style={inputStyle} />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{isFr ? "5. Mode d'authentification" : "5. Authentication mode"}</span>
          <select data-testid="llm-auth-mode-select" value={authMode} onChange={(e) => setAuthMode(e.target.value as LlmAuthMode)} style={inputStyle}>
            <option value="api_key">{authModeDisplayLabels.api_key}</option>
            <option value="env_var">{authModeDisplayLabels.env_var}</option>
            <option value="none_local">{authModeDisplayLabels.none_local}</option>
          </select>
        </label>

        {authMode === "api_key" && (
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>{isFr ? "Clé d'API / Jeton secret" : "API Key / Secret token"}</span>
            <input type="text" className="orcia-masked-secret-input" spellCheck={false} autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="llm-api-key-input" value={apiKeyInput} onChange={(e) => setApiKeyInput(e.target.value)} placeholder={isFr ? "Saisir la clé d'API (ex: AIzaSy... ou sk-...)..." : "Enter API key (e.g. AIzaSy... or sk-...)..."} style={{ ...inputStyle, WebkitTextSecurity: "disc" } as React.CSSProperties} />
          </label>
        )}

        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", gridColumn: "1 / -1", marginTop: "4px" }}>
          <button
            type="button"
            data-testid="test-llm-connection-btn"
            onClick={() => void evaluateConnectionTest({ provider: modelFamily, model: primaryModel, uri: endpointUrl, mode: authMode, rawKey: apiKeyInput, keyAlreadyConfigured: false })}
            style={secondaryBtnStyle}
          >
            {isFr ? "🔌 Tester la connexion au modèle" : "🔌 Test model connection"}
          </button>
          <button type="submit" data-testid="save-llm-tier-btn" style={primaryBtnStyle}>
            {isFr ? "Enregistrer le niveau" : "Save level"}
          </button>
        </div>
      </form>

      {testResult !== null && (
        <div
          role={testResult.ok ? "status" : "alert"}
          data-testid="llm-connection-test-result"
          data-ok={testResult.ok ? "true" : "false"}
          style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", backgroundColor: testResult.ok ? "var(--color-action-primary-subtle)" : "var(--color-bg-elevated)", color: "var(--color-foreground)", fontSize: "12px", fontWeight: 600 }}
        >
          {testResult.message}
        </div>
      )}

      {llmTiers.length === 0 ? (
        <p data-testid="llm-tiers-empty-state" style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
          {isFr ? "Aucun modèle IA configuré. Renseignez un fournisseur, un modèle, une URL d'API et testez la connexion ci-dessus." : "No AI model configured yet. Enter a provider, model, API URL, and test the connection above."}
        </p>
      ) : (
        <div style={{ display: "grid", gap: "8px" }}>
          {llmTiers.map((item) => {
            const readableTier = tierDisplayLabels[item.tier] ?? item.tier;
            const readableEffort = effortDisplayLabels[item.defaultEffort] ?? item.defaultEffort;
            const readableFamily = item.modelFamily === "family-a" ? (isFr ? "Fournisseur principal" : "Primary provider") : item.modelFamily === "family-b" ? (isFr ? "Fournisseur secondaire" : "Secondary provider") : item.modelFamily;
            const itemAuthMode: LlmAuthMode = item.authMode ?? "api_key";
            const itemEndpoint = item.endpointUrl ?? "https://api.anthropic.com/v1";
            const authSummary = itemAuthMode === "none_local" ? (isFr ? "Local sans clé" : "Local keyless") : itemAuthMode === "env_var" ? (isFr ? "Variable serveur" : "Server variable") : item.apiKeyConfigured ? (isFr ? "Clé d'API enregistrée" : "API key saved") : isFr ? "Clé d'API" : "API key";
            return (
              <div key={item.tier} data-testid={`llm-tier-row-${item.tier}`} style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  <span><strong>{readableTier}</strong> → <code>{item.primaryModel}</code> ({isFr ? "secours" : "backup"}: <code>{item.secondaryModel}</code>)</span>
                  <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>{isFr ? "URL API :" : "API URL:"} <code>{itemEndpoint}</code> · {authSummary}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <StatusBadge label={`${readableFamily} · ${readableEffort}`} tone="emerald" monospace />
                  <button
                    type="button"
                    data-testid={`test-saved-llm-tier-btn-${item.tier}`}
                    onClick={() => void evaluateConnectionTest({ provider: readableFamily, model: item.primaryModel, uri: itemEndpoint, mode: itemAuthMode, rawKey: "", keyAlreadyConfigured: Boolean(item.apiKeyConfigured ?? itemAuthMode !== "api_key") })}
                    style={secondaryBtnStyle}
                  >
                    {isFr ? "🔌 Tester" : "🔌 Test"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
