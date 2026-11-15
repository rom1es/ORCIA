import type {
  AiModelCreateRequest,
  AiModelDeleteImpactResponse,
  AiModelMappingItemResponse,
  AiModelPatchRequest,
} from "@orcia/api-client";
import {
  ContextualInfoTriggerButton,
  type InferenceTierAndEffortLabels,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiPermissionVerb,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { ConfiguredLlmTierMapping, LlmAuthMode } from "../components/platformSetupStore";
import {
  createAiModelMappingViaApi,
  deleteAiModelMappingViaApi,
  fetchAiModelDeleteImpactViaApi,
  fetchAiModelMappings,
  patchAiModelMappingViaApi,
  testAiModelConnectionViaApi,
} from "../features/admin/ai-models/aiModelsApiBridge";
import {
  AiModelConfigModal,
  type AiModelModalMode,
} from "../features/admin/ai-models/AiModelConfigModal";
import { AiModelDeleteDialog } from "../features/admin/ai-models/AiModelDeleteDialog";
import { AiModelReindexPanel } from "../features/admin/ai-models/AiModelReindexPanel";
import { AiModelsMasterTable } from "../features/admin/ai-models/AiModelsMasterTable";
import { useI18n } from "../i18n";
import { useAuthSessionStore } from "../stores/authSessionStore";
import {
  AI_MODELS_HUB_EN,
  AI_MODELS_HUB_FR,
} from "../i18n/locales/ai_models_hub_labels";
import { SettingsAiModelsQuickForm } from "./SettingsAiModelsQuickForm";
import { buildFallbackMappingsFromProps } from "./settingsAiModelsFallback";
import {
  detectGoogleGeminiProtocolMode,
  isGoogleGeminiFamily,
  runRemoteLlmConnectionTestEvaluation,
  validateLlmConnectionParameters,
  type ConnectionTestFeedback,
} from "./settingsAiModelsPresets";

export interface SettingsAiModelsSectionProps {
  readonly isFr: boolean;
  readonly llmTiers?: readonly ConfiguredLlmTierMapping[];
  readonly tierAndEffortLabels: InferenceTierAndEffortLabels;
  readonly openHelpSection?: (sectionId: string) => void;
  readonly upsertLlmTier?: (input: ConfiguredLlmTierMapping) => void;
  readonly allowedVerbs?: readonly UiPermissionVerb[];
}

export function SettingsAiModelsSection({
  isFr,
  llmTiers = [],
  tierAndEffortLabels,
  openHelpSection,
  upsertLlmTier,
  allowedVerbs = ["read", "create", "update", "delete", "execute", "grant"],
}: SettingsAiModelsSectionProps): React.ReactElement {
  const { dictionary } = useI18n();
  const hubLabels = dictionary?.aiModelsHub ?? (isFr ? AI_MODELS_HUB_FR : AI_MODELS_HUB_EN);

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

  // Quick form state for backward compatibility
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
    if (res.ok && Array.isArray(res.data)) {
      setServerMappings(res.data);
    }
  };

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const accessToken = useAuthSessionStore((s) => s.accessToken);

  useEffect(() => {
    if (isHydrating) {
      return;
    }
    void loadMappings();
  }, [isFr, isHydrating, accessToken]);

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
              ? {
                  ...m,
                  health_status: "ERROR",
                  last_tested_at: new Date().toISOString(),
                }
              : m,
          ),
        );
        setOperationError(res.errorMessage);
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
      void loadMappings();
    }
  };

  const handleOpenDelete = async (mapping: AiModelMappingItemResponse) => {
    setDeleteState({ open: true, mapping, impact: null, isLoadingImpact: true });
    const res = await fetchAiModelDeleteImpactViaApi(mapping.id, isFr ? "fr" : "en");
    if (res.ok) {
      setDeleteState((prev) => ({ ...prev, impact: res.data, isLoadingImpact: false }));
    } else {
      setDeleteState((prev) => ({ ...prev, isLoadingImpact: false }));
    }
  };

  const handleConfirmDelete = async (
    mappingId: string,
    mode: "reject" | "drain" | "force",
  ): Promise<boolean> => {
    const res = await deleteAiModelMappingViaApi(mappingId, mode, isFr ? "fr" : "en");
    if (res.ok) {
      void loadMappings();
      return true;
    }
    return false;
  };

  const handleSubmitCreate = async (
    payload: AiModelCreateRequest,
    andTest: boolean,
  ): Promise<boolean> => {
    const res = await createAiModelMappingViaApi(payload, isFr ? "fr" : "en");
    if (res.ok) {
      if (upsertLlmTier) {
        upsertLlmTier({
          tier: (payload.inference_tier ?? "medium") as UiInferenceTier,
          primaryModel: payload.model_name,
          secondaryModel: payload.fallback_model_name || payload.model_name,
          modelFamily: payload.model_family,
          defaultEffort: (payload.effort ?? "balanced") as UiInferenceEffort,
          endpointUrl: payload.endpoint_uri,
          authMode: (payload.auth_mode ?? "api_key") as LlmAuthMode,
          apiKeyConfigured: Boolean(
            payload.secret_input?.plaintext_value || payload.auth_mode !== "api_key",
          ),
        });
      }
      if (andTest) {
        const testRes = await testAiModelConnectionViaApi(res.data.id, isFr ? "fr" : "en");
        if (!testRes.ok) {
          setOperationError(testRes.errorMessage);
        } else {
          setOperationError(null);
        }
      } else {
        setOperationError(null);
      }
      void loadMappings();
      return true;
    }
    return false;
  };

  const handleSubmitPatch = async (
    mappingId: string,
    payload: AiModelPatchRequest,
  ): Promise<boolean> => {
    const res = await patchAiModelMappingViaApi(mappingId, payload, isFr ? "fr" : "en");
    if (res.ok) {
      void loadMappings();
      return true;
    }
    return false;
  };

  const evaluateConnectionTest = async () => {
    const params = {
      provider: modelFamily,
      model: primaryModel,
      uri: endpointUrl,
      mode: authMode,
      rawKey: apiKeyInput,
      keyAlreadyConfigured: false,
    };
    const syncErr = validateLlmConnectionParameters({ isFr, ...params });
    if (syncErr !== null) {
      setTestResult(syncErr);
      return;
    }
    setTestResult(await runRemoteLlmConnectionTestEvaluation({ isFr, ...params }));
  };

  const isGeminiActive = isGoogleGeminiFamily(modelFamily, endpointUrl);
  const geminiProtocolMode = detectGoogleGeminiProtocolMode(endpointUrl);

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
  };

  return (
    <section
      data-testid="settings-ai-models-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        {openHelpSection && (
          <ContextualInfoTriggerButton
            sectionId="ai-models-overview"
            label={
              isFr
                ? "Comprendre les informations attendues (Fournisseur, Modèle, URL API, Clé d'API et Test de connexion)"
                : "Understand expected AI model settings (Provider, Model, API URL, API Key, and Connection Test)"
            }
            onOpenHelpSection={openHelpSection}
          />
        )}
      </div>

      {operationError && (
        <div
          role="alert"
          data-testid="ai-model-operation-error"
          style={{
            padding: "10px 14px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-bg-elevated)",
            border: "1px solid var(--color-status-error)",
            color: "var(--color-status-error)",
            fontSize: "13px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{operationError}</span>
          <button
            type="button"
            onClick={() => setOperationError(null)}
            style={{
              background: "none",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontSize: "14px",
              padding: "0 4px",
            }}
            aria-label="Fermer l'erreur"
          >
            ✕
          </button>
        </div>
      )}

      <AiModelReindexPanel
        isFr={isFr}
        canExecute={allowedVerbs.includes("execute")}
      />

      <AiModelsMasterTable
        isFr={isFr}
        labels={hubLabels}
        tierLabels={tierAndEffortLabels}
        mappings={activeMappings}
        allowedVerbs={allowedVerbs}
        testingId={testingId}
        onOpenCreateModal={() =>
          setModalState({ open: true, mode: "create", mapping: null })
        }
        onOpenEditModal={(mapping) =>
          setModalState({ open: true, mode: "edit", mapping })
        }
        onOpenRotateKeyModal={(mapping) =>
          setModalState({ open: true, mode: "rotate-key", mapping })
        }
        onToggleActive={handleToggleActive}
        onOpenDeleteDialog={handleOpenDelete}
        onTestConnection={handleTestConnection}
      />

      <AiModelConfigModal
        open={modalState.open}
        onOpenChange={(open) => setModalState((prev) => ({ ...prev, open }))}
        mode={modalState.mode}
        initialMapping={modalState.mapping}
        labels={hubLabels}
        tierLabels={tierAndEffortLabels}
        isFr={isFr}
        onSubmitCreate={handleSubmitCreate}
        onSubmitPatch={handleSubmitPatch}
      />

      <AiModelDeleteDialog
        open={deleteState.open}
        onOpenChange={(open) => setDeleteState((prev) => ({ ...prev, open }))}
        mapping={deleteState.mapping}
        labels={hubLabels}
        impact={deleteState.impact}
        isLoadingImpact={deleteState.isLoadingImpact}
        onConfirmDelete={handleConfirmDelete}
      />

      <SettingsAiModelsQuickForm
        isFr={isFr}
        selectedTier={selectedTier}
        selectedEffort={selectedEffort}
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
        testResult={testResult}
        setTestResult={setTestResult}
        isGeminiActive={isGeminiActive}
        geminiProtocolMode={geminiProtocolMode}
        onQuickSubmit={handleQuickSubmit}
        onEvaluateTest={() => void evaluateConnectionTest()}
      />
    </section>
  );
}
