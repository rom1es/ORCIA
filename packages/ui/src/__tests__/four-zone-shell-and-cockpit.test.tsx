import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  computeDefaultHelpColumnOpen,
  ContextualHelpColumnAndCenter,
  type ContextualHelpColumnAndCenterLabels,
  ContextualInfoTriggerButton,
  DEFAULT_EIGHT_FIXED_MENU_ENTRIES,
  DisabledButtonAlertIndicator,
  FourZoneDirectionCShell,
  type FourZoneDirectionCShellLabels,
  OrciaButton,
  OrciaDialog,
  ProgressiveDay0AccostageBanner,
  type ProgressiveDay0AccostageLabels,
  StreamlinedCockpitView,
  type StreamlinedCockpitLabels,
  TopHeaderSearchCommand,
  type TopHeaderSearchCommandLabels,
  SidebarAccountPopover,
  UserSettingsModalDialog,
  type UiUserSettingsTabKey,
} from "../index";
import { TEST_USER_SETTINGS_LABELS } from "./userSettingsLabelsFixture";

const SHELL_LABELS: FourZoneDirectionCShellLabels = {
  workspacePrefix: "Espace",
  searchTriggerPlaceholder: "Rechercher dans cet Espace ou partout (⌘K)...",
  contextualHelpButtonLabel: "? Aide",
  notificationsButtonLabel: "🔔 Notifications",
  notificationsDrawerTitle: "Centre de Notifications (420px)",
  notificationsEmptyText: "Aucune notification non lue.",
  sidebarAriaLabel: "Navigation principale à 9 entrées sans numéro",
  railCollapseLabel: "Replier le rail ([)",
  railExpandLabel: "Déplier le rail ([)",
  packSelectorLabel: "Pack Métier actif",
  helpColumnTitle: "❓ Aide Contextuelle (340px)",
  helpColumnExpectedTitle: "Ce qui est attendu ici",
  helpColumnExpectedBody: "Pilotez vos décisions prioritaires ou interrogez Mon Assistant.",
  menuEntries: {
    cockpit: "Cockpit",
    assistant: "Mon Assistant",
    processes: "Mes Processus",
    agents: "Mes Agents",
    spaces: "Mes Espaces",
    organization: "Mon Organisation",
    finops: "FinOps",
    configuration: "Administration",
    help: "Aide",
  },
};

const COCKPIT_LABELS: StreamlinedCockpitLabels = {
  orientationAssistantTitle: "💬 Mon Assistant",
  orientationAssistantDesc: "Interrogez vos sources avec citations [S1] en < 1,2 s.",
  orientationProcessesTitle: "☍ Mes Processus",
  orientationProcessesDesc: "Lancez le workflow pilote sdlc/ticket-to-tech-spec.",
  orientationSpacesTitle: "📦 Mes Espaces",
  orientationSpacesDesc: "Gérez vos sources, livrables et glossaire métier.",
  kpiAnchorsLabel: "Ancrages Humains",
  kpiArbitrationsLabel: "Arbitrages Tie-Break",
  kpiReviewsLabel: "Revues 4 blocs",
  kpiAlertsLabel: "Alertes",
  filterAllLabel: "Toutes les décisions",
  filterShortLabel: "Décisions courtes (Tie-Break)",
  filterHeavyLabel: "Atelier de revue Fokus",
  tieBreakInlineBadge: "⚖️ Arbitrage rapide sur place",
  tieBreakResolvedPrefix: "Arbitrage tranché :",
  heavyActionBadge: "🔒 Revue Fokus requise",
  openFocusReviewCta: "Ouvrir l'atelier de revue →",
  focusWorkshopBreadcrumbPrefix: "Mes Processus › Exécutions & Décisions ›",
  focusWorkshopCloseCta: "← Retour au Cockpit",
  redisLockAcquiredPrefix: "🔒 Verrou Redis acquis :",
};

