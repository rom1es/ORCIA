// @vitest-environment jsdom
import { cleanup, render, screen, within } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  AgentDetailAndSandboxModal,
  AssistantGovernanceModalAndStudio,
  type UiManagedAgentItem,
} from "@orcia/ui";
import { writeCachedAgentsAndSkills } from "../components/agentsAndSkillsBridgeStore";
import {
  clearPlatformSetupStorage,
  type ConfiguredPackItem,
} from "../components/platformSetupStore";
import { buildAssistantAutocompleteSuggestions } from "../features/inbox/assistantAutocompleteHelpers";
import { ProcessRunActionBanner } from "../features/processes/execution/ProcessRunActionBanner";
import type { InteractiveProcessDrawerStatus } from "../features/processes/execution/useInteractiveProcessRunController";
import { getDelegateAgents } from "../features/processes/studio/studioCatalogLabels";
import type { WorkflowDefinitionV2Item } from "../features/processes/processStudioV2Data";
import { ASSISTANT_GOVERNANCE_LABELS_EN } from "../i18n/locales/assistant_stream_labels_en";
import { GOVERNANCE_AND_PACKS_EN_LABELS } from "../i18n/locales/governance_and_packs_labels_en";
import { resetVitestApiBackend } from "./vitest.setup";

const SAMPLE_WORKFLOW: WorkflowDefinitionV2Item = {
  id: "wf-audit-30-6",
  slug: "wf-audit-30-6",
  title: "Architecture Qualification",
  pack_id: "orcia-pack-sdlc",
  vsm_step_num: "01",
  version: "1.0.0",
  status: "published",
  orchestration_type: "deterministic_dbos",
  reflexive_objective: "Verify single decision CTA gating",
  execution_mode: "native_orcia",
  agent_ref: "agent-architecte-solution",
  skills_refs: [],
  knowledge_base_refs: [],
  triggers: [],
  contract: { inputs: [], outputs: [], exit_criteria: [] },
  sub_steps: [
    {
      id: "step-1",
      short_label: "Scope",
      name: "Scope Review",
      trigger_condition_label: "On start",
      role_description: "Review architecture scope",
      instruction_prompt_or_ref: "Review scope",
      output_description: "Scoped summary",
      mcp_tools_allowed: [],
      write_preview_required: false,
      requires_human_checkpoint: true,
      enabled: true,
      human_authored_required: false,
    },
  ],
  controls: { deterministic_gates: [], probabilistic_evaluations: [] },
  guardrails: [],
};

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
});

afterEach(() => {
  cleanup();
});

