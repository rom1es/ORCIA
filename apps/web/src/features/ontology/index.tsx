import { OntologyAndKbExplorerPanel } from "@orcia/ui";
import React from "react";
import { usePersonaContext } from "../../components/ShellContainer";
import {
  DEFAULT_ONTOLOGY_CONCEPTS,
  DEFAULT_STALE_ALERTS,
  DEFAULT_TRIPARTITE_EDGES,
} from "../../components/workspaceFixtures";
import { useI18n } from "../../i18n";

export function OntologyFeaturePanel() {
  const { dictionary } = useI18n();
  const { fixtureMode } = usePersonaContext();

  return (
    <div className="orcia-bento-card">
      <OntologyAndKbExplorerPanel
        concepts={fixtureMode ? DEFAULT_ONTOLOGY_CONCEPTS : []}
        tripartiteEdges={fixtureMode ? DEFAULT_TRIPARTITE_EDGES : []}
        staleAlerts={fixtureMode ? DEFAULT_STALE_ALERTS : []}
        labels={dictionary.ontologyExplorer}
      />
    </div>
  );
}
