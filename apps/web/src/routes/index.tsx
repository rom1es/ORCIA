import {
  CollapsibleAppRail,
  ScopedPromptBox,
  SprintContextWidget,
  TopHeaderBar,
} from "@orcia/ui";
import { createRoute, redirect } from "@tanstack/react-router";
import React from "react";
import { ModuleWorkspaceView } from "../components/ModuleWorkspaceView";
import { useI18n } from "../i18n";
import { Route as rootRoute } from "./__root";
import { preloadModuleQueryData, validateOrciaRouteSearch } from "./searchSchema";

function HomeAntiEmptyStateView() {
  const { dictionary } = useI18n();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <TopHeaderBar
        activeWorkspaceName="Workspace 1 — Paiements & Checkout Web"
        activePackKey="orcia-pack-sdlc"
        activeSprintName="Sprint 24 (PI-2026-Q4)"
        dbosPg18Healthy={true}
        outboxDlqCount={0}
        labels={dictionary.topHeader}
      />
      <div style={{ display: "flex", gap: "16px", alignItems: "flex-start", flexWrap: "wrap" }}>
        <CollapsibleAppRail
          activePackKey="orcia-pack-sdlc"
          actionRequiredCount={2}
          outboxPendingCount={0}
          labels={dictionary.collapsibleRail}
        />
        <div style={{ flex: 1, minWidth: "280px", display: "flex", flexDirection: "column", gap: "16px" }}>
          <SprintContextWidget
            sprintName="Sprint 24 (PI-2026-Q4)"
            sprintGoal="Livrer la supervision multi-runs (< 1 s) et l'accueil Anti-Empty-State scopé."
            completedStories={18}
            totalStories={21}
            openRisksCount={1}
            labels={dictionary.sprintWidget}
          />
          <ScopedPromptBox
            availableSources={[
              {
                sourceUri: "git://gitlab.entreprise.io/payments/checkout-web",
                alias: "repo-checkout",
                authorized: true,
              },
              {
                sourceUri: "confluence://ARCHI/payments-adr",
                alias: "wiki-archi",
                authorized: true,
              },
              {
                sourceUri: "jira://SECOPS/Restricted",
                alias: "jira-secops",
                authorized: false,
              },
            ]}
            labels={dictionary.scopedPrompt}
          />
        </div>
      </div>
      <ModuleWorkspaceView moduleKey="cockpit" />
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: validateOrciaRouteSearch,
  beforeLoad: ({ search }) => {
    if (search.auth === "unauthenticated") {
      throw redirect({ to: "/login" });
    }
  },
  loaderDeps: ({ search }) => ({ fixture: search.fixture === "test" }),
  loader: ({ context, deps }) =>
    preloadModuleQueryData(context.queryClient, "cockpit", deps.fixture),
  component: HomeAntiEmptyStateView,
});
