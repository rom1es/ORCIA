import type {
  AiModelCreateRequest,
  AiModelDeleteImpactResponse,
  AiModelMappingItemResponse,
  AiModelPatchRequest,
} from "@orcia/api-client";
import type { UiInferenceEffort, UiInferenceTier } from "@orcia/ui";
import { useEffect, useState } from "react";
import type { ConfiguredLlmTierMapping, LlmAuthMode } from "../components/platformSetupStore";
import {
  createAiModelMappingViaApi,
  deleteAiModelMappingViaApi,
  fetchAiModelDeleteImpactViaApi,
  fetchAiModelMappings,
  patchAiModelMappingViaApi,
  testAiModelConnectionViaApi,
} from "../features/admin/ai-models/aiModelsApiBridge";
import type { AiModelModalMode } from "../features/admin/ai-models/AiModelConfigModal";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { buildFallbackMappingsFromProps } from "./settingsAiModelsFallback";
import {
  detectGoogleGeminiProtocolMode,
  isGoogleGeminiFamily,
  runRemoteLlmConnectionTestEvaluation,
  validateLlmConnectionParameters,
  type ConnectionTestFeedback,
} from "./settingsAiModelsPresets";

export function useAiModelsSectionController(params: {
  readonly isFr: boolean;
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly upsertLlmTier?: (input: ConfiguredLlmTierMapping) => void;
}) {
  const { isFr, llmTiers, upsertLlmTier } = params;
  const [serverMappings, setServerMappings] = useState<readonly AiModelMappingItemResponse[]>([]);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [modalState, setModalState] = useState<{
    open: boolean;
    mode: AiModelModalMode;
    mapping: AiModelMappingItemResponse | null;
  }>({ open: false, mode: "create", mapping: null });
  const [deleteState, setDeleteState] = useState<{
    open: boolean;
    mapping: AiModelMappingItemResponse | null;
    impact: AiModelDeleteImpactResponse | null;
    isLoadingImpact: boolean;
  }>({ open: false, mapping: null, impact: null, isLoadingImpact: false });

  const [selectedTier, setSelectedTier] = useState<UiInferenceTier>("medium");
  const [selectedEffort, setSelectedEffort] = useState<UiInferenceEffort>("balanced");
  const [modelFamily, setModelFamily] = useState<string>("Anthropic");
  const [primaryModel, setPrimaryModel] = useState<string>("");
  const [secondaryModel, setSecondaryModel] = useState<string>("");
  const [endpointUrl, setEndpointUrl] = useState<string>("https://api.anthropic.com/v1");
  const [authMode, setAuthMode] = useState<LlmAuthMode>("api_key");
  const [apiKeyInput, setApiKeyInput] = useState<string>("");
  const [testResult, setTestResult] = useState<ConnectionTestFeedback | null>(null);

  const loadMappings = async () => {
    const res = await fetchAiModelMappings(isFr ? "fr" : "en");
    if (res.ok && Array.isArray(res.data)) setServerMappings(res.data);
  };

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const accessToken = useAuthSessionStore((s) => s.accessToken);

  useEffect(() => {
    if (isHydrating || !isAuthenticated) return;
    void loadMappings();
  }, [isFr, isHydrating, isAuthenticated, accessToken]);

  const activeMappings =
    Array.isArray(serverMappings) && serverMappings.length > 0
      ? serverMappings
      : buildFallbackMappingsFromProps(llmTiers ?? []);

  const handleTestConnection = async (mappingId: string) => {
    setTestingId(mappingId);
    setOperationError(null);
    try {
      const res = await testAiModelConnectionViaApi(mappingId, isFr ? "fr" : "en");
      if (res.ok) {
        setServerMappings((prev) =>
          prev.map((m) =>
            m.id === mappingId
              ? { ...m, health_status: res.data.health_status, last_latency_ms: res.data.latency_ms, last_tested_at: res.data.tested_at }
              : m,
          ),
        );
      } else {
        setServerMappings((prev) =>
          prev.map((m) =>
            m.id === mappingId ? { ...m, health_status: "ERROR", last_tested_at: new Date().toISOString() } : m,
          ),
        );
        setOperationError(res.errorMessage);
      }
    } finally {
      setTestingId(null);
    }
  };

  const handleToggleActive = async (mapping: AiModelMappingItemResponse) => {
    const res = await patchAiModelMappingViaApi(mapping.id, { is_active: !mapping.is_active }, isFr ? "fr" : "en");
    if (res.ok) void loadMappings();
  };

  const handleOpenDelete = async (mapping: AiModelMappingItemResponse) => {
    setDeleteState({ open: true, mapping, impact: null, isLoadingImpact: true });
    const res = await fetchAiModelDeleteImpactViaApi(mapping.id, isFr ? "fr" : "en");
    setDeleteState((prev) =>
      res.ok ? { ...prev, impact: res.data, isLoadingImpact: false } : { ...prev, isLoadingImpact: false },
    );
  };

  const handleConfirmDelete = async (mappingId: string, mode: "reject" | "drain" | "force"): Promise<boolean> => {
    const res = await deleteAiModelMappingViaApi(mappingId, mode, isFr ? "fr" : "en");
    if (res.ok) {
      void loadMappings();
      return true;
    }
    return false;
  };

  const handleSubmitCreate = async (payload: AiModelCreateRequest, andTest: boolean): Promise<boolean> => {
    const res = await createAiModelMappingViaApi(payload, isFr ? "fr" : "en");
    if (!res.ok) throw new Error(res.errorMessage);
    if (upsertLlmTier) {
      upsertLlmTier({
        tier: (payload.inference_tier ?? "medium") as UiInferenceTier,
        primaryModel: payload.model_name,
        secondaryModel: payload.fallback_model_name || payload.model_name,
        modelFamily: payload.model_family,
        defaultEffort: (payload.effort ?? "balanced") as UiInferenceEffort,
        endpointUrl: payload.endpoint_uri,
        authMode: (payload.auth_mode ?? "api_key") as LlmAuthMode,
        apiKeyConfigured: Boolean(payload.secret_input?.plaintext_value || payload.auth_mode !== "api_key"),
      });
    }
    if (andTest) {
      const testRes = await testAiModelConnectionViaApi(res.data.id, isFr ? "fr" : "en");
      setOperationError(testRes.ok ? null : testRes.errorMessage);
    } else {
      setOperationError(null);
    }
    void loadMappings();
    return true;
  };

  const handleSubmitPatch = async (mappingId: string, payload: AiModelPatchRequest): Promise<boolean> => {
    const res = await patchAiModelMappingViaApi(mappingId, payload, isFr ? "fr" : "en");
    if (!res.ok) throw new Error(res.errorMessage);
    void loadMappings();
    return true;
  };

  const evaluateConnectionTest = async () => {
    const p = { provider: modelFamily, model: primaryModel, uri: endpointUrl, mode: authMode, rawKey: apiKeyInput, keyAlreadyConfigured: false };
    const syncErr = validateLlmConnectionParameters({ isFr, ...p });
    if (syncErr !== null) {
      setTestResult(syncErr);
      return;
    }
    setTestResult(await runRemoteLlmConnectionTestEvaluation({ isFr, ...p }));
  };

  const handleQuickSubmit = () => {
    if (!primaryModel.trim()) return;
    if (upsertLlmTier) {
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
    }
    void handleSubmitCreate(
      {
        scope_level: "GLOBAL",
        display_name: primaryModel.trim(),
        inference_tier: selectedTier,
        effort: selectedEffort,
        provider_slug: modelFamily.trim().toLowerCase(),
        model_family: modelFamily.trim(),
        model_name: primaryModel.trim(),
        fallback_model_name: secondaryModel.trim() || null,
        endpoint_uri: endpointUrl.trim(),
        auth_mode: authMode,
        protocol_mode: "openai_compatible",
        secret_input: authMode === "api_key" && apiKeyInput.trim() ? { action: "set", plaintext_value: apiKeyInput.trim() } : null,
        fallback_order: 1,
      },
      false,
    );
    setPrimaryModel("");
    setSecondaryModel("");
    setApiKeyInput("");
  };

  return {
    activeMappings,
    testingId,
    operationError,
    setOperationError,
    modalState,
    setModalState,
    deleteState,
    setDeleteState,
    selectedTier,
    setSelectedTier,
    selectedEffort,
    setSelectedEffort,
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
    isGeminiActive: isGoogleGeminiFamily(modelFamily, endpointUrl),
    geminiProtocolMode: detectGoogleGeminiProtocolMode(endpointUrl),
    handleTestConnection,
    handleToggleActive,
    handleOpenDelete,
    handleConfirmDelete,
    handleSubmitCreate,
    handleSubmitPatch,
    evaluateConnectionTest,
    handleQuickSubmit,
  };
}
