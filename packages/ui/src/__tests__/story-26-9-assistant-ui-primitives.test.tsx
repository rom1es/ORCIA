import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  AssistantApprovalRequiredCard,
  AssistantSpeedSelectorAndStreamView,
  AssistantToolCallTrace,
  type AssistantSpeedSelectorAndStreamViewLabels,
} from "../index";
import { TEST_ASSISTANT_SPEED_DEFAULTS } from "./assistantLabelsFixture";

const SPEED_LABELS: AssistantSpeedSelectorAndStreamViewLabels = {
  ...TEST_ASSISTANT_SPEED_DEFAULTS,
  headerTitle: "Assistant Response Mode",
  speed1PillLabel: "Fast response",
  speed2PillLabel: "With agent or skill",
  speed3DeepAuditPillLabel: "In-depth analysis",
  cacheHitBadge: "Ready",
  cacheMissBadge: "Preparing",
  nodesDeterministicLabel: "Sources:",
  ttftBadgePrefix: "Latency:",
  inputPlaceholder: "Ask a question...",
  sendPromptCta: "Send",
  toolsUnsupportedNotice: "Selected AI model does not support tools; fast mode only.",
  toolsUnsupportedBadge: "Tools unavailable",
  deepenCta: "Deepen",
  deepenLowEvidenceCta: "Deepen with workspace tools",
};

