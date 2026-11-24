import type { EightFixedMenuKey } from "@orcia/ui";

export interface ShellNotificationsDictionary {
  readonly tempPassword: {
    readonly badge: string;
    readonly title: string;
    readonly description: string;
    readonly cta: string;
  };
  readonly llmMissing: {
    readonly badge: string;
    readonly title: string;
    readonly description: string;
    readonly cta: string;
  };
  readonly billingTeamMissing: {
    readonly badge: string;
    readonly title: string;
    readonly description: string;
    readonly cta: string;
  };
  readonly orgMissing: {
    readonly badge: string;
    readonly title: string;
    readonly description: string;
    readonly cta: string;
  };
  readonly workspaceMissing: {
    readonly badge: string;
    readonly title: string;
    readonly description: string;
    readonly cta: string;
  };
  readonly decisionWaiting: {
    readonly badge: string;
    readonly cta: string;
  };
  readonly inboxTask: {
    readonly openBadge: string;
    readonly claimedBadge: string;
    readonly cta: string;
  };
  readonly autonomous: {
    readonly escalationBadge: string;
    readonly triggerPausedBadge: string;
    readonly qualitySampleBadge: string;
    readonly sampleDescriptionTemplate: string;
    readonly attentionDescriptionTemplate: string;
    readonly reviewCta: string;
    readonly nominalBadge: string;
    readonly inspectCta: string;
  };
  readonly livePresence: {
    readonly badge: string;
    readonly claimedTitleTemplate: string;
    readonly releasedTitleTemplate: string;
    readonly cta: string;
  };
}

export interface ShellBreadcrumbsAndScopeDictionary {
  readonly breadcrumbs: {
    readonly inbox: string;
    readonly studio: string;
    readonly valueStream: string;
    readonly qualityGates: string;
    readonly catalog: string;
    readonly glossary: string;
    readonly sources: string;
    readonly activityLog: string;
    readonly organization: string;
    readonly guidedWizards: string;
    readonly profile: string;
    readonly showcase: string;
    readonly redundantAllSpacesLabels: readonly string[];
  };
  readonly accostageMilestones: {
    readonly firstAdmin: string;
    readonly aiModels: string;
    readonly organization: string;
    readonly firstTeamSpace: string;
    readonly firstSource: string;
    readonly firstProcess: string;
    readonly activeLayersTemplate: string;
  };
  readonly disabledMenuReasons: Partial<Record<EightFixedMenuKey, string>>;
}
