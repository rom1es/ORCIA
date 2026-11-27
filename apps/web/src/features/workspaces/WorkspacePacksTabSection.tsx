import {
  OrciaAlertBanner,
  PackSlotBindingDrawer,
  WorkspacePacksPanel,
} from "@orcia/ui";
import React, { useMemo, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useI18n } from "../../i18n";
import { mergeWorkspaceAndFallbackSlotCandidates } from "../settings/packs/packMappers";
import { useWorkspacePacksController } from "../settings/packs/useWorkspacePacksController";

export interface WorkspacePacksTabSectionProps {
  readonly workspaceId: string;
}

export function WorkspacePacksTabSection({
  workspaceId,
}: WorkspacePacksTabSectionProps): React.ReactElement {
  const { dictionary } = useI18n();
  const packsUi = dictionary.packsUi;
  const { datasources, workspaces } = usePlatformSetup();
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const wsPacks = useWorkspacePacksController({
    workspaceId,
    onStatusMessage: setStatusMessage,
  });

  const activeWorkspaceName = workspaces.find((w) => w.workspaceId === workspaceId)?.name;
  const slotCandidates = useMemo(
    () =>
      mergeWorkspaceAndFallbackSlotCandidates(
        wsPacks.workspaceDatasources,
        datasources,
        activeWorkspaceName,
      ),
    [wsPacks.workspaceDatasources, datasources, activeWorkspaceName],
  );

  return (
    <div data-testid="workspace-packs-tab-section" className="flex flex-col gap-3">
      {statusMessage ? (
        <OrciaAlertBanner tone="emerald" role="status" testId="workspace-packs-status-banner">
          {statusMessage}
        </OrciaAlertBanner>
      ) : null}

      <WorkspacePacksPanel
        packs={wsPacks.packs}
        readOnlyObserver={wsPacks.readOnlyObserver}
        busySlug={wsPacks.busySlug}
        errorMessage={wsPacks.errorMessage}
        labels={packsUi.workspacePanel}
        onToggleActivate={(pack) => void wsPacks.handleToggleActivate(pack)}
        onMovePriority={(slug, dir) => void wsPacks.handleMovePriority(slug, dir)}
        onOpenSlotDrawer={wsPacks.openSlotDrawer}
      />

      <PackSlotBindingDrawer
        open={wsPacks.slotDrawerPack !== null}
        pack={wsPacks.slotDrawerPack}
        candidates={slotCandidates}
        highlightedMissingSlots={wsPacks.slotDrawerMissingSlots}
        readOnlyObserver={wsPacks.readOnlyObserver}
        isSaving={wsPacks.isSavingSlots}
        errorMessage={wsPacks.slotDrawerError}
        labels={packsUi.slotDrawer}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) wsPacks.closeSlotDrawer();
        }}
        onSaveBindings={wsPacks.handleSaveSlotBindings}
      />
    </div>
  );
}
