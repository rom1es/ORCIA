import {
  ContextualInfoTriggerButton,
  DisabledButtonAlertIndicator,
  type ProductLifecyclePhaseType,
  type WorkspaceVisibilityMode,
} from "@orcia/ui";
import React, { useState } from "react";
import type { ConfiguredOrgUnit } from "../../components/platformSetupStore";

export interface CreateWorkspaceCardProps {
  readonly isFr: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly activeScopeName: string;
  readonly activeScopeCategoryLabel: string;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onNavigateToSettings: () => void;
  readonly onCreateWorkspace: (input: {
    name: string;
    slug: string;
    visibilityMode: WorkspaceVisibilityMode;
    lifecyclePhase: ProductLifecyclePhaseType;
    ownerOrgUnitId?: string;
  }) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function CreateWorkspaceCard({
  isFr,
  orgUnits,
  activeScopeName,
  activeScopeCategoryLabel,
  openHelpSection,
  onNavigateToSettings,
  onCreateWorkspace,
}: CreateWorkspaceCardProps): React.ReactElement {
  const [wsName, setWsName] = useState("");
  const [wsSlug, setWsSlug] = useState("");
  const [wsVisibility, setWsVisibility] = useState<WorkspaceVisibilityMode>("STANDARD");
  const [wsPhase, setWsPhase] = useState<ProductLifecyclePhaseType>("BUILD");
  const [selectedTeamId, setSelectedTeamId] = useState<string>("");

  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const effectiveOwnerTeamId =
    selectedTeamId || teamUnits[0]?.id || orgUnits[orgUnits.length - 1]?.id || "";
  const isSubmitDisabled = !wsName.trim();
  const submitDisabledReason =
    teamUnits.length === 0
      ? isFr
        ? "Saisissez le nom de l'Espace de Travail et créez une Équipe de rattachement (facturation IA) dans Configuration › Organisation."
        : "Enter the Workspace name and create a billing Team in Configuration › Organization."
      : isFr
        ? "Saisissez le nom de l'Espace de Travail pour le créer."
        : "Enter the Workspace name to create it.";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!wsName.trim()) return;
    onCreateWorkspace({
      name: wsName.trim(),
      slug: wsSlug.trim() || wsName.trim().toLowerCase().replace(/\s+/g, "-"),
      visibilityMode: wsVisibility,
      lifecyclePhase: wsPhase,
      ...(effectiveOwnerTeamId ? { ownerOrgUnitId: effectiveOwnerTeamId } : {}),
    });
    setWsName("");
    setWsSlug("");
  };

  return (
    <section
      data-testid="create-workspace-panel"
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
          <h2 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>
            {isFr
              ? "Créer un Nouvel Espace de Travail"
              : "Create a New Workspace"}
          </h2>
          <ContextualInfoTriggerButton
            sectionId="workspace-sources"
            label={
              isFr
                ? "Comprendre la création d'un Espace de travail et ses sources"
                : "Understand how to create a Workspace and connect sources"
            }
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <span
          data-testid="workspace-active-scope-banner"
          style={{
            fontSize: "12px",
            fontWeight: 600,
            padding: "4px 10px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
          }}
        >
          {activeScopeCategoryLabel} : {activeScopeName}
        </span>
      </div>

      {teamUnits.length === 0 && (
        <div
          data-testid="workspace-no-billing-team-warning"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            fontSize: "12px",
          }}
        >
          <span>
            {isFr
              ? "💡 Tout Espace de Travail (collectif ou privé) est rattaché à une Équipe pour le suivi des coûts IA. Créez vos Équipes dans Configuration › Organisation."
              : "💡 Every Workspace (team or private) is attached to a Team for AI cost tracking. Create your Teams in Configuration › Organization."}
          </span>
          <button
            type="button"
            data-testid="workspace-go-create-team-btn"
            onClick={onNavigateToSettings}
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface)",
              color: "var(--color-foreground)",
              fontWeight: 600,
              fontSize: "11px",
              cursor: "pointer",
            }}
          >
            {isFr ? "Créer une Équipe →" : "Create a Team →"}
          </button>
        </div>
      )}

      <form
        data-testid="create-workspace-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        onSubmit={handleSubmit}
        style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}
      >
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="workspace-name-input"
          value={wsName}
          onChange={(e) => setWsName(e.target.value)}
          placeholder={
            isFr ? "Nom de l'Espace de Travail..." : "Workspace name..."
          }
          style={{ ...inputStyle, flex: 1, minWidth: "200px" }}
        />
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="workspace-slug-input"
          value={wsSlug}
          onChange={(e) => setWsSlug(e.target.value)}
          placeholder={isFr ? "Identifiant court (optionnel)..." : "Short ID (optional)..."}
          style={inputStyle}
        />
        <select
          data-testid="workspace-owner-team-select"
          aria-label={
            isFr
              ? "Équipe de rattachement (facturation IA)"
              : "Billing Team attachment"
          }
          value={effectiveOwnerTeamId}
          onChange={(e) => setSelectedTeamId(e.target.value)}
          style={inputStyle}
        >
          {teamUnits.length === 0 ? (
            <option value="">
              {isFr
                ? "Équipe de facturation : par défaut"
                : "Billing Team: default"}
            </option>
          ) : (
            teamUnits.map((team) => (
              <option key={team.id} value={team.id}>
                {isFr
                  ? `Équipe de facturation : ${team.name}`
                  : `Billing Team: ${team.name}`}
              </option>
            ))
          )}
        </select>
        <select
          data-testid="workspace-visibility-select"
          value={wsVisibility}
          onChange={(e) =>
            setWsVisibility(e.target.value as WorkspaceVisibilityMode)
          }
          style={inputStyle}
        >
          <option value="STANDARD">
            {isFr ? "Collectif d'équipe (Standard)" : "Team shared (Standard)"}
          </option>
          <option value="PRIVATE_USER">
            {isFr
              ? "Privé personnel (Facturé à l'équipe)"
              : "Private personal (Billed to team)"}
          </option>
          <option value="CONFIDENTIAL_RESTRICTED">
            {isFr ? "Confidentiel (isolé)" : "Confidential (isolated)"}
          </option>
        </select>
        <select
          data-testid="workspace-phase-select"
          value={wsPhase}
          onChange={(e) =>
            setWsPhase(e.target.value as ProductLifecyclePhaseType)
          }
          style={inputStyle}
        >
          <option value="BUILD">{isFr ? "Construction" : "Build"}</option>
          <option value="RUN">{isFr ? "Exploitation" : "Operations"}</option>
          <option value="MIGRATION">{isFr ? "Évolution" : "Evolution"}</option>
        </select>
        <button
          type="submit"
          data-testid="create-workspace-submit-btn"
          disabled={isSubmitDisabled}
          title={isSubmitDisabled ? submitDisabledReason : undefined}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "7px 14px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: "var(--color-primary-cobalt)",
            color: "var(--color-primary-foreground)",
            fontWeight: 600,
            opacity: isSubmitDisabled ? 0.6 : 1,
            cursor: isSubmitDisabled ? "not-allowed" : "pointer",
          }}
        >
          <span>{isFr ? "+ Créer l'Espace" : "+ Create Workspace"}</span>
          <DisabledButtonAlertIndicator
            disabled={isSubmitDisabled}
            reason={submitDisabledReason}
            testIdSuffix="create-workspace-submit-btn"
          />
        </button>
      </form>
    </section>
  );
}
