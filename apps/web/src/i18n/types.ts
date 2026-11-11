import type {
  ArbitrationTieBreakCardLabels,
  HumanLedAnchorCardLabels,
  PresenceClaimPillLabels,
  UiBootstrapOnboardingLabels,
  UiCatalogExplorerLabels,
  UiOntologyExplorerLabels,
  UiPermissionBrokerLabels,
  UiShellLabels,
  UiWorkspaceTopologyLabels,
} from "@orcia/ui";
import type { AdminAndStudioDictionarySection } from "./locales/admin_and_studio_labels";
import type { AssistantDictionarySection } from "./locales/assistant_labels";
import type { GatesAndModulesDictionarySection } from "./locales/gates_and_modules_labels";
import type { GovernanceAndPacksDictionarySection } from "./locales/governance_and_packs_labels";
import type { InboxAndCockpitDictionarySection } from "./locales/inbox_and_cockpit_labels";
import type { ProcessOrchestrationModesDictionarySection } from "./locales/process_orchestration_modes_labels";
import type { ReflexiveTraceAndInspectorDictionarySection } from "./locales/reflexive_trace_and_inspector_labels";
import type { ShellAndSearchDictionarySection } from "./locales/shell_and_search_labels";

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
    ProcessOrchestrationModesDictionarySection,
    ReflexiveTraceAndInspectorDictionarySection,
    GatesAndModulesDictionarySection {
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
  workspaceTopology: UiWorkspaceTopologyLabels;
  catalogExplorer: UiCatalogExplorerLabels;
  permissionBroker: UiPermissionBrokerLabels;
  bootstrapOnboarding: UiBootstrapOnboardingLabels;
  ontologyExplorer: UiOntologyExplorerLabels;
}
