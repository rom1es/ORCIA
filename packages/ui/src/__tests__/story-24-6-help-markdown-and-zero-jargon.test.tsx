import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ArbitrationTieBreakCard,
  CatalogExplorerPanel,
  ContextualHelpColumnAndCenter,
  PermissionBrokerCard,
  PresenceClaimPill,
  TopHeaderSearchCommand,
  UpstreamChallengeRewindModal,
  WorkflowStudioSection,
  type ContextualHelpColumnAndCenterLabels,
  type TopHeaderSearchCommandLabels,
  type UiContextualHelpArticleView,
} from "../index";

afterEach(() => {
  cleanup();
});

const HELP_LABELS_FR: ContextualHelpColumnAndCenterLabels = {
  columnHeaderTitle: "Aide contextuelle",
  centerHeaderTitle: "Centre d'Aide",
  whatForSectionTitle: "À quoi sert cet écran ?",
  stepByStepAccordionTitle: "Comment procéder pas à pas",
  keyTermsAccordionTitle: "Repères & notions utiles",
  faqAccordionTitle: "Questions fréquentes",
  askAssistantOnScreenCta: "Poser une question à Mon Assistant →",
  rollbackButtonLabel: "Revenir à la version précédente",
  rollbackCompletedPrefix: "Version restaurée :",
  mergedLayersPrefix: "Sources du guide :",
  realExampleTitle: "Un exemple réel",
  commonPitfallsTitle: "Ce qui coince souvent",
  technicalDetailsTitle: "Détails techniques",
  versionLabel: "Version",
  layerLabels: {
    BASE: "Base",
    PACK: "Pack",
    WORKSPACE: "Espace",
    USER: "Utilisateur",
  },
  stepsBlockPrefix: "En",
  stepsBlockSuffix: "gestes",
  targetedHelpBadgeLabel: "Aide ciblée",
};

const MARKDOWN_ARTICLE: UiContextualHelpArticleView = {
  resourceId: "help-md-24-6",
  uri: "orcia://system/help/cockpit/fr",
  title: "Cockpit : piloter vos validations",
  version: "1.0.0",
  lang: "fr",
  layer: "BASE",
  packName: "core",
  boundRoutes: ["/cockpit", "/help"],
  summaryWhatFor:
    "Le **Cockpit** centralise vos *validations humaines* avec `0` validation fantôme.",
  stepByStepItems: [
    "Ouvrez la carte **Arbitrage** pour trancher entre `2` options.",
    "Appuyez sur *Valider* après relecture complète.",
  ],
  keyTermsItems: [
    "**Ancrage humain** : règle de signature explicite avant *exécution* (`AD-3`).",
  ],
  faqItems: [
    "Comment ouvrir l'aide ciblée ? Cliquez sur l'icône `ⓘ` à côté du **titre**.",
  ],
  realExampleText:
    "Claire vérifie le bloc **Sécurité** et valide la *synthèse* via `Ctrl+Enter`.",
  commonPitfallsItems: [
    "**Bouton grisé** : l'action attend une *justification* d'au moins `30` caractères.",
  ],
  sections: [
    {
      sectionId: "sec-arbitrage",
      title: "Arbitrage humain",
      body: "Comparez les **impacts** et *coûts* via le panneau `Option A / Option B`.",
    },
  ],
  casKey: "cas/24-6",
  sha256: "24-6",
};

