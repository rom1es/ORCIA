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
  tabConnections: "🔌 Serveurs d'outils & MCP",
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

  it("displays 3 visible tabs, protects PACK agents from deletion while allowing 1-click duplication & workspace enable/disable, and supports PRIVATE vs TEAM visibility & '💬 Utiliser dans Mon Assistant'", () => {
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
      const [agents, setAgents] = useState<UiManagedAgentItem[]>([
        {
          agentId: "agent-pack-arch",
          slug: "pack-arch",
          handle: "@pack-arch",
          name: "Architecte Solution",
          roleMission: "Valider l'architecture",
          instructions: "Vérifier les patterns",
          thinkingLevel: "complex",
          skillIds: ["skill-revue-architecture"],
          visibilityScope: "PACK",
          sourcePackKey: "orcia-pack-sdlc",
          enabledOnWorkspace: true,
        },
      ]);

      return (
        <AgentsAndSkillsManagerView
          agents={agents}
          skills={skills}
          labels={TEST_LABELS}
          onCreateSkill={() => undefined}
          onDeleteSkill={(id) => setSkills((prev) => prev.filter((s) => s.skillId !== id))}
          onExecuteSkill={() => undefined}
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
          onDuplicateAgent={(src) => {
            setAgents((prev) => [
              ...prev,
              {
                ...src,
                agentId: `${src.agentId}-copy`,
                handle: `${src.handle}-copy`,
                name: `${src.name} (Copie)`,
                visibilityScope: "TEAM",
                sourcePackKey: null,
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
          onToggleAgentSkill={() => undefined}
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

    // 1. All 3 tabs are visible
    expect(screen.getByTestId("agents-subview-tab-agents").style.display).not.toBe("none");
    expect(screen.getByTestId("agents-subview-tab-skills").style.display).not.toBe("none");
    expect(screen.getByTestId("agents-subview-tab-connections").style.display).not.toBe("none");

    // 2. Pack agent has no Delete button, can be disabled/enabled on space, and duplicated into a TEAM agent
    expect(screen.queryByTestId("delete-agent-btn-agent-pack-arch")).toBeNull();
    fireEvent.click(screen.getByTestId("toggle-agent-enabled-btn-agent-pack-arch"));
    expect(screen.getByTestId("agent-disabled-badge-agent-pack-arch")).toBeDefined();
    fireEvent.click(screen.getByTestId("duplicate-agent-btn-agent-pack-arch"));
    expect(screen.getByTestId("agent-card-agent-pack-arch-copy")).toBeDefined();
    expect(screen.getByTestId("delete-agent-btn-agent-pack-arch-copy")).toBeDefined();

    // 3. Create an Agent with PRIVATE visibility via the modal
    fireEvent.click(screen.getByTestId("open-create-agent-drawer-btn"));
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

    // 4. Toggle visibility PRIVATE -> TEAM in 1 click and verify auto-save badge '✓ Enregistré'
    fireEvent.click(badge);
    expect(badge.textContent).toContain("👥 Équipe");
    expect(screen.getByTestId("agent-autosaved-badge-agent-perso-1").textContent).toContain(
      "✓ Enregistré",
    );

    // 5. Change thinking level inline and verify FormattedMarkdownContent is rendered
    fireEvent.change(screen.getByTestId("agent-card-thinking-select-agent-perso-1"), {
      target: { value: "complex" },
    });
    expect(
      screen
        .getByTestId("agent-execution-output-agent-perso-1")
        .querySelector('[data-testid="formatted-markdown-content"]'),
    ).not.toBeNull();

    // 6. Click '💬 Utiliser dans Mon Assistant' on Agent and Skill
    fireEvent.click(screen.getByTestId("use-agent-in-assistant-btn-agent-perso-1"));
    expect(usedInAssistant).toContain("@perso-1");

    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    expect(
      screen.getByTestId("skill-visibility-badge-skill-revue-architecture").textContent,
    ).toContain("📦 Pack Métier (orcia-pack-sdlc)");
    expect(screen.queryByTestId("delete-skill-btn-skill-revue-architecture")).toBeNull();
    fireEvent.click(
      screen.getByTestId("use-skill-in-assistant-btn-skill-revue-architecture"),
    );
    expect(usedInAssistant).toContain("/revue-architecture");
  });

  it("renders the 6 ORCIA Agent Governance Blocks (A..F), auto-sets temperature=0.0 on EVALUATOR_GATE posture, and displays the 6/6 Conversational Readiness checklist", () => {
    const submittedAgents: unknown[] = [];

    render(
      <AgentsAndSkillsManagerView
        agents={[]}
        skills={[]}
        labels={TEST_LABELS}
        onCreateSkill={() => undefined}
        onDeleteSkill={() => undefined}
        onExecuteSkill={() => undefined}
        onCreateAgent={(draft) => submittedAgents.push(draft)}
        onToggleAgentSkill={() => undefined}
        onDeleteAgent={() => undefined}
        onExecuteAgent={() => undefined}
      />,
    );

    fireEvent.click(screen.getByTestId("open-create-agent-drawer-btn"));
    expect(screen.getByTestId("create-agent-modal")).toBeDefined();

    // Verify all 6 blocks A..F and the 6 readiness conditions are rendered
    for (const blk of ["A", "B", "C", "D", "E", "F"] as const) {
      expect(screen.getByTestId(`create-agent-block-${blk}`)).toBeDefined();
    }
    for (const idx of [1, 2, 3, 4, 5, 6] as const) {
      expect(screen.getByTestId(`readiness-condition-${idx}`)).toBeDefined();
    }

    // Block A: Fill Identity, switch Posture to EVALUATOR_GATE -> auto-adjusts temperature to 0 & contract to gate_risk_json
    fireEvent.change(screen.getByTestId("agent-name-input"), {
      target: { value: "Auditeur Sécurité Gate" },
    });
    expect(screen.getByTestId("create-agent-handle-preview").textContent).toBe(
      "@auditeur-securite-gate",
    );
    fireEvent.change(screen.getByTestId("create-agent-posture-select"), {
      target: { value: "EVALUATOR_GATE" },
    });
    fireEvent.change(screen.getByTestId("create-agent-human-partner-select"), {
      target: { value: "SECURITY_QA" },
    });
    fireEvent.change(screen.getByTestId("agent-role-input"), {
      target: { value: "Chasser les angles morts de sécurité (Blind & Compliance Hunter)" },
    });

    // Block B: Verify temperature was auto-set to 0 and select deep model + 8192 tokens
    expect(
      (screen.getByTestId("create-agent-temperature-select") as HTMLSelectElement).value,
    ).toBe("0");
    fireEvent.change(screen.getByTestId("create-agent-llm-model-tier-select"), {
      target: { value: "deep" },
    });
    fireEvent.change(screen.getByTestId("create-agent-max-tokens-select"), {
      target: { value: "8192" },
    });

    // Block C: Fill instructions, prompt_ref, dialogue mechanism
    fireEvent.change(screen.getByTestId("agent-instructions-input"), {
      target: { value: "Contrôler systématiquement OWASP Top 10 et secrets." },
    });
    fireEvent.change(screen.getByTestId("create-agent-prompt-ref-input"), {
      target: { value: "git://sec-pack/prompts/compliance-hunter.md@main" },
    });
    fireEvent.change(screen.getByTestId("create-agent-dialogue-mechanism-select"), {
      target: { value: "direct" },
    });

    // Block D & E: Toggle RAG source, Ontology view & MCP tool permission
    fireEvent.click(screen.getByTestId("create-agent-rag-git_repositories"));
    fireEvent.click(screen.getByTestId("create-agent-ontology-securite_conformite"));
    fireEvent.change(screen.getByTestId("create-agent-mcp-tool-jira"), {
      target: { value: "WRITE_PREVIEW" },
    });

    // Readiness pill shows 6/6
    expect(screen.getByTestId("create-agent-readiness-pill").textContent).toContain("6/6");

    fireEvent.click(screen.getByTestId("create-agent-submit-btn"));
    expect(submittedAgents).toHaveLength(1);
    expect(submittedAgents[0]).toMatchObject({
      name: "Auditeur Sécurité Gate",
      posture: "EVALUATOR_GATE",
      humanPartnerRole: "SECURITY_QA",
      llmModelTier: "deep",
      temperature: 0,
      maxTokens: 8192,
      promptRef: "git://sec-pack/prompts/compliance-hunter.md@main",
      dialogueMechanism: "direct",
      outputContractFormat: "gate_risk_json",
      writePreviewRequired: true,
    });
  });
});
