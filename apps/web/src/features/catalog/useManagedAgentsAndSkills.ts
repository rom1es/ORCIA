import { createOrciaApiClient } from "@orcia/api-client";
import type { UiAgentSkillVisibilityScope, UiManagedSkillItem } from "@orcia/ui";
import { useEffect, useRef, useState } from "react";
import type { ConfiguredPackItem } from "../../components/platformSetupStore";
import type { SupportedWebLocale } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import type { AlertFeedbackInput } from "../shared/alertFeedback";
import {
  type CachedAgentsAndSkillsState,
  type CatalogManagedLabels,
  buildSkillLocalOutput,
  mapAgentDtoToUi,
  mapSkillDtoToUi,
  readCachedAgentsAndSkills,
  slugifyIdentifier,
  writeCachedAgentsAndSkills,
} from "./managedAgentsHelpers";
import { useManagedAgentActions } from "./useManagedAgentActions";

export function useManagedAgentsAndSkills(
  activePacks: readonly ConfiguredPackItem[],
  onFeedback: (msg: AlertFeedbackInput) => void,
  locale: SupportedWebLocale,
  catalogLabels: CatalogManagedLabels,
  onModalError?: (msg: string) => void,
) {
  const [managedState, setManagedState] = useState<CachedAgentsAndSkillsState>(() =>
    readCachedAgentsAndSkills(),
  );
  const mutationEpochRef = useRef(0);

  const updateManagedState = (
    updater: (prev: CachedAgentsAndSkillsState) => CachedAgentsAndSkillsState,
  ) => {
    mutationEpochRef.current += 1;
    setManagedState((prev) => {
      const next = updater(prev);
      writeCachedAgentsAndSkills(next);
      return next;
    });
  };

  useEffect(() => {
    let cancelled = false;
    const fetchEpoch = mutationEpochRef.current;
    createOrciaApiClient({ baseUrl: "" })
      .listAgentsAndSkills()
      .then((res) => {
        if (cancelled || mutationEpochRef.current !== fetchEpoch) return;
        const mappedSkills = (res.skills ?? []).map((s) =>
          mapSkillDtoToUi(s, catalogLabels.defaultSkillOutputFormat),
        );
        const mappedAgents = (res.agents ?? []).map(mapAgentDtoToUi);
        const nextState = { agents: mappedAgents, skills: mappedSkills };
        writeCachedAgentsAndSkills(nextState);
        setManagedState(nextState);
      })
      .catch((err: unknown) =>
        onFeedback({
          tone: "crimson",
          message: formatRfc9457ErrorToBanner(err, locale, catalogLabels.catalogErrorContext).fullText,
        }),
      );
    return () => {
      cancelled = true;
    };
  }, [onFeedback, locale, catalogLabels.catalogErrorContext, catalogLabels.defaultSkillOutputFormat]);

  const combinedState = managedState;

  const handleLoadPackTemplates = () => {
    void createOrciaApiClient({ baseUrl: "", locale })
      .listAgentsAndSkills()
      .then((res) => {
        const mappedSkills = (res.skills ?? []).map((s) =>
          mapSkillDtoToUi(s, catalogLabels.defaultSkillOutputFormat),
        );
        const mappedAgents = (res.agents ?? []).map(mapAgentDtoToUi);
        const nextState = { agents: mappedAgents, skills: mappedSkills };
        writeCachedAgentsAndSkills(nextState);
        setManagedState(nextState);
        onFeedback(catalogLabels.packTemplatesLoadedBanner);
      })
      .catch((err: unknown) =>
        onFeedback({
          tone: "crimson",
          message: formatRfc9457ErrorToBanner(err, locale, catalogLabels.catalogErrorContext).fullText,
        }),
      );
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
        onFeedback({
          tone: "crimson",
          message: formatRfc9457ErrorToBanner(err, locale, catalogLabels.skillErrorContext).fullText,
        }),
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
        onFeedback({
          tone: "crimson",
          message: formatRfc9457ErrorToBanner(err, locale, catalogLabels.skillErrorContext).fullText,
        }),
      );
  };

  const handleUpdateSkillVisibility = (
    skillId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => {
    updateManagedState((prev) => ({
      ...prev,
      skills: prev.skills.map((s) =>
        s.skillId === skillId ? { ...s, visibilityScope: nextVisibility } : s,
      ),
    }));
  };

  const handleExecuteSkill = (skillId: string, inputText: string) => {
    updateManagedState((prev) => ({
      ...prev,
      skills: prev.skills.map((skill) =>
        skill.skillId === skillId
          ? {
              ...skill,
              lastExecutionOutput: buildSkillLocalOutput(skill, inputText, catalogLabels),
            }
          : skill,
      ),
    }));
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
        onFeedback({ tone: "crimson", message: detail });
        updateManagedState((prev) => ({
          ...prev,
          skills: prev.skills.map((s) =>
            s.skillId === skillId
              ? {
                  ...s,
                  lastExecutionOutput: `${s.lastExecutionOutput ?? ""}\n${detail}`,
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
    onModalError,
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