describe("Story 26.9 — @orcia/ui Assistant Tool Trace, Approval Card, supports_tools=false & Deepen", () => {
  it("renders AssistantToolCallTrace with status badges and line inspection callback", () => {
    const onInspectLines = vi.fn();
    render(
      <AssistantToolCallTrace
        steps={[
          {
            toolCallId: "tc-1",
            toolName: "surgical_read_lines",
            status: "EXECUTED",
            durationMs: 42,
            summary: "Read 25 lines",
            targetUri: "orcia://repo/docs/spec.md",
            startLine: 10,
            endLine: 35,
          },
          {
            toolCallId: "tc-2",
            toolName: "kb.search",
            status: "RUNNING",
          },
        ]}
        labels={{
          heading: "Tools consulted",
          runningLabel: "Running",
          executedLabel: "Executed",
          deniedLabel: "Denied",
          errorLabel: "Error",
          approvalRequiredLabel: "Approval required",
          inspectLinesLabel: "Inspect",
          durationSuffix: "ms",
        }}
        onInspectLines={onInspectLines}
      />,
    );

    expect(screen.getByTestId("assistant-tool-call-trace")).toBeDefined();
    expect(screen.getByTestId("assistant-tool-call-status-EXECUTED").textContent).toBe("Executed");
    expect(screen.getByTestId("assistant-tool-call-status-RUNNING").textContent).toBe("Running");
    fireEvent.click(screen.getByTestId("assistant-tool-call-inspect-btn-tc-1"));
    expect(onInspectLines).toHaveBeenCalledWith({
      uri: "orcia://repo/docs/spec.md",
      startLine: 10,
      endLine: 35,
    });
  });

  it("enforces human anchor validation on AssistantApprovalRequiredCard and handles approve/reject", () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();
    const onOpenProcess = vi.fn();

    const { rerender } = render(
      <AssistantApprovalRequiredCard
        proposal={{
          proposalId: "prop-1",
          actionKind: "CONTINUE_IN_PROCESS",
          targetUri: "git://repo/main/SPEC.md",
          workflowRef: "orcia://system/workflows/hitl-gate",
          rationale: "External repository write requires human validation.",
          requiresHumanAnchor: true,
          status: "PENDING",
        }}
        labels={{
          heading: "Human approval required",
          targetLabel: "Target",
          workflowLabel: "Process",
          humanAnchorLabel: "Human decision note",
          humanAnchorPlaceholder: "Enter rationale...",
          humanAnchorRequiredError: "Please provide at least 10 characters.",
          approveCta: "Approve & launch",
          rejectCta: "Reject",
          approvedStatusLabel: "Approved",
          rejectedStatusLabel: "Rejected",
          openProcessCta: "Open in Processes",
        }}
        onApprove={onApprove}
        onReject={onReject}
        onOpenProcess={onOpenProcess}
      />,
    );

    fireEvent.click(screen.getByTestId("assistant-approval-approve-btn"));
    expect(screen.getByTestId("assistant-approval-validation-error")).toBeDefined();
    expect(onApprove).not.toHaveBeenCalled();

    fireEvent.change(screen.getByTestId("assistant-approval-anchor-input"), {
      target: { value: "Validated by product lead for release." },
    });
    fireEvent.click(screen.getByTestId("assistant-approval-approve-btn"));
    expect(onApprove).toHaveBeenCalledWith("prop-1", "Validated by product lead for release.");

    fireEvent.click(screen.getByTestId("assistant-approval-reject-btn"));
    expect(onReject).toHaveBeenCalledWith("prop-1", "Validated by product lead for release.");

    rerender(
      <AssistantApprovalRequiredCard
        proposal={{
          proposalId: "prop-1",
          actionKind: "CONTINUE_IN_PROCESS",
          targetUri: "git://repo/main/SPEC.md",
          rationale: "External repository write requires human validation.",
          requiresHumanAnchor: true,
          status: "APPROVED",
          runId: "run-999",
        }}
        labels={{
          heading: "Human approval required",
          targetLabel: "Target",
          workflowLabel: "Process",
          humanAnchorLabel: "Human decision note",
          humanAnchorPlaceholder: "Enter rationale...",
          humanAnchorRequiredError: "Please provide at least 10 characters.",
          approveCta: "Approve & launch",
          rejectCta: "Reject",
          approvedStatusLabel: "Approved",
          rejectedStatusLabel: "Rejected",
          openProcessCta: "Open in Processes",
        }}
        onApprove={onApprove}
        onReject={onReject}
        onOpenProcess={onOpenProcess}
      />,
    );

    expect(screen.getByTestId("assistant-approval-status-badge").textContent).toBe("Approved");
    fireEvent.click(screen.getByTestId("assistant-approval-open-process-btn"));
    expect(onOpenProcess).toHaveBeenCalledWith("run-999");
  });

  it("disables Speed 2/3 when supportsTools=false and renders Deepen CTA when supportsTools=true", () => {
    const onSendTurn = vi.fn();
    const onDeepen = vi.fn();

    const { rerender } = render(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-1"
        userId="u-1"
        hat="PM"
        supportsTools={false}
        stepProgress={[]}
        streamedText="Initial fast answer"
        labels={SPEED_LABELS}
        onDeepenLastTurn={onDeepen}
        onSendTurn={onSendTurn}
      />,
    );

    expect(screen.getByTestId("assistant-tools-unsupported-notice").textContent).toContain(
      "does not support tools",
    );
    expect(
      (screen.getByTestId("assistant-speed-pill-SPEED_2_AGENT_TOOLS") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("assistant-deep-audit-pill-toggle") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(screen.queryByTestId("assistant-deepen-turn-btn")).toBeNull();

    fireEvent.click(screen.getByTestId("assistant-model-and-effort-picker-trigger"));
    expect(
      (screen.getByTestId("assistant-effort-option-balanced") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("assistant-effort-option-deep") as HTMLButtonElement).disabled,
    ).toBe(true);

    rerender(
      <AssistantSpeedSelectorAndStreamView
        workspaceId="ws-1"
        userId="u-1"
        hat="PM"
        supportsTools={true}
        lowEvidence={true}
        stepProgress={[]}
        streamedText="Initial fast answer"
        labels={SPEED_LABELS}
        onDeepenLastTurn={onDeepen}
        onSendTurn={onSendTurn}
      />,
    );

    const deepenBtn = screen.getByTestId("assistant-deepen-turn-btn");
    expect(deepenBtn.getAttribute("data-low-evidence")).toBe("true");
    expect(deepenBtn.textContent).toContain("Deepen with workspace tools");
    fireEvent.click(deepenBtn);
    expect(onDeepen).toHaveBeenCalledTimes(1);
  });
});
