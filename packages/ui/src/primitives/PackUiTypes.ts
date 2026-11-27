export type UiPackScopeType = "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
export type UiPackSlotTargetKind =
  | "UNBOUND"
  | "WORKSPACE_DATASOURCE"
  | "ENTERPRISE_CONNECTOR"
  | "INTERNAL";

export interface UiPackSlotSpec {
  readonly slotKey: string;
  readonly scheme: string;
  readonly connectorKind: string;
  readonly sourceNature: string;
  readonly required: boolean;
  readonly description: string;
}

export interface UiPackSlotBindingItem {
  readonly slotKey: string;
  readonly targetKind: UiPackSlotTargetKind;
  readonly targetId: string | null;
  readonly targetDisplayName: string | null;
  readonly targetUri: string | null;
  readonly targetEnabled: boolean;
  readonly isEffectiveBound: boolean;
}

export interface UiPackSlotTargetCandidate {
  readonly targetKind: Exclude<UiPackSlotTargetKind, "UNBOUND">;
  readonly targetId: string;
  readonly label: string;
  readonly scheme: string;
  readonly uri: string;
}

export interface UiWorkspacePackItem {
  readonly bundleId: string;
  readonly packId: string;
  readonly slug: string;
  readonly name: string;
  readonly version: string;
  readonly bundleKind: "SYSTEM" | "CUSTOM" | string;
  readonly scopeType: string;
  readonly scopeId: string;
  readonly status: string;
  readonly archiveSha256: string;
  readonly description: string;
  readonly isActive: boolean;
  readonly priorityOrder: number | null;
  readonly declaredSlots: readonly UiPackSlotSpec[];
  readonly slotBindings: readonly UiPackSlotBindingItem[];
  readonly missingSlots: readonly string[];
  readonly readinessOk: boolean;
}

export type UiPackComposerEntityType =
  | "AGENT"
  | "SKILL"
  | "INSTRUCTION"
  | "WORKFLOW_V2"
  | "VSM_V2"
  | "ONTOLOGY_CONCEPT"
  | "ONTOLOGY_RELATION"
  | "ONTOLOGY_AXIOM"
  | "DNA_MECHANISM"
  | "POLICY"
  | "HELP_ARTICLE";

export interface UiPackDraftMemberOption {
  readonly entityType: UiPackComposerEntityType;
  readonly entityId: string;
  readonly entitySlug: string;
  readonly title: string;
  readonly lifecycleStatus: string;
}

export interface UiPackClosureIssue {
  readonly entityType: string;
  readonly entityId: string;
  readonly reason: string;
  readonly referencedBy: string;
}

export interface UiPackProseWarning {
  readonly entityType: string;
  readonly entitySlug: string;
  readonly token: string;
  readonly message: string;
}

export interface UiPackDraftItem {
  readonly bundleId: string;
  readonly slug: string;
  readonly name: string;
  readonly version: string;
  readonly description: string;
  readonly author: string;
  readonly license: string;
  readonly scopeType: "BU" | "TEAM" | "WORKSPACE";
  readonly scopeId: string;
  readonly status: "DRAFT" | "PUBLISHED" | "DEPRECATED" | string;
  readonly members: readonly UiPackDraftMemberOption[];
  readonly closureComplete: boolean;
  readonly missingDependencies: readonly UiPackClosureIssue[];
  readonly nonActiveDependencies: readonly UiPackClosureIssue[];
  readonly proseWarnings: readonly UiPackProseWarning[];
}

export interface UiDraftPackReference {
  readonly bundleId: string;
  readonly slug: string;
  readonly name: string;
  readonly version: string;
}

export interface PackImportModalLabels {
  readonly modalTitle: string;
  readonly modalDescription: string;
  readonly closeLabel: string;
  readonly fileFieldLabel: string;
  readonly chooseFileBtn: string;
  readonly noFileSelected: string;
  readonly scopeTypeLabel: string;
  readonly scopeTargetLabel: string;
  readonly scopeGlobalLabel: string;
  readonly scopeBuLabel: string;
  readonly scopeTeamLabel: string;
  readonly scopeWorkspaceLabel: string;
  readonly replaceDraftLabel: string;
  readonly submitBtn: string;
  readonly submittingBtn: string;
  readonly cancelBtn: string;
  readonly observerBlockedHint: string;
}

export interface PackSlotBindingDrawerLabels {
  readonly drawerTitlePrefix: string;
  readonly drawerDescription: string;
  readonly closeLabel: string;
  readonly requiredBadge: string;
  readonly optionalBadge: string;
  readonly readyBadge: string;
  readonly missingBadge: string;
  readonly optionalUnboundBadge: string;
  readonly targetSelectLabel: string;
  readonly unboundOptionLabel: string;
  readonly missingSlotsAlertTitle: string;
  readonly noSlotsMessage: string;
  readonly saveBtn: string;
  readonly savingBtn: string;
  readonly cancelBtn: string;
  readonly observerBlockedHint: string;
}

export interface PackComposerModalLabels {
  readonly createTitle: string;
  readonly editTitle: string;
  readonly closeLabel: string;
  readonly stepMetadataTab: string;
  readonly stepMembersTab: string;
  readonly slugLabel: string;
  readonly nameLabel: string;
  readonly versionLabel: string;
  readonly descriptionLabel: string;
  readonly authorLabel: string;
  readonly licenseLabel: string;
  readonly scopeTypeLabel: string;
  readonly scopeTargetLabel: string;
  readonly scopeBuLabel: string;
  readonly scopeTeamLabel: string;
  readonly scopeWorkspaceLabel: string;
  readonly membersSearchPlaceholder: string;
  readonly membersEmptyHint: string;
  readonly closureCompleteBadge: string;
  readonly closureIncompleteBadge: string;
  readonly missingDependenciesTitle: string;
  readonly proseWarningsTitle: string;
  readonly autoIncludeDependenciesLabel: string;
  readonly saveDraftBtn: string;
  readonly publishBtn: string;
  readonly exportZipBtn: string;
  readonly savingBtn: string;
  readonly entityTypeLabels: Readonly<Record<UiPackComposerEntityType, string>>;
}

export interface EntityUnlinkConfirmDialogLabels {
  readonly title: string;
  readonly descriptionPrefix: string;
  readonly referencingDraftsHeading: string;
  readonly confirmBtn: string;
  readonly confirmingBtn: string;
  readonly cancelBtn: string;
}

export interface WorkspacePacksPanelLabels {
  readonly cardTitle: string;
  readonly cardSubtitle: string;
  readonly emptyMessage: string;
  readonly systemOriginBadge: string;
  readonly customOriginBadge: string;
  readonly activeBadge: string;
  readonly inactiveBadge: string;
  readonly priorityPrefix: string;
  readonly moveUpAriaLabel: string;
  readonly moveDownAriaLabel: string;
  readonly slotReadyBadge: string;
  readonly slotUnboundBadge: string;
  readonly slotOptionalUnboundBadge: string;
  readonly activateBtn: string;
  readonly deactivateBtn: string;
  readonly configureSlotsBtn: string;
  readonly observerReadOnlyNotice: string;
}
