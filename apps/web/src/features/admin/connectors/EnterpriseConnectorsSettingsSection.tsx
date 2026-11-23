import {
  OrciaAlertBanner,
} from "@orcia/ui";
import React from "react";
import type { EnterpriseConnectorCreateRequest } from "@orcia/api-client";
import { resolveDictionaryForFlag } from "../../../i18n";
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
  canMutate = true,
}: EnterpriseConnectorsSettingsSectionProps): React.ReactElement {
  const connCopy = resolveDictionaryForFlag(isFr).featureAdminCatalogSettings.connectors;
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
          <strong style={{ fontSize: "15px" }}>{connCopy.title}</strong>
        </div>
        <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
          {connCopy.globalGovernanceBadge}
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

      {/* Platform connector registration form */}
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
            {connCopy.addConnectorTitle}
          </span>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "8px" }}>
            <select
              data-testid="connector-kind-select"
              value={kind}
              onChange={(e) => setKind(e.target.value as EnterpriseConnectorCreateRequest["connector_kind"])}
              style={inputStyle}
            >
              <option value="GITLAB">{connCopy.kindGitlabOption}</option>
              <option value="JIRA">{connCopy.kindJiraOption}</option>
              <option value="CONFLUENCE">{connCopy.kindConfluenceOption}</option>
              <option value="OIDC_SSO">{connCopy.kindOidcOption}</option>
              <option value="S3_OBJECT_STORE">{connCopy.kindS3Option}</option>
              <option value="SMTP_MAIL">{connCopy.kindSmtpOption}</option>
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
                  ? connCopy.namePlaceholderSmtp
                  : connCopy.namePlaceholderDefault
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
                  : connCopy.baseUrlPlaceholderDefault
              }
              style={inputStyle}
            />
            <select
              data-testid="connector-auth-mode-select"
              value={authMode}
              onChange={(e) => setAuthMode(e.target.value as EnterpriseConnectorCreateRequest["auth_mode"])}
              style={inputStyle}
            >
              <option value="OAUTH2_PASSTHROUGH">{connCopy.authOAuth2Option}</option>
              <option value="PERSONAL_ACCESS_TOKEN">{connCopy.authPatOption}</option>
              <option value="OIDC_FEDERATION">{connCopy.authOidcOption}</option>
              <option value="SERVICE_SECRET">{connCopy.authServiceSecretOption}</option>
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
              placeholder={connCopy.adminSecretPlaceholder}
              style={{ ...inputStyle, flex: 1, fontFamily: "monospace", WebkitTextSecurity: "disc" } as React.CSSProperties}
            />
            <button
              type="submit"
              data-testid="register-connector-submit-btn"
              disabled={!name.trim() || !baseUrl.trim()}
              className="orcia-ds-btn-primary"
              style={{ padding: "7px 14px", fontSize: "12px", whiteSpace: "nowrap" }}
            >
              {connCopy.saveConnectorBtn}
            </button>
          </div>
        </form>
      )}

      {/* Configured connectors list */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <span style={{ fontSize: "13px", fontWeight: 600 }}>
          {connCopy.availableConnectorsTitle}
        </span>

        {isLoading ? (
          <p style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            {connCopy.loadingConnectors}
          </p>
        ) : connectors.length === 0 ? (
          <p style={{ fontSize: "12px", color: "var(--color-muted-foreground)", fontStyle: "italic" }}>
            {connCopy.emptyConnectors}
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
                      {connCopy.personalDelegatedBadge}
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
                      {connCopy.deleteBtn}
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
