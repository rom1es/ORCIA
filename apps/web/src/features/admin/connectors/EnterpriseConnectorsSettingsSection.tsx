import {
  OrciaAlertBanner,
  OrciaIcon,
  StatusBadge,
} from "@orcia/ui";
import React from "react";
import type { EnterpriseConnectorCreateRequest } from "@orcia/api-client";
import type { TranslationDictionary } from "../../../i18n/types";
import { useEnterpriseConnectorsController } from "./useEnterpriseConnectorsController";

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
  canMutate = true,
}: EnterpriseConnectorsSettingsSectionProps): React.ReactElement {
  const {
    connectors,
    isLoading,
    errorMessage,
    successMessage,
    kind,
    setKind,
    name,
    setName,
    baseUrl,
    setBaseUrl,
    authMode,
    setAuthMode,
    adminSecret,
    setAdminSecret,
    handleCreate,
    handleDelete,
  } = useEnterpriseConnectorsController(isFr);

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
              <option value="OAUTH2_PASSTHROUGH">Connexion déléguée (OAuth2 utilisateur)</option>
              <option value="PERSONAL_ACCESS_TOKEN">Jeton d'accès personnel</option>
              <option value="OIDC_FEDERATION">Fédération d'identité (OIDC)</option>
              <option value="SERVICE_SECRET">Secret de service</option>
            </select>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
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
              placeholder={isFr ? "Secret d'administration (optionnel, chiffré côté serveur)" : "Admin secret (optional)"}
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
                  flexWrap: "wrap",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "8px",
                  padding: "10px 14px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border-subtle)",
                  backgroundColor: "var(--color-surface-primary)",
                  fontSize: "12px",
                  minWidth: 0,
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "3px", minWidth: 0 }}>
                  <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px" }}>
                    <strong>{c.name}</strong>
                    <span style={{ fontSize: "10px", fontFamily: "monospace", color: "var(--color-muted-foreground)" }}>
                      [{c.connector_kind}]
                    </span>
                    <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                      {c.auth_mode}
                    </span>
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)", fontFamily: "monospace", wordBreak: "break-all" }}>
                    {c.base_url}
                  </span>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" }}>
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
