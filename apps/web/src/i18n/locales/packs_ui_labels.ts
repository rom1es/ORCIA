import type {
  EntityUnlinkConfirmDialogLabels,
  PackComposerModalLabels,
  PackImportModalLabels,
  PackSlotBindingDrawerLabels,
  WorkspacePacksPanelLabels,
} from "@orcia/ui";

export interface PacksRegistryActionsLabels {
  readonly importPackBtn: string;
  readonly newCustomPackBtn: string;
  readonly uninstallPackBtn: string;
  readonly uninstallSuccessTemplate: string;
  readonly importSuccessTemplate: string;
  readonly composerSectionTitle: string;
  readonly composerEmptyMessage: string;
  readonly editDraftBtn: string;
  readonly deleteDraftBtn: string;
  readonly draftDeletedTemplate: string;
  readonly draftSavedTemplate: string;
  readonly draftPublishedTemplate: string;
  readonly systemOriginBadge: string;
  readonly customOriginBadge: string;
  readonly statusDraftBadge: string;
  readonly statusPublishedBadge: string;
  readonly scopeGlobalLabel: string;
  readonly scopeWorkspaceLabel: string;
  readonly scopeTeamLabel: string;
  readonly scopeBuLabel: string;
  readonly deleteEntityBtn: string;
  readonly deleteWorkflowConfirmLabel: string;
  readonly entityUnlinkedTemplate: string;
  readonly slotBoundSuccessTemplate: string;
  readonly packActivatedSuccessTemplate: string;
  readonly packDeactivatedSuccessTemplate: string;
  readonly packReorderedSuccess: string;
}

export interface PacksUiDictionarySection {
  readonly actions: PacksRegistryActionsLabels;
  readonly importModal: PackImportModalLabels;
  readonly slotDrawer: PackSlotBindingDrawerLabels;
  readonly composerModal: PackComposerModalLabels;
  readonly unlinkDialog: EntityUnlinkConfirmDialogLabels;
  readonly workspacePanel: WorkspacePacksPanelLabels;
}
