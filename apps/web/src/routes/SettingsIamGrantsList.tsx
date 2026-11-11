import { StatusBadge, type UiPermissionVerb } from "@orcia/ui";
import React from "react";
import type { ConfiguredRbacGrant } from "../components/platformSetupStore";

export interface SettingsIamGrantsListProps {
  readonly isFr: boolean;
  readonly canMutate: boolean;
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly selectedGrantIds: readonly string[];
  readonly verbDescriptions: Readonly<Record<UiPermissionVerb, string>>;
  readonly effectBadgeLabels: Readonly<Record<"ALLOW" | "DENY" | "INHERITANCE_BLOCK", string>>;
  readonly formatTargetScopeLabel: (scopePath: string) => string;
  readonly onToggleSelectAll: (checked: boolean) => void;
  readonly onToggleSelectGrant: (grantId: string, checked: boolean) => void;
  readonly onBulkDeleteSelected: () => void;
  readonly onDeleteGrant: (grantId: string) => void;
}

export function SettingsIamGrantsList({
  isFr,
  canMutate,
  rbacGrants,
  selectedGrantIds,
  verbDescriptions,
  effectBadgeLabels,
  formatTargetScopeLabel,
  onToggleSelectAll,
  onToggleSelectGrant,
  onBulkDeleteSelected,
  onDeleteGrant,
}: SettingsIamGrantsListProps): React.ReactElement {
  if (rbacGrants.length === 0) {
    return (
      <p
        data-testid="iam-grants-empty-state"
        style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
      >
        {isFr
          ? "Aucune règle d'habilitation personnalisée."
          : "No custom permission rule configured."}
      </p>
    );
  }

  const allGrantsChecked =
    rbacGrants.length > 0 && rbacGrants.every((g) => selectedGrantIds.includes(g.id));

  return (
    <div style={{ display: "grid", gap: "6px" }}>
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
        <label
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
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
            data-testid="rbac-grants-select-all-checkbox"
            disabled={!canMutate}
            checked={allGrantsChecked}
            onChange={(e) => onToggleSelectAll(e.target.checked)}
          />
          <span>{isFr ? "Tous (Tout sélectionner)" : "All (Select all)"}</span>
        </label>
        {selectedGrantIds.length > 0 && (
          <button
            type="button"
            disabled={!canMutate}
            data-testid="rbac-grants-bulk-delete-btn"
            onClick={onBulkDeleteSelected}
            className="orcia-ds-btn orcia-ds-btn-danger"
            style={{ padding: "5px 10px", fontSize: "12px" }}
          >
            {isFr
              ? `Supprimer la sélection (${selectedGrantIds.length})`
              : `Delete selected (${selectedGrantIds.length})`}
          </button>
        )}
      </div>

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
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
          }}
        >
          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
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
              data-testid={`rbac-grant-checkbox-${g.id}`}
              disabled={!canMutate}
              checked={selectedGrantIds.includes(g.id)}
              onChange={(e) => onToggleSelectGrant(g.id, e.target.checked)}
            />
            <span>
              <strong>
                {g.subjectType === "ROLE"
                  ? isFr
                    ? "Rôle :"
                    : "Role:"
                  : isFr
                    ? "Utilisateur :"
                    : "User:"}{" "}
                {g.subjectId}
              </strong>{" "}
              → {isFr ? "Périmètre cible :" : "Target scope:"}{" "}
              <code>{formatTargetScopeLabel(g.scopePath)}</code>
            </span>
          </label>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <StatusBadge
              label={`${verbDescriptions[g.verb]} · ${effectBadgeLabels[g.effect]}`}
              tone={g.effect === "ALLOW" ? "emerald" : "crimson"}
            />
            <button
              type="button"
              disabled={!canMutate}
              data-testid={`delete-rbac-grant-btn-${g.id}`}
              onClick={() => onDeleteGrant(g.id)}
              className="orcia-ds-btn orcia-ds-btn-danger"
              style={{ padding: "5px 10px", fontSize: "12px" }}
            >
              {isFr ? "Supprimer" : "Delete"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
