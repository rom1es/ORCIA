import { OrciaDialog } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type {
  CreateWorkspaceDatasourceRequest,
  EnterpriseConnectorItemResponse,
  UpdateWorkspaceDatasourceRequest,
  WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import { useI18n } from "../../../i18n";
import { formatRfc9457ErrorToBanner } from "../../../lib/formatRfc9457ErrorToBanner";
import {
  FormInput,
  modalInputStyle,
  WorkspaceSourceAttachCodegraphFields,
} from "./WorkspaceSourceAttachCodegraphFields";
import { WorkspaceSourceAttachSyncFields } from "./WorkspaceSourceAttachSyncFields";

export interface WorkspaceSourceAttachModalProps {
  readonly isOpen: boolean;
  readonly editingDatasource: WorkspaceDatasourceItemResponse | null;
  readonly connectors: readonly EnterpriseConnectorItemResponse[];
  readonly isWorkspaceLead: boolean;
  readonly hasActiveEmbeddingModel?: boolean;
  readonly onNavigateToAiModels?: () => void;
  readonly onClose: () => void;
  readonly onSubmit: (
    payload: CreateWorkspaceDatasourceRequest | UpdateWorkspaceDatasourceRequest,
    isEdit: boolean,
  ) => Promise<void>;
}

const DEFAULT_FORM = {
  alias: "",
  scheme: "git",
  uri: "",
  nature: "DOCUMENT_KB" as "DOCUMENT_KB" | "WORK_TRACKER" | "SOURCE_CODE" | "RELATIONAL_SCHEMA",
  connectorId: "",
  targetScope: "",
  targetRef: "",
  syncMode: "POLLING_24H" as "POLLING_24H" | "WEBHOOK_PUSH",
  syncIdentityMode: "SERVICE_ACCOUNT" as "SERVICE_ACCOUNT" | "TEAM_REFERENT_USER",
  serviceAccountId: "",
  referentUserId: "",
  cgEnabled: false,
  cgAuthMode: "SERVICE_ACCOUNT" as "SERVICE_ACCOUNT" | "WORKSPACE_LEAD_TOKEN",
  cgOwnerUserId: "",
};

export function WorkspaceSourceAttachModal({
  isOpen,
  editingDatasource,
  connectors,
  isWorkspaceLead,
  hasActiveEmbeddingModel = true,
  onNavigateToAiModels,
  onClose,
  onSubmit,
}: WorkspaceSourceAttachModalProps): React.ReactElement {
  const { dictionary, locale } = useI18n();
  const copy = dictionary.epic18Sources.modal;

  const [form, setForm] = useState(DEFAULT_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const updateField = <K extends keyof typeof DEFAULT_FORM>(
    key: K,
    value: (typeof DEFAULT_FORM)[K],
  ) => {
    setSubmitError(null);
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    setSubmitError(null);
    if (editingDatasource) {
      setForm({
        alias: editingDatasource.alias,
        scheme: editingDatasource.scheme,
        uri: editingDatasource.uri,
        nature: editingDatasource.source_nature || "DOCUMENT_KB",
        connectorId: editingDatasource.connector_id || "",
        targetScope: editingDatasource.target_scope || "",
        targetRef: editingDatasource.target_ref || "",
        syncMode: editingDatasource.sync_mode || "POLLING_24H",
        syncIdentityMode: editingDatasource.sync_identity_mode || "SERVICE_ACCOUNT",
        serviceAccountId: editingDatasource.service_account_id || "",
        referentUserId: editingDatasource.referent_user_id || "",
        cgEnabled: Boolean(editingDatasource.codegraph_enabled),
        cgAuthMode: editingDatasource.codegraph_auth_mode || "SERVICE_ACCOUNT",
        cgOwnerUserId: editingDatasource.codegraph_owner_user_id || "",
      });
    } else if (!hasActiveEmbeddingModel) {
      setForm({
        ...DEFAULT_FORM,
        nature: "SOURCE_CODE",
        scheme: "git",
        cgEnabled: false,
      });
    } else {
      setForm(DEFAULT_FORM);
    }
  }, [editingDatasource, isOpen, hasActiveEmbeddingModel]);

  const handleNatureChange = (newNature: typeof DEFAULT_FORM.nature) => {
    const schemeMap: Record<string, string> = {
      SOURCE_CODE: "git",
      WORK_TRACKER: "jira",
      RELATIONAL_SCHEMA: "sql",
      DOCUMENT_KB: "confluence",
    };
    setForm((prev) => ({
      ...prev,
      nature: newNature,
      ...(!editingDatasource
        ? {
            scheme: schemeMap[newNature] || "git",
            cgEnabled: newNature === "SOURCE_CODE",
          }
        : {}),
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.alias.trim() || !form.uri.trim()) return;

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const payload: CreateWorkspaceDatasourceRequest = {
        alias: form.alias.trim(),
        scheme: form.scheme.trim().toLowerCase(),
        uri: form.uri.trim(),
        source_nature: form.nature,
        connector_id: form.connectorId.trim() || null,
        target_scope: form.targetScope.trim() || null,
        target_ref: form.targetRef.trim() || null,
        sync_mode: form.syncMode,
        sync_identity_mode: form.syncIdentityMode,
        service_account_id: form.serviceAccountId.trim() || null,
        referent_user_id: form.referentUserId.trim() || null,
        codegraph_enabled: form.nature === "SOURCE_CODE" ? form.cgEnabled : false,
        codegraph_auth_mode: form.cgAuthMode,
        codegraph_owner_user_id: form.cgOwnerUserId.trim() || null,
      };
      await onSubmit(payload, Boolean(editingDatasource));
      onClose();
    } catch (err: unknown) {
      setSubmitError(formatRfc9457ErrorToBanner(err, locale).fullText);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <OrciaDialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={editingDatasource ? copy.editTitle : copy.createTitle}
      description={copy.description}
      testId="workspace-source-attach-modal"
      hideHeaderCloseButton
    >
      <form
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        onSubmit={handleSave}
        style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "8px" }}
      >
        {!hasActiveEmbeddingModel ? (
          <div
            role="status"
            data-testid="datasource-rag-embedding-required-notice"
            className="rounded-lg border border-status-warning/40 bg-status-warning/10 p-2.5 text-xs text-text-primary"
            style={{ display: "flex", flexDirection: "column", gap: "4px" }}
          >
            <strong className="text-status-warning">⚠️ {copy.ragEmbeddingRequiredTitle}</strong>
            <span className="text-text-secondary">{copy.ragEmbeddingRequiredDescription}</span>
            {onNavigateToAiModels ? (
              <a
                href="/settings/ai-models"
                data-testid="datasource-configure-embedding-link"
                onClick={(e) => {
                  e.preventDefault();
                  onClose();
                  onNavigateToAiModels();
                }}
                className="font-medium text-action-primary underline hover:opacity-80"
              >
                {copy.ragEmbeddingRequiredCta}
              </a>
            ) : null}
          </div>
        ) : null}

        {submitError ? (
          <div
            role="alert"
            data-testid="modal-source-error-alert"
            className="rounded-lg border border-status-danger/40 bg-status-danger/10 p-2.5 text-xs text-status-danger"
          >
            {submitError}
          </div>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.natureLabel}</label>
            <select
              data-testid="modal-source-nature-select"
              value={form.nature}
              onChange={(e) => handleNatureChange(e.target.value as typeof form.nature)}
              style={modalInputStyle}
            >
              <option value="DOCUMENT_KB" disabled={!hasActiveEmbeddingModel}>
                {copy.natureDoc}
                {!hasActiveEmbeddingModel ? copy.ragOptionDisabledSuffix : ""}
              </option>
              <option value="WORK_TRACKER" disabled={!hasActiveEmbeddingModel}>
                {copy.natureTracker}
                {!hasActiveEmbeddingModel ? copy.ragOptionDisabledSuffix : ""}
              </option>
              <option value="SOURCE_CODE">{copy.natureCode}</option>
              <option value="RELATIONAL_SCHEMA" disabled={!hasActiveEmbeddingModel}>
                {copy.natureSchema}
                {!hasActiveEmbeddingModel ? copy.ragOptionDisabledSuffix : ""}
              </option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.connectorLabel}</label>
            <select
              data-testid="modal-connector-select"
              value={form.connectorId}
              onChange={(e) => updateField("connectorId", e.target.value)}
              style={modalInputStyle}
            >
              <option value="">{copy.connectorNone}</option>
              {connectors.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.connector_kind})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.aliasLabel} *</label>
            <FormInput
              testId="modal-source-alias-input"
              type="text"
              required
              placeholder={copy.aliasPlaceholder}
              value={form.alias}
              onChange={(e) => updateField("alias", e.target.value)}
            />
          </div>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>
              {copy.schemeLabel}
            </label>
            <FormInput
              testId="modal-source-scheme-input"
              type="text"
              required
              value={form.scheme}
              onChange={(e) => updateField("scheme", e.target.value)}
            />
          </div>
        </div>

        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.uriLabel} *</label>
          <FormInput
            testId="modal-source-uri-input"
            type="text"
            required
            placeholder={copy.uriPlaceholder}
            value={form.uri}
            onChange={(e) => updateField("uri", e.target.value)}
          />
        </div>

        <WorkspaceSourceAttachSyncFields
          targetScope={form.targetScope}
          targetRef={form.targetRef}
          syncMode={form.syncMode}
          syncIdentityMode={form.syncIdentityMode}
          referentUserId={form.referentUserId}
          serviceAccountId={form.serviceAccountId}
          copy={copy}
          onTargetScopeChange={(val) => updateField("targetScope", val)}
          onTargetRefChange={(val) => updateField("targetRef", val)}
          onSyncModeChange={(val) => updateField("syncMode", val)}
          onSyncIdentityModeChange={(val) => updateField("syncIdentityMode", val)}
          onReferentUserIdChange={(val) => updateField("referentUserId", val)}
          onServiceAccountIdChange={(val) => updateField("serviceAccountId", val)}
        />

        {/* Section GitNexus réservée à SOURCE_CODE */}
        {form.nature === "SOURCE_CODE" ? (
          <WorkspaceSourceAttachCodegraphFields
            cgEnabled={form.cgEnabled}
            cgAuthMode={form.cgAuthMode}
            cgOwnerUserId={form.cgOwnerUserId}
            isWorkspaceLead={isWorkspaceLead}
            copy={copy}
            onCgEnabledChange={(val) => updateField("cgEnabled", val)}
            onCgAuthModeChange={(val) => updateField("cgAuthMode", val)}
            onCgOwnerUserIdChange={(val) => updateField("cgOwnerUserId", val)}
          />
        ) : null}

        <div
          style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "6px" }}
        >
          <button
            type="button"
            data-testid="modal-source-cancel-btn"
            className="orcia-ds-btn orcia-ds-btn-secondary"
            onClick={onClose}
          >
            {copy.cancelBtn}
          </button>
          <button
            type="submit"
            data-testid="modal-source-save-btn"
            disabled={
              isSubmitting ||
              !form.alias.trim() ||
              !form.uri.trim() ||
              (!hasActiveEmbeddingModel && form.nature !== "SOURCE_CODE")
            }
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {editingDatasource ? copy.updateBtn : copy.attachBtn}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}
