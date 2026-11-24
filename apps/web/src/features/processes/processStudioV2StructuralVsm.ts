import { DICTIONARIES, type SupportedWebLocale } from "../../i18n";
import type { LocalizedVsmStepCopy } from "../../i18n/locales/process_catalog_vsm_labels";

interface VsmStepStructureSpec {
  readonly num: "01" | "02" | "03" | "04" | "05" | "06" | "07" | "08" | "09" | "10" | "11";
  readonly actor_type: "agent" | "human";
  readonly linked_workflow_id: string | null;
  readonly hasPassagePoint: boolean;
  readonly subStepIds: readonly string[];
  readonly delegatedToStepNum?: string;
  readonly hasControlStrategy?: boolean;
  readonly deterministicGate?: { readonly id: string; readonly runner_plugin_id: string; readonly max_self_heal_retries: number; readonly config: Record<string, unknown> };
  readonly nonDeterministicGates?: ReadonlyArray<{ readonly id: string; readonly evaluator_type: string; readonly agent_ref: string; readonly risk_threshold: number }>;
}

const PHASE_STRUCTURES: ReadonlyArray<{
  readonly num: "01" | "02" | "03" | "04";
  readonly steps_range: string;
  readonly steps: readonly VsmStepStructureSpec[];
}> = [
  {
    num: "01",
    steps_range: "01–04",
    steps: [
      { num: "01", actor_type: "agent", linked_workflow_id: "wf-01-qualification-prd", hasPassagePoint: false, subStepIds: ["qualification"], delegatedToStepNum: "02" },
      {
        num: "02",
        actor_type: "agent",
        linked_workflow_id: "wf-01-qualification-prd",
        hasPassagePoint: true,
        subStepIds: ["prd", "jira"],
        hasControlStrategy: true,
        deterministicGate: { id: "det-02-1", runner_plugin_id: "markdown_contract_runner", max_self_heal_retries: 3, config: { required_headings: ["# "], min_chars_per_section: 20 } },
        nonDeterministicGates: [{ id: "ndet-02-1", evaluator_type: "adversarial_agent", agent_ref: "pack://sdlc/gates/hunter-archi-contradicteur", risk_threshold: 0.7 }],
      },
      {
        num: "03",
        actor_type: "agent",
        linked_workflow_id: "wf-03-etude-architecture",
        hasPassagePoint: false,
        subStepIds: ["comprendre", "concevoir", "rediger", "controler"],
        hasControlStrategy: true,
        nonDeterministicGates: [
          { id: "ndet-03-1", evaluator_type: "adversarial_agent", agent_ref: "pack://sdlc/gates/hunter-archi-contradicteur", risk_threshold: 0.7 },
          { id: "ndet-03-2", evaluator_type: "adversarial_agent", agent_ref: "pack://sdlc/gates/hunter-archi-contradicteur", risk_threshold: 0.7 },
        ],
      },
      { num: "04", actor_type: "human", linked_workflow_id: null, hasPassagePoint: true, subStepIds: [] },
    ],
  },
  {
    num: "02",
    steps_range: "05–06",
    steps: [
      { num: "05", actor_type: "human", linked_workflow_id: null, hasPassagePoint: false, subStepIds: [] },
      {
        num: "06",
        actor_type: "agent",
        linked_workflow_id: "wf-06-decoupe-us",
        hasPassagePoint: true,
        subStepIds: ["analyse", "epic", "decoupe", "controle", "creation"],
        hasControlStrategy: true,
        nonDeterministicGates: [{ id: "ndet-06-1", evaluator_type: "adversarial_agent", agent_ref: "pack://sdlc/gates/hunter-archi-contradicteur", risk_threshold: 0.7 }],
      },
    ],
  },
  {
    num: "03",
    steps_range: "07–09",
    steps: [
      { num: "07", actor_type: "human", linked_workflow_id: null, hasPassagePoint: false, subStepIds: [] },
      { num: "08", actor_type: "human", linked_workflow_id: "wf-08-dev-external-gate", hasPassagePoint: true, subStepIds: [] },
      { num: "09", actor_type: "human", linked_workflow_id: null, hasPassagePoint: true, subStepIds: [] },
    ],
  },
  {
    num: "04",
    steps_range: "10–11",
    steps: [
      { num: "10", actor_type: "human", linked_workflow_id: null, hasPassagePoint: true, subStepIds: [] },
      { num: "11", actor_type: "human", linked_workflow_id: null, hasPassagePoint: false, subStepIds: [] },
    ],
  },
];

