import type { DeclarativePackSummaryResponse } from "@orcia/api-client";
import {
  OrciaAlertBanner,
  OrciaDataCard,
  PackComposerModal,
  type PackComposerScopeOption,
  PackImportModal,
  type PackImportScopeOption,
  PackSlotBindingDrawer,
  StatusBadge,
  WorkspacePacksPanel,
} from "@orcia/ui";
import React, { useMemo } from "react";
import { usePlatformSetup } from "../../../components/platformSetupStore";
import { useI18n } from "../../../i18n";
import { useAuthSessionStore } from "../../../stores/authSessionStore";
import { PackCardItem } from "./PackCardItem";
import { mergeWorkspaceAndFallbackSlotCandidates } from "./packMappers";
import { usePackComposerAndImportController } from "./usePackComposerAndImportController";
import { useWorkspacePacksController } from "./useWorkspacePacksController";

export interface DeclarativePacksRegistrySectionProps {
  readonly packs: readonly DeclarativePackSummaryResponse[];
  readonly selectedWorkspaceId: string;
  readonly onSelectedWorkspaceChange?: (wsId: string) => void;
  readonly onRefreshPacks: () => Promise<void> | void;
  readonly onExportPackZip: (packId: string) => void;
  readonly onStatusMessage: (msg: string) => void;
  readonly onErrorMessage: (msg: string) => void;
  readonly showInlineActionsBar?: boolean;
  readonly statusMessage?: string | null;
  readonly errorMessage?: string | null;
}

