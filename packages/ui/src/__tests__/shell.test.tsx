import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  AppShell,
  HumanLedAnchorCard,
  type UiHumanProfileBadge,
  type UiScopeNode,
  type UiShellLabels,
  type UiShellModuleItem,
} from "../index";

const MOCK_LABELS: UiShellLabels = {
  brandTitle: "ORCIA",
  brandSubtitle: "Cockpit Obsidienne & Studio Jour",
  sidebarNavigationAriaLabel: "Navigation Globale à 7 Modules",
  sidebarToggleExpandLabel: "Déplier le menu latéral",
  sidebarToggleCollapseLabel: "Replier le menu latéral",
  scopeSwitcherButtonLabel: "Sélecteur de périmètre",
  scopeSwitcherDialogTitle: "Sélecteur de Périmètre Hiérarchique (⌘W)",
  scopeSwitcherCloseLabel: "Fermer",
  scopeLevels: {
    GLOBAL: "Plateforme Globale",
    BU: "BU / Tribu",
    TEAM: "Équipe",
    WORKSPACE: "Workspace Solution",
  },
  accessModes: {
    CONTRIBUTOR_ACTION_REQUIRED: "Contributeur (Action requise)",
    READ_ONLY_OBSERVER: "Consultation seule (Observateur)",
  },
  modules: {
    cockpit: "Cockpit & Chat",
    inbox: "Boîte & Mes Runs",
    catalog: "Catalogue Fédéré",
    ontology: "Ontologie & KB",
    gates: "Gates & Habilitations",
    finops: "FinOps & Audit",
    admin: "Administration & Pilotage des Workspaces",
  },
  staleWarningBadgeLabel: "! [STALE_WARNING]",
  humanProfilePrefixLabel: "Profil Humain",
  conciergeDockTitle: "Agent Concierge & Permission Broker",
  conciergeDockSubtitle: "Co-présence gouvernée (Passthrough)",
  conciergeDockToggleExpandLabel: "Déplier le Dock Concierge",
  conciergeDockToggleCollapseLabel: "Replier le Dock Concierge",
  conciergePermissionBrokerReadyLabel: "Permission Broker actif",
  conciergeInputPlaceholder: "Interroger le Concierge ou diagnostiquer un refus 403...",
  conciergeSendLabel: "Envoyer",
  localeSwitchLabel: "Langue",
  mobileTabs: {
    inbox: "🔔 Inbox",
    chat: "💬 Arbitrage/Chat",
    briefing: "📄 Briefing",
  },
};

