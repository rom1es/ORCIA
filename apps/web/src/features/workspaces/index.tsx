import {
  CommandPaletteModal,
  ContextualInfoTriggerButton,
  DnaStarlarkCompilerAndGlossaryLifecycleView,
  type ControlCenterScopeType,
  type ProductLifecyclePhaseType,
  type UiDatasourceScheme,
  type WorkspaceSubTabKey,
  WorkspaceControlCenter,
  WorkspaceFiveTabsAndExternalRebaseView,
  WorkspaceTopologyPanel,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function WorkspacesFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { openHelpSection } = useShellNavigation();
  const isFr = locale === "fr";
  const {
    workspaces,
    datasources,
    runs,
    workflowOverrides,
    createWorkspace,
    updateWorkspacePhase,
  } = usePlatformSetup();

  const [scopeType, setScopeType] = useState<ControlCenterScopeType>("GLOBAL");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState<WorkspaceSubTabKey>("OVERVIEW");

  // Create Workspace form state (starts 100% empty)
  const [wsName, setWsName] = useState("");
  const [wsSlug, setWsSlug] = useState("");
  const [wsVisibility, setWsVisibility] = useState<
    "STANDARD" | "CONFIDENTIAL_RESTRICTED"
  >("STANDARD");
  const [wsPhase, setWsPhase] = useState<ProductLifecyclePhaseType>("BUILD");

  const handleCreateWorkspace = (e: React.FormEvent) => {
    e.preventDefault();
    if (!wsName.trim()) return;
    createWorkspace({
      name: wsName.trim(),
      slug: wsSlug.trim() || wsName.trim().toLowerCase().replace(/\s+/g, "-"),
      visibilityMode: wsVisibility,
      lifecyclePhase: wsPhase,
    });
    setWsName("");
    setWsSlug("");
  };

  const consolidatedFinopsUsd = workspaces.reduce(
    (sum, ws) => sum + (ws.finopsCostUsd ?? 0),
    0,
  );

  const inputStyle: React.CSSProperties = {
    padding: "7px 10px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--color-border)",
    backgroundColor: "var(--color-surface-card)",
    color: "var(--color-foreground)",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <section
        data-testid="create-workspace-panel"
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "12px" }}
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

        <form
          data-testid="create-workspace-form"
          onSubmit={handleCreateWorkspace}
          style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}
        >
          <input
            type="text"
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
            data-testid="workspace-slug-input"
            value={wsSlug}
            onChange={(e) => setWsSlug(e.target.value)}
            placeholder={isFr ? "Identifiant court (optionnel)..." : "Short ID (optional)..."}
            style={inputStyle}
          />
          <select
            data-testid="workspace-visibility-select"
            value={wsVisibility}
            onChange={(e) =>
              setWsVisibility(
                e.target.value as "STANDARD" | "CONFIDENTIAL_RESTRICTED",
              )
            }
            style={inputStyle}
          >
            <option value="STANDARD">{isFr ? "Standard" : "Standard"}</option>
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
            style={{
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              backgroundColor: "var(--color-primary-cobalt)",
              color: "var(--color-primary-foreground)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isFr ? "+ Créer l'Espace" : "+ Create Workspace"}
          </button>
        </form>
      </section>

      <div className="orcia-bento-card">
        <WorkspaceControlCenter
          scopeType={scopeType}
          scopeLabel={`Périmètre ${scopeType}`}
          isReadOnlyObserver={false}
          consolidatedFinopsUsd={consolidatedFinopsUsd}
          contributorRuns={runs}
          observerRuns={[]}
          datasources={datasources}
          guidanceSteps={[
            {
              stepNumber: 1,
              title: "1. Choisir la phase actuelle de l'Espace",
              description: "Indiquez si l'équipe est en phase de Construction, d'Exploitation ou d'Évolution.",
              actionCommand: "set-lifecycle-phase",
            },
            {
              stepNumber: 2,
              title: "2. Connecter les sources documentaires et outils",
              description: "Ajoutez vos espaces documentaires, suivis de projets et dépôts dans Configuration.",
              actionCommand: "init-datasource",
            },
            {
              stepNumber: 3,
              title: "3. Choisir le mode de connexion aux sources",
              description: "Utilisez le compte personnel de chaque membre ou un compte partagé d'équipe.",
              actionCommand: "configure-execution-identity",
            },
            {
              stepNumber: 4,
              title: "4. Vérifier l'actualité de vos documents",
              description: "Consultez les alertes signalant des documents à mettre à jour.",
              actionCommand: "sync-tripartite-graph",
            },
            {
              stepNumber: 5,
              title: "5. Activer vos processus métiers",
              description: "Adaptez les étapes à votre équipe et lancez votre premier processus.",
              actionCommand: "launch-supervised-run",
            },
          ]}
          workflowOverrides={workflowOverrides}
          workspacesGovernance={workspaces}
          labels={dictionary.controlCenter}
          onChangeScopeType={setScopeType}
          onSelectPhase={updateWorkspacePhase}
          onOpenCommandPalette={() => setPaletteOpen(true)}
        />
      </div>

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
        onClose={() => setPaletteOpen(false)}
      />

      <div className="orcia-bento-card">
        <WorkspaceTopologyPanel
          activePersona="marc"
          workspaces={workspaces.map((ws) => ({
            id: ws.workspaceId,
            name: ws.name,
            ownerOrgUnitName: "Plateforme Globale ORCIA",
            visibilityMode: ws.visibilityMode,
            effectiveRole: "PLATFORM_ADMIN",
            accessMode: ws.accessMode,
            accessOrigin: "GLOBAL_ADMIN",
            finopsCostUsd: ws.finopsCostUsd,
            datasources: datasources
              .filter((d) => d.workspaceName === ws.name)
              .map((d) => ({
                id: d.id,
                alias: d.alias,
                scheme: d.scheme as UiDatasourceScheme,
                uri: d.uri,
                role: d.executionIdentity,
              })),
          }))}
          consolidatedFinopsUsd={consolidatedFinopsUsd}
          catalogResources={[]}
          labels={dictionary.workspaceTopology}
          showPersonaSimulator={false}
          onSelectPersona={() => undefined}
        />
      </div>

      {/* Story 11.1 — Mes Espaces à 5 Sous-Onglets (démarre 100 % vide) */}
      <WorkspaceFiveTabsAndExternalRebaseView
        workspaceSlug={workspaces[0]?.workspaceId ?? ""}
        activeTab={activeSubTab}
        defaultArtifactDestinationUri=""
        pendingGlossaryCandidatesCount={0}
        sources={[]}
        activeWaivers={[]}
        rebasedChunks={[]}
        labels={dictionary.workspaceFiveTabs}
        onSelectTab={setActiveSubTab}
      />

      {/* Story 11.2 — Règles Métiers Automatiques & Glossaire (démarre 100 % vide) */}
      <DnaStarlarkCompilerAndGlossaryLifecycleView
        mechanism={null}
        pendingQueueCandidates={[]}
        top3PrecheckedCandidates={[]}
        labels={dictionary.dnaStarlarkGlossary}
      />
    </div>
  );
}
