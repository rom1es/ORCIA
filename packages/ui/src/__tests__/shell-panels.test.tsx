import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  AppShell,
  CatalogExplorerPanel,
  FederatedUriBadge,
  OntologyAndKbExplorerPanel,
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
  { key: "gates", order: 5, route: "/gates", icon: "shield", contributorBadgeCount: 1, hasStaleWarning: false, enabled: true },
];

const MOCK_SCOPES: UiScopeNode[] = [
  { id: "scope-ws-orcia", level: "WORKSPACE", name: "Workspace Solution ORCIA Core", accessMode: "CONTRIBUTOR_ACTION_REQUIRED" },
];

const MOCK_PROFILE: UiHumanProfileBadge = {
  archetypeKey: "TECH_LEAD",
  displayName: "Tech Lead / Architecte",
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
};

describe("CatalogExplorerPanel, PermissionBrokerCard & OntologyAndKbExplorerPanel", () => {
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

    const maskedPromoteBtn = screen.getByTestId(
      "promote-btn-res-blackbox-security-agent",
    ) as HTMLButtonElement;
    expect(maskedPromoteBtn.disabled).toBe(true);

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
    fireEvent.click(screen.getByTestId("permission-broker-pause-btn"));
    expect(onPause).toHaveBeenCalledWith("tkt-1101");
    fireEvent.click(screen.getByTestId("permission-broker-replay-btn"));
    expect(onReplay).toHaveBeenCalledWith("tkt-1101");
  });

  it("renders OntologyAndKbExplorerPanel empty state and interactive What-If / Promote / RAG filter / Stale Replay", () => {
    const labels = {
      panelTitle: "Ontologie & KB",
      panelSubtitle: "Sous-titre",
      emptyStateMessage: "Aucun concept",
      columns: {
        "1_ENTERPRISE": "1. Entreprise",
        "2_DOMAIN": "2. Domaine",
        "3_TEAM": "3. Équipe",
        "3_WORKSPACE": "3. Workspace",
        "4_RUN_EPHEMERAL": "4. Run",
      },
      profileSelectorLabel: "Profil :",
      whatIfButtonLabel: "Simuler What-If",
      promoteButtonLabel: "Promouvoir",
      promotedBannerPrefix: "Simulation What-If OK :",
      immutableConflictBanner: "HTTP 409 ERR_IMMUTABLE_AXIOM_CONFLICT",
      hybridRagTitle: "RAG Hybride",
      hybridRagSearchPlaceholder: "Rechercher...",
      hybridRagSearchButtonLabel: "Rechercher",
      tripartiteTitle: "Graphe Tripartite",
      staleAlertsTitle: "Alertes Fraîcheur",
      docObsoleteBadgeLabel: "[DOC_OBSOLETE]",
    };

    const { rerender } = render(
      <OntologyAndKbExplorerPanel
        concepts={[]}
        tripartiteEdges={[]}
        staleAlerts={[]}
        labels={labels}
      />,
    );
    expect(screen.getByTestId("ontology-kb-empty-state").textContent).toBe("Aucun concept");

    rerender(
      <OntologyAndKbExplorerPanel
        concepts={[
          {
            conceptKey: "c-mutable",
            canonicalTerm: "PaymentSettlementWindow",
            level: "3_WORKSPACE",
            scopeId: "ws-1",
            definitionText: "T+1",
            immutable: false,
            synonyms: ["Settlement Window"],
            profileTranslations: { EXECUTIVE: "Vue Exec", TECH_LEAD: "Vue Tech Lead" },
            impactedTemplates: ["tpl-1"],
            impactedWorkflows: ["wf-1"],
            impactedRuns: ["run-1"],
          },
        ]}
        tripartiteEdges={[
          {
            edgeKey: "e-1",
            sourceUri: "git://repo/settlement.py",
            targetUri: "jira://PAY/PAY-101",
            relationType: "FIXES",
            jiraIssueKey: "PAY-101",
          },
          {
            edgeKey: "e-2",
            sourceUri: "confluence://PAY/spec",
            targetUri: "jira://PAY/PAY-101",
            relationType: "SPECIFIES",
            jiraIssueKey: "PAY-101",
          },
        ]}
        staleAlerts={[
          {
            alertKey: "alert-1",
            documentKey: "doc-1",
            sourceUri: "confluence://PAY/spec",
            diagnosticMarker: "[STALE_WARNING] [DOC_OBSOLETE]",
            impactedRunIds: ["run-1"],
            justifyingJiraKey: "PAY-101",
          },
        ]}
        labels={labels}
      />,
    );

    fireEvent.change(screen.getByTestId("ontology-profile-selector"), {
      target: { value: "EXECUTIVE" },
    });
    expect(screen.getByTestId("ontology-translation-c-mutable").textContent).toBe("Vue Exec");

    fireEvent.click(screen.getByTestId("what-if-btn-c-mutable"));
    expect(screen.getByTestId("ontology-action-banner").textContent).toContain(
      "Simulation What-If OK : PaymentSettlementWindow",
    );

    fireEvent.click(screen.getByTestId("promote-btn-c-mutable"));
    expect(screen.getByTestId("ontology-action-banner").textContent).toContain(
      "Promouvoir : PaymentSettlementWindow -> 3_WORKSPACE",
    );

    fireEvent.change(screen.getByTestId("hybrid-rag-search-input"), {
      target: { value: "settlement.py" },
    });
    expect(screen.getByTestId("tripartite-edge-e-1")).toBeDefined();
    expect(screen.queryByTestId("tripartite-edge-e-2")).toBeNull();

    fireEvent.click(screen.getByTestId("stale-alert-replay-btn-alert-1"));
    expect(screen.getByTestId("ontology-action-banner").textContent).toContain(
      "[DOC_OBSOLETE] -> confluence://PAY/spec",
    );
  });
});
