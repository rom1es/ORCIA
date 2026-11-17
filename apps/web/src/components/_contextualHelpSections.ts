import type { UiContextualHelpSectionItem } from "@orcia/ui";

const SHARED_WORKFLOW_FINOPS_FR: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "workflows-overview",
    title: "À quoi sert l'Atelier de Processus ?",
    body: "Un Processus est une suite d'étapes réutilisable qui combine vos agents IA et vos points de validation humaine pour produire un livrable fiable (ex. revue de contrat, analyse de demande client). Créez-le en brouillon puis publiez-le lorsqu'il est prêt à être lancé.",
    category: "steps",
  },
  {
    sectionId: "workflows-instructions",
    title: "Comment rédiger l'objectif et les instructions du processus ?",
    body: "Décrivez en langage naturel ce que vos agents doivent accomplir étape par étape : quelles sources consulter, quels points de vigilance vérifier et quel ton adopter dans la synthèse.",
    category: "steps",
  },
  {
    sectionId: "workflows-deliverable-contract",
    title: "Informations demandées au lancement et structure du livrable (optionnel)",
    body: "Indiquez les informations qui seront demandées à l'utilisateur au lancement du processus (ex. nom du fournisseur, montant) ainsi que les grandes rubriques qui devront obligatoirement figurer dans le document final.",
    category: "terms",
  },
  {
    sectionId: "workflows-steps-layers",
    title: "Les 3 grandes étapes d'exécution d'un processus",
    body: "Chaque processus s'exécute en 3 temps : 1) Collecte des documents et du contexte de votre Espace, 2) Analyse par les agents IA et vérification croisée des règles métiers, 3) Validation humaine finale avant diffusion du livrable.",
    category: "steps",
  },
  {
    sectionId: "audit-overview",
    title: "Journal d'activité : auteurs, horodatage et filtres d'observation",
    body: "Le Journal d'Activité (accessible depuis le menu de gauche 📜 Journal d'Activité) trace qui a effectué chaque action, à quelle date/heure et sur quel périmètre (filtré par défaut sur votre niveau d'observation actif). Vous pouvez filtrer par utilisateur, sur les 50 / 100 / 200 / 500 derniers événements ou sur une fenêtre temporelle. Le suivi des coûts et des budgets par espace est quant à lui géré séparément dans l'écran 📊 Coûts & Activité.",
    category: "faq",
  },
  {
    sectionId: "finops-overview",
    title: "Gouvernance des coûts et plafonds budgétaires",
    body: "Pilotez l'équation économique complète de vos processus : coût de setup initial amorti, coût des exécutions par niveau de modèle IA, et temps humain investi comparé à votre référence sans automatisation. Configurez des seuils d'alerte à 80 % et des suspensions automatiques à 100 % pour protéger vos budgets d'équipe.",
    category: "whatFor",
  },
  {
    sectionId: "finops-human-mastery",
    title: "Maîtrise humaine, qualité et réversibilité d'architecture",
    body: "Préservez le discernement de vos experts et la conformité aux décisions verrouillées. Les trois indicateurs mesurent l'équilibre entre cadrage amont et relecture, préviennent les validations trop rapides et signalent tout écart structurel non couvert par une dérogation.",
    category: "whatFor",
  },
  {
    sectionId: "finops-remote-services",
    title: "Télémétrie des services et agents externes",
    body: "Suivez séparément les coûts déclarés par les serveurs d'outils et agents distants, leurs unités métiers propres et l'état de leur coupe-circuit isolé. Chaque connecteur suspendu peut être réarmé indépendamment sans perturber vos modèles internes.",
    category: "terms",
  },
];

const SHARED_WORKFLOW_FINOPS_EN: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "workflows-overview",
    title: "What is the Process Studio for?",
    body: "A Process is a reusable sequence of steps combining your AI agents and human approval checkpoints to produce a reliable deliverable (e.g. contract review, customer request analysis). Save it as a draft and publish it when ready to run.",
    category: "steps",
  },
  {
    sectionId: "workflows-instructions",
    title: "How to write the process goal and instructions?",
    body: "Describe in plain language what your agents should accomplish step by step: which sources to consult, which points of attention to verify, and what tone to use in the summary.",
    category: "steps",
  },
  {
    sectionId: "workflows-deliverable-contract",
    title: "Launch inputs and deliverable structure (optional)",
    body: "Specify the inputs requested from the user when launching the process (e.g. supplier name, amount) as well as the main headings required in the final deliverable.",
    category: "terms",
  },
  {
    sectionId: "workflows-steps-layers",
    title: "The 3 main execution steps of a process",
    body: "Each process runs in 3 stages: 1) Gather documents and Workspace context, 2) AI agent analysis and cross-checking of business rules, 3) Final human approval before sharing the deliverable.",
    category: "steps",
  },
  {
    sectionId: "audit-overview",
    title: "Activity log: authors, timestamps, and observation filters",
    body: "The Activity Log (accessible from the left menu 📜 Activity Log) tracks who performed each action, when, and on which scope (filtered by default to your active observation level). Filter by user, by the last 50 / 100 / 200 / 500 events, or by time window. Cost tracking and workspace budgets are managed separately in 📊 Costs & Activity.",
    category: "faq",
  },
  {
    sectionId: "finops-overview",
    title: "Cost governance and budget thresholds",
    body: "Track the complete economic equation of your processes: amortized initial setup cost, execution run cost across AI model levels, and human time invested compared to manual baseline without automation. Configure 80% warning alerts and 100% hard stops to safeguard team budgets.",
    category: "whatFor",
  },
  {
    sectionId: "finops-human-mastery",
    title: "Human mastery, quality, and architecture reversibility",
    body: "Preserve active expert critical thinking and compliance with locked architectural decisions. The three indicators balance upstream framing against review time, prevent quick approvals, and report any architectural deviation not covered by an approved exception.",
    category: "whatFor",
  },
  {
    sectionId: "finops-remote-services",
    title: "External services & agents telemetry",
    body: "Track reported external tool and agent costs, distinct business units, and isolated connector circuit breaker states separately from internal models. Any suspended connector can be reset independently without impacting internal AI models.",
    category: "terms",
  },
];

