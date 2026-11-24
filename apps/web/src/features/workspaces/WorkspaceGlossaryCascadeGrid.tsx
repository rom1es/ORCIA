import { OrciaIcon, type UiOntologyConceptView, type UiOntologyLevel } from "@orcia/ui";
import React from "react";
import type { ConfiguredOrgUnit } from "../../components/platformSetupStore";
import type { WritableScopeOptionItem } from "../../components/ontologyApiBridge";
import type { OntologyGlossaryCopy } from "../../i18n/locales/ontology_glossary_labels";

export type GlossaryScopeTier = "WORKSPACE" | "TEAM" | "BU" | "ENTERPRISE";

export function resolveGlossaryScopeId(params: {
  readonly selectedScopeTier: GlossaryScopeTier;
  readonly writableScopes: readonly WritableScopeOptionItem[];
  readonly parentBuUnit: ConfiguredOrgUnit | undefined;
  readonly preferredTeamId: string | undefined;
  readonly hasSelectedWorkspace: boolean;
  readonly wsId: string;
}): string {
  const { selectedScopeTier, writableScopes, parentBuUnit, preferredTeamId, hasSelectedWorkspace, wsId } = params;
  if (selectedScopeTier === "ENTERPRISE") {
    return writableScopes.find((s) => s.level === "1_ENTERPRISE")?.scope_id ?? "scope-global";
  }
  if (selectedScopeTier === "BU") {
    const match =
      writableScopes.find((s) => s.level === "2_DOMAIN" && (!parentBuUnit || s.scope_id === parentBuUnit.id)) ??
      writableScopes.find((s) => s.level === "2_DOMAIN");
    return match?.scope_id ?? parentBuUnit?.id ?? "";
  }
  if (selectedScopeTier === "TEAM") {
    const match =
      writableScopes.find((s) => s.level === "3_TEAM" && (!preferredTeamId || s.scope_id === preferredTeamId)) ??
      writableScopes.find((s) => s.level === "3_TEAM");
    return match?.scope_id ?? preferredTeamId ?? "";
  }
  const wsMatch = writableScopes.find(
    (s) => (s.level === "4_WORKSPACE" || s.level === "3_WORKSPACE") && (!hasSelectedWorkspace || s.scope_id === wsId),
  );
  return wsMatch?.scope_id ?? wsId;
}

export interface GlossaryCascadeTierView {
  readonly tierId: string;
  readonly badge: string;
  readonly subtitle: string;
  readonly items: readonly UiOntologyConceptView[];
}

export interface WorkspaceGlossaryCascadeGridProps {
  readonly cascadeTiers: readonly GlossaryCascadeTierView[];
  readonly pendingConceptKeys: readonly string[];
  readonly copy: OntologyGlossaryCopy;
  readonly getLevelBadgeLabel: (level: UiOntologyLevel) => string;
  readonly onPromote: (concept: UiOntologyConceptView) => void;
}

export function WorkspaceGlossaryCascadeGrid({
  cascadeTiers,
  pendingConceptKeys,
  copy,
  getLevelBadgeLabel,
  onPromote,
}: WorkspaceGlossaryCascadeGridProps): React.ReactElement {
  return (
    <div
      data-testid="workspace-glossary-cascade-grid"
      style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "10px" }}
    >
      {cascadeTiers.map((tier) => (
        <div
          key={tier.tierId}
          data-testid={`workspace-glossary-tier-${tier.tierId}`}
          style={{
            padding: "10px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong style={{ fontSize: "12px" }}>{tier.badge}</strong>
            <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
              {tier.items.length}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: "11px", color: "var(--color-muted-foreground)" }}>
            {tier.subtitle}
          </p>
          {tier.items.length === 0 ? (
            <p
              data-testid={`workspace-glossary-empty-${tier.tierId}`}
              style={{ margin: 0, fontSize: "11px", color: "var(--color-muted-foreground)" }}
            >
              {copy.workspaceGlossaryEmptyTier}
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {tier.items.map((concept) => {
                const isPending = pendingConceptKeys.includes(concept.conceptKey);
                const canPromote =
                  concept.level !== "1_ENTERPRISE" && (concept.canProposePromotion ?? true);
                return (
                  <div
                    key={concept.conceptKey}
                    data-testid={`glossary-concept-card-${concept.conceptKey}`}
                    style={{
                      padding: "8px 10px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--color-border-subtle)",
                      backgroundColor: "var(--color-bg-elevated)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: "6px",
                        flexWrap: "wrap",
                      }}
                    >
                      <strong style={{ fontSize: "12px" }}>{concept.canonicalTerm}</strong>
                      <span
                        data-testid={`glossary-concept-level-badge-${concept.conceptKey}`}
                        style={{ fontSize: "10px", color: "var(--color-text-secondary)" }}
                      >
                        {getLevelBadgeLabel(concept.level)}
                      </span>
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
                      {concept.definitionText}
                    </span>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                      {isPending && (
                        <span
                          data-testid={`promoted-glossary-badge-${concept.conceptKey}`}
                          style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            padding: "2px 6px",
                            borderRadius: "var(--radius-sm)",
                            backgroundColor: "var(--color-action-primary-subtle)",
                            color: "var(--color-status-warning)",
                          }}
                        >
                          <OrciaIcon name="hourglass" /> {copy.workspaceGlossaryProposedBadge}
                        </span>
                      )}
                      {canPromote && (
                        <button
                          type="button"
                          data-testid={`promote-glossary-concept-btn-${concept.conceptKey}`}
                          onClick={() => onPromote(concept)}
                          className="orcia-ds-btn"
                        >
                          <OrciaIcon name="promoteUp" />{" "}
                          {concept.level === "2_DOMAIN"
                            ? copy.workspaceGlossaryProposeOrg
                            : copy.workspaceGlossaryProposeTeamOrBu}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
