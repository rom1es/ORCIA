import { CommandPaletteModal } from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { CreateWorkspaceCard } from "./CreateWorkspaceCard";
import { WorkspaceDnaAndWaiversSection } from "./WorkspaceDnaAndWaiversSection";
import { WorkspaceStudioCardsAndDetailView } from "./WorkspaceStudioCardsAndDetailView";

export interface WorkspacesFeaturePanelProps {
  readonly initialWorkspaceId?: string;
  readonly initialTab?: string;
}

export function WorkspacesFeaturePanel({
  initialWorkspaceId,
  initialTab,
}: WorkspacesFeaturePanelProps = {}) {
  const { dictionary, locale } = useI18n();
  const { activeScopeId, navigateToRoute, openHelpSection } = useShellNavigation();
  const isFr = locale === "fr";
  const {
    orgUnits,
    workspaces,
    datasources,
    workflows,
    runs,
    ontologyConcepts,
    scopes,
    createWorkspace,
    updateWorkspacePhase,
    updateWorkspaceVisibility,
    registerDatasource,
    addOntologyConcept,
    promoteOntologyConcept,
  } = usePlatformSetup();

  const [isCreateFormOpen, setIsCreateFormOpen] = useState(true);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);
  const activeScopeName =
    activeScopeNode?.name ?? (isFr ? "Plateforme Globale ORCIA" : "Global Platform ORCIA");

  const selectedPrivateOrTeamWs = workspaces.find((w) => w.workspaceId === activeScopeId);
  const activeScopeCategoryLabel = selectedPrivateOrTeamWs
    ? selectedPrivateOrTeamWs.visibilityMode === "PRIVATE_USER"
      ? isFr
        ? "🔒 Mon Espace Privé"
        : "🔒 My Private Space"
      : isFr
        ? "👥 Espace d'Équipe"
        : "👥 Team Space"
    : activeScopeNode?.level === "TEAM"
      ? isFr
        ? "👥 Équipe active"
        : "👥 Active Team"
      : isFr
        ? "🏢 Supervision Organisation"
        : "🏢 Organization Supervision";

  const scopedWorkspaces =
    activeScopeNode?.level === "WORKSPACE"
      ? workspaces.filter((ws) => ws.workspaceId === activeScopeId)
      : activeScopeNode?.level === "TEAM"
        ? workspaces.filter(
            (ws) => !ws.ownerOrgUnitId || ws.ownerOrgUnitId === activeScopeId,
          )
        : workspaces;

  const displayedWorkspaces =
    scopedWorkspaces.length > 0 ? scopedWorkspaces : workspaces;

  const targetWorkspace =
    (initialWorkspaceId
      ? workspaces.find((w) => w.workspaceId === initialWorkspaceId)
      : undefined) ??
    displayedWorkspaces[0] ??
    workspaces[0] ??
    null;

  const effectiveCreateFormVisible = workspaces.length === 0 || isCreateFormOpen;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {actionFeedback ? (
        <div
          role="status"
          data-testid="workspaces-action-feedback-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          {actionFeedback}
        </div>
      ) : null}

      {effectiveCreateFormVisible ? (
        <div data-testid="create-workspace-collapsible-wrapper">
          <CreateWorkspaceCard
            isFr={isFr}
            orgUnits={orgUnits}
            activeScopeName={activeScopeName}
            activeScopeCategoryLabel={activeScopeCategoryLabel}
            openHelpSection={openHelpSection}
            onNavigateToSettings={() => navigateToRoute("/settings")}
            onCreateWorkspace={async (input) => {
              try {
                const created = await createWorkspace(input);
                setActionFeedback(
                  isFr
                    ? `✅ Espace « ${created.name} » créé (${created.slug ?? created.workspaceId}).`
                    : `✅ Workspace "${created.name}" created (${created.slug ?? created.workspaceId}).`,
                );
              } catch (err: unknown) {
                setActionFeedback(
                  `⚠️ ${err instanceof Error ? err.message : "Erreur lors de la création de l'espace."}`,
                );
              }
            }}
          />
        </div>
      ) : null}

      <WorkspaceStudioCardsAndDetailView
        isFr={isFr}
        initialWorkspaceId={initialWorkspaceId}
        initialTab={initialTab}
        workspaces={displayedWorkspaces}
        datasources={datasources}
        ontologyConcepts={ontologyConcepts}
        workflows={workflows}
        orgUnits={orgUnits}
        isCreateFormExpanded={effectiveCreateFormVisible}
        onToggleCreateForm={() => setIsCreateFormOpen((prev) => !prev)}
        openHelpSection={openHelpSection}
        onNavigateToRoute={navigateToRoute}
        onUpdateWorkspacePhase={updateWorkspacePhase}
        onUpdateWorkspaceVisibility={updateWorkspaceVisibility}
        onRegisterDatasource={registerDatasource}
        onAddOntologyConcept={addOntologyConcept}
        onPromoteOntologyConcept={promoteOntologyConcept}
        onFeedback={setActionFeedback}
      />

      <WorkspaceDnaAndWaiversSection
        isFr={isFr}
        targetWorkspace={targetWorkspace}
        datasources={datasources}
        ontologyConcepts={ontologyConcepts}
        dictionary={dictionary}
        onAddOntologyConcept={addOntologyConcept}
        onFeedback={setActionFeedback}
      />

      <CommandPaletteModal
        isOpen={paletteOpen}
        items={[
          {
            entryId: "nav-cockpit",
            category: "NAVIGATION",
            label: "Aller au Cockpit & Décisions",
            subtitle: "Navigation rapide",
            shortcut: "g c",
            targetRoute: "/cockpit",
          },
          {
            entryId: "nav-settings",
            category: "NAVIGATION",
            label: "Ouvrir la Configuration",
            subtitle: "Organisation, Modèles IA, Sources, Packs, Atelier",
            shortcut: "g s",
            targetRoute: "/settings",
          },
          ...runs.map((r) => ({
            entryId: r.runId,
            category: "RUN" as const,
            label: r.title,
            subtitle: `${r.workspaceName} • ${r.currentStepKey}`,
            shortcut: "Alt + ↑/↓",
            targetRoute: `/cockpit?runId=${r.runId}`,
            accessMode: r.accessMode,
          })),
        ]}
        labels={dictionary.commandPalette}
        onSelectItem={(item) => {
          setPaletteOpen(false);
          navigateToRoute(item.targetRoute);
        }}
        onClose={() => setPaletteOpen(false)}
      />
    </div>
  );
}
