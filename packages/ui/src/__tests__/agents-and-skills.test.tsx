import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import {
  AgentsAndSkillsManagerView,
  type UiAgentThinkingLevel,
  type UiManagedAgentItem,
  type UiManagedSkillItem,
} from "../index";
import { TEST_AGENTS_AND_SKILLS_LABELS as TEST_LABELS } from "./agentsAndSkillsLabelsFixture";

function StatefulHarness() {
  const [skills, setSkills] = useState<UiManagedSkillItem[]>([]);
  const [agents, setAgents] = useState<UiManagedAgentItem[]>([]);

  return (
    <AgentsAndSkillsManagerView
      agents={agents}
      skills={skills}
      labels={TEST_LABELS}
      onCreateSkill={(draft) => {
        const skillId = `skill-${skills.length + 1}`;
        setSkills((prev) => [
          ...prev,
          {
            skillId,
            slug: `skill-${skills.length + 1}`,
            commandHandle: `/skill-${skills.length + 1}`,
            name: draft.name,
            objective: draft.objective,
            inputParameters: draft.inputParameters,
            instructions: draft.instructions,
            expectedOutputFormat: draft.expectedOutputFormat,
            lastExecutionOutput: null,
            visibilityScope: draft.visibilityScope ?? "TEAM",
          },
        ]);
      }}
      onDeleteSkill={(skillId) => {
        setSkills((prev) => prev.filter((s) => s.skillId !== skillId));
        setAgents((prev) =>
          prev.map((a) => ({
            ...a,
            skillIds: a.skillIds.filter((id) => id !== skillId),
          })),
        );
      }}
      onExecuteSkill={(skillId, inputText) => {
        setSkills((prev) =>
          prev.map((s) =>
            s.skillId === skillId
              ? { ...s, lastExecutionOutput: `Exécuté: ${s.name} sur "${inputText}"` }
              : s,
          ),
        );
      }}
      onCreateAgent={(draft) => {
        const agentId = `agent-${agents.length + 1}`;
        setAgents((prev) => [
          ...prev,
          {
            agentId,
            slug: `agent-${agents.length + 1}`,
            handle: `@agent-${agents.length + 1}`,
            name: draft.name,
            roleMission: draft.roleMission,
            instructions: draft.instructions,
            thinkingLevel: draft.thinkingLevel as UiAgentThinkingLevel,
            skillIds: draft.skillIds,
            lastExecutionOutput: null,
            visibilityScope: draft.visibilityScope ?? "TEAM",
          },
        ]);
      }}
      onDuplicateAgent={(sourceAgent) => {
        setAgents((prev) => [
          ...prev,
          {
            ...sourceAgent,
            agentId: `${sourceAgent.agentId}-copy`,
            slug: `${sourceAgent.slug}-copy`,
            handle: `${sourceAgent.handle}-copy`,
            name: `${sourceAgent.name} (Copie)`,
            visibilityScope: "TEAM",
            sourcePackKey: null,
            enabledOnWorkspace: true,
          },
        ]);
      }}
      onToggleAgentEnabled={(agentId, nextEnabled) => {
        setAgents((prev) =>
          prev.map((a) =>
            a.agentId === agentId ? { ...a, enabledOnWorkspace: nextEnabled } : a,
          ),
        );
      }}
      onToggleAgentSkill={(agentId, skillId, nextChecked) => {
        setAgents((prev) =>
          prev.map((a) => {
            if (a.agentId !== agentId) return a;
            const without = a.skillIds.filter((id) => id !== skillId);
            return {
              ...a,
              skillIds: nextChecked ? [...without, skillId] : without,
            };
          }),
        );
      }}
      onDeleteAgent={(agentId) => {
        setAgents((prev) => prev.filter((a) => a.agentId !== agentId));
      }}
      onExecuteAgent={(agentId, prompt) => {
        setAgents((prev) =>
          prev.map((a) =>
            a.agentId === agentId
              ? {
                  ...a,
                  lastExecutionOutput: `Réponse ${a.name} [skills=${a.skillIds.join(",")}] : ${prompt}`,
                }
              : a,
          ),
        );
      }}
      connectionsContent={<div data-testid="custom-connections-slot">Connexions MCP</div>}
    />
  );
}