describe("Story 30.6 — Epic 30 Anti-Regression UI & Lifecycle Audits", () => {
  it("(a) enforces inline modal [role='alert'] rendering across governance and agent modals", () => {
    // Behavioral check 1: AssistantGovernanceModalAndStudio renders [role='alert'] inside its dialog container.
    render(
      React.createElement(AssistantGovernanceModalAndStudio, {
        workspaceId: "ws-audit",
        canEditWorkspaceLayer: true,
        isOpen: true,
        saveError: "HTTP 422 ERR_VALIDATION_FAILED",
        assembledLayers: [],
        labels: ASSISTANT_GOVERNANCE_LABELS_EN,
      }),
    );
    const govDialog = screen.getByTestId("assistant-governance-container");
    const govAlert = within(govDialog).getByTestId("assistant-gov-error-banner");
    expect(govAlert.getAttribute("role")).toBe("alert");
    expect(govAlert.textContent).toContain("ERR_VALIDATION_FAILED");
    cleanup();

    // Behavioral check 2: AgentDetailAndSandboxModal renders [role='alert'] inside its dialog container and zero duplicate name input.
    const draftAgent: UiManagedAgentItem = {
      agentId: "agent-audit-modal",
      slug: "audit-modal",
      handle: "@audit-modal",
      name: "Audit Modal Agent",
      roleMission: "Verify inline dialog alert",
      instructions: "Check modal invariants.",
      thinkingLevel: "medium",
      skillIds: [],
      lastExecutionOutput: null,
      visibilityScope: "TEAM",
      enabledOnWorkspace: true,
      mcpExposed: false,
      lifecycleStatus: "DRAFT",
      testBenchStatus: "UNTESTED",
      testBenchValidated: false,
    };
    render(
      React.createElement(AgentDetailAndSandboxModal, {
        agent: draftAgent,
        skills: [],
        labels: GOVERNANCE_AND_PACKS_EN_LABELS.agentsAndSkillsManager,
        testInputValue: "",
        modalError: "HTTP 422 ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED",
        onChangeTestInput: () => undefined,
        onToggleAgentSkill: () => true,
        onExecuteAgent: () => true,
        onClose: () => undefined,
      }),
    );
    const agentDialog = screen.getByTestId("agent-detail-modal-agent-audit-modal");
    const agentAlert = within(agentDialog).getByTestId("agent-detail-modal-error-agent-audit-modal");
    expect(agentAlert.getAttribute("role")).toBe("alert");
    expect(agentAlert.textContent).toContain("ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED");
    expect(within(agentDialog).getAllByTestId("edit-agent-name-input")).toHaveLength(1);
  });

  it("(b) enforces a single state-gated primary Cobalt CTA in /processes/runs/$runId without Bar 1/Bar 2 duplication", () => {
    const expectedPrimaryCount: ReadonlyArray<
      readonly [InteractiveProcessDrawerStatus, number]
    > = [
      ["WAITING_SUBSTEP_HITL", 1],
      ["WAITING_WRITE_PREVIEW", 1],
      ["WAITING_EXTERNAL_GATE", 1],
      ["WAITING_FINAL_ANCHOR", 1],
      ["RUNNING", 1],
      ["SLA_SUSPENDED", 0],
      ["COMPLETED_APPROVED", 0],
    ];

    for (const [status, expectedCount] of expectedPrimaryCount) {
      const { container, unmount } = render(
        React.createElement(ProcessRunActionBanner, {
          workflow: SAMPLE_WORKFLOW,
          isFr: false,
          status,
          statusLabel: status,
          currentSubStep: SAMPLE_WORKFLOW.sub_steps[0],
          iteration: 1,
          reentryMode: "initial",
          signedTokenPreview: null,
          returnLoopTargetStep: "1",
          returnLoopRemarks: "",
          onSimulateExternalWebhook: () => undefined,
          onApproveCurrentSubStep: () => undefined,
          onAction1AcceptAndSign: () => undefined,
          onAction3RejectAndLoop: () => undefined,
          onAction4SuspendSla: () => undefined,
          onChangeReturnLoopTarget: () => undefined,
          onChangeReturnLoopRemarks: () => undefined,
        }),
      );
      const banner = within(container).getByTestId("process-run-zone1-action-banner");
      const primaryButtons = banner.querySelectorAll("button.orcia-ds-btn-primary");
      expect(primaryButtons.length, `Status ${status} must render ${expectedCount} primary CTA`).toBe(
        expectedCount,
      );
      unmount();
    }
  });

  it("(c) excludes DRAFT agents from Assistant @agent autocomplete and Processes delegate selection", () => {
    const activePack: ConfiguredPackItem = {
      packKey: "orcia-pack-sdlc",
      version: "1.0.0",
      scopePath: "GLOBAL",
      status: "PUBLISHED",
    };
    writeCachedAgentsAndSkills({
      skills: [],
      agents: [
        {
          agentId: "agent-draft-blocked",
          slug: "draft-blocked",
          handle: "@draft-blocked",
          name: "Draft Blocked Agent",
          roleMission: "Must stay excluded",
          instructions: "Never expose while DRAFT.",
          thinkingLevel: "medium",
          skillIds: [],
          lastExecutionOutput: null,
          visibilityScope: "TEAM",
          enabledOnWorkspace: true,
          mcpExposed: false,
          lifecycleStatus: "DRAFT",
          testBenchStatus: "UNTESTED",
          testBenchValidated: false,
        },
        {
          agentId: "agent-active-ready",
          slug: "active-ready",
          handle: "@active-ready",
          name: "Active Ready Agent",
          roleMission: "Allowed in Assistant and Processes",
          instructions: "Run cleanly.",
          thinkingLevel: "medium",
          skillIds: [],
          lastExecutionOutput: null,
          visibilityScope: "TEAM",
          enabledOnWorkspace: true,
          mcpExposed: false,
          lifecycleStatus: "ACTIVE",
          testBenchStatus: "PASSED",
          testBenchValidated: true,
        },
      ],
    });

    const assistantTokens = buildAssistantAutocompleteSuggestions([activePack], false).map(
      (s) => s.token,
    );
    expect(assistantTokens).toContain("@active-ready");
    expect(assistantTokens).not.toContain("@draft-blocked");

    for (const loc of ["fr", "en"] as const) {
      const delegates = getDelegateAgents(loc).map((d) => d.slug);
      expect(delegates).toContain("active-ready");
      expect(delegates).not.toContain("draft-blocked");
    }
  });
});
