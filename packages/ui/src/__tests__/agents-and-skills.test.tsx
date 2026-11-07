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

    // Switch to Connections tab (hidden in DOM for backward compatibility)
    expect(screen.getByTestId("agents-subview-tab-connections").style.display).toBe("none");
    fireEvent.click(screen.getByTestId("agents-subview-tab-connections"));
    expect(screen.getByTestId("custom-connections-slot")).toBeDefined();
  });

  it("displays only 2 visible main tabs (🤖 Agents & 🛠️ Compétences), supports PRIVATE vs TEAM visibility selection, inline thinking level & visibility auto-save ('✓ Enregistré'), FormattedMarkdownContent rendering, and '💬 Utiliser dans Mon Assistant'", () => {
    const usedInAssistant: string[] = [];

    function RichStudioHarness() {
      const [skills, setSkills] = useState<UiManagedSkillItem[]>([
        {
          skillId: "skill-revue-architecture",
          slug: "revue-architecture",
          commandHandle: "/revue-architecture",
          name: "Revue d'Architecture",
          objective: "Vérifier la cohérence des choix d'architecture",
          inputParameters: ["dossier"],
          instructions: "Analyser les composants",
          expectedOutputFormat: "Synthèse Markdown",
          lastExecutionOutput: "### Verdict\n- **Conforme**",
          visibilityScope: "PACK",
          sourcePackKey: "orcia-pack-sdlc",
        },
      ]);
      const [agents, setAgents] = useState<UiManagedAgentItem[]>([]);

      return (
        <AgentsAndSkillsManagerView
          agents={agents}
          skills={skills}
          labels={TEST_LABELS}
          onCreateSkill={(draft) => {
            setSkills((prev) => [
              ...prev,
              {
                skillId: `skill-${prev.length + 1}`,
                slug: `skill-${prev.length + 1}`,
                commandHandle: `/skill-${prev.length + 1}`,
                name: draft.name,
                objective: draft.objective,
                inputParameters: draft.inputParameters,
                instructions: draft.instructions,
                expectedOutputFormat: draft.expectedOutputFormat,
                visibilityScope: draft.visibilityScope ?? "TEAM",
              },
            ]);
          }}
          onDeleteSkill={(id) => setSkills((prev) => prev.filter((s) => s.skillId !== id))}
          onExecuteSkill={() => undefined}
          onUpdateSkillVisibility={(skillId, nextScope) => {
            setSkills((prev) =>
              prev.map((s) =>
                s.skillId === skillId ? { ...s, visibilityScope: nextScope } : s,
              ),
            );
          }}
          onUseSkillInAssistant={(skill) => usedInAssistant.push(skill.commandHandle)}
          onCreateAgent={(draft) => {
            setAgents((prev) => [
              ...prev,
              {
                agentId: "agent-perso-1",
                slug: "perso-1",
                handle: "@perso-1",
                name: draft.name,
                roleMission: draft.roleMission,
                instructions: draft.instructions,
                thinkingLevel: draft.thinkingLevel,
                skillIds: draft.skillIds,
                visibilityScope: draft.visibilityScope ?? "TEAM",
                lastExecutionOutput: "### Analyse prête\n- **Point 1** : RAS",
              },
            ]);
          }}
          onToggleAgentSkill={(agentId, skillId, nextChecked) => {
            setAgents((prev) =>
              prev.map((a) =>
                a.agentId === agentId
                  ? {
                      ...a,
                      skillIds: nextChecked
                        ? [...a.skillIds, skillId]
                        : a.skillIds.filter((id) => id !== skillId),
                    }
                  : a,
              ),
            );
          }}
          onUpdateAgentThinkingLevel={(agentId, nextLvl) => {
            setAgents((prev) =>
              prev.map((a) =>
                a.agentId === agentId ? { ...a, thinkingLevel: nextLvl } : a,
              ),
            );
          }}
          onUpdateAgentVisibility={(agentId, nextScope) => {
            setAgents((prev) =>
              prev.map((a) =>
                a.agentId === agentId ? { ...a, visibilityScope: nextScope } : a,
              ),
            );
          }}
          onDeleteAgent={(id) => setAgents((prev) => prev.filter((a) => a.agentId !== id))}
          onExecuteAgent={() => undefined}
          onUseAgentInAssistant={(agent) => usedInAssistant.push(agent.handle)}
        />
      );
    }

    render(<RichStudioHarness />);

    // 1. Only 2 visible tabs (Connections tab has display: none)
    expect(screen.getByTestId("agents-subview-tab-agents").style.display).not.toBe("none");
    expect(screen.getByTestId("agents-subview-tab-skills").style.display).not.toBe("none");
    expect(screen.getByTestId("agents-subview-tab-connections").style.display).toBe("none");

    // 2. Create an Agent with PRIVATE visibility
    fireEvent.change(screen.getByTestId("agent-visibility-select"), {
      target: { value: "PRIVATE" },
    });
    fireEvent.change(screen.getByTestId("agent-name-input"), {
      target: { value: "Assistant Veille Personnelle" },
    });
    fireEvent.change(screen.getByTestId("agent-role-input"), {
      target: { value: "Synthétiser mes notes privées" },
    });
    fireEvent.change(screen.getByTestId("agent-instructions-input"), {
      target: { value: "Rester synthétique et structuré." },
    });
    fireEvent.click(screen.getByTestId("create-agent-submit-btn"));

    const badge = screen.getByTestId("agent-visibility-badge-agent-perso-1");
    expect(badge.textContent).toContain("🔒 Privé");

    // 3. Toggle visibility PRIVATE -> TEAM in 1 click and verify auto-save badge '✓ Enregistré'
    fireEvent.click(badge);
    expect(badge.textContent).toContain("👥 Équipe");
    expect(screen.getByTestId("agent-autosaved-badge-agent-perso-1").textContent).toContain(
      "✓ Enregistré",
    );

    // 4. Change thinking level inline and verify FormattedMarkdownContent is rendered
    fireEvent.change(screen.getByTestId("agent-card-thinking-select-agent-perso-1"), {
      target: { value: "complex" },
    });
    expect(
      screen
        .getByTestId("agent-execution-output-agent-perso-1")
        .querySelector('[data-testid="formatted-markdown-content"]'),
    ).not.toBeNull();

    // 5. Click '💬 Utiliser dans Mon Assistant' on Agent and Skill
    fireEvent.click(screen.getByTestId("use-agent-in-assistant-btn-agent-perso-1"));
    expect(usedInAssistant).toContain("@perso-1");

    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    expect(
      screen.getByTestId("skill-visibility-badge-skill-revue-architecture").textContent,
    ).toContain("📦 Pack Métier (orcia-pack-sdlc)");
    fireEvent.click(
      screen.getByTestId("use-skill-in-assistant-btn-skill-revue-architecture"),
    );
    expect(usedInAssistant).toContain("/revue-architecture");
  });
});
