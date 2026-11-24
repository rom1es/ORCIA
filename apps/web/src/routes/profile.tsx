import { createOrciaApiClient, type UserProfileSummaryResponse } from "@orcia/api-client";
import { UserProfileOverviewPage, type UiUserProfileSummaryView } from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useOrciaNavigation } from "../components/navigationAdapter";
import { extractUiErrorMessage } from "../components/sidebarAccountMappers";
import { useI18n } from "../i18n";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

function mapProfileDtoToUi(dto: UserProfileSummaryResponse): UiUserProfileSummaryView {
  return {
    userId: dto.user_id,
    displayName: dto.display_name,
    handle: dto.handle,
    email: dto.email,
    primaryRole: dto.primary_role,
    roles: dto.roles ?? [dto.primary_role],
    ledBusinessUnits: dto.led_business_units ?? [],
    ontologyBusinessUnits: dto.ontology_business_units ?? [],
    ledTeams: dto.led_teams ?? [],
    memberTeams: dto.member_teams ?? [],
    totalTokens: dto.total_tokens,
    peakDailyTokens: dto.peak_daily_tokens,
    longestStreakDays: dto.longest_streak_days,
    currentStreakDays: dto.current_streak_days,
    popularItems: (dto.popular_items ?? []).map((item) => ({
      itemType: item.item_type,
      itemKey: item.item_key,
      title: item.title,
      usageCount: item.usage_count,
      targetRoute: item.target_route,
    })),
  };
}

export function UserProfileRouteView(): React.ReactElement {
  const { locale, dictionary } = useI18n();
  const { navigateTo } = useOrciaNavigation();
  const displayName =
    useAuthSessionStore((s) => s.displayName) ?? dictionary.shellChrome.guestDisplayNameFallback;
  const email = useAuthSessionStore((s) => s.email) ?? "";
  const roles = useAuthSessionStore((s) => s.roles);
  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const openUserSettingsModalAtTab = useAuthSessionStore(
    (s) => s.openUserSettingsModalAtTab,
  );

  const client = useMemo(
    () =>
      createOrciaApiClient({
        baseUrl: "",
        locale,
        ...(readOnlyObserver
          ? { extraHeaders: { "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER" } }
          : {}),
      }),
    [locale, readOnlyObserver],
  );

  const fallbackProfile = useMemo<UiUserProfileSummaryView>(
    () => ({
      userId: "me",
      displayName,
      handle: (email.split("@")[0] || displayName.toLowerCase().replace(/\s+/g, ".")) || "user",
      email,
      primaryRole: roles[0] ?? "CONTRIBUTOR",
      roles: roles.length > 0 ? roles : ["CONTRIBUTOR"],
      ledBusinessUnits: [],
      ontologyBusinessUnits: [],
      ledTeams: [],
      memberTeams: [],
      totalTokens: 0,
      peakDailyTokens: 0,
      longestStreakDays: 0,
      currentStreakDays: 0,
      popularItems: [],
    }),
    [displayName, email, roles],
  );

  const [summary, setSummary] = useState<UiUserProfileSummaryView | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const genericErrorLabel =
    dictionary.userAccountAndSettings.passwordSecurity.genericError;

  const loadProfileSummary = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const dto = await client.getUserProfileSummary();
      setSummary(mapProfileDtoToUi(dto));
    } catch (err: unknown) {
      setErrorMessage(extractUiErrorMessage(err, genericErrorLabel));
    } finally {
      setIsLoading(false);
    }
  }, [client, genericErrorLabel]);

  useEffect(() => {
    if (isHydrating || !isAuthenticated) {
      return;
    }
    void loadProfileSummary();
  }, [isHydrating, isAuthenticated, loadProfileSummary]);

  return (
    <UserProfileOverviewPage
      profile={summary ?? fallbackProfile}
      locale={locale}
      labels={dictionary.profileOverview}
      isLoading={isLoading && summary === null}
      errorMessage={errorMessage}
      onRetry={() => void loadProfileSummary()}
      onEditAccount={() => openUserSettingsModalAtTab("ACCOUNT_SECURITY")}
      onSelectPopularItem={(targetRoute) => navigateTo(targetRoute)}
      onExploreAgents={() => navigateTo("/agents")}
    />
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/profile",
  validateSearch: validateOrciaRouteSearch,
  component: UserProfileRouteView,
});
