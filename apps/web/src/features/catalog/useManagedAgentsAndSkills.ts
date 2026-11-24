import { createOrciaApiClient } from "@orcia/api-client";
import type { UiAgentSkillVisibilityScope, UiManagedSkillItem } from "@orcia/ui";
import { useEffect, useState } from "react";
import type { ConfiguredPackItem } from "../../components/platformSetupStore";
import type { SupportedWebLocale } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import {
  buildSkillLocalOutput,
  type CatalogManagedLabels,
  mapAgentDtoToUi,
  mapSkillDtoToUi,
} from "./managedAgentsHelpers";
import {
  type CachedAgentsAndSkillsState,
  mergeManagedStateWithActivePacks,
  PACK_SKILLS_BY_PACK_KEY,
  readCachedAgentsAndSkills,
  slugifyIdentifier,
  writeCachedAgentsAndSkills,
} from "./packAgentsCatalog";
import { useManagedAgentActions } from "./useManagedAgentActions";

export function useManagedAgentsAndSkills(
  activePacks: readonly ConfiguredPackItem[],
  onFeedback: (msg: string) => void,
  locale: SupportedWebLocale,
  catalogLabels: CatalogManagedLabels,
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
        const mappedSkills = (res.skills ?? []).map((s) =>
          mapSkillDtoToUi(s, catalogLabels.defaultSkillOutputFormat),
        );
        const mappedAgents = (res.agents ?? []).map(mapAgentDtoToUi);
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
          `⚠️ ${formatRfc9457ErrorToBanner(err, locale, catalogLabels.catalogErrorContext).fullText}`,
        ),
      );
    return () => {
      cancelled = true;
    };
  }, [onFeedback, locale, catalogLabels.catalogErrorContext, catalogLabels.defaultSkillOutputFormat]);

  const combinedState = mergeManagedStateWithActivePacks(managedState, activePacks);

  const handleLoadPackTemplates = () => {
    const defaultPacks: readonly ConfiguredPackItem[] = [
      { packKey: "orcia-pack-sdlc", version: "1.0.0", scopePath: "GLOBAL", status: "PUBLISHED" },
      { packKey: "orcia-pack-builder", version: "1.0.0", scopePath: "GLOBAL", status: "PUBLISHED" },
    ];
    updateManagedState((prev) => mergeManagedStateWithActivePacks(prev, defaultPacks));
    onFeedback(catalogLabels.packTemplatesLoadedBanner);
  };

  const handleCreateSkill = (draft: {
    name: string;
    objective: string;
    inputParameters: string[];
    instructions: string;
    expectedOutputFormat: string;
    visibilityScope?: "PRIVATE" | "TEAM";
  }) => {
    const slug = slugifyIdentifier(draft.name, "skill");
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
      expectedOutputFormat:
        draft.expectedOutputFormat.trim() || catalogLabels.defaultSkillOutputFormat,
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
          `⚠️ ${formatRfc9457ErrorToBanner(err, locale, catalogLabels.skillErrorContext).fullText}`,
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
          `⚠️ ${formatRfc9457ErrorToBanner(err, locale, catalogLabels.skillErrorContext).fullText}`,
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
            ? {
                ...skill,
                lastExecutionOutput: buildSkillLocalOutput(skill, inputText, catalogLabels),
              }
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
        const detail = formatRfc9457ErrorToBanner(
          err,
          locale,
          catalogLabels.skillErrorContext,
        ).fullText;
        onFeedback(`⚠️ ${detail}`);
        updateManagedState((prev) => ({
          ...prev,
          skills: prev.skills.map((s) =>
            s.skillId === skillId
              ? {
                  ...s,
                  lastExecutionOutput: `${s.lastExecutionOutput ?? ""}\n⚠️ ${detail}`,
                }
              : s,
          ),
        }));
      });
  };

  const agentActions = useManagedAgentActions({
    activePacks,
    locale,
    catalogLabels,
    onFeedback,
    updateManagedState,
  });

  return {
    agents: combinedState.agents,
    skills: combinedState.skills,
    handleLoadPackTemplates,
    handleCreateSkill,
    handleDeleteSkill,
    handleUpdateSkillVisibility,
    handleExecuteSkill,
    ...agentActions,
  };
}
