import type {
  AiModelCreateRequest,
  AiModelMappingItemResponse,
  AiModelPatchRequest,
} from "@orcia/api-client";
import type {
  DiscoveredModelOption,
  UiInferenceEffort,
  UiInferenceTier,
  UiSecretInputValue,
} from "@orcia/ui";
import { useCallback, useEffect, useState } from "react";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";
import {
  discoverProviderModelsViaApi,
  isGoogleGeminiFamily,
} from "../../../routes/settingsAiModelsPresets";

export type AiModelModalMode = "create" | "edit" | "rotate-key";

export function useAiModelConfigModalState(params: {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly mode: AiModelModalMode;
  readonly initialMapping?: AiModelMappingItemResponse | null;
  readonly labels: AiModelsHubDictionary;
  readonly onSubmitCreate: (
    payload: AiModelCreateRequest,
    andTest: boolean,
  ) => Promise<boolean>;
  readonly onSubmitPatch: (
    mappingId: string,
    payload: AiModelPatchRequest,
  ) => Promise<boolean>;
}) {
  const { open, onOpenChange, mode, initialMapping, labels, onSubmitCreate, onSubmitPatch } =
    params;

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
  const [discoveredModels, setDiscoveredModels] = useState<DiscoveredModelOption[]>([]);
  const [isDiscovering, setIsDiscovering] = useState<boolean>(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [hasUserInteracted, setHasUserInteracted] = useState<boolean>(false);

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
    setDiscoveryError(null);
    setHasUserInteracted(false);
    setIsSubmitting(false);
  }, [initialMapping, mode, open]);

  const isGemini = isGoogleGeminiFamily(modelFamily, endpointUri);

  const triggerDiscovery = useCallback(
    async (opts?: { forcedEndpoint?: string; forcedKey?: string; explicit?: boolean }) => {
      const targetEndpoint = (opts?.forcedEndpoint ?? endpointUri).trim();
      if (
        !targetEndpoint ||
        (!targetEndpoint.startsWith("http://") && !targetEndpoint.startsWith("https://"))
      ) {
        setDiscoveredModels([]);
        setDiscoveryError(null);
        return;
      }

      const effectiveProtocol =
        isGemini && targetEndpoint.includes("openai")
          ? "openai_compatible"
          : isGemini
            ? "gemini_native"
            : protocolMode;

      const effectiveKey =
        opts?.forcedKey ??
        (authMode === "api_key"
          ? rawApiKey.trim() || (secretAction === "set" ? secretInputText.trim() : "") // pragma: allowlist secret
          : undefined);

      const canShowError =
        Boolean(opts?.explicit) ||
        hasUserInteracted ||
        mode !== "create" ||
        authMode !== "api_key" ||
        Boolean(effectiveKey);

      setIsDiscovering(true);
      setDiscoveryError(null);

      const res = await discoverProviderModelsViaApi({
        endpointUri: targetEndpoint,
        protocolMode: effectiveProtocol,
        providerSlug: modelFamily.trim().toLowerCase(),
        mappingId: mode === "edit" || mode === "rotate-key" ? initialMapping?.id : undefined,
        apiKey: effectiveKey || undefined,
      });

      setIsDiscovering(false);
      if (res.ok) {
        setDiscoveredModels(
          res.models.map((m) => ({
            id: m.id,
            displayName: m.display_name,
            description: m.description,
            usageHint: m.usage_hint as "chat" | "embedding" | "unknown",
            ownedBy: m.owned_by,
          })),
        );
        setDiscoveryError(null);
      } else if (canShowError) {
        setDiscoveryError(res.error || labels.modelDiscoveryNoMatch);
      } else {
        setDiscoveryError(null);
      }
    },
    [
      endpointUri,
      isGemini,
      protocolMode,
      authMode,
      rawApiKey,
      secretAction,
      secretInputText,
      hasUserInteracted,
      mode,
      modelFamily,
      initialMapping?.id,
      labels.modelDiscoveryNoMatch,
    ],
  );

  useEffect(() => {
    if (!open) {
      setDiscoveredModels([]);
      setDiscoveryError(null);
      return;
    }

    const timer = setTimeout(() => {
      void triggerDiscovery();
    }, 500);

    return () => clearTimeout(timer);
  }, [
    open,
    endpointUri,
    rawApiKey,
    secretInputText,
    authMode,
    modelFamily,
    mode,
    initialMapping?.id,
    triggerDiscovery,
  ]);

  const handleSecretAction = (act: UiSecretInputValue) => {
    setHasUserInteracted(true);
    setSecretAction(act.action);
    setSecretInputText(act.plaintextValue ?? "");
  };

  const handleFormSubmit = async (andTest: boolean) => {
    setHasUserInteracted(true);
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
          usage,
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
          usage,
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

  return {
    selectedTier,
    setSelectedTier,
    selectedEffort,
    setSelectedEffort,
    modelFamily,
    setModelFamily: (val: string) => {
      setHasUserInteracted(true);
      setModelFamily(val);
    },
    displayName,
    setDisplayName,
    primaryModel,
    setPrimaryModel,
    fallbackModel,
    setFallbackModel,
    endpointUri,
    setEndpointUri: (val: string) => {
      setHasUserInteracted(true);
      setEndpointUri(val);
    },
    authMode,
    setAuthMode: (val: "api_key" | "env_var" | "none_local") => {
      setHasUserInteracted(true);
      setAuthMode(val);
    },
    envVarName,
    setEnvVarName,
    rawApiKey,
    setRawApiKey: (val: string) => {
      setHasUserInteracted(true);
      setRawApiKey(val);
    },
    isGemini,
    usage,
    setUsage,
    errorMessage,
    isSubmitting,
    discoveredModels,
    isDiscovering,
    discoveryError,
    triggerDiscovery,
    handleSecretAction,
    handleFormSubmit,
  };
}
