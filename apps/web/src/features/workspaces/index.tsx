import {
  CommandPaletteModal,
  type ControlCenterScopeType,
  type ProductLifecyclePhaseType,
  WorkspaceControlCenter,
  WorkspaceTopologyPanel,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePersonaContext } from "../../components/ShellContainer";
import {
  computePersonaTopology,
  DEFAULT_CATALOG_RESOURCES,
} from "../../components/workspaceFixtures";
import { useI18n } from "../../i18n";

export function WorkspacesFeaturePanel() {
  const { dictionary } = useI18n();
  const { fixtureMode, activePersona, setActivePersona } = usePersonaContext();
  const [scopeType, setScopeType] = useState<ControlCenterScopeType>("GLOBAL");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [phases, setPhases] = useState<Record<string, ProductLifecyclePhaseType>>({
    "ws-1": "BUILD",
    "ws-2": "MIGRATION",
  });

  const topologyData = fixtureMode
    ? computePersonaTopology(activePersona)
    : { workspaces: [], finopsTotal: 0 };

  const isObserver = activePersona === "claire";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div className="orcia-bento-card">
        <WorkspaceControlCenter
          scopeType={scopeType}
          scopeLabel={`Périmètre ${scopeType}`}
          isReadOnlyObserver={isObserver}
          consolidatedFinopsUsd={topologyData.finopsTotal || 13.15}
          contributorRuns={[
            {
              runId: "run-701",
              workspaceId: "ws-1",
              workspaceName: "Workspace 1 — Paiements & Checkout Web",
              title: "Run 701 — Arbitrage Topologie Paiements v2",
              status: "PAUSED_ARBITRATION",
              currentStepKey: "architecture-arbitration",
              executionMode: "COACHING",
              accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
              budgetConsumedUsd: 4.25,
              blackboardSummary: "Synthèse d'architecture prête pour arbitrage humain.",
            },
          ]}
          observerRuns={[
            {
              runId: "run-702",
              workspaceId: "ws-2",
              workspaceName: "Workspace 2 — Core Banking & Ledger",
              title: "Run 702 — Audit Bascule Core Ledger",
              status: "PAUSED_HUMAN_GATE",
              currentStepKey: "ledger-human-gate",
              executionMode: "FAST_PATH",
              accessMode: "READ_ONLY_OBSERVER",
              budgetConsumedUsd: 8.9,
              blackboardSummary: "Rapport de conformité Core Ledger généré.",
            },
          ]}
          datasources={[
            {
              id: "ds-1",
              workspaceName: "Workspace 1 — Paiements & Checkout Web",
              alias: "repo-checkout",
              scheme: "git",
              uri: "git://gitlab.entreprise.io/payments/checkout-web",
              executionIdentity: "passthrough",
              freshnessTtlDays: 90,
              tripartiteStatus: "ALIGNED",
            },
            {
              id: "ds-2",
              workspaceName: "Workspace 1 — Paiements & Checkout Web",
              alias: "wiki-archi",
              scheme: "confluence",
              uri: "confluence://ARCHI/payments-adr",
              executionIdentity: "passthrough",
              freshnessTtlDays: 14,
              tripartiteStatus: "STALE_WARNING",
            },
          ]}
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
              description: "Connecter les dépôts documentaires et bases.",
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
          workflowOverrides={[
            {
              workflowKey: "architecture-arbitration-flow",
              title: "Arbitrage Topologie & Gates Adaptatives",
              baseLayer: "v1.0.0 (Socle Plateforme)",
              teamOverride: "seuil_gate_agentique=0.85",
              workspaceOverride: "human_authored_required=true",
              userOverride: "mode_execution=COACHING",
              spineContractRef: "ARCHITECTURE-SPINE.md (AD-2)",
            },
          ]}
          workspacesGovernance={[
            {
              workspaceId: "ws-1",
              name: "Workspace 1 — Paiements & Checkout Web",
              visibilityMode: "STANDARD",
              lifecyclePhase: phases["ws-1"] ?? "BUILD",
              suggestedWorkflows: [
                "conception-architecture-cible",
                "livraison-incrementale-gouvernee",
              ],
              accessMode: isObserver
                ? "READ_ONLY_OBSERVER"
                : "CONTRIBUTOR_ACTION_REQUIRED",
              finopsCostUsd: 4.25,
            },
            {
              workspaceId: "ws-2",
              name: "Workspace 2 — Core Banking & Ledger",
              visibilityMode: "CONFIDENTIAL_RESTRICTED",
              lifecyclePhase: phases["ws-2"] ?? "MIGRATION",
              suggestedWorkflows: [
                "cartographie-dependances-existant",
                "plan-bascule-sans-interruption",
              ],
              accessMode: "READ_ONLY_OBSERVER",
              finopsCostUsd: 8.9,
              payloadMasked: true,
            },
          ]}
          labels={dictionary.controlCenter}
          onChangeScopeType={setScopeType}
          onSelectPhase={(wsId, phase) =>
            setPhases((prev) => ({ ...prev, [wsId]: phase }))
          }
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
            entryId: "run-701",
            category: "RUN",
            label: "Run 701 — Arbitrage Topologie Paiements v2",
            subtitle: "Workspace 1 • architecture-arbitration",
            shortcut: "Alt + ↑/↓",
            targetRoute: "/cockpit?runId=run-701",
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          },
        ]}
        labels={dictionary.commandPalette}
        onClose={() => setPaletteOpen(false)}
      />

      <div className="orcia-bento-card">
        <WorkspaceTopologyPanel
          activePersona={activePersona}
          workspaces={topologyData.workspaces}
          consolidatedFinopsUsd={topologyData.finopsTotal}
          catalogResources={fixtureMode ? DEFAULT_CATALOG_RESOURCES : []}
          labels={dictionary.workspaceTopology}
          showPersonaSimulator={fixtureMode}
          onSelectPersona={setActivePersona}
        />
      </div>
    </div>
  );
}
