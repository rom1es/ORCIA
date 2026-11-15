import type {
  AiModelCreateRequest,
  AiModelMappingItemResponse,
  AiModelPatchRequest,
} from "@orcia/api-client";
import {
  OrciaDialog,
  SecretField,
  type InferenceTierAndEffortLabels,
  type SecretFieldLabels,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiSecretInputValue,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";
import { isGoogleGeminiFamily } from "../../../routes/settingsAiModelsPresets";
import { AiModelFormFields } from "./AiModelFormFields";

export type AiModelModalMode = "create" | "edit" | "rotate-key";

export interface AiModelConfigModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly mode: AiModelModalMode;
  readonly initialMapping?: AiModelMappingItemResponse | null;
  readonly labels: AiModelsHubDictionary;
  readonly tierLabels: InferenceTierAndEffortLabels;
  readonly isFr: boolean;
  readonly onSubmitCreate: (
    payload: AiModelCreateRequest,
    andTest: boolean,
  ) => Promise<boolean>;
  readonly onSubmitPatch: (
    mappingId: string,
    payload: AiModelPatchRequest,
  ) => Promise<boolean>;
}

export function AiModelConfigModal({
  open,
  onOpenChange,
  mode,
  initialMapping,
  labels,
  tierLabels,
  isFr,
  onSubmitCreate,
  onSubmitPatch,
}: AiModelConfigModalProps): React.ReactElement {
  const [selectedTier, setSelectedTier] = useState<UiInferenceTier>("medium");
  const [selectedEffort, setSelectedEffort] = useState<UiInferenceEffort>("balanced");
  const [modelFamily, setModelFamily] = useState<string>("Anthropic");
  const [displayName, setDisplayName] = useState<string>("");
  const [primaryModel, setPrimaryModel] = useState<string>("");
  const [fallbackModel, setFallbackModel] = useState<string>("");
  const [endpointUri, setEndpointUri] = useState<string>("https://api.anthropic.com/v1");
  const [authMode, setAuthMode] = useState<"api_key" | "env_var" | "none_local">("api_key");
  const [envVarName, setEnvVarName] = useState<string>("");
  const [rawApiKey, setRawApiKey] = useState<string>("");
  const [secretAction, setSecretAction] = useState<"keep" | "set" | "clear">("keep");
  const [secretInputText, setSecretInputText] = useState<string>("");
  const [protocolMode, setProtocolMode] = useState<
    "openai_compatible" | "gemini_native" | "anthropic_messages"
  >("openai_compatible");
  const [usage, setUsage] = useState<"chat" | "embedding">("chat");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    if (initialMapping && (mode === "edit" || mode === "rotate-key")) {
      setSelectedTier(initialMapping.inference_tier as UiInferenceTier);
      setSelectedEffort((initialMapping.effort ?? "balanced") as UiInferenceEffort);
      setModelFamily(initialMapping.provider_slug || "Anthropic");
      setDisplayName(initialMapping.display_name || "");
      setPrimaryModel(initialMapping.model_name || "");
      setFallbackModel(initialMapping.fallback_model_name || "");
      setEndpointUri(initialMapping.endpoint_uri || "");
      setAuthMode(initialMapping.auth_mode as "api_key" | "env_var" | "none_local");
      setEnvVarName(initialMapping.env_var_name || "");
      setProtocolMode(initialMapping.protocol_mode);
      setUsage((initialMapping.usage as "chat" | "embedding") ?? "chat");
      setSecretAction("keep");
      setSecretInputText("");
    } else {
      setSelectedTier("medium");
      setSelectedEffort("balanced");
      setModelFamily("Anthropic");
      setDisplayName("");
      setPrimaryModel("");
      setFallbackModel("");
      setEndpointUri("https://api.anthropic.com/v1");
      setAuthMode("api_key");
      setEnvVarName("");
      setRawApiKey("");
      setSecretAction("keep");
      setSecretInputText("");
      setProtocolMode("openai_compatible");
      setUsage("chat");
    }
    setErrorMessage(null);
    setIsSubmitting(false);
  }, [initialMapping, mode, open]);

  const isGemini = isGoogleGeminiFamily(modelFamily, endpointUri);

  const secretFieldLabels: SecretFieldLabels = {
    fieldLabel: "Clé d'API secrète",
    configuredBadge: "Configurée",
    unconfiguredBadge: "Non configurée",
    fingerprintPrefix: "Empreinte :",
    replaceSecretCta: "Remplacer", // pragma: allowlist secret
    cancelReplaceCta: "Annuler",
    clearSecretCta: "Effacer", // pragma: allowlist secret
    saveNewSecretCta: "Confirmer la nouvelle clé", // pragma: allowlist secret
    inputPlaceholder: "Saisir la nouvelle clé d'API...",
  };

  const handleSecretAction = (act: UiSecretInputValue) => {
    setSecretAction(act.action);
    setSecretInputText(act.plaintextValue ?? "");
  };

  const handleFormSubmit = async (andTest: boolean) => {
    if (usage === "embedding" && modelFamily.toLowerCase() === "anthropic") {
      setErrorMessage(labels.anthropicNoEmbeddingWarning);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      if (mode === "create") {
        const payload: AiModelCreateRequest = {
          scope_level: "GLOBAL",
          display_name: displayName.trim() || primaryModel.trim(),
          inference_tier: usage === "embedding" ? "auto" : selectedTier,
          effort: usage === "embedding" ? "default" : selectedEffort,
          provider_slug: modelFamily.trim().toLowerCase(),
          model_family: modelFamily.trim(),
          model_name: primaryModel.trim(),
          fallback_model_name: fallbackModel.trim() || null,
          endpoint_uri: endpointUri.trim(),
          auth_mode: authMode,
          protocol_mode:
            isGemini && endpointUri.includes("openai")
              ? "openai_compatible"
              : isGemini
                ? "gemini_native"
                : protocolMode,
          usage: usage,
          env_var_name: authMode === "env_var" ? envVarName.trim() : null,
          secret_input:
            authMode === "api_key" && rawApiKey.trim()
              ? { action: "set", plaintext_value: rawApiKey.trim() }
              : null,
          fallback_order: 1,
        };
        const ok = await onSubmitCreate(payload, andTest);
        if (ok) onOpenChange(false);
      } else if (mode === "edit" && initialMapping) {
        const patch: AiModelPatchRequest = {
          display_name: displayName.trim() || null,
          fallback_model_name: fallbackModel.trim() || null,
          endpoint_uri: endpointUri.trim() || null,
          auth_mode: authMode,
          env_var_name: authMode === "env_var" ? envVarName.trim() : null,
          protocol_mode: protocolMode,
          usage: usage,
        };
        const ok = await onSubmitPatch(initialMapping.id, patch);
        if (ok) onOpenChange(false);
      } else if (mode === "rotate-key" && initialMapping) {
        const patch: AiModelPatchRequest = {
          secret_input: {
            action: secretAction,
            plaintext_value: secretAction === "set" ? secretInputText.trim() || null : null, // pragma: allowlist secret
          },
        };
        const ok = await onSubmitPatch(initialMapping.id, patch);
        if (ok) onOpenChange(false);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const modalTitle =
    mode === "create"
      ? labels.modalCreateTitle
      : mode === "edit"
        ? labels.modalEditTitle
        : labels.modalRotateTitle;

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={modalTitle}
      description={labels.modalDescription}
      testId="ai-model-config-modal"
      closeLabel={labels.cancelBtn}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "12px" }}>
        {errorMessage && (
          <div
            role="alert"
            data-testid="ai-model-config-error"
            style={{
              padding: "8px 12px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border)",
              color: "var(--color-foreground)",
              fontSize: "12px",
            }}
          >
            {errorMessage}
          </div>
        )}

        {mode === "rotate-key" && initialMapping ? (
          <div data-testid="ai-model-rotate-key-container">
            <SecretField
              status={{
                configured: Boolean(initialMapping.secret_status?.configured),
                fingerprint: initialMapping.secret_status?.fingerprint ?? null,
                maskedHint: initialMapping.secret_status?.masked_hint ?? null,
                updatedAt: initialMapping.secret_status?.updated_at ?? "",
                updatedBy: initialMapping.secret_status?.updated_by ?? "",
              }}
              labels={secretFieldLabels}
              onSecretAction={handleSecretAction}
            />
          </div>
        ) : (
          <AiModelFormFields
            mode={mode}
            labels={labels}
            tierLabels={tierLabels}
            modelFamily={modelFamily}
            setModelFamily={setModelFamily}
            displayName={displayName}
            setDisplayName={setDisplayName}
            primaryModel={primaryModel}
            setPrimaryModel={setPrimaryModel}
            fallbackModel={fallbackModel}
            setFallbackModel={setFallbackModel}
            endpointUri={endpointUri}
            setEndpointUri={setEndpointUri}
            authMode={authMode}
            setAuthMode={setAuthMode}
            envVarName={envVarName}
            setEnvVarName={setEnvVarName}
            rawApiKey={rawApiKey}
            setRawApiKey={setRawApiKey}
            selectedTier={selectedTier}
            setSelectedTier={setSelectedTier}
            selectedEffort={selectedEffort}
            setSelectedEffort={setSelectedEffort}
            isGemini={isGemini}
            usage={usage}
            setUsage={setUsage}
          />
        )}

        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            gap: "8px",
            marginTop: "12px",
          }}
        >
          <button
            type="button"
            data-testid="cancel-ai-model-btn"
            onClick={() => onOpenChange(false)}
            className="orcia-ds-btn orcia-ds-btn-secondary"
          >
            {labels.cancelBtn}
          </button>

          {mode === "create" && (
            <button
              type="button"
              data-testid="save-and-test-ai-model-btn"
              disabled={isSubmitting}
              onClick={() => void handleFormSubmit(true)}
              className="orcia-ds-btn orcia-ds-btn-secondary"
            >
              {labels.saveAndTestBtn}
            </button>
          )}

          <button
            type="button"
            data-testid="save-ai-model-btn"
            disabled={isSubmitting}
            onClick={() => void handleFormSubmit(false)}
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {mode === "create" ? labels.saveOnlyBtn : labels.updateBtn}
          </button>
        </div>
      </div>
    </OrciaDialog>
  );
}
