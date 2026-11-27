import { getInitialWorkflowsV2 } from "./processStudioV2StructuralWorkflows";
import { getInitialVsmSpec } from "./processStudioV2StructuralVsm";

export type {
  ConnectorHealthItem,
  DeclarativePackItem,
  DeterministicSubStepItem,
  WorkflowDefinitionV2Item,
} from "./processStudioV2Types";
export { getInitialWorkflowsV2 } from "./processStudioV2StructuralWorkflows";
export { getInitialVsmSpec } from "./processStudioV2StructuralVsm";
export {
  loadPersistedWorkflowsV2,
  resetPersistedWorkflowsV2,
  savePersistedWorkflowV2,
} from "./processStudioV2Storage";

export const INITIAL_VSM_SPEC = getInitialVsmSpec("fr");
export const INITIAL_WORKFLOWS_V2 = getInitialWorkflowsV2("fr");
