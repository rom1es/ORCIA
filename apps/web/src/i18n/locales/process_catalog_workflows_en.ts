import type { ProcessCatalogWorkflowsDictionary } from "./process_catalog_packs_and_workflows_labels";

export const PROCESS_CATALOG_WORKFLOWS_EN: ProcessCatalogWorkflowsDictionary = {
  packs: {
    "orcia-pack-sdlc": {
      name: "SDLC Pack — Mon Compte (Idea to Production)",
      description:
        "End-to-end 11-step, 4-phase value stream with 4 guided business processes, 4 specialist agents, 4 skills, and 6 quality gates.",
      connectorUsedFor: {
        "mcp:atlassian-jira": "Read requests/Epics/User Stories and write with prior human confirmation",
        "mcp:atlassian-confluence": "Knowledge base, PRD, Architecture Study Dossiers, and Release notes",
        "mcp:git-provider": "Repository tree, branches, Pull Requests, and External Gate (Step 08)",
      },
    },
    "orcia-pack-docs": {
      name: "ORCIA Documentation & Contextual Help Pack",
      description: "Declarative pack for authoring and validating bilingual FR/EN contextual help guides.",
      connectorUsedFor: {
        "mcp:git-provider": "Repository inspection and documentation export",
      },
    },
  },
  workflows: {
    "wf-01-qualification-prd": {
      title: "Need Qualification, PRD Authoring & Jira Feature Creation",
      triggerSourceLabels: ["VSM Step 01, 02 Entry"],
      contractInputs: ["Initial request (need statement or intake ticket)"],
      contractOutputs: ["# PRD", "## Context", "## Objectives & KPIs", "## Acceptance Criteria", "## WSJF"],
      contractExitCriteria: ["Automated checks passed (up to 3 retries)", "Signed human approval"],
      subSteps: {
        qualification: {
          name: "Need qualification",
          short_label: "Qualification",
          trigger_condition_label: "Always runs first",
          role_description: "Defines the who, what, why, and scope.",
          output_description: "Qualified need brief",
          checkpoint_question: "validated by PO / PM",
        },
        prd: {
          name: "PRD authoring",
          short_label: "PRD",
          trigger_condition_label: "After STATUS: QUALIFIED approval",
          role_description: "Drafts the Light PRD: KPIs, acceptance criteria, WSJF, effort.",
          output_description: "PRD content, validated by PO / PM",
          checkpoint_question: "validated by PO / PM",
        },
        jira: {
          name: "Jira Feature creation",
          short_label: "Jira",
          trigger_condition_label: "After STATUS: PRD VALIDATED approval",
          role_description: "Checks for duplicates and creates the Feature in project MCIA.",
          output_description: "Feature ticket (the PRD) created in project MCIA",
          checkpoint_question: "Preview confirmed, then ticket created",
        },
      },
      deterministicGates: { "det-02-1": { name: "Field completeness validation script" } },
      probabilisticEvaluations: {
        "ndet-02-1": { name: "PRD challenger agent", rubric_ref: "Challenges the PRD on substance and clarity." },
      },
      guardrails: [
        "Never skip a sub-step without human sign-off on the STATUS block.",
        "Always require a preview before creating the Feature ticket in Jira.",
      ],
    },
    "wf-03-etude-architecture": {
      title: "Architecture Framing Study (CRL-Archi-Study — 4 sub-steps)",
      triggerSourceLabels: ["VSM Step 03 Entry"],
      contractInputs: ["prd_valide_uri (PRD approved by Intake Committee)"],
      contractOutputs: [
        "# Architecture Study Dossier",
        "## Context & Requirements",
        "## Architecture Scenarios",
        "## Application Impacts",
        "## Security & Resilience",
      ],
      contractExitCriteria: ["Automated checks passed (up to 3 retries)", "Signed human approval"],
      subSteps: {
        comprendre: {
          name: "Understand need and existing system",
          short_label: "Understand",
          trigger_condition_label: "Generate mode, with a ticket key or URL",
          role_description:
            "Reads the ticket and full knowledge base, analyzes impact, checks code, and asks one consolidated questionnaire for missing context.",
          output_description: "Understanding of the need, impacted system, and gaps",
          checkpoint_question: "architect confirms or corrects understanding",
        },
        concevoir: {
          name: "Design the solution",
          short_label: "Design",
          trigger_condition_label: "After agreement on understanding",
          role_description:
            "Designs from existing architecture. When open choices exist, proposes 2 or 3 options with a recommendation and stack rationale.",
          output_description: "Selected solution, or options and recommendation",
          checkpoint_question: "architect chooses the solution",
        },
        rediger: {
          name: "Draft block by block",
          short_label: "Draft",
          trigger_condition_label: "After solution selection",
          role_description: "Drafts the Study Dossier in six blocks from context to impacts, pausing after each.",
          output_description: "Study Dossier, block by block",
          checkpoint_question: "architect validates, edits, or completes",
        },
        controler: {
          name: "Verify and report",
          short_label: "Verify",
          trigger_condition_label: "After the final block",
          role_description:
            "Verifies the dossier across 14 checkpoints (sources, decisions, stack, diagrams, summary, impacts) and reports findings.",
          output_description: "Study Dossier and summary: stack choices, decisions to justify, open questions",
          checkpoint_question: "Architect reviews and completes: the study remains theirs",
        },
      },
      deterministicGates: {},
      probabilisticEvaluations: {
        "ndet-03-1": {
          name: "Adversarial reviewer agent",
          rubric_ref: "Reviews the generated study adversarially and flags weaknesses.",
        },
        "ndet-03-2": {
          name: "14-point final review",
          rubric_ref: "Verifies sources, decisions, stack, diagrams, summary, and impacts.",
        },
      },
      guardrails: [
        "The architect remains the sovereign author of the Study Dossier.",
        "Every claim about existing systems is verified against the knowledge base and code.",
      ],
    },
    "wf-06-decoupe-us": {
      title: "Epic & INVEST User Story Splitting (5 sub-steps)",
      triggerSourceLabels: ["VSM Step 06 Entry"],
      contractInputs: ["feature_key (Approved Feature key (PRD + Study))"],
      contractOutputs: ["# User Story Breakdown", "## Epic", "## User Stories", "## Acceptance Criteria"],
      contractExitCriteria: ["Automated checks passed (up to 3 retries)", "Signed human approval"],
      subSteps: {
        analyse: {
          name: "Analysis",
          short_label: "Analyze",
          trigger_condition_label: "When given a Feature key, or resuming analysis after feedback",
          role_description:
            "Reads the Feature, PRD, and architecture study, summarizes them, and lists grey areas and questions.",
          output_description: "Synthesis and open questions",
          checkpoint_question: "PO answers questions",
        },
        epic: {
          name: "Epic Creator",
          short_label: "Epic",
          trigger_condition_label: "Once analysis is validated and questions answered",
          role_description:
            "Checks whether an Epic already exists for the Feature; otherwise prepares its creation and links it.",
          output_description: "Epic ready and linked to the Feature",
          checkpoint_question: 'PO confirms ("done", "ok")',
        },
        decoupe: {
          name: "US Splitting",
          short_label: "Split",
          trigger_condition_label: "Once the Epic is ready, or to revise the plan or stories",
          role_description:
            "Proposes a splitting plan first, then drafts each User Story following the DoR / INVEST template.",
          output_description: "Detailed User Stories",
          checkpoint_question: "runs review automatically",
        },
        controle: {
          name: "Quality Check",
          short_label: "Check",
          trigger_condition_label: "Automatically after drafting User Stories, or on request",
          role_description:
            "Evaluates User Stories for INVEST, DoR, and PRD coverage. Outputs an OK/KO verdict with a gap table.",
          output_description: "Verdict and gap table",
          checkpoint_question: "explicit PO approval",
        },
        creation: {
          name: "Creation",
          short_label: "Create",
          trigger_condition_label: "Only after explicit approval following an OK verdict",
          role_description: "Creates Stories in Jira under the Epic and links dependencies between them.",
          output_description: "Stories created under the Epic with dependencies linked",
          checkpoint_question: 'PO confirms creation ("done", "ok")',
        },
      },
      deterministicGates: {},
      probabilisticEvaluations: {
        "ndet-06-1": {
          name: "Review sub-agent",
          rubric_ref: "Evaluates Stories for INVEST, DoR, and PRD coverage; outputs OK/KO with a gap table.",
        },
      },
      guardrails: [
        "Every User Story must meet the Definition of Ready (DoR) and Gherkin format.",
        "Mandatory preview before batch creation in Jira.",
      ],
    },
    "wf-08-dev-external-gate": {
      title: "IDE-Assisted Development & External PR Gate before Dev Review",
      external_tool_label: "GitHub Copilot / Claude Code in IDE",
      triggerSourceLabels: ["VSM Step 08 Entry"],
      contractInputs: ["us_key (Ready (DoR) User Story committed to sprint)"],
      contractOutputs: ["# External PR Gate Report"],
      contractExitCriteria: ["Automated checks passed (up to 3 retries)", "Signed human approval"],
      subSteps: {
        "expose-mcp-context": {
          name: "Expose MCP Context Bundle to IDE",
          short_label: "MCP Context",
          trigger_condition_label: "Developer selects User Story",
          role_description: "Assemble the US, Study Dossier, PRD, and team standards into an MCP bundle.",
          instruction_prompt_or_ref: "Expose MCP context bundle for IDE assistant.",
          output_description: "MCP context bundle ready for IDE",
          checkpoint_question: "Context exposed",
        },
        "external-pr-gatekeeper": {
          name: "ORCIA Quality Gate on Submitted Pull Request",
          short_label: "PR Gate",
          trigger_condition_label: "On git:pr_opened webhook receipt",
          role_description: "Run automated and adversarial checks on the Pull Request diff.",
          instruction_prompt_or_ref: "Verify PR diff alignment with US acceptance criteria and Study Dossier.",
          output_description: "Pre-Dev-Review audit report",
          checkpoint_question: "Ready for Dev Review",
        },
      },
      deterministicGates: {
        "det-08-pr-contract": {
          name: "Pull Request & Tests Compliance Contract",
          required_headings: ["# External PR Gate Report"],
        },
      },
      probabilisticEvaluations: {
        "ndet-08-pr-hunter": {
          name: "Adversarial US / Study Alignment Review",
          rubric_ref: "Verifies implementation follows selected Study scenarios and Gherkin acceptance criteria.",
        },
      },
      guardrails: [
        "No automatic merge without human Dev Review sign-off.",
        "Mandatory automated and adversarial checks when the PR opens.",
      ],
    },
    "wf-generate-orcia-documentation": {
      title: "ORCIA Contextual Help Article Generation & Validation",
      reflexive_objective:
        "Explore the target screen's functional context, author a clear, jargon-free bilingual FR/EN contextual help article, and verify all required sections before editorial approval.",
      triggerSourceLabels: ["Manual / API trigger"],
      contractInputs: ["help_key (Target contextual help key, e.g., studio.five-blocks)"],
      contractOutputs: ["# ", "## Purpose", "## Key Steps"],
      contractExitCriteria: ["Automated checks passed (up to 3 retries)", "Signed human approval"],
      subSteps: {
        "draft-bilingual-help": {
          name: "Bilingual FR/EN authoring by @Redacteur-Documentation-Orcia",
          short_label: "Authoring",
          trigger_condition_label: "Help generation request",
          role_description: "Draft the structured contextual help guide.",
          output_description: "Bilingual FR/EN Markdown guide",
          checkpoint_question: "Editorial approval & attachment",
        },
      },
      deterministicGates: {
        "det-docs-markdown": {
          name: "Contextual help structure contract",
          required_headings: ["# ", "## Purpose", "## Key Steps"],
        },
      },
      probabilisticEvaluations: {},
      guardrails: [
        "Always produce aligned French and English versions.",
        "Never expose confidential credentials or ungoverned internal URLs.",
      ],
    },
  },
};
