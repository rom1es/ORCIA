import type { TranslationDictionary } from "../types";
import { ADMIN_AND_STUDIO_FR_LABELS } from "./admin_and_studio_labels";
import { ASSISTANT_FR_LABELS } from "./assistant_labels";
import { GOVERNANCE_AND_PACKS_FR_LABELS } from "./governance_and_packs_labels";
import { INBOX_AND_COCKPIT_FR_LABELS } from "./inbox_and_cockpit_labels";
import { SHELL_AND_SEARCH_FR_LABELS } from "./shell_and_search_labels";

export const frDictionary: TranslationDictionary = {
  ...INBOX_AND_COCKPIT_FR_LABELS,
  ...ADMIN_AND_STUDIO_FR_LABELS,
  ...SHELL_AND_SEARCH_FR_LABELS,
  ...ASSISTANT_FR_LABELS,
  ...GOVERNANCE_AND_PACKS_FR_LABELS,
  locale: "fr",
  shell: {
    brandTitle: "ORCIA",
    brandSubtitle: "",
    sidebarNavigationAriaLabel: "Navigation principale",
    sidebarToggleExpandLabel: "Déplier le menu latéral",
    sidebarToggleCollapseLabel: "Replier le menu latéral",
    scopeSwitcherButtonLabel: "Sélecteur d'espace (⌘W)",
    scopeSwitcherDialogTitle: "Sélecteur d'espace et d'organisation (⌘W)",
    scopeSwitcherCloseLabel: "Fermer",
    scopeLevels: {
      GLOBAL: "Plateforme Globale",
      BU: "Direction / Pôle",
      TEAM: "Équipe",
      WORKSPACE: "Espace de travail",
    },
    accessModes: {
      CONTRIBUTOR_ACTION_REQUIRED: "Contributeur (Action requise)",
      READ_ONLY_OBSERVER: "Consultation seule (Observateur)",
    },
    modules: {
      cockpit: "Cockpit & Décisions",
      inbox: "Mon Assistant",
      catalog: "Agents & Compétences",
      ontology: "Connaissances & Glossaire",
      gates: "Processus & Validations",
      finops: "Coûts & Journal d'Activité",
      admin: "Mes Espaces",
      bootstrap: "Configuration Initiale",
    },
    staleWarningBadgeLabel: "! À vérifier (source modifiée)",
    humanProfilePrefixLabel: "Rôle métier",
    assistantDockTitle: "Assistant & Accès aux Sources",
    assistantDockSubtitle: "Exécution sécurisée sous votre identité",
    assistantDockToggleExpandLabel: "Déplier le panneau Assistant",
    assistantDockToggleCollapseLabel: "Replier le panneau Assistant",
    assistantPermissionBrokerReadyLabel: "Assistance d'accès active",
    assistantInputPlaceholder: "Poser une question à l'Assistant ou demander un accès manquant...",
    assistantSendLabel: "Envoyer à l'Assistant",
    localeSwitchLabel: "Langue",
    topbarSearchAriaLabel: "Recherche globale",
    topbarSearchPlaceholder: "Rechercher... (⌘K)",
    darkModeToggleLabel: "🌙 Mode sombre",
    mobileNavigationAriaLabel: "Navigation mobile",
    mobileTabs: {
      inbox: "🔔 À traiter",
      chat: "💬 Arbitrage / Chat",
      briefing: "📄 Synthèse",
    },
  },
  humanAnchor: {
    badgeTitle: "✍️ RÉDACTION PERSONNELLE OBLIGATOIRE",
    authorLabel: "Auteur",
    placeholderText: "Saisissez vos orientations et hypothèses structurantes (rédaction personnelle requise)...",
    submitLabel: "Valider et signer ma saisie",
    defaultSectionTitle: "Intentions & Orientations Métier",
    defaultAuthorName: "Responsable référent",
    defaultValue: "Définition des objectifs prioritaires et des critères d'acceptation attendus.",
  },
  arbitrationTieBreak: {
    badgeTitle: "⚖️ ARBITRAGE REQUIS",
    policyPrefixLabel: "Règle de départage",
    recommendedBadgeLabel: "★ Recommandé",
    prosLabel: "Avantages",
    consLabel: "Inconvénients",
    siImpactLabel: "Impact métier & outils",
    finopsImpactLabel: "Coût estimé",
    justificationPlaceholder: "Justification ou orientation complémentaire (optionnel)...",
    selectOptionButtonLabel: "Retenir cette option",
    resolvedBannerPrefix: "✅ Décision d'arbitrage enregistrée pour la suite du processus",
    defaultQuestionTitle: "Choix entre deux orientations",
    defaultContextSummary:
      "Deux options équivalentes ont été préparées et nécessitent votre décision.",
  },
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
      studioTitle:
        "Atelier de Conception de Processus & Modèles de Livrables",
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
      templatePreviewTitle:
        "Aperçu du Modèle de Livrable selon le Public",
      humanMarkdownTabLabel: "Vue Lecture (Document structuré)",
      agentSchemaTabLabel: "Vue Structurée (Champs attendus)",
      sampleHumanMarkdown:
        "## 1. Objectifs & Orientations [✍️ RÉDACTION PERSONNELLE OBLIGATOIRE]\nOrientations directrices du livrable",
      sampleAgentJsonSchema:
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","x-bound-ontology-terms":["Actif Stratégique"]}',
      subWorkflowLocksTitle: "Sous-processus rattachés et versions associées",
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
    pausedStateBanner: "⏸️ Étape mise en attente jusqu'à l'obtention de l'accès",
    replayedStateBanner: "✅ Accès confirmé — Étape relancée avec succès",
    simulatorTitle:
      "Gestion des Accès aux Sources Externes & Demandes d'Habilitation",
    simulatorSubtitle:
      "Détection automatique des accès manquants, identification du responsable et relance de l'étape après déblocage.",
    simulateGitDenialLabel: "Tester un accès manquant sur un dépôt de code",
    simulateConfluenceDenialLabel: "Tester un accès manquant sur un espace documentaire",
    simulateJiraDenialLabel: "Tester un accès manquant sur un projet de suivi",
    simulateConfusedDeputyLabel: "Tester un compte technique non autorisé",
    confusedDeputyBlockedBanner:
      "Exécution bloquée — Ce compte technique partagé n'a pas été approuvé par un administrateur",
    observerDeniedBanner:
      "Action refusée — Votre rôle actuel est limité à la consultation seule",
  },
  bootstrapOnboarding: {
    panelTitle: "Assistant de Configuration Initiale & Accueil des Équipes",
    panelSubtitle:
      "Parcours guidés pour configurer votre organisation, créer vos espaces de travail et connecter vos sources.",
    orthogonalityTitle: "Étape 1 — Configuration d'au moins deux fournisseurs de modèles IA indépendants",
    orthogonalityPassBadge: "Diversité des modèles IA validée (3 fournisseurs indépendants configurés)",
    orthogonalityFailBanner:
      "Configuration incomplète — Configurez au moins 2 fournisseurs de modèles IA distincts pour croiser les revues",
    simulateSingleFamilyLabel: "Tester avec un seul fournisseur IA",
    simulateDualFamilyLabel: "Valider avec au moins 2 fournisseurs IA distincts",
    initWorkspaceTitle: "Création Autonome d'Équipe et d'Espaces de Travail",
    initWorkspaceButtonLabel: "Créer l'équipe et ses espaces de travail",
    initWorkspaceSuccessBanner:
      "Équipe, espaces de travail et invitations créés avec succès",
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
    observerDeniedBanner:
      "Action refusée — Votre rôle actuel est limité à la consultation seule",
    humanAnchorCardLabels: {
      badgeTitle: "✍️ RÉDACTION PERSONNELLE OBLIGATOIRE",
      authorLabel: "Signataire",
      sectionTitle: "Justification métier et périmètre d'utilisation de la source",
      placeholderText: "Expliquez pourquoi cette source est rattachée à l'espace (minimum 30 caractères)...",
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
      "1_ENTERPRISE": "1. Organisation (Global)",
      "2_DOMAIN": "2. Direction / Pôle",
      "3_TEAM": "3a. Équipe",
      "3_WORKSPACE": "3b. Espace de travail",
      "4_RUN_EPHEMERAL": "4. Exécution en cours",
    },
    profileSelectorLabel: "Adapter le vocabulaire au rôle :",
    whatIfButtonLabel: "Estimer l'impact d'une modification",
    promoteButtonLabel: "Proposer ce terme au niveau supérieur",
    promotedBannerPrefix: "Estimation d'impact calculée pour :",
    immutableConflictBanner: "Modification refusée : cette règle d'organisation parente ne peut pas être contredite.",
    hybridRagTitle: "Recherche dans la Base de Connaissances",
    hybridRagSearchPlaceholder: "Rechercher un terme métier, un document ou une référence...",
    hybridRagSearchButtonLabel: "Rechercher",
    tripartiteTitle: "Liens entre Documentation, Suivi d'Activité et Réalisations",
    staleAlertsTitle: "Surveillance de l'Actualité des Documents",
    docObsoleteBadgeLabel: "Mise à jour recommandée",
  },
  modulePages: {
    cockpit: {
      subtitle: "Votre tableau de bord des décisions et actions prioritaires",
      description:
        "Suivez vos processus en cours, rédigez les cadrages attendus et tranchez les points d'arbitrage.",
      uriBadgeExample: "Cockpit",
    },
    inbox: {
      subtitle: "Votre assistant conversationnel appuyé sur vos sources",
      description:
        "Posez vos questions, explorez vos dossiers thématiques et préparez vos livrables avec citations vérifiées.",
      uriBadgeExample: "Mon Assistant",
    },
    catalog: {
      subtitle: "Répertoire des agents, compétences et services connectés",
      description:
        "Consultez, testez et configurez les agents spécialisés et les outils mis à disposition de vos espaces.",
      uriBadgeExample: "Agents & Compétences",
    },
    ontology: {
      subtitle: "Glossaire métier partagé et base documentaire",
      description:
        "Gérez les termes métier de votre organisation et surveillez la fraîcheur de vos documents de référence.",
      uriBadgeExample: "Connaissances",
    },
    gates: {
      subtitle: "Conception des processus et suivi des étapes de validation",
      description:
        "Créez vos processus métiers, vérifiez les contrôles de qualité et validez les livrables étape par étape.",
      uriBadgeExample: "Processus",
    },
    finops: {
      subtitle: "Suivi des coûts d'utilisation et journal d'activité",
      description:
        "Consultez la consommation par espace et par étape ainsi que l'historique complet des décisions validées.",
      uriBadgeExample: "Coûts & Activité",
    },
    admin: {
      subtitle: "Gestion de vos espaces de travail, sources et règles métiers",
      description:
        "Organisez vos espaces, rattachez vos sources documentaires et gérez le glossaire et les règles de vos équipes.",
      uriBadgeExample: "Mes Espaces",
    },
    bootstrap: {
      subtitle: "Parcours guidés de configuration initiale",
      description:
        "Configurez pas à pas votre organisation, vos premiers espaces de travail et vos connexions aux outils.",
      uriBadgeExample: "Configuration",
    },
  },
  upstreamChallengeModal: {
    modalTitle: "Signaler une Correction sur une Étape Précédente",
    modalSubtitle:
      "Indiquez l'élément à ajuster dans une étape précédente, visualisez les étapes suivantes concernées et relancez uniquement ce qui doit être mis à jour.",
    targetStepLabel: "Étape précédente concernée",
    sectionKeyLabel: "Section ou règle à ajuster",
    reasonLabel: "Motif de la demande de correction (minimum 10 caractères)",
    reasonPlaceholder: "Expliquez l'écart ou la précision à apporter sur l'étape précédente...",
    whatIfTitle: "Aperçu des éléments qui seront mis à jour",
    invalidatedStepsLabel: "Étapes suivantes à recalculer",
    invalidatedSectionsLabel: "Sections de livrables impactées",
    invalidatedAxiomsLabel: "Règles métier concernées",
    preservedStepsLabel: "Étapes antérieures conservées sans retraitement",
    translatedSummaryLabel: "Explication adaptée pour le responsable de l'étape précédente",
    submitChallengeCta: "Envoyer la demande de correction",
    replayStepCta: "Relancer à partir de cette étape",
    closeCta: "Fermer",
    challengeSubmittedFeedback: "Demande de correction transmise au responsable de l'étape ✓",
    replayTriggeredFeedback: "Relance effectuée à partir de l'étape sélectionnée ✓",
  },
  humanGates: {
    briefing: {
      gridTitle: "Synthèse de Relecture avant Validation (4 Points Clés)",
      block1Title: "1. Résumé Exécutif",
      block2Title: "2. Points Clés & Vérifications Croisées",
      block3Title: "3. Décisions Proposées",
      block4Title: "4. Hypothèses Retenues",
      inspectHypothesesButtonLabel: "Confirmer la lecture des hypothèses",
      hypothesesInspectedBadgeLabel: "Hypothèses relues",
      hypothesesPendingBadgeLabel: "Relecture requise (Point 4)",
    },
    chunkValidation: {
      sectionListTitle: "Validation Section par Section",
      keyboardNavHint: "Raccourci clavier : Alt + ↑ / ↓",
      approveSectionLabel: "Valider la section",
      coEditSectionLabel: "Modifier la section",
      challengeSectionLabel: "Demander une correction en amont",
      finalizeGateButtonLabel: "Confirmer la validation finale",
      pendingSectionsNotice:
        "Chaque section obligatoire ainsi que le Point 4 (Hypothèses Retenues) doivent être vérifiés avant la validation finale.",
      guardModalTitle: "Confirmation de Relecture Attentive",
      guardModalDescription:
        "Vous avez validé ce document très rapidement. Merci de confirmer que vous avez bien pris connaissance des hypothèses retenues.",
      guardConfirmCheckboxLabel:
        "Je confirme avoir vérifié les hypothèses retenues et les sections importantes",
      guardConfirmButtonLabel: "Confirmer et enregistrer ma validation",
      guardCancelButtonLabel: "Reprendre la lecture",
    },
  },
  inboxAndClaims: {
    filterAllLabel: "Toutes les demandes",
    filterPersonalLabel: "Qui me sont destinées",
    filterTeamLabel: "Pour mon équipe",
    amberCounterPrefix: "Actions en attente :",
    contributorSectionTitle: "Actions Requises de Votre Part",
    observerSectionTitle: "En Suivi — Consultation Seule",
    observerBannerText:
      "👁️ Mode Consultation Seule — Vous suivez cette exécution sans pouvoir la modifier",
    presencePill: {
      claimActionLabel: "Prendre en charge",
      claimedByMeBadge: "🔒 Pris en charge par vous",
      claimedByPeerPrefix: "🔒 Pris en charge par :",
      releaseActionLabel: "Libérer",
      forceUnclaimActionLabel: "Reprendre la main (après 15 min)",
      readOnlyObserverNotice: "Consultation seule",
      sseLatencyPrefix: "Synchronisation :",
    },
  },
};