const RETURN_LOOP_STRUCTURES: ReadonlyArray<{
  readonly id: string;
  readonly from_step_num: string;
  readonly to_step_num: string;
  readonly tier: "primary" | "secondary";
  readonly reentry_mode: "corrections";
}> = [
  { id: "loop-02-to-02-0", from_step_num: "02", to_step_num: "02", tier: "primary", reentry_mode: "corrections" },
  { id: "loop-02-to-01-1", from_step_num: "02", to_step_num: "01", tier: "secondary", reentry_mode: "corrections" },
  { id: "loop-04-to-03-0", from_step_num: "04", to_step_num: "03", tier: "primary", reentry_mode: "corrections" },
  { id: "loop-04-to-04-1", from_step_num: "04", to_step_num: "04", tier: "secondary", reentry_mode: "corrections" },
  { id: "loop-04-to-02-2", from_step_num: "04", to_step_num: "02", tier: "secondary", reentry_mode: "corrections" },
  { id: "loop-06-to-06-0", from_step_num: "06", to_step_num: "06", tier: "primary", reentry_mode: "corrections" },
  { id: "loop-06-to-04-1", from_step_num: "06", to_step_num: "04", tier: "secondary", reentry_mode: "corrections" },
  { id: "loop-08-to-08-0", from_step_num: "08", to_step_num: "08", tier: "primary", reentry_mode: "corrections" },
  { id: "loop-09-to-08-0", from_step_num: "09", to_step_num: "08", tier: "primary", reentry_mode: "corrections" },
  { id: "loop-09-to-07-1", from_step_num: "09", to_step_num: "07", tier: "secondary", reentry_mode: "corrections" },
  { id: "loop-10-to-08-0", from_step_num: "10", to_step_num: "08", tier: "primary", reentry_mode: "corrections" },
  { id: "loop-10-to-10-1", from_step_num: "10", to_step_num: "10", tier: "secondary", reentry_mode: "corrections" },
];

const OPPORTUNITY_STRUCTURES: ReadonlyArray<{ readonly priority: "P1" | "P2" | "P3"; readonly target_steps: string }> = [
  { priority: "P1", target_steps: "O2, O18" },
  { priority: "P2", target_steps: "O12, O13, C10" },
  { priority: "P3", target_steps: "O9" },
];