describe("AgentsAndSkillsManagerView (@orcia/ui)", () => {
  afterEach(() => {
    cleanup();
  });

  it("starts with 0 agents and 0 skills (KPI strip hidden, creation modals closed), opens modals on CTA click, and runs Dry-Run tests inside the Configuration & Sandbox modal", () => {
    render(<StatefulHarness />);

    expect(screen.getByTestId("agents-empty-state")).toBeDefined();
    expect(screen.getByTestId("workspace-assistant-pinned-card")).toBeDefined();
    expect(screen.queryByTestId("agents-kpi-strip")).toBeNull();
    expect(screen.queryByTestId("create-agent-modal")).toBeNull();

    // Switch to Skills tab
    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    expect(screen.getByTestId("skills-empty-state")).toBeDefined();
    expect(screen.queryByTestId("create-skill-modal")).toBeNull();

    // Open Create Skill Modal
    fireEvent.click(screen.getByTestId("open-create-skill-drawer-btn"));
    expect(screen.getByTestId("create-skill-modal")).toBeDefined();

    // Create a Skill
    fireEvent.change(screen.getByTestId("skill-name-input"), {
      target: { value: "Audit RGPD Fournisseur" },
    });
    fireEvent.change(screen.getByTestId("skill-objective-input"), {
      target: { value: "Vérifier les clauses de sous-traitance RGPD" },
    });
    fireEvent.change(screen.getByTestId("skill-params-input"), {
      target: { value: "contrat, dpa" },
    });
    fireEvent.change(screen.getByTestId("skill-output-format-input"), {
      target: { value: "Liste des écarts + verdict" },
    });
    fireEvent.change(screen.getByTestId("skill-instructions-input"), {
      target: { value: "Contrôler l'article 28 et la localisation des serveurs." },
    });
    fireEvent.click(screen.getByTestId("create-skill-submit-btn"));

    // Modal closes automatically on submit and KPI strip is now visible
    expect(screen.queryByTestId("create-skill-modal")).toBeNull();
    expect(screen.getByTestId("agents-kpi-strip")).toBeDefined();

    // Verify Skill card appears & open Skill detail/sandbox modal to execute it
    expect(screen.getByTestId("skill-card-skill-1")).toBeDefined();
    fireEvent.click(screen.getByTestId("open-skill-detail-modal-btn-skill-1"));
    expect(screen.getByTestId("skill-detail-modal-skill-1")).toBeDefined();

    fireEvent.change(screen.getByTestId("skill-test-input-skill-1"), {
      target: { value: "Contrat Acme Cloud hébergé en UE" },
    });
    fireEvent.click(screen.getByTestId("run-skill-btn-skill-1"));
    expect(screen.getAllByTestId("skill-execution-output-skill-1")[0]?.textContent).toContain(
      'Exécuté: Audit RGPD Fournisseur sur "Contrat Acme Cloud hébergé en UE"',
    );
    fireEvent.click(screen.getByTestId("close-skill-detail-modal-btn-skill-1"));

    // Switch back to Agents tab & open Create Agent Modal
    fireEvent.click(screen.getByTestId("agents-subview-tab-agents"));
    fireEvent.click(screen.getByTestId("open-create-agent-drawer-btn"));
    expect(screen.getByTestId("create-agent-modal")).toBeDefined();

    // Create an Agent and select the skill during creation
    fireEvent.change(screen.getByTestId("agent-name-input"), {
      target: { value: "Juriste Conformité IA" },
    });
    fireEvent.change(screen.getByTestId("agent-role-input"), {
      target: { value: "Valider les contrats fournisseurs" },
    });
    fireEvent.change(screen.getByTestId("agent-thinking-level-select"), {
      target: { value: "complex" },
    });
    fireEvent.change(screen.getByTestId("agent-instructions-input"), {
      target: { value: "Vérifier systématiquement les engagements de sécurité." },
    });
    fireEvent.click(screen.getByTestId("create-agent-skill-checkbox-skill-1"));
    fireEvent.click(screen.getByTestId("create-agent-submit-btn"));

    // Modal closes automatically
    expect(screen.queryByTestId("create-agent-modal")).toBeNull();
    expect(screen.getByTestId("agent-card-agent-1")).toBeDefined();

    // Open Agent Detail & Dry-Run Sandbox Modal
    fireEvent.click(screen.getByTestId("open-agent-detail-modal-btn-agent-1"));
    expect(screen.getByTestId("agent-detail-modal-agent-1")).toBeDefined();

    fireEvent.change(screen.getByTestId("agent-test-input-agent-1"), {
      target: { value: "Analyse le contrat fournisseur BetaCorp" },
    });
    fireEvent.click(screen.getByTestId("run-agent-btn-agent-1"));
    expect(screen.getAllByTestId("agent-execution-output-agent-1")[0]?.textContent).toContain(
      "Réponse Juriste Conformité IA [skills=skill-1] : Analyse le contrat fournisseur BetaCorp",
    );

    // Toggle skill off in 1 click inside the detail modal
    fireEvent.click(screen.getByTestId("agent-attach-skill-agent-1-skill-1"));
    fireEvent.click(screen.getByTestId("run-agent-btn-agent-1"));
    expect(screen.getAllByTestId("agent-execution-output-agent-1")[0]?.textContent).toContain(
      "Réponse Juriste Conformité IA [skills=] : Analyse le contrat fournisseur BetaCorp",
    );
    fireEvent.click(screen.getByTestId("close-agent-detail-modal-btn-agent-1"));

    // Switch to visible 3rd Connections tab
    expect(screen.getByTestId("agents-subview-tab-connections").style.display).not.toBe("none");
    fireEvent.click(screen.getByTestId("agents-subview-tab-connections"));
    expect(screen.getByTestId("custom-connections-slot")).toBeDefined();
  });
});
