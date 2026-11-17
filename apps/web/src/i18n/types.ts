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

import type { ActivityDictionarySection } from "./locales/activity_labels";
import type { AdminAndStudioDictionarySection } from "./locales/admin_and_studio_labels";
import type { AiModelsHubDictionary } from "./locales/ai_models_hub_labels";
import type { AssistantDictionarySection } from "./locales/assistant_labels";
import type { AuthSettingsDictionarySection } from "./locales/auth_settings_labels";
import type { Epic18SourcesLabels } from "./locales/epic18_sources_labels";
import type { FinopsDictionarySection } from "./locales/finops_labels";
import type { GovernanceAndPacksDictionarySection } from "./locales/governance_and_packs_labels";
import type { InboxAndCockpitDictionarySection } from "./locales/inbox_and_cockpit_labels";
import type { ShellAndSearchDictionarySection } from "./locales/shell_and_search_labels";

export interface TranslationDictionary
  extends InboxAndCockpitDictionarySection,
    AdminAndStudioDictionarySection,
    ShellAndSearchDictionarySection,
    AssistantDictionarySection,
    GovernanceAndPacksDictionarySection,
    ActivityDictionarySection,
    FinopsDictionarySection {
  locale: SupportedWebLocale;
  aiModelsHub: AiModelsHubDictionary;
  authSettings: AuthSettingsDictionarySection;
  epic18Sources: Epic18SourcesLabels;
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
