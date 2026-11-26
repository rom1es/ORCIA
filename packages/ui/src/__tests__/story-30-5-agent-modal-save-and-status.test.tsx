import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AgentDetailAndSandboxModal,
  AgentsAndSkillsManagerView,
  resolveAgentLifecycleAndBenchStatus,
  type UiManagedAgentItem,
} from "../index";
import { TEST_AGENTS_AND_SKILLS_LABELS as TEST_LABELS } from "./agentsAndSkillsLabelsFixture";

const BASE_AGENT: UiManagedAgentItem = {
  agentId: "agent-alpha",
  slug: "alpha",
  handle: "@alpha",
  name: "Agent Alpha",
  roleMission: "Verify compliance",
  instructions: "Check every rule thoroughly.",
  thinkingLevel: "medium",
  skillIds: [],
  lastExecutionOutput: null,
  visibilityScope: "TEAM",
  enabledOnWorkspace: true,
  mcpExposed: false,
  lifecycleStatus: "ACTIVE",
  testBenchStatus: "PASSED",
  testBenchValidated: true,
};

afterEach(() => {
  cleanup();
});

describe("Story 30.5 Agent Detail Modal Save, Error Alert & Factual Status", () => {
  it("renders single 6-block editor without duplicate fields and confirms explicit Save", async () => {
    function Harness() {
      const [agent, setAgent] = useState<UiManagedAgentItem>(BASE_AGENT);
      return (
        <AgentDetailAndSandboxModal
          agent={agent}
          skills={[]}
          testInputValue=""
          labels={TEST_LABELS}
          onChangeTestInput={() => undefined}
          onToggleAgentSkill={async () => true}
          onExecuteAgent={async () => true}
          onUpdateAgentDetails={async (_id, patch) => {
            setAgent((prev) => ({ ...prev, name: patch.name }));
            return true;
          }}
          onClose={() => undefined}
        />
      );
    }

    render(<Harness />);
    expect(screen.getAllByTestId("edit-agent-name-input")).toHaveLength(1);
    expect(screen.queryByTestId("edit-agent-name-input-agent-alpha")).toBeNull();

    const saveBtn = screen.getByTestId("save-agent-detail-modal-btn-agent-alpha") as HTMLButtonElement;
    expect(saveBtn.disabled).toBe(true);

    fireEvent.change(screen.getByTestId("edit-agent-name-input"), {
      target: { value: "Agent Alpha Updated" },
    });
    expect(saveBtn.disabled).toBe(false);

    // Dirty guard triggers on Escape / Cancel before save
    fireEvent.click(screen.getByTestId("cancel-agent-detail-modal-btn-agent-alpha"));
    expect(screen.getByTestId("agent-detail-agent-alpha-unsaved-changes-alert")).toBeDefined();
    fireEvent.click(screen.getByTestId("agent-detail-agent-alpha-unsaved-stay-btn"));

    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(screen.getByTestId("agent-modal-saved-badge-agent-alpha")).toBeDefined();
    });
    expect((screen.getByTestId("save-agent-detail-modal-btn-agent-alpha") as HTMLButtonElement).disabled).toBe(true);
  });

  it("rolls back MCP toggle and displays inline [role='alert'] inside modal on error", async () => {
    const onToggleMcp = vi.fn(async () => false);
    render(
      <AgentDetailAndSandboxModal
        agent={BASE_AGENT}
        skills={[]}
        testInputValue=""
        labels={TEST_LABELS}
        modalError="ERR_PG18_SYNC: Impossible d'exposer en MCP"
        onChangeTestInput={() => undefined}
        onToggleAgentSkill={async () => true}
        onExecuteAgent={async () => true}
        onToggleAgentMcpExposure={onToggleMcp}
        onClose={() => undefined}
      />,
    );

    const mcpCheckbox = screen.getByTestId("agent-mcp-expose-checkbox-agent-alpha") as HTMLInputElement;
    expect(mcpCheckbox.checked).toBe(false);
    fireEvent.click(mcpCheckbox);

    await waitFor(() => {
      expect(onToggleMcp).toHaveBeenCalledWith("agent-alpha", true);
      expect(mcpCheckbox.checked).toBe(false);
    });
    const alert = screen.getByTestId("agent-detail-modal-error-agent-alpha");
    expect(alert.getAttribute("role")).toBe("alert");
    expect(alert.textContent).toContain("ERR_PG18_SYNC");
  });

  it("disables MCP toggle with hint on read-only Pack preset and blocks DRAFT assistant use", () => {
    const packDraftAgent: UiManagedAgentItem = {
      ...BASE_AGENT,
      agentId: "agent-pack-prd-redacteur",
      name: "Pack Rédacteur PRD",
      visibilityScope: "PACK",
      sourcePackKey: "product_management",
      lifecycleStatus: "DRAFT",
      testBenchStatus: "UNTESTED",
      testBenchValidated: false,
    };
    render(
      <AgentsAndSkillsManagerView
        agents={[packDraftAgent]}
        skills={[]}
        labels={TEST_LABELS}
        onCreateSkill={() => undefined}
        onDeleteSkill={() => undefined}
        onUpdateSkillVisibility={() => undefined}
        onExecuteSkill={() => undefined}
        onCreateAgent={() => undefined}
        onDeleteAgent={() => undefined}
        onUpdateAgentVisibility={() => undefined}
        onToggleAgentSkill={() => undefined}
        onExecuteAgent={() => undefined}
        onUseAgentInAssistant={() => undefined}
      />,
    );

    const useAssistantBtn = screen.getByTestId(
      "use-agent-in-assistant-btn-agent-pack-prd-redacteur",
    ) as HTMLButtonElement;
    expect(useAssistantBtn.disabled).toBe(true);
    expect(screen.getByTestId("agent-lifecycle-badge-agent-pack-prd-redacteur").textContent).toContain("Brouillon");
    expect(screen.getByTestId("agent-test-bench-badge-agent-pack-prd-redacteur").textContent).toContain("À tester");

    cleanup();
    render(
      <AgentDetailAndSandboxModal
        agent={packDraftAgent}
        skills={[]}
        testInputValue=""
        labels={TEST_LABELS}
        onChangeTestInput={() => undefined}
        onToggleAgentSkill={async () => true}
        onExecuteAgent={async () => true}
        onToggleAgentMcpExposure={async () => true}
        onClose={() => undefined}
      />,
    );

    const mcpCheckbox = screen.getByTestId(
      "agent-mcp-expose-checkbox-agent-pack-prd-redacteur",
    ) as HTMLInputElement;
    expect(mcpCheckbox.disabled).toBe(true);
    expect(screen.getByTestId("agent-mcp-disabled-hint-agent-pack-prd-redacteur")).toBeDefined();
    expect(
      (screen.getByTestId("detail-agent-pack-prd-redacteur-agent-llm-model-tier-select") as HTMLSelectElement)
        .disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("detail-agent-pack-prd-redacteur-agent-output-contract-select") as HTMLSelectElement)
        .disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("run-agent-btn-agent-pack-prd-redacteur") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("save-agent-detail-modal-btn-agent-pack-prd-redacteur") as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(screen.getByTestId("agent-bench-pack-readonly-hint-agent-pack-prd-redacteur")).toBeDefined();

    // P1-5: omitted lifecycleStatus must strictly default to DRAFT even if lastExecutionOutput exists
    const legacyLike = {
      ...BASE_AGENT,
      lifecycleStatus: undefined,
      lastExecutionOutput: "Old output",
    };
    expect(resolveAgentLifecycleAndBenchStatus(legacyLike).lifecycleStatus).toBe("DRAFT");
  });
});