export function DeclarativePacksRegistrySection({
  packs,
  selectedWorkspaceId,
  onSelectedWorkspaceChange,
  onRefreshPacks,
  onExportPackZip,
  onStatusMessage,
  onErrorMessage,
  showInlineActionsBar = true,
  statusMessage = null,
  errorMessage = null,
}: DeclarativePacksRegistrySectionProps): React.ReactElement {
  const { dictionary, isFr } = useI18n();
  const packsUi = dictionary.packsUi;
  const actionsCopy = packsUi.actions;
  const { orgUnits, workspaces, datasources } = usePlatformSetup();
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);

  const importScopeOptions: readonly PackImportScopeOption[] = useMemo(
    () => [
      ...workspaces.map((ws) => ({
        id: ws.workspaceId,
        label: `${actionsCopy.scopeWorkspaceLabel} · ${ws.name}`,
        scopeType: "WORKSPACE" as const,
      })),
      ...orgUnits.map((unit) => ({
        id: unit.id,
        label: `${unit.level === "BU" ? actionsCopy.scopeBuLabel : actionsCopy.scopeTeamLabel} · ${unit.name}`,
        scopeType: (unit.level === "BU" ? "BU" : "TEAM") as "BU" | "TEAM",
      })),
    ],
    [actionsCopy.scopeBuLabel, actionsCopy.scopeTeamLabel, actionsCopy.scopeWorkspaceLabel, orgUnits, workspaces],
  );

  const composerScopeOptions: readonly PackComposerScopeOption[] = importScopeOptions;

  const wsPacks = useWorkspacePacksController({
    workspaceId: selectedWorkspaceId,
    onStatusMessage,
  });

  const composer = usePackComposerAndImportController({
    activeWorkspaceId: selectedWorkspaceId,
    onPacksMutated: async () => {
      await onRefreshPacks();
      await wsPacks.reloadWorkspacePacks();
    },
    onStatusMessage,
    onErrorMessage,
  });

  const activeWorkspaceName = workspaces.find(
    (w) => w.workspaceId === selectedWorkspaceId,
  )?.name;
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
    <div data-testid="declarative-packs-unified-section" className="flex flex-col gap-4">
      {errorMessage ? (
        <OrciaAlertBanner tone="crimson" role="alert" testId="declarative-packs-error-alert">
          {errorMessage}
        </OrciaAlertBanner>
      ) : null}
      {statusMessage ? (
        <OrciaAlertBanner tone="emerald" role="status" testId="declarative-packs-status-alert">
          {statusMessage}
        </OrciaAlertBanner>
      ) : null}

      {showInlineActionsBar ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          {onSelectedWorkspaceChange && workspaces.length > 0 ? (
            <select
              aria-label={dictionary.featureAdminCatalogSettings.packsRegistry.selectWorkspaceAriaLabel}
              data-testid="packs-unified-workspace-select"
              value={selectedWorkspaceId}
              onChange={(e) => onSelectedWorkspaceChange(e.target.value)}
              className="orcia-ds-select"
            >
              {workspaces.map((ws) => (
                <option key={ws.workspaceId} value={ws.workspaceId}>
                  {ws.name}
                </option>
              ))}
            </select>
          ) : (
            <div />
          )}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="open-pack-import-modal-btn"
              disabled={readOnlyObserver}
              onClick={() => composer.setImportModalOpen(true)}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
            >
              {actionsCopy.importPackBtn}
            </button>
            <button
              type="button"
              data-testid="open-pack-composer-modal-btn"
              disabled={readOnlyObserver}
              onClick={composer.openCreateComposer}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
            >
              {actionsCopy.newCustomPackBtn}
            </button>
          </div>
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "16px",
        }}
      >
        {packs.map((pack) => (
          <PackCardItem
            key={pack.bundle_id || pack.id}
            pack={pack}
            isFr={isFr}
            readOnlyObserver={readOnlyObserver}
            onExportZip={onExportPackZip}
            onUninstall={(bundleId, slug) => void composer.handleUninstallBundle(bundleId, slug)}
          />
        ))}
      </div>

      {selectedWorkspaceId ? (
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
      ) : null}

      <OrciaDataCard
        testId="pack-composer-drafts-card"
        icon="pack"
        title={actionsCopy.composerSectionTitle}
      >
        {composer.drafts.length === 0 ? (
          <p
            data-testid="pack-composer-drafts-empty"
            className="m-0 text-xs text-[var(--orcia-text-secondary)]"
          >
            {actionsCopy.composerEmptyMessage}
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {composer.drafts.map((draft) => (
              <div
                key={draft.bundleId}
                data-testid={`pack-composer-draft-row-${draft.slug}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded border p-3"
                style={{
                  borderColor: "var(--color-border-subtle)",
                  backgroundColor: "var(--color-bg-elevated)",
                }}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <strong className="text-sm">{draft.name}</strong>
                  <StatusBadge label={`v${draft.version}`} tone="cobalt" monospace />
                  <StatusBadge
                    label={
                      draft.status === "PUBLISHED"
                        ? actionsCopy.statusPublishedBadge
                        : actionsCopy.statusDraftBadge
                    }
                    tone={draft.status === "PUBLISHED" ? "emerald" : "amber"}
                  />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    data-testid={`edit-pack-draft-btn-${draft.slug}`}
                    onClick={() => void composer.openEditComposer(draft.bundleId)}
                    className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
                  >
                    {actionsCopy.editDraftBtn}
                  </button>
                  <button
                    type="button"
                    data-testid={`delete-pack-draft-btn-${draft.slug}`}
                    disabled={readOnlyObserver}
                    onClick={() => void composer.handleDeleteDraft(draft.bundleId, draft.slug)}
                    className="orcia-ds-btn orcia-ds-btn-danger orcia-ds-btn-sm"
                  >
                    {actionsCopy.deleteDraftBtn}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </OrciaDataCard>

      <PackImportModal
        open={composer.importModalOpen}
        scopeOptions={importScopeOptions}
        defaultWorkspaceId={selectedWorkspaceId}
        readOnlyObserver={readOnlyObserver}
        isSubmitting={composer.isImporting}
        errorMessage={composer.importError}
        labels={packsUi.importModal}
        onOpenChange={composer.setImportModalOpen}
        onSubmitImport={composer.handleImportPackFile}
      />

      <PackComposerModal
        open={composer.composerOpen}
        draft={composer.activeDraft}
        availableMembers={composer.availableMembers}
        scopeOptions={composerScopeOptions}
        defaultScopeId={selectedWorkspaceId}
        readOnlyObserver={readOnlyObserver}
        isBusy={composer.isComposerBusy}
        errorMessage={composer.composerError}
        labels={packsUi.composerModal}
        onOpenChange={composer.setComposerOpen}
        onSaveDraft={composer.handleSaveDraft}
        onPublishDraft={composer.handlePublishDraft}
        onExportDraftZip={composer.handleExportDraftZip}
      />

      <PackSlotBindingDrawer
        open={wsPacks.slotDrawerPack !== null}
        pack={wsPacks.slotDrawerPack}
        candidates={slotCandidates}
        highlightedMissingSlots={wsPacks.slotDrawerMissingSlots}
        readOnlyObserver={readOnlyObserver}
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
