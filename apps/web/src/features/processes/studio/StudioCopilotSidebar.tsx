import React, { useState } from "react";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../../i18n";

export interface StudioCopilotSidebarProps {
  onAttachSkill: (skillUri: string) => void;
  onAttachMcpTool: (toolPermission: string) => void;
  onAttachDeterministicGate: (gate: {
    id: string;
    name: string;
    runner:
      | "markdown_contract_runner"
      | "json_schema_runner"
      | "cli_sandbox_runner"
      | "catalog_invariant_runner";
  }) => void;
  isFr: boolean;
}

export function StudioCopilotSidebar({
  onAttachSkill,
  onAttachMcpTool,
  onAttachDeterministicGate,
  isFr,
}: StudioCopilotSidebarProps) {
  const copy = resolveDictionaryForFlag(isFr).processStudioUi.studio;
  const [prompt, setPrompt] = useState<string>("");
  const [messages, setMessages] = useState<
    Array<{ sender: "user" | "copilot"; text: string }>
  >([
    {
      sender: "copilot",
      text: copy.copilotWelcomeMessage,
    },
  ]);

  const handleSendPrompt = () => {
    const trimmed = prompt.trim();
    if (!trimmed) return;
    setMessages((prev) => [
      ...prev,
      { sender: "user", text: trimmed },
      {
        sender: "copilot",
        text: formatI18nTemplate(copy.copilotReplyTemplate, { prompt: trimmed }),
      },
    ]);
    setPrompt("");
  };

  return (
    <aside
      data-testid="studio-copilot-sidebar"
      className="orcia-bento-card min-w-0 overflow-hidden"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        minWidth: 0,
      }}
    >
      <div>
        <h3 style={{ margin: 0, fontSize: "15px" }}>{copy.copilotTitle}</h3>
        <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {copy.copilotSubtitle}
        </p>
      </div>

      {/* Assistant Log */}
      <div
        data-testid="studio-copilot-messages"
        className="rounded border p-2.5 text-xs"
        style={{
          backgroundColor: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-subtle)",
          maxHeight: "130px",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
        }}
      >
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              color:
                msg.sender === "copilot"
                  ? "var(--color-primary-cobalt)"
                  : "var(--color-text-primary)",
            }}
          >
            <strong>
              {msg.sender === "copilot" ? copy.copilotAdvicePrefix : copy.copilotUserPrefix}
            </strong>{" "}
            {msg.text}
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", minWidth: 0 }}>
        <input
          type="text"
          data-testid="studio-copilot-input"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={copy.copilotPlaceholder}
          className="orcia-ds-input min-w-0"
          style={{ flex: "1 1 170px", minWidth: 0 }}
        />
        <button
          type="button"
          data-testid="studio-copilot-send-btn"
          onClick={handleSendPrompt}
          className="orcia-ds-btn-primary shrink-0"
        >
          {copy.copilotAskBtn}
        </button>
      </div>

      {/* Connected tools */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px" }}>{copy.copilotToolsHeading}</strong>
        {copy.copilotTools.map((tool) => (
          <div
            key={tool.id}
            className="flex items-center justify-between gap-2 rounded border px-2.5 py-1.5 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <span style={{ fontSize: "12px" }}>{tool.label}</span>
            <button
              type="button"
              data-testid={`copilot-add-mcp-${tool.id.replace(/[^a-z0-9]/gi, "-")}`}
              onClick={() => onAttachMcpTool(tool.id)}
              className="orcia-ds-btn-secondary"
            >
              +
            </button>
          </div>
        ))}
      </div>

      {/* Business skills */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px" }}>{copy.copilotSkillsHeading}</strong>
        {copy.copilotSkills.map((skill) => (
          <div
            key={skill.id}
            className="flex items-center justify-between gap-2 rounded border px-2.5 py-1.5 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <span style={{ fontSize: "12px" }}>{skill.label}</span>
            <button
              type="button"
              data-testid={`copilot-add-skill-${skill.id.split("/").pop() ?? "skill"}`}
              onClick={() => onAttachSkill(skill.id)}
              className="orcia-ds-btn-secondary"
            >
              +
            </button>
          </div>
        ))}
      </div>

      {/* Automated quality checks */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px" }}>{copy.copilotGatesHeading}</strong>
        {copy.copilotGates.map((gate) => (
          <div
            key={gate.id}
            className="flex items-center justify-between gap-2 rounded border px-2.5 py-1.5 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <span style={{ fontSize: "12px", fontWeight: 500 }}>{gate.name}</span>
            <button
              type="button"
              data-testid={`copilot-add-gate-${gate.id}`}
              onClick={() => onAttachDeterministicGate(gate)}
              className="orcia-ds-btn-secondary"
            >
              +
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
