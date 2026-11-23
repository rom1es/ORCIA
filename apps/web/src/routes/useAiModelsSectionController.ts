import type {
  AiModelCreateRequest,
  AiModelDeleteImpactResponse,
  AiModelMappingItemResponse,
  AiModelPatchRequest,
} from "@orcia/api-client";
import type { UiInferenceEffort, UiInferenceTier } from "@orcia/ui";
import { useCallback, useEffect, useState } from "react";
import {
  useOptionalPlatformSetup,
  type LlmAuthMode,
} from "../components/platformSetupStore";
import {
  createAiModelMappingViaApi,
  deleteAiModelMappingViaApi,
  fetchAiModelDeleteImpactViaApi,
  fetchAiModelMappings,
  patchAiModelMappingViaApi,
  testAiModelConnectionViaApi,
} from "../features/admin/ai-models/aiModelsApiBridge";
import type { AiModelModalMode } from "../features/admin/ai-models/AiModelConfigModal";
import type { AiModelDeleteConfirmResult } from "../features/admin/ai-models/AiModelDeleteDialog";
import { useAuthSessionStore } from "../stores/authSessionStore";
import {
  detectGoogleGeminiProtocolMode,
  isGoogleGeminiFamily,
  resolveEffectiveLlmProtocolMode,
  runRemoteLlmConnectionTestEvaluation,
  validateLlmConnectionParameters,
  type ConnectionTestFeedback,
} from "./settingsAiModelsPresets";

