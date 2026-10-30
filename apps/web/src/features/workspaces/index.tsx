import {
  CommandPaletteModal,
  type ControlCenterScopeType,
  type ProductLifecyclePhaseType,
  type UiDatasourceScheme,
  WorkspaceControlCenter,
  WorkspaceTopologyPanel,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useI18n } from "../../i18n";

export function WorkspacesFeaturePanel() {
  const { dictionary, locale } = useI18n();
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
        <div>
          <h2 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>
            {isFr
              ? "Initialiser un Nouvel Espace de Travail (Workspace)"
              : "Initialize a New Solution Workspace"}
          </h2>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {isFr
              ? "Créez un Espace de Travail pour déverrouiller le sélecteur de périmètre (⌘W), rattacher des sources documentaires et lancer des Runs."
              : "Create a Workspace to unlock the scope switcher (⌘W), attach knowledge sources, and launch Runs."}
          </p>
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
            placeholder={isFr ? "Identifiant / Slug..." : "Slug..."}
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
            <option value="STANDARD">STANDARD</option>
            <option value="CONFIDENTIAL_RESTRICTED">CONFIDENTIAL_RESTRICTED</option>
          </select>
          <select
            data-testid="workspace-phase-select"
            value={wsPhase}
            onChange={(e) =>
              setWsPhase(e.target.value as ProductLifecyclePhaseType)
            }
            style={inputStyle}
          >
            <option value="BUILD">BUILD</option>
            <option value="RUN">RUN</option>
            <option value="MIGRATION">MIGRATION</option>
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
            {isFr ? "+ Créer le Workspace" : "+ Create Workspace"}
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
              title: "1. Qualifier la phase du Produit / Workspace",
              description: "Sélectionner RUN, BUILD ou MIGRATION.",
              actionCommand: "set-lifecycle-phase",
            },
            {
              stepNumber: 2,
              title: "2. Rattacher les sources dédiées et partagées",
              description: "Connecter les dépôts documentaires et bases dans /settings.",
              actionCommand: "init-datasource",
            },
            {
              stepNumber: 3,
              title: "3. Configurer l'identité d'exécution",
              description: "Choisir passthrough ou service_account.",
              actionCommand: "configure-execution-identity",
            },
            {
              stepNumber: 4,
              title: "4. Vérifier l'alignement dans le Graphe Tripartite",
              description: "Inspecter les alertes [STALE_WARNING].",
              actionCommand: "sync-tripartite-graph",
            },
            {
              stepNumber: 5,
              title: "5. Activer les Workflows et Surcharges 4 niveaux",
              description: "Valider les Gates et lancer un Run supervisé.",
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
            label: "Aller au Cockpit & Flux de Travail",
            subtitle: "Navigation rapide",
            shortcut: "g c",
            targetRoute: "/cockpit",
          },
          {
            entryId: "nav-settings",
            category: "NAVIGATION",
            label: "Ouvrir le Hub de Paramétrage (/settings)",
            subtitle: "IAM, Modèles IA, Connecteurs, Packs, Studio",
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
    </div>
  );
}
