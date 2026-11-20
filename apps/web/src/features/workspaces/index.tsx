import { CommandPaletteModal, OrciaAlertBanner, OrciaDialog } from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { resolveGlobalScopeLabel } from "../../components/platformSetupWorkspaces";
import { useShellNavigation } from "../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../stores/authSessionStore";
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

  const [isCreateFormOpen, setIsCreateFormOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const authEmail = useAuthSessionStore((s) => s.email);
  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);
  const activeScopeName = activeScopeNode?.name ?? resolveGlobalScopeLabel(isFr);

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

  const resolvedActiveWsId = resolveEffectiveWorkspaceId(activeScopeId, workspaces, authEmail);
  const targetWorkspace =
    (initialWorkspaceId
      ? workspaces.find((w) => w.workspaceId === initialWorkspaceId)
      : undefined) ??
    displayedWorkspaces.find((w) => w.workspaceId === resolvedActiveWsId) ??
    displayedWorkspaces[0] ??
    workspaces[0] ??
    null;

  const effectiveCreateFormVisible = isCreateFormOpen;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <nav
        aria-label={isFr ? "Navigation Mes Espaces" : "My Spaces navigation"}
        className="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2"
        style={{
          backgroundColor: "var(--color-bg-surface)",
          borderColor: "var(--color-border-subtle)",
        }}
      >
        <span className="text-xs font-semibold">
          {isFr ? "Espaces de travail & Sources" : "Workspaces & Sources"}
        </span>
        <button
          type="button"
          data-testid="spaces-open-glossary-link"
          onClick={() => navigateToRoute("/ontology")}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
        >
          {isFr ? "📖 Glossaire métier →" : "📖 Business Glossary →"}
        </button>
      </nav>
      {actionFeedback ? (
        <OrciaAlertBanner
          tone={actionFeedback.startsWith("⚠️") ? "crimson" : "emerald"}
          role={actionFeedback.startsWith("⚠️") ? "alert" : "status"}
          testId="workspaces-action-feedback-banner"
        >
          {actionFeedback}
        </OrciaAlertBanner>
      ) : null}

      <OrciaDialog
        open={effectiveCreateFormVisible}
        onOpenChange={setIsCreateFormOpen}
        title={isFr ? "Créer un Nouvel Espace de Travail" : "Create a New Workspace"}
        testId="create-workspace-modal"
        closeLabel={isFr ? "Fermer" : "Close"}
      >
        <div className="orcia-ds-dialog-body" data-testid="create-workspace-collapsible-wrapper">
          <CreateWorkspaceCard
            isFr={isFr}
            orgUnits={orgUnits}
            activeScopeName={activeScopeName}
            activeScopeCategoryLabel={activeScopeCategoryLabel}
            openHelpSection={openHelpSection}
            onNavigateToSettings={() => {
              setIsCreateFormOpen(false);
              navigateToRoute("/settings");
            }}
            onCreateWorkspace={async (input) => {
              try {
                const created = await createWorkspace(input);
                setActionFeedback(
                  isFr
                    ? `✅ Espace « ${created.name} » créé (${created.slug ?? created.workspaceId}).`
                    : `✅ Workspace "${created.name}" created (${created.slug ?? created.workspaceId}).`,
                );
                setIsCreateFormOpen(false);
              } catch (err: unknown) {
                setActionFeedback(
                  `⚠️ ${formatRfc9457ErrorToBanner(err, locale, isFr ? "Espace de travail" : "Workspace").fullText}`,
                );
              }
            }}
          />
        </div>
      </OrciaDialog>

      <WorkspaceStudioCardsAndDetailView
        isFr={isFr}
        initialWorkspaceId={initialWorkspaceId || resolvedActiveWsId || undefined}
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

      {targetWorkspace !== null ? (
        <WorkspaceDnaAndWaiversSection
          isFr={isFr}
          targetWorkspace={targetWorkspace}
          datasources={datasources}
          ontologyConcepts={ontologyConcepts}
          dictionary={dictionary}
          onAddOntologyConcept={addOntologyConcept}
          onFeedback={setActionFeedback}
        />
      ) : null}

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
            label: isFr ? "Ouvrir l'Administration" : "Open Administration",
            subtitle: isFr
              ? "Comptes, Authentification, Modèles IA, Connecteurs, Packs"
              : "Accounts, Authentication, AI Models, Connectors, Packs",
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
