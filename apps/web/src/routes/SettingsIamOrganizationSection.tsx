import {
  ContextualInfoTriggerButton,
  DisabledButtonAlertIndicator,
  type ControlCenterWorkspaceGovItem,
  type UiPermissionVerb,
} from "@orcia/ui";
import React, { useState } from "react";
import type {
  ConfiguredOrgUnit,
  ConfiguredRbacGrant,
} from "../components/platformSetupStore";
import { SettingsIamGrantsList } from "./SettingsIamGrantsList";

export interface SettingsIamOrganizationSectionProps {
  readonly isFr: boolean;
  readonly canMutate?: boolean;
  readonly allowedVerbs: readonly UiPermissionVerb[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly openHelpSection: (sectionId: string) => void;
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

export function SettingsIamOrganizationSection({
  isFr,
  canMutate = true,
  allowedVerbs,
  orgUnits,
  workspaces,
  rbacGrants,
  openHelpSection,
  addRbacGrant,
  removeRbacGrant,
}: SettingsIamOrganizationSectionProps) {
  const [grantSubjectType, setGrantSubjectType] = useState<"ROLE" | "USER">("ROLE");
  const [grantSubjectId, setGrantSubjectId] = useState("TEAM_LEAD");
  const [grantScopePath, setGrantScopePath] = useState("GLOBAL");
  const [grantSelectedVerbs, setGrantSelectedVerbs] = useState<readonly UiPermissionVerb[]>([
    "execute",
  ]);
  const [grantEffect, setGrantEffect] = useState<"ALLOW" | "DENY" | "INHERITANCE_BLOCK">("ALLOW");
  const [selectedGrantIds, setSelectedGrantIds] = useState<readonly string[]>([]);

  const hasNoKnownOrganization = orgUnits.length === 0 && workspaces.length === 0;
  const grantDisabled = !canMutate || hasNoKnownOrganization || grantSelectedVerbs.length === 0;
  const grantDisabledReason = !canMutate
    ? isFr
      ? "Droits d'administration requis pour modifier les habilitations."
      : "Administrative permissions required to update grants."
    : hasNoKnownOrganization
      ? isFr
        ? "Créez d'abord au moins une Direction (BU) ou une Équipe dans l'onglet Organisation."
        : "Create at least one Division (BU) or Team in the Organization tab first."
      : isFr
        ? "Sélectionnez au moins une habilitation à attribuer."
        : "Select at least one permission verb to grant.";

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
        INHERITANCE_BLOCK:
          "Isoler ce périmètre — N'applique pas les droits hérités de la Direction parente",
      }
    : {
        ALLOW: "Allow — Grants the checked actions on the selected scope",
        DENY: "Deny — Explicitly blocks these actions (overrides any allow rule)",
        INHERITANCE_BLOCK:
          "Isolate this scope — Does not apply permissions inherited from the parent division",
      };

  const effectBadgeLabels: Record<"ALLOW" | "DENY" | "INHERITANCE_BLOCK", string> = isFr
    ? { ALLOW: "Autorisé", DENY: "Interdit", INHERITANCE_BLOCK: "Périmètre isolé" }
    : { ALLOW: "Allowed", DENY: "Denied", INHERITANCE_BLOCK: "Isolated scope" };

  const allVerbsChecked =
    allowedVerbs.length > 0 && allowedVerbs.every((v) => grantSelectedVerbs.includes(v));

  const formatTargetScopeLabel = (scopePath: string): string => {
    if (scopePath === "GLOBAL") return isFr ? "Plateforme entière" : "Entire platform";
    const matchedUnit = orgUnits.find((u) => u.slug === scopePath || u.id === scopePath);
    if (matchedUnit) {
      const kind = matchedUnit.level === "TEAM" ? (isFr ? "Équipe" : "Team") : "BU";
      return `${kind} : ${matchedUnit.name} (${matchedUnit.slug})`;
    }
    const matchedWs = workspaces.find((w) => w.name === scopePath);
    if (matchedWs) return `${isFr ? "Espace de travail" : "Workspace"} : ${matchedWs.name}`;
    return scopePath;
  };

  const controlsLocked = !canMutate || hasNoKnownOrganization;

  return (
    <section
      data-testid="settings-iam-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <h2 style={{ margin: 0, fontSize: "15px" }}>
          {isFr
            ? "Attribuer et Gérer les Règles d'Habilitation"
            : "Grant and Manage Permission Rules"}
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

      {hasNoKnownOrganization && (
        <p
          data-testid="rbac-grants-disabled-no-org-hint"
          style={{
            margin: 0,
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            fontSize: "12px",
            color: "var(--color-muted-foreground)",
          }}
        >
          {isFr
            ? "Créez d'abord au moins une Direction (BU) ou une Équipe dans l'onglet Organisation avant de pouvoir attribuer des règles d'habilitation."
            : "Create at least one Division (BU) or Team in the Organization tab before granting permission rules."}
        </p>
      )}

      <form
        data-testid="create-rbac-grant-form"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        aria-disabled={controlsLocked}
        onSubmit={(e) => {
          e.preventDefault();
          if (
            controlsLocked ||
            !grantSubjectId.trim() ||
            !grantScopePath.trim() ||
            grantSelectedVerbs.length === 0
          ) {
            return;
          }
          for (const v of grantSelectedVerbs) {
            addRbacGrant({
              subjectType: grantSubjectType,
              subjectId: grantSubjectId.trim(),
              scopePath: grantScopePath.trim(),
              verb: v,
              effect: grantEffect,
            });
          }
        }}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          opacity: controlsLocked ? 0.55 : 1,
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "flex-end" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>
              {isFr ? "Type de bénéficiaire" : "Beneficiary type"}
            </span>
            <select
              data-testid="rbac-subject-type-select"
              disabled={controlsLocked}
              value={grantSubjectType}
              onChange={(e) => setGrantSubjectType(e.target.value as "ROLE" | "USER")}
              style={inputStyle}
            >
              <option value="ROLE">{isFr ? "Rôle" : "Role"}</option>
              <option value="USER">{isFr ? "Utilisateur" : "User"}</option>
            </select>
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", flex: 1, minWidth: "180px" }}>
            <span style={{ fontWeight: 600 }}>
              {isFr ? "Qui ? (Bénéficiaire : Rôle ou Utilisateur)" : "Who? (Beneficiary: Role or User)"}
            </span>
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="rbac-subject-input"
              disabled={controlsLocked}
              value={grantSubjectId}
              onChange={(e) => setGrantSubjectId(e.target.value)}
              placeholder={isFr ? "Ex: Product Manager, Architecte ou email..." : "e.g. Product Manager, Architect..."}
              style={inputStyle}
            />
          </label>

          <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", flex: 1, minWidth: "220px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <label htmlFor="rbac-scope-preset-select" style={{ fontWeight: 600 }}>
                {isFr ? "Sur quoi ? (Périmètre cible)" : "On what? (Target scope)"}
              </label>
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
              disabled={controlsLocked}
              value={grantScopePath}
              onChange={(e) => setGrantScopePath(e.target.value)}
              style={inputStyle}
            >
              <option value="GLOBAL">{isFr ? "Plateforme entière" : "Entire platform"}</option>
              {orgUnits.map((u) => (
                <option key={u.id} value={u.slug}>
                  {u.level === "TEAM"
                    ? isFr ? `Équipe : ${u.name} (${u.slug})` : `Team: ${u.name} (${u.slug})`
                    : isFr ? `Direction (BU) : ${u.name} (${u.slug})` : `Division (BU): ${u.name} (${u.slug})`}
                </option>
              ))}
              {workspaces
                .filter((ws) => !orgUnits.some((u) => u.name === ws.name || u.slug === ws.name))
                .map((ws) => (
                  <option key={ws.name} value={ws.name}>
                    {isFr ? `Espace de travail : ${ws.name}` : `Workspace: ${ws.name}`}
                  </option>
                ))}
            </select>
          </div>

          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>{isFr ? "Effet de la règle" : "Rule effect"}</span>
            <select
              data-testid="rbac-effect-select"
              disabled={controlsLocked}
              value={grantEffect}
              onChange={(e) => setGrantEffect(e.target.value as "ALLOW" | "DENY" | "INHERITANCE_BLOCK")}
              style={inputStyle}
            >
              <option value="ALLOW">{effectDescriptions.ALLOW}</option>
              <option value="DENY">{effectDescriptions.DENY}</option>
              <option value="INHERITANCE_BLOCK">{effectDescriptions.INHERITANCE_BLOCK}</option>
            </select>
          </label>

          <button
            type="submit"
            data-testid="create-rbac-grant-btn"
            disabled={grantDisabled}
            title={grantDisabled ? grantDisabledReason : undefined}
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            <span>{isFr ? "+ Ajouter la règle" : "+ Add rule"}</span>
            <DisabledButtonAlertIndicator
              disabled={grantDisabled}
              reason={grantDisabledReason}
              testIdSuffix="create-rbac-grant-btn"
            />
          </button>
        </div>

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
          <span style={{ fontWeight: 600 }}>{isFr ? "Habilitations à attribuer :" : "Permissions to grant:"}</span>
          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "5px",
              fontWeight: 600,
              cursor: controlsLocked ? "not-allowed" : "pointer",
            }}
          >
            <input
              type="checkbox"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="rbac-verb-checkbox-all"
              disabled={controlsLocked}
              checked={allVerbsChecked}
              onChange={(e) => setGrantSelectedVerbs(e.target.checked ? [...allowedVerbs] : ["execute"])}
            />
            <span>{isFr ? "Tous" : "All"}</span>
          </label>
          {allowedVerbs.map((v) => (
            <label
              key={v}
              style={{ display: "inline-flex", alignItems: "center", gap: "5px", cursor: controlsLocked ? "not-allowed" : "pointer" }}
            >
              <input
                type="checkbox"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={`rbac-verb-checkbox-${v}`}
                disabled={controlsLocked}
                checked={grantSelectedVerbs.includes(v)}
                onChange={(e) =>
                  setGrantSelectedVerbs((prev) =>
                    e.target.checked ? (prev.includes(v) ? prev : [...prev, v]) : prev.filter((item) => item !== v),
                  )
                }
              />
              <span>{verbDescriptions[v]}</span>
            </label>
          ))}
        </div>
      </form>

      <SettingsIamGrantsList
        isFr={isFr}
        canMutate={canMutate}
        rbacGrants={rbacGrants}
        selectedGrantIds={selectedGrantIds}
        verbDescriptions={verbDescriptions}
        effectBadgeLabels={effectBadgeLabels}
        formatTargetScopeLabel={formatTargetScopeLabel}
        onToggleSelectAll={(checked) =>
          setSelectedGrantIds(checked ? rbacGrants.map((g) => g.id) : [])
        }
        onToggleSelectGrant={(grantId, checked) =>
          setSelectedGrantIds((prev) =>
            checked
              ? prev.includes(grantId)
                ? prev
                : [...prev, grantId]
              : prev.filter((id) => id !== grantId),
          )
        }
        onBulkDeleteSelected={() => {
          for (const id of selectedGrantIds) removeRbacGrant(id);
          setSelectedGrantIds([]);
        }}
        onDeleteGrant={(grantId) => {
          removeRbacGrant(grantId);
          setSelectedGrantIds((prev) => prev.filter((id) => id !== grantId));
        }}
      />
    </section>
  );
}
