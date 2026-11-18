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
} from "@orcia/ui";
import React from "react";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";
import { AiModelFormFields } from "./AiModelFormFields";
import {
  type AiModelModalMode,
  useAiModelConfigModalState,
} from "./useAiModelConfigModalState";

export type { AiModelModalMode };

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

const SECRET_FIELD_LABELS: SecretFieldLabels = {
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

export function AiModelConfigModal({
  open,
  onOpenChange,
  mode,
  initialMapping,
  labels,
  tierLabels,
  onSubmitCreate,
  onSubmitPatch,
}: AiModelConfigModalProps): React.ReactElement {
  const s = useAiModelConfigModalState({
    open,
    onOpenChange,
    mode,
    initialMapping,
    labels,
    onSubmitCreate,
    onSubmitPatch,
  });

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
      <div className="orcia-ds-dialog-body" style={{ paddingTop: "4px" }}>
        {s.errorMessage && (
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
            {s.errorMessage}
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
              labels={SECRET_FIELD_LABELS}
              onSecretAction={s.handleSecretAction}
            />
          </div>
        ) : (
          <AiModelFormFields
            mode={mode}
            labels={labels}
            tierLabels={tierLabels}
            modelFamily={s.modelFamily}
            setModelFamily={s.setModelFamily}
            displayName={s.displayName}
            setDisplayName={s.setDisplayName}
            primaryModel={s.primaryModel}
            setPrimaryModel={s.setPrimaryModel}
            fallbackModel={s.fallbackModel}
            setFallbackModel={s.setFallbackModel}
            endpointUri={s.endpointUri}
            setEndpointUri={s.setEndpointUri}
            authMode={s.authMode}
            setAuthMode={s.setAuthMode}
            envVarName={s.envVarName}
            setEnvVarName={s.setEnvVarName}
            rawApiKey={s.rawApiKey}
            setRawApiKey={s.setRawApiKey}
            selectedTier={s.selectedTier}
            setSelectedTier={s.setSelectedTier}
            selectedEffort={s.selectedEffort}
            setSelectedEffort={s.setSelectedEffort}
            isGemini={s.isGemini}
            usage={s.usage}
            setUsage={s.setUsage}
            discoveredModels={s.discoveredModels}
            isDiscovering={s.isDiscovering}
            discoveryError={s.discoveryError}
            onRefreshDiscovery={() => void s.triggerDiscovery({ explicit: true })}
          />
        )}
      </div>

      <div className="orcia-ds-dialog-footer">
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
            disabled={s.isSubmitting}
            onClick={() => void s.handleFormSubmit(true)}
            className="orcia-ds-btn orcia-ds-btn-secondary"
          >
            {labels.saveAndTestBtn}
          </button>
        )}

        <button
          type="button"
          data-testid="save-ai-model-btn"
          disabled={s.isSubmitting}
          onClick={() => void s.handleFormSubmit(false)}
          className="orcia-ds-btn orcia-ds-btn-primary"
        >
          {mode === "create" ? labels.saveOnlyBtn : labels.updateBtn}
        </button>
      </div>
    </OrciaDialog>
  );
}
