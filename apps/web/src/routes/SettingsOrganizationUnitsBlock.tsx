import { ContextualInfoTriggerButton, OrciaIcon } from "@orcia/ui";
import React, { useState } from "react";
import type {
  ConfiguredOrgUnit,
  ConfiguredPlatformAdmin,
} from "../components/platformSetupStore";
import { formatCountNoun } from "../stores/authSessionStore";
import { SettingsOrganizationUnitRow } from "./SettingsOrganizationUnitRow";

export interface SettingsOrganizationUnitsBlockProps {
  readonly isFr: boolean;
  readonly canMutate?: boolean;
  readonly platformAdmin?: ConfiguredPlatformAdmin | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly toggleAdminTeamMembership?: (teamId: string) => void;
  readonly addOrgUnit: (
    input: Omit<ConfiguredOrgUnit, "id"> & { readonly attachCurrentAdmin?: boolean },
  ) => void;
  readonly removeOrgUnit: (orgUnitId: string) => {
    readonly deleted: boolean;
    readonly blockedReason: string | null;
  };
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function SettingsOrganizationUnitsBlock({
  isFr,
  canMutate = true,
  platformAdmin,
  orgUnits,
  openHelpSection,
  toggleAdminTeamMembership,
  addOrgUnit,
  removeOrgUnit,
}: SettingsOrganizationUnitsBlockProps) {
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [orgLevel, setOrgLevel] = useState<"BU" | "TEAM">("BU");
  const [orgParentId, setOrgParentId] = useState("scope-global");
  const [attachAdminToNewTeam, setAttachAdminToNewTeam] = useState(true);
  const [orgDeleteFeedback, setOrgDeleteFeedback] = useState<string | null>(null);
  const [confirmDeleteOrgId, setConfirmDeleteOrgId] = useState<string | null>(null);

  const buUnits = orgUnits.filter((u) => u.level === "BU");
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const memberTeamIds = platformAdmin?.memberTeamIds ?? [];
  const attachedTeams = teamUnits.filter((t) => memberTeamIds.includes(t.id));

  const attachedBillingLabel = isFr
    ? `Compte rattaché à ${formatCountNoun(attachedTeams.length, "Équipe de facturation", "Équipes de facturation", "fr")} : ${attachedTeams.map((t) => t.name).join(", ")}`
    : `Account attached to ${formatCountNoun(attachedTeams.length, "billing Team", "billing Teams", "en")}: ${attachedTeams.map((t) => t.name).join(", ")}`;

  return (
    <section
      data-testid="settings-organization-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <h2 style={{ margin: 0, fontSize: "15px" }}>
            {isFr
              ? "Structure de l'Organisation (Directions / BU & Équipes)"
              : "Organization Structure (Divisions / BUs & Teams)"}
          </h2>
          <ContextualInfoTriggerButton
            sectionId="iam-org-tree"
            label={
              isFr
                ? "Comprendre la structure Directions (BU) et Équipes"
                : "Understand Divisions (BUs) and Teams structure"
            }
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <span
          data-testid="admin-team-membership-summary-badge"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "11px",
            fontWeight: 600,
            padding: "4px 8px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            color:
              attachedTeams.length > 0
                ? "var(--color-text-primary)"
                : "var(--color-status-error)",
          }}
        >
          {attachedTeams.length > 0 ? (
            <>
              <OrciaIcon name="team" size={13} />
              <span>{attachedBillingLabel}</span>
            </>
          ) : (
            <>
              <OrciaIcon name="warning" size={13} />
              <span>
                {isFr
                  ? "Aucune Équipe de facturation rattachée à votre compte (appels IA verrouillés)"
                  : "No billing Team attached to your account (AI calls locked)"}
              </span>
            </>
          )}
        </span>
      </div>

