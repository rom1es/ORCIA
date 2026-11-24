import type {
  BiModeLoginLabels,
  CollapsibleAppRailLabels,
  CommandPaletteModalLabels,
  MobileCompanionLabels,
  ScopedPromptBoxLabels,
  SprintContextWidgetLabels,
  TopHeaderBarLabels,
  WorkspaceControlCenterLabels,
} from "@orcia/ui";

export interface InboxAndCockpitDictionarySection {
  readonly controlCenter: WorkspaceControlCenterLabels;
  readonly commandPalette: CommandPaletteModalLabels;
  readonly mobileCompanion: MobileCompanionLabels;
  readonly biModeLogin: BiModeLoginLabels;
  readonly collapsibleRail: CollapsibleAppRailLabels;
  readonly topHeader: TopHeaderBarLabels;
  readonly sprintWidget: SprintContextWidgetLabels;
  readonly scopedPrompt: ScopedPromptBoxLabels;
  readonly humanLedGovernance: {
    readonly sectionTitle: string;
    readonly anchorAndArbitrationDesc: string;
    readonly anchorOnlyDesc: string;
    readonly arbitrationOnlyDesc: string;
    readonly signatureLabel: string;
  };
}

export { INBOX_AND_COCKPIT_FR_LABELS } from "./inbox_and_cockpit_labels_fr";
export { INBOX_AND_COCKPIT_EN_LABELS } from "./inbox_and_cockpit_labels_en";
