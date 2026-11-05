import {
  ContextualInfoTriggerButton,
  EffortSelector,
  InferenceTierBadge,
  LayersInspectorPopover,
  SecretField,
  StatusBadge,
  WorkflowTopGovernanceBar,
  type ControlCenterDatasourceItem,
  type ControlCenterWorkspaceGovItem,
  type InferenceTierAndEffortLabels,
  type StudioLifecycleTabKey,
  type SubWorkflowLayerViewItem,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import React, { useState } from "react";
import type {
  ConfiguredAuditEvent,
  ConfiguredLlmTierMapping,
  ConfiguredPackItem,
  ConfiguredWorkflowItem,
  PlatformSetupContextValue,
} from "../components/platformSetupStore";
import { SimplifiedProcessBuilderSection } from "../components/SimplifiedProcessBuilderSection";
import type { TranslationDictionary } from "../i18n/types";
import type { SettingsSectionTab } from "./settings";

export interface SettingsSecondaryTabsSectionProps {
  readonly activeTab: Exclude<SettingsSectionTab, "iam">;
  readonly isFr: boolean;
  readonly copy: TranslationDictionary["settingsHub"];
  readonly tierAndEffortLabels: InferenceTierAndEffortLabels;
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly packs: readonly ConfiguredPackItem[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly auditEvents: readonly ConfiguredAuditEvent[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly upsertLlmTier: (input: ConfiguredLlmTierMapping) => void;
  readonly registerDatasource: PlatformSetupContextValue["registerDatasource"];
  readonly registerPack: (input: ConfiguredPackItem) => void;
  readonly upsertWorkflow: (input: ConfiguredWorkflowItem) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

const primaryBtnStyle: React.CSSProperties = {
  padding: "7px 14px",
  borderRadius: "var(--radius-sm)",
  border: "none",
  backgroundColor: "var(--color-primary-cobalt)",
  color: "var(--color-primary-foreground)",
  fontWeight: 600,
  cursor: "pointer",
};

export function SettingsSecondaryTabsSection({
  activeTab,
  isFr,
  copy,
  tierAndEffortLabels,
  llmTiers,
  workspaces,
  datasources,
  packs,
  workflows,
  auditEvents,
  openHelpSection,
  upsertLlmTier,
  registerDatasource,
  registerPack,
  upsertWorkflow,
}: SettingsSecondaryTabsSectionProps) {
  const [connAlias, setConnAlias] = useState("");
  const [connScheme, setConnScheme] = useState<"git" | "confluence" | "jira" | "db">("git");
  const [connUri, setConnUri] = useState("");
  const [connIdentity, setConnIdentity] = useState<"passthrough" | "service_account">("passthrough");
  const [connSecretConfigured, setConnSecretConfigured] = useState(false);
  const [connSecretFingerprint, setConnSecretFingerprint] = useState<string | null>(null);

  const [selectedTier, setSelectedTier] = useState<UiInferenceTier>("medium");
  const [selectedEffort, setSelectedEffort] = useState<UiInferenceEffort>("balanced");
  const [primaryModel, setPrimaryModel] = useState("");
  const [secondaryModel, setSecondaryModel] = useState("");
  const [modelFamily, setModelFamily] = useState("family-a");

  const [packKey, setPackKey] = useState("");
  const [packVersion, setPackVersion] = useState("1.0.0");
  const [packScope, setPackScope] = useState("GLOBAL");

  const [wfKey, setWfKey] = useState("");
  const [wfTitle, setWfTitle] = useState("");
  const [wfVersion, setWfVersion] = useState("1.0.0");
  const [wfStatus, setWfStatus] = useState<StudioLifecycleTabKey>("DRAFT");
  const [wfPrePrompt, setWfPrePrompt] = useState("");
  const [wfParamsCsv, setWfParamsCsv] = useState("");
  const [wfSectionsCsv, setWfSectionsCsv] = useState("");
  const [layers, setLayers] = useState<readonly SubWorkflowLayerViewItem[]>([
    { layerId: "layer-ctx", label: "1. Collecte de Contexte & Sources", zone: "inputs", orderIndex: 1, enabled: true },
    { layerId: "layer-agent", label: "2. Exécution Agentique & Vérification", zone: "capabilities", orderIndex: 1, enabled: true },
    { layerId: "layer-out", label: "3. Validation du Contrat de Sortie", zone: "deliverables", orderIndex: 1, enabled: true },
  ]);

  if (activeTab === "ai-models") {
    return (
      <section data-testid="settings-ai-models-section" className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <InferenceTierBadge tier={selectedTier} effort={selectedEffort} labels={tierAndEffortLabels} />
            <ContextualInfoTriggerButton
              sectionId="ai-models-overview"
              label={isFr ? "Comprendre les niveaux de modèles IA et les fournisseurs indépendants" : "Understand AI model levels and independent providers"}
              onOpenHelpSection={openHelpSection}
            />
          </div>
          <EffortSelector
            selectedTier={selectedTier}
            selectedEffort={selectedEffort}
            labels={tierAndEffortLabels}
            onTierChange={setSelectedTier}
            onEffortChange={setSelectedEffort}
          />
        </div>
        <form
          data-testid="configure-llm-tier-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!primaryModel.trim()) return;
            upsertLlmTier({
              tier: selectedTier,
              primaryModel: primaryModel.trim(),
              secondaryModel: secondaryModel.trim() || primaryModel.trim(),
              modelFamily: modelFamily.trim() || "family-a",
              defaultEffort: selectedEffort,
            });
            setPrimaryModel("");
            setSecondaryModel("");
          }}
          style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}
        >
          <input type="text" data-testid="llm-primary-model-input" value={primaryModel} onChange={(e) => setPrimaryModel(e.target.value)} placeholder={isFr ? "Modèle principal (ex: fournisseur/modèle)..." : "Primary model..."} style={{ ...inputStyle, flex: 1, minWidth: "200px" }} />
          <input type="text" data-testid="llm-secondary-model-input" value={secondaryModel} onChange={(e) => setSecondaryModel(e.target.value)} placeholder={isFr ? "Modèle secondaire de secours..." : "Backup model..."} style={{ ...inputStyle, flex: 1, minWidth: "200px" }} />
          <input type="text" data-testid="llm-family-input" value={modelFamily} onChange={(e) => setModelFamily(e.target.value)} placeholder={isFr ? "Fournisseur IA (ex: Mistral, Anthropic)..." : "AI provider..."} style={inputStyle} />
          <button type="submit" data-testid="save-llm-tier-btn" style={primaryBtnStyle}>{isFr ? "Enregistrer le niveau" : "Save level"}</button>
        </form>
        {llmTiers.length === 0 ? (
          <p data-testid="llm-tiers-empty-state" style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr ? "Aucun modèle IA configuré. Associez les niveaux simple / standard / approfondi à vos modèles IA." : "No AI model configured yet. Assign simple / standard / in-depth levels to your AI models."}
          </p>
        ) : (
          <div style={{ display: "grid", gap: "8px" }}>
            {llmTiers.map((item) => (
              <div key={item.tier} data-testid={`llm-tier-row-${item.tier}`} style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span><strong>{item.tier}</strong> → <code>{item.primaryModel}</code> (secours: <code>{item.secondaryModel}</code>)</span>
                <StatusBadge label={`${item.modelFamily} · ${item.defaultEffort}`} tone="emerald" monospace />
              </div>
            ))}
          </div>
        )}
      </section>
    );
  }

  if (activeTab === "connectors") {
    return (
      <section data-testid="settings-connectors-section" className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <strong style={{ fontSize: "14px" }}>{isFr ? "Clé d'accès et connexion aux sources documentaires" : "Access key and document source connection"}</strong>
          <ContextualInfoTriggerButton
            sectionId="connectors-overview"
            label={isFr ? "Comprendre la connexion aux outils et la protection des clés d'accès" : "Understand tool connections and access key protection"}
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <SecretField
          status={{ configured: connSecretConfigured, fingerprint: connSecretFingerprint, updatedAt: "", updatedBy: "" }}
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
            fieldLabel: isFr ? "Clé secrète du connecteur (protégée après saisie)" : "Connector secret key (protected after entry)",
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
          <select data-testid="connector-scheme-select" value={connScheme} onChange={(e) => setConnScheme(e.target.value as "git" | "confluence" | "jira" | "db")} style={inputStyle}>
            <option value="git">git</option>
            <option value="confluence">confluence</option>
            <option value="jira">jira</option>
            <option value="db">db</option>
          </select>
          <input type="text" data-testid="connector-alias-input" value={connAlias} onChange={(e) => setConnAlias(e.target.value)} placeholder={isFr ? "Alias du connecteur..." : "Connector alias..."} style={inputStyle} />
          <input type="text" data-testid="connector-uri-input" value={connUri} onChange={(e) => setConnUri(e.target.value)} placeholder={isFr ? "URI (ex: git://...)" : "URI (e.g. git://...)"} style={{ ...inputStyle, flex: 1, minWidth: "220px" }} />
          <select data-testid="connector-identity-select" value={connIdentity} onChange={(e) => setConnIdentity(e.target.value as "passthrough" | "service_account")} style={inputStyle}>
            <option value="passthrough">passthrough</option>
            <option value="service_account">service_account</option>
          </select>
          <button type="submit" data-testid="save-connector-btn" style={primaryBtnStyle}>{isFr ? "+ Enregistrer le connecteur" : "+ Save connector"}</button>
        </form>
        {datasources.length === 0 ? (
          <p data-testid="connectors-empty-state" style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>{isFr ? "Aucun connecteur configuré." : "No connector configured yet."}</p>
        ) : (
          <div style={{ display: "grid", gap: "8px" }}>
            {datasources.map((ds) => (
              <div key={ds.id} data-testid={`connector-row-${ds.id}`} style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span><strong>{ds.alias}</strong> — <code>{ds.uri}</code></span>
                <StatusBadge label={`${ds.scheme} · ${ds.executionIdentity}`} tone="cobalt" monospace />
              </div>
            ))}
          </div>
        )}
      </section>
    );
  }

  if (activeTab === "packs") {
    return (
      <section data-testid="settings-packs-section" className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <form
          data-testid="register-pack-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (!packKey.trim()) return;
            registerPack({ packKey: packKey.trim(), version: packVersion.trim() || "1.0.0", scopePath: packScope.trim() || "GLOBAL", status: "PUBLISHED" });
            setPackKey("");
          }}
          style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}
        >
          <input type="text" data-testid="pack-key-input" value={packKey} onChange={(e) => setPackKey(e.target.value)} placeholder={isFr ? "Identifiant du Pack (ex: orcia-pack-sdlc)..." : "Pack key..."} style={{ ...inputStyle, flex: 1, minWidth: "220px" }} />
          <input type="text" data-testid="pack-version-input" value={packVersion} onChange={(e) => setPackVersion(e.target.value)} placeholder="SemVer (1.0.0)" style={inputStyle} />
          <input type="text" data-testid="pack-scope-input" value={packScope} onChange={(e) => setPackScope(e.target.value)} placeholder="Périmètre (GLOBAL)" style={inputStyle} />
          <button type="submit" data-testid="save-pack-btn" style={primaryBtnStyle}>{isFr ? "+ Activer le Pack" : "+ Activate Pack"}</button>
        </form>
        {packs.length === 0 ? (
          <p data-testid="packs-empty-state" style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>{isFr ? "Aucun Pack métier activé sur ce périmètre." : "No business Pack activated on this scope yet."}</p>
        ) : (
          <div style={{ display: "grid", gap: "8px" }}>
            {packs.map((p) => (
              <div key={`${p.packKey}@${p.version}`} data-testid={`pack-row-${p.packKey}`} style={{ padding: "8px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>{p.packKey}@{p.version}</strong>
                <StatusBadge label={`${p.status} · ${p.scopePath}`} tone="emerald" monospace />
              </div>
            ))}
          </div>
        )}
      </section>
    );
  }

  if (activeTab === "workflows") {
    void WorkflowTopGovernanceBar;
    void LayersInspectorPopover;
    void wfKey;
    void setWfKey;
    void wfTitle;
    void setWfTitle;
    void wfVersion;
    void setWfVersion;
    void wfStatus;
    void setWfStatus;
    void wfPrePrompt;
    void setWfPrePrompt;
    void wfParamsCsv;
    void setWfParamsCsv;
    void wfSectionsCsv;
    void setWfSectionsCsv;
    void layers;
    void setLayers;
    return (
      <SimplifiedProcessBuilderSection
        isFr={isFr}
        workflows={workflows}
        openHelpSection={openHelpSection}
        upsertWorkflow={upsertWorkflow}
      />
    );
  }

  return (
    <section data-testid="settings-audit-section" className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <h2 style={{ margin: 0, fontSize: "15px" }}>{isFr ? "Journal des Modifications de Configuration" : "Configuration Change Log"}</h2>
        <ContextualInfoTriggerButton
          sectionId="audit-overview"
          label={isFr ? "Comprendre le journal d'activité et le suivi des modifications" : "Understand the activity log and configuration change tracking"}
          onOpenHelpSection={openHelpSection}
        />
      </div>
      {auditEvents.length === 0 ? (
        <p data-testid="audit-events-empty-state" style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>{isFr ? "Aucun événement de paramétrage enregistré." : "No configuration event recorded yet."}</p>
      ) : (
        <div style={{ display: "grid", gap: "6px" }}>
          {auditEvents.map((ev) => (
            <div key={ev.id} data-testid={`audit-event-row-${ev.id}`} style={{ padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>{ev.summary}</span>
              <StatusBadge label={ev.eventType} tone="cobalt" monospace />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
