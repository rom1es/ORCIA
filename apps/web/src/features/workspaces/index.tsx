import { WorkspaceTopologyPanel } from "@orcia/ui";
import React from "react";
import { usePersonaContext } from "../../components/ShellContainer";
import {
  computePersonaTopology,
  DEFAULT_CATALOG_RESOURCES,
} from "../../components/workspaceFixtures";
import { useI18n } from "../../i18n";

export function WorkspacesFeaturePanel() {
  const { dictionary } = useI18n();
  const { fixtureMode, activePersona, setActivePersona } = usePersonaContext();
  const topologyData = fixtureMode
    ? computePersonaTopology(activePersona)
    : { workspaces: [], finopsTotal: 0 };

  return (
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
  );
}
