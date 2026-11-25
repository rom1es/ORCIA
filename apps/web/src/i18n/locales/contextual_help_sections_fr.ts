import type { UiContextualHelpSectionItem } from "@orcia/ui";

export const WORKFLOW_SECTIONS_FR: readonly UiContextualHelpSectionItem[] = [
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
    sectionId: "autonomy-contract",
    title: "Contrat d'autonomie encadré",
    body: "Un contrat d'autonomie autorise un processus non critique à s'exécuter de bout en bout via un compte de service habilité sur votre Espace, sous plafond budgétaire et avec bascule automatique vers l'équipe dès qu'un contrôle qualité ou une ambiguïté l'exige.",
    category: "terms",
  },
  {
    sectionId: "autonomous-supervision",
    title: "Supervision, arrêt d'urgence & rétablissement",
    body: "Toute exécution automatisée sous contrat est signalée par un badge bleu distinctif. En cas d'anomalie, vous pouvez déclencher un arrêt d'urgence immédiat ou annuler et rétablir la version précédente du livrable ou de la fiche d'aide en un clic.",
    category: "terms",
  },
  {
    sectionId: "workflow-triggers",
    title: "Déclencheurs automatiques et événements planifiés",
    body: "Configurez les événements ou planifications qui lancent automatiquement un processus gouverné (arrivée d'une demande, mise à jour d'un document, revue périodique) dans le respect du budget autorisé.",
    category: "steps",
  },
  {
    sectionId: "orcia-doc-generation-process",
    title: "Génération et synchronisation de la documentation d'aide",
    body: "Ce processus met à jour les fiches d'aide de chaque écran et les publie dans votre Centre d'aide sans écraser les adaptations validées.",
    category: "steps",
  },
];

export const CONFIGURATION_SECTIONS_FR: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "iam-org-tree",
    title: "Structure de l'organisation (Directions / BU & Équipes)",
    body: "Organisez votre entreprise en Directions (BU) puis en Équipes. Les Espaces de travail projets/produits se gèrent quant à eux dans le menu Mes Espaces. Une unité d'organisation ne peut être supprimée que si elle ne contient aucune Équipe rattachée ni règle d'accès dépendante.",
    category: "steps",
  },
  {
    sectionId: "iam-role-grants",
    title: "Règles d'accès : Qui ? et Sur quoi ?",
    body: "Chaque règle associe un bénéficiaire (Rôle ou Utilisateur, ex. Rôle : Responsable Produit) à un périmètre cible (Plateforme entière, Direction / BU, Équipe ou Espace de travail, ex. Équipe Paiement) et précise les habilitations attribuées (Créer, Consulter les ressources, Modifier, Supprimer, Exécuter / Utiliser, Déléguer des droits). Aucun secret n'est jamais lisible après enregistrement.",
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
    body: "Pour chaque niveau d'usage (Simple, Standard, Approfondi), renseignez : 1) le Fournisseur IA (ex. Anthropic, OpenAI, Mistral AI, Ollama local), 2) l'identifiant du modèle principal (et un modèle de secours optionnel), 3) l'URL de l'API, et 4) le mode d'authentification. Cliquez sur « Tester la connexion au modèle » avant d'enregistrer pour vérifier immédiatement la réponse du serveur.",
    category: "steps",
  },
  {
    sectionId: "packs-overview",
    title: "Packs métiers prêts à l'emploi",
    body: "Les Packs métiers sont fournis par la plateforme (ou conçus dans Mes Processus) et regroupent des processus, des agents spécialisés et un glossaire métier. Choisissez un périmètre (Plateforme entière, Direction, Équipe ou Espace de travail) puis activez ou désactivez le Pack en 1 clic.",
    category: "terms",
  },
];

