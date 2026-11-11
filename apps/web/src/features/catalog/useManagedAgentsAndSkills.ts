import { createOrciaApiClient } from "@orcia/api-client";
import type {
  AgentSixBlocksDraftState,
  CreateAgentSixBlocksInput,
  UiAgentDialogueMechanism,
  UiAgentHumanPartnerRole,
  UiAgentLlmModelTier,
  UiAgentOutputContractFormat,
  UiAgentPosture,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "@orcia/ui";
import { useEffect, useState } from "react";
import type { ConfiguredPackItem } from "../../components/platformSetupStore";
import {
  type CachedAgentsAndSkillsState,
  mergeManagedStateWithActivePacks,
  PACK_AGENTS_BY_PACK_KEY,
  PACK_SKILLS_BY_PACK_KEY,
  readCachedAgentsAndSkills,
  slugifyIdentifier,
  writeCachedAgentsAndSkills,
} from "./packAgentsCatalog";

function buildSkillLocalOutput(skill: UiManagedSkillItem, inputText: string): string {
  return [
    `### ⏳ Exécution de la compétence **${skill.name}** (\`${skill.commandHandle}\`)`,
    `- **Objectif** : ${skill.objective}`,
    `- **Entrée analysée** : ${inputText.trim()}`,
    `- **Méthode appliquée** : ${skill.instructions}`,
    `- **Livrable (${skill.expectedOutputFormat})** : Analyse structurée prête pour validation métier.`,
  ].join("\n");
}

function buildAgentLocalOutput(
  agent: UiManagedAgentItem,
  allSkills: readonly UiManagedSkillItem[],
  prompt: string,
): string {
  const attached = allSkills.filter((s) => agent.skillIds.includes(s.skillId));
  const skillsLine =
    attached.length > 0
      ? `- **Compétences mobilisées (${attached.length})** : ${attached.map((s) => `${s.name} (\`${s.commandHandle}\`)`).join(", ")}`
      : "- **Compétences mobilisées** : Aucune compétence rattachée (exécution directe)";
  return [
    `### ⏳ Agent **${agent.name}** (${agent.roleMission}) — Réflexion : \`${agent.thinkingLevel}\``,
    `- **Posture** : ${agent.posture ?? "PRODUCER"} · **Binôme** : ${agent.humanPartnerRole ?? "PO_PM"} · **Contrat** : ${agent.outputContractFormat ?? "markdown_structure"}`,
    `- **Demande traitée** : ${prompt.trim()}`,
    `- **Posture & instructions** : ${agent.instructions}`,
    skillsLine,
    "- **Synthèse de l'Agent** : Préparation de la réponse avec citations vérifiables [S1]...",
  ].join("\n");
}

