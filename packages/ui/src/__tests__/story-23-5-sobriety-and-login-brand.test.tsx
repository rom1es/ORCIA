import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  BiModeLoginView,
  FourZoneDirectionCShell,
  StreamlinedCockpitView,
  type FourZoneDirectionCShellLabels,
  type StreamlinedCockpitLabels,
} from "../index";
import { FourZoneSidebarRail } from "../primitives/FourZoneSidebarRail";
import { FourZoneTopHeaderSection } from "../primitives/FourZoneTopHeaderSection";

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

afterEach(() => {
  cleanup();
});

describe("Story 23.5 — Brand ORCIA in Sidebar/Login, TopHeaderBar sobriety & Cockpit orientation cards", () => {
  it("renders login-brand-header and OrciaPasswordInput (maskMode='password', show/hide toggle) in BiModeLoginView", () => {
    render(
      <BiModeLoginView
        authMode="LOCAL"
        labels={{
          title: "Connexion ORCIA",
          subtitle: "Accès sécurisé",
          primarySsoCta: "SSO",
          localAccordionToggle: "Connexion locale",
          emailLabel: "Adresse e-mail",
          passwordLabel: "Mot de passe", // pragma: allowlist secret
          showPasswordLabel: "Afficher le mot de passe", // pragma: allowlist secret
          hidePasswordLabel: "Masquer le mot de passe", // pragma: allowlist secret
          totpLabel: "Code TOTP",
          submitLocalCta: "Se connecter",
          errorBannerTitle: "Erreur d'authentification",
        }}
      />,
    );

    const brandHeader = screen.getByTestId("login-brand-header");
    expect(brandHeader.textContent).toContain("ORCIA");

    const pwInput = screen.getByTestId("login-local-password") as HTMLInputElement;
    expect(pwInput.type).toBe("password");
    expect(pwInput.getAttribute("autoComplete")).toBe("current-password");

    const toggleBtn = screen.getByTestId(
      "login-local-password-toggle-visibility",
    ) as HTMLButtonElement;
    expect(toggleBtn.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(toggleBtn);
    expect(pwInput.type).toBe("text");
    expect(toggleBtn.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(toggleBtn);
    expect(pwInput.type).toBe("password");
  });

  it("places clickable [O] ORCIA home link in FourZoneTopHeaderSection and removes sidebar-brand-logo from FourZoneSidebarRail (Story 25.2)", () => {
    const onSelectMenu = vi.fn();
    const onNavigateHome = vi.fn();
    const { rerender } = render(
      <>
        <FourZoneTopHeaderSection
          isMobile={false}
          railCollapsed={false}
          activeWorkspaceName="Espace Paiement"
          workspaceDropdownOpen={false}
          onToggleWorkspaceDropdown={() => {}}
          onCloseWorkspaceDropdown={() => {}}
          onNavigateHome={onNavigateHome}
          helpColumnOpen={false}
          onToggleHelpColumn={() => {}}
          notificationsOpen={false}
          onToggleNotifications={() => {}}
          effectiveNotificationCount={0}
          labels={SHELL_LABELS}
          breadcrumbItems={[{ label: "Cockpit" }]}
        />
        <FourZoneSidebarRail
          railCollapsed={false}
          onToggleRailCollapsed={() => {}}
          activeMenuKey="cockpit"
          activePackKey="core"
          availablePacks={[]}
          labels={SHELL_LABELS}
          onSelectMenu={onSelectMenu}
        />
      </>,
    );

    const topbar = screen.getByTestId("four-zone-top-header-bar");
    const homeLink = screen.getByTestId("topbar-orcia-home-link");
    expect(topbar.contains(homeLink)).toBe(true);
    expect(homeLink.textContent).toContain("ORCIA");
    fireEvent.click(homeLink);
    expect(onNavigateHome).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("topbar-fixed-workspace-selector")).toBeNull();
    expect(screen.queryByTestId("sidebar-brand-logo")).toBeNull();

    // When rail collapses, sidebar logo remains absent and topbar selector becomes visible on desktop
    rerender(
      <>
        <FourZoneTopHeaderSection
          isMobile={false}
          railCollapsed={true}
          activeWorkspaceName="Espace Paiement"
          workspaceDropdownOpen={false}
          onToggleWorkspaceDropdown={() => {}}
          onCloseWorkspaceDropdown={() => {}}
          onNavigateHome={onNavigateHome}
          helpColumnOpen={false}
          onToggleHelpColumn={() => {}}
          notificationsOpen={false}
          onToggleNotifications={() => {}}
          effectiveNotificationCount={0}
          labels={SHELL_LABELS}
          breadcrumbItems={[{ label: "Cockpit" }]}
        />
        <FourZoneSidebarRail
          railCollapsed={true}
          onToggleRailCollapsed={() => {}}
          activeMenuKey="cockpit"
          activePackKey="core"
          availablePacks={[]}
          labels={SHELL_LABELS}
          onSelectMenu={onSelectMenu}
        />
      </>,
    );

    expect(screen.queryByTestId("sidebar-brand-logo")).toBeNull();
    expect(screen.getByTestId("topbar-fixed-workspace-selector")).toBeTruthy();
  });

  it("renders StreamlinedCockpitView orientation cards when 0 decisions and passes quick prompt to assistant", () => {
    const onOpenAssistant = vi.fn();
    const onNavigateModule = vi.fn();

    render(
      <FourZoneDirectionCShell
        activeMenuKey="cockpit"
        activeWorkspaceName="Espace Paiement"
        activePackKey="core"
        availablePacks={[]}
        userDisplayName="Admin"
        userHatLabel="Administrateur"
        pendingDecisionsTotal={0}
        viewportWidth={1440}
        labels={SHELL_LABELS}
        onSelectMenu={() => {}}
      >
        <StreamlinedCockpitView
          decisions={[]}
          currentUserId="admin@orcia.test"
          labels={COCKPIT_LABELS}
          onOpenAssistant={onOpenAssistant}
          onNavigateModule={onNavigateModule}
        />
      </FourZoneDirectionCShell>,
    );

    expect(screen.getByTestId("cockpit-calm-orientation-panel")).toBeTruthy();
    expect(screen.queryByTestId("cockpit-decisions-kpis")).toBeNull();
    fireEvent.change(screen.getByTestId("cockpit-quick-assistant-input"), {
      target: { value: "Analyser le workflow SEPA" },
    });
    fireEvent.click(screen.getByTestId("cockpit-quick-assistant-submit"));
    expect(onOpenAssistant).toHaveBeenCalledWith("Analyser le workflow SEPA");
  });
});
