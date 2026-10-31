import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  computeDefaultHelpColumnOpen,
  DEFAULT_EIGHT_FIXED_MENU_ENTRIES,
  FourZoneDirectionCShell,
  type FourZoneDirectionCShellLabels,
  ProgressiveDay0AccostageBanner,
  type ProgressiveDay0AccostageLabels,
  StreamlinedCockpitView,
  type StreamlinedCockpitLabels,
  TopHeaderSearchCommand,
  type TopHeaderSearchCommandLabels,
  UserAccountDropdownAndSettingsModal,
  type UserAccountDropdownAndSettingsLabels,
} from "../index";

const SHELL_LABELS: FourZoneDirectionCShellLabels = {
  workspacePrefix: "Espace",
  searchTriggerPlaceholder: "Rechercher dans cet Espace ou partout (⌘K)...",
  contextualHelpButtonLabel: "? Aide",
  notificationsButtonLabel: "🔔 Notifications",
  notificationsDrawerTitle: "Centre de Notifications (420px)",
  notificationsEmptyText: "Aucune notification non lue.",
  sidebarAriaLabel: "Navigation principale à 8 entrées sans numéro",
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
    finops: "FinOps",
    configuration: "Configuration",
    help: "Aide",
  },
};

const COCKPIT_LABELS: StreamlinedCockpitLabels = {
  zeroDecisionsBanner: "✅ Aucune décision en attente",
  quickAssistantTitle: "Accès rapide à Mon Assistant",
  quickAssistantPlaceholder: "Posez une question ou préparez un dossier...",
  quickAssistantCta: "Ouvrir Mon Assistant →",
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

    // Zone 1: TopHeaderBar (52px) with fixed "Espace : [Nom] ⌄" selector, ⌘K, ? Aide, 🔔 Notifications (420px), 👤 Login + Hat
    const topbar = screen.getByTestId("four-zone-top-header-bar");
    expect(topbar.style.height).toBe("52px");
    const wsBtn = screen.getByTestId("topbar-fixed-workspace-selector");
    expect(wsBtn.textContent).toContain("Espace : Portail Paiement");
    fireEvent.click(wsBtn);
    expect(onOpenWorkspaceSwitcher).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId("topbar-federated-search-trigger"));
    expect(onOpenSearchCommand).toHaveBeenCalledTimes(1);

    expect(screen.getByTestId("topbar-hat-badge").textContent).toBe("Product Manager");

    // Notifications 420px drawer toggle
    expect(screen.queryByTestId("topbar-notifications-drawer")).toBeNull();
    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    const notifDrawer = screen.getByTestId("topbar-notifications-drawer");
    expect(notifDrawer.style.width).toBe("420px");

    // Zone 2: Sidebar (240px / 68px Rail via '[') with exactly 8 unnumbered entries
    const sidebar = screen.getByTestId("four-zone-sidebar");
    expect(sidebar.style.width).toBe("240px");
    expect(DEFAULT_EIGHT_FIXED_MENU_ENTRIES).toHaveLength(8);
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

    // When total == 0: KPI counters (0/0/0/0) and filter bar are hidden!
    expect(screen.queryByTestId("cockpit-kpi-counters-grid")).toBeNull();
    expect(screen.queryByTestId("cockpit-decisions-filter-bar")).toBeNull();
    expect(screen.getByTestId("cockpit-zero-decisions-banner").textContent).toContain(
      "✅ Aucune décision en attente",
    );
    expect(screen.getByTestId("cockpit-quick-assistant-box")).toBeDefined();
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

  it("Story 9.2 — enforces ORCIA_BOOTSTRAP_TOKEN when ORCIA_ENV != local and unlocks Quick Trial Mode (1 model) then AD-10 Gates (>= 2 families)", () => {
    const accostageLabels: ProgressiveDay0AccostageLabels = {
      bannerTitle: "Parcours d'Accostage Progressif Jour 0",
      welcomeWizardTitle: "Assistant de Bienvenue (/welcome-setup)",
      step1AdminTitle: "Étape 1 : Premier Administrateur (LOCK TABLE users)",
      step2LlmTitle: "Étape 2 : Modèles IA Progressifs",
      step3SpaceTitle: "Étape 3 : Jalons d'Accostage 1/6",
      bootstrapTokenLabel: "Jeton d'amorçage ORCIA_BOOTSTRAP_TOKEN",
      bootstrapTokenPlaceholder: "Saisissez ORCIA_BOOTSTRAP_TOKEN...",
      bootstrapTokenDeniedBanner:
        "HTTP 403 ERR_INVALID_BOOTSTRAP_TOKEN — Jeton d'amorçage invalide",
      createFirstAdminCta: "Créer le compte PLATFORM_ADMIN",
      addFirstModelCta: "+ Configurer 1er modèle",
      addSecondModelFamilyCta: "+ Ajouter 2e famille orthogonale",
      singleFamilyAmberWarning:
        "⚠️ 1 seule famille de modèles configurée — Ajoutez une 2e famille dans Configuration › Modèles IA pour activer les Gates Agentiques AD-10",
      dualFamilyAd10UnlockedBadge:
        "✅ ≥ 2 familles orthogonales actives — Gates Agentiques AD-10 débloquées",
      assistantTrialReadyBadge:
        "🚀 Mode Essai Rapide actif : Mon Assistant & Cockpit débloqués",
    };

    render(
      <ProgressiveDay0AccostageBanner
        completedCount={1}
        orciaEnv="staging"
        milestones={[
          {
            index: 1,
            key: "first-admin",
            title: "1. Compte Administrateur Initial",
            completed: true,
            targetRoute: "/welcome-setup",
          },
        ]}
        labels={accostageLabels}
      />,
    );

    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("Accostage 1/6");

    // Submitting without bootstrap token on staging -> 403 ERR_INVALID_BOOTSTRAP_TOKEN
    fireEvent.click(screen.getByTestId("welcome-setup-submit-admin-btn"));
    expect(screen.getByTestId("welcome-setup-token-denied-banner").textContent).toContain(
      "ERR_INVALID_BOOTSTRAP_TOKEN",
    );

    // Provide token -> creates admin under LOCK TABLE users IN EXCLUSIVE MODE
    fireEvent.change(screen.getByTestId("welcome-setup-bootstrap-token-input"), {
      target: { value: "valid-boot-tok" },
    });
    fireEvent.click(screen.getByTestId("welcome-setup-submit-admin-btn"));
    expect(screen.getByTestId("welcome-setup-admin-created-badge").textContent).toContain(
      "LOCK TABLE users IN EXCLUSIVE MODE",
    );

    // Add 1st LLM model -> Quick Trial Mode with amber warning badge
    fireEvent.click(screen.getByTestId("welcome-setup-add-first-llm-btn"));
    expect(screen.getByTestId("accostage-single-family-amber-badge").textContent).toContain(
      "⚠️ 1 seule famille de modèles configurée",
    );
    expect(screen.getByTestId("welcome-setup-assistant-trial-ready")).toBeDefined();

    // Add 2nd distinct LLM family -> AD-10 Agentic Gates unlocked!
    fireEvent.click(screen.getByTestId("welcome-setup-add-second-llm-btn"));
    expect(screen.queryByTestId("accostage-single-family-amber-badge")).toBeNull();
    expect(screen.getByTestId("accostage-dual-family-ad10-badge").textContent).toContain(
      "AD-10",
    );
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

  it("Story 9.4 — opens UserAccountDropdown (280px), persists 0ms Anti-FOUC localStorage, auto-closes dropdown when opening UserSettingsModal (720px, 4 tabs), and manages pat_mcp_* tokens", () => {
    const accountLabels: UserAccountDropdownAndSettingsLabels = {
      triggerAriaLabel: "Ouvrir le menu rapide du compte (280px)",
      dropdownWidthNote: "280px",
      hatSelectorLabel: "Casquette métier",
      themeQuickToggleLabel: "🌓 Apparence (0 ms)",
      localeQuickToggleLabel: "🌐 Langue (0 ms)",
      openAccountSettingsLabel: "⚙️ Paramètres de mon compte...",
      openPassthroughSourcesLabel: "🔗 Mes accès aux sources...",
      logoutButtonLabel: "🚪 Se déconnecter",
      modalTitle: "⚙️ Paramètres de mon compte (720px × max 600px)",
      tab1PreferencesTitle: "🎨 Préférences & Affichage",
      tab2SecurityTitle: "👤 Profil & Sécurité",
      tab3PassthroughTitle: "🔗 Accès aux sources (Passthrough)",
      tab4McpKeysTitle: "💻 Clés IDE & MCP",
      customizeAssistantRedirectCta:
        "💬 Personnaliser le comportement de Mon Assistant →",
      testPassthroughTokenCta: "🔌 Tester mon jeton",
      generateMcpTokenCta: "+ Générer un jeton MCP scopé (pat_mcp_*)",
      revokeMcpTokenCta: "Révoquer (< 10 ms)",
      targetWholeSpaceLabel: "Tout l'Espace (/api/v1/mcp/spaces/<ws_slug>)",
      targetSingleAgentLabel: "Un agent précis (/api/v1/mcp/agents/<agent_slug>)",
      ideJsonReadyTitle: "Extrait JSON prêt à copier",
    };

    const onPreferencesSync = vi.fn();
    const onLogout = vi.fn();
    const onNavigateAssistantBehavior = vi.fn();

    render(
      <UserAccountDropdownAndSettingsModal
        userDisplayName="Hélène"
        userEmail="helene@orcia.local"
        userRole="CONTRIBUTOR"
        labels={accountLabels}
        onPreferencesSync={onPreferencesSync}
        onLogout={onLogout}
        onNavigateAssistantBehavior={onNavigateAssistantBehavior}
      />,
    );

    // 1. Open UserAccountDropdown (280px)
    fireEvent.click(screen.getByTestId("user-account-dropdown-trigger"));
    expect(screen.getByTestId("user-account-dropdown-menu")).toBeDefined();

    // 2. 1-click theme switch writes 0ms to documentElement/localStorage ("orcia_theme") + triggers PATCH sync
    fireEvent.click(screen.getByTestId("dropdown-quick-theme-switch"));
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(onPreferencesSync).toHaveBeenCalledWith({ theme: "dark" });

    // 3. Clicking "⚙️ Paramètres de mon compte..." automatically closes UserAccountDropdown and opens UserSettingsModal (720px)
    fireEvent.click(screen.getByTestId("dropdown-open-settings-modal-btn"));
    expect(screen.queryByTestId("user-account-dropdown-menu")).toBeNull();
    expect(screen.getByTestId("user-settings-modal")).toBeDefined();

    // Tab 1 redirect link to Mon Assistant behavior
    fireEvent.click(screen.getByTestId("user-settings-assistant-redirect-link"));
    expect(onNavigateAssistantBehavior).toHaveBeenCalledWith(
      "/assistant?modal=settings",
    );

    // Switch to Tab 4 (💻 Clés IDE & MCP), select AGENT target, generate pat_mcp_* token and revoke it
    fireEvent.click(screen.getByTestId("user-settings-tab-IDE_MCP_KEYS"));
    fireEvent.change(screen.getByTestId("mcp-target-kind-select"), {
      target: { value: "AGENT" },
    });
    fireEvent.change(screen.getByTestId("mcp-target-slug-input"), {
      target: { value: "sdlc-spec-agent" },
    });
    fireEvent.click(screen.getByTestId("mcp-generate-token-btn"));
    expect(screen.getByTestId("mcp-issued-plaintext-banner").textContent).toContain(
      "pat_mcp_",
    );
    expect(screen.getByTestId("mcp-ide-snippet-mcp-tok-1").textContent).toContain(
      "/api/v1/mcp/agents/sdlc-spec-agent",
    );

    fireEvent.click(screen.getByTestId("mcp-revoke-btn-mcp-tok-1"));
    expect(screen.getByTestId("mcp-token-revoked-badge-mcp-tok-1")).toBeDefined();
  });
});
