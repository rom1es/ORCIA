import React, { useState } from "react";

export interface StudioCopilotSidebarProps {
  onAttachSkill: (skillUri: string) => void;
  onAttachMcpTool: (toolPermission: string) => void;
  onAttachDeterministicGate: (gate: {
    id: string;
    name: string;
    runner: "markdown_contract_runner" | "json_schema_runner" | "cli_sandbox_runner" | "catalog_invariant_runner";
  }) => void;
  isFr: boolean;
}

const AVAILABLE_MCP_TOOLS = [
  "mcp:atlassian-jira (read)",
  "mcp:atlassian-jira (write_preview)",
  "mcp:atlassian-confluence (read)",
  "mcp:atlassian-confluence (write_preview)",
  "mcp:git-provider (read)",
];

const AVAILABLE_SKILLS = [
  "pack://sdlc/skills/qualification-besoin",
  "pack://sdlc/skills/redaction-prd-wsjf",
  "pack://sdlc/skills/diagrammes-mermaid",
  "pack://sdlc/skills/decoupe-us-invest",
  "pack://orcia-docs/skills/redaction-aide-bilingue",
];

const AVAILABLE_GATES: ReadonlyArray<{
  id: string;
  name: string;
  runner: "markdown_contract_runner" | "json_schema_runner" | "cli_sandbox_runner" | "catalog_invariant_runner";
}> = [
  {
    id: "det-prd-fields",
    name: "Contrat Markdown PRD & WSJF",
    runner: "markdown_contract_runner",
  },
  {
    id: "det-de-14-points",
    name: "Contrôle Dossier d'Étude 14 points",
    runner: "markdown_contract_runner",
  },
  {
    id: "det-invest-dor",
    name: "Validation INVEST & Gherkin DoR",
    runner: "json_schema_runner",
  },
  {
    id: "det-validate-help-article",
    name: "Validation Aide Bilingue FR/EN",
    runner: "catalog_invariant_runner",
  },
];

export function StudioCopilotSidebar({
  onAttachSkill,
  onAttachMcpTool,
  onAttachDeterministicGate,
  isFr,
}: StudioCopilotSidebarProps) {
  const [prompt, setPrompt] = useState<string>("");
  const [messages, setMessages] = useState<Array<{ sender: "user" | "copilot"; text: string }>>([
    {
      sender: "copilot",
      text: isFr
        ? "Bonjour ! Je suis le Copilot de Conception Process Studio. Cliquez sur [+] pour rattacher un connecteur MCP (orcia-connectors), un Skill Markdown ou une Gate déterministe au workflow."
        : "Hello! I am the Process Studio Design Copilot. Click [+] to attach an MCP connector, Markdown Skill, or deterministic Gate.",
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
        text: isFr
          ? `Suggestion appliquée pour « ${trimmed} » : privilégiez un runner déterministe en amont (auto-heal 3x) avant l'agent contradicteur.`
          : `Suggestion prepared for "${trimmed}": run a deterministic gate (3x self-heal) before the adversarial agent.`,
      },
    ]);
    setPrompt("");
  };

  return (
    <aside
      data-testid="studio-copilot-sidebar"
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <div>
        <h3 style={{ margin: 0, fontSize: "15px" }}>
          {isFr ? "🤖 Copilot de Conception & Catalogue [+]" : "🤖 Design Copilot & [+] Catalog"}
        </h3>
        <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {isFr
            ? "Ajoutez en 1 clic les briques déclaratives des Packs et connecteurs MCP."
            : "Attach declarative Pack assets and MCP connectors in 1 click."}
        </p>
      </div>

      {/* Chat Log */}
      <div
        data-testid="studio-copilot-messages"
        className="rounded border p-2.5 text-xs"
        style={{
          backgroundColor: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-subtle)",
          maxHeight: "150px",
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
            <strong>{msg.sender === "copilot" ? "Copilot :" : "Vous :"}</strong> {msg.text}
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: "6px" }}>
        <input
          type="text"
          data-testid="studio-copilot-input"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={
            isFr
              ? "Ex: Ajouter un contrôle WSJF..."
              : "E.g., Add WSJF check..."
          }
          className="orcia-ds-input"
          style={{ flex: 1 }}
        />
        <button
          type="button"
          data-testid="studio-copilot-send-btn"
          onClick={handleSendPrompt}
          className="orcia-ds-btn-primary"
        >
          {isFr ? "Envoyer" : "Send"}
        </button>
      </div>

      {/* Clickable [+] MCP Toolboxes */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px" }}>
          {isFr ? "Toolboxes MCP (orcia-connectors) :" : "MCP Toolboxes (orcia-connectors):"}
        </strong>
        {AVAILABLE_MCP_TOOLS.map((tool) => (
          <div
            key={tool}
            className="flex items-center justify-between gap-2 rounded border px-2 py-1 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>{tool}</span>
            <button
              type="button"
              data-testid={`copilot-add-mcp-${tool.replace(/[^a-z0-9]/gi, "-")}`}
              onClick={() => onAttachMcpTool(tool)}
              className="orcia-ds-btn-secondary"
            >
              [+]
            </button>
          </div>
        ))}
      </div>

      {/* Clickable [+] Declarative Skills */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px" }}>
          {isFr ? "Skills Markdown (packs/<domaine>/skills/) :" : "Markdown Skills:"}
        </strong>
        {AVAILABLE_SKILLS.map((skill) => (
          <div
            key={skill}
            className="flex items-center justify-between gap-2 rounded border px-2 py-1 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>
              {skill.replace("pack://", "")}
            </span>
            <button
              type="button"
              data-testid={`copilot-add-skill-${skill.split("/").pop()}`}
              onClick={() => onAttachSkill(skill)}
              className="orcia-ds-btn-secondary"
            >
              [+]
            </button>
          </div>
        ))}
      </div>

      {/* Clickable [+] Generic Deterministic Gates */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px" }}>
          {isFr ? "Runners Déterministes de Gates :" : "Deterministic Gate Runners:"}
        </strong>
        {AVAILABLE_GATES.map((gate) => (
          <div
            key={gate.id}
            className="flex items-center justify-between gap-2 rounded border px-2 py-1 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>{gate.name}</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "10.5px", color: "var(--color-text-secondary)" }}>
                {gate.runner}
              </div>
            </div>
            <button
              type="button"
              data-testid={`copilot-add-gate-${gate.id}`}
              onClick={() => onAttachDeterministicGate(gate)}
              className="orcia-ds-btn-secondary"
            >
              [+]
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
