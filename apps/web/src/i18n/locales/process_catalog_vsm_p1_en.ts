import type { ProcessCatalogVsmPart1Dictionary } from "./process_catalog_vsm_labels";

export const PROCESS_CATALOG_VSM_P1_EN: ProcessCatalogVsmPart1Dictionary = {
  title: "Idea to Production",
  subtitle: "Mon Compte Agentic Workflow",
  knowledgeBase: {
    title: "Knowledge Base",
    description:
      "A single source of truth, kept up to date and projected for each reader, human or agent. Today knowledge is scattered across eight places, only one of which is authoritative: the code.",
  },
  phases: {
    "01": { name: "Emergence & Framing", goal: "From need to specifications", deliverables_summary: "4 steps" },
    "02": { name: "Prioritization & Commitment", goal: "From study to committed PI", deliverables_summary: "2 steps" },
    "03": { name: "Realization", goal: "From code to approved US", deliverables_summary: "3 steps" },
    "04": { name: "Delivery", goal: "From release to production launch", deliverables_summary: "2 steps" },
  },
  steps: {
    "01": {
      title: "Funnel",
      actor_label: "Rovo",
      status_badge: "Agentified",
      summary: "The **Qualification** sub-agent defines the who, what, why, and scope of the need.",
      deliverable: "A qualified need: who, what, why, scope, validated by PO / PM",
      attention_point:
        "The title is the only mandatory field. Linking an epic is recommended to indicate the track, though not enforced. Neither architect nor target PI is set at this stage.",
      today: {
        actors: "PO / PM manually",
        activities:
          "PO / PM creates the ticket in Jira. Title is the only mandatory field. · Linking to an epic is recommended but optional.",
        deliverable: "A ticket shell with a title",
        pain_points: "None; the ticket can remain an empty shell",
      },
      tomorrow: {
        actors:
          "The **Qualification** sub-agent defines who, what, why, and scope by gathering context from Confluence, Jira, or the web. PO / PM validates STATUS: QUALIFIED.",
        activities:
          "PO / PM describes the need to the Product Orchestrator. · Orchestrator delegates qualification to the sub-agent, which gathers context and stakeholders. · Sub-agent drafts who, what, why, and scope verbatim. · PO / PM edits until ready. · PO / PM validates STATUS: QUALIFIED; the orchestrator waits for approval.",
        deliverable: "A qualified need: who, what, why, scope, validated by PO / PM",
        gains: "PO / PM validates STATUS: QUALIFIED",
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {
          qualification: {
            name: "Need Qualification",
            shortLabel: "Qualification",
            trigger: "Always first",
            role: "Defines who, what, why, and scope.",
            output: "Qualified need",
            humanCheck: "STATUS: QUALIFIED",
          },
        },
        human_ai_interactions: {
          initiative: "An explored need from discovery",
          humanValidation: "PO / PM validates STATUS: QUALIFIED before PRD authoring can start",
        },
        delegation_note: "Quality checks for intake cover the PRD and are described in Step 02.",
        complements_and_missing: [
          "The title is the only mandatory field. Linking an epic is recommended, though not enforced. Neither architect nor target PI is set at this stage.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "PO / PM validates STATUS: QUALIFIED before the agent proceeds to PRD authoring.",
        ],
      },
    },
    "02": {
      title: "In Review",
      actor_label: "Rovo",
      status_badge: "POC Step 1",
      summary: "**PRD Authoring** writes the PRD, then **Jira Creation** creates the Feature ticket in MCIA.",
      deliverable:
        "Feature ticket (the PRD): templated, with KPIs, acceptance criteria, WSJF, and effort, duplicate-free and ready for the intake committee",
      attention_point:
        "**The Feature ticket is the PRD**: drafted here with enough detail for committee decisions, finalized in Step 04. All three fields are distinct in Jira and extractable. Scope creep and target PI risks emerge early here.",
      today: {
        actors: "PO / PM. Free-form format.",
        activities:
          "PO / PM drafts description, benefit hypotheses, and acceptance criteria free-form. · Gathers UX, legal, and business inputs. · Submits to intake committee.",
        deliverable: "Feature ticket (the PRD): description, benefit hypotheses, acceptance criteria",
        pain_points: "Intake committee: business, engineering, build & run managers, PO, architects",
      },
      tomorrow: {
        actors:
          "**PRD Authoring** sub-agent drafts the Light PRD (KPIs, acceptance criteria, WSJF, effort). Once STATUS: PRD VALIDATED, **Jira Creation** checks duplicates and creates the Feature after preview.",
        activities:
          "After QUALIFIED validation, the orchestrator assigns PRD drafting. · Sub-agent searches templates and KPIs and drafts Light PRD. · PO / PM validates STATUS: PRD VALIDATED. · Sub-agent checks duplicates and prepares the MCIA Feature ticket. · PO / PM confirms preview and creates ticket. · Moves to intake committee.",
        deliverable:
          "Feature ticket (the PRD): templated, with KPIs, acceptance criteria, WSJF, and effort, duplicate-free and ready for the intake committee",
        gains: "PO / PM validates PRD and Feature, then the intake committee decides",
      },
      passage_point: {
        decision: "Intake Committee",
        question:
          "The drafted need is pitched to business, tech, build/run managers, PO, and architects. Either architects take over or it returns for revision.",
        possible_outcomes: [
          "Return to Step 02 (corrections)",
          "Return to Step 01 (corrections)",
          "Approve & proceed to next step",
        ],
      },
      detail_tabs: {
        agent_sub_steps: {
          prd: {
            name: "PRD Authoring",
            shortLabel: "PRD",
            trigger: "After STATUS: QUALIFIED approval",
            role: "Drafts Light PRD: KPIs, acceptance criteria, WSJF, effort.",
            output: "PRD content validated by PO / PM",
            humanCheck: "STATUS: PRD VALIDATED",
          },
          jira: {
            name: "Jira Creation",
            shortLabel: "Jira",
            trigger: "After STATUS: PRD VALIDATED approval",
            role: "Checks duplicates and creates the Feature in MCIA.",
            output: "Feature ticket (the PRD) created in MCIA",
            humanCheck: "Preview approved, then ticket created",
          },
        },
        human_ai_interactions: {
          initiative: "The ticket and inputs to gather: UX, legal, business",
          humanValidation:
            "PO / PM validates STATUS: PRD VALIDATED and Feature preview; then the intake committee decides",
        },
        deterministic_gates: {
          "det-02-1": {
            name: "Field completeness script",
            short_label: "Script: characters per field",
            status: "hypothesis",
            verifies_description: "Checks character count on each Feature ticket field.",
            on_ko_behavior: "To be specified.",
          },
        },
        non_deterministic_gates: {
          "ndet-02-1": {
            name: "PRD challenger agent",
            short_label: "PRD challenger agent",
            status: "hypothesis",
            verifies_description: "Challenges the PRD on substance.",
            hypothesis_note:
              "Hypothesis to confirm: leverage architecture study business questions to strengthen the need.",
            on_ko_behavior: "To be specified.",
          },
        },
        complements_and_missing: [
          "**The Feature ticket is the PRD**: drafted here for committee decisions, finalized in Step 04. Three distinct extractable Jira fields help detect scope creep early.",
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "PO / PM validates STATUS: PRD VALIDATED and Feature preview; then the intake committee decides.",
        ],
      },
    },
    "03": {
      title: "Architecture Framing",
      actor_label: "GitHub Copilot",
      status_badge: "POC Step 3",
      summary:
        "The architect builds the study with the agent as a thinking partner: the agent questions, proposes, and drafts; the architect arbitrates.",
      deliverable:
        "Templated Study Dossier co-built with the architect: solution, decision log, Mermaid diagrams, T-shirt sizing, open questions",
      attention_point:
        '"Framing" here strictly means **architecture framing**. Output goes to two distinct forums: systematic team walkthrough and architecture board when impact requires it.',
      today: {
        actors: "Lead architect. Variable output without sizing.",
        activities:
          "Lead architect writes the study dossier in Confluence with variable format and no sizing. · Walks the team through, then presents to architecture board if impact warrants.",
        deliverable: "Study dossier in Confluence",
        pain_points: "Mandatory team walkthrough, then architecture board depending on impact; CISO if sensitive.",
      },
      tomorrow: {
        actors:
          "The architect co-builds with **CRL Architecture Study**, which gathers existing facts, asks consolidated questions, proposes options, and drafts; the architect arbitrates every milestone.",
        activities:
          "Architect starts with Feature key. · Agent reads KB, code, and past studies, analyzes impact, and asks one consolidated questionnaire. · Checkpoint 1: architect confirms understanding. · Agent designs solution or proposes 2–3 options. · Checkpoint 2: architect picks solution. · Agent drafts block by block; architect validates each. · Agent runs 14-point check; architect reviews and signs off.",
        deliverable:
          "Templated Study Dossier co-built with the architect: solution, decision log, Mermaid diagrams, T-shirt sizing, open questions",
        gains: "Architect arbitrates at every checkpoint, then walkthrough and board",
      },
      passage_point: null,
      detail_tabs: {
        agent_sub_steps: {
          comprendre: {
            name: "Understand need & existing system",
            shortLabel: "Understand",
            trigger: "Generate mode with ticket key or URL",
            role: "Reads ticket and KB, checks code impact, and asks one consolidated questionnaire for missing info.",
            output: "Understanding of need, impacted systems, and gaps",
            humanCheck: "Validation point 1",
          },
          concevoir: {
            name: "Design the solution",
            shortLabel: "Design",
            trigger: "After agreement on understanding",
            role: "Designs from existing stack; proposes 2–3 options and recommendation when undecided.",
            output: "Selected solution, or options and recommendation",
            humanCheck: "Validation point 2",
          },
          rediger: {
            name: "Draft block by block",
            shortLabel: "Draft",
            trigger: "After solution selection",
            role: "Drafts the dossier in six blocks from context to impacts, pausing after each.",
            output: "Dossier, block by block",
            humanCheck: "Each block validated",
          },
          controler: {
            name: "Verify and report",
            shortLabel: "Verify",
            trigger: "After the last block",
            role: "Checks 14 points (sources, decisions, stack, diagrams, summary, impacts) and reports.",
            output: "Dossier and report: stack choices, decisions to justify, open questions",
            humanCheck: "Architect reviews and completes: the study remains theirs",
          },
        },
        human_ai_interactions: {
          initiative: "Feature ticket (PRD), CRL knowledge base, crl-back/crl-front code, past studies",
          humanValidation:
            "Architect arbitrates understanding, solution choice, and every drafted block; then team walkthrough and architecture board.",
        },
        non_deterministic_gates: {
          "ndet-03-1": {
            name: "Adversarial reviewer agent",
            short_label: "Adversarial reviewer",
            status: "add",
            verifies_description: "Reviews generated study adversarially and flags weaknesses.",
            hypothesis_note: null,
            on_ko_behavior: "Objections return to the Architecture Study agent; architect arbitrates.",
          },
          "ndet-03-2": {
            name: "14-point final review",
            short_label: "Agent final check",
            status: "place",
            verifies_description: "Self-checks dossier: sources, decisions, stack, diagrams, summary, impacts.",
            hypothesis_note: null,
            on_ko_behavior: "Agent fixes issues; edits touching validated blocks require architect approval.",
          },
        },
        complements_and_missing: [
          '"Framing" strictly means **architecture framing**. Two distinct forums follow: systematic team walkthrough and conditional architecture board.',
        ],
        guardrails: [
          "AI is a thinking tool and assistant; humans own every action.",
          "Architect arbitrates understanding, solution choice, and every drafted block.",
        ],
      },
    },
  },
};