describe("Story 24.6 (USER24-BUG-3 + UX23-05 + UX23-08) — Markdown Help & Zero Jargon in @orcia/ui", () => {
  it("USER24-BUG-3: renders inline Markdown (**bold**, *italic*, `code`) as HTML with zero raw ** or backtick in Zone 4 and /help", () => {
    const { container: zone4Container } = render(
      <ContextualHelpColumnAndCenter
        mode="COLUMN_340PX"
        route="/cockpit"
        pack="core"
        redisCacheKey="help:route:/cockpit:core:fr"
        mergedLayers={["BASE"]}
        article={MARKDOWN_ARTICLE}
        activeSectionId="sec-arbitrage"
        isAdmin={false}
        showTechnicalMetadata={false}
        labels={HELP_LABELS_FR}
        onAskAssistantOnScreen={vi.fn()}
      />,
    );

    expect(zone4Container.textContent).not.toContain("**");
    expect(zone4Container.textContent).not.toContain("`");
    expect(zone4Container.querySelectorAll("strong").length).toBeGreaterThanOrEqual(4);
    expect(zone4Container.querySelectorAll("em").length).toBeGreaterThanOrEqual(4);
    expect(zone4Container.querySelectorAll("code").length).toBeGreaterThanOrEqual(4);
    expect(screen.getByTestId("help-section-sec-arbitrage").querySelector("code")?.textContent).toBe(
      "Option A / Option B",
    );

    // Open FAQ accordion in Zone 4
    fireEvent.click(screen.getByTestId("help-accordion-faq-btn"));
    expect(screen.getByTestId("help-accordion-faq-content").textContent).not.toContain("**");
    expect(screen.getByTestId("help-accordion-faq-content").textContent).not.toContain("`");
    expect(
      screen.getByTestId("help-accordion-faq-content").querySelector("code")?.textContent,
    ).toBe("ⓘ");

    cleanup();

    // HELP_MENU_CENTER mode (/help) with all accordions opened
    const { container: centerContainer } = render(
      <ContextualHelpColumnAndCenter
        mode="HELP_MENU_CENTER"
        route="/help"
        pack="core"
        redisCacheKey="help:route:/help:core:fr"
        mergedLayers={["BASE"]}
        article={MARKDOWN_ARTICLE}
        activeSectionId="sec-arbitrage"
        isAdmin={false}
        showTechnicalMetadata={false}
        labels={HELP_LABELS_FR}
        onAskAssistantOnScreen={vi.fn()}
      />,
    );

    const stepsBtn = screen.queryByTestId("help-accordion-steps-btn");
    if (stepsBtn && stepsBtn.getAttribute("aria-expanded") !== "true") {
      fireEvent.click(stepsBtn);
    }
    if (screen.getByTestId("help-accordion-terms-btn").getAttribute("aria-expanded") !== "true") {
      fireEvent.click(screen.getByTestId("help-accordion-terms-btn"));
    }
    if (screen.getByTestId("help-accordion-faq-btn").getAttribute("aria-expanded") !== "true") {
      fireEvent.click(screen.getByTestId("help-accordion-faq-btn"));
    }

    expect(centerContainer.textContent).not.toContain("**");
    expect(centerContainer.textContent).not.toContain("`");
    expect(screen.getByTestId("help-accordion-steps-content").querySelector("strong")?.textContent).toBe("Arbitrage");
    expect(screen.getByTestId("help-accordion-terms-content").querySelector("strong")?.textContent).toBe("Ancrage humain");
    expect(screen.getByTestId("help-accordion-faq-content").querySelector("strong")?.textContent).toBe("titre");
    expect(screen.getByTestId("contextual-help-common-pitfalls-box").querySelector("strong")?.textContent).toBe(
      "Bouton grisé",
    );
  });

  it("UX23-05: TopHeaderSearchResultsPane renders white OrciaIcon help icon and zero ❓ emoji", () => {
    const labels: TopHeaderSearchCommandLabels = {
      modalTitle: "Recherche rapide (⌘K)",
      inputPlaceholder: "Rechercher...",
      scopeScreenLabel: "Cet écran",
      scopeWorkspaceLabel: "Cet Espace",
      scopeAllWorkspacesLabel: "Tous mes Espaces",
      speed1SectionTitle: "Résultats immédiats",
      speed2SectionTitle: "Passages proches",
      semanticCloseMatchBadge: "Passage proche",
      emptyResultsLabel: "Aucun résultat",
      previewPaneTitle: "Aperçu",
      deepLinkActionLabel: "Ouvrir ↵",
      openHelpColumnActionLabel: "Ouvrir ❓ Aide",
      askAssistantFooterPrefix: "Poser la question",
      askAssistantFooterSuffix: "à Mon Assistant →",
      familyLabels: {
        FOLDERS_DISCUSSIONS: "Dossiers",
        PROCESSES_EXECUTIONS: "Processus",
        AGENTS_TOOLS: "Agents",
        DELIVERABLES_ARTIFACTS: "Livrables",
        SOURCES_SNIPPETS: "Sources",
        ONTOLOGY_GLOSSARY: "Ontologie",
        HELP_ACTIONS: "Aide",
      },
    };

    const { container } = render(
      <TopHeaderSearchCommand
        labels={labels}
        initialQuery="cockpit"
        speed1Hits={[
          {
            itemId: "help-1",
            family: "HELP_ACTIONS",
            title: "Guide Cockpit",
            snippet: "Aide contextuelle",
            workspaceId: "GLOBAL",
            screenRoute: "/cockpit",
            deepLinkUri: "help://cockpit/overview",
            speedTier: 1,
            lockedTop: true,
            score: 1.0,
            badge: null,
            highlightDurationMs: 2000,
            opensContextualHelpColumn: true,
          },
        ]}
        speed2Hits={[
          {
            itemId: "help-2",
            family: "HELP_ACTIONS",
            title: "Guide Cockpit Avancé",
            snippet: "Aide contextuelle avancée",
            workspaceId: "GLOBAL",
            screenRoute: "/cockpit",
            deepLinkUri: "help://cockpit/advanced",
            speedTier: 2,
            lockedTop: false,
            score: 0.85,
            badge: "Passage proche",
            highlightDurationMs: 2000,
            opensContextualHelpColumn: true,
          },
        ]}
        onSelectDeepLink={vi.fn()}
        onAskAssistant={vi.fn()}
      />,
    );

    expect(container.textContent).not.toContain("❓");
    const openBtn1 = screen.getByTestId("cmdk-open-btn-help-1");
    const openBtn2 = screen.getByTestId("cmdk-open-btn-help-2");
    expect(openBtn1.querySelector('[data-orcia-icon="help"]')).not.toBeNull();
    expect(openBtn2.querySelector('[data-orcia-icon="help"]')).not.toBeNull();
  });

  it("UX23-08: PermissionBrokerCard renders procedureMarkdown HTML, safely decodes URIs, and exposes zero HTTP 403 / Step jargon", () => {
    const { container } = render(
      <PermissionBrokerCard
        ticket={{
          id: "tkt-24-6",
          ticketKey: "tkt-perm-git",
          stepKey: "step-02-execution",
          stepNumber: 2,
          stepState: "PERMISSION_DENIED_STEP",
          status: "WAITING_FOR_PERMISSION",
          targetUri: "git%3A%2F%2Fgithub.enterprise%2Fpayments%2Fcheckout-core.git",
          connectorScheme: "git",
          executionIdentity: "passthrough",
          upstreamHttpStatus: 403,
          requiredRole: "ROLE_GIT_PAYMENTS_MAINTAINER",
          approverTeam: "Équipe Sécurité",
          slaHours: 4,
          jiraRequestUrl: "https://jira.enterprise.internal/secure/CreateIssue!init.jspa",
          permissionBrokerHint: "jira%3A%2F%2FIAM%2FROLE_GIT_PAYMENTS_MAINTAINER",
          procedureMarkdown:
            "Demandez l'accès **Maintainer** sur `checkout-core` puis relancez l'étape.",
        }}
        labels={{
          cardBadgeTitle: "Accès requis",
          passthroughBadgeLabel: "Identité utilisateur",
          servicePrincipalBadgeLabel: "Compte applicatif",
          targetUriLabel: "Source externe bloquée",
          requiredRoleLabel: "Rôle requis",
          approverTeamLabel: "Équipe approbatrice",
          slaHoursPrefix: "Délai cible",
          rfcHintLabel: "Référence",
          jiraRequestButtonLabel: "Demander l'accès dans Atlassian Jira",
          pauseStepButtonLabel: "Mettre en pause",
          replayStepButtonLabel: "Rejouer l'étape",
          stepPrefix: "Étape",
          pausedStateBanner: "Mise en pause",
          replayedStateBanner: "Relancée",
          simulatorTitle: "Simulateur",
          simulatorSubtitle: "Sous-titre",
          simulateGitDenialLabel: "Git",
          simulateConfluenceDenialLabel: "Confluence",
          simulateJiraDenialLabel: "Jira",
          simulateConfusedDeputyLabel: "Escalade",
          confusedDeputyBlockedBanner: "Bloqué",
          observerDeniedBanner: "Lecture seule",
        }}
      />,
    );

    expect(screen.getByTestId("permission-broker-target-uri").textContent).toBe(
      "git://github.enterprise/payments/checkout-core.git",
    );
    expect(screen.getByTestId("permission-broker-hint").textContent).toBe(
      "jira://IAM/ROLE_GIT_PAYMENTS_MAINTAINER",
    );
    const mdContainer = screen.getByTestId("permission-broker-card-procedure-md");
    expect(mdContainer.querySelector("strong")?.textContent).toBe("Maintainer");
    expect(mdContainer.querySelector("code")?.textContent).toBe("checkout-core");
    expect(mdContainer.textContent).not.toContain("**");
    expect(container.textContent).not.toContain("HTTP 403");
    expect(container.textContent).not.toMatch(/\bStep\s+2\b/);
    expect(container.textContent).toContain("Étape 2");
  });

  it("UX23-08: CatalogExplorerPanel, WorkflowStudioSection, ArbitrationTieBreakCard, UpstreamChallengeRewindModal & PresenceClaimPill expose zero raw jargon", () => {
    const { container } = render(
      <div>
        <CatalogExplorerPanel
          activePersona="claire"
          items={[]}
          runLockTriplets={[]}
          labels={{
            panelTitle: "Explorateur du Catalogue",
            panelSubtitle: "Sources gouvernées",
            emptyStateMessage: "Aucun élément disponible dans le catalogue pour ce filtre.",
            filterAllSchemesLabel: "Tous",
            maskedSourceBadgeLabel: "Source masquée",
            openSourceBadgeLabel: "Source ouverte",
            resolveCasButtonLabel: "Vérifier",
            casResolvedBannerPrefix: "Vérifié",
            promoteScopeButtonLabel: "Partager",
            promotedBannerPrefix: "Partagé",
            promoteDeniedObserverBanner: "Lecture seule",
            overrideSectionTitle: "Adaptations",
            overrideSectionSubtitle: "4 niveaux",
            overrideLayers: {
              base: "Base",
              teamParent: "Direction",
              teamSub: "Équipe",
              workspace: "Espace",
              user: "Utilisateur",
            },
            runLockTitle: "Verrouillage",
            bmadAdapterTitle: "Import Pack",
            bmadImportButtonLabel: "Importer",
            bmadImportedBanner: "Importé",
          }}
        />
        <WorkflowStudioSection
          labels={{
            studioTitle: "Studio Processus",
            studioSubtitle: "Validation",
            validateNominalLabel: "Valider",
            simulateCriticalAutonomousLabel: "Simuler critique",
            simulateMissingIntentionLabel: "Simuler intention",
            simulateMaxDepthLabel: "Simuler profondeur",
            validDagBanner: "Valide",
            criticalAutonomousErrorBanner: "Erreur critique",
            missingIntentionErrorBanner: "Erreur intention",
            maxDepthErrorBanner: "Erreur profondeur",
            templatePreviewTitle: "Aperçu",
            humanMarkdownTabLabel: "Vue Humaine",
            agentSchemaTabLabel: "Contrat",
            sampleHumanMarkdown: "# Aperçu",
            sampleAgentJsonSchema: "{}",
            subWorkflowLocksTitle: "Sous-processus",
            depthPrefix: "Niveau",
            principalDepthLabel: "principal",
          }}
        />
        <ArbitrationTieBreakCard
          arbitrationId="arb-24-6"
          stepKey="arb-step"
          questionTitle="Choix d'architecture"
          tieBreakPolicy="PAUSE_AND_ESCALATE"
          options={[
            {
              optionKey: "OPT_A",
              title: "Option A — Isolation dédiée",
              pros: ["Sécurité"],
              cons: ["Coût"],
              siImpact: "Faible",
              finopsImpact: "20 €/mois",
            },
          ]}
          labels={{
            badgeTitle: "Arbitrage",
            policyPrefixLabel: "Règle",
            recommendedBadgeLabel: "Recommandé",
            prosLabel: "Avantages",
            consLabel: "Inconvénients",
            siImpactLabel: "Impact SI",
            finopsImpactLabel: "Impact coûts",
            justificationPlaceholder: "Justification...",
            selectOptionButtonLabel: "Choisir",
            resolvedBannerPrefix: "Décision",
          }}
        />
        <UpstreamChallengeRewindModal
          isOpen={true}
          inline={true}
          preview={{
            runId: "run-24-6",
            challengerStepKey: "delegate-sub-workflow",
            targetUpstreamStepKey: "frame-architecture-intent",
            challengedSectionKey: "fx_rate_guarantee_rule",
            targetProfileArchetype: "PM_PO",
            translatedSummary: "Impact métier sur l'échéancier.",
            invalidatedDownstreamStepKeys: ["frame-architecture-intent"],
            invalidatedArtifactSections: ["fx_rate_guarantee_rule"],
            invalidatedOntologyAxiomKeys: ["axiom-l1-strategic-asset"],
            preservedUpstreamStepKeys: ["step-0-intake"],
            upstreamTokensSaved: 1000,
          }}
          labels={{
            modalTitle: "Remise en cause amont",
            modalSubtitle: "Contester une règle",
            targetStepLabel: "Étape ciblée",
            sectionKeyLabel: "Règle contestée",
            reasonLabel: "Justification",
            reasonPlaceholder: "Expliquez...",
            whatIfTitle: "Simulation d'impact",
            invalidatedStepsLabel: "Étapes invalidées",
            invalidatedSectionsLabel: "Sections impactées",
            invalidatedAxiomsLabel: "Règles concernées",
            preservedStepsLabel: "Étapes préservées",
            translatedSummaryLabel: "Synthèse métier",
            submitChallengeCta: "Envoyer",
            replayStepCta: "Relancer",
            closeCta: "Fermer",
            challengeSubmittedFeedback: "Envoyé",
            replayTriggeredFeedback: "Relancé",
            stepLabels: {
              "frame-architecture-intent": "Cadrage d'architecture",
              "step-0-intake": "Réception initiale",
            },
            sectionLabels: {
              fx_rate_guarantee_rule: "Règle de garantie de taux",
            },
            axiomLabels: {
              "axiom-l1-strategic-asset": "Règle d'actif stratégique",
            },
            profileLabels: {
              PM_PO: "Chef de produit",
            },
          }}
        />
        <PresenceClaimPill
          taskId="task-24-6"
          stepExecutionId="step-24-6"
          presenceState="CLAIMED_BY_ME"
          sseLatencyMs={0.5}
          labels={{
            claimActionLabel: "Prendre en charge",
            claimedByMeBadge: "Prise en charge par vous",
            claimedByPeerPrefix: "Prise en charge par",
            releaseActionLabel: "Libérer",
            forceUnclaimActionLabel: "Reprendre",
            readOnlyObserverNotice: "Lecture seule",
            sseLatencyPrefix: "Synchronisation",
            sseSyncedStatusLabel: "temps réel",
          }}
        />
      </div>,
    );

    expect(screen.getByTestId("catalog-explorer-empty-state").textContent).toContain(
      "Aucun élément disponible",
    );
    expect(screen.getByTestId("sub-lock-depth-0").textContent).toContain("Niveau principal");
    expect(container.textContent).not.toContain("depth=0");
    expect(container.textContent).not.toContain("PAUSE_AND_ESCALATE");
    expect(container.textContent).not.toContain("(OPT_A)");
    expect(container.textContent).not.toContain("frame-architecture-intent");
    expect(container.textContent).not.toContain("PM_PO");
    expect(container.textContent).not.toContain("0.5 ms");
    expect(container.textContent).toContain("temps réel");
    expect(container.textContent).toContain("Cadrage d'architecture");
    expect(container.textContent).toContain("Chef de produit");
  });
});
