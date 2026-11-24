import type { ProcessCatalogVsmPart3Dictionary } from "./process_catalog_vsm_labels";

export const PROCESS_CATALOG_VSM_P3_EN: ProcessCatalogVsmPart3Dictionary = {
  steps: {
    "08": {
      title: "Development",
      actor_label: "GitHub Copilot",
      status_badge: "POC Step 5",
      summary: "Code, then a pull request — same output, same quality bar",
      deliverable: "Code, then a pull request — same output, same quality bar",
      attention_point:
        "Some tasks stay out of reach (provisioning a database, opening a topic) and the POC explicitly surfaces those boundaries.",
      today: {
        actors: "Assigned developer, locally",
        deliverable: "Code, then a pull request",
        pain_points: "Dev Review: peer developer who did not write the code reviews, never delegated",
      },
      tomorrow: {
        actors: "Assists coding; the developer steers, fixes, and owns the pull request.",
        deliverable: "Code, then a pull request — same output, same quality bar",
        gains: "Dev Review: peer developer who did not write the code reviews, never delegated",
      },
      passage_point: {
        decision: "Dev Review",
        question:
          "A peer developer who did not write the code reviews and approves the merge. The POC intentionally keeps this human gate intact.",
        possible_outcomes: ["Return to Step 08 (corrections)", "Approve & proceed to next step"],
      },
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "User Stories, study dossier, and team coding standards",
          humanValidation: "Dev Review: peer developer reviews and approves merge, never delegated",
        },
        complements_and_missing: [
          "Infrastructure tasks outside scope remain explicit boundaries surfaced by the POC.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "Dev Review: peer developer reviews and approves merge, never delegated",
        ],
      },
    },
    "09": {
      title: "QA & Acceptance",
      actor_label: "GitHub Copilot",
      status_badge: "POC Use Case",
      summary: "Validated User Story and a self-enriching regression test suite",
      deliverable: "Validated User Story and a self-enriching regression test suite",
      attention_point:
        "Merge happens before business acceptance in this flow choice, which dictates where quality gates bite. Scenario generation is a key POC use case.",
      today: {
        actors: "Cross-team QA runs test scenarios",
        deliverable: "Validated US, moved to pending release",
        pain_points: "QA test, functional architect review, BO & PM demo, then PO review",
      },
      tomorrow: {
        actors: "Generates scenarios and adds missing regression cases after each bug; QA executes and decides.",
        deliverable: "Validated User Story and a self-enriching regression test suite",
        gains: "QA test, functional architect review, BO & PM demo, then PO review",
      },
      passage_point: {
        decision: "PO review",
        question: "Functional sign-off against acceptance criteria after QA testing on staging.",
        possible_outcomes: [
          "Return to Step 08 (corrections)",
          "Return to Step 07 (corrections)",
          "Approve & proceed to next step",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Package deployed to staging and test scenarios",
          humanValidation: "QA test, functional architect review, BO & PM demo, then PO review",
        },
        complements_and_missing: [
          "Scenario generation from acceptance criteria and bug reports enriches regression coverage over time.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "QA test, functional architect review, BO & PM demo, then PO review",
        ],
      },
    },
    "10": {
      title: "Deployment",
      actor_label: "Rovo",
      status_badge: "Human Governance",
      summary: "The same deployment page, pre-filled and verified in a fraction of the time",
      deliverable: "The same deployment page, pre-filled and verified in a fraction of the time",
      attention_point:
        "Everything copied into the deployment page (Stories, impacted components, versions) **already exists in Jira**. Code freeze occurs ~3 weeks before release.",
      today: {
        actors: "Co-authored manually in Confluence, completeness checked by eye",
        deliverable: "Deployment page and release frozen at code freeze",
        pain_points: "Release manager & Ops: page completeness, then code freeze",
      },
      tomorrow: {
        actors: "Pre-populates the page from Jira; humans complete only judgment calls.",
        deliverable: "The same deployment page, pre-filled and verified in a fraction of the time",
        gains: "Release manager & Ops: page completeness, then code freeze",
      },
      passage_point: {
        decision: "Regression, perf, integration, pre-production",
        question:
          "Four environments with a go/no-go at each promotion: regression on frozen build, load tests, partner systems integration, and rollback test.",
        possible_outcomes: [
          "Return to Step 08 (corrections)",
          "Return to Step 10 (corrections)",
          "Approve & proceed to next step",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Release User Stories, impacted components, target versions",
          humanValidation: "Release manager & Ops: page completeness, then code freeze",
        },
        complements_and_missing: [
          "Everything copied onto the deployment page already exists in Jira.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "Release manager & Ops: page completeness, then code freeze",
        ],
      },
    },
    "11": {
      title: "Release & Go-Live",
      actor_label: "Human / Team",
      status_badge: "Human Governance",
      summary: "Feature live in production, followed by impact & KPI review",
      deliverable: "Feature live in production, followed by impact & KPI review",
      attention_point:
        "Features can be deployed behind a config toggle and enabled on schedule. A post-launch KPI review closes the loop.",
      today: {
        actors: "System team following developer runbook",
        deliverable: "Feature live in production, followed by impact & KPI review",
        pain_points: "Go/no-go at every environment gate: Ops, QA, partner systems",
      },
      tomorrow: {
        actors: "System team following developer runbook",
        deliverable: "Feature live in production, followed by impact & KPI review",
        gains: "Go/no-go at every environment gate: Ops, QA, partner systems",
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {},
        human_ai_interactions: {
          initiative: "Validated release package and activation runbook",
          humanValidation: "Go/no-go at every environment gate: Ops, QA, partner systems",
        },
        complements_and_missing: [
          "Post-launch KPI review measures actual feature outcomes in production.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "Go/no-go at every environment gate: Ops, QA, partner systems",
        ],
      },
    },
  },
  returnLoops: {
    "loop-02-to-02-0": {
      trigger_condition: "Request deemed unready: vague need, unsubstantiated benefits, oversized scope.",
      reason: "Committee questions, missing details, benefit hypotheses to back up, potential re-scoping.",
      impact_summary:
        "Feedback is logged on the Feature. Product Orchestrator resumes PRD Authoring, produces a revised PRD answering each point, and PO / PM re-validates STATUS: PRD VALIDATED.",
    },
    "loop-02-to-01-1": {
      trigger_condition: "Feedback challenges qualification (who, what, why, scope); orchestrator resumes Qualification.",
      reason: "Feedback challenges qualification (who, what, why, scope); orchestrator resumes Qualification.",
    },
    "loop-04-to-03-0": {
      trigger_condition: "Study uncovers a blocking issue or architecture board issues a no-go.",
      reason: "Blockers, open questions, deeper scenarios needed, CISO requirements.",
      impact_summary:
        "Walkthrough and board comments attach to the Study Dossier. Architect resumes in corrections mode; agent integrates remarks and flags dependent sections; architect arbitrates.",
    },
    "loop-04-to-04-1": {
      trigger_condition: "Feedback targets product requirements rather than architecture.",
      reason: "Feedback targets product requirements rather than architecture.",
    },
    "loop-04-to-02-2": {
      trigger_condition: "Feedback challenges the underlying business need itself.",
      reason: "Feedback challenges the underlying business need itself.",
    },
    "loop-06-to-06-0": {
      trigger_condition: "Teams do not commit: incomplete split, unhandled dependencies.",
      reason: "Cross-team dependencies, missing or oversized stories, team questions.",
      impact_summary:
        "PI Planning remarks attach to the Feature. PO restarts Agent US: splitting revises stories, Quality Check re-verifies, and nothing is created without sign-off.",
    },
    "loop-06-to-04-1": {
      trigger_condition: "Requirements are insufficient to split into stories.",
      reason: "Requirements are insufficient to split into stories.",
    },
    "loop-08-to-08-0": {
      trigger_condition: "Code review requests changes.",
      reason: "Line-by-line review comments.",
      impact_summary:
        "Pull request comments become input for the coding agent's next iteration. Developer drives fixes; review remains human.",
    },
    "loop-09-to-08-0": {
      trigger_condition: "Result fails acceptance criteria.",
      reason: "Observed gaps, criterion by criterion.",
      impact_summary:
        "Agent compares output to acceptance criteria and documents gaps, proposing return to development or refinement; PO confirms.",
    },
    "loop-09-to-07-1": {
      trigger_condition: "Acceptance criterion itself is ambiguous or incomplete.",
      reason: "Acceptance criterion itself is ambiguous or incomplete.",
    },
    "loop-10-to-08-0": {
      trigger_condition: "Blocking defect appears in regression, load, integration, or staging tests.",
      reason: "Defect details, target environment, triggering scenario.",
      impact_summary:
        "The triggering scenario joins the test suite; fix restarts from development with that scenario as input.",
    },
    "loop-10-to-10-1": {
      trigger_condition: "Issue stems from deployment runbook or procedure rather than code.",
      reason: "Issue stems from deployment runbook or procedure rather than code.",
    },
  },
  opportunities: {
    P1: {
      title: "Standardize Feature content",
      description:
        "Standardize review expectations: description, benefit hypotheses, acceptance criteria. All three Jira fields exist; adding a template and sizing unlocks downstream prioritization and clean agent intake.",
    },
    P2: {
      title: "Standardize User Story format",
      description:
        "Structure acceptance criteria in agent-readable Given/When/Then format and derive QA scenarios, unlocking automated test generation and tool-assisted PO review.",
    },
    P3: {
      title: "Auto-generate User Stories",
      description:
        "Generate templated User Stories from the architecture study and need so refinement becomes a review, removing copy-paste and pre-wiring Epic/Confluence/mockup context.",
    },
  },
};
