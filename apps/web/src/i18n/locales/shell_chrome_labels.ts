export interface ShellChromeDictionary {
  readonly brandName: string;
  readonly guestDisplayNameFallback: string;
  readonly loadingSession: string;
  readonly loginInitializing: string;
  readonly firstBootMandatoryBadge: string;
  readonly inboxNotificationsSubtitle: string;
  readonly inboxNotificationsDescription: string;
  readonly rootErrorBoundary: {
    readonly unexpectedError: string;
    readonly reloadPage: string;
  };
  readonly temporaryPasswordBanner: {
    readonly warningText: string;
    readonly changePasswordCta: string;
  };
  readonly simplifiedProcessBuilder: {
    readonly title: string;
    readonly description: string;
    readonly publishedBadgeTemplate: string;
    readonly draftsBadgeTemplate: string;
    readonly newProcessCta: string;
    readonly openProcessesMenuCta: string;
    readonly savedProcessesTitle: string;
    readonly savedProcessesCountTemplate: string;
    readonly emptyState: string;
    readonly statusPublished: string;
    readonly statusDraft: string;
  };
  readonly createProcessDialog: {
    readonly dialogTitle: string;
    readonly closeLabel: string;
    readonly nameLabel: string;
    readonly namePlaceholder: string;
    readonly keyLabel: string;
    readonly keyPlaceholder: string;
    readonly statusLabel: string;
    readonly statusDraft: string;
    readonly statusPublished: string;
    readonly prePromptLabel: string;
    readonly prePromptHelpLabel: string;
    readonly prePromptPlaceholder: string;
    readonly contractHeading: string;
    readonly contractHelpLabel: string;
    readonly paramsPlaceholder: string;
    readonly sectionsPlaceholder: string;
    readonly layersHeading: string;
    readonly layersHelpLabel: string;
    readonly stepEnabled: string;
    readonly stepSkipped: string;
    readonly versionTemplate: string;
    readonly cancelCta: string;
    readonly saveCta: string;
    readonly defaultLayers: {
      readonly ctx: string;
      readonly agent: string;
      readonly out: string;
    };
  };
  readonly platformSetupGovernance: {
    readonly adminInitErrorContext: string;
    readonly aiModelConfigErrorContext: string;
    readonly defaultAdminDisplayName: string;
    readonly divisionLabel: string;
    readonly teamLabel: string;
    readonly roleLabel: string;
    readonly userLabel: string;
    readonly globalScopeLabel: string;
    readonly userLaunchedSummary: string;
    readonly teamScopePrefix: string;
    readonly spaceScopePrefix: string;
    readonly adminCreatedTemplate: string;
    readonly teamDetachedTemplate: string;
    readonly teamAttachedTemplate: string;
    readonly orgUnitCreatedTemplate: string;
    readonly grantCreatedTemplate: string;
    readonly grantRevokedTemplate: string;
    readonly llmTierConfiguredTemplate: string;
    readonly packDeactivatedTemplate: string;
    readonly runLaunchedTemplate: string;
    readonly ontologyConceptCreatedTemplate: string;
  };
  readonly auditSanitizer: {
    readonly globalScopeLabel: string;
    readonly onGlobalPhrase: string;
    readonly statusPublished: string;
    readonly statusDraft: string;
    readonly statusValidated: string;
    readonly personalIdentityMode: string;
    readonly sharedAccountMode: string;
  };
}
