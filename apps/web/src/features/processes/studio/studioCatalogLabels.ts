import type { UiManagedAgentItem } from "@orcia/ui";
import { readCachedAgentsAndSkills } from "../../../components/agentsAndSkillsBridgeStore";
import { DICTIONARIES, type SupportedWebLocale } from "../../../i18n";
import type { ProcessDelegateAgentLabel } from "../../../i18n/locales/process_studio_ui_labels";

export type DelegateAgentOption = ProcessDelegateAgentLabel;

export function getHumanToolLabel(
  tool: string,
  locale: SupportedWebLocale = "fr",
): string {
  return DICTIONARIES[locale].processStudioUi.studio.humanToolLabels[tool] ?? tool;
}

export function getHumanSkillLabel(
  skill: string,
  locale: SupportedWebLocale = "fr",
): string {
  return DICTIONARIES[locale].processStudioUi.studio.humanSkillLabels[skill] ?? skill;
}

export function getHumanKbLabel(
  kb: string,
  locale: SupportedWebLocale = "fr",
): string {
  return DICTIONARIES[locale].processStudioUi.studio.humanKbLabels[kb] ?? kb;
}

export function getDelegateAgents(
  locale: SupportedWebLocale = "fr",
  managedAgents: readonly UiManagedAgentItem[] = readCachedAgentsAndSkills().agents,
): readonly DelegateAgentOption[] {
  const blockedSlugs = new Set<string>(
    managedAgents
      .filter((a) => a.lifecycleStatus === "DRAFT" || a.enabledOnWorkspace === false)
      .map((a) => a.slug),
  );
  const baseDefaults = DICTIONARIES[locale].processStudioUi.studio.delegateAgents.filter(
    (d) => !blockedSlugs.has(d.slug),
  );
  const seen = new Set<string>(baseDefaults.map((d) => d.slug));
  const activeCustom: DelegateAgentOption[] = [];
  for (const ag of managedAgents) {
    if (ag.lifecycleStatus !== "ACTIVE" || ag.enabledOnWorkspace === false) continue;
    if (seen.has(ag.slug)) continue;
    seen.add(ag.slug);
    activeCustom.push({
      slug: ag.slug,
      label: ag.name,
      role: ag.roleMission,
    });
  }
  return [...baseDefaults, ...activeCustom];
}
