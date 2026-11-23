import { OrciaModelCombobox, type DiscoveredModelOption } from "@orcia/ui";
import React from "react";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";
import { resolvePrimaryModelPlaceholder } from "../../../routes/settingsAiModelsPresets";

export const aiModelInputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "13px",
  width: "100%",
};

export interface AiModelAuthAndEndpointFieldsProps {
  readonly mode: "create" | "edit" | "rotate-key";
  readonly labels: AiModelsHubDictionary;
  readonly modelFamily: string;
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
  readonly usage: "chat" | "embedding";
  readonly discoveredModels: readonly DiscoveredModelOption[];
  readonly isDiscovering: boolean;
  readonly discoveryError: string | null;
  readonly onRefreshDiscovery?: () => void;
}

export function AiModelAuthAndEndpointFields({
  mode,
  labels,
  modelFamily,
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
  usage,
  discoveredModels,
  isDiscovering,
  discoveryError,
  onRefreshDiscovery,
}: AiModelAuthAndEndpointFieldsProps): React.ReactElement {
  const discoveryLabels = {
    noModelsFound: labels.modelDiscoveryNoMatch,
    refreshLabel: labels.modelDiscoveryRefresh,
    loadingLabel: labels.modelDiscoveryLoading,
    freeformHint: labels.modelDiscoveryFreeformHint,
    chatBadge: labels.chatBadge,
    embeddingBadge: labels.embeddingBadge,
  };

  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{labels.primaryModelLabel}</span>
          <OrciaModelCombobox
            testId="ai-model-primary-model-input"
            value={primaryModel}
            onChange={setPrimaryModel}
            disabled={mode === "edit"}
            models={discoveredModels}
            targetUsage={usage}
            isLoading={isDiscovering}
            errorMessage={discoveryError}
            onRefresh={onRefreshDiscovery}
            placeholder={resolvePrimaryModelPlaceholder(modelFamily, labels)}
            labels={discoveryLabels}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{labels.fallbackModelLabel}</span>
          <OrciaModelCombobox
            testId="ai-model-fallback-model-input"
            value={fallbackModel}
            onChange={setFallbackModel}
            models={discoveredModels}
            targetUsage={usage}
            isLoading={isDiscovering}
            onRefresh={onRefreshDiscovery}
            placeholder={labels.fallbackModelPlaceholder}
            labels={discoveryLabels}
          />
        </label>
      </div>

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

      {(mode === "create" || mode === "edit") && authMode === "api_key" && (
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{labels.secretApiKey}</span>
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
            placeholder={
              mode === "edit"
                ? labels.secretApiKeyEditPlaceholder
                : labels.secretApiKeyCreatePlaceholder
            }
            style={{ ...aiModelInputStyle, WebkitTextSecurity: "disc" } as React.CSSProperties}
          />
        </label>
      )}
    </>
  );
}
