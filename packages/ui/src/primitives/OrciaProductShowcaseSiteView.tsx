import React, { useMemo, useState } from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { getOrciaIconGlyph, ORCIA_EIGHT_MENU_ICON_NAMES } from "../components/icons";
import { OrciaButton, OrciaSectionCard, OrciaTabBar } from "./DesignSystemControls";
import { StatusBadge } from "./StatusBadge";

export type OrciaShowcasePillarTabKey =
  | "macro"
  | "features"
  | "architecture"
  | "changelog";

export interface OrciaShowcaseInstalledPackItem {
  readonly key: string;
  readonly version: string;
  readonly description: string;
}

export interface OrciaShowcaseArchitectureDecisionItem {
  readonly code: string;
  readonly title: string;
}

export interface OrciaShowcaseStackComponentItem {
  readonly name: string;
  readonly version: string;
}

export interface OrciaShowcaseTechLeadReportItem {
  readonly date: string;
  readonly phaseOrStory: string;
  readonly reportFile: string;
  readonly domain: string;
  readonly summary: string;
}

export interface OrciaShowcaseManifestStats {
  readonly activeRoutesCount: number;
  readonly uiPrimitivesCount: number;
  readonly installedPacksCount: number;
  readonly alembicMigrationsCount: number;
  readonly architectureDecisionsCount: number;
  readonly stackComponentsCount: number;
  readonly techLeadReportsCount: number;
  readonly capabilitiesCount?: number;
  readonly liveCapabilitiesCount?: number;
  readonly verifiedCapabilitiesCount?: number;
}

export interface OrciaShowcaseManifestData {
  readonly lastSyncedDate: string;
  readonly stats: OrciaShowcaseManifestStats;
  readonly activeRoutes: readonly string[];
  readonly uiPrimitives: readonly string[];
  readonly installedPacks: readonly OrciaShowcaseInstalledPackItem[];
  readonly alembicMigrations: readonly string[];
  readonly architectureDecisions: readonly OrciaShowcaseArchitectureDecisionItem[];
  readonly stackComponents: readonly OrciaShowcaseStackComponentItem[];
  readonly techLeadReports: readonly OrciaShowcaseTechLeadReportItem[];
}

export interface OrciaProductShowcaseSiteViewProps {
  readonly locale?: "fr" | "en";
  readonly manifest: OrciaShowcaseManifestData;
  readonly initialTab?: OrciaShowcasePillarTabKey;
  readonly onNavigateToRoute?: (route: string) => void;
  readonly onOpenHelpSection?: (sectionId: string) => void;
  readonly onDownloadStandaloneHtml?: () => void;
}

interface ScreenGuideSpec {
  readonly id: string;
  readonly icon: string;
  readonly titleFr: string;
  readonly titleEn: string;
  readonly route: string;
  readonly summaryFr: string;
  readonly summaryEn: string;
  readonly keyActionsFr: readonly string[];
  readonly keyActionsEn: readonly string[];
}

const NINE_SCREENS_GUIDE: readonly ScreenGuideSpec[] = [
  {
    id: "cockpit",
    get icon() {
      return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.cockpit);
    },
    titleFr: "1. ◈ Cockpit",
    titleEn: "1. ◈ Cockpit",
    route: "/cockpit",
    summaryFr:
      "Tableau de bord opérationnel réunissant vos décisions humaines en attente, l'état d'avancement initial et le démarrage rapide de processus.",
    summaryEn:
      "Operational dashboard gathering your pending human decisions, initial setup progress, and quick process launch.",
    keyActionsFr: [
      "Traiter en 1 clic les arbitrages urgents sans quitter le tableau de bord",
      "Ouvrir l'atelier de relecture approfondie d'une étape avec réservation exclusive",
      "Démarrer une nouvelle exécution de processus sur l'Espace actif",
    ],
    keyActionsEn: [
      "Resolve urgent arbitrations in 1 click without leaving the dashboard",
      "Open the focused review workshop for a step with exclusive team claim",
      "Launch a new process run on the active Workspace",
    ],
  },
  {
    id: "assistant",
    get icon() {
      return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.assistant);
    },
    titleFr: "2. 💬 Mon Assistant",
    titleEn: "2. 💬 My Assistant",
    route: "/assistant",
    summaryFr:
      "Espace conversationnel à 3 vitesses d'exécution, organisé en dossiers thématiques partageables avec citations vérifiées et personnalisation à 4 niveaux.",
    summaryEn:
      "3-speed conversational workspace organized in shareable thematic folders with verified citations and 4-level customization.",
    keyActionsFr: [
      "Choisir entre réponse rapide, appel d'un agent ou compétence, et réflexion approfondie",
      "Vérifier chaque fait grâce aux pastilles de citation [S1], [G1] et [O1]",
      "Classer et partager les fils de discussion dans des dossiers Privés, Partagés ou d'Espace",
    ],
    keyActionsEn: [
      "Switch between fast reply, agent/skill invocation, and deep reasoning",
      "Verify every claim through [S1], [G1], and [O1] citation pills",
      "Organize and share threads inside Private, Shared, or Workspace folders",
    ],
  },
  {
    id: "processes",
    get icon() {
      return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.processes);
    },
    titleFr: "3. ☍ Mes Processus",
    titleEn: "3. ☍ My Processes",
    route: "/processes",
    summaryFr:
      "Atelier de création et de suivi des processus métiers étape par étape, studio de Packs Métiers et générateur de guides d'aide.",
    summaryEn:
      "Step-by-step business process builder and tracker, Business Pack studio, and help guide generator.",
    keyActionsFr: [
      "Construire un processus guidé avec ses instructions, son contrat de livrable et ses étapes",
      "Assembler et certifier un Pack Métier complet avec simulation d'impact",
      "Rédiger et rattacher à chaud une fiche d'aide contextuelle à n'importe quel écran",
    ],
    keyActionsEn: [
      "Build a guided process with instructions, deliverable contract, and steps",
      "Assemble and certify a complete Business Pack with impact simulation",
      "Author and hot-attach a contextual help guide to any screen",
    ],
  },
  {
    id: "agents",
    get icon() {
      return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.agents);
    },
    titleFr: "4. 🤖 Mes Agents",
    titleEn: "4. 🤖 My Agents",
    route: "/agents",
    summaryFr:
      "Catalogue et gestion de vos agents spécialisés, de vos compétences réutilisables et banc de test des connexions aux services externes.",
    summaryEn:
      "Catalog and management of specialized agents, reusable skills, and external service connection test bench.",
    keyActionsFr: [
      "Créer un agent spécialisé et lui rattacher des compétences métiers en 1 clic",
      "Tester immédiatement un agent ou une compétence sur un cas concret",
      "Qualifier et éprouver à chaud un service externe en 4 étapes de sécurité",
    ],
    keyActionsEn: [
      "Create a specialized agent and attach business skills in 1 click",
      "Test an agent or skill immediately on a concrete input",
      "Qualify and live-test an external service across 4 safety steps",
    ],
  },
  {
    id: "spaces",
    get icon() {
      return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.spaces);
    },
    titleFr: "5. 📦 Mes Espaces",
    titleEn: "5. 📦 My Spaces",
    route: "/spaces",
    summaryFr:
      "Centre de pilotage de vos espaces de travail en 5 sous-onglets : exécutions, sources documentaires, glossaire et règles métiers, réconciliation externe et équipe.",
    summaryEn:
      "5-tab workspace control center: executions, documentary sources, business glossary and rules, external reconciliation, and team.",
    keyActionsFr: [
      "Gérer le cycle de vie du glossaire métier et valider les règles proposées (plafond de 15 termes)",
      "Inspecter et réconcilier les modifications effectuées par les humains dans leurs outils externes",
      "Piloter les sources documentaires rattachées et les exceptions acquittées",
    ],
    keyActionsEn: [
      "Manage the business glossary lifecycle and validate proposed rules (capped at 15 terms)",
      "Inspect and reconcile edits made by humans in external tools",
      "Govern attached documentary sources and acknowledged exceptions",
    ],
  },
  {
    id: "finops",
    get icon() {
      return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.finops);
    },
    titleFr: "6. 📊 Suivi des Coûts",
    titleEn: "6. 📊 Cost Tracking",
    route: "/finops",
    summaryFr:
      "Suivi budgétaire transparent des consommations par direction, par espace, par processus et par étape, avec plafonds et coupe-circuit automatique.",
    summaryEn:
      "Transparent budget tracking across divisions, workspaces, processes, and steps, with spending caps and automatic circuit-breakers.",
    keyActionsFr: [
      "Visualiser la répartition des coûts par espace de travail et par exécution",
      "Définir des plafonds budgétaires préventifs par exécution et par déclencheur",
      "Autoriser explicitement une extension de budget lorsqu'une étape est mise en pause",
    ],
    keyActionsEn: [
      "Visualize cost breakdown by workspace and execution",
      "Set preventive budget caps per run and per trigger",
      "Explicitly authorize a budget extension when a step is paused",
    ],
  },
  {
    id: "activity",
    get icon() {
      return getOrciaIconGlyph("menuActivity");
    },
    titleFr: "7. 📜 Journal d'Activité",
    titleEn: "7. 📜 Activity Log",
    route: "/activity",
    summaryFr:
      "Historique horodaté et inaltérable de toutes les actions réalisées sur la plateforme, filtré par défaut sur votre niveau d'observation actif.",
    summaryEn:
      "Timestamped, tamper-evident history of all actions performed on the platform, filtered by default to your active observation scope.",
    keyActionsFr: [
      "Consulter qui a réalisé quelle action, à quelle seconde et sur quel périmètre",
      "Filtrer instantanément par périmètre observé, par auteur, par volume (50 à 500) ou par période",
      "Revenir en 1 clic au périmètre d'observation de votre session connectée",
    ],
    keyActionsEn: [
      "Audit who performed which action, at what exact time, and on which scope",
      "Filter by observed scope, author, volume (50 to 500), or time window",
      "Reset in 1 click to your connected session's observation scope",
    ],
  },
  {
    id: "settings",
    get icon() {
      return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.configuration);
    },
    titleFr: "8. ⚙ Configuration",
    titleEn: "8. ⚙ Configuration",
    route: "/settings",
    summaryFr:
      "Administration unifiée de l'arborescence d'organisation, des habilitations, des modèles IA avec test de connectivité, des connecteurs et des Packs Métiers.",
    summaryEn:
      "Unified administration of organization tree, permissions, AI models with connectivity test, connectors, and Business Packs.",
    keyActionsFr: [
      "Structurer les Directions (BU) et Équipes puis attribuer les droits sur chaque périmètre cible",
      "Configurer les fournisseurs de modèles IA et tester en direct la connexion",
      "Activer ou désactiver en 1 clic les Packs Métiers sur la plateforme, une Direction ou un Espace",
    ],
    keyActionsEn: [
      "Structure Divisions (BUs) and Teams, then grant permissions on each target scope",
      "Configure AI model providers and live-test connectivity",
      "Enable or disable Business Packs in 1 click on the platform, a Division, or a Workspace",
    ],
  },
  {
    id: "help",
    get icon() {
      return getOrciaIconGlyph(ORCIA_EIGHT_MENU_ICON_NAMES.help);
    },
    titleFr: "9. ❓ Aide Contextuelle (ⓘ) & Recherche Globale (⌘K)",
    titleEn: "9. ❓ Contextual Help (ⓘ) & Global Search (⌘K)",
    route: "/help",
    summaryFr:
      "Centre d'aide contextuelle rattaché à chaque titre d'écran via le bouton discret ⓘ, glossaire partagé et recherche instantanée à 2 vitesses (⌘K).",
    summaryEn:
      "Contextual help center bound to every screen header via the ⓘ trigger button, shared glossary, and 2-speed instant search (⌘K).",
    keyActionsFr: [
      "Cliquer sur n'importe quelle icône ⓘ pour ouvrir et surligner l'explication ciblée dans la colonne droite",
      "Rechercher instantanément (⌘K) dans les dossiers, les processus, le glossaire et les guides",
      "Restaurer en 1 clic la version précédente d'un guide d'aide ou interroger Mon Assistant sur l'écran actif",
    ],
    keyActionsEn: [
      "Click any ⓘ icon to open and highlight the targeted explanation in the right column",
      "Search instantly (⌘K) across folders, processes, glossary terms, and guides",
      "Restore the previous version of a help guide in 1 click or ask My Assistant about the active screen",
    ],
  },
];

