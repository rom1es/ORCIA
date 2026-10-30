import type {
  ArbitrationTieBreakCardLabels,
  ChunkValidationCardLabels,
  CognitiveReviewBriefingLabels,
  HumanLedAnchorCardLabels,
  PresenceClaimPillLabels,
  UiBootstrapOnboardingLabels,
  UiCatalogExplorerLabels,
  UiModuleKey,
  UiOntologyExplorerLabels,
  UiPermissionBrokerLabels,
  UiShellLabels,
  UiWorkspaceTopologyLabels,
  UpstreamChallengeModalLabels,
} from "@orcia/ui";

export type SupportedWebLocale = "fr" | "en";

export interface ModulePageCopy {
  subtitle: string;
  description: string;
  uriBadgeExample: string;
}

export interface InboxAndClaimsCopy {
  filterAllLabel: string;
  filterPersonalLabel: string;
  filterTeamLabel: string;
  amberCounterPrefix: string;
  contributorSectionTitle: string;
  observerSectionTitle: string;
  observerBannerText: string;
  presencePill: PresenceClaimPillLabels;
}

import type { Epic5DictionarySection } from "./locales/epic5_labels";

export interface TranslationDictionary extends Epic5DictionarySection {
  locale: SupportedWebLocale;
  shell: UiShellLabels;
  humanAnchor: HumanLedAnchorCardLabels & {
    defaultSectionTitle: string;
    defaultAuthorName: string;
    defaultValue: string;
  };
  arbitrationTieBreak: ArbitrationTieBreakCardLabels & {
    defaultQuestionTitle: string;
    defaultContextSummary: string;
  };
  upstreamChallengeModal: UpstreamChallengeModalLabels;
  humanGates: {
    briefing: CognitiveReviewBriefingLabels;
    chunkValidation: ChunkValidationCardLabels;
  };
  inboxAndClaims: InboxAndClaimsCopy;
  workspaceTopology: UiWorkspaceTopologyLabels;
  catalogExplorer: UiCatalogExplorerLabels;
  permissionBroker: UiPermissionBrokerLabels;
  bootstrapOnboarding: UiBootstrapOnboardingLabels;
  ontologyExplorer: UiOntologyExplorerLabels;
  modulePages: Record<UiModuleKey, ModulePageCopy>;
}