export const CONFIGURATION_SECTIONS_FR: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "iam-org-tree",
    title: "Structure de l'organisation (Directions / BU & Équipes)",
    body: "Organisez votre entreprise en Directions (BU) puis en Équipes. Les Espaces de travail projets/produits se gèrent quant à eux dans le menu 📦 Mes Espaces. Une unité d'organisation ne peut être supprimée que si elle ne contient aucune Équipe rattachée ni règle d'accès dépendante.",
    category: "steps",
  },
  {
    sectionId: "iam-role-grants",
    title: "Règles d'accès : Qui ? et Sur quoi ?",
    body: "Chaque règle associe un bénéficiaire (Rôle ou Utilisateur, ex. Rôle : Chef1) à un périmètre cible (Plateforme entière, Direction / BU, Équipe ou Espace de travail, ex. aqwZSX) et précise les habilitations attribuées (Créer, Consulter les ressources, Modifier, Supprimer, Exécuter / Utiliser, Déléguer des droits). Aucun secret n'est jamais lisible après enregistrement.",
    category: "terms",
  },
  {
    sectionId: "iam-target-scope",
    title: "Qu'est-ce que le Périmètre cible (« Sur quoi ? ») ?",
    body: "Le périmètre cible désigne l'endroit précis de votre organisation où s'applique la règle d'habilitation : soit toute la plateforme, soit une Direction (BU) entière et ses équipes, soit une Équipe, soit un Espace de travail précis. Par exemple, donner un droit à « Product Manager » sur le périmètre cible « Équipe : Paiement » signifie que ce droit ne s'exercera que dans l'équipe Paiement.",
    category: "terms",
  },
  {
    sectionId: "iam-inheritance-block",
    title: "Effet de la règle (Autoriser, Interdire, Isoler ce périmètre)",
    body: "« Autoriser » accorde les actions cochées. « Interdire » est toujours prioritaire. « Isoler ce périmètre » coupe les accès généraux hérités de la Direction parente pour une Équipe ou un Espace confidentiel.",
    category: "terms",
  },
  {
    sectionId: "connectors-overview",
    title: "Connexion à vos outils et sources documentaires",
    body: "Enregistrez vos espaces documentaires, suivis de projets ou dépôts de code. Vos clés d'accès sont protégées dès l'enregistrement et ne sont jamais ré-affichées en clair.",
    category: "steps",
  },
  {
    sectionId: "ai-models-overview",
    title: "Modèles IA : Fournisseur, URL d'API, Authentification & Test de connexion",
    body: "Pour chaque niveau d'usage (Simple, Standard, Approfondi), renseignez : 1) le Fournisseur IA (ex. Anthropic, OpenAI, Mistral AI, Ollama local), 2) l'identifiant du modèle principal (et un modèle de secours optionnel), 3) l'URL de l'API (ex. https://api.anthropic.com/v1 ou http://localhost:11434/v1), et 4) le mode d'authentification (Clé d'API secrète, Variable serveur ou Serveur local sans clé). Cliquez sur « 🔌 Tester la connexion au modèle » avant d'enregistrer pour vérifier immédiatement la réponse du serveur.",
    category: "steps",
  },
  {
    sectionId: "packs-overview",
    title: "Packs métiers prêts à l'emploi",
    body: "Les Packs métiers sont fournis par la plateforme (ou conçus dans Mes Processus) et regroupent des processus, des agents spécialisés et un glossaire métier. Choisissez un périmètre (Plateforme entière, Direction, Équipe ou Espace de travail) puis activez ou désactivez le Pack en 1 clic.",
    category: "terms",
  },
  ...SHARED_WORKFLOW_FINOPS_FR,
];

