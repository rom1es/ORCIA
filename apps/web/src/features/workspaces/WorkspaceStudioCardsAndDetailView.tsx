import {
  getOrciaIconGlyph,
  OrciaIcon,
  type ControlCenterDatasourceItem,
  type ControlCenterWorkspaceGovItem,
  type ProductLifecyclePhaseType,
  type UiOntologyConceptView,
  type UiOntologyLevel,
  type WorkspaceVisibilityMode,
} from "@orcia/ui";
import React, { useState } from "react";
import type {
  ConfiguredOrgUnit,
  ConfiguredWorkflowItem,
  PlatformSetupContextValue,
} from "../../components/platformSetupStore";
import { WorkspaceDetailTabsPanel } from "./WorkspaceDetailTabsPanel";

export type WorkspaceQuickFilterKey = "ALL" | "TEAM" | "PRIVATE";

export interface WorkspaceStudioCardsAndDetailViewProps {
  readonly isFr: boolean;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly isCreateFormExpanded: boolean;
  readonly onToggleCreateForm: () => void;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onNavigateToRoute: (route: string) => void;
  readonly onUpdateWorkspacePhase: (workspaceId: string, phase: ProductLifecyclePhaseType) => void;
  readonly onUpdateWorkspaceVisibility: (workspaceId: string, visibilityMode: WorkspaceVisibilityMode) => void;
  readonly onRegisterDatasource: PlatformSetupContextValue["registerDatasource"];
  readonly onAddOntologyConcept: (input: UiOntologyConceptView) => void;
  readonly onPromoteOntologyConcept: (conceptKey: string, targetLevel: UiOntologyLevel, targetScopeId?: string) => void;
  readonly onFeedback: (message: string) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function WorkspaceStudioCardsAndDetailView({
  isFr,
  workspaces,
  datasources,
  ontologyConcepts,
  workflows,
  orgUnits,
  isCreateFormExpanded,
  onToggleCreateForm,
  openHelpSection,
  onNavigateToRoute,
  onUpdateWorkspacePhase,
  onUpdateWorkspaceVisibility,
  onRegisterDatasource,
  onAddOntologyConcept,
  onPromoteOntologyConcept,
  onFeedback,
}: WorkspaceStudioCardsAndDetailViewProps): React.ReactElement {
  const [filterMode, setFilterMode] = useState<WorkspaceQuickFilterKey>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedWsId, setSelectedWsId] = useState<string>("");
  const [autosavedWsIds, setAutosavedWsIds] = useState<readonly string[]>([]);

  const teamWorkspacesCount = workspaces.filter((w) => w.visibilityMode !== "PRIVATE_USER").length;
  const privateWorkspacesCount = workspaces.filter((w) => w.visibilityMode === "PRIVATE_USER").length;

