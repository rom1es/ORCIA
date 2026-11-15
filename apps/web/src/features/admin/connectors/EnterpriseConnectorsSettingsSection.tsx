import {
  ContextualInfoTriggerButton,
  OrciaAlertBanner,
  OrciaIcon,
  StatusBadge,
  type ControlCenterDatasourceItem,
} from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import {
  createOrciaApiClient,
  OrciaProblemError,
  type EnterpriseConnectorCreateRequest,
  type EnterpriseConnectorItemResponse,
} from "@orcia/api-client";
import type { TranslationDictionary } from "../../../i18n/types";
import { useAuthSessionStore } from "../../../stores/authSessionStore";
import type { PlatformSetupContextValue } from "../../../components/platformSetupStore";

export interface EnterpriseConnectorsSettingsSectionProps {
  readonly isFr: boolean;
  readonly copy: TranslationDictionary["settingsHub"];
  readonly openHelpSection: (sectionId: string) => void;
  readonly canMutate?: boolean;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "12px",
};

export function EnterpriseConnectorsSettingsSection({
  isFr,
  copy,
  openHelpSection,
  canMutate = true,
}: EnterpriseConnectorsSettingsSectionProps): React.ReactElement {
  const [connectors, setConnectors] = useState<readonly EnterpriseConnectorItemResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // New connector form state
  const [kind, setKind] = useState<EnterpriseConnectorCreateRequest["connector_kind"]>("GITLAB");
  const [name, setName] = useState<string>("");
  const [baseUrl, setBaseUrl] = useState<string>("");
  const [authMode, setAuthMode] = useState<EnterpriseConnectorCreateRequest["auth_mode"]>("OAUTH2_PASSTHROUGH");
  const [adminSecret, setAdminSecret] = useState<string>("");

  const client = createOrciaApiClient({ baseUrl: "" });

  const loadConnectors = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await client.listEnterpriseConnectors();
      setConnectors(res.items);
    } catch (err) {
      if (err instanceof OrciaProblemError) {
        setErrorMessage(err.problem.title || err.message);
      } else {
        setErrorMessage(isFr ? "Impossible de charger les connecteurs." : "Failed to load connectors.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [isFr]);

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const accessToken = useAuthSessionStore((s) => s.accessToken);

  useEffect(() => {
    if (isHydrating) {
      return;
    }
    setErrorMessage(null);
    void loadConnectors();
  }, [loadConnectors, isHydrating, accessToken]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !baseUrl.trim()) return;
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await client.createEnterpriseConnector({
        connector_kind: kind,
        name: name.trim(),
        base_url: baseUrl.trim(),
        auth_mode: authMode,
        admin_secret_value: adminSecret.trim() ? adminSecret.trim() : undefined,
        enabled: true,
      });
      setName("");
      setBaseUrl("");
      setAdminSecret("");
      setSuccessMessage(
        isFr ? "Connecteur d'entreprise enregistré au niveau du socle." : "Enterprise connector registered.",
      );
      await loadConnectors();
    } catch (err) {
      if (err instanceof OrciaProblemError) {
        setErrorMessage(err.problem.detail || err.problem.title);
      } else {
        setErrorMessage(isFr ? "Erreur lors de l'enregistrement du connecteur." : "Error registering connector.");
      }
    }
  };

  const handleDelete = async (connectorId: string) => {
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await client.deleteEnterpriseConnector(connectorId);
      setSuccessMessage(isFr ? "Connecteur supprimé." : "Connector deleted.");
      await loadConnectors();
    } catch (err) {
      if (err instanceof OrciaProblemError) {
        setErrorMessage(err.problem.detail || err.problem.title);
      } else {
        setErrorMessage(isFr ? "Erreur lors de la suppression." : "Error deleting connector.");
      }
    }
  };

  return (
    <section
      data-testid="settings-connectors-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <strong style={{ fontSize: "15px" }}>
            {isFr
              ? "Connecteurs d'Entreprise du Socle"
              : "Enterprise Connectors"}
          </strong>
          <ContextualInfoTriggerButton
            sectionId="connectors-overview"
            label={
              isFr
                ? "Comprendre la configuration des connecteurs du socle"
                : "Understand foundation connectors configuration"
            }
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
          {isFr ? "Gouvernance globale Socle (zéro pollution d'espace)" : "Global Foundation Governance"}
        </span>
      </div>

      {errorMessage && (
        <OrciaAlertBanner tone="crimson" testId="connectors-error-banner">
          {errorMessage}
        </OrciaAlertBanner>
      )}

      {successMessage && (
        <OrciaAlertBanner tone="emerald" role="status" testId="connectors-success-banner">
          {successMessage}
        </OrciaAlertBanner>
      )}

      {/* Formulaire d'enregistrement de connecteur socle */}
      {canMutate && (
        <form
          data-testid="register-connector-form"
          autoComplete="off"
          data-lpignore="true"
          data-form-type="other"
          onSubmit={handleCreate}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            padding: "12px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border-subtle)",
            backgroundColor: "var(--color-surface-card)",
          }}
        >
          <span style={{ fontSize: "13px", fontWeight: 600 }}>
            {isFr ? "Ajouter un connecteur d'entreprise" : "Add an enterprise connector"}
          </span>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "8px" }}>
            <select
              data-testid="connector-kind-select"
              value={kind}
              onChange={(e) => setKind(e.target.value as EnterpriseConnectorCreateRequest["connector_kind"])}
              style={inputStyle}
            >
              <option value="GITLAB">GitLab Entreprise</option>
              <option value="JIRA">Jira Entreprise</option>
              <option value="CONFLUENCE">Confluence</option>
              <option value="OIDC_SSO">OIDC SSO / IAM</option>
              <option value="S3_OBJECT_STORE">S3 Object Store</option>
              <option value="SMTP_MAIL">
                {isFr ? "Serveur SMTP (codes OTP e-mail)" : "SMTP Server (email OTP codes)"}
              </option>
            </select>
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="connector-name-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={
                kind === "SMTP_MAIL"
                  ? isFr
                    ? "Nom usuel (ex: SMTP Relais Entreprise)"
                    : "Display name (e.g. Corporate SMTP)"
                  : isFr
                    ? "Nom usuel (ex: GitLab DS3C)"
                    : "Display name"
              }
              style={inputStyle}
            />
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="connector-base-url-input"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={
                kind === "SMTP_MAIL"
                  ? "smtp://smtp.entreprise.internal:587"
                  : isFr
                    ? "URL de base (ex: https://gitlab.ds3c.internal)"
                    : "Base URL"
              }
              style={inputStyle}
            />
            <select
              data-testid="connector-auth-mode-select"
              value={authMode}
              onChange={(e) => setAuthMode(e.target.value as EnterpriseConnectorCreateRequest["auth_mode"])}
              style={inputStyle}
            >
              <option value="OAUTH2_PASSTHROUGH">OAuth2 Passthrough</option>
              <option value="PERSONAL_ACCESS_TOKEN">Jeton d'accès personnel (PAT)</option>
              <option value="OIDC_FEDERATION">Fédération OIDC</option>
              <option value="SERVICE_SECRET">Secret de service</option>
            </select>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="connector-admin-secret-input"
              value={adminSecret}
              onChange={(e) => setAdminSecret(e.target.value)}
              placeholder={isFr ? "Secret d'administration (optionnel, chiffré AES-256-GCM)" : "Admin secret (optional)"}
              style={{ ...inputStyle, flex: 1, fontFamily: "monospace", WebkitTextSecurity: "disc" } as React.CSSProperties}
            />
            <button
              type="submit"
              data-testid="register-connector-submit-btn"
              disabled={!name.trim() || !baseUrl.trim()}
              className="orcia-ds-btn-primary"
              style={{ padding: "7px 14px", fontSize: "12px", whiteSpace: "nowrap" }}
            >
              {isFr ? "Enregistrer le connecteur" : "Save connector"}
            </button>
          </div>
        </form>
      )}

      {/* Liste des connecteurs configurés */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <span style={{ fontSize: "13px", fontWeight: 600 }}>
          {isFr ? "Connecteurs disponibles sur la plateforme" : "Available platform connectors"}
        </span>

        {isLoading ? (
          <p style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            {isFr ? "Chargement des connecteurs..." : "Loading connectors..."}
          </p>
        ) : connectors.length === 0 ? (
          <p style={{ fontSize: "12px", color: "var(--color-muted-foreground)", fontStyle: "italic" }}>
            {isFr
              ? "Aucun connecteur d'entreprise configuré pour l'instant."
              : "No enterprise connectors configured yet."}
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {connectors.map((c) => (
              <div
                key={c.id}
                data-testid={`enterprise-connector-row-${c.id}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border-subtle)",
                  backgroundColor: "var(--color-surface-primary)",
                  fontSize: "12px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <strong>{c.name}</strong>
                    <span style={{ fontSize: "10px", fontFamily: "monospace", color: "var(--color-muted-foreground)" }}>
                      [{c.connector_kind}]
                    </span>
                    <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                      {c.auth_mode}
                    </span>
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)", fontFamily: "monospace" }}>
                    {c.base_url}
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  {c.admin_secret_status.configured ? (
                    <span
                      data-testid={`connector-secret-badge-${c.id}`}
                      style={{
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "10px",
                        fontFamily: "monospace",
                        backgroundColor: "rgba(34, 197, 94, 0.1)",
                        color: "var(--color-status-success)",
                        border: "1px solid rgba(34, 197, 94, 0.2)",
                      }}
                    >
                      {c.admin_secret_status.fingerprint || "sha256:configured"}
                    </span>
                  ) : (
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "10px",
                        backgroundColor: "var(--color-surface-secondary)",
                        color: "var(--color-muted-foreground)",
                      }}
                    >
                      {isFr ? "Passthrough nominatif" : "Personal passthrough"}
                    </span>
                  )}

                  {canMutate && (
                    <button
                      type="button"
                      data-testid={`delete-connector-btn-${c.id}`}
                      onClick={() => handleDelete(c.id)}
                      className="orcia-ds-btn-danger"
                      style={{ padding: "4px 8px", fontSize: "11px" }}
                    >
                      {isFr ? "Supprimer" : "Delete"}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
