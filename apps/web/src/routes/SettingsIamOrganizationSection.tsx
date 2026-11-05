import {
  ContextualInfoTriggerButton,
  StatusBadge,
  type ControlCenterWorkspaceGovItem,
  type UiPermissionVerb,
} from "@orcia/ui";
import React, { useState } from "react";
import type { ConfiguredOrgUnit, ConfiguredRbacGrant } from "../components/platformSetupStore";
import { SettingsOrganizationUnitsBlock } from "./SettingsOrganizationUnitsBlock";

export interface SettingsIamOrganizationSectionProps {
  readonly isFr: boolean;
  readonly allowedVerbs: readonly UiPermissionVerb[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly addOrgUnit: (input: Omit<ConfiguredOrgUnit, "id">) => void;
  readonly removeOrgUnit: (orgUnitId: string) => {
    readonly deleted: boolean;
    readonly blockedReason: string | null;
  };
  readonly addRbacGrant: (input: Omit<ConfiguredRbacGrant, "id">) => void;
  readonly removeRbacGrant: (grantId: string) => void;
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

export function SettingsIamOrganizationSection({
  isFr,
  allowedVerbs,
  orgUnits,
  workspaces,
  rbacGrants,
  openHelpSection,
  addOrgUnit,
  removeOrgUnit,
  addRbacGrant,
  removeRbacGrant,
}: SettingsIamOrganizationSectionProps) {
  const [grantSubjectType, setGrantSubjectType] = useState<"ROLE" | "USER">("ROLE");
  const [grantSubjectId, setGrantSubjectId] = useState("TEAM_LEAD");
  const [grantScopePath, setGrantScopePath] = useState("GLOBAL");
  const [grantSelectedVerbs, setGrantSelectedVerbs] = useState<readonly UiPermissionVerb[]>(["execute"]);
  const [grantEffect, setGrantEffect] = useState<"ALLOW" | "DENY" | "INHERITANCE_BLOCK">("ALLOW");
  const [selectedGrantIds, setSelectedGrantIds] = useState<readonly string[]>([]);

  const hasNoKnownOrganization = orgUnits.length === 0 && workspaces.length === 0;

  const verbDescriptions: Record<UiPermissionVerb, string> = isFr
    ? {
        create: "Créer",
        read: "Lire / Voir les secrets",
        update: "Modifier",
        delete: "Supprimer",
        execute: "Exécuter / Utiliser",
        grant: "Déléguer des droits",
      }
    : {
        create: "Create",
        read: "Read / View secrets",
        update: "Update",
        delete: "Delete",
        execute: "Execute / Use",
        grant: "Delegate rights",
      };

  const effectDescriptions: Record<"ALLOW" | "DENY" | "INHERITANCE_BLOCK", string> = isFr
    ? {
        ALLOW: "Autoriser — Accorde les actions cochées sur le périmètre choisi",
        DENY: "Interdire — Bloque explicitement ces actions (prioritaire sur toute autorisation)",
        INHERITANCE_BLOCK: "Isoler ce périmètre — N'applique pas les droits hérités de la Direction parente",
      }
    : {
        ALLOW: "Allow — Grants the checked actions on the selected scope",
        DENY: "Deny — Explicitly blocks these actions (overrides any allow rule)",
        INHERITANCE_BLOCK: "Isolate this scope — Does not apply permissions inherited from the parent division",
      };

  const effectBadgeLabels: Record<"ALLOW" | "DENY" | "INHERITANCE_BLOCK", string> = isFr
    ? { ALLOW: "Autorisé", DENY: "Interdit", INHERITANCE_BLOCK: "Périmètre isolé" }
    : { ALLOW: "Allowed", DENY: "Denied", INHERITANCE_BLOCK: "Isolated scope" };

  const allVerbsChecked = allowedVerbs.every((v) => grantSelectedVerbs.includes(v));
  const allGrantsChecked = rbacGrants.length > 0 && rbacGrants.every((g) => selectedGrantIds.includes(g.id));

  const formatTargetScopeLabel = (scopePath: string): string => {
    if (scopePath === "GLOBAL") return isFr ? "Plateforme entière" : "Entire platform";
    const matchedUnit = orgUnits.find((u) => u.slug === scopePath || u.id === scopePath);
    if (matchedUnit) {
      const kind = matchedUnit.level === "TEAM" ? (isFr ? "Espace" : "Space") : "BU";
      return `${kind} : ${matchedUnit.name} (${matchedUnit.slug})`;
    }
    const matchedWs = workspaces.find((w) => w.name === scopePath);
    if (matchedWs) return `${isFr ? "Espace" : "Space"} : ${matchedWs.name}`;
    return scopePath;
  };

  return (
    <section
      data-testid="settings-iam-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <SettingsOrganizationUnitsBlock
        isFr={isFr}
        orgUnits={orgUnits}
        openHelpSection={openHelpSection}
        addOrgUnit={addOrgUnit}
        removeOrgUnit={removeOrgUnit}
      />

      <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <h2 style={{ margin: 0, fontSize: "15px" }}>
            {isFr ? "2. Attribuer et Gérer les Règles d'Habilitation" : "2. Grant and Manage Permission Rules"}
          </h2>
          <ContextualInfoTriggerButton
            sectionId="iam-role-grants"
            label={isFr ? "Comprendre comment attribuer une règle d'habilitation (Qui ? et Sur quoi ?)" : "Understand how to grant a permission rule (Who? and On what?)"}
            onOpenHelpSection={openHelpSection}
          />
        </div>

        {hasNoKnownOrganization && (
          <p
            data-testid="rbac-grants-disabled-no-org-hint"
            style={{
              margin: "8px 0 0 0",
              padding: "8px 12px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-card)",
              fontSize: "12px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {isFr
              ? "Créez d'abord au moins une Direction (BU) ou un Espace dans la section 1 ci-dessus avant de pouvoir attribuer des règles d'habilitation."
              : "Create at least one Division (BU) or Space in section 1 above before granting permission rules."}
          </p>
        )}

        <form
          data-testid="create-rbac-grant-form"
          aria-disabled={hasNoKnownOrganization}
          onSubmit={(e) => {
            e.preventDefault();
            if (hasNoKnownOrganization || !grantSubjectId.trim() || !grantScopePath.trim() || grantSelectedVerbs.length === 0) return;
            for (const v of grantSelectedVerbs) {
              addRbacGrant({ subjectType: grantSubjectType, subjectId: grantSubjectId.trim(), scopePath: grantScopePath.trim(), verb: v, effect: grantEffect });
            }
          }}
          style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "10px", opacity: hasNoKnownOrganization ? 0.55 : 1 }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "flex-end" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
              <span style={{ fontWeight: 600 }}>{isFr ? "Type de bénéficiaire" : "Beneficiary type"}</span>
              <select data-testid="rbac-subject-type-select" disabled={hasNoKnownOrganization} value={grantSubjectType} onChange={(e) => setGrantSubjectType(e.target.value as "ROLE" | "USER")} style={inputStyle}>
                <option value="ROLE">{isFr ? "Rôle" : "Role"}</option>
                <option value="USER">{isFr ? "Utilisateur" : "User"}</option>
              </select>
            </label>

            <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", flex: 1, minWidth: "180px" }}>
              <span style={{ fontWeight: 600 }}>{isFr ? "Qui ? (Bénéficiaire : Rôle ou Utilisateur)" : "Who? (Beneficiary: Role or User)"}</span>
              <input
                type="text"
                data-testid="rbac-subject-input"
                disabled={hasNoKnownOrganization}
                value={grantSubjectId}
                onChange={(e) => setGrantSubjectId(e.target.value)}
                placeholder={isFr ? "Ex: Product Manager, Architecte ou email..." : "e.g. Product Manager, Architect..."}
                style={inputStyle}
              />
            </label>

            <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", flex: 1, minWidth: "220px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <label htmlFor="rbac-scope-preset-select" style={{ fontWeight: 600 }}>{isFr ? "Sur quoi ? (Périmètre cible)" : "On what? (Target scope)"}</label>
                <ContextualInfoTriggerButton
                  sectionId="iam-target-scope"
                  label={isFr ? "Comprendre ce qu'est le Périmètre cible (Sur quoi ?)" : "Understand what Target scope (On what?) means"}
                  onOpenHelpSection={openHelpSection}
                />
              </div>
              <select
                id="rbac-scope-preset-select"
                data-testid="rbac-scope-preset-select"
                aria-label={isFr ? "Sur quoi ? (Périmètre cible)" : "On what? (Target scope)"}
                disabled={hasNoKnownOrganization}
                value={grantScopePath}
                onChange={(e) => setGrantScopePath(e.target.value)}
                style={inputStyle}
              >
                <option value="GLOBAL">{isFr ? "Plateforme entière" : "Entire platform"}</option>
                {orgUnits.map((u) => (
                  <option key={u.id} value={u.slug}>
                    {u.level === "TEAM"
                      ? isFr ? `Espace : ${u.name} (${u.slug})` : `Space: ${u.name} (${u.slug})`
                      : isFr ? `Direction (BU) : ${u.name} (${u.slug})` : `Division (BU): ${u.name} (${u.slug})`}
                  </option>
                ))}
                {workspaces
                  .filter((ws) => !orgUnits.some((u) => u.name === ws.name || u.slug === ws.name))
                  .map((ws) => (
                    <option key={ws.name} value={ws.name}>{isFr ? `Espace : ${ws.name}` : `Space: ${ws.name}`}</option>
                  ))}
              </select>
            </div>

            <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
              <span style={{ fontWeight: 600 }}>{isFr ? "Effet de la règle" : "Rule effect"}</span>
              <select data-testid="rbac-effect-select" disabled={hasNoKnownOrganization} value={grantEffect} onChange={(e) => setGrantEffect(e.target.value as "ALLOW" | "DENY" | "INHERITANCE_BLOCK")} style={inputStyle}>
                <option value="ALLOW">{effectDescriptions.ALLOW}</option>
                <option value="DENY">{effectDescriptions.DENY}</option>
                <option value="INHERITANCE_BLOCK">{effectDescriptions.INHERITANCE_BLOCK}</option>
              </select>
            </label>

            <button
              type="submit"
              data-testid="create-rbac-grant-btn"
              disabled={hasNoKnownOrganization || grantSelectedVerbs.length === 0}
              style={{ ...primaryBtnStyle, cursor: hasNoKnownOrganization ? "not-allowed" : "pointer" }}
            >
              {isFr ? "+ Ajouter la règle" : "+ Add rule"}
            </button>
          </div>

          <div
            data-testid="rbac-verbs-checkbox-group"
            style={{ display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "12px" }}
          >
            <span style={{ fontWeight: 600 }}>{isFr ? "Habilitations à attribuer :" : "Permissions to grant:"}</span>
            <label style={{ display: "inline-flex", alignItems: "center", gap: "5px", fontWeight: 600, cursor: hasNoKnownOrganization ? "not-allowed" : "pointer" }}>
              <input
                type="checkbox"
                data-testid="rbac-verb-checkbox-all"
                disabled={hasNoKnownOrganization}
                checked={allVerbsChecked}
                onChange={(e) => setGrantSelectedVerbs(e.target.checked ? [...allowedVerbs] : ["execute"])}
              />
              <span>{isFr ? "Tous" : "All"}</span>
            </label>
            {allowedVerbs.map((v) => (
              <label key={v} style={{ display: "inline-flex", alignItems: "center", gap: "5px", cursor: hasNoKnownOrganization ? "not-allowed" : "pointer" }}>
                <input
                  type="checkbox"
                  data-testid={`rbac-verb-checkbox-${v}`}
                  disabled={hasNoKnownOrganization}
                  checked={grantSelectedVerbs.includes(v)}
                  onChange={(e) =>
                    setGrantSelectedVerbs((prev) => (e.target.checked ? (prev.includes(v) ? prev : [...prev, v]) : prev.filter((item) => item !== v)))
                  }
                />
                <span>{verbDescriptions[v]}</span>
              </label>
            ))}
          </div>
        </form>

        {rbacGrants.length === 0 ? (
          <p data-testid="iam-grants-empty-state" style={{ margin: "10px 0 0 0", fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr ? "Aucune règle d'habilitation personnalisée." : "No custom permission rule configured."}
          </p>
        ) : (
          <div style={{ display: "grid", gap: "6px", marginTop: "10px" }}>
            <div
              data-testid="rbac-grants-bulk-toolbar"
              style={{ padding: "6px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px" }}
            >
              <label style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 600, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  data-testid="rbac-grants-select-all-checkbox"
                  checked={allGrantsChecked}
                  onChange={(e) => setSelectedGrantIds(e.target.checked ? rbacGrants.map((g) => g.id) : [])}
                />
                <span>{isFr ? "Tous (Tout sélectionner)" : "All (Select all)"}</span>
              </label>
              {selectedGrantIds.length > 0 && (
                <button
                  type="button"
                  data-testid="rbac-grants-bulk-delete-btn"
                  onClick={() => {
                    for (const id of selectedGrantIds) removeRbacGrant(id);
                    setSelectedGrantIds([]);
                  }}
                  style={dangerBtnStyle}
                >
                  {isFr ? `Supprimer la sélection (${selectedGrantIds.length})` : `Delete selected (${selectedGrantIds.length})`}
                </button>
              )}
            </div>

            {rbacGrants.map((g) => (
              <div
                key={g.id}
                data-testid={`rbac-grant-row-${g.id}`}
                style={{ padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}
              >
                <label style={{ display: "inline-flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    data-testid={`rbac-grant-checkbox-${g.id}`}
                    checked={selectedGrantIds.includes(g.id)}
                    onChange={(e) =>
                      setSelectedGrantIds((prev) => (e.target.checked ? (prev.includes(g.id) ? prev : [...prev, g.id]) : prev.filter((id) => id !== g.id)))
                    }
                  />
                  <span>
                    <strong>{g.subjectType === "ROLE" ? (isFr ? "Rôle :" : "Role:") : isFr ? "Utilisateur :" : "User:"} {g.subjectId}</strong>{" "}
                    → {isFr ? "Périmètre cible :" : "Target scope:"} <code>{formatTargetScopeLabel(g.scopePath)}</code>
                  </span>
                </label>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <StatusBadge label={`${verbDescriptions[g.verb]} · ${effectBadgeLabels[g.effect]}`} tone={g.effect === "ALLOW" ? "emerald" : "crimson"} />
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
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
