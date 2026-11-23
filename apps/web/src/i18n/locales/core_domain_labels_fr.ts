import type { TranslationDictionary } from "../types";

export const CORE_DOMAIN_FR_LABELS: Pick<
  TranslationDictionary,
  | "workspaceTopology"
  | "catalogExplorer"
  | "permissionBroker"
  | "bootstrapOnboarding"
  | "ontologyExplorer"
> = {
  workspaceTopology: {
    panelTitle: "Organisation des Équipes, Espaces de Travail et Droits d'Accès",
    panelSubtitle:
      "Visualisez la structure de votre organisation, les espaces rattachés et la visibilité des sources.",
    personaSelectorLabel: "Prévisualiser le point de vue d'un profil",
    personas: {
      karim: "Karim — Administrateur Plateforme (Organisation)",
      claire: "Claire — Directrice de Pôle (Suivi consolidé)",
      marc: "Marc — Responsable d'Équipe (Équipe Paiement)",
      nadia: "Nadia — Contributrice (Réalisation)",
      partenaire: "Partenaire Externe (Accès limité à l'Espace 1)",
    },
    finopsRollupPrefix: "Suivi budgétaire consolidé",
    confidentialExcludedNotice:
      "Les espaces marqués comme confidentiels ne remontent aucun contenu métier aux niveaux parents.",
    datasourcesCountPrefix: "Sources documentaires et outils rattachés",
    catalogPermissionsTitle: "Droits d'Accès aux Sources & Protection des Contenus Confidentiels",
    sourceMaskedBadgeLabel: "🔒 Source non autorisée",
    sourceOpenBadgeLabel: "📖 Source accessible",
    inspectSourceButtonLabel: "Consulter la source",
    sourceDeniedErrorBanner: "Accès refusé — Vous ne disposez pas du droit de lecture sur cette source",
    sourceAllowedBannerPrefix: "Accès autorisé — Source disponible",
    mutationGuardButtonLabel: "Vérifier le droit de modification",
    mutationAllowedBanner: "Modification autorisée (rôle Contributeur actif)",
    mutationDeniedObserverBanner:
      "Action refusée — Votre rôle actuel est limité à la consultation seule",
  },
  catalogExplorer: {
    panelTitle: "Catalogue des Agents, Compétences et Modèles de Processus",
    panelSubtitle:
      "Explorez les ressources disponibles dans vos espaces et personnalisez-les selon vos besoins.",
    emptyStateMessage: "Aucun élément disponible dans le catalogue pour ce filtre.",
    scopeLabels: {
      DRAFT: "Brouillon",
      SHARED_WORKSPACE: "Partagé (Espace)",
      SHARED_TEAM: "Partagé (Équipe)",
      SHARED_BU: "Partagé (Direction)",
      PENDING_APPROVAL: "Validation en attente",
      PUBLISHED_ORG: "Publié (Organisation)",
    },
    filterAllSchemesLabel: "Toutes les sources",
    maskedSourceBadgeLabel: "🔒 Source restreinte",
    openSourceBadgeLabel: "📖 Source accessible",
    resolveCasButtonLabel: "Vérifier la version",
    casResolvedBannerPrefix: "Version vérifiée et prête à l'emploi",
    promoteScopeButtonLabel: "Partager à un niveau supérieur",
    promotedBannerPrefix: "Ressource partagée avec succès",
    promoteDeniedObserverBanner:
      "Partage refusé — Votre rôle actuel est limité à la consultation seule",
    overrideSectionTitle: "Personnalisation par Niveau (Standard -> Équipe -> Espace -> Personnel)",
    overrideSectionSubtitle:
      "Adaptez les réglages à chaque niveau tout en garantissant la traçabilité des versions utilisées.",
    overrideLayers: {
      base: "1. Standard de référence",
      teamParent: "2a. Équipe parente",
      teamSub: "2b. Sous-équipe",
      workspace: "3. Espace de travail",
      user: "4. Préférences personnelles",
    },
    runLockTitle: "Versions de référence utilisées pour cette exécution",
    bmadAdapterTitle: "Importation de pack de compétences externe",
    bmadImportButtonLabel: "Importer un pack de compétences",
    bmadImportedBanner:
      "Pack de compétences importé et prêt à être utilisé dans vos processus",
    workflowStudio: {
      studioTitle: "Atelier de Conception de Processus & Modèles de Livrables",
      studioSubtitle:
        "Vérifiez la cohérence des étapes, la présence des points de validation et la structure des livrables.",
      validateNominalLabel: "Vérifier un processus valide",
      simulateCriticalAutonomousLabel: "Tester un processus critique sans validation humaine",
      simulateMissingIntentionLabel: "Tester une réalisation sans cadrage préalable",
      simulateMaxDepthLabel: "Tester un emboîtement excessif de sous-processus",
      validDagBanner:
        "Processus valide : enchaînement des étapes cohérent et cadrage préalable respecté",
      criticalAutonomousErrorBanner:
        "Validation requise [Ligne 6] — Un processus critique doit comporter une étape de validation humaine",
      missingIntentionErrorBanner:
        "Cadrage requis [Ligne 18] — Cette étape nécessite une étape préalable de définition des objectifs",
      maxDepthErrorBanner:
        "Structure trop complexe [Ligne 24] — Le nombre de sous-processus imbriqués dépasse la limite autorisée (3)",
      templatePreviewTitle: "Aperçu du Modèle de Livrable selon le Public",
      humanMarkdownTabLabel: "Vue Lecture (Document structuré)",
      agentSchemaTabLabel: "Vue Structurée (Champs attendus)",
      sampleHumanMarkdown:
        "## 1. Objectifs & Orientations [✍️ RÉDACTION PERSONNELLE OBLIGATOIRE]\nOrientations directrices du livrable",
      sampleAgentJsonSchema:
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","x-bound-ontology-terms":["Actif Stratégique"]}',
      subWorkflowLocksTitle: "Sous-processus rattachés et versions associées",
      depthPrefix: "Niveau",
    },
  },
  permissionBroker: {
    cardBadgeTitle: "⚠️ ACCÈS À UNE SOURCE REQUISE",
    passthroughBadgeLabel: "Compte utilisé : votre compte personnel",
    servicePrincipalBadgeLabel: "Compte utilisé : compte technique partagé",
    targetUriLabel: "Source externe non accessible",
    requiredRoleLabel: "Habilitation ou groupe requis",
    approverTeamLabel: "Équipe responsable de l'accès",
    slaHoursPrefix: "Délai habituel",
    rfcHintLabel: "Conseil de résolution",
    jiraRequestButtonLabel: "Demander l'accès auprès de l'équipe responsable",
    pauseStepButtonLabel: "Mettre l'étape en attente",
    replayStepButtonLabel: "Relancer l'étape",
    stepPrefix: "Étape",
    pausedStateBanner: "⏸️ Étape mise en attente jusqu'à l'obtention de l'accès",
    replayedStateBanner: "✅ Accès confirmé — Étape relancée avec succès",
    simulatorTitle: "Gestion des Accès aux Sources Externes & Demandes d'Habilitation",
    simulatorSubtitle:
      "Détection automatique des accès manquants, identification du responsable et relance de l'étape après déblocage.",
    simulateGitDenialLabel: "Tester un accès manquant sur un dépôt de code",
    simulateConfluenceDenialLabel: "Tester un accès manquant sur un espace documentaire",
    simulateJiraDenialLabel: "Tester un accès manquant sur un projet de suivi",
    simulateConfusedDeputyLabel: "Tester un compte technique non autorisé",
    confusedDeputyBlockedBanner:
      "Exécution bloquée — Ce compte technique partagé n'a pas été approuvé par un administrateur",
    observerDeniedBanner: "Action refusée — Votre rôle actuel est limité à la consultation seule",
  },
  bootstrapOnboarding: {
    panelTitle: "Assistant de Configuration Initiale & Accueil des Équipes",
    panelSubtitle:
      "Parcours guidés pour configurer votre organisation, créer vos espaces de travail et connecter vos sources.",
    orthogonalityTitle:
      "Étape 1 — Configuration d'au moins deux fournisseurs de modèles IA indépendants",
    orthogonalityPassBadge:
      "Diversité des modèles IA validée (3 fournisseurs indépendants configurés)",
    orthogonalityFailBanner:
      "Configuration incomplète — Configurez au moins 2 fournisseurs de modèles IA distincts pour croiser les revues",
    simulateSingleFamilyLabel: "Tester avec un seul fournisseur IA",
    simulateDualFamilyLabel: "Valider avec au moins 2 fournisseurs IA distincts",
    initWorkspaceTitle: "Création Autonome d'Équipe et d'Espaces de Travail",
    initWorkspaceButtonLabel: "Créer l'équipe et ses espaces de travail",
    initWorkspaceSuccessBanner: "Équipe, espaces de travail et invitations créés avec succès",
    initDatasourceTitle: "Connexion d'une Nouvelle Source Documentaire ou Outil",
    initDatasourceButtonLabel: "Enregistrer et publier la source",
    initDatasourceSuccessBanner:
      "Source rattachée à l'espace avec sa justification et sa fréquence de mise à jour",
    humanAnchorErrorBanner:
      "Justification requise — Veuillez rédiger une justification d'au moins 30 caractères et signer",
    initUserTitle: "Configuration de Mon Profil & Connexion à Mes Outils",
    initUserButtonLabel: "Enregistrer mon profil et mes accès personnels",
    initUserSuccessBanner:
      "Rôle métier confirmé et identifiants personnels enregistrés en toute sécurité",
    observerDeniedBanner: "Action refusée — Votre rôle actuel est limité à la consultation seule",
    humanAnchorCardLabels: {
      badgeTitle: "✍️ RÉDACTION PERSONNELLE OBLIGATOIRE",
      authorLabel: "Signataire",
      sectionTitle: "Justification métier et périmètre d'utilisation de la source",
      placeholderText:
        "Expliquez pourquoi cette source est rattachée à l'espace (minimum 30 caractères)...",
      signatureLabel: "Nom ou signature du responsable",
      signaturePlaceholder: "Ex : Responsable d'espace",
      submitLabel: "Valider et signer",
    },
  },
  ontologyExplorer: {
    panelTitle: "Glossaire Métier, Règles de l'Organisation & Liens Documentaires",
    panelSubtitle:
      "Consultez les définitions partagées à chaque niveau de l'organisation et vérifiez l'impact des modifications.",
    emptyStateMessage:
      "Aucun terme métier ni document indexé pour le moment. Créez un espace ou connectez une source pour enrichir la base de connaissances.",
    columns: {
      "1_ENTERPRISE": "Organisation (Global)",
      "2_DOMAIN": "Direction / Pôle",
      "3_TEAM": "Équipe",
      "3_WORKSPACE": "Espace de travail",
      "4_RUN_EPHEMERAL": "Exécution en cours",
    },
    profileSelectorLabel: "Adapter le vocabulaire au rôle :",
    whatIfButtonLabel: "Estimer l'impact d'une modification",
    promoteButtonLabel: "Proposer ce terme au niveau supérieur",
    promotedBannerPrefix: "Estimation d'impact calculée pour :",
    immutableConflictBanner:
      "Modification refusée : cette règle d'organisation parente ne peut pas être contredite.",
    hybridRagTitle: "Recherche dans la Base de Connaissances",
    hybridRagSearchPlaceholder: "Rechercher un terme métier, un document ou une référence...",
    hybridRagSearchButtonLabel: "Rechercher",
    tripartiteTitle: "Liens entre Documentation, Suivi d'Activité et Réalisations",
    staleAlertsTitle: "Surveillance de l'Actualité des Documents",
    docObsoleteBadgeLabel: "Mise à jour recommandée",
    auditSubmitLabel: "Relier et vérifier",
    auditConfluencePlaceholder: "Adresse de la page documentaire (ex. confluence://ESPACE/page)",
    auditGitPlaceholder: "Dépôt ou symbole applicatif (ex. https://git.internal.orcia/app)",
    auditJiraPlaceholder: "Référence ticket (ex. PROJ-101)",
  },
};
