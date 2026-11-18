/**
 * Types for `UserProfileOverviewPage` (`AD-21`, `Story 20.4`).
 * Isolated in `packages/ui` — zero imports of `@orcia/api-client` or `@tanstack/react-router`.
 */

export type UiProfilePopularItemType = "AGENT" | "PROCESS" | "SKILL" | "TOOL";

export interface UiProfilePopularUsageItem {
  readonly itemType: UiProfilePopularItemType;
  readonly itemKey: string;
  readonly title: string;
  readonly usageCount: number;
  readonly targetRoute: string;
}

export interface UiUserProfileSummaryView {
  readonly userId: string;
  readonly displayName: string;
  readonly handle: string;
  readonly email: string;
  readonly primaryRole: string;
  readonly roles: readonly string[];
  readonly ledBusinessUnits: readonly string[];
  readonly ontologyBusinessUnits: readonly string[];
  readonly ledTeams: readonly string[];
  readonly memberTeams: readonly string[];
  readonly totalTokens: number;
  readonly peakDailyTokens: number;
  readonly longestStreakDays: number;
  readonly currentStreakDays: number;
  readonly popularItems: readonly UiProfilePopularUsageItem[];
}

export interface UserProfileOverviewLabels {
  readonly editButtonLabel: string;
  readonly ledBuBadgePrefix: string;
  readonly ontologyBuBadgePrefix: string;
  readonly ledTeamBadgePrefix: string;
  readonly memberTeamBadgePrefix: string;
  readonly totalTokensLabel: string;
  readonly totalTokensHint: string;
  readonly peakDailyTokensLabel: string;
  readonly peakDailyTokensHint: string;
  readonly longestStreakLabel: string;
  readonly currentStreakLabel: string;
  readonly daysUnitSingular: string;
  readonly daysUnitPlural: string;
  readonly popularSectionTitle: string;
  readonly popularSectionSubtitle: string;
  readonly usageCountSingular: string;
  readonly usageCountPlural: string;
  readonly itemTypeLabels: Readonly<Record<UiProfilePopularItemType, string>>;
  readonly emptyPopularTitle: string;
  readonly emptyPopularDescription: string;
  readonly exploreAgentsCta: string;
  readonly loadingLabel: string;
  readonly retryLabel: string;
}
