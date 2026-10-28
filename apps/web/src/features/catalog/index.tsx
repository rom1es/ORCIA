import { CatalogExplorerPanel } from "@orcia/ui";
import React from "react";
import { usePersonaContext } from "../../components/ShellContainer";
import {
  DEFAULT_CATALOG_EXPLORER_ITEMS,
  DEFAULT_RUN_LOCK_TRIPLETS,
} from "../../components/workspaceFixtures";
import { useI18n } from "../../i18n";

export function CatalogFeaturePanel() {
  const { dictionary } = useI18n();
  const { fixtureMode, activePersona } = usePersonaContext();

  return (
    <div className="orcia-bento-card">
      <CatalogExplorerPanel
        activePersona={activePersona}
        items={fixtureMode ? DEFAULT_CATALOG_EXPLORER_ITEMS : []}
        runLockTriplets={fixtureMode ? DEFAULT_RUN_LOCK_TRIPLETS : []}
        labels={dictionary.catalogExplorer}
      />
    </div>
  );
}
