import type { ProcessCatalogVsmPart2Dictionary } from "./process_catalog_vsm_labels";

export const PROCESS_CATALOG_VSM_P2_EN: ProcessCatalogVsmPart2Dictionary = {
  steps: {
    "04": {
      title: "Product Requirements Finalization",
      actor_label: "Rovo",
      status_badge: "Human Governance",
      summary: "Complete PRD, finalized mockups, and observability KPIs",
      deliverable: "Complete PRD, finalized mockups, and observability KPIs",
      attention_point:
        "This step and architecture framing inform each other: architects challenge the need, product refines requirements. UX mockups are produced cross-team 2–3 days/week and must finish before Ready to Prioritize.",
      today: {
        actors: "PM, PO, and architect in workshops. Many round-trips without standardized deliverable.",
        deliverable: "Specification deliverables at varying levels of completeness",
        pain_points: "To define: architecture board validates the study, no body currently validates product requirements",
      },
      tomorrow: {
        actors: "Completes the templated PRD and flags missing items including observability; team decides.",
        deliverable: "Complete PRD, finalized mockups, and observability KPIs",
        gains: "To define: architecture board validates the study, no body currently validates product requirements",
      },
      passage_point: {
        decision: "Team walkthrough, architecture board, CISO",
        question:
          "Two distinct bodies. Team walkthrough is mandatory for Mon Compte. Architecture board gathers domain architects without product and triggers on ecosystem impact (blocking no-go). CISO joins when sensitive.",
        possible_outcomes: [
          "Return to Step 03 (corrections)",
          "Return to Step 04 (corrections)",
          "Return to Step 02 (corrections)",
          "Approve & proceed to next step",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Approved PRD from intake committee and architecture study dossier",
          humanValidation: "To define: architecture board validates the study, no body validates product requirements yet",
        },
        complements_and_missing: [
          "This step and architecture framing inform each other; UX mockups must be finalized before Ready to Prioritize.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "To define: architecture board validates the study, no body validates product requirements yet",
        ],
      },
    },
    "05": {
      title: "Prioritization Inputs",
      actor_label: "Human / Team",
      status_badge: "Human Governance",
      summary: "Value and effort already filled on the Feature ticket, with WSJF computed in Step 02 to confirm",
      deliverable: "Value and effort already filled on the Feature ticket, with WSJF computed in Step 02 to confirm",
      attention_point:
        "This step does not decide the final sequence; it produces **the inputs needed to prioritize** (must/should/could rank). Scoring fields and formulas already exist in Jira.",
      today: {
        actors: "Ad-hoc across teams without a dedicated forum; scoring fields unused.",
        deliverable: "Complexity and value inconsistently populated",
        pain_points: "Prioritization itself is processed by the release train",
      },
      tomorrow: {
        actors:
          "No agent at this step. WSJF and effort arrive pre-filled on the Feature ticket from Step 02; the team confirms and human prioritization decides.",
        deliverable: "Value and effort already filled on the Feature ticket, with WSJF computed in Step 02 to confirm",
        gains: "Prioritization itself is processed by the release train",
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Approved topics and their macro estimates",
          humanValidation: "Prioritization itself is processed by the release train",
        },
        complements_and_missing: [
          "This step produces **prioritization inputs** rather than a go/no-go; Jira scoring fields already exist.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "Prioritization itself is processed by the release train",
        ],
      },
    },
    "06": {
      title: "User Story Splitting",
      actor_label: "Rovo",
      status_badge: "POC Step 4",
      summary: "Agent analyzes, prepares Epic, splits, verifies, then creates Stories; PO validates each transition.",
      deliverable:
        "Epic linked to the Feature and DoR / INVEST Stories verified and created under the Epic with dependencies",
      attention_point:
        "Splitting ahead of PI Planning aligns with SAFe so teams commit to real stories rather than raw features.",
      today: {
        actors: "PO and developers during refinement before PI Planning",
        activities:
          "PO and developers split the Feature into User Stories before PI Planning. · Stories are drafted and sometimes sized. · PI Planning then commits the teams.",
        deliverable: "Drafted User Stories, sometimes estimated",
        pain_points: "PI Planning: release train team commitment on day two",
      },
      tomorrow: {
        actors:
          "**Agent US** analyzes the Feature, PRD, and study, finds or prepares the Epic, proposes a splitting plan, drafts DoR / INVEST Stories, verifies them, and creates them in Jira with PO sign-off at every step.",
        activities:
          "PO provides Feature key. · Agent summarizes Feature, PRD, and study and lists questions. · PO approves analysis. · Agent prepares Epic and PO confirms. · Agent proposes splitting plan; PO validates. · Agent drafts DoR / INVEST Stories and Quality Check evaluates them. · After OK verdict and PO sign-off, Stories and dependencies are created.",
        deliverable:
          "Epic linked to the Feature and DoR / INVEST Stories verified and created under the Epic with dependencies",
        gains: "PO validates every agent transition, then PI Planning commits teams",
      },
      passage_point: {
        decision: "PI Planning, two days",
        question:
          "Around a hundred people over two days. Cross-team dependencies are resolved, Stories placed in iterations, and selected Features move to Ready on day two.",
        possible_outcomes: [
          "Return to Step 06 (corrections)",
          "Return to Step 04 (corrections)",
          "Approve & proceed to next step",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {
          analyse: {
            name: "Analysis",
            shortLabel: "Analyze",
            trigger: "When given a Feature key or resuming after feedback",
            role: "Reads Feature, PRD, and architecture study; synthesizes and flags gaps and questions.",
            output: "Synthesis and open questions",
            humanCheck: "Analysis validated",
          },
          epic: {
            name: "Epic Creator",
            shortLabel: "Epic",
            trigger: "Once analysis is validated and questions answered",
            role: "Finds an existing Epic or prepares creation and links it to the Feature.",
            output: "Epic ready and linked to Feature",
            humanCheck: "Epic created",
          },
          decoupe: {
            name: "US Splitting",
            shortLabel: "Split",
            trigger: "Once Epic is ready, or to revise the plan or stories",
            role: "Proposes splitting plan first, then drafts each Story using DoR / INVEST.",
            output: "Detailed User Stories",
            humanCheck: "Check triggered",
          },
          controle: {
            name: "Quality Check",
            shortLabel: "Check",
            trigger: "Automatically after drafting Stories, or on demand",
            role: "Evaluates Stories for INVEST, DoR, and PRD coverage; outputs OK/KO verdict and gap table.",
            output: "Verdict and gap table",
            humanCheck: 'Check OK, then "I approve"',
          },
          creation: {
            name: "Creation",
            shortLabel: "Create",
            trigger: "Only after explicit sign-off following an OK check",
            role: "Creates Stories in Jira under the Epic and links dependencies.",
            output: "Stories created under Epic with dependencies",
            humanCheck: 'PO confirms creation ("done", "ok")',
          },
        },
        human_ai_interactions: {
          initiative: "Feature key (PRD) and architecture study dossier",
          humanValidation:
            "PO validates analysis, splitting plan, and quality check before any Jira creation; PI Planning then commits teams.",
        },
        non_deterministic_gates: {
          "ndet-06-1": {
            name: "Check Sub-Agent",
            short_label: "Check Sub-Agent",
            status: "place",
            verifies_description: "Evaluates Stories for INVEST, DoR, and PRD coverage; returns OK/KO with gap table.",
            hypothesis_note: null,
            on_ko_behavior: "Gap table guides Story revisions; nothing is created without OK and PO sign-off.",
          },
        },
        complements_and_missing: [
          "Pre-PI splitting aligns with SAFe so teams commit to concrete User Stories.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "PO validates analysis, splitting plan, and quality check before Jira creation.",
        ],
      },
    },
    "07": {
      title: "User Story Refinement",
      actor_label: "Human / Team",
      status_badge: "Human Governance",
      summary: "Business rules, test scenarios, sub-task breakdown",
      deliverable: "Business rules, test scenarios, sub-task breakdown",
      attention_point:
        "Open workshop question: where PO functional UAT ends and QA edge cases begin. **QA must attend this step** so automation effort is estimated early.",
      today: {
        actors: "PO and developers in iteration",
        deliverable: "Business rules, test scenarios, sub-task breakdown",
        pain_points: 'PO and developers on "to validate" and "to fix" statuses; QA should participate to build scenarios.',
      },
      tomorrow: {
        actors: "No agent here. Stories arrive in DoR / INVEST format from Step 06; PO and developers refine them.",
        deliverable: "Business rules, test scenarios, sub-task breakdown",
        gains: 'PO and developers on "to validate" and "to fix" statuses; QA participates to design test scenarios.',
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Story from splitting, already formatted to DoR / INVEST with acceptance criteria",
          humanValidation: 'PO and developers on "to validate" and "to fix" statuses; QA builds test scenarios.',
        },
        complements_and_missing: [
          "QA participation at refinement clarifies UAT boundaries and automation workload.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "PO, developers, and QA align acceptance scenarios before implementation.",
        ],
      },
    },
  },
};
