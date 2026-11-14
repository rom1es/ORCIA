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

const AVAILABLE_MCP_TOOLS: ReadonlyArray<{ id: string; labelFr: string; labelEn: string }> = [
  {
    id: "mcp:atlassian-jira (read)",
    labelFr: "Jira — Lecture des demandes & tickets",
    labelEn: "Jira — Read requests & issues",
  },
  {
    id: "mcp:atlassian-jira (write_preview)",
    labelFr: "Jira — Création de ticket (sous validation)",
    labelEn: "Jira — Create issue (with approval)",
  },
  {
    id: "mcp:atlassian-confluence (read)",
    labelFr: "Confluence — Lecture du socle documentaire",
    labelEn: "Confluence — Read knowledge base",
  },
  {
    id: "mcp:atlassian-confluence (write_preview)",
    labelFr: "Confluence — Publication de page (sous validation)",
    labelEn: "Confluence — Publish page (with approval)",
  },
  {
    id: "mcp:git-provider (read)",
    labelFr: "Git — Consultation du dépôt & Pull Requests",
    labelEn: "Git — Read repository & Pull Requests",
  },
];

const AVAILABLE_SKILLS: ReadonlyArray<{ uri: string; labelFr: string; labelEn: string }> = [
  {
    uri: "pack://sdlc/skills/qualification-besoin",
    labelFr: "Qualification structurée du besoin",
    labelEn: "Structured Need Qualification",
  },
  {
    uri: "pack://sdlc/skills/redaction-prd-wsjf",
    labelFr: "Rédaction du PRD & priorisation WSJF",
    labelEn: "PRD Authoring & WSJF Prioritization",
  },
  {
    uri: "pack://sdlc/skills/diagrammes-mermaid",
    labelFr: "Schémas d'architecture & flux",
    labelEn: "Architecture & Flow Diagrams",
  },
  {
    uri: "pack://sdlc/skills/decoupe-us-invest",
    labelFr: "Découpage en User Stories (INVEST & Gherkin)",
    labelEn: "INVEST & Gherkin User Story Splitting",
  },
  {
    uri: "pack://orcia-docs/skills/redaction-aide-bilingue",
    labelFr: "Rédaction de guides utilisateurs FR/EN",
    labelEn: "Bilingual User Guide Authoring",
  },
];

const AVAILABLE_GATES: ReadonlyArray<{
  id: string;
  name: string;
  runner: "markdown_contract_runner" | "json_schema_runner" | "cli_sandbox_runner" | "catalog_invariant_runner";
}> = [
  {
    id: "det-prd-fields",
    name: "Vérification des rubriques du PRD & WSJF",
    runner: "markdown_contract_runner",
  },
  {
    id: "det-de-14-points",
    name: "Contrôle des 14 points du Dossier d'Étude",
    runner: "markdown_contract_runner",
  },
  {
    id: "det-invest-dor",
    name: "Conformité INVEST & critères d'acceptation",
    runner: "json_schema_runner",
  },
  {
    id: "det-validate-help-article",
    name: "Vérification de complétude documentaire FR/EN",
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
        ? "Utilisez le catalogue ci-dessous pour ajouter un outil, un savoir-faire métier ou un contrôle de qualité à ce processus."
        : "Use the catalog below to add a tool, a business skill, or a quality check to this process.",
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
          ? `Recommandation pour « ${trimmed} » : ajoutez d'abord une vérification automatique de complétude avant la relecture finale.`
          : `Recommendation for "${trimmed}": add an automated completeness check before the final review.`,
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
          {isFr ? "Catalogue de briques & Assistant" : "Process Building Blocks & Assistant"}
        </h3>
        <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {isFr
            ? "Ajoutez en 1 clic les outils, savoir-faire et contrôles qualité nécessaires."
            : "Add tools, business skills, and quality checks in 1 click."}
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
            <strong>{msg.sender === "copilot" ? "Conseil :" : "Vous :"}</strong> {msg.text}
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: "6px" }}>
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
          placeholder={
            isFr
              ? "Ex : Ajouter un contrôle de priorisation..."
              : "E.g., Add prioritization check..."
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
          {isFr ? "Demander" : "Ask"}
        </button>
      </div>

      {/* Outils connectés */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px" }}>
          {isFr ? "Outils connectés :" : "Connected Tools:"}
        </strong>
        {AVAILABLE_MCP_TOOLS.map((tool) => (
          <div
            key={tool.id}
            className="flex items-center justify-between gap-2 rounded border px-2.5 py-1.5 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <span style={{ fontSize: "12px" }}>{isFr ? tool.labelFr : tool.labelEn}</span>
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

      {/* Savoir-faire métier */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px" }}>
          {isFr ? "Savoir-faire métier :" : "Business Skills:"}
        </strong>
        {AVAILABLE_SKILLS.map((skill) => (
          <div
            key={skill.uri}
            className="flex items-center justify-between gap-2 rounded border px-2.5 py-1.5 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <span style={{ fontSize: "12px" }}>{isFr ? skill.labelFr : skill.labelEn}</span>
            <button
              type="button"
              data-testid={`copilot-add-skill-${skill.uri.split("/").pop() ?? "skill"}`}
              onClick={() => onAttachSkill(skill.uri)}
              className="orcia-ds-btn-secondary"
            >
              +
            </button>
          </div>
        ))}
      </div>

      {/* Contrôles automatiques de qualité */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <strong style={{ fontSize: "12px" }}>
          {isFr ? "Contrôles automatiques de qualité :" : "Automated Quality Checks:"}
        </strong>
        {AVAILABLE_GATES.map((gate) => (
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
