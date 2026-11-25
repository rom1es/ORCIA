import {
  OrciaIcon,
  type InferenceTierAndEffortLabels,
  type UiPermissionVerb,
} from "@orcia/ui";
import React from "react";
import type { ConfiguredLlmTierMapping } from "../components/platformSetupStore";
import { AiModelConfigModal } from "../features/admin/ai-models/AiModelConfigModal";
import { AiModelDeleteDialog } from "../features/admin/ai-models/AiModelDeleteDialog";
import { AiModelReindexPanel } from "../features/admin/ai-models/AiModelReindexPanel";
import { AiModelsMasterTable } from "../features/admin/ai-models/AiModelsMasterTable";
import { resolveDictionaryForFlag, useI18n } from "../i18n";
import { SettingsAiModelsQuickForm } from "./SettingsAiModelsQuickForm";
import { useAiModelsSectionController } from "./useAiModelsSectionController";

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
  tierAndEffortLabels,
  allowedVerbs = ["read", "create", "update", "delete", "execute", "grant"],
}: SettingsAiModelsSectionProps): React.ReactElement {
  const { dictionary } = useI18n();
  const hubLabels = dictionary?.aiModelsHub ?? resolveDictionaryForFlag(isFr).aiModelsHub;
  const ctrl = useAiModelsSectionController({ isFr });
  const hasActiveEmbeddingModel = ctrl.activeMappings.some(
    (m) =>
      m.usage === "embedding" &&
      m.is_active &&
      !m.draining &&
      (m.scope_level ?? "GLOBAL") === "GLOBAL",
  );

  return (
    <section
      data-testid="settings-ai-models-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {ctrl.operationError && (
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
          <span>{ctrl.operationError}</span>
          <button
            type="button"
            onClick={() => ctrl.setOperationError(null)}
            style={{
              background: "none",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontSize: "14px",
              padding: "0 4px",
            }}
            aria-label={hubLabels.closeErrorLabel}
          >
            <OrciaIcon name="close" size={14} />
          </button>
        </div>
      )}

      <AiModelReindexPanel
        isFr={isFr}
        canExecute={allowedVerbs.includes("execute")}
        hasActiveEmbeddingModel={hasActiveEmbeddingModel}
        refreshSignal={ctrl.mappingsRevision}
      />

      <AiModelsMasterTable
        isFr={isFr}
        labels={hubLabels}
        tierLabels={tierAndEffortLabels}
        mappings={ctrl.activeMappings}
        allowedVerbs={allowedVerbs}
        testingId={ctrl.testingId}
        testErrorsByModelId={ctrl.testErrorsByModelId}
        onOpenCreateModal={() =>
          ctrl.setModalState({ open: true, mode: "create", mapping: null })
        }
        onOpenEditModal={(mapping) =>
          ctrl.setModalState({ open: true, mode: "edit", mapping })
        }
        onOpenRotateKeyModal={(mapping) =>
          ctrl.setModalState({ open: true, mode: "rotate-key", mapping })
        }
        onToggleActive={ctrl.handleToggleActive}
        onOpenDeleteDialog={ctrl.handleOpenDelete}
        onTestConnection={ctrl.handleTestConnection}
      />

      <AiModelConfigModal
        open={ctrl.modalState.open}
        onOpenChange={(open) => ctrl.setModalState((prev) => ({ ...prev, open }))}
        mode={ctrl.modalState.mode}
        initialMapping={ctrl.modalState.mapping}
        labels={hubLabels}
        tierLabels={tierAndEffortLabels}
        isFr={isFr}
        onSubmitCreate={ctrl.handleSubmitCreate}
        onSubmitPatch={ctrl.handleSubmitPatch}
      />

      <AiModelDeleteDialog
        open={ctrl.deleteState.open}
        onOpenChange={(open) => ctrl.setDeleteState((prev) => ({ ...prev, open }))}
        mapping={ctrl.deleteState.mapping}
        labels={hubLabels}
        impact={ctrl.deleteState.impact}
        isLoadingImpact={ctrl.deleteState.isLoadingImpact}
        onConfirmDelete={ctrl.handleConfirmDelete}
      />

      <SettingsAiModelsQuickForm
        isFr={isFr}
        selectedTier={ctrl.selectedTier}
        selectedEffort={ctrl.selectedEffort}
        modelFamily={ctrl.modelFamily}
        setModelFamily={ctrl.setModelFamily}
        primaryModel={ctrl.primaryModel}
        setPrimaryModel={ctrl.setPrimaryModel}
        secondaryModel={ctrl.secondaryModel}
        setSecondaryModel={ctrl.setSecondaryModel}
        endpointUrl={ctrl.endpointUrl}
        setEndpointUrl={ctrl.setEndpointUrl}
        authMode={ctrl.authMode}
        setAuthMode={ctrl.setAuthMode}
        apiKeyInput={ctrl.apiKeyInput}
        setApiKeyInput={ctrl.setApiKeyInput}
        testResult={ctrl.testResult}
        setTestResult={ctrl.setTestResult}
        isGeminiActive={ctrl.isGeminiActive}
        geminiProtocolMode={ctrl.geminiProtocolMode}
        onQuickSubmit={ctrl.handleQuickSubmit}
        onEvaluateTest={() => void ctrl.evaluateConnectionTest()}
      />
    </section>
  );
}
