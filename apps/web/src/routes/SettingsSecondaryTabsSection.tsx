import {
  ContextualInfoTriggerButton,
  SecretField,
  StatusBadge,
  type ControlCenterDatasourceItem,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React, { useState } from "react";
import type { PlatformSetupContextValue } from "../components/platformSetupStore";
import type { TranslationDictionary } from "../i18n/types";

export interface SettingsSecondaryTabsSectionProps {
  readonly isFr: boolean;
  readonly copy: TranslationDictionary["settingsHub"];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly registerDatasource: PlatformSetupContextValue["registerDatasource"];
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function SettingsSecondaryTabsSection({
  isFr,
  copy,
  workspaces,
  datasources,
  openHelpSection,
  registerDatasource,
}: SettingsSecondaryTabsSectionProps) {
  const [connAlias, setConnAlias] = useState("");
  const [connScheme, setConnScheme] = useState<"git" | "confluence" | "jira" | "db">("git");
  const [connUri, setConnUri] = useState("");
  const [connIdentity, setConnIdentity] = useState<"passthrough" | "service_account">(
    "passthrough",
  );
  const [connSecretConfigured, setConnSecretConfigured] = useState(false);
  const [connSecretFingerprint, setConnSecretFingerprint] = useState<string | null>(null);

  return (
    <section
      data-testid="settings-connectors-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <strong style={{ fontSize: "14px" }}>
          {isFr
            ? "Clé d'accès et connexion aux sources documentaires"
            : "Access key and document source connection"}
        </strong>
        <ContextualInfoTriggerButton
          sectionId="connectors-overview"
          label={
            isFr
              ? "Comprendre la connexion aux outils et la protection des clés d'accès"
              : "Understand tool connections and access key protection"
          }
          onOpenHelpSection={openHelpSection}
        />
      </div>
      <SecretField
        status={{
          configured: connSecretConfigured,
          fingerprint: connSecretFingerprint,
          updatedAt: "",
          updatedBy: "",
        }}
        onSecretAction={(action) => {
          if (action.action === "set" && action.plaintextValue) {
            setConnSecretConfigured(true);
            setConnSecretFingerprint("sha256:configured");
          } else if (action.action === "clear") {
            setConnSecretConfigured(false);
            setConnSecretFingerprint(null);
          }
        }}
        labels={{
          fieldLabel: isFr
            ? "Clé secrète du connecteur (protégée après saisie)"
            : "Connector secret key (protected after entry)",
          configuredBadge: copy.secretFieldLabels.configuredBadge,
          unconfiguredBadge: copy.secretFieldLabels.unconfiguredBadge,
          fingerprintPrefix: copy.secretFieldLabels.fingerprintLabel,
          replaceSecretCta: copy.secretFieldLabels.replaceButton,
          cancelReplaceCta: copy.secretFieldLabels.keepButton,
          clearSecretCta: copy.secretFieldLabels.clearButton,
          saveNewSecretCta: copy.secretFieldLabels.replaceButton,
          inputPlaceholder: copy.secretFieldLabels.inputPlaceholder,
        }}
      />
      <form
        data-testid="register-connector-form"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        onSubmit={(e) => {
          e.preventDefault();
          if (!connAlias.trim() || !connUri.trim()) return;
          registerDatasource({
            workspaceName: workspaces[0]?.name ?? "Plateforme Globale ORCIA",
            alias: connAlias.trim(),
            scheme: connScheme,
            uri: connUri.trim(),
            executionIdentity: connIdentity,
            freshnessTtlDays: 30,
          });
          setConnAlias("");
          setConnUri("");
        }}
        style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}
      >
        <select
          data-testid="connector-scheme-select"
          value={connScheme}
          onChange={(e) =>
            setConnScheme(e.target.value as "git" | "confluence" | "jira" | "db")
          }
          style={inputStyle}
        >
          <option value="git">git</option>
          <option value="confluence">confluence</option>
          <option value="jira">jira</option>
          <option value="db">db</option>
        </select>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="connector-alias-input"
          value={connAlias}
          onChange={(e) => setConnAlias(e.target.value)}
          placeholder={isFr ? "Alias du connecteur..." : "Connector alias..."}
          style={inputStyle}
        />
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="connector-uri-input"
          value={connUri}
          onChange={(e) => setConnUri(e.target.value)}
          placeholder={isFr ? "URI (ex: git://...)" : "URI (e.g. git://...)"}
          style={{ ...inputStyle, flex: 1, minWidth: "220px" }}
        />
        <select
          data-testid="connector-identity-select"
          value={connIdentity}
          onChange={(e) =>
            setConnIdentity(e.target.value as "passthrough" | "service_account")
          }
          style={inputStyle}
        >
          <option value="passthrough">passthrough</option>
          <option value="service_account">service_account</option>
        </select>
        <button
          type="submit"
          data-testid="save-connector-btn"
          className="orcia-ds-btn orcia-ds-btn-primary"
        >
          {isFr ? "+ Enregistrer le connecteur" : "+ Save connector"}
        </button>
      </form>
      {datasources.length === 0 ? (
        <p
          data-testid="connectors-empty-state"
          style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
        >
          {isFr ? "Aucun connecteur configuré." : "No connector configured yet."}
        </p>
      ) : (
        <div style={{ display: "grid", gap: "8px" }}>
          {datasources.map((ds) => (
            <div
              key={ds.id}
              data-testid={`connector-row-${ds.id}`}
              style={{
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>
                <strong>{ds.alias}</strong> — <code>{ds.uri}</code>
              </span>
              <StatusBadge
                label={`${ds.scheme} · ${ds.executionIdentity}`}
                tone="cobalt"
                monospace
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
