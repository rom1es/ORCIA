import {
  EffortSelector,
  InferenceTierBadge,
  LayersInspectorPopover,
  PermissionGuard,
  SecretField,
  StatusBadge,
  WorkflowTopGovernanceBar,
  type InferenceTierAndEffortLabels,
  type StudioLifecycleTabKey,
  type SubWorkflowLayerViewItem,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiPermissionVerb,
} from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import { usePlatformSetup } from "../components/platformSetupStore";
import { useI18n } from "../i18n";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

export type SettingsSectionTab =
  | "iam"
  | "connectors"
  | "ai-models"
  | "packs"
  | "workflows"
  | "audit";

export function SettingsHubView() {
  const { dictionary, locale } = useI18n();
  const copy = dictionary.settingsHub;
  const isFr = locale === "fr";

  const {
    orgUnits,
    rbacGrants,
    llmTiers,
    workspaces,
    datasources,
    packs,
    workflows,
    auditEvents,
    addOrgUnit,
    addRbacGrant,
    upsertLlmTier,
    registerDatasource,
    registerPack,
    upsertWorkflow,
  } = usePlatformSetup();

  const [activeTab, setActiveTab] = useState<SettingsSectionTab>("iam");
  const [allowedVerbs] = useState<readonly UiPermissionVerb[]>([
    "create",
    "read",
    "update",
    "delete",
    "execute",
    "grant",
  ]);

  // Tab 1: IAM / Org Unit form state
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [orgLevel, setOrgLevel] = useState<"BU" | "TEAM">("BU");
  const [grantSubjectType, setGrantSubjectType] = useState<"ROLE" | "USER">("ROLE");
  const [grantSubjectId, setGrantSubjectId] = useState("TEAM_LEAD");
  const [grantScopePath, setGrantScopePath] = useState("GLOBAL");
  const [grantVerb, setGrantVerb] = useState<UiPermissionVerb>("execute");
  const [grantEffect, setGrantEffect] = useState<"ALLOW" | "DENY" | "INHERITANCE_BLOCK">("ALLOW");

  // Tab 2: Connectors form state
  const [connAlias, setConnAlias] = useState("");
  const [connScheme, setConnScheme] = useState<"git" | "confluence" | "jira" | "db">("git");
  const [connUri, setConnUri] = useState("");
  const [connIdentity, setConnIdentity] = useState<"passthrough" | "service_account">("passthrough");
  const [connSecretConfigured, setConnSecretConfigured] = useState(false);
  const [connSecretFingerprint, setConnSecretFingerprint] = useState<string | null>(null);

  // Tab 3: AI Models & Cognitive Tiers form state
  const [selectedTier, setSelectedTier] = useState<UiInferenceTier>("medium");
  const [selectedEffort, setSelectedEffort] = useState<UiInferenceEffort>("balanced");
  const [primaryModel, setPrimaryModel] = useState("");
  const [secondaryModel, setSecondaryModel] = useState("");
  const [modelFamily, setModelFamily] = useState("family-a");

  // Tab 4: Packs form state
  const [packKey, setPackKey] = useState("");
  const [packVersion, setPackVersion] = useState("1.0.0");
  const [packScope, setPackScope] = useState("GLOBAL");

  // Tab 5: Workflow Studio form state
  const [wfKey, setWfKey] = useState("");
  const [wfTitle, setWfTitle] = useState("");
  const [wfVersion, setWfVersion] = useState("1.0.0");
  const [wfStatus, setWfStatus] = useState<StudioLifecycleTabKey>("DRAFT");
  const [wfPrePrompt, setWfPrePrompt] = useState("");
  const [wfParamsCsv, setWfParamsCsv] = useState("");
  const [wfSectionsCsv, setWfSectionsCsv] = useState("");
  const [layers, setLayers] = useState<readonly SubWorkflowLayerViewItem[]>([
    {
      layerId: "layer-ctx",
      label: "1. Collecte de Contexte & Sources",
      zone: "inputs",
      orderIndex: 1,
      enabled: true,
    },
    {
      layerId: "layer-agent",
      label: "2. Exécution Agentique & Vérification",
      zone: "capabilities",
      orderIndex: 1,
      enabled: true,
    },
    {
      layerId: "layer-out",
      label: "3. Validation du Contrat de Sortie",
      zone: "deliverables",
      orderIndex: 1,
      enabled: true,
    },
  ]);

  const tierAndEffortLabels: InferenceTierAndEffortLabels = {
    tierLabel: copy.tabs.aiModels,
    effortLabel: "Effort",
    simpleBadge: copy.tierLabels.simple,
    mediumBadge: copy.tierLabels.medium,
    complexBadge: copy.tierLabels.complex,
    autoBadge: copy.tierLabels.auto,
    effortDefault: copy.effortLabels.default,
    effortFast: copy.effortLabels.fast,
    effortBalanced: copy.effortLabels.balanced,
    effortDeep: copy.effortLabels.deep,
  };

  const tabs: readonly { key: SettingsSectionTab; label: string }[] = [
    { key: "iam", label: copy.tabs.iam },
    { key: "ai-models", label: copy.tabs.aiModels },
    { key: "connectors", label: copy.tabs.connectors },
    { key: "packs", label: copy.tabs.packs },
    { key: "workflows", label: copy.tabs.workflows },
    { key: "audit", label: copy.tabs.audit },
  ];

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

  return (
    <div
      data-testid="settings-hub-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <header className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <h1 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>{copy.hubTitle}</h1>
        <p style={{ margin: 0, fontSize: "var(--font-size-body)", color: "var(--color-muted-foreground)" }}>
          {copy.hubSubtitle}
        </p>

        <nav
          role="tablist"
          aria-label="Settings hub navigation"
          style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "8px" }}
        >
          {tabs.map((tab) => {
            const isSelected = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={isSelected}
                data-testid={`settings-tab-${tab.key}`}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: isSelected
                    ? "1px solid var(--color-primary-cobalt)"
                    : "1px solid var(--color-border)",
                  backgroundColor: isSelected
                    ? "var(--color-primary-cobalt)"
                    : "var(--color-surface-card)",
                  color: isSelected
                    ? "var(--color-primary-foreground)"
                    : "var(--color-foreground)",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </header>

      <PermissionGuard
        scopePath="GLOBAL"
        verb="read"
        allowedVerbs={allowedVerbs}
        labels={{
          passiveLockBadge: "🔒 Accès restreint",
          passiveLockDescription: copy.lockedSectionNotice,
          requestAccessCta: copy.requestAccessLabel,
          disabledHint: copy.lockedSectionNotice,
        }}
      >
        <div
          data-testid={`settings-panel-${activeTab}`}
          style={{ display: "flex", flexDirection: "column", gap: "16px" }}
        >
          {activeTab === "iam" && (
            <section
              data-testid="settings-iam-section"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "16px" }}
            >
              <div>
                <h2 style={{ margin: 0, fontSize: "15px" }}>
                  {isFr
                    ? "1. Créer une Unité d'Organisation (BU / Équipe)"
                    : "1. Create an Organization Unit (BU / Team)"}
                </h2>
                <form
                  data-testid="create-org-unit-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!orgName.trim()) return;
                    addOrgUnit({
                      name: orgName.trim(),
                      slug: orgSlug.trim() || orgName.trim().toLowerCase().replace(/\s+/g, "-"),
                      level: orgLevel,
                      parentId: "scope-global",
                    });
                    setOrgName("");
                    setOrgSlug("");
                  }}
                  style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "10px" }}
                >
                  <select
                    data-testid="org-unit-level-select"
                    value={orgLevel}
                    onChange={(e) => setOrgLevel(e.target.value as "BU" | "TEAM")}
                    style={inputStyle}
                  >
                    <option value="BU">BU (Business Unit)</option>
                    <option value="TEAM">TEAM (Équipe)</option>
                  </select>
                  <input
                    type="text"
                    data-testid="org-unit-name-input"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder={isFr ? "Nom de l'unité..." : "Unit name..."}
                    style={{ ...inputStyle, flex: 1, minWidth: "180px" }}
                  />
                  <input
                    type="text"
                    data-testid="org-unit-slug-input"
                    value={orgSlug}
                    onChange={(e) => setOrgSlug(e.target.value)}
                    placeholder={isFr ? "Slug (optionnel)..." : "Slug (optional)..."}
                    style={inputStyle}
                  />
                  <button type="submit" data-testid="create-org-unit-btn" style={primaryBtnStyle}>
                    {isFr ? "+ Créer l'unité" : "+ Create unit"}
                  </button>
                </form>

                {orgUnits.length === 0 ? (
                  <p
                    data-testid="iam-org-units-empty-state"
                    style={{ margin: "10px 0 0 0", fontSize: "13px", color: "var(--color-muted-foreground)" }}
                  >
                    {isFr
                      ? "Aucune unité d'organisation configurée."
                      : "No organization unit configured yet."}
                  </p>
                ) : (
                  <div style={{ display: "grid", gap: "6px", marginTop: "10px" }}>
                    {orgUnits.map((u) => (
                      <div
                        key={u.id}
                        data-testid={`org-unit-row-${u.id}`}
                        style={{
                          padding: "8px 10px",
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--color-border)",
                          display: "flex",
                          justifyContent: "space-between",
                        }}
                      >
                        <strong>{u.name}</strong>
                        <StatusBadge label={`${u.level} · ${u.slug}`} tone="cobalt" monospace />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: "14px" }}>
                <h2 style={{ margin: 0, fontSize: "15px" }}>
                  {isFr
                    ? "2. Attribuer une Règle d'Habilitation RBAC/ABAC (6 Verbes)"
                    : "2. Grant a 6-Verb RBAC/ABAC Permission Rule"}
                </h2>
                <form
                  data-testid="create-rbac-grant-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!grantSubjectId.trim() || !grantScopePath.trim()) return;
                    addRbacGrant({
                      subjectType: grantSubjectType,
                      subjectId: grantSubjectId.trim(),
                      scopePath: grantScopePath.trim(),
                      verb: grantVerb,
                      effect: grantEffect,
                    });
                  }}
                  style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "10px" }}
                >
                  <select
                    value={grantSubjectType}
                    onChange={(e) => setGrantSubjectType(e.target.value as "ROLE" | "USER")}
                    style={inputStyle}
                  >
                    <option value="ROLE">ROLE</option>
                    <option value="USER">USER</option>
                  </select>
                  <input
                    type="text"
                    data-testid="rbac-subject-input"
                    value={grantSubjectId}
                    onChange={(e) => setGrantSubjectId(e.target.value)}
                    placeholder="Sujet (ex: TEAM_LEAD)"
                    style={inputStyle}
                  />
                  <input
                    type="text"
                    data-testid="rbac-scope-input"
                    value={grantScopePath}
                    onChange={(e) => setGrantScopePath(e.target.value)}
                    placeholder="Périmètre (ex: GLOBAL)"
                    style={inputStyle}
                  />
                  <select
                    data-testid="rbac-verb-select"
                    value={grantVerb}
                    onChange={(e) => setGrantVerb(e.target.value as UiPermissionVerb)}
                    style={inputStyle}
                  >
                    <option value="create">create</option>
                    <option value="read">read</option>
                    <option value="update">update</option>
                    <option value="delete">delete</option>
                    <option value="execute">execute</option>
                    <option value="grant">grant</option>
                  </select>
                  <select
                    data-testid="rbac-effect-select"
                    value={grantEffect}
                    onChange={(e) =>
                      setGrantEffect(e.target.value as "ALLOW" | "DENY" | "INHERITANCE_BLOCK")
                    }
                    style={inputStyle}
                  >
                    <option value="ALLOW">ALLOW</option>
                    <option value="DENY">DENY</option>
                    <option value="INHERITANCE_BLOCK">INHERITANCE_BLOCK</option>
                  </select>
                  <button type="submit" data-testid="create-rbac-grant-btn" style={primaryBtnStyle}>
                    {isFr ? "+ Ajouter la règle" : "+ Add rule"}
                  </button>
                </form>

                {rbacGrants.length === 0 ? (
                  <p
                    data-testid="iam-grants-empty-state"
                    style={{ margin: "10px 0 0 0", fontSize: "13px", color: "var(--color-muted-foreground)" }}
                  >
                    {isFr ? "Aucune règle d'habilitation personnalisée." : "No custom permission rule configured."}
                  </p>
                ) : (
                  <div style={{ display: "grid", gap: "6px", marginTop: "10px" }}>
                    {rbacGrants.map((g) => (
                      <div
                        key={g.id}
                        data-testid={`rbac-grant-row-${g.id}`}
                        style={{
                          padding: "8px 10px",
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--color-border)",
                          display: "flex",
                          justifyContent: "space-between",
                        }}
                      >
                        <span>
                          <strong>{g.subjectType}:{g.subjectId}</strong> → <code>{g.scopePath}</code>
                        </span>
                        <StatusBadge
                          label={`${g.verb} (${g.effect})`}
                          tone={g.effect === "ALLOW" ? "emerald" : "crimson"}
                          monospace
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          )}

          {activeTab === "ai-models" && (
            <section
              data-testid="settings-ai-models-section"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "14px" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <InferenceTierBadge
                  tier={selectedTier}
                  effort={selectedEffort}
                  labels={tierAndEffortLabels}
                />
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
                <input
                  type="text"
                  data-testid="llm-primary-model-input"
                  value={primaryModel}
                  onChange={(e) => setPrimaryModel(e.target.value)}
                  placeholder={isFr ? "Modèle primaire (ex: provider/model-id)..." : "Primary model..."}
                  style={{ ...inputStyle, flex: 1, minWidth: "200px" }}
                />
                <input
                  type="text"
                  data-testid="llm-secondary-model-input"
                  value={secondaryModel}
                  onChange={(e) => setSecondaryModel(e.target.value)}
                  placeholder={isFr ? "Modèle secondaire de secours..." : "Secondary fallback model..."}
                  style={{ ...inputStyle, flex: 1, minWidth: "200px" }}
                />
                <input
                  type="text"
                  data-testid="llm-family-input"
                  value={modelFamily}
                  onChange={(e) => setModelFamily(e.target.value)}
                  placeholder={isFr ? "Famille AD-10..." : "Model family..."}
                  style={inputStyle}
                />
                <button type="submit" data-testid="save-llm-tier-btn" style={primaryBtnStyle}>
                  {isFr ? "Enregistrer le palier" : "Save tier"}
                </button>
              </form>

              {llmTiers.length === 0 ? (
                <p
                  data-testid="llm-tiers-empty-state"
                  style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
                >
                  {isFr
                    ? "Aucun palier cognitif configuré. Associez les paliers simple / medium / complex à vos modèles IA."
                    : "No cognitive tier configured yet. Bind simple / medium / complex tiers to your AI models."}
                </p>
              ) : (
                <div style={{ display: "grid", gap: "8px" }}>
                  {llmTiers.map((item) => (
                    <div
                      key={item.tier}
                      data-testid={`llm-tier-row-${item.tier}`}
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
                        <strong>{item.tier}</strong> → <code>{item.primaryModel}</code> (secours: <code>{item.secondaryModel}</code>)
                      </span>
                      <StatusBadge
                        label={`${item.modelFamily} · ${item.defaultEffort}`}
                        tone="emerald"
                        monospace
                      />
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {activeTab === "connectors" && (
            <section
              data-testid="settings-connectors-section"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "14px" }}
            >
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
                  fieldLabel: isFr ? "Secret du connecteur (Write-Only)" : "Connector Secret (Write-Only)",
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
                  data-testid="connector-alias-input"
                  value={connAlias}
                  onChange={(e) => setConnAlias(e.target.value)}
                  placeholder={isFr ? "Alias du connecteur..." : "Connector alias..."}
                  style={inputStyle}
                />
                <input
                  type="text"
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
                <button type="submit" data-testid="save-connector-btn" style={primaryBtnStyle}>
                  {isFr ? "+ Enregistrer le connecteur" : "+ Save connector"}
                </button>
              </form>

              {datasources.length === 0 ? (
                <p
                  data-testid="connectors-empty-state"
                  style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
                >
                  {isFr
                    ? "Aucun connecteur configuré."
                    : "No connector configured yet."}
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
          )}

          {activeTab === "packs" && (
            <section
              data-testid="settings-packs-section"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "14px" }}
            >
              <form
                data-testid="register-pack-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!packKey.trim()) return;
                  registerPack({
                    packKey: packKey.trim(),
                    version: packVersion.trim() || "1.0.0",
                    scopePath: packScope.trim() || "GLOBAL",
                    status: "PUBLISHED",
                  });
                  setPackKey("");
                }}
                style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}
              >
                <input
                  type="text"
                  data-testid="pack-key-input"
                  value={packKey}
                  onChange={(e) => setPackKey(e.target.value)}
                  placeholder={isFr ? "Identifiant du Pack (ex: orcia-pack-sdlc)..." : "Pack key..."}
                  style={{ ...inputStyle, flex: 1, minWidth: "220px" }}
                />
                <input
                  type="text"
                  data-testid="pack-version-input"
                  value={packVersion}
                  onChange={(e) => setPackVersion(e.target.value)}
                  placeholder="SemVer (1.0.0)"
                  style={inputStyle}
                />
                <input
                  type="text"
                  data-testid="pack-scope-input"
                  value={packScope}
                  onChange={(e) => setPackScope(e.target.value)}
                  placeholder="Périmètre (GLOBAL)"
                  style={inputStyle}
                />
                <button type="submit" data-testid="save-pack-btn" style={primaryBtnStyle}>
                  {isFr ? "+ Activer le Pack" : "+ Activate Pack"}
                </button>
              </form>

              {packs.length === 0 ? (
                <p
                  data-testid="packs-empty-state"
                  style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
                >
                  {isFr
                    ? "Aucun Pack métier activé sur ce périmètre."
                    : "No business Pack activated on this scope yet."}
                </p>
              ) : (
                <div style={{ display: "grid", gap: "8px" }}>
                  {packs.map((p) => (
                    <div
                      key={`${p.packKey}@${p.version}`}
                      data-testid={`pack-row-${p.packKey}`}
                      style={{
                        padding: "8px 12px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <strong>
                        {p.packKey}@{p.version}
                      </strong>
                      <StatusBadge label={`${p.status} · ${p.scopePath}`} tone="emerald" monospace />
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {activeTab === "workflows" && (
            <section
              data-testid="settings-workflows-section"
              style={{ display: "flex", flexDirection: "column", gap: "14px" }}
            >
              <WorkflowTopGovernanceBar
                workflowKey={wfKey || "nouveau-workflow"}
                version={wfVersion}
                lifecycleStatus={wfStatus}
                prePromptSha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                requiredParams={wfParamsCsv ? wfParamsCsv.split(",").map((s) => s.trim()).filter(Boolean) : []}
                requiredMarkdownSections={
                  wfSectionsCsv ? wfSectionsCsv.split(",").map((s) => s.trim()).filter(Boolean) : []
                }
                triggers={["manual"]}
                activeTab={wfStatus}
                tabCounts={[
                  {
                    tab: "PUBLISHED",
                    label: "PUBLISHED",
                    count: workflows.filter((w) => w.status === "PUBLISHED").length,
                  },
                  {
                    tab: "DRAFT",
                    label: "DRAFT",
                    count: workflows.filter((w) => w.status === "DRAFT").length,
                  },
                  { tab: "TRASH", label: "TRASH", count: 0 },
                  { tab: "ACTIVE_RUNS", label: "ACTIVE_RUNS", count: 0 },
                  { tab: "PAUSED_ARBITRATION", label: "PAUSED_ARBITRATION", count: 0 },
                ]}
                onSelectTab={setWfStatus}
                onForkDraft={() => {
                  setWfVersion("1.1.0-draft");
                  setWfStatus("DRAFT");
                }}
                onPublishDraft={() => {
                  setWfStatus("PUBLISHED");
                }}
                labels={{
                  prePromptButton: copy.studioLabels.prePromptButton,
                  contractButton: copy.studioLabels.contractButton,
                  triggersButton: copy.studioLabels.triggersButton,
                  dryRunButton: copy.studioLabels.dryRunButton,
                  forkButton: copy.studioLabels.forkButton,
                  publishButton: copy.studioLabels.publishButton,
                  readOnlyPublishedHint: copy.studioLabels.readOnlyPublishedHint,
                }}
              />

              <form
                data-testid="create-workflow-form"
                className="orcia-bento-card"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!wfKey.trim() || !wfTitle.trim()) return;
                  upsertWorkflow({
                    workflowKey: wfKey.trim(),
                    title: wfTitle.trim(),
                    version: wfVersion.trim() || "1.0.0",
                    status: wfStatus === "PUBLISHED" ? "PUBLISHED" : "DRAFT",
                    prePrompt: wfPrePrompt.trim(),
                    prePromptSha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    requiredParams: wfParamsCsv
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                    requiredMarkdownSections: wfSectionsCsv
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                    triggers: ["manual"],
                    layers,
                  });
                  setWfKey("");
                  setWfTitle("");
                }}
                style={{ display: "flex", flexDirection: "column", gap: "10px" }}
              >
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  <input
                    type="text"
                    data-testid="workflow-key-input"
                    value={wfKey}
                    onChange={(e) => setWfKey(e.target.value)}
                    placeholder={isFr ? "Clé du workflow (ex: audit-architecture)..." : "Workflow key..."}
                    style={{ ...inputStyle, flex: 1, minWidth: "180px" }}
                  />
                  <input
                    type="text"
                    data-testid="workflow-title-input"
                    value={wfTitle}
                    onChange={(e) => setWfTitle(e.target.value)}
                    placeholder={isFr ? "Titre du workflow..." : "Workflow title..."}
                    style={{ ...inputStyle, flex: 1, minWidth: "180px" }}
                  />
                  <input
                    type="text"
                    data-testid="workflow-params-input"
                    value={wfParamsCsv}
                    onChange={(e) => setWfParamsCsv(e.target.value)}
                    placeholder={isFr ? "Paramètres requis (csv)..." : "Required params (csv)..."}
                    style={inputStyle}
                  />
                  <input
                    type="text"
                    data-testid="workflow-sections-input"
                    value={wfSectionsCsv}
                    onChange={(e) => setWfSectionsCsv(e.target.value)}
                    placeholder={isFr ? "Sections Markdown (csv)..." : "Markdown sections (csv)..."}
                    style={inputStyle}
                  />
                </div>
                <textarea
                  data-testid="workflow-preprompt-textarea"
                  value={wfPrePrompt}
                  onChange={(e) => setWfPrePrompt(e.target.value)}
                  rows={3}
                  placeholder={isFr ? "Pré-prompt système du workflow..." : "System pre-prompt..."}
                  style={inputStyle}
                />
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button type="submit" data-testid="save-workflow-btn" style={primaryBtnStyle}>
                    {isFr ? "+ Enregistrer le Workflow" : "+ Save Workflow"}
                  </button>
                </div>
              </form>

              <LayersInspectorPopover
                nodeId="subwf-studio"
                nodeTitle={isFr ? "Inspecteur de Couches du Sous-Workflow" : "Sub-Workflow Layers Inspector"}
                layers={layers}
                onToggleLayer={(layerId, nextEnabled) => {
                  setLayers((prev) =>
                    prev.map((item) =>
                      item.layerId === layerId ? { ...item, enabled: nextEnabled } : item,
                    ),
                  );
                }}
                labels={{
                  badgePrefix: copy.studioLabels.layersBadgePrefix,
                  inputsZoneTitle: copy.studioLabels.inputsZoneTitle,
                  capabilitiesZoneTitle: copy.studioLabels.capabilitiesZoneTitle,
                  deliverablesZoneTitle: copy.studioLabels.deliverablesZoneTitle,
                  enabledStatusLabel: copy.studioLabels.enabledStatusLabel,
                  skippedStatusLabel: copy.studioLabels.skippedStatusLabel,
                  deleteActionLabel: copy.studioLabels.deleteActionLabel,
                }}
              />
            </section>
          )}

          {activeTab === "audit" && (
            <section
              data-testid="settings-audit-section"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "10px" }}
            >
              <h2 style={{ margin: 0, fontSize: "15px" }}>
                {isFr
                  ? "Journal des Modifications de Configuration (Outbox)"
                  : "Configuration Change Log (Outbox)"}
              </h2>
              {auditEvents.length === 0 ? (
                <p
                  data-testid="audit-events-empty-state"
                  style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
                >
                  {isFr
                    ? "Aucun événement de paramétrage enregistré."
                    : "No configuration event recorded yet."}
                </p>
              ) : (
                <div style={{ display: "grid", gap: "6px" }}>
                  {auditEvents.map((ev) => (
                    <div
                      key={ev.id}
                      data-testid={`audit-event-row-${ev.id}`}
                      style={{
                        padding: "8px 10px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span>{ev.summary}</span>
                      <StatusBadge label={ev.eventType} tone="cobalt" monospace />
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      </PermissionGuard>
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings",
  validateSearch: validateOrciaRouteSearch,
  component: SettingsHubView,
});
