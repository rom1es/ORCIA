import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  AppShell,
  CatalogExplorerPanel,
  FederatedUriBadge,
  HumanLedAnchorCard,
  type UiHumanProfileBadge,
  type UiScopeNode,
  type UiShellLabels,
  type UiShellModuleItem,
} from "../index";

const MOCK_LABELS: UiShellLabels = {
  brandTitle: "ORCIA",
  brandSubtitle: "",
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
    bootstrap: "Initialisation & Onboarding",
  },
  staleWarningBadgeLabel: "! [STALE_WARNING]",
  humanProfilePrefixLabel: "Profil Humain",
  assistantDockTitle: "Agent Assistant & Permission Broker",
  assistantDockSubtitle: "Co-présence gouvernée (Passthrough)",
  assistantDockToggleExpandLabel: "Déplier le Dock Assistant",
  assistantDockToggleCollapseLabel: "Replier le Dock Assistant",
  assistantPermissionBrokerReadyLabel: "Permission Broker actif",
  assistantInputPlaceholder: "Interroger l'Assistant ou diagnostiquer un refus 403...",
  assistantSendLabel: "Envoyer",
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
  { key: "bootstrap", order: 8, route: "/bootstrap", icon: "rocket", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
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

describe("AppShell, GlobalSidebar, ScopeSwitcher, AssistantDock & HumanLedAnchorCard", () => {
  it("renders the 3 columns, 7 Global Sidebar modules, and toggles sidebar/dock/scope via keyboard shortcuts", () => {
    const onSelectModule = vi.fn();
    const onSelectScope = vi.fn();
    const onSubmitAssistantPrompt = vi.fn();

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
        onSubmitAssistantPrompt={onSubmitAssistantPrompt}
      >
        <div data-testid="child-canvas">Contenu Central</div>
      </AppShell>,
    );

    const appShell = screen.getByTestId("orcia-app-shell");
    const sidebar = screen.getByTestId("global-sidebar");
    const dock = screen.getByTestId("assistant-dock");
    expect(sidebar.getAttribute("data-collapsed")).toBe("false");
    expect(dock.getAttribute("data-collapsed")).toBe("false");
    expect(appShell.getAttribute("data-active-mobile-tab")).toBe("inbox");
    expect(screen.getByTestId("topbar-search-input")).toBeDefined();
    expect(screen.getByTestId("sidebar-collapse-toggle").textContent).toBe("«");
    expect(screen.getByTestId("assistant-dock-toggle").textContent).toBe("»");

    for (const mod of MOCK_MODULES) {
      expect(screen.getByTestId(`sidebar-nav-item-${mod.key}`)).toBeDefined();
    }
    fireEvent.click(screen.getByTestId("sidebar-nav-item-inbox"));
    expect(onSelectModule).toHaveBeenCalledWith("inbox", "/inbox");

    fireEvent.keyDown(window, { key: "[" });
    expect(sidebar.getAttribute("data-collapsed")).toBe("true");
    expect(screen.getByTestId("sidebar-collapse-toggle").textContent).toBe("»");

    fireEvent.keyDown(window, { key: "]" });
    expect(dock.getAttribute("data-collapsed")).toBe("true");
    expect(screen.getByTestId("assistant-dock-toggle").textContent).toBe("«");

    fireEvent.click(screen.getByTestId("assistant-dock-toggle"));
    expect(dock.getAttribute("data-collapsed")).toBe("false");

    const promptInput = screen.getByTestId("assistant-prompt-input") as HTMLInputElement;
    promptInput.focus();
    fireEvent.keyDown(promptInput, { key: "[" });
    fireEvent.keyDown(promptInput, { key: "]" });
    expect(sidebar.getAttribute("data-collapsed")).toBe("true");
    expect(dock.getAttribute("data-collapsed")).toBe("false");

    fireEvent.change(promptInput, { target: { value: "  Diagnostiquer refus 403  " } });
    fireEvent.click(screen.getByTestId("assistant-prompt-submit"));
    expect(onSubmitAssistantPrompt).toHaveBeenCalledWith("Diagnostiquer refus 403");
    expect(promptInput.value).toBe("");

    fireEvent.keyDown(window, { key: "w", ctrlKey: true });
    expect(screen.getByTestId("scope-switcher-dialog")).toBeDefined();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("scope-switcher-dialog")).toBeNull();

    fireEvent.keyDown(window, { key: "w", ctrlKey: true });
    fireEvent.click(screen.getByTestId("scope-option-scope-global"));
    expect(onSelectScope).toHaveBeenCalledWith("scope-global");

    const chatMobileTab = screen.getByTestId("mobile-tab-chat");
    fireEvent.click(chatMobileTab);
    expect(chatMobileTab.getAttribute("data-active")).toBe("true");
    expect(appShell.getAttribute("data-active-mobile-tab")).toBe("chat");

    // Verify Top Bar User Profile Dropdown, Dark Mode switch, and Escape close
    fireEvent.click(screen.getByTestId("user-profile-dropdown-trigger"));
    expect(screen.getByTestId("user-profile-dropdown-menu")).toBeDefined();

    fireEvent.click(screen.getByTestId("dark-mode-toggle-switch"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    fireEvent.click(screen.getByTestId("dark-mode-toggle-switch"));
    expect(document.documentElement.getAttribute("data-theme")).toBeNull();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("user-profile-dropdown-menu")).toBeNull();
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

  it("hides disabled modules (enabled: false) in GlobalSidebar and displays role/orgUnitName in footer", () => {
    render(
      <AppShell
        modules={MOCK_MODULES.map((m) => (m.key === "admin" ? { ...m, enabled: false } : m))}
        activeModuleKey="cockpit"
        scopes={MOCK_SCOPES}
        activeScopeId="scope-ws-orcia"
        humanProfile={{
          ...MOCK_PROFILE,
          role: "CONTRIBUTOR",
          orgUnitName: "Sous-Équipe Checkout",
        }}
        labels={MOCK_LABELS}
        currentLocale="fr"
        onSelectModule={vi.fn()}
        onSelectScope={vi.fn()}
      >
        <div>Contenu</div>
      </AppShell>,
    );

    expect(screen.queryByTestId("sidebar-nav-item-admin")).toBeNull();
    expect(screen.getByTestId("sidebar-human-profile-org").textContent).toContain(
      "CONTRIBUTOR · Sous-Équipe Checkout",
    );
  });

  it("renders FederatedUriBadge (UX-DR8) and CatalogExplorerPanel with CAS resolution, promotion, and BMAD import", () => {
    render(
      <div>
        <FederatedUriBadge
          uri="git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0"
          scheme="git"
          sha256Short="8a91c4e2f01b"
          grantedPermissions={["DISCOVER", "EXECUTE"]}
          sourceMasked={true}
          maskedSourceLabel="🔒 Source masquée"
          openSourceLabel="📖 Source ouverte"
        />
        <CatalogExplorerPanel
          activePersona="marc"
          items={[
            {
              resourceId: "res-jira-secops-playbook",
              uri: "jira://PAYSEC/PAYSEC-101",
              scheme: "jira",
              title: "Playbook SecOps",
              description: "Playbook brouillon",
              resourceType: "workflow",
              sourceFormat: "ORCIA",
              version: "v0.1.0",
              sha256Short: "1d83f5a0e72c",
              casKey: "cas/1d83f5a0e72c",
              visibilityScope: "DRAFT",
              grantedPermissions: ["DISCOVER", "EXECUTE", "READ_SOURCE", "EDIT", "ADMIN"],
              sourceMasked: false,
            },
            {
              resourceId: "res-blackbox-security-agent",
              uri: "git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0",
              scheme: "git",
              title: "Agent Boîte Noire",
              description: "Agent masqué",
              resourceType: "agent",
              sourceFormat: "ORCIA",
              version: "v2.1.0",
              sha256Short: "8a91c4e2f01b",
              casKey: "cas/8a91c4e2f01b",
              visibilityScope: "SHARED_TEAM",
              grantedPermissions: ["DISCOVER", "EXECUTE"],
              sourceMasked: true,
            },
          ]}
          runLockTriplets={[
            {
              alias: "workflow-definition",
              scheme: "db",
              uri: "db://orcia/catalog/payment-delivery-workflow@v1.2.0",
              resolvedVersion: "v1.2.0",
              sha256Short: "3c18b7e9d04a",
            },
          ]}
          labels={{
            panelTitle: "Catalogue Fédéré",
            panelSubtitle: "Sous-titre",
            filterAllSchemesLabel: "Tous",
            maskedSourceBadgeLabel: "🔒 Source masquée",
            openSourceBadgeLabel: "📖 Source ouverte",
            resolveCasButtonLabel: "Résoudre CAS",
            casResolvedBannerPrefix: "HTTP 200 OK",
            promoteScopeButtonLabel: "Promouvoir",
            promotedBannerPrefix: "Promu",
            promoteDeniedObserverBanner: "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY",
            overrideSectionTitle: "Surcharges 4 Niveaux",
            overrideSectionSubtitle: "Base -> Team -> Workspace -> User",
            overrideLayers: {
              base: "1. Base",
              teamParent: "2a. Parent",
              teamSub: "2b. Sub",
              workspace: "3. Workspace",
              user: "4. User",
            },
            runLockTitle: "run-lock.json",
            bmadAdapterTitle: "BMAD Adapter",
            bmadImportButtonLabel: "Importer BMAD",
            bmadImportedBanner: "BMAD_PACK importé",
          }}
        />
      </div>,
    );

    const badge = screen.getByTestId("uri-badge");
    expect(badge.getAttribute("data-uri-scheme")).toBe("git");
    expect(badge.getAttribute("data-source-masked")).toBe("true");
    expect(screen.getByTestId("catalog-scheme-filter-orcia")).toBeDefined();

    // Verify promote button is disabled on item without EDIT/ADMIN for non-admin persona
    const maskedPromoteBtn = screen.getByTestId(
      "promote-btn-res-blackbox-security-agent",
    ) as HTMLButtonElement;
    expect(maskedPromoteBtn.disabled).toBe(true);

    // Filter by scheme jira -> hides git item; filter ALL -> shows both
    fireEvent.click(screen.getByTestId("catalog-scheme-filter-jira"));
    expect(screen.getByTestId("catalog-item-card-res-jira-secops-playbook")).toBeDefined();
    expect(screen.queryByTestId("catalog-item-card-res-blackbox-security-agent")).toBeNull();

    fireEvent.click(screen.getByTestId("catalog-scheme-filter-ALL"));
    expect(screen.getByTestId("catalog-item-card-res-blackbox-security-agent")).toBeDefined();

    fireEvent.click(screen.getByTestId("resolve-cas-btn-res-jira-secops-playbook"));
    expect(
      screen.getByTestId("resolve-cas-result-res-jira-secops-playbook").textContent,
    ).toContain("cas/1d83f5a0e72c");

    fireEvent.click(screen.getByTestId("promote-btn-res-jira-secops-playbook"));
    expect(screen.getByTestId("promote-result-res-jira-secops-playbook").textContent).toContain(
      "DRAFT -> SHARED_WORKSPACE",
    );

    fireEvent.click(screen.getByTestId("bmad-import-trigger-btn"));
    expect(screen.getByTestId("bmad-import-result").textContent).toContain("BMAD_PACK");
  });

  it("auto-expands AssistantDock and renders PermissionBrokerCard (UX-DR11) on PERMISSION_DENIED_STEP", () => {
    const onPause = vi.fn();
    const onReplay = vi.fn();

    render(
      <AppShell
        modules={MOCK_MODULES}
        activeModuleKey="gates"
        scopes={MOCK_SCOPES}
        activeScopeId="scope-ws-orcia"
        humanProfile={MOCK_PROFILE}
        labels={MOCK_LABELS}
        currentLocale="fr"
        defaultDockCollapsed={true}
        permissionBrokerTicket={{
          id: "tkt-1101",
          ticketKey: "tkt-perm-step-02-git",
          stepKey: "step-02-execution",
          stepNumber: 2,
          stepState: "PERMISSION_DENIED_STEP",
          status: "WAITING_FOR_PERMISSION",
          targetUri: "git://github.enterprise/payments/checkout-core.git",
          connectorScheme: "git",
          executionIdentity: "passthrough",
          upstreamHttpStatus: 403,
          requiredRole: "ROLE_GIT_PAYMENTS_MAINTAINER",
          approverTeam: "SecOps & Core Payments IAM",
          slaHours: 4,
          jiraRequestUrl:
            "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10420&summary=test",
          permissionBrokerHint: "jira://IAM/ROLE_GIT_PAYMENTS_MAINTAINER",
        }}
        permissionBrokerLabels={{
          cardBadgeTitle: "⚠️ PERMISSION BROKER",
          passthroughBadgeLabel: "Identité : passthrough",
          servicePrincipalBadgeLabel: "Identité : service_principal",
          targetUriLabel: "Source externe bloquée",
          requiredRoleLabel: "Rôle requis",
          approverTeamLabel: "Équipe approbatrice",
          slaHoursPrefix: "SLA",
          rfcHintLabel: "Indice RFC 9457",
          jiraRequestButtonLabel: "Demander l'accès dans Atlassian Jira",
          pauseStepButtonLabel: "Mettre en pause",
          replayStepButtonLabel: "Rejouer l'étape",
          pausedStateBanner: "⏸️ En pause",
          replayedStateBanner: "✅ Rejouée",
          simulatorTitle: "Simulateur",
          simulatorSubtitle: "Sous-titre",
          simulateGitDenialLabel: "Simuler Git",
          simulateConfluenceDenialLabel: "Simuler Confluence",
          simulateJiraDenialLabel: "Simuler Jira",
          simulateConfusedDeputyLabel: "Tester Service Principal",
          confusedDeputyBlockedBanner: "ERR_CONFUSED_DEPUTY_BLOCKED",
          observerDeniedBanner: "ERR_OBSERVER_MODE_READ_ONLY",
        }}
        onSelectModule={vi.fn()}
        onSelectScope={vi.fn()}
        onPausePermissionStep={onPause}
        onReplayPermissionStep={onReplay}
      >
        <div>Gates Content</div>
      </AppShell>,
    );

    const dock = screen.getByTestId("assistant-dock");
    expect(dock.getAttribute("data-collapsed")).toBe("false");

    const card = screen.getByTestId("permission-broker-card");
    expect(card.getAttribute("data-step-state")).toBe("PERMISSION_DENIED_STEP");
    expect(card.getAttribute("data-execution-identity")).toBe("passthrough");
    expect(screen.getByTestId("permission-broker-required-role").textContent).toBe(
      "ROLE_GIT_PAYMENTS_MAINTAINER",
    );
    expect(screen.getByTestId("permission-broker-approver-team").textContent).toBe(
      "SecOps & Core Payments IAM",
    );
    expect(screen.getByTestId("permission-broker-jira-link").getAttribute("href")).toContain(
      "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa",
    );

    fireEvent.click(screen.getByTestId("permission-broker-pause-btn"));
    expect(onPause).toHaveBeenCalledWith("tkt-1101");

    fireEvent.click(screen.getByTestId("permission-broker-replay-btn"));
    expect(onReplay).toHaveBeenCalledWith("tkt-1101");
  });
});
