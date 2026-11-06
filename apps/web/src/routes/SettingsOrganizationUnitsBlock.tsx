import { ContextualInfoTriggerButton, StatusBadge } from "@orcia/ui";
import React, { useState } from "react";
import type {
  ConfiguredOrgUnit,
  ConfiguredPlatformAdmin,
} from "../components/platformSetupStore";

export interface SettingsOrganizationUnitsBlockProps {
  readonly isFr: boolean;
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

export function SettingsOrganizationUnitsBlock({
  isFr,
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

  return (
    <div>
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
              ? "1. Structure de l'Organisation (Directions / BU & Équipes)"
              : "1. Organization Structure (Divisions / BUs & Teams)"}
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
          {attachedTeams.length > 0
            ? isFr
              ? `👥 Compte rattaché à ${attachedTeams.length} Équipe(s) de facturation : ${attachedTeams.map((t) => t.name).join(", ")}`
              : `👥 Account attached to ${attachedTeams.length} billing Team(s): ${attachedTeams.map((t) => t.name).join(", ")}`
            : isFr
              ? "⚠️ Aucune Équipe de facturation rattachée à votre compte (appels IA verrouillés)"
              : "⚠️ No billing Team attached to your account (AI calls locked)"}
        </span>
      </div>

      <form
        data-testid="create-org-unit-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
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
          marginTop: "10px",
          alignItems: "center",
        }}
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
          <option value="BU">
            {isFr ? "Direction / Pôle (BU)" : "Division / Business Unit (BU)"}
          </option>
          <option value="TEAM">{isFr ? "Équipe" : "Team"}</option>
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
              cursor: "pointer",
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
          style={{
            margin: "10px 0 0 0",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
          }}
        >
          {isFr
            ? "Aucune unité d'organisation (BU ou Équipe) configurée."
            : "No organization unit (BU or Team) configured yet."}
        </p>
      ) : (
        <div style={{ display: "grid", gap: "6px", marginTop: "10px" }}>
          {orgUnits.map((u) => {
            const parentNode = orgUnits.find((p) => p.id === u.parentId);
            const childCount = orgUnits.filter((c) => c.parentId === u.id).length;
            const levelDisplay = u.level === "TEAM" ? (isFr ? "ÉQUIPE" : "TEAM") : "BU";
            const isConfirming = confirmDeleteOrgId === u.id;
            const isAdminMember = u.level === "TEAM" && memberTeamIds.includes(u.id);
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
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    flexWrap: "wrap",
                  }}
                >
                  <strong>{u.name}</strong>
                  <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
                    {parentNode
                      ? isFr
                        ? `↳ Rattaché à la BU : ${parentNode.name}`
                        : `↳ Parent BU: ${parentNode.name}`
                      : isFr
                        ? "↳ Niveau Racine (Plateforme entière)"
                        : "↳ Root Level (Entire platform)"}
                  </span>
                  {childCount > 0 && (
                    <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                      ({childCount} {isFr ? "Équipe(s) rattachée(s)" : "attached Team(s)"})
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  {u.level === "TEAM" && (
                    <>
                      <StatusBadge
                        testId={`org-unit-member-badge-${u.id}`}
                        label={
                          isAdminMember
                            ? isFr
                              ? "✓ Membre (Facturation active)"
                              : "✓ Member (Billing active)"
                            : isFr
                              ? "Non rattaché"
                              : "Not attached"
                        }
                        tone={isAdminMember ? "emerald" : "neutral"}
                      />
                      {toggleAdminTeamMembership && (
                        <button
                          type="button"
                          data-testid={`toggle-team-membership-btn-${u.id}`}
                          onClick={() => toggleAdminTeamMembership(u.id)}
                          style={dangerBtnStyle}
                        >
                          {isAdminMember
                            ? isFr
                              ? "Retirer mon rattachement"
                              : "Detach my account"
                            : isFr
                              ? "+ Rattacher mon compte"
                              : "+ Attach my account"}
                        </button>
                      )}
                    </>
                  )}
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
  );
}
