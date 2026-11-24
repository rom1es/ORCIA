import { CommandPaletteModal, OrciaAlertBanner, OrciaDialog } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { resolveGlobalScopeLabel } from "../../components/platformSetupWorkspaces";
import { useShellNavigation } from "../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { formatI18nTemplate, useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import { CreateWorkspaceCard } from "./CreateWorkspaceCard";
import { WorkspaceDnaAndWaiversSection } from "./WorkspaceDnaAndWaiversSection";
import { formatWorkspaceCreatedBannerId } from "./workspaceDisplayHelpers";
import { WorkspaceStudioCardsAndDetailView } from "./WorkspaceStudioCardsAndDetailView";

export interface WorkspacesFeaturePanelProps {
  readonly initialWorkspaceId?: string;
  readonly initialTab?: string;
}

export function WorkspacesFeaturePanel({
  initialWorkspaceId,
  initialTab,
}: WorkspacesFeaturePanelProps = {}) {
  const { dictionary, isFr, locale } = useI18n();
  const wsPanelCopy = dictionary.featureWorkspaces.panel;
  const { activeScopeId, setActiveScopeId, navigateToRoute, openHelpSection } =
    useShellNavigation();
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
  const [fallbackSelectedWsId, setFallbackSelectedWsId] = useState<string | null>(null);

  useEffect(() => {
    setFallbackSelectedWsId(null);
  }, [activeScopeId]);

  const authEmail = useAuthSessionStore((s) => s.email);
  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);
  const activeScopeName = activeScopeNode?.name ?? resolveGlobalScopeLabel(isFr);

  const selectedPrivateOrTeamWs = workspaces.find((w) => w.workspaceId === activeScopeId);
  const activeScopeCategoryLabel = selectedPrivateOrTeamWs
    ? selectedPrivateOrTeamWs.visibilityMode === "PRIVATE_USER"
      ? wsPanelCopy.privateSpaceLabel
      : wsPanelCopy.teamSpaceLabel
    : activeScopeNode?.level === "TEAM"
      ? wsPanelCopy.activeTeamLabel
      : wsPanelCopy.orgSupervisionLabel;

  const explicitTargetWs = initialWorkspaceId
    ? workspaces.find((w) => w.workspaceId === initialWorkspaceId)
    : undefined;

  const resolvedActiveWsId = resolveEffectiveWorkspaceId(activeScopeId, workspaces, authEmail);
  const effectiveWsId =
    explicitTargetWs?.workspaceId ??
    (fallbackSelectedWsId && workspaces.some((w) => w.workspaceId === fallbackSelectedWsId)
      ? fallbackSelectedWsId
      : resolvedActiveWsId);
  const targetWorkspace =
    workspaces.find((w) => w.workspaceId === effectiveWsId) ?? workspaces[0] ?? null;

  const handleSelectWorkspace = (nextWsId: string) => {
    setFallbackSelectedWsId(nextWsId);
    setActiveScopeId?.(nextWsId);
  };

  const effectiveCreateFormVisible = isCreateFormOpen;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
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
        title={wsPanelCopy.createModalTitle}
        testId="create-workspace-modal"
        closeLabel={wsPanelCopy.createModalCloseLabel}
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
                if (!initialWorkspaceId) {
                  handleSelectWorkspace(created.workspaceId);
                }
                setActionFeedback(
                  formatI18nTemplate(wsPanelCopy.workspaceCreatedTemplate, {
                    name: created.name,
                    id: formatWorkspaceCreatedBannerId(created),
                  }),
                );
                setIsCreateFormOpen(false);
              } catch (err: unknown) {
                setActionFeedback(
                  `⚠️ ${formatRfc9457ErrorToBanner(err, locale, wsPanelCopy.workspaceErrorContext).fullText}`,
                );
              }
            }}
          />
        </div>
      </OrciaDialog>

      <WorkspaceStudioCardsAndDetailView
        isFr={isFr}
        initialWorkspaceId={targetWorkspace?.workspaceId}
        initialTab={initialTab}
        workspaces={workspaces}
        datasources={datasources}
        ontologyConcepts={ontologyConcepts}
        workflows={workflows}
        orgUnits={orgUnits}
        isCreateFormExpanded={effectiveCreateFormVisible}
        onSelectWorkspace={handleSelectWorkspace}
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
          initialTab={initialTab}
          targetWorkspace={targetWorkspace}
          datasources={datasources}
          ontologyConcepts={ontologyConcepts}
          orgUnits={orgUnits}
          dictionary={dictionary}
          openHelpSection={openHelpSection}
          onRegisterDatasource={registerDatasource}
          onAddOntologyConcept={addOntologyConcept}
          onPromoteOntologyConcept={promoteOntologyConcept}
          onFeedback={setActionFeedback}
        />
      ) : null}

      <CommandPaletteModal
        isOpen={paletteOpen}
        rgaaLabels={dictionary.rgaaModal}
        items={[
          {
            entryId: "nav-cockpit",
            category: "NAVIGATION",
            label: wsPanelCopy.paletteCockpitLabel,
            subtitle: wsPanelCopy.paletteCockpitSubtitle,
            shortcut: "g c",
            targetRoute: "/cockpit",
          },
          {
            entryId: "nav-settings",
            category: "NAVIGATION",
            label: wsPanelCopy.paletteSettingsLabel,
            subtitle: wsPanelCopy.paletteSettingsSubtitle,
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