const MOCK_MODULES: UiShellModuleItem[] = [
  { key: "cockpit", order: 1, route: "/cockpit", icon: "message", contributorBadgeCount: 1, hasStaleWarning: false, enabled: true },
  { key: "inbox", order: 2, route: "/inbox", icon: "bell", contributorBadgeCount: 2, hasStaleWarning: false, enabled: true },
  { key: "catalog", order: 3, route: "/catalog", icon: "package", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "ontology", order: 4, route: "/ontology", icon: "dna", contributorBadgeCount: 0, hasStaleWarning: true, enabled: true },
  { key: "gates", order: 5, route: "/gates", icon: "shield", contributorBadgeCount: 1, hasStaleWarning: false, enabled: true },
  { key: "finops", order: 6, route: "/finops", icon: "chart", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "admin", order: 7, route: "/workspaces", icon: "settings", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
];

const MOCK_SCOPES: UiScopeNode[] = [
  { id: "scope-global", level: "GLOBAL", name: "Plateforme Globale ORCIA", accessMode: "READ_ONLY_OBSERVER" },
  { id: "scope-bu-digital", level: "BU", name: "BU Produits & Plateformes", parentId: "scope-global", accessMode: "READ_ONLY_OBSERVER" },
  { id: "scope-team-core", level: "TEAM", name: "Équipe Architecture", parentId: "scope-bu-digital", accessMode: "CONTRIBUTOR_ACTION_REQUIRED" },
  { id: "scope-ws-orcia", level: "WORKSPACE", name: "Workspace Solution ORCIA Core", parentId: "scope-team-core", accessMode: "CONTRIBUTOR_ACTION_REQUIRED" },
];

const MOCK_PROFILE: UiHumanProfileBadge = {
  archetypeKey: "TECH_LEAD",
  displayName: "Tech Lead / Architecte",
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
};

describe("AppShell, GlobalSidebar, ScopeSwitcher, ConciergeDock & HumanLedAnchorCard", () => {
  it("renders the 3 columns, 7 Global Sidebar modules, and toggles sidebar/dock/scope via keyboard shortcuts", () => {
    const onSelectModule = vi.fn();
    const onSelectScope = vi.fn();
    const onSubmitConciergePrompt = vi.fn();

    render(
      <AppShell
        modules={MOCK_MODULES}
        activeModuleKey="cockpit"
        scopes={MOCK_SCOPES}
        activeScopeId="scope-ws-orcia"
        humanProfile={MOCK_PROFILE}
        labels={MOCK_LABELS}
        currentLocale="fr"
        onSelectModule={onSelectModule}
        onSelectScope={onSelectScope}
        onSubmitConciergePrompt={onSubmitConciergePrompt}
      >
        <div data-testid="child-canvas">Contenu Central</div>
      </AppShell>,
    );

    const appShell = screen.getByTestId("orcia-app-shell");
    const sidebar = screen.getByTestId("global-sidebar");
    const dock = screen.getByTestId("concierge-dock");
    expect(sidebar.getAttribute("data-collapsed")).toBe("false");
    expect(dock.getAttribute("data-collapsed")).toBe("false");
    expect(appShell.getAttribute("data-active-mobile-tab")).toBe("inbox");

    // Verify all 7 modules render and clicking a module invokes onSelectModule
    for (const mod of MOCK_MODULES) {
      expect(screen.getByTestId(`sidebar-nav-item-${mod.key}`)).toBeDefined();
    }
    fireEvent.click(screen.getByTestId("sidebar-nav-item-inbox"));
    expect(onSelectModule).toHaveBeenCalledWith("inbox", "/inbox");

    // Press '[' to collapse sidebar (235px -> 68px)
    fireEvent.keyDown(window, { key: "[" });
    expect(sidebar.getAttribute("data-collapsed")).toBe("true");

    // Press ']' to collapse Concierge Dock
    fireEvent.keyDown(window, { key: "]" });
    expect(dock.getAttribute("data-collapsed")).toBe("true");

    // Uncollapse dock via button so input is visible
    fireEvent.click(screen.getByTestId("concierge-dock-toggle"));
    expect(dock.getAttribute("data-collapsed")).toBe("false");

    // When focus is inside an input field, '[' and ']' must be ignored
    const promptInput = screen.getByTestId("concierge-prompt-input") as HTMLInputElement;
    promptInput.focus();
    fireEvent.keyDown(promptInput, { key: "[" });
    fireEvent.keyDown(promptInput, { key: "]" });
    expect(sidebar.getAttribute("data-collapsed")).toBe("true");
    expect(dock.getAttribute("data-collapsed")).toBe("false");

    // Submitting a prompt in ConciergeDock invokes onSubmitConciergePrompt with trimmed text and clears input
    fireEvent.change(promptInput, { target: { value: "  Diagnostiquer refus 403  " } });
    fireEvent.click(screen.getByTestId("concierge-prompt-submit"));
    expect(onSubmitConciergePrompt).toHaveBeenCalledWith("Diagnostiquer refus 403");
    expect(promptInput.value).toBe("");

    // Press Ctrl+W / Meta+W (⌘W) to open Hierarchical Scope Switcher, then Escape to close it
    fireEvent.keyDown(window, { key: "w", ctrlKey: true });
    expect(screen.getByTestId("scope-switcher-dialog")).toBeDefined();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("scope-switcher-dialog")).toBeNull();

    // Reopen Scope Switcher and select a scope
    fireEvent.keyDown(window, { key: "w", ctrlKey: true });
    fireEvent.click(screen.getByTestId("scope-option-scope-global"));
    expect(onSelectScope).toHaveBeenCalledWith("scope-global");

    // Clicking a mobile tab updates active mobile tab state
    const chatMobileTab = screen.getByTestId("mobile-tab-chat");
    fireEvent.click(chatMobileTab);
    expect(chatMobileTab.getAttribute("data-active")).toBe("true");
    expect(appShell.getAttribute("data-active-mobile-tab")).toBe("chat");
  });

  it("renders HumanLedAnchorCard with mandatory human authoring attributes and no AI auto-fill", () => {
    const onSign = vi.fn();
    render(
      <HumanLedAnchorCard
        sectionKey="vision"
        sectionTitle="Hypothèses Structurantes"
        authorName="Camille Tech Lead"
        value="Architecture Hexagonale Stricte"
        labels={{
          badgeTitle: "✍️ ANCRAGE HUMAIN OBLIGATOIRE (human_authored_required: true)",
          authorLabel: "Auteur humain",
          placeholderText: "Rédigez votre ancrage humain...",
          submitLabel: "Signer l'ancrage humain",
        }}
        onSignAnchor={onSign}
      />,
    );

    const card = screen.getByTestId("human-anchor-card-vision");
    expect(card.getAttribute("data-human-authored-required")).toBe("true");
    fireEvent.click(screen.getByText("Signer l'ancrage humain"));
    expect(onSign).toHaveBeenCalledWith("vision", "Architecture Hexagonale Stricte");
  });
});