export const SECTIONS_BY_ROUTE_FR: Readonly<Record<string, readonly UiContextualHelpSectionItem[]>> = {
  "/cockpit": [
    {
      sectionId: "cockpit-decisions",
      title: "Décisions en attente et relectures",
      body: "Le Cockpit regroupe uniquement les points qui demandent votre intervention : rédactions personnelles, arbitrages rapides entre deux options ou relectures détaillées de livrables.",
      category: "steps",
    },
    {
      sectionId: "module-overview",
      title: "Repères du Cockpit",
      body: "Suivez l'avancement du démarrage de la plateforme, traitez vos décisions prioritaires ou lancez directement un processus.",
      category: "whatFor",
    },
  ],
  "/assistant": [
    {
      sectionId: "assistant-modes",
      title: "Modèle IA et mode de réflexion (Standard ou Approfondi)",
      body: "Choisissez le modèle adapté (Rapide, Polyvalent ou Raisonnement avancé) et basculez entre « Standard » (réponse directe avec vos sources, ex. « Polyvalent · Standard ») et « Approfondi » (réflexion décomposée en étapes avec citations vérifiées).",
      category: "steps",
    },
    {
      sectionId: "assistant-folders",
      title: "Dossiers thématiques et notes permanentes de Mon Assistant",
      body: "Regroupez vos échanges par sujet dans un dossier et épinglez vos consignes permanentes pour qu'elles soient automatiquement prises en compte à chaque question.",
      category: "steps",
    },
  ],
  "/inbox": [
    {
      sectionId: "inbox-claims",
      title: "Prise en charge et coordination des tâches d'équipe",
      body: "Prenez en charge une demande disponible pour indiquer à votre équipe que vous la traitez, puis libérez-la si un collègue doit reprendre la main.",
      category: "steps",
    },
    {
      sectionId: "inbox-vs-activity",
      title: "Différence entre Boîte de Réception et Journal d'Activité",
      body: "La Boîte de Réception présente uniquement les notifications opérationnelles et tâches en attente de votre Espace actif ; le Journal d'Activité conserve l'historique complet des opérations passées.",
      category: "terms",
    },
  ],
  "/spaces": [
    {
      sectionId: "workspace-sources",
      title: "Sources de référence et unités d'organisation",
      body: "Chaque Espace de travail est rattaché à une unité d'organisation (Direction ou Équipe) et isole ses sources documentaires ainsi que l'enregistrement de ses livrables.",
      category: "terms",
    },
    {
      sectionId: "glossary-rules",
      title: "Glossaire métier de l'Espace",
      body: "Définissez les termes clés de votre équipe et transformez vos règles métiers en vérifications automatiques exécutées à chaque étape.",
      category: "terms",
    },
  ],
  "/processes": WORKFLOW_SECTIONS_FR,
  "/gates": [
    {
      sectionId: "orcia-doc-generation-process",
      title: "Génération et synchronisation de la documentation d'aide",
      body: "Ce processus met à jour les fiches d'aide de chaque écran et les publie dans votre Centre d'aide sans écraser les adaptations validées.",
      category: "steps",
    },
    {
      sectionId: "autonomous-supervision",
      title: "Supervision, arrêt d'urgence & rétablissement",
      body: "Toute exécution automatisée sous contrat est signalée par un badge bleu distinctif. En cas d'anomalie, vous pouvez déclencher un arrêt d'urgence immédiat ou rétablir la version précédente.",
      category: "terms",
    },
  ],
  "/agents": [
    {
      sectionId: "connectors-overview",
      title: "Agents spécialisés et connexions d'outils",
      body: "Consultez les agents disponibles et testez les connecteurs autorisés sur votre périmètre actif.",
      category: "steps",
    },
  ],
  "/catalog": [
    {
      sectionId: "showcase-packs",
      title: "Catalogue des packs, modèles et agents",
      body: "Parcourez les packs métiers, gabarits de processus et agents disponibles sur la plateforme.",
      category: "terms",
    },
  ],
  "/finops": [
    {
      sectionId: "finops-overview",
      title: "Gouvernance des coûts et plafonds budgétaires",
      body: "Pilotez l'équation économique complète de vos processus : coût de setup initial amorti, coût des exécutions par niveau de modèle IA et seuils d'alerte à 80 % et 100 %.",
      category: "whatFor",
    },
    {
      sectionId: "finops-human-mastery",
      title: "Maîtrise humaine, qualité et réversibilité d'architecture",
      body: "Préservez le discernement de vos experts et la conformité aux décisions verrouillées.",
      category: "whatFor",
    },
    {
      sectionId: "finops-remote-services",
      title: "Télémétrie des services et agents externes",
      body: "Suivez séparément les coûts déclarés par les serveurs d'outils et agents distants ainsi que l'état de leur coupe-circuit isolé.",
      category: "terms",
    },
    {
      sectionId: "autonomous-supervision",
      title: "Supervision des exécutions automatisées",
      body: "Auditez les exécutions autonomes sous contrat et rétablissez une version antérieure en un clic si nécessaire.",
      category: "terms",
    },
  ],
  "/activity": [
    {
      sectionId: "audit-overview",
      title: "Journal d'activité : auteurs, horodatage et filtres d'observation",
      body: "Le Journal d'Activité trace qui a effectué chaque action, à quelle date/heure et sur quel périmètre (filtré par défaut sur votre niveau d'observation actif). Le suivi des coûts et des budgets par espace est géré séparément dans FinOps.",
      category: "faq",
    },
  ],
  "/ontology": [
    {
      sectionId: "glossary-rules",
      title: "Glossaire métier et règles automatiques",
      body: "Définissez les termes clés de votre équipe et transformez vos règles métiers en vérifications automatiques exécutées à chaque étape.",
      category: "terms",
    },
  ],
  "/organization": [
    {
      sectionId: "org-hierarchy",
      title: "Directions (BU), Équipes et rattachement budgétaire",
      body: "Chaque Direction regroupe des Équipes autonomes qui portent leurs membres, leurs responsables et la facturation des appels IA. Les unités parentes ou sœurs en lecture seule restent protégées contre toute modification non autorisée.",
      category: "steps",
    },
    {
      sectionId: "org-delegation",
      title: "Délégation locale et invitations scopées",
      body: "Les responsables de Direction ou d'Équipe gèrent directement les membres et invitent des collaborateurs dans leur propre périmètre sans intervention d'un administrateur global.",
      category: "terms",
    },
  ],
  "/settings": CONFIGURATION_SECTIONS_FR,
  "/settings/packs": [...CONFIGURATION_SECTIONS_FR, ...WORKFLOW_SECTIONS_FR],
  "/showcase": [
    {
      sectionId: "showcase-overview",
      title: "Présentation vivante d'ORCIA",
      body: "Explorez la vision Human-Led, les fonctionnalités livrées et les choix d'architecture de la plateforme.",
      category: "whatFor",
    },
    {
      sectionId: "showcase-packs",
      title: "Packs métiers installés sur la plateforme",
      body: "Les packs métiers regroupent des processus prêts à l'emploi, des agents spécialisés et un glossaire adapté à un domaine d'activité.",
      category: "terms",
    },
  ],
};