describe("Story 9.1 — 4-Zone Direction C Shell, 8 Non-Numbered Menus & Streamlined Cockpit", () => {
  it("renders the 4 strict zones (TopHeaderBar 52px, Sidebar 240px/68px with 8 unnumbered menus, Central 1fr, Contextual Help 340px) and auto-collapses Help on < 1440px when total >= 1", () => {
    expect(computeDefaultHelpColumnOpen(1600, 0)).toBe(true);
    expect(computeDefaultHelpColumnOpen(1600, 3)).toBe(true);
    expect(computeDefaultHelpColumnOpen(1280, 0)).toBe(true);
    expect(computeDefaultHelpColumnOpen(1280, 2)).toBe(false);

    const onSelectMenu = vi.fn();
    const onOpenWorkspaceSwitcher = vi.fn();
    const onOpenSearchCommand = vi.fn();
    const onSelectPack = vi.fn();

    const { rerender } = render(
      <FourZoneDirectionCShell
        activeMenuKey="cockpit"
        activeWorkspaceName="Portail Paiement"
        activePackKey="orcia-pack-sdlc"
        availablePacks={["orcia-pack-sdlc", "orcia-pack-builder"]}
        userDisplayName="Hélène PM"
        userHatLabel="Product Manager"
        pendingDecisionsTotal={0}
        viewportWidth={1440}
        labels={SHELL_LABELS}
        onSelectMenu={onSelectMenu}
        onOpenWorkspaceSwitcher={onOpenWorkspaceSwitcher}
        onOpenSearchCommand={onOpenSearchCommand}
        onSelectPack={onSelectPack}
      >
        <div data-testid="central-zone-child">Cockpit Content</div>
      </FourZoneDirectionCShell>,
    );

    // Zone 2: TopHeaderBar (52px) places [O] ORCIA home link top-left & hides duplicate workspace selector on Desktop while Sidebar is expanded
    const topbar = screen.getByTestId("four-zone-top-header-bar");
    expect(topbar.style.height).toBe("52px");
    expect(screen.queryByTestId("topbar-fixed-workspace-selector")).toBeNull();
    expect(screen.queryByTestId("sidebar-brand-logo")).toBeNull();
    expect(screen.getByTestId("topbar-orcia-home-link").textContent).toContain("ORCIA");

    // Collapsing Sidebar rail reveals the compact TopHeaderBar workspace selector
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    const wsBtn = screen.getByTestId("topbar-fixed-workspace-selector");
    expect(wsBtn.textContent).toContain("Espace : Portail Paiement");
    fireEvent.click(wsBtn);
    expect(onOpenWorkspaceSwitcher).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));

    fireEvent.click(screen.getByTestId("topbar-federated-search-trigger"));
    expect(onOpenSearchCommand).toHaveBeenCalledTimes(1);

    expect(screen.queryByTestId("topbar-hat-badge")).toBeNull();
    expect(screen.queryByTestId("topbar-user-account-trigger")).toBeNull();

    // Notifications 420px drawer toggle
    expect(screen.queryByTestId("topbar-notifications-drawer")).toBeNull();
    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    const notifDrawer = screen.getByTestId("topbar-notifications-drawer");
    expect(notifDrawer.style.width).toBe("min(420px, 100vw)");

    // Zone 2: Sidebar (240px / 68px Rail via '[') with exactly 9 unnumbered entries (Story 25.2)
    const sidebar = screen.getByTestId("four-zone-sidebar");
    expect(sidebar.style.width).toBe("240px");
    expect(DEFAULT_EIGHT_FIXED_MENU_ENTRIES).toHaveLength(9);
    for (const entry of DEFAULT_EIGHT_FIXED_MENU_ENTRIES) {
      const btn = screen.getByTestId(`eight-menu-item-${entry.key}`);
      expect(btn.textContent).not.toMatch(/^\d+\./);
    }
    fireEvent.click(screen.getByTestId("eight-menu-item-assistant"));
    expect(onSelectMenu).toHaveBeenCalledWith("assistant", "/assistant");

    // Toggle sidebar rail 240px <-> 68px via '[' key
    fireEvent.keyDown(window, { key: "[" });
    expect(sidebar.style.width).toBe("68px");
    expect(sidebar.getAttribute("data-rail-collapsed")).toBe("true");

    // Footer pack selector
    fireEvent.change(screen.getByTestId("sidebar-pack-selector"), {
      target: { value: "orcia-pack-builder" },
    });
    expect(onSelectPack).toHaveBeenCalledWith("orcia-pack-builder");

    // Zone 4: Contextual Help Column (340px) is open when total == 0
    const helpCol = screen.getByTestId("four-zone-contextual-help-column");
    expect(helpCol.style.width).toBe("340px");

    // Rerender with viewportWidth = 1280 (< 1440px) and pendingDecisionsTotal = 2 (>= 1) -> auto-collapses!
    rerender(
      <FourZoneDirectionCShell
        activeMenuKey="cockpit"
        activeWorkspaceName="Portail Paiement"
        activePackKey="orcia-pack-sdlc"
        availablePacks={["orcia-pack-sdlc"]}
        userDisplayName="Hélène PM"
        userHatLabel="Product Manager"
        pendingDecisionsTotal={2}
        viewportWidth={1280}
        labels={SHELL_LABELS}
        onSelectMenu={onSelectMenu}
      >
        <div data-testid="central-zone-child">Cockpit Content</div>
      </FourZoneDirectionCShell>,
    );
    expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();

    // Clicking '? Aide' opens it on demand
    fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    expect(screen.getByTestId("four-zone-contextual-help-column")).toBeDefined();
  });

  it("hides 0/0/0/0 KPI counters and filter bar when total == 0, and separates 1-click Tie-Break from Focus Review Workshop (with Redis lock AD-4) when total >= 1", () => {
    const onResolveTieBreak = vi.fn();
    const onOpenFocusReview = vi.fn();

    const { rerender } = render(
      <StreamlinedCockpitView
        decisions={[]}
        currentUserId="user-yanis-01"
        labels={COCKPIT_LABELS}
        onResolveTieBreak={onResolveTieBreak}
        onOpenFocusReview={onOpenFocusReview}
      />,
    );

    // When total == 0: KPI counters (0/0/0/0), filter bar, and Story 25.3 removed waiting blocks are hidden!
    expect(screen.queryByTestId("cockpit-kpi-counters-grid")).toBeNull();
    expect(screen.queryByTestId("cockpit-decisions-filter-bar")).toBeNull();
    expect(screen.queryByTestId("cockpit-zero-decisions-banner")).toBeNull();
    expect(screen.queryByTestId("cockpit-quick-assistant-box")).toBeNull();
    expect(screen.queryByTestId("cockpit-quick-assistant-input")).toBeNull();
    expect(screen.getByTestId("cockpit-calm-orientation-panel")).toBeDefined();
    expect(screen.getByTestId("cockpit-orientation-card-assistant")).toBeDefined();
    expect(screen.getByTestId("cockpit-orientation-card-processes")).toBeDefined();
    expect(screen.getByTestId("cockpit-orientation-card-spaces")).toBeDefined();

    // When total >= 1: KPI counters appear, Tie-Break resolves in 1 click on place, heavy review opens Focus Review Workshop with Redis lock
    rerender(
      <StreamlinedCockpitView
        decisions={[
          {
            decisionId: "dec-tie-1",
            kind: "TIE_BREAK",
            runId: "run-101",
            stepExecutionId: "step-exec-101",
            title: "Choix du cache de session : Redis Cluster vs Valkey",
            summary: "Deux options équivalentes détectées par l'agent.",
            options: ["Option A : Redis 7.4", "Option B : Valkey 8"],
          },
          {
            decisionId: "dec-heavy-2",
            kind: "REVIEW_BRIEFING",
            runId: "run-202",
            stepExecutionId: "step-exec-202",
            title: "Spécification Technique Ticket PAY-412 (Briefing 4 blocs)",
            summary: "Artefact de 2 400 mots avec 3 hypothèses structurantes.",
          },
        ]}
        currentUserId="user-yanis-01"
        labels={COCKPIT_LABELS}
        onResolveTieBreak={onResolveTieBreak}
        onOpenFocusReview={onOpenFocusReview}
      />,
    );

    expect(screen.getByTestId("cockpit-kpi-counters-grid")).toBeDefined();
    expect(screen.getByTestId("cockpit-decisions-filter-bar")).toBeDefined();

    // 1-click inline resolution for Tie-Break
    fireEvent.click(screen.getByTestId("cockpit-tiebreak-option-dec-tie-1-0"));
    expect(onResolveTieBreak).toHaveBeenCalledWith("dec-tie-1", "Option A : Redis 7.4");
    expect(screen.getByTestId("cockpit-tiebreak-resolved-dec-tie-1").textContent).toContain(
      "Option A : Redis 7.4",
    );

    // Heavy action opens Focus Review Workshop and acquires Redis lock SET lock:step:<step_execution_id> <user_id> NX EX 900
    fireEvent.click(screen.getByTestId("cockpit-open-focus-review-btn-dec-heavy-2"));
    expect(onOpenFocusReview).toHaveBeenCalledWith(
      expect.objectContaining({
        decisionId: "dec-heavy-2",
        runId: "run-202",
        stepExecutionId: "step-exec-202",
        redisLockKey: "lock:step:step-exec-202",
        redisLockTtlSeconds: 900,
      }),
    );
    const workshop = screen.getByTestId("focus-review-workshop-view");
    expect(workshop.textContent).toContain("Run #run-202");
    expect(screen.getByTestId("focus-review-redis-lock-badge").textContent).toContain(
      "SET lock:step:step-exec-202 user-yanis-01 NX EX 900",
    );
  });

  it("Story 25.1 — renders unified 6-milestone ProgressiveDay0AccostageBanner without Step 1/2/3 sub-cards, locks uncollapsible < 6/6, and switches Quick Trial -> AD-10 badges", () => {
    const accostageLabels: ProgressiveDay0AccostageLabels = {
      bannerTitle: "Guide de Démarrage de la Plateforme",
      singleFamilyAmberWarning:
        "⚠️ Un seul fournisseur IA configuré — Ajoutez un 2e fournisseur indépendant dans Configuration › Modèles IA pour activer les revues croisées",
      dualFamilyAd10UnlockedBadge:
        "✅ ≥ 2 familles orthogonales actives — Gates Agentiques AD-10 débloquées",
      progressFormatTemplate: "{completed} / {total} complétées",
      collapseGuideLabel: "Réduire",
      expandGuideLabel: "Déplier le guide",
      milestoneDoneLabel: "Terminé",
      milestoneOpenLabel: "Configurer",
      adminInitializedBadge: "Administrateur de plateforme initialisé",
    };
    const onNavigateMilestone = vi.fn();

    const sixMilestones = (completedKeys: readonly string[]) => [
      { index: 1, key: "first-admin", title: "1. Compte Admin", completed: completedKeys.includes("first-admin"), targetRoute: "/profile" },
      { index: 2, key: "step-llm", title: "2. Modèles IA", completed: completedKeys.includes("step-llm"), targetRoute: "/configuration" },
      { index: 3, key: "step-iam", title: "3. Organisation", completed: completedKeys.includes("step-iam"), targetRoute: "/organization" },
      { index: 4, key: "step-workspaces", title: "4. Premier Espace d'équipe", completed: completedKeys.includes("step-workspaces"), targetRoute: "/spaces" },
      { index: 5, key: "step-connectors", title: "5. Première Source", completed: completedKeys.includes("step-connectors"), targetRoute: "/configuration" },
      { index: 6, key: "step-workflows", title: "6. Premier Processus", completed: completedKeys.includes("step-workflows"), targetRoute: "/processes" },
    ];

    const { rerender } = render(
      <ProgressiveDay0AccostageBanner
        completedCount={1}
        totalCount={6}
        defaultCompact={true}
        adminCreated={true}
        adminDisplayName="Alice Admin"
        initialFamilies={[]}
        milestones={sixMilestones(["first-admin"])}
        labels={accostageLabels}
        onNavigateMilestone={onNavigateMilestone}
      />,
    );

    // No redundant Step 1 / Step 2 / Step 3 wizard sub-blocks
    expect(screen.queryByTestId("welcome-setup-3step-wizard")).toBeNull();
    expect(screen.queryByTestId("welcome-setup-step1-card")).toBeNull();
    expect(screen.queryByTestId("welcome-setup-step2-card")).toBeNull();
    expect(screen.queryByTestId("welcome-setup-step3-card")).toBeNull();
    expect(screen.queryByTestId("welcome-setup-submit-admin-btn")).toBeNull();

    // Progress pill + uncollapsible lock when completedCount < 6 (even if defaultCompact=true)
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("1 / 6 complétées");
    expect(screen.queryByTestId("accostage-compact-toggle-btn")).toBeNull();
    expect(screen.getByTestId("progressive-day0-accostage-banner").getAttribute("data-compact")).toBe("false");

    const wsMilestone = screen.getByTestId("accostage-milestone-step-workspaces");
    expect(wsMilestone.textContent).toContain("4. Premier Espace d'équipe");
    expect(wsMilestone.getAttribute("data-completed")).toBe("false");
    fireEvent.click(wsMilestone);
    expect(onNavigateMilestone).toHaveBeenCalledWith("/spaces");

    // Completed milestone uses green --color-gate-pass tokens and aligned grid
    const adminMilestone = screen.getByTestId("accostage-milestone-first-admin");
    expect(adminMilestone.getAttribute("data-completed")).toBe("true");
    expect(adminMilestone.className).toContain("bg-[var(--color-gate-pass-bg)]");
    expect(adminMilestone.className).toContain("text-[var(--color-gate-pass)]");
    expect(adminMilestone.className).toContain("grid-cols-");
    expect(adminMilestone.querySelector('[data-orcia-icon="check"]')).not.toBeNull();
    expect(wsMilestone.querySelector('[data-orcia-icon="arrowRight"]')).not.toBeNull();

    // 1 model family -> Quick Trial amber warning
    rerender(
      <ProgressiveDay0AccostageBanner
        completedCount={2}
        totalCount={6}
        adminCreated={true}
        adminDisplayName="Alice Admin"
        initialFamilies={["qwen-2.5"]}
        milestones={sixMilestones(["first-admin", "step-llm"])}
        labels={accostageLabels}
        onNavigateMilestone={onNavigateMilestone}
      />,
    );
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("2 / 6 complétées");
    expect(screen.getByTestId("accostage-single-family-amber-badge").textContent).toContain(
      "⚠️ Un seul fournisseur IA configuré",
    );

    // 2 orthogonal families + 6/6 completed -> AD-10 badge + collapsible toggle unlocked!
    rerender(
      <ProgressiveDay0AccostageBanner
        completedCount={6}
        totalCount={6}
        defaultCompact={false}
        adminCreated={true}
        adminDisplayName="Alice Admin"
        initialFamilies={["qwen-2.5", "anthropic-claude"]}
        milestones={sixMilestones(["first-admin", "step-llm", "step-iam", "step-workspaces", "step-connectors", "step-workflows"])}
        labels={accostageLabels}
        onNavigateMilestone={onNavigateMilestone}
      />,
    );
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("6 / 6 complétées");
    expect(screen.queryByTestId("accostage-single-family-amber-badge")).toBeNull();
    expect(screen.getByTestId("accostage-dual-family-ad10-badge").textContent).toContain("AD-10");
    const toggleBtn = screen.getByTestId("accostage-compact-toggle-btn");
    expect(toggleBtn.textContent).toContain("Réduire");
    fireEvent.click(toggleBtn);
    expect(screen.getByTestId("progressive-day0-accostage-banner").getAttribute("data-compact")).toBe("true");
    expect(screen.getByTestId("accostage-compact-toggle-btn").textContent).toContain("Déplier le guide");
  });

  it("Story 25.1 — CockpitOrientationCards mirrors disabledMenuKeys on assistant and processes cards", () => {
    const onNavigateModule = vi.fn();
    const { rerender } = render(
      <StreamlinedCockpitView
        decisions={[]}
        currentUserId="user-1"
        labels={COCKPIT_LABELS}
        disabledMenuKeys={{
          assistant: "Configurez un modèle IA",
          processes: "Configurez un modèle IA",
        }}
        onNavigateModule={onNavigateModule}
      />,
    );

    const processesCard = screen.getByTestId("cockpit-orientation-card-processes") as HTMLButtonElement;
    expect(processesCard.disabled).toBe(true);
    expect(processesCard.getAttribute("aria-disabled")).toBe("true");
    fireEvent.click(processesCard);
    expect(onNavigateModule).not.toHaveBeenCalled();

    rerender(
      <StreamlinedCockpitView
        decisions={[]}
        currentUserId="user-1"
        labels={COCKPIT_LABELS}
        disabledMenuKeys={{}}
        onNavigateModule={onNavigateModule}
      />,
    );

    const unlockedProcesses = screen.getByTestId("cockpit-orientation-card-processes") as HTMLButtonElement;
    expect(unlockedProcesses.disabled).toBe(false);
    fireEvent.click(unlockedProcesses);
    expect(onNavigateModule).toHaveBeenCalledWith("/processes");
  });

  it("Story 9.3 — executes Two-Speed Federated Search (⌘K) with Zero Layout Shift, 3 scopes, 7 families, and 2s Deep-Linking", () => {
    const searchLabels: TopHeaderSearchCommandLabels = {
      modalTitle: "Recherche Fédérée & Contextuelle à 2 Vitesses (⌘K)",
      inputPlaceholder: "Rechercher...",
      scopeScreenLabel: "📍 Cet écran",
      scopeWorkspaceLabel: "📦 Cet Espace",
      scopeAllWorkspacesLabel: "🌐 Tous mes Espaces",
      speed1SectionTitle: "Vitesse 1 — Résultats lexicaux immédiats (< 30 ms · 0 $)",
      speed2SectionTitle: "Vitesse 2 — Passages proches sémantiques (Pause 450 ms)",
      semanticCloseMatchBadge: "✨ Passage proche",
      emptyResultsLabel: "Aucun résultat trouvé.",
      previewPaneTitle: "Aperçu rapide (⌘+Entrée)",
      deepLinkActionLabel: "Ouvrir ↵",
      openHelpColumnActionLabel: "Ouvrir ❓ Aide",
      askAssistantFooterPrefix: "💬 Poser la question",
      askAssistantFooterSuffix: "à Mon Assistant →",
      familyLabels: {
        FOLDERS_DISCUSSIONS: "Dossiers & Discussions",
        PROCESSES_EXECUTIONS: "Processus & Exécutions",
        AGENTS_TOOLS: "Agents & Outils",
        DELIVERABLES_ARTIFACTS: "Livrables & Artefacts",
        SOURCES_SNIPPETS: "Sources & Passages",
        ONTOLOGY_GLOSSARY: "Ontologie & Glossaire",
        HELP_ACTIONS: "Aide & Actions",
      },
    };

    const onSelectDeepLink = vi.fn();
    const onAskAssistant = vi.fn();

    const speed1Hits = [
      {
        itemId: "hit-speed1-1",
        family: "FOLDERS_DISCUSSIONS" as const,
        title: "Dossier Architecture Paiement",
        snippet: "Synthèse avec citations [S1].",
        workspaceId: "ws-claims-alpha",
        screenRoute: "/cockpit",
        deepLinkUri: "/assistant?folder=hit-speed1-1#focus-hit-speed1-1",
        speedTier: 1 as const,
        lockedTop: true,
        score: 1.2,
        badge: null,
        highlightDurationMs: 2000,
        opensContextualHelpColumn: false,
      },
      {
        itemId: "hit-speed1-help",
        family: "HELP_ACTIONS" as const,
        title: "Guide : Arbitrer un Tie-Break",
        snippet: "Comment trancher en 1 clic.",
        workspaceId: "ws-claims-alpha",
        screenRoute: "/cockpit",
        deepLinkUri: "help://cockpit/overview",
        speedTier: 1 as const,
        lockedTop: true,
        score: 1.1,
        badge: null,
        highlightDurationMs: 2000,
        opensContextualHelpColumn: true,
      },
    ];

    const speed2Hits = [
      {
        itemId: "hit-speed2-sem",
        family: "SOURCES_SNIPPETS" as const,
        title: "Mécanisme de compensation interbancaire",
        snippet: "Règlement continu sur le grand livre.",
        workspaceId: "ws-claims-alpha",
        screenRoute: "/cockpit",
        deepLinkUri: "/spaces#focus-hit-speed2-sem",
        speedTier: 2 as const,
        lockedTop: false,
        score: 0.89,
        badge: "✨ Passage proche",
        highlightDurationMs: 2000,
        opensContextualHelpColumn: false,
      },
    ];

    const { rerender } = render(
      <TopHeaderSearchCommand
        labels={searchLabels}
        initialQuery="architecture paiement contrat"
        speed1Hits={speed1Hits}
        speed2Hits={[]}
        onSelectDeepLink={onSelectDeepLink}
        onAskAssistant={onAskAssistant}
      />,
    );

    // Move selection to index 1 (second Speed 1 item)
    const dialog = screen.getByTestId("top-header-search-command");
    fireEvent.keyDown(dialog, { key: "ArrowDown" });
    expect(
      screen.getByTestId("cmdk-results-list").getAttribute("data-selected-index"),
    ).toBe("1");

    // Append Speed 2 hits -> Zero Layout Shift: selected index remains 1 and Speed 1 stays on top!
    rerender(
      <TopHeaderSearchCommand
        labels={searchLabels}
        initialQuery="architecture paiement contrat"
        speed1Hits={speed1Hits}
        speed2Hits={speed2Hits}
        onSelectDeepLink={onSelectDeepLink}
        onAskAssistant={onAskAssistant}
      />,
    );
    expect(
      screen.getByTestId("cmdk-results-list").getAttribute("data-selected-index"),
    ).toBe("1");
    expect(
      screen.getByTestId("cmdk-semantic-badge-hit-speed2-sem").textContent,
    ).toBe("✨ Passage proche");

    // Tab cycles scope WORKSPACE -> ALL_WORKSPACES
    fireEvent.keyDown(dialog, { key: "Tab" });
    expect(
      screen.getByTestId("cmdk-scope-ALL_WORKSPACES").getAttribute("aria-selected"),
    ).toBe("true");

    // Clicking open on first Speed 1 hit triggers 2000ms auto-focus deep link
    fireEvent.click(screen.getByTestId("cmdk-open-btn-hit-speed1-1"));
    expect(onSelectDeepLink).toHaveBeenCalledWith({
      itemId: "hit-speed1-1",
      deepLinkUri: "/assistant?folder=hit-speed1-1#focus-hit-speed1-1",
      highlightDurationMs: 2000,
      opensContextualHelpColumn: false,
    });
    expect(
      screen.getByTestId("cmdk-deeplink-highlight-banner").textContent,
    ).toContain("2000 ms");

    // Clicking preview button opens right-side preview pane (⌘+Enter)
    fireEvent.click(screen.getByTestId("cmdk-preview-btn-hit-speed1-1"));
    expect(screen.getByTestId("cmdk-preview-pane")).toBeDefined();

    // Footer CTA asks Mon Assistant with pre-filled query & active scope
    fireEvent.click(screen.getByTestId("cmdk-ask-assistant-cta"));
    expect(onAskAssistant).toHaveBeenCalledWith(
      "architecture paiement contrat",
      "ALL_WORKSPACES",
    );
  });

  it("Story 20.3 — renders SidebarAccountPopover & 5-tab UserSettingsModalDialog without hardcoded MCP secrets", () => {
    const onUpdatePreferences = vi.fn();
    const onCreateMcpToken = vi.fn();
    const onRevokeMcpToken = vi.fn();
    const onLogout = vi.fn();
    const onNavigateProfile = vi.fn();
    const onNavigateAssistantBehavior = vi.fn();

    function TestHarness() {
      const [modalOpen, setModalOpen] = React.useState(false);
      const [activeTab, setActiveTab] = React.useState<UiUserSettingsTabKey>("GENERAL");
      return (
        <>
          <SidebarAccountPopover
            railCollapsed={false}
            userDisplayName="Hélène"
            userEmail="helene@orcia.local"
            userRoleLabel="Contributeur"
            labels={TEST_USER_SETTINGS_LABELS.popover}
            onOpenSettingsTab={(tab) => {
              setActiveTab(tab);
              setModalOpen(true);
            }}
            onNavigateProfile={onNavigateProfile}
            onNavigateHelp={vi.fn()}
            onNavigateShowcase={vi.fn()}
            onLogout={onLogout}
          />
          <UserSettingsModalDialog
            open={modalOpen}
            onOpenChange={setModalOpen}
            activeTab={activeTab}
            onSelectTab={setActiveTab}
            userEmail="helene@orcia.local"
            userRole="CONTRIBUTOR"
            theme="light"
            locale="fr"
            defaultAssistantHat="ANALYST_PM_PO"
            assistantTone="balanced"
            personalInstructions=""
            autoOpenHelp={true}
            notificationsEnabled={true}
            mcpTokens={[
              {
                tokenId: "mcp-tok-1",
                label: "IDE MCP",
                tokenPrefix: "pat_mcp_dyn1...",
                tokenSha256: "sha256_verified",
                expiresInDays: 30,
                rpmLimit: 60,
                targetKind: "AGENT",
                targetSlug: "sdlc-spec-agent",
                mcpEndpointUri: "/api/v1/mcp/agents/sdlc-spec-agent",
                ideJsonSnippet: '{"mcpServers":{"orcia":{"url":"https://orcia.internal/api/v1/mcp/agents/sdlc-spec-agent"}}}',
                revoked: false,
              },
            ]}
            lastIssuedPlaintext={null}
            labels={TEST_USER_SETTINGS_LABELS}
            onUpdatePreferences={onUpdatePreferences}
            onNavigateAssistantBehavior={onNavigateAssistantBehavior}
            onCreateMcpToken={onCreateMcpToken}
            onRevokeMcpToken={onRevokeMcpToken}
          />
        </>
      );
    }

    render(<TestHarness />);

    expect(screen.getByTestId("sidebar-open-my-account-btn").textContent).toContain("Hélène");
    expect(screen.queryByTestId("dropdown-hat-selector")).toBeNull();

    // Open popover via keyboard Enter or pointerDown
    fireEvent.keyDown(screen.getByTestId("sidebar-open-my-account-btn"), { key: "Enter" });
    fireEvent.click(screen.getByTestId("account-popover-personalization-btn"));
    expect(screen.getByTestId("user-settings-modal")).toBeDefined();

    // Switch to General tab & update theme
    fireEvent.click(screen.getByTestId("user-settings-tab-GENERAL"));
    fireEvent.click(screen.getByTestId("settings-theme-dark"));
    expect(onUpdatePreferences).toHaveBeenCalledWith({ theme: "dark" });

    // Switch to Personalization tab & check redirect CTA
    fireEvent.click(screen.getByTestId("user-settings-tab-PERSONALIZATION"));
    fireEvent.click(screen.getByTestId("user-settings-assistant-redirect-link"));
    expect(onNavigateAssistantBehavior).toHaveBeenCalledWith("/assistant");

    // Switch to IDE_MCP_KEYS tab, generate and revoke
    fireEvent.click(screen.getByTestId("user-settings-tab-IDE_MCP_KEYS"));
    fireEvent.change(screen.getByTestId("mcp-target-kind-select"), {
      target: { value: "AGENT" },
    });
    fireEvent.change(screen.getByTestId("mcp-target-slug-input"), {
      target: { value: "sdlc-spec-agent" },
    });
    fireEvent.click(screen.getByTestId("mcp-generate-token-btn"));
    expect(onCreateMcpToken).toHaveBeenCalled();
    expect(screen.getByTestId("mcp-ide-snippet-mcp-tok-1").textContent).toContain(
      "/api/v1/mcp/agents/sdlc-spec-agent",
    );
    fireEvent.click(screen.getByTestId("mcp-revoke-btn-mcp-tok-1"));
    expect(onRevokeMcpToken).toHaveBeenCalledWith("mcp-tok-1");
  });

  it("Story 9.5 — renders Hybrid Contextual Help (340px column + /help center) with 4-layer merge, 3 accordions, assistant screen link, and 1-click Rollback @v(N-1)", () => {
    const helpLabels: ContextualHelpColumnAndCenterLabels = {
      columnHeaderTitle: "❓ Aide Contextuelle (340px)",
      centerHeaderTitle: "Centre d'Aide & Gouvernance (/help)",
      whatForSectionTitle: "À quoi sert cet écran ?",
      stepByStepAccordionTitle: "Pas-à-pas opérationnel",
      keyTermsAccordionTitle: "Termes clés du Pack",
      faqAccordionTitle: "Questions fréquentes",
      askAssistantOnScreenCta:
        "Poser une question à l'assistant sur cet écran →",
      rollbackButtonLabel: "⏪ Rollback",
      rollbackCompletedPrefix: "Version restaurée :",
      mergedLayersPrefix: "Fusion 4 couches :",
    };

    const onAskAssistantOnScreen = vi.fn();
    const onRollbackVersion = vi.fn();

    render(
      <ContextualHelpColumnAndCenter
        mode="COLUMN_340PX"
        route="/mes-espaces/$id/sources"
        pack="orcia-pack-sdlc"
        redisCacheKey="help:route:/mes-espaces/$id/sources:orcia-pack-sdlc:fr"
        mergedLayers={["BASE", "PACK", "WORKSPACE"]}
        rollbackAvailable={true}
        isAdmin={true}
        article={{
          resourceId: "orcia://pack/sdlc/help/fr/spaces-sources",
          uri: "orcia://pack/sdlc/help/fr/spaces-sources@2.0.0",
          title: "Brancher & synchroniser vos Sources (Pack SDLC)",
          version: "2.0.0",
          previousVersion: "1.1.0",
          lang: "fr",
          layer: "PACK",
          packName: "orcia-pack-sdlc",
          boundRoutes: ["/mes-espaces/$id/sources", "/spaces/sources"],
          summaryWhatFor:
            "Configurez les dépôts Git, projets Jira et espaces Confluence pour l'ontologie N1–N4.",
          stepByStepItems: [
            "Connectez votre dépôt Git via un jeton Passthrough.",
            "Lancez l'indexation incrémentale SHA-256.",
          ],
          keyTermsItems: [
            "Passthrough OIDC : jeton individuel utilisateur.",
            "CAS SHA-256 : stockage adressable par le contenu.",
          ],
          faqItems: [
            "Comment forcer une resynchronisation ? Cliquez sur Tester la connexion.",
          ],
          casKey: "cas/aaaa0000aaaa0000",
          sha256: "a".repeat(64),
        }}
        labels={helpLabels}
        onAskAssistantOnScreen={onAskAssistantOnScreen}
        onRollbackVersion={onRollbackVersion}
      />,
    );

    const panel = screen.getByTestId("contextual-help-hybrid-panel");
    expect(panel.getAttribute("data-mode")).toBe("COLUMN_340PX");
    expect(
      screen.getByTestId("contextual-help-merged-layers").textContent,
    ).toContain("Base / Pack / Espace");
    expect(
      screen.getByTestId("contextual-help-what-for-box").textContent,
    ).toContain("À quoi sert cet écran ?");

    // Toggle FAQ accordion (closed by default -> open)
    expect(screen.queryByTestId("help-accordion-faq-content")).toBeNull();
    fireEvent.click(screen.getByTestId("help-accordion-faq-btn"));
    expect(
      screen.getByTestId("help-accordion-faq-content").textContent,
    ).toContain("resynchronisation");

    // 1-click Rollback to @v(N-1) (1.1.0)
    fireEvent.click(screen.getByTestId("contextual-help-rollback-btn"));
    expect(onRollbackVersion).toHaveBeenCalledWith(
      "orcia://pack/sdlc/help/fr/spaces-sources",
    );
    expect(
      screen.getByTestId("contextual-help-version-pill").textContent,
    ).toBe("v1.1.0");
    expect(
      screen.getByTestId("contextual-help-rollback-banner").textContent,
    ).toContain("v1.1.0");

    // Ask Assistant about current screen
    fireEvent.click(screen.getByTestId("contextual-help-ask-assistant-btn"));
    expect(onAskAssistantOnScreen).toHaveBeenCalledWith(
      "/mes-espaces/$id/sources",
      expect.stringContaining("/mes-espaces/$id/sources"),
    );
  });

  it("renders ContextualInfoTriggerButton ('i'), opens controlled FourZoneDirectionCShell help column on click, and highlights activeSectionId in ContextualHelpColumnAndCenter", () => {
    const helpLabels: ContextualHelpColumnAndCenterLabels = {
      columnHeaderTitle: "Aide Contextuelle",
      centerHeaderTitle: "Centre d'Aide",
      whatForSectionTitle: "À quoi sert cet écran ?",
      stepByStepAccordionTitle: "Guide pas-à-pas",
      keyTermsAccordionTitle: "Points clés",
      faqAccordionTitle: "Questions fréquentes",
      askAssistantOnScreenCta: "Poser une question à Mon Assistant",
      rollbackButtonLabel: "Revenir à la version précédente",
      rollbackCompletedPrefix: "Version précédente restaurée :",
      mergedLayersPrefix: "Origine :",
    };

    function ControlledShellHarness() {
      const [helpOpen, setHelpOpen] = React.useState(false);
      const [activeSectionId, setActiveSectionId] = React.useState<string | null>(null);

      return (
        <FourZoneDirectionCShell
          activeMenuKey="configuration"
          activeWorkspaceName="Portail Paiement"
          activePackKey="orcia-pack-sdlc"
          availablePacks={["orcia-pack-sdlc"]}
          userDisplayName="Hélène PM"
          userHatLabel="Product Manager"
          pendingDecisionsTotal={2}
          viewportWidth={1280}
          helpColumnOpen={helpOpen}
          onHelpColumnOpenChange={setHelpOpen}
          onSelectMenu={vi.fn()}
          labels={SHELL_LABELS}
          helpColumnContent={
            <ContextualHelpColumnAndCenter
              mode="COLUMN_340PX"
              route="/settings"
              pack="orcia-pack-sdlc"
              redisCacheKey="help:route:/settings:orcia-pack-sdlc:fr"
              mergedLayers={["BASE"]}
              rollbackAvailable={false}
              isAdmin={true}
              activeSectionId={activeSectionId}
              article={{
                resourceId: "orcia://system/help/fr/settings",
                uri: "orcia://system/help/fr/settings@1.0.0",
                title: "Organisation & Habilitations",
                version: "1.0.0",
                previousVersion: "1.0.0",
                lang: "fr",
                layer: "BASE",
                packName: "orcia-pack-sdlc",
                boundRoutes: ["/settings"],
                summaryWhatFor: "Gérez votre organigramme et les droits d'accès.",
                stepByStepItems: ["Créez une BU puis une Équipe."],
                keyTermsItems: ["6 actions : Créer, Consulter, Modifier, Supprimer, Exécuter, Déléguer."],
                faqItems: ["Comment supprimer une BU ? Retirez d'abord ses équipes."],
                sections: [
                  {
                    sectionId: "iam-org-tree",
                    title: "Organigramme (BU & Équipes)",
                    body: "Structurez vos Directions (BU) et Équipes rattachées.",
                    category: "steps",
                  },
                  {
                    sectionId: "iam-role-grants",
                    title: "Attribution des droits",
                    body: "Attribuez les 6 actions (Créer, Consulter, Modifier, Supprimer, Exécuter, Déléguer).",
                    category: "terms",
                  },
                ],
                casKey: "cas/settings",
                sha256: "b".repeat(64),
              }}
              labels={helpLabels}
            />
          }
        >
          <div>
            <h2>
              Organigramme{" "}
              <ContextualInfoTriggerButton
                sectionId="iam-org-tree"
                label="Voir l'aide sur l'organigramme"
                onOpenHelpSection={(secId) => {
                  setActiveSectionId(secId);
                  setHelpOpen(true);
                }}
              />
            </h2>
          </div>
        </FourZoneDirectionCShell>
      );
    }

    render(<ControlledShellHarness />);

    // Initially closed
    expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();

    // Click the 'i' info trigger button (wireframe SVG)
    const triggerBtn = screen.getByTestId("contextual-info-trigger-iam-org-tree");
    expect(triggerBtn.querySelector("svg")).not.toBeNull();
    expect(triggerBtn.getAttribute("aria-label")).toBe("Voir l'aide sur l'organigramme");
    fireEvent.click(triggerBtn);

    // Right-hand contextual help column is now open and the targeted section is highlighted
    const helpColumn = screen.getByTestId("four-zone-contextual-help-column");
    const centralWorkspace = screen.getByTestId("four-zone-central-workspace");
    expect(helpColumn).toBeDefined();
    expect(centralWorkspace.style.overflowY).toBe("auto");
    expect(helpColumn.style.overflowY).toBe("auto");

    const activeSection = screen.getByTestId("help-section-iam-org-tree");
    expect(activeSection.getAttribute("data-active")).toBe("true");
    expect(activeSection.textContent).toContain("Organigramme (BU & Équipes)");

    const inactiveSection = screen.getByTestId("help-section-iam-role-grants");
    expect(inactiveSection.getAttribute("data-active")).toBe("false");
  });

  it("isolates vertical scrolling between Zone 3 (main workspace) and Zone 4 (contextual help) and pins the activeSectionId triggered via 'i' to the top of the help sections list without scrolling window", () => {
    const helpLabels: ContextualHelpColumnAndCenterLabels = {
      columnHeaderTitle: "Aide Contextuelle",
      centerHeaderTitle: "Centre d'Aide",
      whatForSectionTitle: "À quoi sert cet écran ?",
      stepByStepAccordionTitle: "Guide pas-à-pas",
      keyTermsAccordionTitle: "Points clés",
      faqAccordionTitle: "Questions fréquentes",
      askAssistantOnScreenCta: "Poser une question à Mon Assistant",
      rollbackButtonLabel: "Revenir à la version précédente",
      rollbackCompletedPrefix: "Version précédente restaurée :",
      mergedLayersPrefix: "Origine :",
    };

    const windowScrollSpy = vi.spyOn(window, "scrollTo");

    function PinnedHelpHarness() {
      const [activeSectionId, setActiveSectionId] = React.useState<string | null>(null);
      return (
        <FourZoneDirectionCShell
          activeMenuKey="configuration"
          activeWorkspaceName="Plateforme Globale"
          activePackKey="orcia-core"
          availablePacks={[]}
          userDisplayName="Romain"
          userHatLabel="Administrateur"
          pendingDecisionsTotal={0}
          viewportWidth={1440}
          helpColumnOpen={true}
          onSelectMenu={vi.fn()}
          labels={SHELL_LABELS}
          helpColumnContent={
            <ContextualHelpColumnAndCenter
              mode="COLUMN_340PX"
              route="/settings"
              pack="orcia-core"
              redisCacheKey="help:route:/settings:core:fr"
              mergedLayers={["BASE", "PACK"]}
              activeSectionId={activeSectionId}
              article={{
                resourceId: "help-configuration",
                uri: "orcia://packs/core/help/configuration/fr",
                title: "Configuration",
                version: "1.0.0",
                lang: "fr",
                layer: "PACK",
                packName: "orcia-core",
                boundRoutes: ["/settings"],
                summaryWhatFor: "Paramétrez votre plateforme.",
                stepByStepItems: ["Étape 1"],
                keyTermsItems: ["Terme 1"],
                faqItems: ["FAQ 1"],
                sections: [
                  {
                    sectionId: "iam-org-tree",
                    title: "Structure de l'organisation",
                    body: "Directions et Espaces.",
                    category: "steps",
                  },
                  {
                    sectionId: "ai-models-overview",
                    title: "Modèles IA : Fournisseur & URL API",
                    body: "Configurez et testez vos modèles IA.",
                    category: "steps",
                  },
                  {
                    sectionId: "audit-overview",
                    title: "Journal d'activité",
                    body: "Consultez l'historique.",
                    category: "faq",
                  },
                ],
                casKey: "cas/help_v1",
                sha256: "c".repeat(64),
              }}
              labels={helpLabels}
            />
          }
        >
          <div>
            <ContextualInfoTriggerButton
              sectionId="audit-overview"
              label="Voir l'aide sur le journal d'activité"
              onOpenHelpSection={(secId) => setActiveSectionId(secId)}
            />
          </div>
        </FourZoneDirectionCShell>
      );
    }

    render(<PinnedHelpHarness />);

    const sectionsList = screen.getByTestId("contextual-help-sections-list");
    // Before clicking 'i', sections are in original order: iam-org-tree first, audit-overview last
    expect(sectionsList.children[0]?.getAttribute("data-testid")).toBe(
      "help-section-iam-org-tree",
    );
    expect(sectionsList.children[2]?.getAttribute("data-testid")).toBe(
      "help-section-audit-overview",
    );

    windowScrollSpy.mockClear();

    // Click 'i' for audit-overview (originally at the bottom)
    fireEvent.click(screen.getByTestId("contextual-info-trigger-audit-overview"));

    // 1. audit-overview is now pinned at the very top (index 0) of contextual-help-sections-list with the "Aide ciblée" badge
    expect(sectionsList.children[0]?.getAttribute("data-testid")).toBe(
      "help-section-audit-overview",
    );
    expect(sectionsList.children[0]?.getAttribute("data-active")).toBe("true");
    expect(screen.getByTestId("contextual-help-pinned-active-badge").textContent).toBe(
      "Aide ciblée",
    );

    // 2. Window scroll was NEVER called (main screen never loses its scroll position)
    expect(windowScrollSpy).not.toHaveBeenCalled();
  });

  it("renders DisabledButtonAlertIndicator as non-intrusive accessible sr-only tooltip without red '!' SVG badge when disabled=true", () => {
    const { rerender } = render(
      <OrciaButton
        data-testid="sample-action-btn"
        disabled={true}
        disabledReason="Complétez d'abord les champs obligatoires."
      >
        Valider l'étape
      </OrciaButton>,
    );

    const btn = screen.getByTestId("sample-action-btn") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    const alertIcon = screen.getByTestId("disabled-button-alert-icon-sample-action-btn");
    const alertTooltip = screen.getByTestId("disabled-button-alert-tooltip-sample-action-btn");
    expect(alertIcon.querySelector("svg")).toBeNull();
    expect(alertIcon.className).toContain("sr-only");
    expect(alertIcon.getAttribute("title")).toBe("Complétez d'abord les champs obligatoires.");
    expect(alertTooltip.getAttribute("role")).toBe("tooltip");
    expect(alertTooltip.getAttribute("data-tooltip-text")).toBe(
      "Complétez d'abord les champs obligatoires.",
    );

    // Enable button -> accessible reason and tooltip disappear completely from DOM
    rerender(
      <OrciaButton
        data-testid="sample-action-btn"
        disabled={false}
        disabledReason="Complétez d'abord les champs obligatoires."
      >
        Valider l'étape
      </OrciaButton>,
    );
    expect(btn.disabled).toBe(false);
    expect(screen.queryByTestId("disabled-button-alert-icon-sample-action-btn")).toBeNull();
    expect(screen.queryByTestId("disabled-button-alert-tooltip-sample-action-btn")).toBeNull();
    expect(
      render(<DisabledButtonAlertIndicator disabled={false} reason="Inactif" />).container.firstChild,
    ).toBeNull();
  });

  it("blocks the '[' sidebar rail shortcut while an aria-modal='true' OrciaDialog is open and restores it once closed", () => {
    const { rerender } = render(
      <>
        <FourZoneDirectionCShell
          activeMenuKey="cockpit"
          activeWorkspaceName="Espace Test"
          activePackKey=""
          availablePacks={[]}
          userDisplayName="Alice Admin"
          userHatLabel="Administrateur"
          pendingDecisionsTotal={0}
          viewportWidth={1440}
          labels={SHELL_LABELS}
          onSelectMenu={() => {}}
          onOpenWorkspaceSwitcher={() => {}}
          onOpenSearchCommand={() => {}}
          onSelectPack={() => {}}
        >
          <div>Contenu</div>
        </FourZoneDirectionCShell>
        <OrciaDialog
          open={true}
          onOpenChange={() => {}}
          title="Modale modale ouverte"
          testId="modal-blocking-bracket"
        >
          <div>Corps</div>
        </OrciaDialog>
      </>,
    );

    const sidebar = screen.getByTestId("four-zone-sidebar");
    expect(screen.getByTestId("modal-blocking-bracket").getAttribute("aria-modal")).toBe("true");
    expect(sidebar.getAttribute("data-rail-collapsed")).toBe("false");

    fireEvent.keyDown(window, { key: "[" });
    expect(sidebar.getAttribute("data-rail-collapsed")).toBe("false");

    rerender(
      <>
        <FourZoneDirectionCShell
          activeMenuKey="cockpit"
          activeWorkspaceName="Espace Test"
          activePackKey=""
          availablePacks={[]}
          userDisplayName="Alice Admin"
          userHatLabel="Administrateur"
          pendingDecisionsTotal={0}
          viewportWidth={1440}
          labels={SHELL_LABELS}
          onSelectMenu={() => {}}
          onOpenWorkspaceSwitcher={() => {}}
          onOpenSearchCommand={() => {}}
          onSelectPack={() => {}}
        >
          <div>Contenu</div>
        </FourZoneDirectionCShell>
        <OrciaDialog
          open={false}
          onOpenChange={() => {}}
          title="Modale modale fermée"
          testId="modal-blocking-bracket"
        >
          <div>Corps</div>
        </OrciaDialog>
      </>,
    );

    fireEvent.keyDown(window, { key: "[" });
    expect(sidebar.getAttribute("data-rail-collapsed")).toBe("true");
    fireEvent.keyDown(window, { key: "[" });
    expect(sidebar.getAttribute("data-rail-collapsed")).toBe("false");
    cleanup();
  });
});
