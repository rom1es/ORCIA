import type { ConfiguredWorkflowItem } from "../../components/platformSetupStore";

export function buildOrciaDocumentationWorkflowSpec(
  isFr: boolean,
  status: "DRAFT" | "PUBLISHED" = "PUBLISHED",
): ConfiguredWorkflowItem {
  return {
    workflowKey: "generate-orcia-documentation",
    title: isFr
      ? "Processus 6 — Générer et Synchroniser la Documentation Complète d'ORCIA (Guides Écrans, FAQ Architecture & Catalogue)"
      : "Process 6 — Generate and Synchronize Full ORCIA Documentation (Screen Guides, Architecture FAQ & Catalog)",
    version: "1.0.0",
    status,
    prePrompt: isFr
      ? "Recenser les écrans et routes d'ORCIA, rédiger et synchroniser les guides fonctionnels par écran (FR/EN) et la FAQ d'architecture, contrôler la conformité documentaire, puis publier les fiches d'aide et le catalogue."
      : "Inventory ORCIA screens and routes, author and synchronize bilingual screen guides (FR/EN) and the architecture FAQ, run deterministic quality checks, then publish help articles and the catalog.",
    prePromptSha256:
      "a4b9c2f18d7e6034521983746501928374650192837465019283746501928374", // pragma: allowlist secret
    requiredParams: ["langues", "perimetre_routes", "inclure_faq_architecture"],
    requiredMarkdownSections: [
      "Objectif",
      "Guide Fonctionnel par Écran",
      "Architecture & Modèle Métier",
      "Questions Fréquentes (FAQ)",
    ],
    triggers: ["manual"],
    layers: [
      {
        layerId: "layer-doc-inventory",
        label: isFr
          ? "1. Inventaire du dépôt ORCIA (20 routes UI, primitives @orcia/ui, fiches FR/EN, FAQ & rapports)"
          : "1. ORCIA repository inventory (20 UI routes, @orcia/ui primitives, FR/EN guides, FAQ & reports)",
        zone: "inputs",
        orderIndex: 1,
        enabled: true,
      },
      {
        layerId: "layer-doc-authoring",
        label: isFr
          ? "2. Génération & enrichissement des guides et de la FAQ (@Rédacteur-Documentation-Orcia & @Architecte-Métier-Pack)"
          : "2. Screen guides & FAQ authoring (@Rédacteur-Documentation-Orcia & @Architecte-Métier-Pack)",
        zone: "capabilities",
        orderIndex: 2,
        enabled: true,
      },
      {
        layerId: "layer-doc-validation",
        label: isFr
          ? "3. Contrôle qualité déterministe (routes liées, sections obligatoires, zéro secret ni jargon)"
          : "3. Deterministic quality check (bound routes, mandatory sections, zero secret or internal jargon)",
        zone: "capabilities",
        orderIndex: 3,
        enabled: true,
      },
      {
        layerId: "layer-doc-publish",
        label: isFr
          ? "4. Publication & rattachement à chaud (docs/help/ FR/EN & site de documentation /showcase)"
          : "4. Hot attachment & publication (docs/help/ FR/EN & /showcase documentation site)",
        zone: "deliverables",
        orderIndex: 4,
        enabled: true,
      },
    ],
  };
}

export function buildGeneratedDocumentationMarkdown(isFr: boolean): string {
  if (!isFr) {
    return [
      "# ORCIA Complete Documentation — Screen Guides, Architecture & FAQ",
      "",
      "## Objectif",
      "Provide a unified, up-to-date reference covering every ORCIA screen, the organizational domain model, and frequently asked questions.",
      "",
      "## Guide Fonctionnel par Écran",
      "- **Cockpit**: Monitor active processes, pending human decisions, and workspace indicators.",
      "- **My Assistant**: Converse with your AI assistant, select reasoning effort, and organize work into folders.",
      "- **My Spaces**: Manage project sources, business rules, glossary terms, and deliverables.",
      "- **My Agents & My Processes**: Configure specialized agents, skills, and reusable multi-step processes.",
      "- **Administration & Activity Log**: Govern user accounts, authentication, AI models, connectors, packs, and full audit history.",
      "",
      "## Architecture & Business Model",
      "- **Business Units (BU) & Billing Teams**: Teams group members and carry AI consumption budgets.",
      "- **Workspaces**: Every workspace (shared, private, or confidential) is attached to a billing team and inherits organization rules.",
      "",
      "## Frequently Asked Questions (FAQ)",
      "- **What is the difference between a Team and a Workspace?** A Team represents people and budget ownership; a Workspace isolates project documents, glossary terms, and deliverables.",
      "- **How do I refresh contextual help across screens?** Run the « Génération de la documentation ORCIA » process from `☍ My Processes`.",
    ].join("\n");
  }

  return [
    "# Documentation Complète d'ORCIA — Guides Écrans, Architecture & FAQ",
    "",
    "## Objectif",
    "Fournir un référentiel unifié et à jour couvrant l'ensemble des écrans d'ORCIA, le modèle métier d'organisation et les réponses aux questions fréquentes.",
    "",
    "## Guide Fonctionnel par Écran",
    "- **Cockpit** : Superviser les processus en cours, les arbitrages humains en attente et l'avancement des espaces.",
    "- **Mon Assistant** : Dialoguer avec l'assistant IA, choisir le niveau de réflexion et classer ses échanges par dossiers.",
    "- **Mes Espaces** : Gérer les sources documentaires, les règles métiers, le glossaire et les livrables d'un projet.",
    "- **Mes Agents & Mes Processus** : Configurer les agents spécialisés, leurs compétences et les processus gouvernés.",
    "- **Administration & Journal d'Activité** : Administrer les habilitations, l'authentification, les modèles IA, les connecteurs et la traçabilité.",
    "",
    "## Architecture & Modèle Métier",
    "- **Directions (BU) & Équipes de facturation** : L'Équipe regroupe les utilisateurs et porte le rattachement budgétaire des appels IA.",
    "- **Espaces de Travail** : Chaque espace (collectif, privé personnel ou confidentiel) est rattaché à une équipe et hérite des règles de l'organisation.",
    "",
    "## Questions Fréquentes (FAQ)",
    "- **Quelle est la différence entre une Équipe et un Espace de travail ?** L'Équipe porte les membres et le budget, tandis que l'Espace de travail isole les documents, le glossaire et les livrables d'un projet.",
    "- **Comment mettre à jour l'aide contextuelle d'un écran ?** Lancez en 1 clic le processus « Génération de la Documentation ORCIA » depuis `☍ Mes Processus`.",
  ].join("\n");
}
