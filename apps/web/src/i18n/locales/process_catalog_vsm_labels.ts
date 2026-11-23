export interface LocalizedVsmStepSubStepCopy {
  readonly name: string;
  readonly shortLabel: string;
  readonly trigger: string;
  readonly role: string;
  readonly output: string;
  readonly humanCheck: string;
}

export interface LocalizedVsmControlGateCopy {
  readonly name: string;
  readonly short_label: string;
  readonly status: string;
  readonly verifies_description: string;
  readonly on_ko_behavior: string;
  readonly hypothesis_note?: string | null;
}

export interface LocalizedVsmStepCopy {
  readonly title: string;
  readonly actor_label: string;
  readonly status_badge: string;
  readonly summary: string;
  readonly deliverable: string;
  readonly attention_point: string;
  readonly today: {
    readonly actors: string;
    readonly activities?: string;
    readonly deliverable: string;
    readonly pain_points: string;
  };
  readonly tomorrow: {
    readonly actors: string;
    readonly activities?: string;
    readonly deliverable: string;
    readonly gains: string;
  };
  readonly passage_point: {
    readonly decision: string;
    readonly question: string;
    readonly possible_outcomes: readonly string[];
  } | null;
  readonly detail_tabs: {
    readonly agent_sub_steps: Readonly<Record<string, LocalizedVsmStepSubStepCopy>>;
    readonly human_ai_interactions: {
      readonly initiative: string;
      readonly humanValidation: string;
    };
    readonly delegation_note?: string;
    readonly deterministic_gates?: Readonly<Record<string, LocalizedVsmControlGateCopy>>;
    readonly non_deterministic_gates?: Readonly<Record<string, LocalizedVsmControlGateCopy>>;
    readonly complements_and_missing: readonly string[];
    readonly guardrails: readonly string[];
  };
}

export interface LocalizedVsmReturnLoopCopy {
  readonly trigger_condition: string;
  readonly reason: string;
  readonly impact_summary?: string;
}

export interface LocalizedVsmOpportunityCopy {
  readonly title: string;
  readonly description: string;
}

export interface ProcessCatalogVsmPart1Dictionary {
  readonly title: string;
  readonly subtitle: string;
  readonly knowledgeBase: {
    readonly title: string;
    readonly description: string;
  };
  readonly phases: Readonly<
    Record<
      "01" | "02" | "03" | "04",
      { readonly name: string; readonly goal: string; readonly deliverables_summary: string }
    >
  >;
  readonly steps: Readonly<Record<"01" | "02" | "03", LocalizedVsmStepCopy>>;
}

export interface ProcessCatalogVsmPart2Dictionary {
  readonly steps: Readonly<Record<"04" | "05" | "06" | "07", LocalizedVsmStepCopy>>;
}

export interface ProcessCatalogVsmPart3Dictionary {
  readonly steps: Readonly<Record<"08" | "09" | "10" | "11", LocalizedVsmStepCopy>>;
  readonly returnLoops: Readonly<Record<string, LocalizedVsmReturnLoopCopy>>;
  readonly opportunities: Readonly<Record<"P1" | "P2" | "P3", LocalizedVsmOpportunityCopy>>;
}
