import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import {
  AgentsAndSkillsManagerView,
  type AgentsAndSkillsManagerLabels,
  type UiAgentThinkingLevel,
  type UiManagedAgentItem,
  type UiManagedSkillItem,
} from "../index";

const TEST_LABELS: AgentsAndSkillsManagerLabels = {
  heading: "🤖 Mes Agents & Compétences (Skills)",
  subtitle: "Créez vos compétences réutilisables et rattachez-les à vos agents.",
  tabAgents: "🤖 Mes Agents",
  tabSkills: "🛠️ Compétences (Skills)",
  tabConnections: "🔌 Connexions externes",
  emptyAgentsTitle: "Aucun agent configuré",
  emptyAgentsDescription: "Créez votre premier agent ci-dessus.",
  emptySkillsTitle: "Aucune compétence enregistrée",
  emptySkillsDescription: "Créez votre première compétence ci-dessus.",
  createAgentSectionTitle: "Créer un Agent spécialisé",
  agentNameLabel: "Nom de l'agent",
  agentNamePlaceholder: "Ex: Analyste Risques Fournisseurs",
  agentRoleLabel: "Rôle & mission métier",
  agentRolePlaceholder: "Ex: Évaluer la conformité",
  agentInstructionsLabel: "Instructions de travail",
  agentInstructionsPlaceholder: "Précisez la posture...",
  agentThinkingLevelLabel: "Niveau de réflexion par défaut",
  thinkingLevels: {
    simple: "⚡ Rapide",
    medium: "⚖️ Équilibré",
    complex: "🧠 Approfondi",
    auto: "✨ Automatique",
  },
  attachedSkillsLabel: "Compétences rattachées",
  noSkillsAvailableHint: "Aucune compétence disponible.",
  createAgentButtonLabel: "+ Enregistrer l'Agent",
  testAgentInputPlaceholder: "Demande concrète...",
  runAgentButtonLabel: "▶ Exécuter l'Agent",
  deleteAgentButtonLabel: "Supprimer",
  mobilizedSkillsLabel: "Compétences mobilisées",
  createSkillSectionTitle: "Créer une Compétence (Skill) réutilisable",
  skillUsageBanner: "Une compétence est modulaire.",
  skillNameLabel: "Nom de la compétence",
  skillNamePlaceholder: "Ex: Synthèse de conformité",
  skillObjectiveLabel: "Objectif métier",
  skillObjectivePlaceholder: "Ex: Vérifier les clauses...",
  skillParamsLabel: "Paramètres d'entrée attendus",
  skillParamsPlaceholder: "Ex: contrat, annexe",
  skillInstructionsLabel: "Méthode & instructions d'exécution",
  skillInstructionsPlaceholder: "Étapes de vérification...",
  skillOutputFormatLabel: "Format de résultat attendu",
  skillOutputFormatPlaceholder: "Ex: Tableau Go / No-Go",
  createSkillButtonLabel: "+ Enregistrer la Compétence",
  testSkillInputPlaceholder: "Cas de test...",
  runSkillButtonLabel: "▶ Tester la Compétence",
  deleteSkillButtonLabel: "Supprimer",
};

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
          },
        ]);
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

  it("starts with 0 agents and 0 skills, supports creating and executing a Skill, creating an Agent, attaching the Skill in 1 click, and executing the Agent", () => {
    render(<StatefulHarness />);

    expect(screen.getByTestId("agents-empty-state")).toBeDefined();

    // Switch to Skills tab
    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    expect(screen.getByTestId("skills-empty-state")).toBeDefined();

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

    // Verify Skill card appears & execute it in 1 click
    expect(screen.getByTestId("skill-card-skill-1")).toBeDefined();
    fireEvent.change(screen.getByTestId("skill-test-input-skill-1"), {
      target: { value: "Contrat Acme Cloud hébergé en UE" },
    });
    fireEvent.click(screen.getByTestId("run-skill-btn-skill-1"));
    expect(screen.getByTestId("skill-execution-output-skill-1").textContent).toContain(
      'Exécuté: Audit RGPD Fournisseur sur "Contrat Acme Cloud hébergé en UE"',
    );

    // Switch back to Agents tab
    fireEvent.click(screen.getByTestId("agents-subview-tab-agents"));

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

    // Verify Agent card appears with attached skill and execute it in 1 click
    expect(screen.getByTestId("agent-card-agent-1")).toBeDefined();
    fireEvent.change(screen.getByTestId("agent-test-input-agent-1"), {
      target: { value: "Analyse le contrat fournisseur BetaCorp" },
    });
    fireEvent.click(screen.getByTestId("run-agent-btn-agent-1"));
    expect(screen.getByTestId("agent-execution-output-agent-1").textContent).toContain(
      "Réponse Juriste Conformité IA [skills=skill-1] : Analyse le contrat fournisseur BetaCorp",
    );

    // Toggle skill off in 1 click on the existing agent card
    fireEvent.click(screen.getByTestId("agent-attach-skill-agent-1-skill-1"));
    fireEvent.click(screen.getByTestId("run-agent-btn-agent-1"));
    expect(screen.getByTestId("agent-execution-output-agent-1").textContent).toContain(
      "Réponse Juriste Conformité IA [skills=] : Analyse le contrat fournisseur BetaCorp",
    );

    // Switch to Connections tab
    fireEvent.click(screen.getByTestId("agents-subview-tab-connections"));
    expect(screen.getByTestId("custom-connections-slot")).toBeDefined();
  });
});
