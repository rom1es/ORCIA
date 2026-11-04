import {
  ContextualInfoTriggerButton,
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
import { useShellNavigation } from "../components/ShellContainer";
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
  const { openHelpSection } = useShellNavigation();
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
    removeOrgUnit,
    addRbacGrant,
    removeRbacGrant,
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
  const [orgParentId, setOrgParentId] = useState("scope-global");
  const [orgDeleteFeedback, setOrgDeleteFeedback] = useState<string | null>(null);
  const [confirmDeleteOrgId, setConfirmDeleteOrgId] = useState<string | null>(null);

  const [grantSubjectType, setGrantSubjectType] = useState<"ROLE" | "USER">("ROLE");
  const [grantSubjectId, setGrantSubjectId] = useState("TEAM_LEAD");
  const [grantScopePath, setGrantScopePath] = useState("GLOBAL");
  const [grantVerb, setGrantVerb] = useState<UiPermissionVerb>("execute");
  const [grantSelectedVerbs, setGrantSelectedVerbs] = useState<readonly UiPermissionVerb[]>([
    "execute",
  ]);
  const [grantEffect, setGrantEffect] = useState<"ALLOW" | "DENY" | "INHERITANCE_BLOCK">("ALLOW");
  const [selectedGrantIds, setSelectedGrantIds] = useState<readonly string[]>([]);

  const verbDescriptions: Record<UiPermissionVerb, string> = isFr
    ? {
        create: "Créer (create)",
        read: "Lire / Voir les secrets (read)",
        update: "Modifier (update)",
        delete: "Supprimer (delete)",
        execute: "Exécuter / Utiliser (execute)",
        grant: "Déléguer des droits (grant)",
      }
    : {
        create: "Create (create)",
        read: "Read / View secrets (read)",
        update: "Update (update)",
        delete: "Delete (delete)",
        execute: "Execute / Use (execute)",
        grant: "Delegate rights (grant)",
      };

  const effectDescriptions: Record<"ALLOW" | "DENY" | "INHERITANCE_BLOCK", string> = isFr
    ? {
        ALLOW: "Autoriser (ALLOW) — Accorde les actions cochées sur la cible",
        DENY: "Interdire (DENY) — Bloque explicitement (prioritaire sur toute autorisation)",
        INHERITANCE_BLOCK:
          "Couper l'héritage (INHERITANCE_BLOCK) — Annule les droits hérités des niveaux parents (Organisation / BU) sur ce périmètre",
      }
    : {
        ALLOW: "Allow (ALLOW) — Grants the checked actions on the target scope",
        DENY: "Deny (DENY) — Explicitly blocks (overrides any allow rule)",
        INHERITANCE_BLOCK:
          "Block inheritance (INHERITANCE_BLOCK) — Clears permissions inherited from parent scopes (Organization / BU) at this level",
      };

  const allVerbsChecked = allowedVerbs.every((v) => grantSelectedVerbs.includes(v));
  const allGrantsChecked =
    rbacGrants.length > 0 && rbacGrants.every((g) => selectedGrantIds.includes(g.id));

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

  const dangerBtnStyle: React.CSSProperties = {
    padding: "5px 10px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--color-border)",
    backgroundColor: "var(--color-surface-card)",
    color: "var(--color-foreground)",
    fontSize: "12px",
    fontWeight: 600,
    cursor: "pointer",
  };

  const buUnits = orgUnits.filter((u) => u.level === "BU");

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
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <h2 style={{ margin: 0, fontSize: "15px" }}>
                    {isFr
                      ? "1. Structure de l'Organisation (Directions / BU & Espaces)"
                      : "1. Organization Structure (Divisions / BUs & Workspaces)"}
                  </h2>
                  <ContextualInfoTriggerButton
                    sectionId="iam-org-tree"
                    label={
                      isFr
                        ? "Comprendre la structure Directions (BU) et Espaces"
                        : "Understand Divisions (BUs) and Workspaces structure"
                    }
                    onOpenHelpSection={openHelpSection}
                  />
                </div>
                <form
                  data-testid="create-org-unit-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!orgName.trim()) return;
                    const resolvedParentId =
                      orgLevel === "BU" ? "scope-global" : orgParentId || "scope-global";
                    addOrgUnit({
                      name: orgName.trim(),
                      slug: orgSlug.trim() || orgName.trim().toLowerCase().replace(/\s+/g, "-"),
                      level: orgLevel,
                      parentId: resolvedParentId,
                    });
                    setOrgName("");
                    setOrgSlug("");
                    setOrgDeleteFeedback(null);
                  }}
                  style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "10px", alignItems: "center" }}
                >
                  <select
                    data-testid="org-unit-level-select"
                    value={orgLevel}
                    onChange={(e) => {
                      const nextLevel = e.target.value as "BU" | "TEAM";
                      setOrgLevel(nextLevel);
                      if (nextLevel === "BU") {
                        setOrgParentId("scope-global");
                      } else if (buUnits.length > 0 && orgParentId === "scope-global") {
                        setOrgParentId(buUnits[0]!.id);
                      }
                    }}
                    style={inputStyle}
                  >
                    <option value="BU">BU (Business Unit / Direction)</option>
                    <option value="TEAM">{isFr ? "Espace (Équipe)" : "Space (Team)"}</option>
                  </select>

                  {orgLevel === "TEAM" && (
                    <select
                      data-testid="org-unit-parent-select"
                      aria-label={isFr ? "BU parente de rattachement" : "Parent BU"}
                      value={orgParentId}
                      onChange={(e) => setOrgParentId(e.target.value)}
                      style={inputStyle}
                    >
                      <option value="scope-global">
                        {isFr ? "Rattachement : Plateforme Globale" : "Parent: Global Platform"}
                      </option>
                      {buUnits.map((bu) => (
                        <option key={bu.id} value={bu.id}>
                          {isFr ? `Rattaché à la BU : ${bu.name}` : `Attached to BU: ${bu.name}`}
                        </option>
                      ))}
                    </select>
                  )}

                  <input
                    type="text"
                    data-testid="org-unit-name-input"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder={
                      orgLevel === "BU"
                        ? isFr
                          ? "Nom de la BU (ex: Direction Produit)..."
                          : "BU name..."
                        : isFr
                          ? "Nom de l'Espace / Équipe..."
                          : "Space / Team name..."
                    }
                    style={{ ...inputStyle, flex: 1, minWidth: "180px" }}
                  />
                  <input
                    type="text"
                    data-testid="org-unit-slug-input"
                    value={orgSlug}
                    onChange={(e) => setOrgSlug(e.target.value)}
                    placeholder={isFr ? "Identifiant court / Slug (optionnel)..." : "Slug (optional)..."}
                    style={inputStyle}
                  />
                  <button type="submit" data-testid="create-org-unit-btn" style={primaryBtnStyle}>
                    {isFr ? "+ Créer l'unité" : "+ Create unit"}
                  </button>
                </form>

                {orgDeleteFeedback && (
                  <div
                    role="alert"
                    data-testid="org-unit-delete-feedback"
                    style={{
                      marginTop: "10px",
                      padding: "8px 12px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-border)",
                      backgroundColor: "var(--color-surface-card)",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    ⚠️ {orgDeleteFeedback}
                  </div>
                )}

                {orgUnits.length === 0 ? (
                  <p
                    data-testid="iam-org-units-empty-state"
                    style={{ margin: "10px 0 0 0", fontSize: "13px", color: "var(--color-muted-foreground)" }}
                  >
                    {isFr
                      ? "Aucune unité d'organisation (BU ou Espace) configurée."
                      : "No organization unit (BU or Space) configured yet."}
                  </p>
                ) : (
                  <div style={{ display: "grid", gap: "6px", marginTop: "10px" }}>
                    {orgUnits.map((u) => {
                      const parentNode = orgUnits.find((p) => p.id === u.parentId);
                      const childCount = orgUnits.filter((c) => c.parentId === u.id).length;
                      const levelDisplay =
                        u.level === "TEAM" ? (isFr ? "ESPACE" : "SPACE") : "BU";
                      const isConfirming = confirmDeleteOrgId === u.id;
                      return (
                        <div
                          key={u.id}
                          data-testid={`org-unit-row-${u.id}`}
                          style={{
                            padding: "8px 10px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--color-border)",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            flexWrap: "wrap",
                            gap: "8px",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                            <strong>{u.name}</strong>
                            <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
                              {parentNode
                                ? isFr
                                  ? `↳ Rattaché à la BU : ${parentNode.name}`
                                  : `↳ Parent BU: ${parentNode.name}`
                                : isFr
                                  ? "↳ Niveau Racine (Plateforme Globale)"
                                  : "↳ Root Level (Global Platform)"}
                            </span>
                            {childCount > 0 && (
                              <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                                ({childCount} {isFr ? "Espace(s) rattaché(s)" : "attached Space(s)"})
                              </span>
                            )}
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <StatusBadge label={`${levelDisplay} · ${u.slug}`} tone="cobalt" monospace />
                            {!isConfirming ? (
                              <button
                                type="button"
                                data-testid={`delete-org-unit-btn-${u.id}`}
                                onClick={() => {
                                  setOrgDeleteFeedback(null);
                                  setConfirmDeleteOrgId(u.id);
                                }}
                                style={dangerBtnStyle}
                              >
                                {isFr ? "Supprimer" : "Delete"}
                              </button>
                            ) : (
                              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                                  {isFr
                                    ? "Attention : vérifie l'absence d'éléments orphelins"
                                    : "Warning: checks for orphan dependencies"}
                                </span>
                                <button
                                  type="button"
                                  data-testid={`confirm-delete-org-unit-btn-${u.id}`}
                                  onClick={() => {
                                    const res = removeOrgUnit(u.id);
                                    if (!res.deleted && res.blockedReason) {
                                      setOrgDeleteFeedback(res.blockedReason);
                                    } else {
                                      setOrgDeleteFeedback(null);
                                    }
                                    setConfirmDeleteOrgId(null);
                                  }}
                                  style={dangerBtnStyle}
                                >
                                  {isFr ? "Confirmer la suppression" : "Confirm delete"}
                                </button>
                                <button
                                  type="button"
                                  data-testid={`cancel-delete-org-unit-btn-${u.id}`}
                                  onClick={() => setConfirmDeleteOrgId(null)}
                                  style={dangerBtnStyle}
                                >
                                  {isFr ? "Annuler" : "Cancel"}
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <h2 style={{ margin: 0, fontSize: "15px" }}>
                    {isFr
                      ? "2. Attribuer et Gérer les Règles d'Habilitation"
                      : "2. Grant and Manage Permission Rules"}
                  </h2>
                  <ContextualInfoTriggerButton
                    sectionId="iam-role-grants"
                    label={
                      isFr
                        ? "Comprendre comment attribuer une règle d'habilitation (Qui ? et Sur quoi ?)"
                        : "Understand how to grant a permission rule (Who? and On what?)"
                    }
                    onOpenHelpSection={openHelpSection}
                  />
                </div>

                <form
                  data-testid="create-rbac-grant-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!grantSubjectId.trim() || !grantScopePath.trim()) return;
                    const verbsToGrant =
                      grantSelectedVerbs.length > 0 ? grantSelectedVerbs : [grantVerb];
                    for (const v of verbsToGrant) {
                      addRbacGrant({
                        subjectType: grantSubjectType,
                        subjectId: grantSubjectId.trim(),
                        scopePath: grantScopePath.trim(),
                        verb: v,
                        effect: grantEffect,
                      });
                    }
                  }}
                  style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "10px" }}
                >
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "flex-end" }}>
                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
                      <span style={{ fontWeight: 600 }}>
                        {isFr ? "Type de bénéficiaire" : "Beneficiary type"}
                      </span>
                      <select
                        data-testid="rbac-subject-type-select"
                        value={grantSubjectType}
                        onChange={(e) => setGrantSubjectType(e.target.value as "ROLE" | "USER")}
                        style={inputStyle}
                      >
                        <option value="ROLE">{isFr ? "Rôle (ROLE)" : "Role (ROLE)"}</option>
                        <option value="USER">{isFr ? "Utilisateur (USER)" : "User (USER)"}</option>
                      </select>
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", flex: 1, minWidth: "180px" }}>
                      <span style={{ fontWeight: 600 }}>
                        {isFr
                          ? "Qui ? (Bénéficiaire : Rôle ou Utilisateur)"
                          : "Who? (Beneficiary: Role or User)"}
                      </span>
                      <input
                        type="text"
                        data-testid="rbac-subject-input"
                        value={grantSubjectId}
                        onChange={(e) => setGrantSubjectId(e.target.value)}
                        placeholder={
                          isFr
                            ? "Ex: TEAM_LEAD, ARCHITECT ou email utilisateur..."
                            : "e.g. TEAM_LEAD, ARCHITECT or user email..."
                        }
                        style={inputStyle}
                      />
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", flex: 1, minWidth: "220px" }}>
                      <span style={{ fontWeight: 600 }}>
                        {isFr
                          ? "Sur quoi ? (Périmètre cible : GLOBAL, BU, Espace)"
                          : "On what? (Target scope: GLOBAL, BU, Space)"}
                      </span>
                      <div style={{ display: "flex", gap: "6px" }}>
                        {orgUnits.length > 0 && (
                          <select
                            data-testid="rbac-scope-preset-select"
                            aria-label={isFr ? "Choisir un périmètre existant" : "Select existing scope"}
                            value={
                              grantScopePath === "GLOBAL" ||
                              orgUnits.some((u) => u.slug === grantScopePath)
                                ? grantScopePath
                                : ""
                            }
                            onChange={(e) => {
                              if (e.target.value) {
                                setGrantScopePath(e.target.value);
                              }
                            }}
                            style={inputStyle}
                          >
                            <option value="GLOBAL">GLOBAL (Plateforme)</option>
                            {orgUnits.map((u) => (
                              <option key={u.id} value={u.slug}>
                                {u.level === "TEAM" ? "Espace" : "BU"} : {u.name} ({u.slug})
                              </option>
                            ))}
                          </select>
                        )}
                        <input
                          type="text"
                          data-testid="rbac-scope-input"
                          value={grantScopePath}
                          onChange={(e) => setGrantScopePath(e.target.value)}
                          placeholder={isFr ? "Périmètre (ex: GLOBAL ou slug d'Espace)" : "Scope (e.g. GLOBAL)"}
                          style={{ ...inputStyle, flex: 1 }}
                        />
                      </div>
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
                      <span style={{ fontWeight: 600 }}>
                        {isFr ? "Action principale" : "Primary action"}
                      </span>
                      <select
                        data-testid="rbac-verb-select"
                        value={grantVerb}
                        onChange={(e) => {
                          const v = e.target.value as UiPermissionVerb;
                          setGrantVerb(v);
                          setGrantSelectedVerbs([v]);
                        }}
                        style={inputStyle}
                      >
                        {allowedVerbs.map((v) => (
                          <option key={v} value={v}>
                            {verbDescriptions[v]}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
                      <span style={{ fontWeight: 600 }}>
                        {isFr ? "Effet de la règle" : "Rule effect"}
                      </span>
                      <select
                        data-testid="rbac-effect-select"
                        value={grantEffect}
                        onChange={(e) =>
                          setGrantEffect(e.target.value as "ALLOW" | "DENY" | "INHERITANCE_BLOCK")
                        }
                        style={inputStyle}
                      >
                        <option value="ALLOW">{effectDescriptions.ALLOW}</option>
                        <option value="DENY">{effectDescriptions.DENY}</option>
                        <option value="INHERITANCE_BLOCK">
                          {effectDescriptions.INHERITANCE_BLOCK}
                        </option>
                      </select>
                    </label>

                    <button type="submit" data-testid="create-rbac-grant-btn" style={primaryBtnStyle}>
                      {isFr ? "+ Ajouter la règle" : "+ Add rule"}
                    </button>
                  </div>

                  {/* Cases à cocher des actions d'habilitation avec l'entrée "Tous" */}
                  <div
                    data-testid="rbac-verbs-checkbox-group"
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "12px",
                      alignItems: "center",
                      padding: "8px 10px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-border)",
                      fontSize: "12px",
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>
                      {isFr ? "Habilitations à attribuer :" : "Permissions to grant:"}
                    </span>
                    <label style={{ display: "inline-flex", alignItems: "center", gap: "5px", fontWeight: 600, cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        data-testid="rbac-verb-checkbox-all"
                        checked={allVerbsChecked}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setGrantSelectedVerbs([...allowedVerbs]);
                          } else {
                            setGrantSelectedVerbs([grantVerb]);
                          }
                        }}
                      />
                      <span>{isFr ? "Tous" : "All"}</span>
                    </label>
                    {allowedVerbs.map((v) => {
                      const checked = grantSelectedVerbs.includes(v);
                      return (
                        <label
                          key={v}
                          style={{ display: "inline-flex", alignItems: "center", gap: "5px", cursor: "pointer" }}
                        >
                          <input
                            type="checkbox"
                            data-testid={`rbac-verb-checkbox-${v}`}
                            checked={checked}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setGrantSelectedVerbs((prev) =>
                                  prev.includes(v) ? prev : [...prev, v],
                                );
                              } else {
                                setGrantSelectedVerbs((prev) =>
                                  prev.filter((item) => item !== v),
                                );
                              }
                            }}
                          />
                          <span>{verbDescriptions[v]}</span>
                        </label>
                      );
                    })}
                  </div>
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
                    <div
                      data-testid="rbac-grants-bulk-toolbar"
                      style={{
                        padding: "6px 10px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        fontSize: "12px",
                      }}
                    >
                      <label style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 600, cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          data-testid="rbac-grants-select-all-checkbox"
                          checked={allGrantsChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedGrantIds(rbacGrants.map((g) => g.id));
                            } else {
                              setSelectedGrantIds([]);
                            }
                          }}
                        />
                        <span>{isFr ? "Tous (Tout sélectionner)" : "All (Select all)"}</span>
                      </label>
                      {selectedGrantIds.length > 0 && (
                        <button
                          type="button"
                          data-testid="rbac-grants-bulk-delete-btn"
                          onClick={() => {
                            for (const id of selectedGrantIds) {
                              removeRbacGrant(id);
                            }
                            setSelectedGrantIds([]);
                          }}
                          style={dangerBtnStyle}
                        >
                          {isFr
                            ? `Supprimer la sélection (${selectedGrantIds.length})`
                            : `Delete selected (${selectedGrantIds.length})`}
                        </button>
                      )}
                    </div>

                    {rbacGrants.map((g) => {
                      const isRowChecked = selectedGrantIds.includes(g.id);
                      return (
                        <div
                          key={g.id}
                          data-testid={`rbac-grant-row-${g.id}`}
                          style={{
                            padding: "8px 10px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--color-border)",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            flexWrap: "wrap",
                            gap: "8px",
                          }}
                        >
                          <label style={{ display: "inline-flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                            <input
                              type="checkbox"
                              data-testid={`rbac-grant-checkbox-${g.id}`}
                              checked={isRowChecked}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedGrantIds((prev) =>
                                    prev.includes(g.id) ? prev : [...prev, g.id],
                                  );
                                } else {
                                  setSelectedGrantIds((prev) =>
                                    prev.filter((id) => id !== g.id),
                                  );
                                }
                              }}
                            />
                            <span>
                              <strong>
                                {g.subjectType === "ROLE"
                                  ? isFr
                                    ? "Rôle"
                                    : "Role"
                                  : isFr
                                    ? "Utilisateur"
                                    : "User"}{" "}
                                ({g.subjectType}:{g.subjectId})
                              </strong>{" "}
                              → {isFr ? "Périmètre cible :" : "Target scope:"}{" "}
                              <code>{g.scopePath}</code>
                            </span>
                          </label>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <StatusBadge
                              label={`${g.verb} (${g.effect})`}
                              tone={g.effect === "ALLOW" ? "emerald" : "crimson"}
                              monospace
                            />
                            <button
                              type="button"
                              data-testid={`delete-rbac-grant-btn-${g.id}`}
                              onClick={() => {
                                removeRbacGrant(g.id);
                                setSelectedGrantIds((prev) => prev.filter((id) => id !== g.id));
                              }}
                              style={dangerBtnStyle}
                            >
                              {isFr ? "Supprimer" : "Delete"}
                            </button>
                          </div>
                        </div>
                      );
                    })}
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
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <InferenceTierBadge
                    tier={selectedTier}
                    effort={selectedEffort}
                    labels={tierAndEffortLabels}
                  />
                  <ContextualInfoTriggerButton
                    sectionId="ai-models-overview"
                    label={
                      isFr
                        ? "Comprendre les niveaux de modèles IA et les fournisseurs indépendants"
                        : "Understand AI model levels and independent providers"
                    }
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
                <input
                  type="text"
                  data-testid="llm-primary-model-input"
                  value={primaryModel}
                  onChange={(e) => setPrimaryModel(e.target.value)}
                  placeholder={isFr ? "Modèle principal (ex: fournisseur/modèle)..." : "Primary model..."}
                  style={{ ...inputStyle, flex: 1, minWidth: "200px" }}
                />
                <input
                  type="text"
                  data-testid="llm-secondary-model-input"
                  value={secondaryModel}
                  onChange={(e) => setSecondaryModel(e.target.value)}
                  placeholder={isFr ? "Modèle secondaire de secours..." : "Backup model..."}
                  style={{ ...inputStyle, flex: 1, minWidth: "200px" }}
                />
                <input
                  type="text"
                  data-testid="llm-family-input"
                  value={modelFamily}
                  onChange={(e) => setModelFamily(e.target.value)}
                  placeholder={isFr ? "Fournisseur IA (ex: Mistral, Anthropic)..." : "AI provider..."}
                  style={inputStyle}
                />
                <button type="submit" data-testid="save-llm-tier-btn" style={primaryBtnStyle}>
                  {isFr ? "Enregistrer le niveau" : "Save level"}
                </button>
              </form>

              {llmTiers.length === 0 ? (
                <p
                  data-testid="llm-tiers-empty-state"
                  style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
                >
                  {isFr
                    ? "Aucun modèle IA configuré. Associez les niveaux simple / standard / approfondi à vos modèles IA."
                    : "No AI model configured yet. Assign simple / standard / in-depth levels to your AI models."}
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
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h2 style={{ margin: 0, fontSize: "15px" }}>
                  {isFr
                    ? "Journal des Modifications de Configuration"
                    : "Configuration Change Log"}
                </h2>
                <ContextualInfoTriggerButton
                  sectionId="audit-overview"
                  label={
                    isFr
                      ? "Comprendre le journal d'activité et le suivi des modifications"
                      : "Understand the activity log and configuration change tracking"
                  }
                  onOpenHelpSection={openHelpSection}
                />
              </div>
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
