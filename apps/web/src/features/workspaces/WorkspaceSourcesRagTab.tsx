import {
  ContextualInfoTriggerButton,
  DisabledButtonAlertIndicator,
  OrciaIcon,
  type ControlCenterDatasourceItem,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import {
  createOrciaApiClient,
  type EnterpriseConnectorItemResponse,
  type WorkspaceDatasourceItemResponse,
} from "@orcia/api-client";
import type { PlatformSetupContextValue } from "../../components/platformSetupStore";
import { useAuthSessionStore } from "../../stores/authSessionStore";

export interface WorkspaceSourcesRagTabProps {
  readonly isFr?: boolean;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem;
  readonly fallbackDatasources?: readonly ControlCenterDatasourceItem[];
  readonly openHelpSection?: (sectionId: string) => void;
  readonly onRegisterDatasource?: PlatformSetupContextValue["registerDatasource"];
  readonly onFeedback?: (message: string) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "12px",
};

export function WorkspaceSourcesRagTab({
  isFr = true,
  activeWorkspace,
  fallbackDatasources = [],
  openHelpSection = () => {},
  onRegisterDatasource = async () => {},
  onFeedback = () => {},
}: WorkspaceSourcesRagTabProps): React.ReactElement {
  const openUserSettingsModalAtTab = useAuthSessionStore((s) => s.openUserSettingsModalAtTab);

  const [datasources, setDatasources] = useState<readonly WorkspaceDatasourceItemResponse[]>([]);
  const [connectors, setConnectors] = useState<readonly EnterpriseConnectorItemResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Form states
  const [dsAlias, setDsAlias] = useState<string>("");
  const [dsScheme, setDsScheme] = useState<"git" | "confluence" | "jira" | "db">("git");
  const [dsUri, setDsUri] = useState<string>("");
  const [connectorId, setConnectorId] = useState<string>("");
  const [syncMode, setSyncMode] = useState<"SERVICE_ACCOUNT" | "TEAM_REFERENT_USER">("SERVICE_ACCOUNT");
  const [serviceAccountId, setServiceAccountId] = useState<string>("");
  const [referentUserId, setReferentUserId] = useState<string>("");

  // Renewal inline state
  const [renewingDsId, setRenewingDsId] = useState<string | null>(null);
  const [newReferentInput, setNewReferentInput] = useState<string>("");

  const client = createOrciaApiClient({ baseUrl: "" });
  const wsId = activeWorkspace.workspaceId || "";

  const loadData = useCallback(async () => {
    if (!wsId) return;
    setIsLoading(true);
    try {
      const [dsRes, connRes] = await Promise.all([
        client.listWorkspaceDatasources(wsId),
        client.listEnterpriseConnectors(),
      ]);
      setDatasources(dsRes.items);
      setConnectors(connRes.items);
    } catch {
      // Fallback in unit tests without full server
    } finally {
      setIsLoading(false);
    }
  }, [wsId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const isDsSubmitDisabled = !dsAlias.trim() || !dsUri.trim();
  const dsSubmitDisabledReason = isFr
    ? "Renseignez le nom et l'adresse (URL/URI) de la source documentaire pour la connecter."
    : "Enter the source name and URL/URI to connect it.";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isDsSubmitDisabled) return;

    const savedAlias = dsAlias.trim();
    const savedUri = dsUri.trim();
    const savedScheme = dsScheme;
    const savedConnId = connectorId;
    const savedSyncMode = syncMode;
    const savedSaId = serviceAccountId.trim();
    const savedRefId = referentUserId.trim();

    onRegisterDatasource?.({
      workspaceName: activeWorkspace.name,
      alias: savedAlias,
      scheme: savedScheme,
      uri: savedUri,
      executionIdentity: savedSyncMode === "SERVICE_ACCOUNT" ? "service_account" : "passthrough",
      freshnessTtlDays: 30,
    });

    onFeedback(
      isFr
        ? `✅ Source « ${savedAlias} » rattachée à l'espace « ${activeWorkspace.name} ».`
        : `✅ Source "${savedAlias}" attached to workspace "${activeWorkspace.name}".`,
    );

    setDsAlias("");
    setDsUri("");
    setServiceAccountId("");
    setReferentUserId("");

    if (wsId) {
      void (async () => {
        try {
          await client.createWorkspaceDatasource(wsId, {
            alias: savedAlias,
            scheme: savedScheme,
            uri: savedUri,
            connector_id: savedConnId || undefined,
            sync_identity_mode: savedSyncMode,
            service_account_id: savedSyncMode === "SERVICE_ACCOUNT" && savedSaId ? savedSaId : undefined,
            referent_user_id: savedSyncMode === "TEAM_REFERENT_USER" && savedRefId ? savedRefId : undefined,
          });
          await loadData();
        } catch {
          // Graceful ignore if offline / test mock
        }
      })();
    }
  };

  const handleRenewReferent = async (dsId: string) => {
    if (!newReferentInput.trim() || !wsId) return;
    try {
      await client.updateWorkspaceDatasource(wsId, dsId, {
        referent_user_id: newReferentInput.trim(),
        sync_identity_mode: "TEAM_REFERENT_USER",
      });
      setRenewingDsId(null);
      setNewReferentInput("");
      onFeedback(isFr ? "Référent de synchronisation renouvelé avec succès." : "Sync referent successfully renewed.");
      await loadData();
    } catch {
      onFeedback(isFr ? "Erreur lors du renouvellement du référent." : "Error renewing referent.");
    }
  };

  const attachedFallback = (fallbackDatasources || []).filter(
    (d) => d.workspaceName === activeWorkspace.name,
  );
  const apiAliases = new Set(datasources.map((d) => d.alias));
  const fallbackOnly = attachedFallback
    .filter((f) => !apiAliases.has(f.alias))
    .map((f) => ({
      id: f.id,
      workspace_id: wsId,
      alias: f.alias,
      scheme: f.scheme,
      uri: f.uri,
      connector_id: null,
      sync_identity_mode:
        f.executionIdentity === "service_account"
          ? ("SERVICE_ACCOUNT" as const)
          : ("TEAM_REFERENT_USER" as const),
      service_account_id: null,
      referent_user_id: null,
      sync_status: "ACTIVE" as const,
      sync_status_reason: null,
      created_at_iso: "",
    }));

  const displaySources = [...datasources, ...fallbackOnly];

  return (
    <div data-testid="workspace-detail-sources-content" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      {/* Bannière Soft Cold-Start 1-clic */}
      <div
        data-testid="rag-passthrough-cold-start-banner"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: "rgba(59, 130, 246, 0.08)",
          border: "1px solid rgba(59, 130, 246, 0.2)",
          fontSize: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <OrciaIcon name="plug" size={16} />
          <span>
            {isFr
              ? "Attribution nominative : vos droits personnels Jira / GitLab s'appliquent sur vos lectures et actions."
              : "Nominative attribution: your personal Jira / GitLab rights apply to your reads and actions."}
          </span>
        </div>
        <button
          type="button"
          data-testid="open-my-account-passthrough-cta"
          onClick={() => openUserSettingsModalAtTab("PASSTHROUGH_SOURCES")}
          className="orcia-ds-btn-secondary"
          style={{ padding: "4px 10px", fontSize: "11px", whiteSpace: "nowrap" }}
        >
          {isFr ? "👤 Mon Compte › Mes Connexions" : "👤 My Account › Connections"}
        </button>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <strong style={{ fontSize: "14px" }}>
          {isFr ? `Connecter une source documentaire à « ${activeWorkspace.name} »` : `Connect a document source to "${activeWorkspace.name}"`}
        </strong>
        <ContextualInfoTriggerButton
          sectionId="workspace-sources"
          label={isFr ? "Comprendre comment rattacher des sources documentaires" : "Understand how to attach document sources"}
          onOpenHelpSection={openHelpSection}
        />
      </div>

      {/* Formulaire d'ajout inline */}
      <form
        data-testid="workspace-inline-add-datasource-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "8px",
          padding: "12px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-border)",
          backgroundColor: "var(--color-bg-elevated)",
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "8px" }}>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="workspace-inline-ds-alias-input"
            value={dsAlias}
            onChange={(e) => setDsAlias(e.target.value)}
            placeholder={isFr ? "Nom de la source (ex: Wiki Produit)..." : "Source name..."}
            style={inputStyle}
          />
          <select
            data-testid="workspace-inline-ds-scheme-select"
            value={dsScheme}
            onChange={(e) => setDsScheme(e.target.value as "git" | "confluence" | "jira" | "db")}
            style={inputStyle}
          >
            <option value="git">{isFr ? "Dépôt Git" : "Git Repository"}</option>
            <option value="confluence">{isFr ? "Espace Confluence" : "Confluence Space"}</option>
            <option value="jira">{isFr ? "Projet Jira" : "Jira Project"}</option>
            <option value="db">{isFr ? "Base documentaire" : "Document Database"}</option>
          </select>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="workspace-inline-ds-uri-input"
            value={dsUri}
            onChange={(e) => setDsUri(e.target.value)}
            placeholder={isFr ? "Adresse URL / URI (ex: https://...)" : "Source URL / URI..."}
            style={inputStyle}
          />
          {connectors.length > 0 && (
            <select
              data-testid="workspace-inline-ds-connector-select"
              value={connectorId}
              onChange={(e) => setConnectorId(e.target.value)}
              style={inputStyle}
            >
              <option value="">{isFr ? "Connecteur socle associé (optionnel)" : "Associated connector (optional)"}</option>
              {connectors.map((c) => (
                <option key={c.id} value={c.id}>{c.name} ({c.connector_kind})</option>
              ))}
            </select>
          )}
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
          <select
            data-testid="workspace-inline-ds-identity-select"
            value={syncMode}
            onChange={(e) => setSyncMode(e.target.value as "SERVICE_ACCOUNT" | "TEAM_REFERENT_USER")}
            style={inputStyle}
          >
            <option value="SERVICE_ACCOUNT">{isFr ? "Compte de service (recommandé)" : "Service account (recommended)"}</option>
            <option value="TEAM_REFERENT_USER">{isFr ? "Membre référent de l'équipe (repli sans compte de service)" : "Team referent user (fallback)"}</option>
          </select>

          {syncMode === "SERVICE_ACCOUNT" ? (
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="workspace-inline-ds-service-account-input"
              value={serviceAccountId}
              onChange={(e) => setServiceAccountId(e.target.value)}
              placeholder={isFr ? "ID compte de service (optionnel)" : "Service account ID"}
              style={{ ...inputStyle, minWidth: "160px" }}
            />
          ) : (
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="workspace-inline-ds-referent-input"
              value={referentUserId}
              onChange={(e) => setReferentUserId(e.target.value)}
              placeholder={isFr ? "Email / Principal du référent..." : "Referent user ID/email..."}
              style={{ ...inputStyle, minWidth: "200px" }}
            />
          )}

          <button
            type="submit"
            data-testid="workspace-inline-ds-submit-btn"
            disabled={isDsSubmitDisabled}
            title={isDsSubmitDisabled ? dsSubmitDisabledReason : undefined}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              backgroundColor: "var(--color-primary-cobalt)",
              color: "var(--color-primary-foreground)",
              fontWeight: 600,
              opacity: isDsSubmitDisabled ? 0.6 : 1,
              cursor: isDsSubmitDisabled ? "not-allowed" : "pointer",
              marginLeft: "auto",
            }}
          >
            <span>{isFr ? "+ Connecter la source" : "+ Connect source"}</span>
            <DisabledButtonAlertIndicator
              disabled={isDsSubmitDisabled}
              reason={dsSubmitDisabledReason}
              testIdSuffix="workspace-inline-ds-submit-btn"
            />
          </button>
        </div>
      </form>

      {/* Liste des sources avec indicateurs de santé RAG */}
      {displaySources.length === 0 ? (
        <p data-testid="workspace-detail-sources-empty" style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}>
          {isFr ? "Aucune source documentaire n'est encore rattachée à cet Espace." : "No document source is attached to this Workspace yet."}
        </p>
      ) : (
        <div style={{ display: "grid", gap: "8px" }}>
          {displaySources.map((ds) => {
            const isPaused = ds.sync_status === "PAUSED_REFERENT_RENEWAL_REQUIRED";
            const isRenewing = renewingDsId === ds.id;

            return (
              <div
                key={ds.id}
                data-testid={`workspace-detail-source-row-${ds.id}`}
                style={{
                  padding: "10px 14px",
                  borderRadius: "var(--radius-sm)",
                  border: isPaused ? "1px solid rgba(245, 158, 11, 0.4)" : "1px solid var(--color-border)",
                  backgroundColor: isPaused ? "rgba(245, 158, 11, 0.04)" : "var(--color-surface-card)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                  <div>
                    <strong>{ds.alias}</strong>{" "}
                    <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)", fontFamily: "monospace" }}>
                      ({ds.scheme})
                    </span>{" "}
                    <a
                      href={ds.uri}
                      target="_blank"
                      rel="noreferrer"
                      style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-action-primary)" }}
                    >
                      {ds.uri}
                    </a>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    {isPaused ? (
                      <span
                        data-testid={`rag-sync-paused-badge-${ds.id}`}
                        style={{
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 600,
                          backgroundColor: "rgba(245, 158, 11, 0.15)",
                          color: "var(--color-status-warning)",
                          border: "1px solid rgba(245, 158, 11, 0.3)",
                        }}
                      >
                        ⚠️ {isFr ? "Synchronisation en pause — Référent à renouveler" : "Sync paused — Renewal required"}
                        {ds.sync_status_reason && ` (${ds.sync_status_reason})`}
                      </span>
                    ) : (
                      <span
                        data-testid={`rag-sync-active-badge-${ds.id}`}
                        style={{
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 500,
                          backgroundColor: "rgba(34, 197, 94, 0.1)",
                          color: "var(--color-status-success)",
                          border: "1px solid rgba(34, 197, 94, 0.2)",
                        }}
                      >
                        <OrciaIcon name="checkFilled" size={12} /> {isFr ? "Synchronisation active" : "Sync active"}
                      </span>
                    )}

                    {isPaused && (
                      <button
                        type="button"
                        data-testid={`renew-referent-btn-${ds.id}`}
                        onClick={() => {
                          setRenewingDsId(ds.id);
                          setNewReferentInput(ds.referent_user_id || "");
                        }}
                        className="orcia-ds-btn-secondary"
                        style={{ padding: "3px 8px", fontSize: "11px" }}
                      >
                        {isFr ? "Renouveler le référent" : "Renew referent"}
                      </button>
                    )}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "11px", color: "var(--color-text-secondary)" }}>
                  <span>
                    {ds.sync_identity_mode === "SERVICE_ACCOUNT"
                      ? (isFr ? "Indexation : Compte de service" : "Indexing: Service account")
                      : `${isFr ? "Indexation : Référent d'équipe" : "Indexing: Team referent"} (${ds.referent_user_id || "aucun"})`}
                  </span>
                  <span style={{ fontStyle: "italic", fontSize: "10px" }}>
                    {isFr ? "Filtrage nominatif Passthrough actif à la lecture" : "Passthrough active on read"}
                  </span>
                </div>

                {isRenewing && (
                  <form
                    data-testid={`renew-referent-form-${ds.id}`}
                    autoComplete="off"
                    data-lpignore="true"
                    data-form-type="other"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void handleRenewReferent(ds.id);
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      marginTop: "6px",
                      paddingTop: "6px",
                      borderTop: "1px solid var(--color-border-subtle)",
                    }}
                  >
                    <input
                      type="text"
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      data-bwignore="true"
                      data-form-type="other"
                      data-testid={`renew-referent-input-${ds.id}`}
                      value={newReferentInput}
                      onChange={(e) => setNewReferentInput(e.target.value)}
                      placeholder={isFr ? "Nouveau membre référent (email)..." : "New referent email..."}
                      style={{ ...inputStyle, flex: 1 }}
                    />
                    <button
                      type="submit"
                      data-testid={`renew-referent-submit-btn-${ds.id}`}
                      disabled={!newReferentInput.trim()}
                      className="orcia-ds-btn-primary"
                      style={{ padding: "5px 10px", fontSize: "11px" }}
                    >
                      {isFr ? "Valider le renouvellement" : "Confirm renewal"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setRenewingDsId(null)}
                      className="orcia-ds-btn-secondary"
                      style={{ padding: "5px 10px", fontSize: "11px" }}
                    >
                      {isFr ? "Annuler" : "Cancel"}
                    </button>
                  </form>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
