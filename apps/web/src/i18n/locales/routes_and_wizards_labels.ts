import type { DurableWizardStepDescriptor, StatusBadgeTone } from "@orcia/ui";

export interface ActivityEventLabelSpec {
  readonly label: string;
  readonly tone: StatusBadgeTone;
}

export interface RoutesAndWizardsDictionary {
  readonly activityEvents: Readonly<Record<string, ActivityEventLabelSpec>>;
  readonly settingsHubExtra: {
    readonly tabsAriaLabel: string;
    readonly restrictedAccessBadge: string;
    readonly rootSuffix: string;
  };
  readonly aiModelsQuickForm: {
    readonly summaryLabel: string;
    readonly geminiProtocolLabel: string;
    readonly geminiModeNative: string;
    readonly geminiModeOpenai: string;
    readonly providerLabel: string;
    readonly primaryModelLabel: string;
    readonly secondaryModelLabel: string;
    readonly endpointUrlLabel: string;
    readonly authModeLabel: string;
    readonly authApiKeyOption: string;
    readonly authEnvVarOption: string;
    readonly authNoneLocalOption: string;
    readonly apiKeyLabel: string;
    readonly testConnectionCta: string;
    readonly saveTierCta: string;
  };
  readonly settingsPacks: {
    readonly catalogErrorContext: string;
    readonly entirePlatformLabel: string;
    readonly divisionLabel: string;
    readonly teamLabel: string;
    readonly workspaceLabel: string;
    readonly catalogTitle: string;
    readonly targetScopeLabel: string;
    readonly activeBadgePrefix: string;
    readonly globalAlreadyCoveredNote: string;
    readonly countsTemplate: string;
    readonly disableGlobalCta: string;
    readonly disableScopeCta: string;
    readonly enableOnScopeTemplate: string;
    readonly emptyState: string;
  };
  readonly orgUnitsActions: {
    readonly divisionLabel: string;
    readonly teamLabel: string;
    readonly createdTemplate: string;
    readonly updatedTemplate: string;
    readonly membersUpdatedTemplate: string;
    readonly deletedTemplate: string;
    readonly secopsDeletedTemplate: string;
    readonly secopsBulkDeletedTemplate: string;
  };
  readonly wizardsStepForm: {
    readonly steps: readonly DurableWizardStepDescriptor[];
    readonly orgUnitLabel: string;
    readonly orgUnitPlaceholder: string;
    readonly workspaceLabel: string;
    readonly workspacePlaceholder: string;
    readonly connectorAliasPlaceholder: string;
    readonly connectorUriPlaceholder: string;
    readonly primaryModelLabel: string;
    readonly primaryModelPlaceholder: string;
    readonly reviewInstruction: string;
  };
}
