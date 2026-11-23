import {
  OrciaIcon,
  type ControlCenterDatasourceItem,
  type ControlCenterWorkspaceGovItem,
  type ProductLifecyclePhaseType,
  type UiOntologyConceptView,
  type UiOntologyLevel,
  type WorkspaceVisibilityMode,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type {
  ConfiguredOrgUnit,
  ConfiguredWorkflowItem,
  PlatformSetupContextValue,
} from "../../components/platformSetupStore";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../i18n";
import { WorkspaceDetailTabsPanel } from "./WorkspaceDetailTabsPanel";
import { WorkspaceStudioSummaryCard } from "./WorkspaceStudioSummaryCard";

export type WorkspaceQuickFilterKey = "ALL" | "TEAM" | "PRIVATE";

export interface WorkspaceStudioCardsAndDetailViewProps {
  readonly isFr: boolean;
  readonly initialWorkspaceId?: string;
  readonly initialTab?: string;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly isCreateFormExpanded: boolean;
  readonly onToggleCreateForm: () => void;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onNavigateToRoute: (route: string) => void;
  readonly onUpdateWorkspacePhase: (workspaceId: string, phase: ProductLifecyclePhaseType) => void | Promise<void>;
  readonly onUpdateWorkspaceVisibility: (workspaceId: string, visibilityMode: WorkspaceVisibilityMode) => void | Promise<void>;
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
  initialWorkspaceId,
  initialTab,
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
  const studioCopy = resolveDictionaryForFlag(isFr).featureWorkspaces.studioCards;
  const [filterMode, setFilterMode] = useState<WorkspaceQuickFilterKey>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedWsId, setSelectedWsId] = useState<string>(initialWorkspaceId || "");
  useEffect(() => {
    if (initialWorkspaceId) {
      setSelectedWsId(initialWorkspaceId);
    }
  }, [initialWorkspaceId]);
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
            {workspaces.length > 0
              ? formatI18nTemplate(studioCopy.filterAllCountTemplate, { count: workspaces.length })
              : studioCopy.filterAll}
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
            {teamWorkspacesCount > 0
              ? formatI18nTemplate(studioCopy.filterTeamCountTemplate, { count: teamWorkspacesCount })
              : studioCopy.filterTeam}
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
            {privateWorkspacesCount > 0
              ? formatI18nTemplate(studioCopy.filterPrivateCountTemplate, {
                  count: privateWorkspacesCount,
                })
              : studioCopy.filterPrivate}
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
            placeholder={studioCopy.searchPlaceholder}
            style={{ ...inputStyle, minWidth: "230px", fontSize: "12px" }}
          />
          <button
            type="button"
            data-testid="toggle-create-workspace-form-btn"
            aria-expanded={isCreateFormExpanded}
            onClick={onToggleCreateForm}
            className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
          >
            {studioCopy.newSpaceBtn}
          </button>
        </div>
      </section>

      {filteredWorkspaces.length === 0 ? (
        <section
          data-testid="workspaces-cards-empty-state"
          className="orcia-bento-card"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "10px",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
          }}
        >
          <span>{studioCopy.emptyFilterText}</span>
        </section>
      ) : (
        <section
          data-testid="workspaces-summary-cards-grid"
          style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(310px, 1fr))", gap: "12px" }}
        >
          {filteredWorkspaces.map((ws) => (
            <WorkspaceStudioSummaryCard
              key={ws.workspaceId}
              ws={ws}
              isFr={isFr}
              isSelected={activeWorkspace?.workspaceId === ws.workspaceId}
              isAutosaved={autosavedWsIds.includes(ws.workspaceId)}
              wsSourcesCount={datasources.filter((d) => d.workspaceName === ws.name).length}
              ontologyConceptsCount={ontologyConcepts.length}
              workflowsCount={workflows.length}
              inputStyle={inputStyle}
              onSelectWorkspace={setSelectedWsId}
              onUpdateWorkspacePhase={onUpdateWorkspacePhase}
              onUpdateWorkspaceVisibility={onUpdateWorkspaceVisibility}
              onMarkAutosaved={markAutosaved}
              onFeedback={onFeedback}
              onNavigateToRoute={onNavigateToRoute}
            />
          ))}
        </section>
      )}

      {activeWorkspace && (
        <WorkspaceDetailTabsPanel
          isFr={isFr}
          initialTab={initialTab}
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