/**
 * Pure `@orcia/ui` component presenting the ORCIA Product & Architecture Showcase Site (`/showcase`).
 * Strictly separates:
 * - Space 1 (`showcase-pillar-macro`): Macro Vision, Human-Led Governance & Double Anti-Hallucination Barrier (0 implementation jargon)
 * - Space 2 (`showcase-pillar-features`): Functional Guide — 6 Human-Led Devices & 9 Screens (0 implementation jargon)
 * - Space 3 (`showcase-pillar-architecture`): Under-the-Hood Engineering & Technical Architecture (full stack, DBOS, PostgreSQL 18, Starlark, pgvector, RRF, Sandboxes)
 * - Space 4 (`showcase-pillar-changelog`): Living Repository Changelog & Synced Metrics (`pnpm site:sync`)
 */
export function OrciaProductShowcaseSiteView({
  locale = "fr",
  manifest,
  initialTab = "macro",
  onNavigateToRoute,
  onOpenHelpSection,
  onDownloadStandaloneHtml,
}: OrciaProductShowcaseSiteViewProps): React.ReactElement {
  const isFr = locale === "fr";
  const [activeTab, setActiveTab] = useState<OrciaShowcasePillarTabKey>(initialTab);
  const [changelogFilter, setChangelogFilter] = useState<string>("");
  const [exportedBannerVisible, setExportedBannerVisible] = useState<boolean>(false);

  const filteredReports = useMemo(() => {
    const q = changelogFilter.trim().toLowerCase();
    if (!q) {
      return manifest.techLeadReports;
    }
    return manifest.techLeadReports.filter((item) => {
      const haystack =
        `${item.date} ${item.phaseOrStory} ${item.reportFile} ${item.domain} ${item.summary}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [changelogFilter, manifest.techLeadReports]);

  const handleExportTrigger = (): void => {
    setExportedBannerVisible(true);
    onDownloadStandaloneHtml?.();
  };

  return (
    <div
      data-testid="orcia-product-showcase-site-view"
      className="orcia-ds-page"
    >
      {/* Hero Banner */}
      <OrciaSectionCard
        testId="showcase-hero-card"
        title={
          isFr
            ? "🌐 Site de Présentation & Documentation Vivante d'ORCIA"
            : "🌐 ORCIA Living Product & Architecture Showcase Site"
        }
        subtitle={
          isFr
            ? "Explorez ORCIA à travers 3 espaces strictement séparés (Vision & Pilotage Humain, Guide Fonctionnel des 9 Écrans, Architecture & Choix Techniques sous le capot) et son Historique des Évolutions synchronisé automatiquement."
            : "Explore ORCIA across 3 strictly separated spaces (Macro Human-Led Vision, Functional Guide to the 9 Screens, Under-the-Hood Engineering Architecture) and its automatically synchronized Evolution Changelog."
        }
        helpSectionId="showcase-overview"
        helpLabel={
          isFr
            ? "Comprendre l'organisation en 3 espaces étanches du site de présentation ORCIA"
            : "Understand the 3 strictly separated spaces of the ORCIA showcase site"
        }
        onOpenHelpSection={onOpenHelpSection}
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge
              testId="showcase-sync-date-badge"
              label={
                isFr
                  ? `Synchronisé : ${manifest.lastSyncedDate}`
                  : `Synced: ${manifest.lastSyncedDate}`
              }
              tone="emerald"
              monospace
            />
            <OrciaButton
              testId="showcase-export-standalone-btn"
              variant="secondary"
              onClick={handleExportTrigger}
            >
              {isFr
                ? "⬇ Exporter le site HTML autonome (docs/site-catalog/index.html)"
                : "⬇ Export standalone HTML site (docs/site-catalog/index.html)"}
            </OrciaButton>
          </div>
        }
      >
        {exportedBannerVisible && (
          <div
            data-testid="showcase-standalone-export-banner"
            className="orcia-ds-alert orcia-ds-alert-success"
          >
            {isFr
              ? "Export HTML5 autonome prêt : ouvrez directement `docs/site-catalog/index.html`."
              : "Standalone HTML5 export ready: open `docs/site-catalog/index.html` directly."}
          </div>
        )}

        <OrciaTabBar
          ariaLabel={
            isFr
              ? "Navigation des 4 espaces du site de présentation ORCIA"
              : "ORCIA Showcase Site 4-space navigation"
          }
          activeTab={activeTab}
          onSelectTab={(key) => setActiveTab(key as OrciaShowcasePillarTabKey)}
          tabs={[
            {
              key: "macro",
              label: isFr
                ? "1. Vision & Pilotage Humain (Macro)"
                : "1. Vision & Human-Led Governance (Macro)",
              testId: "showcase-tab-macro",
            },
            {
              key: "features",
              label: isFr
                ? "2. Fonctionnalités & Écrans (Guide Fonctionnel)"
                : "2. Features & Screens (Functional Guide)",
              testId: "showcase-tab-features",
            },
            {
              key: "architecture",
              label: isFr
                ? "3. Architecture & Choix Techniques (Sous le Capot)"
                : "3. Architecture & Engineering Choices (Under the Hood)",
              testId: "showcase-tab-architecture",
            },
            {
              key: "changelog",
              label: isFr
                ? `4. 🔄 Historique des Évolutions (${manifest.stats.techLeadReportsCount})`
                : `4. 🔄 Evolution Changelog (${manifest.stats.techLeadReportsCount})`,
              testId: "showcase-tab-changelog",
            },
          ]}
        />
      </OrciaSectionCard>

      {/* =====================================================================
       * ESPACE 1 — 1. VISION & PILOTAGE HUMAIN (MACRO)
       * RÈGLE D'ÉTANCHÉITÉ STRICTE : Zéro terme technique d'implémentation !
       * ===================================================================== */}
      {activeTab === "macro" && (
        <section
          data-testid="showcase-pillar-macro"
          className="orcia-ds-page"
        >
          {/* 1.1 Pourquoi ORCIA ? */}
          <OrciaSectionCard
            testId="showcase-macro-why-orcia"
            title={
              isFr
                ? "1.1 Pourquoi ORCIA ? Orchestrer Processus, Contexte documentaire et Agents spécialisés sous conduite humaine"
                : "1.1 Why ORCIA? Orchestrating Processes, Documentary Context, and Specialized Agents under Human Leadership"
            }
            subtitle={
              isFr
                ? "Sortir des discussions éphémères isolées pour bâtir des livrables d'entreprise fiables, traçables et gouvernés par vos équipes."
                : "Move beyond isolated ephemeral chats to build reliable, traceable enterprise deliverables governed by your teams."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="font-bold text-sm" style={{ color: "var(--color-action-primary)" }}>
                  {isFr ? "☍ Processus Métiers Structurés" : "☍ Structured Business Processes"}
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Vos travaux complexes avancent étape par étape selon des contrats de livrables précis, capables de se mettre en pause le temps d'une décision humaine et de reprendre sans jamais perdre le fil."
                    : "Your complex workflows progress step by step under clear deliverable contracts, able to pause for human decisions and resume without losing context."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="font-bold text-sm" style={{ color: "var(--color-action-primary)" }}>
                  {isFr ? "📚 Contexte Documentaire & Glossaire Vivant" : "📚 Documentary Context & Living Glossary"}
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Chaque étape s'appuie exclusivement sur les sources documentaires rattachées à votre Espace de travail et sur le glossaire métier officiel de votre organisation, avec alerte immédiate si un document est obsolète."
                    : "Every step relies on the documentary sources bound to your Workspace and your organization's official business glossary, with immediate alerts when a document is outdated."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="font-bold text-sm" style={{ color: "var(--color-action-primary)" }}>
                  {isFr ? "🤖 Agents Spécialisés Gouvernés" : "🤖 Governed Specialized Agents"}
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Des agents dotés de compétences ciblées préparent les analyses, vérifient la cohérence et synthétisent les options, tout en respectant strictement les droits d'accès de chaque collaborateur."
                    : "Specialized agents equipped with targeted skills prepare analyses, verify consistency, and synthesize options while strictly enforcing each team member's access rights."}
                </p>
              </div>
            </div>
          </OrciaSectionCard>

          {/* 1.2 Le Principe Fondateur Human-Led */}
          <OrciaSectionCard
            testId="showcase-macro-human-led"
            title={
              isFr
                ? "1.2 Le Principe Fondateur « Human-Led » : L'Humain aux Commandes, jamais Spectateur"
                : "1.2 The Founding 'Human-Led' Principle: Humans in Command, Never Spectators"
            }
            subtitle={
              isFr
                ? "Quatre verrous méthodologiques garantissent que l'intelligence artificielle prépare et éclaire le travail sans jamais déposséder l'expert humain de sa responsabilité."
                : "Four methodological safeguards guarantee that AI prepares and illuminates work without ever stripping human experts of their authority."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div
                data-testid="showcase-macro-human-anchor-pillar"
                className="rounded-lg border p-4 space-y-2"
                style={{
                  backgroundColor: "var(--color-human-led-bg)",
                  borderColor: "var(--color-primary-dark)",
                }}
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-bold text-sm">
                    {isFr
                      ? "✍️ 1. Ancrages de Rédaction Humaine obligatoires (identité visuelle Violette)"
                      : "✍️ 1. Mandatory Human-Authored Anchors (Violet visual identity)"}
                  </span>
                  <StatusBadge label={isFr ? "Exclusivité Humaine" : "Human Exclusive"} tone="cobalt" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "L'intention initiale, les objectifs stratégiques et les hypothèses structurantes appartiennent exclusivement à l'auteur humain. Identifiées par une couleur Violette dédiée dans toute l'application, ces sections ne peuvent jamais être rédigées ni altérées par un agent IA."
                    : "Initial intent, strategic objectives, and foundational assumptions belong exclusively to the human author. Highlighted by a dedicated Violet visual identity across the app, these sections can never be authored or altered by an AI agent."}
                </p>
              </div>

              <div
                data-testid="showcase-macro-anti-rubber-stamping-pillar"
                className="rounded-lg border p-4 space-y-2"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-bold text-sm">
                    {isFr
                      ? "🛑 2. Zéro validation machinale (« Anti-Validation Fantôme »)"
                      : "🛑 2. Zero Mechanical Rubber-Stamping ('Anti-Ghost Validation')"}
                  </span>
                  <StatusBadge label={isFr ? "Lecture Active" : "Active Review"} tone="cobalt" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Fini les pavés de 20 pages validés sans être lus : chaque étape produit une synthèse de décision en 4 blocs (Résumé, Éléments clés, Décisions prises, Hypothèses retenues), exige une validation section par section (Approuver / Co-éditer / Contester) et vérifie le respect d'un temps minimal de lecture active."
                    : "No more 20-page walls of text approved blindly: every step produces a 4-block decision briefing (Summary, Key Elements, Decisions Taken, Assumptions Retained), requires section-by-section validation (Approve / Co-edit / Challenge), and enforces a minimum active reading time."}
                </p>
              </div>

              <div
                data-testid="showcase-macro-human-arbitration-pillar"
                className="rounded-lg border p-4 space-y-2"
                style={{
                  backgroundColor: "var(--color-arbitration-bg)",
                  borderColor: "var(--color-arbitration-amber)",
                }}
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-bold text-sm">
                    {isFr
                      ? "⚖️ 3. Arbitrage humain systématique en cas de dilemme ou de contradiction"
                      : "⚖️ 3. Systematic Human Arbitration on Dilemmas or Contradictions"}
                  </span>
                  <StatusBadge label={isFr ? "Pause & Options" : "Pause & Options"} tone="amber" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Lorsqu'un agent détecte une contradiction entre deux documents de référence ou fait face à plusieurs options d'architecture équivalentes, il a l'interdiction d'inventer un compromis implicite : le processus se met en pause et présente clairement la matrice de choix à l'humain."
                    : "When an agent detects a contradiction between two reference documents or faces multiple equivalent options, it is forbidden from inventing an implicit compromise: the process pauses and clearly presents the decision matrix to the human."}
                </p>
              </div>

              <div
                data-testid="showcase-macro-no-wild-writes-pillar"
                className="rounded-lg border p-4 space-y-2"
                style={{
                  backgroundColor: "var(--color-gate-emerald-bg)",
                  borderColor: "var(--color-gate-emerald)",
                }}
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-bold text-sm">
                    {isFr
                      ? "🛡️ 4. Aucune modification sauvage des outils de l'entreprise"
                      : "🛡️ 4. Zero Unapproved Writes to Enterprise Tools"}
                  </span>
                  <StatusBadge label={isFr ? "Actions Préparées" : "Staged Actions"} tone="emerald" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Aucune publication ni mise à jour dans vos outils externes ne peut partir directement d'une discussion rapide : les actions externes sont toujours préparées en attente d'accord humain. Et si un collaborateur modifie ensuite un document hors plateforme, ORCIA respecte et intègre ses modifications sans jamais les écraser."
                    : "No publication or update to your external tools can ever be triggered directly from a quick chat: external actions are always staged pending human approval. And if a colleague later edits a document outside the platform, ORCIA respects and reconciles their human edits without ever overwriting them."}
                </p>
              </div>
            </div>
          </OrciaSectionCard>

          {/* 1.3 La Double Barrière Anti-Hallucination & Anti-Propagation d'Erreurs */}
          <OrciaSectionCard
            testId="showcase-macro-double-barrier"
            title={
              isFr
                ? "1.3 La Double Barrière Anti-Hallucination & Anti-Propagation d'Erreurs (Déterministe + Probabiliste)"
                : "1.3 The Double Anti-Hallucination & Error-Containment Barrier (Deterministic + Probabilistic)"
            }
            subtitle={
              isFr
                ? "Comment ORCIA brise l'effet boule de neige où une erreur dès l'étape 1 contamine tout le reste d'un processus."
                : "How ORCIA breaks the snowball effect where an error in Step 1 contaminates the entire downstream process."
            }
          >
            <div
              className="rounded-lg border p-3.5 text-xs mb-3"
              style={{
                backgroundColor: "var(--color-stale-bg)",
                borderColor: "var(--color-stale-crimson)",
              }}
            >
              <strong>
                {isFr
                  ? "⚠️ Le piège des chaînes d'IA classiques (l'effet boule de neige) : "
                  : "⚠️ The trap of classic AI chains (the snowball effect): "}
              </strong>
              <span style={{ color: "var(--color-text-primary)" }}>
                {isFr
                  ? "lorsqu'un premier agent commet une légère approximation ou cite une source inexistante en étape 1, l'agent de l'étape 2 la prend pour une vérité établie, et l'étape 3 construit tout un livrable erroné dessus. ORCIA bloque cette propagation grâce à trois barrières successives :"
                  : "when a first agent makes a slight approximation or cites a non-existent source in Step 1, Step 2 treats it as established truth, and Step 3 builds an entire flawed deliverable on top of it. ORCIA stops this propagation with three successive barriers:"}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div
                data-testid="showcase-macro-barrier-deterministic"
                className="rounded-lg border p-4 space-y-2"
                style={{
                  backgroundColor: "var(--color-gate-emerald-bg)",
                  borderColor: "var(--color-gate-emerald)",
                }}
              >
                <StatusBadge
                  label={isFr ? "Barrière n°1 · Certitude 100 % · Coût 0 €" : "Barrier #1 · 100% Certainty · $0 Cost"}
                  tone="emerald"
                />
                <h3 className="font-bold text-sm">
                  {isFr
                    ? "Les Contrôles Déterministes (Instantanés & Mathématiques)"
                    : "Deterministic Controls (Instant & Mathematical)"}
                </h3>
                <ul className="space-y-1 list-disc list-inside" style={{ color: "var(--color-text-secondary)" }}>
                  <li>
                    {isFr
                      ? "Vérification exacte de la structure du livrable et de toutes les sections obligatoires attendues."
                      : "Exact verification of deliverable structure and all required sections."}
                  </li>
                  <li>
                    {isFr
                      ? "Exécution automatique des règles métiers codifiées du glossaire de votre organisation."
                      : "Automatic execution of codified business rules from your organization's glossary."}
                  </li>
                  <li>
                    {isFr
                      ? "Détection immédiate de toute dérive par rapport aux modèles de référence de l'entreprise."
                      : "Immediate detection of any drift against enterprise reference templates."}
                  </li>
                  <li>
                    {isFr
                      ? "Contrôle mathématique que chaque citation ([S1], [G1], [O1]) pointe vers un document réel et accessible."
                      : "Mathematical check that every citation ([S1], [G1], [O1]) points to a real, accessible source."}
                  </li>
                </ul>
              </div>

              <div
                data-testid="showcase-macro-barrier-probabilistic"
                className="rounded-lg border p-4 space-y-2"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <StatusBadge
                  label={isFr ? "Barrière n°2 · Regard Indépendant · 5 Angles" : "Barrier #2 · Independent Judge · 5 Angles"}
                  tone="cobalt"
                />
                <h3 className="font-bold text-sm">
                  {isFr
                    ? "Les Contrôles Probabilistes Croisés (Zéro Juge et Partie)"
                    : "Cross-Family Probabilistic Controls (Never Judge and Party)"}
                </h3>
                <ul className="space-y-1 list-disc list-inside" style={{ color: "var(--color-text-secondary)" }}>
                  <li>
                    {isFr
                      ? "Interdiction absolue pour un modèle IA de valider son propre travail : le vérificateur appartient obligatoirement à une famille de modèles différente du rédacteur."
                      : "Strict ban on an AI model reviewing its own work: the verifier must belong to a different model family than the author."}
                  </li>
                  <li>
                    {isFr
                      ? "Purge complète des brouillons de raisonnement intermédiaires pour ne juger que le livrable factuel."
                      : "Complete purge of intermediate reasoning drafts so only the factual deliverable is judged."}
                  </li>
                  <li>
                    {isFr
                      ? "Analyse parallèle sous 5 angles indépendants : alignement avec l'étape 1, vérification factuelle assertion par assertion, cas limites, conformité métier/sécurité et synthèse."
                      : "Parallel review across 5 independent angles: Step 1 alignment, claim-by-claim fact checking, edge cases, business/security compliance, and synthesis."}
                  </li>
                </ul>
              </div>

              <div
                data-testid="showcase-macro-barrier-rewind"
                className="rounded-lg border p-4 space-y-2"
                style={{
                  backgroundColor: "var(--color-arbitration-bg)",
                  borderColor: "var(--color-arbitration-amber)",
                }}
              >
                <StatusBadge
                  label={isFr ? "Barrière n°3 · Simulation & Recalcul Ciblé" : "Barrier #3 · Impact Simulation & Targeted Replay"}
                  tone="amber"
                />
                <h3 className="font-bold text-sm">
                  {isFr
                    ? "La Remise en Cause Amont (« Et si on corrigeait l'étape précédente ? »)"
                    : "Upstream Challenge ('What if we fixed the previous step?')"}
                </h3>
                <ul className="space-y-1 list-disc list-inside" style={{ color: "var(--color-text-secondary)" }}>
                  <li>
                    {isFr
                      ? "À tout moment, un expert peut remettre en question une hypothèse ou une règle issue d'une étape antérieure."
                      : "At any point, an expert can challenge an assumption or rule originating from an earlier step."}
                  </li>
                  <li>
                    {isFr
                      ? "Le simulateur affiche avant exécution la liste exacte des étapes et livrables qui seront impactés."
                      : "The simulator previews the exact list of downstream steps and deliverables that will be impacted."}
                  </li>
                  <li>
                    {isFr
                      ? "Le recalcul repart uniquement de l'étape corrigée en conservant tout le travail validé en amont, sans jamais perdre l'historique."
                      : "Recalculation restarts strictly from the corrected step while preserving all validated upstream work and full history."}
                  </li>
                </ul>
              </div>
            </div>
          </OrciaSectionCard>

          {/* 1.4 Gouvernance par l'Organisation Réelle & Packs Métiers */}
          <OrciaSectionCard
            testId="showcase-macro-org-and-packs"
            title={
              isFr
                ? "1.4 Gouvernance par l'Organisation Réelle & Activation en 1 Clic des Packs Métiers"
                : "1.4 Real-World Organizational Governance & 1-Click Business Pack Activation"
            }
            subtitle={
              isFr
                ? "Une hiérarchie naturelle (Plateforme entière ➔ Directions / BU ➔ Équipes ➔ Espaces de travail) enrichie par des Packs Métiers prêts à l'emploi."
                : "A natural hierarchy (Entire Platform ➔ Divisions / BUs ➔ Teams ➔ Workspaces) enriched by ready-to-use Business Packs."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="font-bold text-sm">
                  {isFr
                    ? "🏢 Hiérarchie d'Organisation : Plateforme entière ➔ Directions (BU) ➔ Équipes"
                    : "🏢 Organization Hierarchy: Entire Platform ➔ Divisions (BUs) ➔ Teams"}
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Les directives d'entreprise s'appliquent automatiquement à toute l'organisation, chaque Direction (BU) ou Équipe y ajoute ses normes métiers, et chaque Espace de travail rassemble les sources et exécutions d'un projet ou produit précis."
                    : "Enterprise directives apply automatically across the organization, each Division (BU) or Team layers its domain standards, and each Workspace gathers the sources and runs of a specific project or product."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="font-bold text-sm">
                  {isFr
                    ? "📦 Packs Métiers Prêts à l'Emploi & Déduplication Intelligente"
                    : "📦 Ready-to-Use Business Packs & Smart Deduplication"}
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Un Pack Métier regroupe des processus, des agents spécialisés, des règles de contrôle et des guides d'aide cohérents pour un métier donné. Il s'active ou se désactive en 1 clic sur le périmètre de votre choix."
                    : "A Business Pack bundles coherent processes, specialized agents, control rules, and help guides for a given domain. Enable or disable it in 1 click on your chosen scope."}
                </p>
              </div>
            </div>
          </OrciaSectionCard>
        </section>
      )}

      {/* =====================================================================
       * ESPACE 2 — 2. FONCTIONNALITÉS & ÉCRANS (GUIDE FONCTIONNEL)
       * RÈGLE D'ÉTANCHÉITÉ STRICTE : Zéro terme technique d'implémentation !
       * ===================================================================== */}
      {activeTab === "features" && (
        <section
          data-testid="showcase-pillar-features"
          className="orcia-ds-page"
        >
          {/* Volet A — Les 6 Dispositifs Concrets du Pilotage Humain */}
          <OrciaSectionCard
            testId="showcase-features-six-devices"
            title={
              isFr
                ? "Volet A — Les 6 Dispositifs Concrets du Pilotage Humain (Human-Led) et de la Fiabilité dans l'Interface"
                : "Part A — The 6 Concrete Human-Led & Reliability Devices in the Interface"
            }
            subtitle={
              isFr
                ? "Chaque garantie méthodologique se traduit par un composant visuel immédiatement reconnaissable par les équipes."
                : "Every methodological guarantee translates into a visual component immediately recognizable by teams."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div
                data-testid="showcase-device-1-human-anchor"
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-human-led-bg)",
                  borderColor: "var(--color-primary-dark)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm">
                    {isFr
                      ? "1. Carte d'Ancrage Humain (identité visuelle Violette réservée à la rédaction humaine)"
                      : "1. Human-Led Anchor Card (Violet visual identity reserved for human authoring)"}
                  </strong>
                  <StatusBadge label={isFr ? "Dispositif 1" : "Device 1"} tone="cobalt" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Signale visuellement les sections que seul un être humain peut rédiger et signer (objectifs, contraintes, contrat d'autonomie). Tant que l'auteur humain n'a pas saisi et signé son intention, l'étape ne peut pas démarrer."
                    : "Visually highlights sections that only a human can author and sign (objectives, constraints, autonomy contract). Until the human author enters and signs their intent, the step cannot start."}
                </p>
              </div>

              <div
                data-testid="showcase-device-2-arbitration-card"
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-arbitration-bg)",
                  borderColor: "var(--color-arbitration-amber)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm">
                    {isFr
                      ? "2. Carte d'Arbitrage en 1 Clic"
                      : "2. 1-Click Arbitration Decision Card"}
                  </strong>
                  <StatusBadge label={isFr ? "Dispositif 2" : "Device 2"} tone="amber" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Expose clairement un dilemme ou une contradiction entre deux sources en comparant les options, leurs impacts et leurs preuves. Le décideur tranche en 1 clic ou ajoute sa propre directive."
                    : "Clearly exposes a dilemma or contradiction between two sources by comparing options, impacts, and evidence. The decision-maker resolves it in 1 click or adds a custom directive."}
                </p>
              </div>

              <div
                data-testid="showcase-device-3-briefing-grid"
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm">
                    {isFr
                      ? "3. Grille de Relecture en 4 Blocs & Validation par Section"
                      : "3. 4-Block Review Briefing Grid & Section-by-Section Validation"}
                  </strong>
                  <StatusBadge label={isFr ? "Dispositif 3" : "Device 3"} tone="cobalt" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Synthétise tout livrable en 4 encadrés (Résumé, Éléments clés, Décisions prises, Hypothèses retenues) accompagnés du découpage du document où chaque section est Approuvée, Co-éditée ou Contestée."
                    : "Summarizes every deliverable into 4 boxes (Summary, Key Elements, Decisions Taken, Assumptions Retained) paired with document chunks where each section is Approved, Co-edited, or Challenged."}
                </p>
              </div>

              <div
                data-testid="showcase-device-4-impact-simulator"
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm">
                    {isFr
                      ? "4. Simulateur d'Impact Amont & Retour en Arrière Ciblé"
                      : "4. Upstream Impact Simulator & Targeted Rewind"}
                  </strong>
                  <StatusBadge label={isFr ? "Dispositif 4" : "Device 4"} tone="amber" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Permet de corriger une décision prise lors d'une étape précédente en visualisant d'abord toutes les étapes aval impactées, puis en relançant uniquement la branche concernée."
                    : "Lets you amend a decision made in an earlier step by first previewing all impacted downstream steps, then re-running only the affected branch."}
                </p>
              </div>

              <div
                data-testid="showcase-device-5-verified-citations"
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-gate-emerald-bg)",
                  borderColor: "var(--color-gate-emerald)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm">
                    {isFr
                      ? "5. Citations Vérifiées ([S1], [G1], [O1]) & Glossaire Métier (À valider)"
                      : "5. Verified Citations ([S1], [G1], [O1]) & Business Glossary (To Validate)"}
                  </strong>
                  <StatusBadge label={isFr ? "Dispositif 5" : "Device 5"} tone="emerald" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Relie chaque affirmation aux sources documentaires ([S1]), aux termes du glossaire ([G1]) et aux vérifications d'outils ([O1]). Les nouveaux termes métiers proposés sont plafonnés à 15 dans la file « À valider »."
                    : "Links every statement to documentary sources ([S1]), glossary terms ([G1]), and tool checks ([O1]). Newly proposed business terms are capped at 15 in the 'To Validate' queue."}
                </p>
              </div>

              <div
                data-testid="showcase-device-6-team-claim"
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <strong className="text-sm">
                    {isFr
                      ? "6. Prise en Charge Exclusive en Équipe & Niveaux d'Observation (Contributeur vs Observateur)"
                      : "6. Exclusive Team Claim & Observation Levels (Contributor vs Observer)"}
                  </strong>
                  <StatusBadge label={isFr ? "Dispositif 6" : "Device 6"} tone="cobalt" />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Évite que deux membres d'une équipe ne modifient la même étape en même temps grâce à un badge de prise en charge en temps réel, et protège les périmètres supervisés en lecture seule (Observateur)."
                    : "Prevents two team members from editing the same step simultaneously through a real-time claim badge, and protects supervised scopes in read-only Observer mode."}
                </p>
              </div>
            </div>
          </OrciaSectionCard>

          {/* Volet B — Les 9 Écrans du Menu d'ORCIA expliqués un par un */}
          <OrciaSectionCard
            testId="showcase-features-nine-screens"
            title={
              isFr
                ? "Volet B — Les 9 Écrans du Menu d'ORCIA expliqués un par un"
                : "Part B — The 9 Screens of the ORCIA Menu Explained One by One"
            }
            subtitle={
              isFr
                ? "Cliquez sur « Ouvrir cet écran » pour naviguer directement vers la fonctionnalité correspondante dans l'application."
                : "Click 'Open this screen' to navigate directly to the corresponding feature in the application."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              {NINE_SCREENS_GUIDE.map((scr) => (
                <div
                  key={scr.id}
                  data-testid={`showcase-screen-card-${scr.id}`}
                  className="rounded-lg border p-4 flex flex-col justify-between gap-3"
                  style={{
                    backgroundColor: "var(--color-bg-elevated)",
                    borderColor: "var(--color-border-subtle)",
                  }}
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <strong className="text-sm">
                        {isFr ? scr.titleFr : scr.titleEn}
                      </strong>
                      <StatusBadge label={scr.route} tone="cobalt" monospace />
                    </div>
                    <p style={{ color: "var(--color-text-secondary)" }}>
                      {isFr ? scr.summaryFr : scr.summaryEn}
                    </p>
                    <ul
                      className="space-y-1 list-disc list-inside"
                      style={{ color: "var(--color-text-primary)" }}
                    >
                      {(isFr ? scr.keyActionsFr : scr.keyActionsEn).map((act, i) => (
                        <li key={i}>{act}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="pt-2 border-t flex justify-end" style={{ borderColor: "var(--color-border-subtle)" }}>
                    <OrciaButton
                      testId={`showcase-navigate-screen-${scr.id}`}
                      variant="secondary"
                      onClick={() => onNavigateToRoute?.(scr.route)}
                    >
                      {isFr ? `Ouvrir ${scr.route} →` : `Open ${scr.route} →`}
                    </OrciaButton>
                  </div>
                </div>
              ))}
            </div>
          </OrciaSectionCard>
        </section>
      )}

      {/* =====================================================================
       * ESPACE 3 — 3. ARCHITECTURE & CHOIX TECHNIQUES (SOUS LE CAPOT)
       * ICI (ET UNIQUEMENT ICI) SONT EXPOSÉS LA STACK ET LES CHOIX D'INGÉNIERIE
       * ===================================================================== */}
      {activeTab === "architecture" && (
        <section
          data-testid="showcase-pillar-architecture"
          className="orcia-ds-page"
        >
          {/* 3.1 Monolithe Modulaire Hybride & Isolation Hexagonale */}
          <OrciaSectionCard
            testId="showcase-arch-modular-monolith"
            title={
              isFr
                ? "3.1 Monolithe Modulaire Hybride (TypeScript / Python 3.12+) & Isolation Hexagonale"
                : "3.1 Hybrid Modular Monolith (TypeScript / Python 3.12+) & Hexagonal Isolation"
            }
            subtitle={
              isFr
                ? "Graphe acyclique de packages vérifié par `lint-imports` (5 contrats) et `lint_spine.py` contre `ARCHITECTURE-SPINE.md`."
                : "Acyclic package graph verified by `lint-imports` (5 contracts) and `lint_spine.py` against `ARCHITECTURE-SPINE.md`."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="font-bold text-sm">
                  {isFr
                    ? "Frontière Frontend SPA Pure (`pnpm 10.6` + `Turborepo 2.4`)"
                    : "Pure SPA Frontend Boundary (`pnpm 10.6` + `Turborepo 2.4`)"}
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Application SPA `Vite 6.4` + `TanStack Router 1.166` (`React 19.1`, `Tailwind CSS 4.3`) découpée en 8 modules `@orcia/web/src/features/<domaine>/`, consommant exclusivement la librairie Design System isolée `@orcia/ui` (`packages/ui`) et le SDK `@orcia/api-client` généré depuis OpenAPI 3.1 (`0-diff`)."
                    : "Pure SPA built with `Vite 6.4` + `TanStack Router 1.166` (`React 19.1`, `Tailwind CSS 4.3`) sliced into 8 `@orcia/web/src/features/<domain>/` modules, consuming exclusively the isolated `@orcia/ui` Design System and the OpenAPI 3.1 `@orcia/api-client` SDK (`0-diff`)."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="font-bold text-sm">
                  {isFr
                    ? "Noyau Python 3.12+ Hexagonal (`uv 0.13.5` Workspace)"
                    : "Hexagonal Python 3.12+ Core (`uv 0.13.5` Workspace)"}
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Flux strictement unidirectionnel `orcia-kernel` ← `orcia-core` (8 domaines sans cycle, zéro import `fastapi` / `sqlalchemy` / `dbos` / `dramatiq` / `redis` / `litellm` / `docling` / `wasmtime` dans `domain/` et `ports/`) ← `apps/api` (`FastAPI`, schémas Pydantic v2, RFC 9457) & `apps/worker`."
                    : "Strictly unidirectional flow `orcia-kernel` ← `orcia-core` (8 acyclic domains, zero `fastapi` / `sqlalchemy` / `dbos` / `dramatiq` / `redis` / `litellm` / `docling` / `wasmtime` imports in `domain/` and `ports/`) ← `apps/api` (`FastAPI`, Pydantic v2 schemas, RFC 9457) & `apps/worker`."}
                </p>
              </div>
            </div>
          </OrciaSectionCard>

          {/* 3.2 Implémentation Technique des Garanties Human-Led */}
          <OrciaSectionCard
            testId="showcase-arch-human-led-impl"
            title={
              isFr
                ? "3.2 Implémentation Technique des Garanties « Human-Led »"
                : "3.2 Technical Implementation of 'Human-Led' Guarantees"
            }
            subtitle={
              isFr
                ? "Comment le backend FastAPI, PostgreSQL 18 et Redis 7.4 verrouillent matériellement l'autorité humaine."
                : "How FastAPI, PostgreSQL 18, and Redis 7.4 materially enforce human authority."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-human-led-bg)",
                  borderColor: "var(--color-primary-dark)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "Signatures `SHA-256` dans `human_anchor_signatures`"
                    : "`SHA-256` Signatures in `human_anchor_signatures`"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Rejet matériel `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED` sur toute écriture provenant d'une identité d'agent sur un champ `human_authored_required: true`, y compris sur le serveur MCP entrant `GovernedMcpServerService` (`/api/v1/mcp`)."
                    : "Material `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED` rejection on any agent-initiated write targeting a `human_authored_required: true` field, including through `GovernedMcpServerService` (`/api/v1/mcp`)."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "`AdaptiveHumanGateService` & Garde Anti-Rubber-Stamping `< 15 s`"
                    : "`AdaptiveHumanGateService` & `< 15 s` Anti-Rubber-Stamping Guard"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Table `chunk_approvals` bloquant la transition tant qu'un tronçon est en attente (`ERR_UNAPPROVED_CHUNKS_REMAINING`) et garde temporel rejetant les validations d'artefacts > 1 000 mots soumises en moins de 15 secondes (`ERR_RUBBER_STAMPING_GUARD_TRIGGERED`)."
                    : "`chunk_approvals` table blocking transition while any chunk remains unapproved (`ERR_UNAPPROVED_CHUNKS_REMAINING`) and time guard rejecting approvals of > 1,000-word artifacts submitted in under 15 seconds (`ERR_RUBBER_STAMPING_GUARD_TRIGGERED`)."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "Verrous Atomiques Redis 7.4 & Baux `ResourceLeaseService`"
                    : "Atomic Redis 7.4 Locks & `ResourceLeaseService` Leases"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Prise en charge d'équipe par `SET lock:step:<id> <user_id> NX EX 900` relayée en SSE (`< 500 ms`), baux PostgreSQL `resource_leases` avec jetons de fencing monotones transmis à `ConnectorPort.invoke`, et `RunAccessGuard` rejetant `READ_ONLY_OBSERVER` avec `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`."
                    : "Team claim via `SET lock:step:<id> <user_id> NX EX 900` broadcast over SSE (`< 500 ms`), PostgreSQL `resource_leases` with monotonic fencing tokens passed to `ConnectorPort.invoke`, and `RunAccessGuard` rejecting `READ_ONLY_OBSERVER` with `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "`ExternalEditRebaser` (`HUMAN_AMENDED_EXTERNAL`) & Actions Staged"
                    : "`ExternalEditRebaser` (`HUMAN_AMENDED_EXTERNAL`) & Staged Actions"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Diff structurel Markdown/AST marquant les modifications humaines faites hors plateforme en `HUMAN_AMENDED_EXTERNAL` (inviolables par l'agent aval), actions externes préparées dans `draft_artifact_jsonb` signées par `run-lock.json`, et verrou `ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE`."
                    : "Structural Markdown/AST diff marking external human edits as `HUMAN_AMENDED_EXTERNAL` (inviolable by downstream agents), staged actions in `draft_artifact_jsonb` signed with `run-lock.json`, and `ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE` guard."}
                </p>
              </div>
            </div>
          </OrciaSectionCard>

          {/* 3.3 Implémentation des Mécanismes Déterministes */}
          <OrciaSectionCard
            testId="showcase-arch-deterministic-impl"
            title={
              isFr
                ? "3.3 Implémentation des Mécanismes Déterministes (Zéro Hallucination, Reproductibilité & Sandboxes)"
                : "3.3 Deterministic Mechanisms Implementation (Zero Hallucination, Reproducibility & Sandboxes)"
            }
            subtitle={
              isFr
                ? "Validation statique DAG, `run-lock.json` sur SeaweedFS CAS, Wasmtime Palier 1a, Starlark + RE2 O(n) Palier 1b, gVisor Palier 2 et vérificateur de citations `< 5 ms`."
                : "Static DAG validation, `run-lock.json` on SeaweedFS CAS, Tier 1a Wasmtime, Tier 1b Starlark + RE2 O(n), Tier 2 gVisor, and `< 5 ms` citation verifier."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-gate-emerald-bg)",
                  borderColor: "var(--color-gate-emerald)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "`WorkflowYamlValidator` & `RunLockService` (`SeaweedFS 4.17` CAS)"
                    : "`WorkflowYamlValidator` & `RunLockService` (`SeaweedFS 4.17` CAS)"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Détection statique des cycles DAG (`ERR_WORKFLOW_CYCLE_DETECTED`), profondeur `SUB_WORKFLOW <= 3` et ancres obligatoires (`ERR_WORKFLOW_ANCHOR_MISSING`). Épinglage `SHA-256` immuable de chaque source et sous-workflow dans `run_lock_jsonb` et `cas/<sha256>`."
                    : "Static detection of DAG cycles (`ERR_WORKFLOW_CYCLE_DETECTED`), `SUB_WORKFLOW <= 3` depth, and required anchors (`ERR_WORKFLOW_ANCHOR_MISSING`). Immutable `SHA-256` pinning of every source and sub-workflow in `run_lock_jsonb` and `cas/<sha256>`."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "Sandbox Palier 1a (`Wasmtime` / `SubprocessTier1SandboxAdapter`)"
                    : "Tier 1a Sandbox (`Wasmtime` / `SubprocessTier1SandboxAdapter`)"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Exécution isolée `< 5 000 ms`, `256 MB` RAM, zéro réseau pour les validateurs structurels universels : JSON Schema, contrat Markdown, axiomes et détection de Pattern Drift contre `ARCHITECTURE-SPINE.md`."
                    : "Isolated `< 5,000 ms`, `256 MB` RAM, zero-network execution for universal structural validators: JSON Schema, Markdown contract, axioms, and Pattern Drift detection against `ARCHITECTURE-SPINE.md`."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "Compilateur `Text-to-Starlark` & Sandbox Palier 1b (`StarlarkMechanismSandbox`)"
                    : "`Text-to-Starlark` Compiler & Tier 1b Sandbox (`StarlarkMechanismSandbox`)"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Exécution `< 2 ms` (`0 $` LLM au Run-Time) de règles métiers `Starlark` adossées à `google-re2` garantissant une complexité linéaire O(n) anti-ReDoS pour la chaîne causale `DIRECTIVE ➔ NORME ➔ MÉCANISME`, avec auto-test `passing_test_payload` / `failing_test_payload`."
                    : "`< 2 ms` (`$0` runtime LLM cost) execution of `Starlark` business rules backed by `google-re2` guaranteeing linear O(n) anti-ReDoS complexity for the `DIRECTIVE ➔ NORM ➔ MECHANISM` causal chain, with `passing_test_payload` / `failing_test_payload` self-tests."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "Sandbox Palier 2 (`BimodalSandboxAdapter`) & Vérificateur de Citations `< 5 ms`"
                    : "Tier 2 Sandbox (`BimodalSandboxAdapter`) & `< 5 ms` Citation Verifier"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Conteneur isolé `gVisor/Rootless < 60 s` (`--network=none`, snapshot CAS lecture seule) exécutant `pytest`, `vitest`, `ruff`, `mypy`, `tsc`. En sortie de stream, `AssistantCitationAndV5GuardService` vérifie en `< 5 ms` chaque citation `[S1]`, `[G1]`, `[O1]` contre `citation_map` et `READ_SOURCE`."
                    : "Isolated `gVisor/Rootless < 60 s` container (`--network=none`, read-only CAS snapshot) running `pytest`, `vitest`, `ruff`, `mypy`, `tsc`. Post-stream, `AssistantCitationAndV5GuardService` verifies every `[S1]`, `[G1]`, `[O1]` citation in `< 5 ms` against `citation_map` and `READ_SOURCE`."}
                </p>
              </div>
            </div>
          </OrciaSectionCard>

          {/* 3.4 Implémentation des Mécanismes Probabilistes Gouvernés */}
          <OrciaSectionCard
            testId="showcase-arch-probabilistic-impl"
            title={
              isFr
                ? "3.4 Implémentation des Mécanismes Probabilistes Gouvernés (Orthogonalité des Modèles, RAG Hybride & Replay Ciblé)"
                : "3.4 Governed Probabilistic Mechanisms (Model Orthogonality, Hybrid RAG & Targeted Replay)"
            }
            subtitle={
              isFr
                ? "Juge orthogonal multi-familles à 5 lentilles, recherche hybride `PostgreSQL 18` + `pgvector` `halfvec(1024)` + `RRF (k=60)` et orchestration durable `DBOS Transact 2.14`."
                : "Cross-family 5-lens orthogonal judge, `PostgreSQL 18` + `pgvector` `halfvec(1024)` + `RRF (k=60)` hybrid search, and `DBOS Transact 2.14` durable orchestration."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "`AgenticGateService` & `CognitiveRouterService`"
                    : "`AgenticGateService` & `CognitiveRouterService`"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Impose `evaluator_model_family != executor_model_family` (`ERR_MODEL_ORTHOGONALITY_VIOLATION`) à l'intérieur du `SovereigntyTier` (`C0..C3`), purge la chaîne de pensée (CoT) de l'exécuteur et exécute en parallèle les 5 lentilles d'audit (dont `fact_verification`)."
                    : "Enforces `evaluator_model_family != executor_model_family` (`ERR_MODEL_ORTHOGONALITY_VIOLATION`) within the `SovereigntyTier` (`C0..C3`), purges executor Chain-of-Thought (CoT), and runs the 5 audit lenses in parallel (including `fact_verification`)."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "RAG Hybride `PostgreSQL 18` + `pgvector 0.8.7` + `RRF (k=60)`"
                    : "Hybrid RAG `PostgreSQL 18` + `pgvector 0.8.7` + `RRF (k=60)`"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Ingestion documentaire via `Docling` sur workers `Dramatiq`, vecteurs `halfvec(1024)` indexés HNSW combinés à la recherche plein texte `tsvector` (`ts_rank_cd`) par Reciprocal Rank Fusion `RRF (k=60)`, Graphe Tripartite (`WITH RECURSIVE depth <= 2`) et détection `auditDocVsCode`."
                    : "Document ingestion via `Docling` on `Dramatiq` workers, HNSW-indexed `halfvec(1024)` vectors combined with `tsvector` (`ts_rank_cd`) full-text search via Reciprocal Rank Fusion `RRF (k=60)`, Tripartite Graph (`WITH RECURSIVE depth <= 2`), and `auditDocVsCode`."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "`DBOS Transact 2.14` & `UpstreamChallengeAndReplayService`"
                    : "`DBOS Transact 2.14` & `UpstreamChallengeAndReplayService`"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Orchestration durable sur `PostgreSQL 18` via `SQLAlchemy 2.1 Asyncio`, table append-only `blackboard_snapshots` protégée par trigger `BEFORE UPDATE OR DELETE RAISE EXCEPTION`, calcul d'impact DAG via `input_uris` et fork ciblé à l'étape N avec `0` token amont consommé."
                    : "Durable orchestration on `PostgreSQL 18` via `SQLAlchemy 2.1 Asyncio`, append-only `blackboard_snapshots` table protected by `BEFORE UPDATE OR DELETE RAISE EXCEPTION` trigger, DAG impact calculation via `input_uris`, and targeted fork at Step N with `0` upstream tokens consumed."}
                </p>
              </div>
            </div>
          </OrciaSectionCard>

          {/* 3.5 Sécurité, Cryptographie & Design System @orcia/ui */}
          <OrciaSectionCard
            testId="showcase-arch-security-and-ds"
            title={
              isFr
                ? "3.5 Sécurité, Cryptographie & Design System `@orcia/ui`"
                : "3.5 Security, Cryptography & `@orcia/ui` Design System"
            }
            subtitle={
              isFr
                ? "Authentification bi-mode, chiffrement par enveloppe DEK/KEK, scrubbing PII réversible et isolation en 3 couches du Design System."
                : "Bi-mode authentication, DEK/KEK envelope encryption, reversible PII scrubbing, and 3-layer Design System isolation."
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "`OIDC PKCE` + `Argon2id / TOTP` & Enveloppe `DEK/KEK`"
                    : "`OIDC PKCE` + `Argon2id / TOTP` & `DEK/KEK` Envelope"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "Protection anti-First-User Takeover par `LOCK TABLE users IN EXCLUSIVE MODE`, coffre `EnvelopeVaultSecretProvider` (DEK/KEK par Workspace, `SecretRef` non-sérialisable), `PiiReversibleScrubber` sous TTL Redis, et neutralisation anti-LastPass sur tous les secrets techniques hors `/login`."
                    : "Anti-First-User Takeover protection via `LOCK TABLE users IN EXCLUSIVE MODE`, `EnvelopeVaultSecretProvider` vault (per-Workspace DEK/KEK, non-serializable `SecretRef`), Redis-TTL `PiiReversibleScrubber`, and anti-LastPass protection on all technical inputs outside `/login`."}
                </p>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-1.5"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? "Séparation 3 Couches : `@orcia/ui` (`tokens.css`) / `i18n` / `@orcia/api-client`"
                    : "3-Layer Separation: `@orcia/ui` (`tokens.css`) / `i18n` / `@orcia/api-client`"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {isFr
                    ? "100 % des variables CSS sémantiques et classes `.orcia-ds-*` résident dans `packages/ui/src/styles/tokens.css`. `@orcia/ui` ne contient aucun appel réseau ni dépendance de routage, les textes FR/EN sont typés de bout en bout, et le contrat OpenAPI 3.1 est vérifié à `0-diff`."
                    : "100% of semantic CSS variables and `.orcia-ds-*` classes live in `packages/ui/src/styles/tokens.css`. `@orcia/ui` has zero network or router dependencies, FR/EN dictionaries are strictly typed end-to-end, and the OpenAPI 3.1 contract is verified at `0-diff`."}
                </p>
              </div>
            </div>
          </OrciaSectionCard>
        </section>
      )}

      {/* =====================================================================
       * ESPACE 4 — 4. 🔄 HISTORIQUE DES ÉVOLUTIONS & STATISTIQUES VIVANTES
       * Alimenté automatiquement par `infra/scripts/sync_site_catalog.py`
       * ===================================================================== */}
      {activeTab === "changelog" && (
        <section
          data-testid="showcase-pillar-changelog"
          className="orcia-ds-page"
        >
          {/* Compteurs vivants du dépôt */}
          <OrciaSectionCard
            testId="showcase-changelog-live-stats"
            title={
              isFr
                ? "4.1 Métriques Vivantes du Dépôt ORCIA (Synchronisées par `pnpm site:sync`)"
                : "4.1 Live ORCIA Repository Metrics (Synchronized by `pnpm site:sync`)"
            }
            subtitle={
              isFr
                ? "Ces compteurs sont extraits automatiquement du code source réel et vérifiés en intégration continue (`pnpm site:check`)."
                : "These counters are automatically extracted from the live source tree and verified in continuous integration (`pnpm site:check`)."
            }
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div
                data-testid="showcase-stat-routes"
                className="rounded-lg border p-3 text-center"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="text-lg font-bold" style={{ color: "var(--color-action-primary)" }}>
                  {manifest.stats.activeRoutesCount}
                </div>
                <div style={{ color: "var(--color-text-secondary)" }}>
                  {isFr ? "Routes Web Actives" : "Active Web Routes"}
                </div>
              </div>

              <div
                data-testid="showcase-stat-primitives"
                className="rounded-lg border p-3 text-center"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="text-lg font-bold" style={{ color: "var(--color-action-primary)" }}>
                  {manifest.stats.uiPrimitivesCount}
                </div>
                <div style={{ color: "var(--color-text-secondary)" }}>
                  {isFr ? "Primitives @orcia/ui" : "@orcia/ui Primitives"}
                </div>
              </div>

              <div
                data-testid="showcase-stat-migrations"
                className="rounded-lg border p-3 text-center"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="text-lg font-bold" style={{ color: "var(--color-action-primary)" }}>
                  {manifest.stats.alembicMigrationsCount}
                </div>
                <div style={{ color: "var(--color-text-secondary)" }}>
                  {isFr ? "Migrations Alembic" : "Alembic Migrations"}
                </div>
              </div>

              <div
                data-testid="showcase-stat-reports"
                className="rounded-lg border p-3 text-center"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="text-lg font-bold" style={{ color: "var(--color-action-primary)" }}>
                  {manifest.stats.techLeadReportsCount}
                </div>
                <div style={{ color: "var(--color-text-secondary)" }}>
                  {isFr ? "Rapports Tech Lead" : "Tech Lead Reports"}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 text-xs">
              <div
                className="rounded-lg border p-3.5 space-y-2"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div className="flex items-center justify-between">
                  <strong className="text-sm">
                    {isFr
                      ? `Packs Métiers Installés (${manifest.stats.installedPacksCount})`
                      : `Installed Business Packs (${manifest.stats.installedPacksCount})`}
                  </strong>
                  <ContextualInfoTriggerButton
                    sectionId="showcase-packs"
                    label={
                      isFr
                        ? "Comprendre les Packs Métiers détectés dans packages/orcia-pack-*"
                        : "Understand Business Packs detected in packages/orcia-pack-*"
                    }
                    onOpenHelpSection={onOpenHelpSection}
                  />
                </div>
                <div className="space-y-1.5">
                  {manifest.installedPacks.map((pack) => (
                    <div
                      key={pack.key}
                      className="orcia-ds-row"
                    >
                      <StatusBadge
                        label={`${pack.key}@${pack.version}`}
                        tone="emerald"
                        monospace
                      />
                      <span style={{ color: "var(--color-text-secondary)" }}>
                        {pack.description}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div
                className="rounded-lg border p-3.5 space-y-2"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <strong className="text-sm">
                  {isFr
                    ? `Versions de la Stack (ARCHITECTURE-SPINE.md · ${manifest.stats.stackComponentsCount} briques)`
                    : `Locked Stack Versions (ARCHITECTURE-SPINE.md · ${manifest.stats.stackComponentsCount} items)`}
                </strong>
                <div className="max-h-[220px] overflow-y-auto space-y-1">
                  {manifest.stackComponents.map((comp) => (
                    <div key={comp.name} className="orcia-ds-row">
                      <span className="font-semibold">{comp.name}</span>
                      <StatusBadge label={comp.version} tone="cobalt" monospace />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </OrciaSectionCard>

          {/* Chronologie complète des Rapports Tech Lead */}
          <OrciaSectionCard
            testId="showcase-changelog-reports-card"
            title={
              isFr
                ? `4.2 Chronologie Vivante des Rapports Tech Lead (${filteredReports.length} / ${manifest.stats.techLeadReportsCount})`
                : `4.2 Living Tech Lead Reports Timeline (${filteredReports.length} / ${manifest.stats.techLeadReportsCount})`
            }
            subtitle={
              isFr
                ? "Extraite automatiquement de `docs/implementation-artifacts/tech-lead-reports/README.md`."
                : "Automatically extracted from `docs/implementation-artifacts/tech-lead-reports/README.md`."
            }
          >
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              spellCheck={false}
              data-testid="showcase-changelog-search-input"
              value={changelogFilter}
              onChange={(e) => setChangelogFilter(e.target.value)}
              placeholder={
                isFr
                  ? "Filtrer l'historique par date, Story, domaine ou mot-clé..."
                  : "Filter changelog by date, Story, domain, or keyword..."
              }
              className="orcia-ds-input w-full"
            />

            <div
              data-testid="showcase-changelog-reports-list"
              className="space-y-2.5 max-h-[600px] overflow-y-auto"
            >
              {filteredReports.map((rep) => (
                <article
                  key={rep.reportFile}
                  data-testid={`showcase-report-item-${rep.reportFile}`}
                  className="rounded-lg border p-3.5 space-y-1.5 text-xs"
                  style={{
                    backgroundColor: "var(--color-bg-elevated)",
                    borderColor: "var(--color-border-subtle)",
                  }}
                >
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2 flex-wrap">
                      <StatusBadge label={rep.date} tone="cobalt" monospace />
                      <StatusBadge label={rep.phaseOrStory} tone="emerald" />
                    </div>
                    <span
                      className="font-mono text-[11px]"
                      style={{ color: "var(--color-text-secondary)" }}
                    >
                      {rep.reportFile}
                    </span>
                  </div>
                  <div className="font-bold text-sm" style={{ color: "var(--color-text-primary)" }}>
                    {rep.domain}
                  </div>
                  <p style={{ color: "var(--color-text-secondary)" }}>
                    {rep.summary}
                  </p>
                </article>
              ))}
            </div>
          </OrciaSectionCard>
        </section>
      )}
    </div>
  );
}