  const filteredWorkspaces = workspaces.filter((ws) => {
    if (filterMode === "TEAM" && ws.visibilityMode === "PRIVATE_USER") return false;
    if (filterMode === "PRIVATE" && ws.visibilityMode !== "PRIVATE_USER") return false;
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      return ws.name.toLowerCase().includes(q) || (ws.ownerOrgUnitName ?? "").toLowerCase().includes(q);
    }
    return true;
  });

  const activeWorkspace =
    workspaces.find((w) => w.workspaceId === selectedWsId) ?? filteredWorkspaces[0] ?? workspaces[0] ?? null;

  const markAutosaved = (workspaceId: string) => {
    setAutosavedWsIds((prev) => (prev.includes(workspaceId) ? prev : [...prev, workspaceId]));
  };

  const getTabStyle = (active: boolean): React.CSSProperties => ({
    fontWeight: active ? 700 : 500,
    backgroundColor: active ? "var(--color-action-primary-subtle)" : "var(--color-bg-elevated)",
    color: active ? "var(--color-action-primary)" : "var(--color-text-primary)",
  });

  return (
    <div
      data-testid="workspaces-redesigned-studio-view"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <section
        data-testid="workspaces-header-and-filters-bar"
        className="orcia-bento-card"
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="workspaces-filter-all"
            aria-pressed={filterMode === "ALL"}
            onClick={() => setFilterMode("ALL")}
            className="orcia-ds-tab"
            style={getTabStyle(filterMode === "ALL")}
          >
            {isFr ? `Tous (${workspaces.length})` : `All (${workspaces.length})`}
          </button>
          <button
            type="button"
            data-testid="workspaces-filter-team"
            aria-pressed={filterMode === "TEAM"}
            onClick={() => setFilterMode("TEAM")}
            className="orcia-ds-tab"
            style={getTabStyle(filterMode === "TEAM")}
          >
            <OrciaIcon name="team" />{" "}
            {isFr ? `Espaces d'Équipe (${teamWorkspacesCount})` : `Team Spaces (${teamWorkspacesCount})`}
          </button>
          <button
            type="button"
            data-testid="workspaces-filter-private"
            aria-pressed={filterMode === "PRIVATE"}
            onClick={() => setFilterMode("PRIVATE")}
            className="orcia-ds-tab"
            style={getTabStyle(filterMode === "PRIVATE")}
          >
            <OrciaIcon name="lock" />{" "}
            {isFr ? `Mes Espaces Privés (${privateWorkspacesCount})` : `My Private Spaces (${privateWorkspacesCount})`}
          </button>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="workspaces-search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={isFr ? "Rechercher un espace ou une équipe..." : "Search a space or team..."}
            style={{ ...inputStyle, minWidth: "210px", fontSize: "12px" }}
          />
          <button
            type="button"
            data-testid="toggle-create-workspace-form-btn"
            aria-expanded={isCreateFormExpanded}
            onClick={onToggleCreateForm}
            style={{
              padding: "7px 12px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-primary-cobalt)",
              color: "var(--color-primary-foreground)",
              fontWeight: 600,
              fontSize: "12px",
              cursor: "pointer",
            }}
          >
            {isCreateFormExpanded
              ? isFr ? "− Replier le formulaire" : "− Hide form"
              : isFr ? "+ Créer un Espace de Travail" : "+ Create a Workspace"}
          </button>
        </div>
      </section>

      {filteredWorkspaces.length === 0 ? (
        <section
          data-testid="workspaces-cards-empty-state"
          className="orcia-bento-card"
          style={{ fontSize: "13px", color: "var(--color-muted-foreground)" }}
        >
          {isFr
            ? "Aucun Espace de Travail ne correspond à ce filtre. Créez votre premier espace ci-dessus pour connecter vos sources et définir votre glossaire métier."
            : "No Workspace matches this filter. Create your first workspace above to connect sources and define your business glossary."}
        </section>
      ) : (
        <section
          data-testid="workspaces-summary-cards-grid"
          style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(310px, 1fr))", gap: "12px" }}
        >
          {filteredWorkspaces.map((ws) => {
            const wsSourcesCount = datasources.filter((d) => d.workspaceName === ws.name).length;
            const isSelected = activeWorkspace?.workspaceId === ws.workspaceId;
            const isAutosaved = autosavedWsIds.includes(ws.workspaceId);
            const visibilityIconName =
              ws.visibilityMode === "PRIVATE_USER"
                ? "lock"
                : ws.visibilityMode === "CONFIDENTIAL_RESTRICTED"
                  ? "shield"
                  : "team";
            const visibilityLabelText =
              ws.visibilityMode === "PRIVATE_USER"
                ? isFr ? "Privé personnel" : "Private personal"
                : ws.visibilityMode === "CONFIDENTIAL_RESTRICTED"
                  ? isFr ? "Confidentiel isolé" : "Confidential isolated"
                  : isFr ? "Collectif d'équipe" : "Team shared";

            return (
              <div
                key={ws.workspaceId}
                data-testid={`workspace-studio-card-${ws.workspaceId}`}
                className="orcia-bento-card"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  border: isSelected ? "2px solid var(--color-action-primary)" : "1px solid var(--color-border)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                  <div>
                    <strong style={{ fontSize: "15px" }}>{ws.name}</strong>
                    <div style={{ fontSize: "11px", color: "var(--color-muted-foreground)", marginTop: "2px" }}>
                      {isFr ? "Équipe de facturation :" : "Billing Team :"}{" "}
                      <strong>{ws.ownerOrgUnitName ?? "Plateforme Globale ORCIA"}</strong>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    {isAutosaved && (
                      <span
                        data-testid={`workspace-autosaved-badge-${ws.workspaceId}`}
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "var(--radius-sm)",
                          backgroundColor: "var(--color-action-primary-subtle)",
                          color: "var(--color-status-success)",
                        }}
                      >
                        <OrciaIcon name="check" /> {isFr ? "Enregistré" : "Saved"}
                      </span>
                    )}
                    <span
                      data-testid={`workspace-visibility-badge-${ws.workspaceId}`}
                      style={{
                        fontSize: "11px",
                        fontWeight: 600,
                        padding: "3px 8px",
                        borderRadius: "var(--radius-sm)",
                        backgroundColor: "var(--color-bg-elevated)",
                        border: "1px solid var(--color-border-subtle)",
                      }}
                    >
                      <OrciaIcon name={visibilityIconName} /> {visibilityLabelText}
                    </span>
                  </div>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", fontSize: "11px", color: "var(--color-text-secondary)" }}>
                  <span><OrciaIcon name="books" /> <strong>{wsSourcesCount}</strong> {isFr ? "Sources rattachées" : "Attached sources"}</span>
                  <span><OrciaIcon name="bookOpen" /> <strong>{ontologyConcepts.length}</strong> {isFr ? "Termes & Règles actifs" : "Active terms & rules"}</span>
                  <span><OrciaIcon name="menuProcesses" /> <strong>{workflows.length}</strong> {isFr ? "Processus" : "Processes"}</span>
                  <span><OrciaIcon name="moneyBag" /> <strong>{(ws.finopsCostUsd ?? 0).toFixed(2)} $</strong></span>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center", paddingTop: "4px" }}>
                  <select
                    data-testid={`workspace-card-phase-select-${ws.workspaceId}`}
                    aria-label={isFr ? "Phase de l'espace" : "Workspace phase"}
                    value={ws.lifecyclePhase}
                    onChange={(e) => {
                      onUpdateWorkspacePhase(ws.workspaceId, e.target.value as ProductLifecyclePhaseType);
                      markAutosaved(ws.workspaceId);
                    }}
                    style={{ ...inputStyle, fontSize: "11px", padding: "4px 8px" }}
                  >
                    <option value="BUILD">{isFr ? "Phase : Construction" : "Phase: Build"}</option>
                    <option value="RUN">{isFr ? "Phase : Exploitation" : "Phase: Operations"}</option>
                    <option value="MIGRATION">{isFr ? "Phase : Évolution" : "Phase: Evolution"}</option>
                  </select>

                  <select
                    data-testid={`workspace-card-visibility-select-${ws.workspaceId}`}
                    aria-label={isFr ? "Visibilité de l'espace" : "Workspace visibility"}
                    value={ws.visibilityMode}
                    onChange={(e) => {
                      onUpdateWorkspaceVisibility(ws.workspaceId, e.target.value as WorkspaceVisibilityMode);
                      markAutosaved(ws.workspaceId);
                    }}
                    style={{ ...inputStyle, fontSize: "11px", padding: "4px 8px" }}
                  >
                    <option value="STANDARD">
                      {`${getOrciaIconGlyph("team")} ${isFr ? "Collectif d'équipe" : "Team shared"}`}
                    </option>
                    <option value="PRIVATE_USER">
                      {`${getOrciaIconGlyph("lock")} ${isFr ? "Privé personnel" : "Private personal"}`}
                    </option>
                    <option value="CONFIDENTIAL_RESTRICTED">
                      {`${getOrciaIconGlyph("shield")} ${isFr ? "Confidentiel isolé" : "Confidential isolated"}`}
                    </option>
                  </select>

                  {ws.visibilityMode === "PRIVATE_USER" && (
                    <button
                      type="button"
                      data-testid={`share-private-workspace-btn-${ws.workspaceId}`}
                      onClick={() => {
                        onUpdateWorkspaceVisibility(ws.workspaceId, "STANDARD");
                        markAutosaved(ws.workspaceId);
                        onFeedback(
                          isFr
                            ? `✅ L'espace « ${ws.name} » est désormais partagé avec l'équipe.`
                            : `✅ Workspace "${ws.name}" is now shared with the team.`,
                        );
                      }}
                      style={{
                        padding: "4px 8px",
                        fontSize: "11px",
                        fontWeight: 600,
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                        backgroundColor: "var(--color-action-primary-subtle)",
                        color: "var(--color-action-primary)",
                        cursor: "pointer",
                      }}
                    >
                      <OrciaIcon name="team" /> {isFr ? "Partager avec l'Équipe" : "Share with Team"}
                    </button>
                  )}
                </div>

                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "8px",
                    justifyContent: "space-between",
                    alignItems: "center",
                    borderTop: "1px solid var(--color-border-subtle)",
                    paddingTop: "8px",
                  }}
                >
                  <button
                    type="button"
                    data-testid={`select-active-workspace-btn-${ws.workspaceId}`}
                    onClick={() => setSelectedWsId(ws.workspaceId)}
                    style={{
                      padding: "5px 10px",
                      fontSize: "11px",
                      fontWeight: 600,
                      borderRadius: "var(--radius-sm)",
                      border: "none",
                      backgroundColor: isSelected ? "var(--color-action-primary)" : "var(--color-bg-elevated)",
                      color: isSelected ? "var(--color-primary-foreground)" : "var(--color-text-primary)",
                      cursor: "pointer",
                    }}
                  >
                    <OrciaIcon name="target" /> {isFr ? "Travailler dans cet Espace" : "Work in this Space"}
                  </button>
                  <div style={{ display: "flex", gap: "6px" }}>
                    <button
                      type="button"
                      data-testid={`workspace-open-assistant-btn-${ws.workspaceId}`}
                      onClick={() => onNavigateToRoute("/assistant")}
                      style={{
                        padding: "4px 8px",
                        fontSize: "11px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                        backgroundColor: "var(--color-surface-card)",
                        cursor: "pointer",
                      }}
                    >
                      <OrciaIcon name="menuAssistant" /> {isFr ? "Ouvrir Mon Assistant" : "Open My Assistant"}
                    </button>
                    <button
                      type="button"
                      data-testid={`workspace-open-processes-btn-${ws.workspaceId}`}
                      onClick={() => onNavigateToRoute("/processes")}
                      style={{
                        padding: "4px 8px",
                        fontSize: "11px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                        backgroundColor: "var(--color-surface-card)",
                        cursor: "pointer",
                      }}
                    >
                      <OrciaIcon name="menuProcesses" /> {isFr ? "Lancer un Processus" : "Launch a Process"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </section>
      )}

      {activeWorkspace && (
        <WorkspaceDetailTabsPanel
          isFr={isFr}
          activeWorkspace={activeWorkspace}
          datasources={datasources}
          ontologyConcepts={ontologyConcepts}
          orgUnits={orgUnits}
          openHelpSection={openHelpSection}
          onRegisterDatasource={onRegisterDatasource}
          onAddOntologyConcept={onAddOntologyConcept}
          onPromoteOntologyConcept={onPromoteOntologyConcept}
          onFeedback={onFeedback}
        />
      )}
    </div>
  );
}
