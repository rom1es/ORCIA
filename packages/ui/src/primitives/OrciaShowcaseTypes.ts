export type OrciaShowcasePillarTabKey =
  | "macro"
  | "features"
  | "architecture"
  | "changelog";

export interface OrciaShowcaseInstalledPackItem {
  readonly key: string;
  readonly version: string;
  readonly description: string;
}

export interface OrciaShowcaseArchitectureDecisionItem {
  readonly code: string;
  readonly title: string;
}

export interface OrciaShowcaseStackComponentItem {
  readonly name: string;
  readonly version: string;
}

export interface OrciaShowcaseTechLeadReportItem {
  readonly date: string;
  readonly phaseOrStory: string;
  readonly reportFile: string;
  readonly domain: string;
  readonly summary: string;
}

export interface OrciaShowcaseManifestStats {
  readonly activeRoutesCount: number;
  readonly uiPrimitivesCount: number;
  readonly installedPacksCount: number;
  readonly alembicMigrationsCount: number;
  readonly architectureDecisionsCount: number;
  readonly stackComponentsCount: number;
  readonly techLeadReportsCount: number;
  readonly capabilitiesCount?: number;
  readonly liveCapabilitiesCount?: number;
  readonly verifiedCapabilitiesCount?: number;
  readonly userJourneysCount?: number;
  readonly coveredUserJourneysCount?: number;
  readonly e2eCoveredCapabilitiesCount?: number;
}

export interface OrciaShowcaseManifestData {
  readonly lastSyncedDate: string;
  readonly stats: OrciaShowcaseManifestStats;
  readonly activeRoutes: readonly string[];
  readonly uiPrimitives: readonly string[];
  readonly installedPacks: readonly OrciaShowcaseInstalledPackItem[];
  readonly alembicMigrations: readonly string[];
  readonly architectureDecisions: readonly OrciaShowcaseArchitectureDecisionItem[];
  readonly stackComponents: readonly OrciaShowcaseStackComponentItem[];
  readonly techLeadReports: readonly OrciaShowcaseTechLeadReportItem[];
}

export interface OrciaShowcaseScreenGuideItem {
  readonly id:
    | "cockpit"
    | "assistant"
    | "processes"
    | "agents"
    | "spaces"
    | "finops"
    | "activity"
    | "settings"
    | "help";
  readonly title: string;
  readonly route: string;
  readonly summary: string;
  readonly keyActions: readonly string[];
  readonly openRouteLabel: string;
}

export interface OrciaShowcaseTitleDescCard {
  readonly title: string;
  readonly description: string;
}

export interface OrciaShowcaseBadgeCard extends OrciaShowcaseTitleDescCard {
  readonly badge: string;
}

export interface OrciaShowcaseMacroLabels {
  readonly whyTitle: string;
  readonly whySubtitle: string;
  readonly whyCards: readonly [
    OrciaShowcaseTitleDescCard,
    OrciaShowcaseTitleDescCard,
    OrciaShowcaseTitleDescCard,
  ];
  readonly humanLedTitle: string;
  readonly humanLedSubtitle: string;
  readonly humanAnchorCard: OrciaShowcaseBadgeCard;
  readonly antiRubberStampingCard: OrciaShowcaseBadgeCard;
  readonly humanArbitrationCard: OrciaShowcaseBadgeCard;
  readonly noWildWritesCard: OrciaShowcaseBadgeCard;
  readonly doubleBarrierTitle: string;
  readonly doubleBarrierSubtitle: string;
  readonly snowballWarningPrefix: string;
  readonly snowballWarningBody: string;
  readonly deterministicBarrier: {
    readonly badge: string;
    readonly title: string;
    readonly items: readonly string[];
  };
  readonly probabilisticBarrier: {
    readonly badge: string;
    readonly title: string;
    readonly items: readonly string[];
  };
  readonly rewindBarrier: {
    readonly badge: string;
    readonly title: string;
    readonly items: readonly string[];
  };
  readonly orgPacksTitle: string;
  readonly orgPacksSubtitle: string;
  readonly orgHierarchyCard: OrciaShowcaseTitleDescCard;
  readonly packsCard: OrciaShowcaseTitleDescCard;
}

