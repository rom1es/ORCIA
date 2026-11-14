import { OrciaDialog, OrciaSwitch } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type {
  CreateWorkspaceDatasourceRequest,
  EnterpriseConnectorItemResponse,
  UpdateWorkspaceDatasourceRequest,
  WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import { useI18n } from "../../../i18n";

export interface WorkspaceSourceAttachModalProps {
  readonly isOpen: boolean;
  readonly editingDatasource: WorkspaceDatasourceItemResponse | null;
  readonly connectors: readonly EnterpriseConnectorItemResponse[];
  readonly isWorkspaceLead: boolean;
  readonly onClose: () => void;
  readonly onSubmit: (
    payload: CreateWorkspaceDatasourceRequest | UpdateWorkspaceDatasourceRequest,
    isEdit: boolean,
  ) => Promise<void>;
}

const inputStyle: React.CSSProperties = {
  padding: "6px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "12px",
  width: "100%",
  boxSizing: "border-box",
};

export function WorkspaceSourceAttachModal({
  isOpen,
  editingDatasource,
  connectors,
  isWorkspaceLead,
  onClose,
  onSubmit,
}: WorkspaceSourceAttachModalProps): React.ReactElement {
  const { dictionary } = useI18n();
  const copy = dictionary.epic18Sources.modal;

  const [alias, setAlias] = useState("");
  const [scheme, setScheme] = useState("git");
  const [uri, setUri] = useState("");
  const [nature, setNature] = useState<"DOCUMENT_KB" | "WORK_TRACKER" | "SOURCE_CODE" | "RELATIONAL_SCHEMA">("DOCUMENT_KB");
  const [connectorId, setConnectorId] = useState("");
  const [targetScope, setTargetScope] = useState("");
  const [targetRef, setTargetRef] = useState("");
  const [syncMode, setSyncMode] = useState<"POLLING_24H" | "WEBHOOK_PUSH">("POLLING_24H");
  const [syncIdentityMode, setSyncIdentityMode] = useState<"SERVICE_ACCOUNT" | "TEAM_REFERENT_USER">("SERVICE_ACCOUNT");
  const [serviceAccountId, setServiceAccountId] = useState("");
  const [referentUserId, setReferentUserId] = useState("");
  const [cgEnabled, setCgEnabled] = useState(false);
  const [cgAuthMode, setCgAuthMode] = useState<"SERVICE_ACCOUNT" | "WORKSPACE_LEAD_TOKEN">("SERVICE_ACCOUNT");
  const [cgOwnerUserId, setCgOwnerUserId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (editingDatasource) {
      setAlias(editingDatasource.alias);
      setScheme(editingDatasource.scheme);
      setUri(editingDatasource.uri);
      setNature(editingDatasource.source_nature || "DOCUMENT_KB");
      setConnectorId(editingDatasource.connector_id || "");
      setTargetScope(editingDatasource.target_scope || "");
      setTargetRef(editingDatasource.target_ref || "");
      setSyncMode(editingDatasource.sync_mode || "POLLING_24H");
      setSyncIdentityMode(editingDatasource.sync_identity_mode || "SERVICE_ACCOUNT");
      setServiceAccountId(editingDatasource.service_account_id || "");
      setReferentUserId(editingDatasource.referent_user_id || "");
      setCgEnabled(Boolean(editingDatasource.codegraph_enabled));
      setCgAuthMode(editingDatasource.codegraph_auth_mode || "SERVICE_ACCOUNT");
      setCgOwnerUserId(editingDatasource.codegraph_owner_user_id || "");
    } else {
      setAlias("");
      setScheme("git");
      setUri("");
      setNature("DOCUMENT_KB");
      setConnectorId("");
      setTargetScope("");
      setTargetRef("");
      setSyncMode("POLLING_24H");
      setSyncIdentityMode("SERVICE_ACCOUNT");
      setServiceAccountId("");
      setReferentUserId("");
      setCgEnabled(false);
      setCgAuthMode("SERVICE_ACCOUNT");
      setCgOwnerUserId("");
    }
  }, [editingDatasource, isOpen]);

  const handleNatureChange = (newNature: typeof nature) => {
    setNature(newNature);
    if (!editingDatasource) {
      if (newNature === "SOURCE_CODE") {
        setScheme("git");
        setCgEnabled(true);
      } else if (newNature === "WORK_TRACKER") {
        setScheme("jira");
        setCgEnabled(false);
      } else if (newNature === "RELATIONAL_SCHEMA") {
        setScheme("sql");
        setCgEnabled(false);
      } else {
        setScheme("confluence");
        setCgEnabled(false);
      }
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!alias.trim() || !uri.trim()) return;

    setIsSubmitting(true);
    try {
      const payload: CreateWorkspaceDatasourceRequest = {
        alias: alias.trim(),
        scheme: scheme.trim().toLowerCase(),
        uri: uri.trim(),
        source_nature: nature,
        connector_id: connectorId.trim() || null,
        target_scope: targetScope.trim() || null,
        target_ref: targetRef.trim() || null,
        sync_mode: syncMode,
        sync_identity_mode: syncIdentityMode,
        service_account_id: serviceAccountId.trim() || null,
        referent_user_id: referentUserId.trim() || null,
        codegraph_enabled: nature === "SOURCE_CODE" ? cgEnabled : false,
        codegraph_auth_mode: cgAuthMode,
        codegraph_owner_user_id: cgOwnerUserId.trim() || null,
      };
      await onSubmit(payload, Boolean(editingDatasource));
      onClose();
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
    >
      <form
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        onSubmit={handleSave}
        style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "8px" }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.natureLabel}</label>
            <select
              data-testid="modal-source-nature-select"
              value={nature}
              onChange={(e) => handleNatureChange(e.target.value as typeof nature)}
              style={inputStyle}
            >
              <option value="DOCUMENT_KB">{copy.natureDoc}</option>
              <option value="WORK_TRACKER">{copy.natureTracker}</option>
              <option value="SOURCE_CODE">{copy.natureCode}</option>
              <option value="RELATIONAL_SCHEMA">{copy.natureSchema}</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.connectorLabel}</label>
            <select
              data-testid="modal-connector-select"
              value={connectorId}
              onChange={(e) => setConnectorId(e.target.value)}
              style={inputStyle}
            >
              <option value="">{copy.connectorNone}</option>
              {connectors.map((c) => (
                <option key={c.id} value={c.id}>{c.name} ({c.connector_kind})</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.aliasLabel} *</label>
            <input
              data-testid="modal-source-alias-input"
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              required
              placeholder={copy.aliasPlaceholder}
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>Schéma (git, jira, confluence, sql)</label>
            <input
              data-testid="modal-source-scheme-input"
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              required
              value={scheme}
              onChange={(e) => setScheme(e.target.value)}
              style={inputStyle}
            />
          </div>
        </div>

        <div>
          <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.uriLabel} *</label>
          <input
            data-testid="modal-source-uri-input"
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            required
            placeholder={copy.uriPlaceholder}
            value={uri}
            onChange={(e) => setUri(e.target.value)}
            style={inputStyle}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.targetScopeLabel}</label>
            <input
              data-testid="modal-source-target-scope-input"
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              value={targetScope}
              onChange={(e) => setTargetScope(e.target.value)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.targetRefLabel}</label>
            <input
              data-testid="modal-source-target-ref-input"
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              value={targetRef}
              onChange={(e) => setTargetRef(e.target.value)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.syncModeLabel}</label>
            <select
              data-testid="modal-source-sync-mode-select"
              value={syncMode}
              onChange={(e) => setSyncMode(e.target.value as typeof syncMode)}
              style={inputStyle}
            >
              <option value="POLLING_24H">Sonde 24h</option>
              <option value="WEBHOOK_PUSH">Webhook push</option>
            </select>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.ragIdentityLabel}</label>
            <select
              data-testid="modal-source-rag-identity-select"
              value={syncIdentityMode}
              onChange={(e) => setSyncIdentityMode(e.target.value as typeof syncIdentityMode)}
              style={inputStyle}
            >
              <option value="SERVICE_ACCOUNT">{copy.ragServiceAccount}</option>
              <option value="TEAM_REFERENT_USER">{copy.ragReferentUser}</option>
            </select>
          </div>
          <div>
            {syncIdentityMode === "TEAM_REFERENT_USER" ? (
              <>
                <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.referentUserIdLabel}</label>
                <input
                  data-testid="modal-source-referent-user-input"
                  type="text"
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  value={referentUserId}
                  onChange={(e) => setReferentUserId(e.target.value)}
                  style={inputStyle}
                />
              </>
            ) : (
              <>
                <label style={{ fontSize: "11px", fontWeight: 600 }}>{copy.serviceAccountIdLabel}</label>
                <input
                  data-testid="modal-source-service-account-input"
                  type="text"
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  value={serviceAccountId}
                  onChange={(e) => setServiceAccountId(e.target.value)}
                  style={inputStyle}
                />
              </>
            )}
          </div>
        </div>

        {/* Section GitNexus réservée à SOURCE_CODE */}
        {nature === "SOURCE_CODE" ? (
          <div
            data-testid="modal-gitnexus-section"
            style={{
              padding: "10px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border-subtle)",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "12px", fontWeight: 600 }}>{copy.gitnexusSectionTitle}</span>
              <OrciaSwitch
                checked={cgEnabled}
                disabled={!isWorkspaceLead}
                ariaLabel={copy.gitnexusEnableLabel}
                testId="modal-gitnexus-enabled-switch"
                onCheckedChange={setCgEnabled}
              />
            </div>
            {cgEnabled ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                <div>
                  <label style={{ fontSize: "11px" }}>{copy.gitnexusAuthModeLabel}</label>
                  <select
                    data-testid="modal-gitnexus-auth-mode-select"
                    value={cgAuthMode}
                    disabled={!isWorkspaceLead}
                    onChange={(e) => setCgAuthMode(e.target.value as typeof cgAuthMode)}
                    style={inputStyle}
                  >
                    <option value="SERVICE_ACCOUNT">{copy.ragServiceAccount}</option>
                    <option value="WORKSPACE_LEAD_TOKEN">{copy.gitnexusOwnerUserLabel}</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "11px" }}>{copy.gitnexusOwnerUserLabel}</label>
                  <input
                    data-testid="modal-gitnexus-owner-user-input"
                    type="text"
                    autoComplete="off"
                    data-lpignore="true"
                    data-1p-ignore="true"
                    data-bwignore="true"
                    data-form-type="other"
                    disabled={!isWorkspaceLead}
                    value={cgOwnerUserId}
                    onChange={(e) => setCgOwnerUserId(e.target.value)}
                    style={inputStyle}
                  />
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "6px" }}>
          <button
            type="button"
            data-testid="modal-source-cancel-btn"
            className="orcia-ds-btn orcia-ds-btn-secondary"
            onClick={onClose}
          >
            Annuler
          </button>
          <button
            type="submit"
            data-testid="modal-source-save-btn"
            disabled={isSubmitting || !alias.trim() || !uri.trim()}
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {editingDatasource ? "Mettre à jour" : "Rattacher la source"}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}
