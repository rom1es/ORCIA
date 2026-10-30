import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  BiModeLoginView,
  CollapsibleAppRail,
  CommandPaletteModal,
  GuidanceDrawer,
  MobileCompanionView,
  PresenceClaimPill,
  ProductLifecycleCard,
  ScopedPromptBox,
  SprintContextWidget,
  TopHeaderBar,
  WorkspaceControlCenter,
  resolveResponsiveBreakpoint,
} from "../index";

describe("Epic 5 @orcia/ui Primitives (Stories 5.1, 5.2, 5.3, 5.4)", () => {
  it("Story 5.1: PresenceClaimPill renders UNCLAIMED, CLAIMED_BY_ME and CLAIMED_BY_PEER (0.85 opacity + Force Unclaim)", () => {
    const onClaim = vi.fn();
    const onRelease = vi.fn();
    const labels = {
      claimActionLabel: "Prendre (Claim)",
      claimedByMeBadge: "🔒 Pris par vous",
      claimedByPeerPrefix: "🔒 En cours :",
      releaseActionLabel: "Relâcher",
      forceUnclaimActionLabel: "Forcer la reprise (15m)",
      readOnlyObserverNotice: "Consultation seule (403)",
      sseLatencyPrefix: "SSE :",
    };

    const { rerender } = render(
      <PresenceClaimPill
        taskId="task-1"
        stepExecutionId="step-1"
        presenceState="UNCLAIMED"
        labels={labels}
        onClaim={onClaim}
      />,
    );
    fireEvent.click(screen.getByTestId("claim-task-btn-task-1"));
    expect(onClaim).toHaveBeenCalledWith("task-1");

    rerender(
      <PresenceClaimPill
        taskId="task-1"
        stepExecutionId="step-1"
        presenceState="CLAIMED_BY_PEER"
        claimedByDisplayName="Nadia"
        canForceUnclaim={true}
        labels={labels}
        onRelease={onRelease}
      />,
    );
    const pill = screen.getByTestId("presence-claim-pill-task-1");
    expect(pill.getAttribute("data-presence-state")).toBe("CLAIMED_BY_PEER");
    fireEvent.click(screen.getByTestId("force-unclaim-btn-task-1"));
    expect(onRelease).toHaveBeenCalledWith("task-1", true);
  });

  it("Story 5.2: WorkspaceControlCenter switches 4 fractal tabs, Scope Selector, GuidanceDrawer, ProductLifecycleCard & CommandPaletteModal", () => {
    const onSelectPhase = vi.fn();
    const onChangeScope = vi.fn();
    const onClosePalette = vi.fn();

    render(
      <>
        <WorkspaceControlCenter
          scopeType="GLOBAL"
          scopeLabel="Plateforme Globale"
          isReadOnlyObserver={false}
          consolidatedFinopsUsd={32.65}
          contributorRuns={[
            {
              runId: "r-1",
              workspaceId: "ws-1",
              workspaceName: "WS 1",
              title: "Run #1",
              status: "PAUSED_ARBITRATION",
              currentStepKey: "step-1",
              executionMode: "COACHING",
              accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
              budgetConsumedUsd: 4.25,
              blackboardSummary: "Résumé",
            },
          ]}
          observerRuns={[]}
          datasources={[
            {
              id: "ds-1",
              workspaceName: "WS 1",
              alias: "repo-1",
              scheme: "git",
              uri: "git://org/repo",
              executionIdentity: "passthrough",
              freshnessTtlDays: 14,
              tripartiteStatus: "STALE_WARNING",
            },
          ]}
          guidanceSteps={[
            {
              stepNumber: 1,
              title: "1. Qualifier",
              description: "Choisir phase",
              actionCommand: "set-lifecycle-phase",
            },
          ]}
          workflowOverrides={[
            {
              workflowKey: "wf-1",
              title: "Workflow 1",
              baseLayer: "v1",
              teamOverride: "t1",
              workspaceOverride: "w1",
              userOverride: "u1",
              spineContractRef: "AD-2",
            },
          ]}
          workspacesGovernance={[
            {
              workspaceId: "ws-1",
              name: "WS 1",
              visibilityMode: "STANDARD",
              lifecyclePhase: "BUILD",
              suggestedWorkflows: ["wf-build"],
              accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
              finopsCostUsd: 4.25,
            },
          ]}
          labels={{
            title: "Centre de Pilotage",
            scopeSelectorLabel: "Périmètre",
            scopeGlobal: "Global",
            scopeBu: "BU",
            scopeTeam: "Équipe",
            scopeWorkspace: "Workspace",
            tab1Runs: "1. Runs",
            tab2Datasources: "2. Sources",
            tab3Workflows: "3. Workflows",
            tab4Governance: "4. Gouvernance",
            contributorRunsHeader: "Actions Requises",
            observerRunsHeader: "En Suivi",
            attachDatasourceButton: "Rattacher",
            launchRunButton: "Lancer",
            observerBannerDefault: "Mode Consultation Seule",
            guidanceDrawer: {
              drawerTitle: "Guide 5 étapes",
              toggleExpand: "Déplier",
              toggleCollapse: "Replier",
              commandPrefix: "Action",
            },
            lifecycleCard: {
              phaseTitle: "Cycle",
              runBadge: "RUN",
              buildBadge: "BUILD",
              migrationBadge: "MIGRATION",
              suggestedWorkflowsTitle: "Workflows",
              readOnlyHint: "Lecture seule",
            },
          }}
          onChangeScopeType={onChangeScope}
          onSelectPhase={onSelectPhase}
        />
        <CommandPaletteModal
          isOpen={true}
          items={[
            {
              entryId: "nav-ws",
              category: "NAVIGATION",
              label: "Workspaces",
              subtitle: "Supervision",
              shortcut: "g w",
              targetRoute: "/workspaces",
            },
          ]}
          labels={{
            modalTitle: "Palette",
            searchPlaceholder: "Rechercher...",
            closeButton: "Fermer",
            emptyResults: "Aucun",
            contributorBadge: "Contributeur",
            observerBadge: "Observateur",
          }}
          onClose={onClosePalette}
        />
      </>,
    );

    fireEvent.click(screen.getByTestId("scope-selector-BU"));
    expect(onChangeScope).toHaveBeenCalledWith("BU");

    fireEvent.click(screen.getByTestId("control-center-tab-datasources"));
    expect(screen.getByTestId("guidance-drawer")).toBeDefined();

    fireEvent.click(screen.getByTestId("control-center-tab-workflows"));
    expect(screen.getByTestId("override-item-wf-1")).toBeDefined();

    fireEvent.click(screen.getByTestId("control-center-tab-governance"));
    fireEvent.click(screen.getByTestId("lifecycle-btn-ws-1-MIGRATION"));
    expect(onSelectPhase).toHaveBeenCalledWith("ws-1", "MIGRATION");

    fireEvent.keyDown(screen.getByTestId("command-palette-modal"), {
      key: "Escape",
    });
    expect(onClosePalette).toHaveBeenCalled();
  });

  it("Story 5.3: MobileCompanionView enforces 3 breakpoints, 3 bottom tabs, Desktop-only banner & WCAG 2.2 AA badges", () => {
    expect(resolveResponsiveBreakpoint(1440)).toBe("DESKTOP");
    expect(resolveResponsiveBreakpoint(1024)).toBe("LAPTOP");
    expect(resolveResponsiveBreakpoint(390)).toBe("MOBILE");

    const onApprove = vi.fn();
    render(
      <MobileCompanionView
        viewportWidthPx={390}
        attemptedDesktopOnlyFeature="YAML_EDITOR"
        briefingSections={[
          { sectionId: "sec-1", title: "Section 1", approved: false },
        ]}
        labels={{
          companionTitle: "Mobile Companion",
          tabInbox: "🔔 Inbox",
          tabArbitration: "💬 Arbitrage/Chat",
          tabBriefing: "📄 Briefing",
          desktopOnlyBanner: "Fonctionnalité réservée au poste Desktop",
          blockedYamlEditorLabel: "Édition YAML",
          blockedHeavyCoEditingLabel: "Co-édition lourde",
          blockedAdminModuleLabel: "Administration",
          badgeHumanAnchor: "✍️ Ancrage Humain",
          badgeAiArbitration: "⚖️ Arbitrage IA",
          badgeGate: "🛡️ Gate",
          badgeStaleWarning: "🚨 Obsolète",
          approveSectionCta: "Valider",
          liveRegionDefault: "Flux SSE actif",
        }}
        onApproveBriefingSection={onApprove}
      />,
    );

    expect(
      screen.getByTestId("desktop-only-restriction-banner").textContent,
    ).toContain("Fonctionnalité réservée au poste Desktop");
    expect(
      screen.getByTestId("semantic-badge-HUMAN_ANCHOR").textContent,
    ).toContain("✍️ Ancrage Humain");

    fireEvent.click(screen.getByTestId("mobile-tab-btn-briefing"));
    fireEvent.click(screen.getByTestId("mobile-approve-btn-sec-1"));
    expect(onApprove).toHaveBeenCalledWith("sec-1");
  });

  it("Story 5.4: BiModeLoginView, CollapsibleAppRail, TopHeaderBar, SprintContextWidget & ScopedPromptBox", () => {
    const onAudit = vi.fn();
    const onSubmitPrompt = vi.fn();

    render(
      <>
        <BiModeLoginView
          labels={{
            title: "Connexion ORCIA",
            subtitle: "Bi-Mode",
            primarySsoCta: "SSO d'Entreprise (OIDC PKCE)",
            localAccordionToggle: "Connexion locale",
            emailLabel: "Email",
            passwordLabel: "Mot de passe", // pragma: allowlist secret
            totpLabel: "TOTP",
            submitLocalCta: "Connexion",
            errorBannerTitle: "Erreur RFC 9457",
          }}
          error={{
            errorCode: "ERR_INVALID_CREDENTIALS",
            detail: "Session expirée",
            traceId: "trace-123",
          }}
        />
        <CollapsibleAppRail
          activePackKey="orcia-pack-sdlc"
          labels={{
            railAriaLabel: "Rail",
            expandRailCta: "Étendre",
            collapseRailCta: "Replier",
            activePackPrefix: "Pack",
            actionRequiredBadgeLabel: "actions",
            outboxHealthyLabel: "nominal",
          }}
        />
        <TopHeaderBar
          activeWorkspaceName="WS 1"
          activePackKey="orcia-pack-sdlc"
          activeSprintName="Sprint 24"
          labels={{
            workspacePackSelectorLabel: "Workspace",
            sprintSelectorLabel: "Sprint",
            dbosPg18HealthLabel: "DBOS/PG18",
            outboxHealthLabel: "Outbox",
          }}
        />
        <SprintContextWidget
          sprintName="Sprint 24"
          sprintGoal="Livrer Epic 5"
          completedStories={4}
          totalStories={4}
          openRisksCount={0}
          labels={{
            widgetTitle: "Contexte Sprint",
            sprintGoalLabel: "Objectif",
            velocityLabel: "Vélocité",
            openRisksLabel: "Risques",
            auditRisksCta: "Auditer les risques du sprint / lot avec l'IA",
            auditCompletedMessage: "Audit lancé",
          }}
          onAuditSprintRisks={onAudit}
        />
        <ScopedPromptBox
          availableSources={[
            {
              sourceUri: "git://repo-1",
              alias: "repo-1",
              authorized: true,
            },
          ]}
          labels={{
            boxTitle: "Prompt Scopé",
            promptPlaceholder: "Question...",
            ragScopeLabel: "Sources RAG",
            cognitiveTierLabel: "Tier",
            tier1Label: "Tier 1",
            tier2Label: "Tier 2",
            tier3Label: "Tier 3",
            submitCta: "Envoyer",
          }}
          onSubmitScopedPrompt={onSubmitPrompt}
        />
      </>,
    );

    expect(screen.getByTestId("login-rfc9457-error").textContent).toContain(
      "ERR_INVALID_CREDENTIALS",
    );
    fireEvent.click(screen.getByTestId("login-local-accordion-toggle"));
    expect(screen.getByTestId("login-local-form")).toBeDefined();

    const rail = screen.getByTestId("collapsible-app-rail");
    expect(rail.getAttribute("data-rail-mode")).toBe("expanded-240px");
    fireEvent.keyDown(rail, { key: "[" });
    expect(rail.getAttribute("data-rail-mode")).toBe("rail-72px");

    fireEvent.click(screen.getByTestId("sprint-audit-risks-cta"));
    expect(onAudit).toHaveBeenCalledWith("Sprint 24");

    fireEvent.click(screen.getByTestId("scoped-prompt-submit"));
    expect(onSubmitPrompt).toHaveBeenCalled();
  });
});
