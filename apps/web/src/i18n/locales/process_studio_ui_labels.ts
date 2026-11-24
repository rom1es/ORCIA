export interface ProcessCatalogItemLabel {
  readonly id: string;
  readonly label: string;
}

export interface ProcessDelegateAgentLabel {
  readonly slug: string;
  readonly label: string;
  readonly role: string;
}

export interface ProcessStudioGateCatalogItem {
  readonly id: string;
  readonly name: string;
  readonly runner:
    | "markdown_contract_runner"
    | "json_schema_runner"
    | "cli_sandbox_runner"
    | "catalog_invariant_runner";
}

export interface ProcessStudioUiDictionary {
  readonly hub: {
    readonly catalogResourceLabel: string;
    readonly pendingValidationBadge: string;
    readonly activeDossiersTitle: string;
    readonly activeDossiersSubtitle: string;
    readonly reviewPendingDossierBtn: string;
    readonly featuredDossierPrefix: string;
    readonly featuredStepBadge: string;
    readonly featuredReadySummary: string;
    readonly openDeliverableBtn: string;
    readonly availableProcessesTitle: string;
    readonly availableProcessesSubtitle: string;
    readonly filterProcessesAriaLabel: string;
    readonly filterAll: string;
    readonly filterActive: string;
    readonly filterDrafts: string;
    readonly filterExternalIde: string;
    readonly newProcessBtn: string;
    readonly stepNumberBadgeTemplate: string;
    readonly crossCuttingProcessBadge: string;
    readonly ideAndTeamBadge: string;
    readonly statusActiveBadge: string;
    readonly statusDraftBadge: string;
    readonly launchProcessBtn: string;
    readonly customizeInStudioBtn: string;
    readonly vsmOverviewEyebrow: string;
    readonly vsmOverviewSubtitle: string;
    readonly exploreFullVsmBtn: string;
    readonly vsmPhaseStepsRangeTemplate: string;
    readonly vsmStepsCountUnit: string;
  };
  readonly studio: {
    readonly backToProcessesBtn: string;
    readonly viewStepInVsmTemplate: string;
    readonly activeVersionBadgeTemplate: string;
    readonly draftVersionBadgeTemplate: string;
    readonly studioTitleTemplate: string;
    readonly viewModesAriaLabel: string;
    readonly tabStepsAndRules: string;
    readonly tabSimulateImpact: string;
    readonly tabSpecification: string;
    readonly saveDraftBtn: string;
    readonly publishBtn: string;
    readonly testRunBtn: string;
    readonly skillAttachedBanner: string;
    readonly toolAttachedBanner: string;
    readonly gateAttachedTemplate: string;
    readonly block1Title: string;
    readonly block1InputsLabel: string;
    readonly block1OutputsLabel: string;
    readonly block1CriteriaLabel: string;
    readonly block1CriteriaValue: string;
    readonly block2GuidedOrciaBtn: string;
    readonly block2ExternalIdeBtn: string;
    readonly block2ExternalBannerTitle: string;
    readonly block2ExternalBannerDesc: string;
    readonly block2StepLabelTemplate: string;
    readonly block2HumanReviewBadge: string;
    readonly block2ConfirmPublishBadge: string;
    readonly block2StepEnabledBtn: string;
    readonly block2StepSkippedBtn: string;
    readonly block2GoalLabel: string;
    readonly block2ExpectedOutputLabel: string;
    readonly block3Title: string;
    readonly block4Title: string;
    readonly block5Title: string;
    readonly block5AutomatedTitle: string;
    readonly block5ChallengerTitle: string;
    readonly simulationTitle: string;
    readonly rerunSimulationBtn: string;
    readonly simulationStepsVerifiedLabel: string;
    readonly simulationExternalWritesLabel: string;
    readonly simulationZeroIsolatedValue: string;
    readonly simulationChecksLabel: string;
    readonly simulationCompliantValue: string;
    readonly simulationEstimatedCostLabel: string;
    readonly declarativeSpecTitle: string;
    readonly copilotTitle: string;
    readonly copilotSubtitle: string;
    readonly copilotWelcomeMessage: string;
    readonly copilotReplyTemplate: string;
    readonly copilotAdvicePrefix: string;
    readonly copilotUserPrefix: string;
    readonly copilotPlaceholder: string;
    readonly copilotAskBtn: string;
    readonly copilotToolsHeading: string;
    readonly copilotSkillsHeading: string;
    readonly copilotGatesHeading: string;
    readonly mapperDefaultParamTemplate: string;
    readonly mapperDefaultTriggerLabel: string;
    readonly mapperDefaultExitCriteria: readonly string[];
    readonly humanToolLabels: Readonly<Record<string, string>>;
    readonly humanSkillLabels: Readonly<Record<string, string>>;
    readonly humanKbLabels: Readonly<Record<string, string>>;
    readonly delegateAgents: readonly ProcessDelegateAgentLabel[];
    readonly copilotTools: readonly ProcessCatalogItemLabel[];
    readonly copilotSkills: readonly ProcessCatalogItemLabel[];
    readonly copilotGates: readonly ProcessStudioGateCatalogItem[];
  };
}
