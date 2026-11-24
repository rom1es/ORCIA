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
): readonly DelegateAgentOption[] {
  return DICTIONARIES[locale].processStudioUi.studio.delegateAgents;
}