function buildStep(spec: VsmStepStructureSpec, copy: LocalizedVsmStepCopy) {
  const detGates = spec.deterministicGate
    ? [{
        ...spec.deterministicGate,
        name: copy.detail_tabs.deterministic_gates?.[spec.deterministicGate.id]?.name ?? spec.deterministicGate.id,
        short_label: copy.detail_tabs.deterministic_gates?.[spec.deterministicGate.id]?.short_label ?? spec.deterministicGate.id,
        status: copy.detail_tabs.deterministic_gates?.[spec.deterministicGate.id]?.status ?? "place",
        verifies_description: copy.detail_tabs.deterministic_gates?.[spec.deterministicGate.id]?.verifies_description ?? "",
        on_ko_behavior: copy.detail_tabs.deterministic_gates?.[spec.deterministicGate.id]?.on_ko_behavior ?? "",
      }]
    : [];
  const ndetGates = (spec.nonDeterministicGates ?? []).map((g) => {
    const gc = copy.detail_tabs.non_deterministic_gates?.[g.id];
    return {
      ...g,
      name: gc?.name ?? g.id,
      short_label: gc?.short_label ?? g.id,
      status: gc?.status ?? "place",
      verifies_description: gc?.verifies_description ?? "",
      hypothesis_note: gc?.hypothesis_note ?? null,
      on_ko_behavior: gc?.on_ko_behavior ?? "",
    };
  });
  return {
    num: spec.num,
    title: copy.title,
    actor_type: spec.actor_type,
    actor_label: copy.actor_label,
    status_badge: copy.status_badge,
    summary: copy.summary,
    deliverable: copy.deliverable,
    attention_point: copy.attention_point,
    linked_workflow_id: spec.linked_workflow_id,
    today: { actors: copy.today.actors, activities: copy.today.activities ?? "", deliverable: copy.today.deliverable, pain_points: copy.today.pain_points },
    tomorrow: { actors: copy.tomorrow.actors, activities: copy.tomorrow.activities ?? "", deliverable: copy.tomorrow.deliverable, gains: copy.tomorrow.gains },
    passage_point:
      spec.hasPassagePoint && copy.passage_point
        ? { decision: copy.passage_point.decision, question: copy.passage_point.question, actors: "sdlc:committee, sdlc:architect, sdlc:po", possible_outcomes: [...copy.passage_point.possible_outcomes] }
        : null,
    detail_tabs: {
      agent_sub_steps: spec.subStepIds.map((id) => ({ id, ...(copy.detail_tabs.agent_sub_steps[id]!) })),
      human_ai_interactions: { ...copy.detail_tabs.human_ai_interactions },
      controls_and_gates: {
        ...(spec.delegatedToStepNum ? { delegated_to_step_num: spec.delegatedToStepNum, delegation_note: copy.detail_tabs.delegation_note ?? "" } : {}),
        ...(spec.hasControlStrategy ? { strategy: "fail_fast", sandbox_dry_run: true } : {}),
        deterministic: detGates,
        non_deterministic: ndetGates,
      },
      complements_and_missing: [...copy.detail_tabs.complements_and_missing],
      guardrails: [...copy.detail_tabs.guardrails],
    },
  };
}

export function getInitialVsmSpec(locale: SupportedWebLocale = "fr") {
  const d = DICTIONARIES[locale];
  const p1 = d.processCatalogVsmP1;
  const p2 = d.processCatalogVsmP2;
  const p3 = d.processCatalogVsmP3;
  const allStepsCopy: Record<VsmStepStructureSpec["num"], LocalizedVsmStepCopy> = {
    ...p1.steps,
    ...p2.steps,
    ...p3.steps,
  };
  return {
    id: "vsm-mon-compte-idea-to-prod",
    slug: "mon-compte-idea-to-prod",
    title: p1.title,
    subtitle: p1.subtitle,
    version: "2.0.0",
    knowledge_base: {
      title: p1.knowledgeBase.title,
      description: p1.knowledgeBase.description,
      feeds_steps: ["01", "02", "03", "06", "08", "09", "11"],
    },
    phases: PHASE_STRUCTURES.map((phase) => {
      const phaseCopy = p1.phases[phase.num];
      return {
        num: phase.num,
        name: phaseCopy.name,
        goal: phaseCopy.goal,
        steps_range: phase.steps_range,
        deliverables_summary: phaseCopy.deliverables_summary,
        steps: phase.steps.map((s) => buildStep(s, allStepsCopy[s.num])),
      };
    }),
    return_loops: RETURN_LOOP_STRUCTURES.map((loop) => {
      const loopCopy = p3.returnLoops[loop.id]!;
      return {
        ...loop,
        trigger_condition: loopCopy.trigger_condition,
        reason: loopCopy.reason,
        impact_summary: loopCopy.impact_summary ?? "",
      };
    }),
    opportunities: OPPORTUNITY_STRUCTURES.map((opp) => {
      const oppCopy = p3.opportunities[opp.priority];
      return {
        priority: opp.priority,
        target_steps: opp.target_steps,
        title: oppCopy.title,
        description: oppCopy.description,
      };
    }),
  };
}