export function useManagedAgentsAndSkills(
  activePacks: readonly ConfiguredPackItem[],
  onFeedback: (msg: string) => void,
) {
  const [managedState, setManagedState] = useState<CachedAgentsAndSkillsState>(() =>
    readCachedAgentsAndSkills(),
  );

  const updateManagedState = (
    updater: (prev: CachedAgentsAndSkillsState) => CachedAgentsAndSkillsState,
  ) => {
    setManagedState((prev) => {
      const next = updater(prev);
      writeCachedAgentsAndSkills(next);
      return next;
    });
  };

  useEffect(() => {
    let cancelled = false;
    createOrciaApiClient({ baseUrl: "" })
      .listAgentsAndSkills()
      .then((res) => {
        if (cancelled) return;
        const mappedSkills: UiManagedSkillItem[] = (res.skills ?? []).map((s) => ({
          skillId: s.skill_id,
          slug: s.slug,
          commandHandle: s.command_handle,
          name: s.name,
          objective: s.objective,
          inputParameters: s.input_parameters ?? [],
          instructions: s.instructions,
          expectedOutputFormat: s.expected_output_format ?? "Synthèse structurée",
          lastExecutionOutput: null,
          visibilityScope: (s.visibility_scope ?? "TEAM") as UiAgentSkillVisibilityScope,
          sourcePackKey: s.source_pack_key ?? null,
        }));
        const mappedAgents: UiManagedAgentItem[] = (res.agents ?? []).map((a) => ({
          agentId: a.agent_id,
          slug: a.slug,
          handle: a.handle,
          name: a.name,
          roleMission: a.role_mission,
          instructions: a.instructions,
          thinkingLevel: (a.thinking_level ?? "medium") as UiAgentThinkingLevel,
          skillIds: a.skill_ids ?? [],
          lastExecutionOutput: null,
          visibilityScope: (a.visibility_scope ?? "TEAM") as UiAgentSkillVisibilityScope,
          sourcePackKey: a.source_pack_key ?? null,
          enabledOnWorkspace: a.enabled_in_workspace ?? true,
          mcpExposed: a.mcp_exposed ?? false,
          posture: (a.posture ?? "PRODUCER") as UiAgentPosture,
          humanPartnerRole: (a.human_partner_role ?? "PO_PM") as UiAgentHumanPartnerRole,
          llmModelTier: (a.llm_model_tier ?? "team_default") as UiAgentLlmModelTier,
          temperature: a.temperature ?? 0.2,
          maxTokens: a.max_tokens ?? 4096,
          promptRef: a.prompt_ref ?? null,
          invocationModes: a.invocation_modes ?? ["generer", "corrections", "section"],
          dialogueMechanism: (a.dialogue_mechanism ??
            "questionnaire_prealable") as UiAgentDialogueMechanism,
          allowedRagSources: a.allowed_rag_sources ?? ["all_workspace_sources"],
          ontologyViews: a.ontology_views ?? ["glossary", "apis_adr", "prd_regles_metier"],
          mcpToolPermissions: a.mcp_tool_permissions ?? {
            search_tool: "READ_ONLY",
            confluence: "WRITE_PREVIEW",
            jira: "WRITE_PREVIEW",
            git: "READ_ONLY",
          },
          guardrails: a.guardrails ?? [
            "citations_obligatoires",
            "aucun_fait_invente",
            "isolation_prompt_injection",
            "filtrage_dcp_pii",
          ],
          outputContractFormat: (a.output_contract_format ??
            "markdown_structure") as UiAgentOutputContractFormat,
          writePreviewRequired: a.write_preview_required ?? true,
          testBenchValidated: a.test_bench_validated ?? false,
        }));
        if (mappedAgents.length === 0 && mappedSkills.length === 0) {
          const cached = readCachedAgentsAndSkills();
          if (cached.agents.length > 0 || cached.skills.length > 0) return;
        }
        const nextState = { agents: mappedAgents, skills: mappedSkills };
        writeCachedAgentsAndSkills(nextState);
        setManagedState(nextState);
      })
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Chargement hors ligne (${err instanceof Error ? err.message : "cache local actif"}).`,
        ),
      );
    return () => {
      cancelled = true;
    };
  }, [onFeedback]);

  const combinedState = mergeManagedStateWithActivePacks(managedState, activePacks);
  const resolveAgents = (prev: CachedAgentsAndSkillsState): readonly UiManagedAgentItem[] =>
    prev.agents.length > 0
      ? prev.agents
      : mergeManagedStateWithActivePacks(prev, activePacks).agents;

  const handleLoadPackTemplates = () => {
    const defaultPacks: readonly ConfiguredPackItem[] = [
      { packKey: "orcia-pack-sdlc", version: "1.0.0", scopePath: "GLOBAL", status: "PUBLISHED" },
      { packKey: "orcia-pack-builder", version: "1.0.0", scopePath: "GLOBAL", status: "PUBLISHED" },
    ];
    updateManagedState((prev) => mergeManagedStateWithActivePacks(prev, defaultPacks));
    onFeedback("✅ Agents et compétences des Packs Métiers chargés dans votre atelier.");
  };

  const handleCreateSkill = (draft: {
    name: string;
    objective: string;
    inputParameters: string[];
    instructions: string;
    expectedOutputFormat: string;
    visibilityScope?: "PRIVATE" | "TEAM";
  }) => {
    const slug = slugifyIdentifier(draft.name, "competence");
    const skillId = slug.startsWith("skill-") ? slug : `skill-${slug}`;
    const slashSlug = slug.startsWith("skill-") ? slug.slice(6) || slug : slug;
    const optimisticSkill: UiManagedSkillItem = {
      skillId,
      slug: slashSlug,
      commandHandle: `/${slashSlug}`,
      name: draft.name.trim(),
      objective: draft.objective.trim(),
      inputParameters: draft.inputParameters,
      instructions: draft.instructions.trim(),
      expectedOutputFormat: draft.expectedOutputFormat.trim() || "Synthèse structurée",
      lastExecutionOutput: null,
      visibilityScope: draft.visibilityScope ?? "TEAM",
    };
    updateManagedState((prev) => ({
      ...prev,
      skills: [...prev.skills.filter((s) => s.skillId !== skillId), optimisticSkill],
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .upsertSkill({
        skill_id: skillId,
        name: optimisticSkill.name,
        objective: optimisticSkill.objective,
        input_parameters: [...optimisticSkill.inputParameters],
        instructions: optimisticSkill.instructions,
        expected_output_format: optimisticSkill.expectedOutputFormat,
        visibility_scope: optimisticSkill.visibilityScope,
      })
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Synchronisation compétence différée (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleDeleteSkill = (skillId: string) => {
    updateManagedState((prev) => ({
      skills: prev.skills.filter((s) => s.skillId !== skillId),
      agents: prev.agents.map((a) => ({
        ...a,
        skillIds: a.skillIds.filter((id) => id !== skillId),
      })),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .deleteSkill(skillId)
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Suppression différée (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleUpdateSkillVisibility = (
    skillId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => {
    updateManagedState((prev) => {
      const baseList = prev.skills.some((s) => s.skillId === skillId)
        ? prev.skills
        : mergeManagedStateWithActivePacks(prev, activePacks).skills;
      return {
        ...prev,
        skills: baseList.map((s) =>
          s.skillId === skillId ? { ...s, visibilityScope: nextVisibility } : s,
        ),
      };
    });
  };

  const handleExecuteSkill = (skillId: string, inputText: string) => {
    updateManagedState((prev) => {
      const baseSkills = prev.skills.some((s) => s.skillId === skillId)
        ? prev.skills
        : [
            ...prev.skills,
            ...Object.values(PACK_SKILLS_BY_PACK_KEY)
              .flat()
              .filter((s) => s.skillId === skillId),
          ];
      return {
        ...prev,
        skills: baseSkills.map((skill) =>
          skill.skillId === skillId
            ? { ...skill, lastExecutionOutput: buildSkillLocalOutput(skill, inputText) }
            : skill,
        ),
      };
    });
    void createOrciaApiClient({ baseUrl: "" })
      .executeSkill(skillId, { input_text: inputText })
      .then((res) =>
        updateManagedState((prev) => ({
          ...prev,
          skills: prev.skills.map((s) =>
            s.skillId === skillId ? { ...s, lastExecutionOutput: res.output_text } : s,
          ),
        })),
      )
      .catch((err: unknown) => {
        const detail = err instanceof Error ? err.message : "erreur serveur";
        updateManagedState((prev) => ({
          ...prev,
          skills: prev.skills.map((s) =>
            s.skillId === skillId
              ? {
                  ...s,
                  lastExecutionOutput: `${s.lastExecutionOutput ?? ""}\n⚠️ Remarque : exécution locale utilisée (${detail}).`,
                }
              : s,
          ),
        }));
      });
  };

  const handleCreateAgent = (draft: CreateAgentSixBlocksInput) => {
    const slug = slugifyIdentifier(draft.name, "agent");
    const agentId = slug.startsWith("agent-") ? slug : `agent-${slug}`;
    const handleSlug = slug.startsWith("agent-") ? slug.slice(6) || slug : slug;
    const optimisticAgent: UiManagedAgentItem = {
      agentId,
      slug: handleSlug,
      handle: `@${handleSlug}`,
      name: draft.name.trim(),
      roleMission: draft.roleMission.trim(),
      instructions: draft.instructions.trim(),
      thinkingLevel: draft.thinkingLevel,
      skillIds: [...draft.skillIds],
      lastExecutionOutput: null,
      visibilityScope: draft.visibilityScope ?? "TEAM",
      enabledOnWorkspace: true,
      mcpExposed: false,
      posture: draft.posture ?? "PRODUCER",
      humanPartnerRole: draft.humanPartnerRole ?? "PO_PM",
      llmModelTier: draft.llmModelTier ?? "team_default",
      temperature: draft.temperature ?? 0.2,
      maxTokens: draft.maxTokens ?? 4096,
      promptRef: draft.promptRef ?? null,
      invocationModes: draft.invocationModes ?? ["generer", "corrections", "section"],
      dialogueMechanism: draft.dialogueMechanism ?? "questionnaire_prealable",
      allowedRagSources: draft.allowedRagSources ?? ["all_workspace_sources"],
      ontologyViews: draft.ontologyViews ?? ["glossary", "apis_adr", "prd_regles_metier"],
      mcpToolPermissions: draft.mcpToolPermissions ?? {
        search_tool: "READ_ONLY",
        confluence: "WRITE_PREVIEW",
        jira: "WRITE_PREVIEW",
        git: "READ_ONLY",
      },
      guardrails: draft.guardrails ?? [
        "citations_obligatoires",
        "aucun_fait_invente",
        "isolation_prompt_injection",
        "filtrage_dcp_pii",
      ],
      outputContractFormat: draft.outputContractFormat ?? "markdown_structure",
      writePreviewRequired: draft.writePreviewRequired ?? true,
      testBenchValidated: false,
    };
    updateManagedState((prev) => ({
      ...prev,
      agents: [...prev.agents.filter((a) => a.agentId !== agentId), optimisticAgent],
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .upsertAgent({
        agent_id: agentId,
        name: optimisticAgent.name,
        role_mission: optimisticAgent.roleMission,
        instructions: optimisticAgent.instructions,
        thinking_level: optimisticAgent.thinkingLevel,
        skill_ids: [...optimisticAgent.skillIds],
        visibility_scope: optimisticAgent.visibilityScope,
        posture: optimisticAgent.posture,
        human_partner_role: optimisticAgent.humanPartnerRole,
        llm_model_tier: optimisticAgent.llmModelTier,
        temperature: optimisticAgent.temperature,
        max_tokens: optimisticAgent.maxTokens,
        prompt_ref: optimisticAgent.promptRef ?? undefined,
        invocation_modes: [...(optimisticAgent.invocationModes ?? [])],
        dialogue_mechanism: optimisticAgent.dialogueMechanism,
        allowed_rag_sources: [...(optimisticAgent.allowedRagSources ?? [])],
        ontology_views: [...(optimisticAgent.ontologyViews ?? [])],
        mcp_tool_permissions: { ...(optimisticAgent.mcpToolPermissions ?? {}) },
        guardrails: [...(optimisticAgent.guardrails ?? [])],
        output_contract_format: optimisticAgent.outputContractFormat,
        write_preview_required: optimisticAgent.writePreviewRequired,
        test_bench_validated: optimisticAgent.testBenchValidated,
      })
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Synchronisation agent différée (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleDuplicateAgent = (sourceAgent: UiManagedAgentItem) => {
    const customName = `${sourceAgent.name} (Copie)`;
    const slug = slugifyIdentifier(customName, "agent-copie");
    const agentId = slug.startsWith("agent-") ? slug : `agent-${slug}`;
    const handleSlug = slug.startsWith("agent-") ? slug.slice(6) || slug : slug;
    const duplicated: UiManagedAgentItem = {
      ...sourceAgent,
      agentId,
      slug: handleSlug,
      handle: `@${handleSlug}`,
      name: customName,
      visibilityScope: "TEAM",
      sourcePackKey: null,
      enabledOnWorkspace: true,
    };
    updateManagedState((prev) => ({
      ...prev,
      agents: [...resolveAgents(prev).filter((a) => a.agentId !== agentId), duplicated],
    }));
    onFeedback(`✅ Agent « ${duplicated.name} » dupliqué et prêt à être personnalisé.`);
    void createOrciaApiClient({ baseUrl: "" })
      .duplicateAgent(sourceAgent.agentId, { new_name: customName, visibility_scope: "TEAM" })
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Duplication synchronisée localement (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleToggleAgentEnabled = (agentId: string, nextEnabled: boolean) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) =>
        a.agentId === agentId ? { ...a, enabledOnWorkspace: nextEnabled } : a,
      ),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .updateAgentGovernance(agentId, { enabled_in_workspace: nextEnabled })
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ État d'activation enregistré localement (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleToggleAgentMcpExposure = (agentId: string, nextExposed: boolean) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) =>
        a.agentId === agentId ? { ...a, mcpExposed: nextExposed } : a,
      ),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .updateAgentGovernance(agentId, { mcp_exposed: nextExposed })
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Exposition MCP enregistrée localement (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleUpdateAgentDetails = (
    agentId: string,
    patch: Partial<AgentSixBlocksDraftState> & {
      name: string;
      roleMission: string;
      instructions: string;
      thinkingLevel: UiAgentThinkingLevel;
      visibilityScope?: UiAgentSkillVisibilityScope;
      mcpExposed?: boolean;
    },
  ) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) => (a.agentId === agentId ? { ...a, ...patch } : a)),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .upsertAgent({
        agent_id: agentId,
        name: patch.name,
        role_mission: patch.roleMission,
        instructions: patch.instructions,
        thinking_level: patch.thinkingLevel,
        skill_ids: patch.skillIds ? [...patch.skillIds] : [],
        visibility_scope: patch.visibilityScope,
        mcp_exposed: patch.mcpExposed,
        posture: patch.posture,
        human_partner_role: patch.humanPartnerRole,
        llm_model_tier: patch.llmModelTier,
        temperature: patch.temperature,
        max_tokens: patch.maxTokens,
        prompt_ref: patch.promptRef || undefined,
        invocation_modes: patch.invocationModes ? [...patch.invocationModes] : undefined,
        dialogue_mechanism: patch.dialogueMechanism,
        allowed_rag_sources: patch.allowedRagSources ? [...patch.allowedRagSources] : undefined,
        ontology_views: patch.ontologyViews ? [...patch.ontologyViews] : undefined,
        mcp_tool_permissions: patch.mcpToolPermissions
          ? { ...patch.mcpToolPermissions }
          : undefined,
        guardrails: patch.guardrails ? [...patch.guardrails] : undefined,
        output_contract_format: patch.outputContractFormat,
        write_preview_required: patch.writePreviewRequired,
        test_bench_validated: patch.testBenchValidated,
      })
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Mise à jour d'agent différée (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleToggleAgentSkill = (agentId: string, skillId: string, nextChecked: boolean) => {
    let nextSkillIdsForApi: string[] = [];
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((agent) => {
        if (agent.agentId !== agentId) return agent;
        const without = agent.skillIds.filter((id) => id !== skillId);
        const updatedIds = nextChecked ? [...without, skillId] : without;
        nextSkillIdsForApi = updatedIds;
        return { ...agent, skillIds: updatedIds };
      }),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .updateAgentSkills(agentId, { skill_ids: nextSkillIdsForApi })
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Rattachement compétence différé (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleUpdateAgentThinkingLevel = (
    agentId: string,
    nextThinkingLevel: UiAgentThinkingLevel,
  ) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) =>
        a.agentId === agentId ? { ...a, thinkingLevel: nextThinkingLevel } : a,
      ),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .updateAgentGovernance(agentId, { thinking_level: nextThinkingLevel })
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Palier de réflexion enregistré localement (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleUpdateAgentVisibility = (
    agentId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) =>
        a.agentId === agentId ? { ...a, visibilityScope: nextVisibility } : a,
      ),
    }));
    if (nextVisibility === "PRIVATE" || nextVisibility === "TEAM") {
      void createOrciaApiClient({ baseUrl: "" })
        .updateAgentGovernance(agentId, { visibility_scope: nextVisibility })
        .catch((err: unknown) =>
          onFeedback(
            `⚠️ Visibilité enregistrée localement (${err instanceof Error ? err.message : "hors ligne"}).`,
          ),
        );
    }
  };

  const handleDeleteAgent = (agentId: string) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: prev.agents.filter((a) => a.agentId !== agentId),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .deleteAgent(agentId)
      .catch((err: unknown) =>
        onFeedback(
          `⚠️ Suppression différée (${err instanceof Error ? err.message : "hors ligne"}).`,
        ),
      );
  };

  const handleExecuteAgent = (agentId: string, prompt: string) => {
    updateManagedState((prev) => {
      const baseAgents = prev.agents.some((a) => a.agentId === agentId)
        ? prev.agents
        : [
            ...prev.agents,
            ...Object.values(PACK_AGENTS_BY_PACK_KEY)
              .flat()
              .filter((a) => a.agentId === agentId),
          ];
      const allSkills = [
        ...prev.skills,
        ...Object.values(PACK_SKILLS_BY_PACK_KEY)
          .flat()
          .filter((sk) => !prev.skills.some((ps) => ps.skillId === sk.skillId)),
      ];
      return {
        ...prev,
        agents: baseAgents.map((agent) =>
          agent.agentId === agentId
            ? {
                ...agent,
                testBenchValidated: true,
                lastExecutionOutput: buildAgentLocalOutput(agent, allSkills, prompt),
              }
            : agent,
        ),
      };
    });
    void createOrciaApiClient({ baseUrl: "" })
      .executeAgent(agentId, { prompt })
      .then((res) =>
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) =>
            a.agentId === agentId
              ? {
                  ...a,
                  testBenchValidated: true,
                  lastExecutionOutput: res.response_text,
                  lastInvokedSkills: (res.invoked_skills ?? []).map(
                    (s) => `${s.skill_name} (${s.command_handle})`,
                  ),
                }
              : a,
          ),
        })),
      )
      .catch((err: unknown) => {
        const detail = err instanceof Error ? err.message : "erreur serveur";
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) =>
            a.agentId === agentId
              ? {
                  ...a,
                  testBenchValidated: true,
                  lastExecutionOutput: `${a.lastExecutionOutput ?? ""}\n⚠️ Remarque : exécution locale utilisée (${detail}).`,
                }
              : a,
          ),
        }));
      });
  };

  return {
    agents: combinedState.agents,
    skills: combinedState.skills,
    handleLoadPackTemplates,
    handleCreateSkill,
    handleDeleteSkill,
    handleUpdateSkillVisibility,
    handleExecuteSkill,
    handleCreateAgent,
    handleDuplicateAgent,
    handleToggleAgentEnabled,
    handleToggleAgentMcpExposure,
    handleUpdateAgentDetails,
    handleToggleAgentSkill,
    handleUpdateAgentThinkingLevel,
    handleUpdateAgentVisibility,
    handleDeleteAgent,
    handleExecuteAgent,
  };
}