export interface OrciaShowcaseFeaturesLabels {
  readonly devicesTitle: string;
  readonly devicesSubtitle: string;
  readonly device1HumanAnchor: OrciaShowcaseBadgeCard;
  readonly device2Arbitration: OrciaShowcaseBadgeCard;
  readonly device3BriefingGrid: OrciaShowcaseBadgeCard;
  readonly device4ImpactSimulator: OrciaShowcaseBadgeCard;
  readonly device5VerifiedCitations: OrciaShowcaseBadgeCard;
  readonly device6TeamClaim: OrciaShowcaseBadgeCard;
  readonly screensTitle: string;
  readonly screensSubtitle: string;
  readonly screens: readonly OrciaShowcaseScreenGuideItem[];
}

export interface OrciaShowcaseArchitectureLabels {
  readonly modularMonolithTitle: string;
  readonly modularMonolithSubtitle: string;
  readonly frontendBoundaryCard: OrciaShowcaseTitleDescCard;
  readonly backendCoreCard: OrciaShowcaseTitleDescCard;
  readonly humanLedImplTitle: string;
  readonly humanLedImplSubtitle: string;
  readonly humanAnchorImplCard: OrciaShowcaseTitleDescCard;
  readonly adaptiveGateImplCard: OrciaShowcaseTitleDescCard;
  readonly redisLocksImplCard: OrciaShowcaseTitleDescCard;
  readonly externalRebaseImplCard: OrciaShowcaseTitleDescCard;
  readonly deterministicImplTitle: string;
  readonly deterministicImplSubtitle: string;
  readonly workflowValidatorCard: OrciaShowcaseTitleDescCard;
  readonly tier1aSandboxCard: OrciaShowcaseTitleDescCard;
  readonly tier1bStarlarkCard: OrciaShowcaseTitleDescCard;
  readonly tier2SandboxCard: OrciaShowcaseTitleDescCard;
  readonly probabilisticImplTitle: string;
  readonly probabilisticImplSubtitle: string;
  readonly agenticGateCard: OrciaShowcaseTitleDescCard;
  readonly hybridRagCard: OrciaShowcaseTitleDescCard;
  readonly dbosReplayCard: OrciaShowcaseTitleDescCard;
  readonly securityDsTitle: string;
  readonly securityDsSubtitle: string;
  readonly authVaultCard: OrciaShowcaseTitleDescCard;
  readonly threeLayerDsCard: OrciaShowcaseTitleDescCard;
}

export interface OrciaShowcaseChangelogLabels {
  readonly statsTitle: string;
  readonly statsSubtitle: string;
  readonly activeRoutesStatLabel: string;
  readonly uiPrimitivesStatLabel: string;
  readonly alembicMigrationsStatLabel: string;
  readonly techLeadReportsStatLabel: string;
  readonly verifiedCapabilitiesStatLabel: string;
  readonly installedPacksTitleTemplate: string;
  readonly installedPacksHelpLabel: string;
  readonly stackVersionsTitleTemplate: string;
  readonly reportsTimelineTitleTemplate: string;
  readonly reportsTimelineSubtitle: string;
  readonly searchPlaceholder: string;
}

export interface OrciaShowcaseLabels {
  readonly heroTitle: string;
  readonly heroSubtitle: string;
  readonly heroHelpLabel: string;
  readonly syncedBadgePrefix: string;
  readonly exportStandaloneButton: string;
  readonly exportBannerMessage: string;
  readonly tabsAriaLabel: string;
  readonly tabMacroLabel: string;
  readonly tabFeaturesLabel: string;
  readonly tabArchitectureLabel: string;
  readonly tabChangelogLabelTemplate: string;
  readonly macro: OrciaShowcaseMacroLabels;
  readonly features: OrciaShowcaseFeaturesLabels;
  readonly architecture: OrciaShowcaseArchitectureLabels;
  readonly changelog: OrciaShowcaseChangelogLabels;
}

export interface OrciaProductShowcaseSiteViewProps {
  readonly manifest: OrciaShowcaseManifestData;
  readonly labels: OrciaShowcaseLabels;
  readonly initialTab?: OrciaShowcasePillarTabKey;
  readonly onNavigateToRoute?: (route: string) => void;
  readonly onOpenHelpSection?: (sectionId: string) => void;
  readonly onDownloadStandaloneHtml?: () => void;
}
