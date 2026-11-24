export interface LocalizedPackCopy {
  readonly name: string;
  readonly description: string;
  readonly connectorUsedFor: Readonly<Record<string, string>>;
}

export interface LocalizedWorkflowSubStepCopy {
  readonly name: string;
  readonly short_label: string;
  readonly trigger_condition_label: string;
  readonly role_description: string;
  readonly instruction_prompt_or_ref?: string;
  readonly output_description: string;
  readonly checkpoint_question: string | null;
}

export interface LocalizedWorkflowCopy {
  readonly title: string;
  readonly reflexive_objective?: string | null;
  readonly external_tool_label?: string | null;
  readonly triggerSourceLabels: readonly string[];
  readonly contractInputs: readonly string[];
  readonly contractOutputs: readonly string[];
  readonly contractExitCriteria: readonly string[];
  readonly subSteps: Readonly<Record<string, LocalizedWorkflowSubStepCopy>>;
  readonly deterministicGates: Readonly<
    Record<string, { readonly name: string; readonly required_headings?: readonly string[] }>
  >;
  readonly probabilisticEvaluations: Readonly<
    Record<string, { readonly name: string; readonly rubric_ref: string }>
  >;
  readonly guardrails: readonly string[];
}

export interface ProcessCatalogWorkflowsDictionary {
  readonly packs: Readonly<Record<"orcia-pack-sdlc" | "orcia-pack-docs", LocalizedPackCopy>>;
  readonly workflows: Readonly<Record<string, LocalizedWorkflowCopy>>;
}
