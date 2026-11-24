import type {
  AgentsAndSkillsManagerLabels,
  DnaStarlarkAndGlossaryLabels,
  HelpArticleGeneratorAndValidatorLabels,
  PackBuilderProcessesStudioLabels,
  RemoteServiceTestBenchLabels,
  WorkspaceFiveTabsLabels,
} from "@orcia/ui";
import { GOVERNANCE_AND_PACKS_EN_LABELS } from "./governance_and_packs_labels_en";
import { GOVERNANCE_AND_PACKS_FR_LABELS } from "./governance_and_packs_labels_fr";

export interface GovernanceAndPacksDictionarySection {
  readonly workspaceFiveTabs: WorkspaceFiveTabsLabels;
  readonly dnaStarlarkGlossary: DnaStarlarkAndGlossaryLabels;
  readonly remoteServiceTestBench: RemoteServiceTestBenchLabels;
  readonly packBuilderStudio: PackBuilderProcessesStudioLabels;
  readonly helpArticleGenerator: HelpArticleGeneratorAndValidatorLabels;
  readonly agentsAndSkillsManager: AgentsAndSkillsManagerLabels;
}

export { GOVERNANCE_AND_PACKS_EN_LABELS, GOVERNANCE_AND_PACKS_FR_LABELS };
