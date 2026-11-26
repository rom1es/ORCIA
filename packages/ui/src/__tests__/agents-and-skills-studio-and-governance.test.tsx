import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import {
  AgentsAndSkillsManagerView,
  type UiManagedAgentItem,
  type UiManagedSkillItem,
} from "../index";
import { TEST_AGENTS_AND_SKILLS_LABELS as TEST_LABELS } from "./agentsAndSkillsLabelsFixture";

describe("AgentsAndSkillsManagerView Studio & Governance (@orcia/ui)", () => {
  afterEach(() => cleanup());

  it("displays 3 visible tabs, protects PACK agents from deletion while allowing duplication & enable/disable, and supports PRIVATE vs TEAM visibility & Assistant handoff", async () => {
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
                lifecycleStatus: "ACTIVE",
                testBenchStatus: "PASSED",
                testBenchValidated: true,
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

    // Singular KPI counts and human-readable model passport formatting
    const kpiStrip = screen.getByTestId("agents-kpi-strip");
    expect(kpiStrip.textContent).toContain("1 actif");
    expect(kpiStrip.textContent).toContain("1 réutilisable");
    const passport = screen.getByTestId("agent-governance-passport-agent-pack-arch");
    expect(passport.textContent).toContain("Par défaut · Précis · Contexte 4k");
    expect(passport.textContent).not.toContain("Temp ");
    expect(passport.textContent).not.toContain("4096 tok");
    expect(passport.textContent).not.toContain("team_default");

    // 1. All 3 tabs are visible
    expect(screen.getByTestId("agents-subview-tab-agents").style.display).not.toBe("none");
    expect(screen.getByTestId("agents-subview-tab-skills").style.display).not.toBe("none");
    expect(screen.getByTestId("agents-subview-tab-connections").style.display).not.toBe("none");

    // 2. Read-only PACK preset disables delete/enable/thinking controls and allows duplication into a TEAM copy
    expect(screen.queryByTestId("delete-agent-btn-agent-pack-arch")).toBeNull();
    expect(
      (screen.getByTestId("toggle-agent-enabled-btn-agent-pack-arch") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("agent-card-thinking-select-agent-pack-arch") as HTMLSelectElement)
        .disabled,
    ).toBe(true);
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
    expect(badge.querySelector('[data-orcia-icon="lock"] svg')).not.toBeNull();
    expect(badge.textContent).toContain("Privé");

    // 4. Toggle visibility PRIVATE -> TEAM in 1 click and verify auto-save badge
    fireEvent.click(badge);
    expect(badge.querySelector('[data-orcia-icon="team"] svg')).not.toBeNull();
    expect(badge.textContent).toContain("Équipe");
    expect(
      (await screen.findByTestId("agent-autosaved-badge-agent-perso-1")).textContent,
    ).toContain("Enregistré");

    // 5. Change thinking level inline and verify FormattedMarkdownContent is rendered
    fireEvent.change(screen.getByTestId("agent-card-thinking-select-agent-perso-1"), {
      target: { value: "complex" },
    });
    expect(
      screen
        .getByTestId("agent-execution-output-agent-perso-1")
        .querySelector('[data-testid="formatted-markdown-content"]'),
    ).not.toBeNull();

    // 6. Click Assistant handoff CTA on Agent and Skill
    fireEvent.click(screen.getByTestId("use-agent-in-assistant-btn-agent-perso-1"));
    expect(usedInAssistant).toContain("@perso-1");

    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    const skillBadge = screen.getByTestId("skill-visibility-badge-skill-revue-architecture");
    expect(skillBadge.querySelector("svg")).not.toBeNull();
    expect(skillBadge.textContent).toContain("Pack Métier (orcia-pack-sdlc)");
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

    for (const blk of ["A", "B", "C", "D", "E", "F"] as const) {
      expect(screen.getByTestId(`create-agent-block-${blk}`)).toBeDefined();
    }
    for (const idx of [1, 2, 3, 4, 5, 6] as const) {
      expect(screen.getByTestId(`readiness-condition-${idx}`)).toBeDefined();
    }

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

    expect(
      (screen.getByTestId("create-agent-temperature-select") as HTMLSelectElement).value,
    ).toBe("0");
    fireEvent.change(screen.getByTestId("create-agent-llm-model-tier-select"), {
      target: { value: "deep" },
    });
    fireEvent.change(screen.getByTestId("create-agent-max-tokens-select"), {
      target: { value: "8192" },
    });

    fireEvent.change(screen.getByTestId("agent-instructions-input"), {
      target: { value: "Contrôler systématiquement OWASP Top 10 et secrets." },
    });
    fireEvent.change(screen.getByTestId("create-agent-prompt-ref-input"), {
      target: { value: "git://sec-pack/prompts/compliance-hunter.md@main" },
    });
    fireEvent.change(screen.getByTestId("create-agent-dialogue-mechanism-select"), {
      target: { value: "direct" },
    });

    fireEvent.click(screen.getByTestId("create-agent-rag-git_repositories"));
    fireEvent.click(screen.getByTestId("create-agent-ontology-securite_conformite"));
    fireEvent.change(screen.getByTestId("create-agent-mcp-tool-jira"), {
      target: { value: "WRITE_PREVIEW" },
    });

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
