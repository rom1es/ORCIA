import type {
  ContextualHelpColumnAndCenterLabels,
  FourZoneDirectionCShellLabels,
  ProgressiveDay0AccostageLabels,
  StreamlinedCockpitLabels,
  TopHeaderSearchCommandLabels,
  UserAccountDropdownAndSettingsLabels,
} from "@orcia/ui";

export interface FirstBootAdminModalLabels {
  readonly title: string;
  readonly description: string;
  readonly firstTimeBadge: string;
  readonly fullNameLabel: string;
  readonly fullNamePlaceholder: string;
  readonly emailLabel: string;
  readonly emailPlaceholder: string;
  readonly passwordLabel: string; // pragma: allowlist secret
  readonly confirmPasswordLabel: string; // pragma: allowlist secret
  readonly showPasswordLabel: string; // pragma: allowlist secret
  readonly hidePasswordLabel: string; // pragma: allowlist secret
  readonly passwordMismatchError: string; // pragma: allowlist secret
  readonly assignedRoleBadge: string;
  readonly submitCta: string;
  readonly missingFieldsHint: string;
  readonly reopenSetupCta: string;
  readonly day0DisabledAdminMissingReason: string;
}

export interface ShellAndSearchDictionarySection {
  readonly fourZoneShell: FourZoneDirectionCShellLabels;
  readonly sidebarFooter: {
    readonly myAccountLabel: string;
    readonly documentationLabel: string;
  };
  readonly firstBootAdminModal: FirstBootAdminModalLabels;
  readonly streamlinedCockpit: StreamlinedCockpitLabels;
  readonly progressiveAccostage: ProgressiveDay0AccostageLabels;
  readonly topHeaderSearch: TopHeaderSearchCommandLabels;
  readonly userAccountAndSettings: UserAccountDropdownAndSettingsLabels;
  readonly contextualHelpHybrid: ContextualHelpColumnAndCenterLabels;
}

export { SHELL_AND_SEARCH_FR_LABELS } from "./shell_and_search_labels_fr";
export { SHELL_AND_SEARCH_EN_LABELS } from "./shell_and_search_labels_en";