export function useAiModelsSectionController(params: {
  readonly isFr: boolean;
}) {
  const { isFr } = params;
  const platformSetup = useOptionalPlatformSetup();
  const [serverMappings, setServerMappings] = useState<readonly AiModelMappingItemResponse[]>([]);
  const [mappingsRevision, setMappingsRevision] = useState<number>(0);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testErrorsByModelId, setTestErrorsByModelId] = useState<Record<string, string>>({});
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

  const [selectedTier] = useState<UiInferenceTier>("medium");
  const [selectedEffort] = useState<UiInferenceEffort>("balanced");
  const [modelFamily, setModelFamily] = useState<string>("Anthropic");
  const [primaryModel, setPrimaryModel] = useState<string>("");
  const [secondaryModel, setSecondaryModel] = useState<string>("");
  const [endpointUrl, setEndpointUrl] = useState<string>("https://api.anthropic.com/v1");
  const [authMode, setAuthMode] = useState<LlmAuthMode>("api_key");
  const [apiKeyInput, setApiKeyInput] = useState<string>("");
  const [testResult, setTestResult] = useState<ConnectionTestFeedback | null>(null);

  const loadMappings = useCallback(async () => {
    const res = await fetchAiModelMappings(isFr ? "fr" : "en");
    if (res.ok && Array.isArray(res.data)) {
      setServerMappings(res.data);
      setMappingsRevision((r) => r + 1);
    } else if (!res.ok) {
      setOperationError(res.errorMessage);
    }
  }, [isFr]);

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const accessToken = useAuthSessionStore((s) => s.accessToken);

  useEffect(() => {
    if (isHydrating || !isAuthenticated) return;
    void loadMappings();
  }, [isHydrating, isAuthenticated, accessToken, loadMappings]);

  const activeMappings = serverMappings;

  const clearModelTestError = (mappingId: string) => {
    setTestErrorsByModelId((prev) => {
      if (!(mappingId in prev)) return prev;
      const next = { ...prev };
      delete next[mappingId];
      return next;
    });
  };

  const handleTestConnection = async (mappingId: string) => {
    setTestingId(mappingId);
    clearModelTestError(mappingId);
    try {
      const res = await testAiModelConnectionViaApi(mappingId, isFr ? "fr" : "en");
      if (res.ok) {
        setServerMappings((prev) =>
          prev.map((m) =>
            m.id === mappingId
              ? {
                  ...m,
                  health_status: res.data.health_status,
                  last_latency_ms: res.data.latency_ms,
                  last_tested_at: res.data.tested_at,
                }
              : m,
          ),
        );
      } else {
        setServerMappings((prev) =>
          prev.map((m) =>
            m.id === mappingId
              ? { ...m, health_status: "ERROR", last_tested_at: new Date().toISOString() }
              : m,
          ),
        );
        setTestErrorsByModelId((prev) => ({
          ...prev,
          [mappingId]: res.errorMessage,
        }));
      }
    } finally {
      setTestingId(null);
    }
  };

  const handleToggleActive = async (mapping: AiModelMappingItemResponse) => {
    const res = await patchAiModelMappingViaApi(
      mapping.id,
      { is_active: !mapping.is_active },
      isFr ? "fr" : "en",
    );
    if (res.ok) {
      await loadMappings();
      await platformSetup?.refreshAccostage?.();
    } else {
      setOperationError(res.errorMessage);
    }
  };

  const handleOpenDelete = async (mapping: AiModelMappingItemResponse) => {
    setDeleteState({ open: true, mapping, impact: null, isLoadingImpact: true });
    const res = await fetchAiModelDeleteImpactViaApi(mapping.id, isFr ? "fr" : "en");
    setDeleteState((prev) =>
      res.ok ? { ...prev, impact: res.data, isLoadingImpact: false } : { ...prev, isLoadingImpact: false },
    );
  };

  const handleConfirmDelete = async (
    mappingId: string,
    mode: "reject" | "drain" | "force",
  ): Promise<AiModelDeleteConfirmResult> => {
    const res = await deleteAiModelMappingViaApi(mappingId, mode, isFr ? "fr" : "en");
    if (!res.ok) {
      return { ok: false, errorMessage: res.errorMessage };
    }
    clearModelTestError(mappingId);
    await loadMappings();
    await platformSetup?.refreshAccostage?.();
    return { ok: true };
  };

  const handleSubmitCreate = async (
    payload: AiModelCreateRequest,
    andTest: boolean,
  ): Promise<boolean> => {
    const res = await createAiModelMappingViaApi(payload, isFr ? "fr" : "en");
    if (!res.ok) throw new Error(res.errorMessage);
    setOperationError(null);
    if (andTest) {
      const testRes = await testAiModelConnectionViaApi(res.data.id, isFr ? "fr" : "en");
      if (!testRes.ok) {
        setTestErrorsByModelId((prev) => ({
          ...prev,
          [res.data.id]: testRes.errorMessage,
        }));
      }
    }
    await loadMappings();
    await platformSetup?.refreshAccostage?.();
    return true;
  };

  const handleSubmitPatch = async (
    mappingId: string,
    payload: AiModelPatchRequest,
  ): Promise<boolean> => {
    const res = await patchAiModelMappingViaApi(mappingId, payload, isFr ? "fr" : "en");
    if (!res.ok) throw new Error(res.errorMessage);
    await loadMappings();
    await platformSetup?.refreshAccostage?.();
    return true;
  };

  const evaluateConnectionTest = async () => {
    const p = {
      provider: modelFamily,
      model: primaryModel,
      uri: endpointUrl,
      mode: authMode,
      rawKey: apiKeyInput,
      keyAlreadyConfigured: false,
    };
    const syncErr = validateLlmConnectionParameters({ isFr, ...p });
    if (syncErr !== null) {
      setTestResult(syncErr);
      return;
    }
    setTestResult(await runRemoteLlmConnectionTestEvaluation({ isFr, ...p }));
  };

  const handleQuickSubmit = async () => {
    if (!primaryModel.trim()) return;
    try {
      await handleSubmitCreate(
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
          protocol_mode: resolveEffectiveLlmProtocolMode(modelFamily, endpointUrl),
          secret_input:
            authMode === "api_key" && apiKeyInput.trim()
              ? { action: "set", plaintext_value: apiKeyInput.trim() }
              : null,
          fallback_order: 1,
        },
        false,
      );
      setPrimaryModel("");
      setSecondaryModel("");
      setApiKeyInput("");
    } catch (err: unknown) {
      setOperationError(err instanceof Error ? err.message : String(err));
    }
  };

  return {
    activeMappings,
    mappingsRevision,
    testingId,
    testErrorsByModelId,
    operationError,
    setOperationError,
    modalState,
    setModalState,
    deleteState,
    setDeleteState,
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
    isGeminiActive: isGoogleGeminiFamily(modelFamily, endpointUrl),
    geminiProtocolMode: detectGoogleGeminiProtocolMode(endpointUrl),
    handleTestConnection,
    handleToggleActive,
    handleOpenDelete,
    handleConfirmDelete,
    handleSubmitCreate,
    handleSubmitPatch,
    evaluateConnectionTest,
    handleQuickSubmit: () => void handleQuickSubmit(),
  };
}
