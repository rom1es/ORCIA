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
  UserProfileOverviewLabels,
} from "@orcia/ui";
import type { ClientErrorLabels } from "../lib/clientErrorCodes";
import type { CategoryAControllersDictionary } from "./locales/category_a_controller_labels";
import type { Rfc9457BannerDictionary } from "./locales/rfc9457_banner_labels";
import type { ActivityDictionarySection } from "./locales/activity_labels";
import type { AdminAndStudioDictionarySection } from "./locales/admin_and_studio_labels";
import type { AiModelsHubDictionary } from "./locales/ai_models_hub_labels";
import type { AssistantDictionarySection } from "./locales/assistant_labels";
import type { AuthSettingsDictionarySection } from "./locales/auth_settings_labels";
import type { AutonomousSupervisionCopy } from "./locales/autonomous_supervision_labels";
import type { AutonomyContractStudioCopy } from "./locales/autonomy_contract_labels";
import type { Epic18SourcesLabels } from "./locales/epic18_sources_labels";
import type { FinopsDictionarySection } from "./locales/finops_labels";
import type { GovernanceAndPacksDictionarySection } from "./locales/governance_and_packs_labels";
import type { InboxAndCockpitDictionarySection } from "./locales/inbox_and_cockpit_labels";
import type { OntologyGlossaryCopy } from "./locales/ontology_glossary_labels";
import type { ProcessOrchestrationModesDictionarySection } from "./locales/process_orchestration_modes_labels";
import type { ReflexiveTraceAndInspectorDictionarySection } from "./locales/reflexive_trace_and_inspector_labels";
import type { ShellAndSearchDictionarySection } from "./locales/shell_and_search_labels";
import type { WorkflowTriggersStudioCopy } from "./locales/workflow_triggers_labels";

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

export interface TranslationDictionary
  extends InboxAndCockpitDictionarySection,
    AdminAndStudioDictionarySection,
    ShellAndSearchDictionarySection,
    AssistantDictionarySection,
    GovernanceAndPacksDictionarySection,
    ActivityDictionarySection,
    FinopsDictionarySection,
    ProcessOrchestrationModesDictionarySection,
    ReflexiveTraceAndInspectorDictionarySection {
  locale: SupportedWebLocale;
  clientErrors: ClientErrorLabels;
  rfc9457Errors: Rfc9457BannerDictionary;
  categoryAControllers: CategoryAControllersDictionary;
  aiModelsHub: AiModelsHubDictionary;
  authSettings: AuthSettingsDictionarySection;
  autonomousSupervision: AutonomousSupervisionCopy;
  autonomyContract: AutonomyContractStudioCopy;
  epic18Sources: Epic18SourcesLabels;
  workflowTriggers: WorkflowTriggersStudioCopy;
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
  ontologyGlossary: OntologyGlossaryCopy;
  profileOverview: UserProfileOverviewLabels;
  modulePages: Record<UiModuleKey, ModulePageCopy>;
}