      <form
        data-testid="create-org-unit-form"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        onSubmit={(e) => {
          e.preventDefault();
          if (!canMutate || !orgName.trim()) return;
          const resolvedParentId =
            orgLevel === "BU" ? "scope-global" : orgParentId || "scope-global";
          addOrgUnit({
            name: orgName.trim(),
            slug: orgSlug.trim() || orgName.trim().toLowerCase().replace(/\s+/g, "-"),
            level: orgLevel,
            parentId: resolvedParentId,
            attachCurrentAdmin: orgLevel === "TEAM" ? attachAdminToNewTeam : false,
          });
          setOrgName("");
          setOrgSlug("");
          setOrgDeleteFeedback(null);
        }}
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "8px",
          alignItems: "center",
        }}
      >
        <select
          data-testid="org-unit-level-select"
          disabled={!canMutate}
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
          <option value="BU">
            {isFr ? "Direction / Pôle (BU)" : "Division / Business Unit (BU)"}
          </option>
          <option value="TEAM">{isFr ? "Équipe" : "Team"}</option>
        </select>

        {orgLevel === "TEAM" && (
          <select
            data-testid="org-unit-parent-select"
            aria-label={isFr ? "BU parente de rattachement" : "Parent BU"}
            disabled={!canMutate}
            value={orgParentId}
            onChange={(e) => setOrgParentId(e.target.value)}
            style={inputStyle}
          >
            <option value="scope-global">
              {isFr ? "Rattachement : Plateforme entière" : "Parent: Entire platform"}
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
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="org-unit-name-input"
          disabled={!canMutate}
          value={orgName}
          onChange={(e) => setOrgName(e.target.value)}
          placeholder={
            orgLevel === "BU"
              ? isFr
                ? "Nom de la BU (ex: Direction Produit)..."
                : "BU name..."
              : isFr
                ? "Nom de l'Équipe (ex: Équipe Paiement)..."
                : "Team name..."
          }
          style={{ ...inputStyle, flex: 1, minWidth: "180px" }}
        />
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="org-unit-slug-input"
          disabled={!canMutate}
          value={orgSlug}
          onChange={(e) => setOrgSlug(e.target.value)}
          placeholder={
            isFr ? "Identifiant court (optionnel)..." : "Short identifier (optional)..."
          }
          style={inputStyle}
        />

        {orgLevel === "TEAM" && (
          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: canMutate ? "pointer" : "not-allowed",
            }}
          >
            <input
              type="checkbox"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="org-unit-attach-admin-checkbox"
              disabled={!canMutate}
              checked={attachAdminToNewTeam}
              onChange={(e) => setAttachAdminToNewTeam(e.target.checked)}
            />
            <span>
              {isFr
                ? "Rattacher mon compte à cette équipe (facturation & accès)"
                : "Attach my account to this team (billing & access)"}
            </span>
          </label>
        )}

        <button
          type="submit"
          disabled={!canMutate}
          data-testid="create-org-unit-btn"
          className="orcia-ds-btn orcia-ds-btn-primary"
        >
          {isFr ? "+ Créer l'unité" : "+ Create unit"}
        </button>
      </form>

      {orgDeleteFeedback && (
        <div
          role="alert"
          data-testid="org-unit-delete-feedback"
          className="orcia-ds-alert orcia-ds-alert-warning"
          style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
        >
          <OrciaIcon name="warning" size={14} />
          <span>{orgDeleteFeedback}</span>
        </div>
      )}

      {orgUnits.length === 0 ? (
        <p
          data-testid="iam-org-units-empty-state"
          style={{
            margin: 0,
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
          }}
        >
          {isFr
            ? "Aucune unité d'organisation (BU ou Équipe) configurée."
            : "No organization unit (BU or Team) configured yet."}
        </p>
      ) : (
        <div style={{ display: "grid", gap: "6px" }}>
          {orgUnits.map((u) => (
            <SettingsOrganizationUnitRow
              key={u.id}
              unit={u}
              isFr={isFr}
              canMutate={canMutate}
              parentNode={orgUnits.find((p) => p.id === u.parentId)}
              childCount={orgUnits.filter((c) => c.parentId === u.id).length}
              isAdminMember={u.level === "TEAM" && memberTeamIds.includes(u.id)}
              isConfirming={confirmDeleteOrgId === u.id}
              onToggleAdminTeamMembership={toggleAdminTeamMembership}
              onRequestDelete={(unitId) => {
                setOrgDeleteFeedback(null);
                setConfirmDeleteOrgId(unitId);
              }}
              onConfirmDelete={(unitId) => {
                const res = removeOrgUnit(unitId);
                if (!res.deleted && res.blockedReason) {
                  setOrgDeleteFeedback(res.blockedReason);
                } else {
                  setOrgDeleteFeedback(null);
                }
                setConfirmDeleteOrgId(null);
              }}
              onCancelDelete={() => setConfirmDeleteOrgId(null)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
