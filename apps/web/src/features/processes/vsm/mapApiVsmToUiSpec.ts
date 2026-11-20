import type { ApiValueStreamMapSpec } from "@orcia/api-client";
import { INITIAL_VSM_SPEC } from "../processStudioV2Data";

export type UiVsmSpec = typeof INITIAL_VSM_SPEC;

interface ApiVsmStepNode {
  readonly node_type?: string;
  readonly num: string;
  readonly title?: string;
  readonly linked_workflow_id?: string | null;
  readonly actor_actuel?: string;
  readonly output_actuel?: string;
  readonly actor_ia?: string;
  readonly output_ia?: string;
}

function isApiVsmStepNode(node: unknown): node is ApiVsmStepNode {
  return (
    Boolean(node) &&
    typeof node === "object" &&
    (node as { node_type?: unknown }).node_type === "step" &&
    typeof (node as { num?: unknown }).num === "string"
  );
}

export function mapApiVsmToUiSpec(
  apiVsm: ApiValueStreamMapSpec,
  baseSpec: UiVsmSpec = INITIAL_VSM_SPEC,
): UiVsmSpec {
  const stepNodesByNum = new Map<string, ApiVsmStepNode>();
  for (const node of apiVsm.nodes ?? []) {
    if (isApiVsmStepNode(node)) {
      stepNodesByNum.set(node.num, node);
    }
  }

  const phasesByNum = new Map<string, Record<string, string>>();
  for (const phase of apiVsm.phases ?? []) {
    if (phase && typeof phase === "object") {
      phasesByNum.set(String(phase.num ?? phase.id ?? ""), phase);
    }
  }

  const mappedPhases = baseSpec.phases.map((phase) => {
    const apiPhase = phasesByNum.get(phase.num);
    return {
      ...phase,
      name: apiPhase?.label || phase.name,
      goal: apiPhase?.subtitle || phase.goal,
      steps: phase.steps.map((step) => {
        const apiNode = stepNodesByNum.get(step.num);
        if (!apiNode) {
          return step;
        }
        return {
          ...step,
          title: apiNode.title || step.title,
          linked_workflow_id:
            (apiNode.linked_workflow_id ?? step.linked_workflow_id) as typeof step.linked_workflow_id,
          today: {
            ...step.today,
            actors: apiNode.actor_actuel || step.today.actors,
            deliverable: apiNode.output_actuel || step.today.deliverable,
          },
          tomorrow: {
            ...step.tomorrow,
            actors: apiNode.actor_ia || step.tomorrow.actors,
            deliverable: apiNode.output_ia || step.tomorrow.deliverable,
          },
        };
      }),
    };
  }) as UiVsmSpec["phases"];

  const kbFoundation = apiVsm.knowledge_foundation ?? {};
  return {
    ...baseSpec,
    id: apiVsm.id || baseSpec.id,
    slug: apiVsm.slug || baseSpec.slug,
    title: apiVsm.title || baseSpec.title,
    subtitle: apiVsm.subtitle || baseSpec.subtitle,
    knowledge_base: {
      ...baseSpec.knowledge_base,
      title: kbFoundation.title || baseSpec.knowledge_base.title,
      description: kbFoundation.summary || baseSpec.knowledge_base.description,
    },
    phases: mappedPhases,
  };
}
