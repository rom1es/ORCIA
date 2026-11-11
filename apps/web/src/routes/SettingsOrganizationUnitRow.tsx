import { StatusBadge } from "@orcia/ui";
import React from "react";
import type { ConfiguredOrgUnit } from "../components/platformSetupStore";
import { formatCountNoun } from "../stores/authSessionStore";

export interface SettingsOrganizationUnitRowProps {
  readonly unit: ConfiguredOrgUnit;
  readonly isFr: boolean;
  readonly canMutate: boolean;
  readonly parentNode: ConfiguredOrgUnit | undefined;
  readonly childCount: number;
  readonly isAdminMember: boolean;
  readonly isConfirming: boolean;
  readonly onToggleAdminTeamMembership?: (teamId: string) => void;
  readonly onRequestDelete: (unitId: string) => void;
  readonly onConfirmDelete: (unitId: string) => void;
  readonly onCancelDelete: () => void;
}

export function SettingsOrganizationUnitRow({
  unit,
  isFr,
  canMutate,
  parentNode,
  childCount,
  isAdminMember,
  isConfirming,
  onToggleAdminTeamMembership,
  onRequestDelete,
  onConfirmDelete,
  onCancelDelete,
}: SettingsOrganizationUnitRowProps) {
  const levelDisplay = unit.level === "TEAM" ? (isFr ? "ÉQUIPE" : "TEAM") : "BU";
  const attachedChildrenLabel = isFr
    ? formatCountNoun(childCount, "Équipe rattachée", "Équipes rattachées", "fr")
    : formatCountNoun(childCount, "attached Team", "attached Teams", "en");

  return (
    <div
      data-testid={`org-unit-row-${unit.id}`}
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
        <strong>{unit.name}</strong>
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
            ({attachedChildrenLabel})
          </span>
        )}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
        {unit.level === "TEAM" && (
          <>
            <StatusBadge
              testId={`org-unit-member-badge-${unit.id}`}
              label={
                isAdminMember
                  ? isFr
                    ? "Membre (Facturation active)"
                    : "Member (Billing active)"
                  : isFr
                    ? "Non rattaché"
                    : "Not attached"
              }
              tone={isAdminMember ? "emerald" : "neutral"}
            />
            {onToggleAdminTeamMembership && (
              <button
                type="button"
                disabled={!canMutate}
                data-testid={`toggle-team-membership-btn-${unit.id}`}
                onClick={() => onToggleAdminTeamMembership(unit.id)}
                className="orcia-ds-btn orcia-ds-btn-secondary"
                style={{ padding: "5px 10px", fontSize: "12px" }}
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
        <StatusBadge label={`${levelDisplay} · ${unit.slug}`} tone="cobalt" monospace />
        {!isConfirming ? (
          <button
            type="button"
            disabled={!canMutate}
            data-testid={`delete-org-unit-btn-${unit.id}`}
            onClick={() => onRequestDelete(unit.id)}
            className="orcia-ds-btn orcia-ds-btn-danger"
            style={{ padding: "5px 10px", fontSize: "12px" }}
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
              disabled={!canMutate}
              data-testid={`confirm-delete-org-unit-btn-${unit.id}`}
              onClick={() => onConfirmDelete(unit.id)}
              className="orcia-ds-btn orcia-ds-btn-danger"
              style={{ padding: "5px 10px", fontSize: "12px" }}
            >
              {isFr ? "Confirmer la suppression" : "Confirm delete"}
            </button>
            <button
              type="button"
              data-testid={`cancel-delete-org-unit-btn-${unit.id}`}
              onClick={onCancelDelete}
              className="orcia-ds-btn orcia-ds-btn-secondary"
              style={{ padding: "5px 10px", fontSize: "12px" }}
            >
              {isFr ? "Annuler" : "Cancel"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