export const CONFIGURATION_SECTIONS_EN: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "iam-org-tree",
    title: "Organization structure (Divisions / BUs & Teams)",
    body: "Structure your company into Divisions (BUs) and Teams. Project/product Workspaces are managed separately in 📦 My Workspaces. An organization unit can only be deleted once no child teams or access rules depend on it.",
    category: "steps",
  },
  {
    sectionId: "iam-role-grants",
    title: "Access rules: Who? and On what?",
    body: "Each rule links a beneficiary (Role or User, e.g. Role: Chef1) to a target scope (Entire platform, BU, Team, or Workspace, e.g. aqwZSX) and specifies granted permissions (Create, Read & view resources, Update, Delete, Execute / Use, Delegate rights). Secrets are strictly write-only and never readable.",
    category: "terms",
  },
  {
    sectionId: "iam-target-scope",
    title: "What is Target scope ('On what?')?",
    body: "The target scope identifies the exact level of your organization where the permission rule applies: either the entire platform, a whole Division (BU) and its teams, a Team, or a single Workspace. For instance, granting a permission to 'Product Manager' on target scope 'Team: Payments' means that right only applies inside the Payments team.",
    category: "terms",
  },
  {
    sectionId: "iam-inheritance-block",
    title: "Rule effect (Allow, Deny, Isolate this scope)",
    body: "'Allow' grants the selected actions. 'Deny' always takes priority. 'Isolate this scope' stops broad permissions inherited from a parent BU on a confidential team or workspace.",
    category: "terms",
  },
  {
    sectionId: "connectors-overview",
    title: "Connecting your tools and document sources",
    body: "Register your documentation spaces, project trackers, or code repositories. Access keys are protected upon saving and never displayed in plain text again.",
    category: "steps",
  },
  {
    sectionId: "ai-models-overview",
    title: "AI Models: Provider, API URL, Authentication & Connection Test",
    body: "For each usage level (Simple, Standard, In-Depth), specify: 1) AI Provider (e.g. Anthropic, OpenAI, Mistral AI, local Ollama), 2) primary model ID (and optional backup model), 3) API Endpoint URL (e.g. https://api.anthropic.com/v1 or http://localhost:11434/v1), and 4) authentication mode (Secret API Key, Server environment variable, or Keyless local server). Click '🔌 Test model connection' before saving to verify server response.",
    category: "steps",
  },
  {
    sectionId: "packs-overview",
    title: "Ready-to-use Business Packs",
    body: "Business Packs are provided by the platform (or authored in My Processes) and bundle processes, specialized agents, and a domain glossary. Select a target scope (Entire Platform, Division, or Workspace) and enable or disable a Pack in 1 click.",
    category: "terms",
  },
  ...SHARED_WORKFLOW_FINOPS_EN,
];

export const GENERAL_SECTIONS_FR: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "module-overview",
    title: "Repères de cet écran",
    body: "Cet écran présente les éléments rattachés à votre Espace actif. Vous pouvez changer d'Espace à tout moment depuis le sélecteur situé en haut à gauche.",
    category: "whatFor",
  },
  {
    sectionId: "cockpit-decisions",
    title: "Décisions en attente et relectures",
    body: "Le Cockpit regroupe uniquement les points qui demandent votre intervention : rédactions personnelles, arbitrages rapides entre deux options ou relectures détaillées de livrables.",
    category: "steps",
  },
  {
    sectionId: "assistant-modes",
    title: "Les 3 modes de réponse de Mon Assistant",
    body: "Choisissez « Réponse rapide » pour une question directe, « Avec un agent » pour mobiliser un outil connecté, ou « Analyse approfondie » pour croiser plusieurs points de vue avec citations vérifiées.",
    category: "steps",
  },
  {
    sectionId: "workspace-sources",
    title: "Sources de référence et documents de travail",
    body: "Rattachez vos sources documentaires à votre Espace et définissez où vos livrables validés doivent être enregistrés par défaut.",
    category: "terms",
  },
  {
    sectionId: "glossary-rules",
    title: "Glossaire métier et règles automatiques",
    body: "Définissez les termes clés de votre équipe et transformez vos règles métiers en vérifications automatiques exécutées à chaque étape.",
    category: "terms",
  },
  ...SHARED_WORKFLOW_FINOPS_FR,
];

export const GENERAL_SECTIONS_EN: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "module-overview",
    title: "Screen overview",
    body: "This screen displays items linked to your active Workspace. You can switch Workspaces at any time using the selector in the top-left header.",
    category: "whatFor",
  },
  {
    sectionId: "cockpit-decisions",
    title: "Pending decisions and reviews",
    body: "The Cockpit gathers only items requiring your input: personal authoring entries, quick choices between two options, or detailed deliverable reviews.",
    category: "steps",
  },
  {
    sectionId: "assistant-modes",
    title: "My Assistant's 3 response modes",
    body: "Pick 'Fast response' for a direct question, 'With an agent' to use a connected tool, or 'In-depth analysis' to cross-check multiple perspectives with verified citations.",
    category: "steps",
  },
  {
    sectionId: "workspace-sources",
    title: "Reference sources and working documents",
    body: "Connect your document sources to your Workspace and choose where approved deliverables should be saved by default.",
    category: "terms",
  },
  {
    sectionId: "glossary-rules",
    title: "Business glossary and automated rules",
    body: "Define your team's key terms and turn business rules into automated checks executed at every step.",
    category: "terms",
  },
  ...SHARED_WORKFLOW_FINOPS_EN,
];
