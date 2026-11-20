import type {
  ContextualHelpColumnAndCenterLabels,
  FourZoneDirectionCShellLabels,
  ProgressiveDay0AccostageLabels,
  StreamlinedCockpitLabels,
  TopHeaderSearchCommandLabels,
  UserAccountDropdownAndSettingsLabels,
} from "@orcia/ui";

export interface FirstBootAdminModalLabels {
  readonly title: string;
  readonly description: string;
  readonly firstTimeBadge: string;
  readonly fullNameLabel: string;
  readonly fullNamePlaceholder: string;
  readonly emailLabel: string;
  readonly emailPlaceholder: string;
  readonly passwordLabel: string; // pragma: allowlist secret
  readonly confirmPasswordLabel: string; // pragma: allowlist secret
  readonly showPasswordLabel: string; // pragma: allowlist secret
  readonly hidePasswordLabel: string; // pragma: allowlist secret
  readonly passwordMismatchError: string; // pragma: allowlist secret
  readonly assignedRoleBadge: string;
  readonly submitCta: string;
  readonly missingFieldsHint: string;
  readonly reopenSetupCta: string;
  readonly day0DisabledAdminMissingReason: string;
}

export interface ShellAndSearchDictionarySection {
  readonly fourZoneShell: FourZoneDirectionCShellLabels;
  readonly sidebarFooter: {
    readonly myAccountLabel: string;
    readonly documentationLabel: string;
  };
  readonly firstBootAdminModal: FirstBootAdminModalLabels;
  readonly streamlinedCockpit: StreamlinedCockpitLabels;
  readonly progressiveAccostage: ProgressiveDay0AccostageLabels;
  readonly topHeaderSearch: TopHeaderSearchCommandLabels;
  readonly userAccountAndSettings: UserAccountDropdownAndSettingsLabels;
  readonly contextualHelpHybrid: ContextualHelpColumnAndCenterLabels;
}

export const SHELL_AND_SEARCH_FR_LABELS: ShellAndSearchDictionarySection = {
  fourZoneShell: {
    workspacePrefix: "Espace",
    searchTriggerPlaceholder: "Rechercher… (⌘K)",
    contextualHelpButtonLabel: "Aide",
    notificationsButtonLabel: "Notifications",
    notificationsDrawerTitle: "Centre de Notifications",
    notificationsEmptyText: "Aucune notification non lue.",
    notificationsVsActivityHint:
      "Le Centre de Notifications regroupe vos actions et prérequis en attente. Pour consulter l'historique complet des opérations de votre périmètre, ouvrez le Journal d'Activité.",
    notificationsOpenActivityCta: "Ouvrir le Journal d'Activité →",
    autonomousNominalGroupTitle: "Exécutions autonomes nominales",
    autonomousDefaultTriggerLabel: "Automatisé sous contrat",
    sidebarAriaLabel: "Navigation principale",
    railCollapseLabel: "Replier le menu",
    railExpandLabel: "Déplier le menu",
    packSelectorLabel: "Domaine métier actif",
    helpColumnTitle: "Aide Contextuelle",
    helpColumnExpectedTitle: "À propos de cet écran",
    helpColumnExpectedBody:
      "Retrouvez ici les explications détaillées et les conseils liés à votre écran actuel.",
    helpColumnScrollMoreLabel: "Défiler pour voir la suite ↓",
    menuEntries: {
      cockpit: "Cockpit",
      assistant: "Mon Assistant",
      processes: "Mes Processus",
      agents: "Mes Agents",
      spaces: "Mes Espaces",
      finops: "FinOps",
      configuration: "Configuration",
      help: "Aide",
    },
    organizationMenuLabel: "Mon Organisation",
    activityMenuLabel: "Journal d'Activité",
    doubleSelector: {
      teamBuLabel: "Équipe / Direction",
      workspaceLabel: "Espace",
      allWorkspacesOption: "Tous les espaces",
    },
    mobileTabs: {
      navAriaLabel: "Navigation mobile",
      cockpit: "Cockpit",
      assistant: "Mon Assistant",
      decisions: "Décisions",
      menuLabel: "Menu",
    },
    mobileDesktopRecommendedText:
      "Affichage optimisé pour ordinateur : tous les réglages restent accessibles ci-dessous.",
  },
  sidebarFooter: {
    myAccountLabel: "Mon Compte",
    documentationLabel: "Documentation",
  },
  firstBootAdminModal: {
    title: "Création du compte Administrateur de la plateforme",
    description:
      "Aucun compte administrateur n'est encore enregistré. Créez le premier compte Administrateur pour configurer votre organisation.",
    firstTimeBadge: "Première mise en route",
    fullNameLabel: "Nom complet",
    fullNamePlaceholder: "Ex : Romain",
    emailLabel: "Adresse e-mail",
    emailPlaceholder: "admin@entreprise.fr",
    passwordLabel: "Mot de passe", // pragma: allowlist secret
    confirmPasswordLabel: "Confirmer le mot de passe", // pragma: allowlist secret
    showPasswordLabel: "Afficher le mot de passe", // pragma: allowlist secret
    hidePasswordLabel: "Masquer le mot de passe", // pragma: allowlist secret
    passwordMismatchError: "Les deux mots de passe ne correspondent pas.", // pragma: allowlist secret
    assignedRoleBadge: "Rôle attribué : Administrateur de la plateforme",
    submitCta: "Créer le compte Administrateur",
    missingFieldsHint:
      "Renseignez le nom complet et l'adresse e-mail (avec mot de passe concordant) pour créer le compte Administrateur.",
    reopenSetupCta: "Créer le compte Administrateur",
    day0DisabledAdminMissingReason:
      "Créez d'abord le premier compte Administrateur pour accéder à cette section.",
  },
  streamlinedCockpit: {
    zeroDecisionsBanner: "✅ Aucune décision en attente",
    quickAssistantTitle: "Accès rapide à Mon Assistant",
    quickAssistantPlaceholder: "Posez une question ou préparez un dossier...",
    quickAssistantCta: "Ouvrir Mon Assistant →",
    orientationAssistantTitle: "💬 Mon Assistant",
    orientationAssistantDesc:
      "Interrogez vos sources documentaires avec citations vérifiées.",
    orientationProcessesTitle: "☍ Mes Processus",
    orientationProcessesDesc:
      "Configurez et lancez vos processus métiers étape par étape.",
    orientationSpacesTitle: "📦 Mes Espaces",
    orientationSpacesDesc:
      "Gérez vos sources, vos livrables et le glossaire de votre équipe.",
    kpiAnchorsLabel: "Rédactions attendues",
    kpiArbitrationsLabel: "Arbitrages rapides",
    kpiReviewsLabel: "Relectures complètes",
    kpiAlertsLabel: "Alertes",
    filterAllLabel: "Toutes les décisions",
    filterShortLabel: "Arbitrages rapides",
    filterHeavyLabel: "Relectures détaillées",
    tieBreakInlineBadge: "⚖️ Arbitrage rapide sur place",
    tieBreakResolvedPrefix: "Décision enregistrée :",
    heavyActionBadge: "🔒 Relecture détaillée requise",
    openFocusReviewCta: "Ouvrir l'atelier de relecture →",
    focusWorkshopBreadcrumbPrefix: "Mes Processus › Exécutions & Décisions ›",
    focusWorkshopCloseCta: "← Retour au Cockpit",
    redisLockAcquiredPrefix: "🔒 Pris en charge par vous :",
  },
  progressiveAccostage: {
    bannerTitle: "Guide de Démarrage de la Plateforme",
    welcomeWizardTitle: "Assistant de Bienvenue",
    step1AdminTitle: "Étape 1 : Compte Administrateur de la plateforme",
    step2LlmTitle: "Étape 2 : Connexion des Modèles IA (1 modèle pour démarrer, 2 pour les revues croisées)",
    step3SpaceTitle: "Étape 3 : Parcours en 6 jalons",
    bootstrapTokenLabel: "Clé d'installation initiale",
    bootstrapTokenPlaceholder: "Saisissez la clé d'installation fournie au déploiement...",
    bootstrapTokenDeniedBanner:
      "Clé d'installation invalide — Vérifiez la clé générée lors du déploiement",
    createFirstAdminCta: "Créer le compte Administrateur de la plateforme",
    addFirstModelCta: "+ Configurer un 1er modèle IA",
    addSecondModelFamilyCta: "+ Ajouter un 2e fournisseur IA indépendant",
    singleFamilyAmberWarning:
      "⚠️ Un seul fournisseur IA configuré — Ajoutez un 2e fournisseur indépendant dans Configuration › Modèles IA pour activer les revues croisées",
    dualFamilyAd10UnlockedBadge:
      "✅ Au moins 2 fournisseurs IA indépendants actifs — Revues croisées disponibles",
    assistantTrialReadyBadge:
      "🚀 Prêt à démarrer : Mon Assistant et le Cockpit sont disponibles",
    progressLabelPrefix: "Accostage",
    progressFormatTemplate: "{completed} / {total} complétées",
    collapseGuideLabel: "Réduire",
    expandGuideLabel: "Déplier le guide",
    milestoneDoneLabel: "Terminé",
    milestoneOpenLabel: "Configurer",
    adminInitializedBadge: "Administrateur de plateforme initialisé",
  },
  topHeaderSearch: {
    modalTitle: "Recherche Globale (⌘K)",
    inputPlaceholder: "Rechercher un dossier, un processus, un document, un terme métier ou une aide...",
    scopeScreenLabel: "📍 Cet écran",
    scopeWorkspaceLabel: "📦 Cet Espace",
    scopeAllWorkspacesLabel: "🌐 Tous mes Espaces",
    speed1SectionTitle: "Correspondances exactes",
    speed2SectionTitle: "Passages proches par le sens",
    semanticCloseMatchBadge: "✨ Passage proche",
    emptyResultsLabel: "Aucun résultat trouvé dans ce périmètre.",
    previewPaneTitle: "Aperçu rapide (⌘+Entrée)",
    deepLinkActionLabel: "Ouvrir ↵",
    openHelpColumnActionLabel: "Ouvrir l'aide",
    askAssistantFooterPrefix: "💬 Poser la question",
    askAssistantFooterSuffix: "à Mon Assistant →",
    familyLabels: {
      FOLDERS_DISCUSSIONS: "Dossiers & Discussions",
      PROCESSES_EXECUTIONS: "Processus & Exécutions",
      AGENTS_TOOLS: "Agents & Outils",
      DELIVERABLES_ARTIFACTS: "Livrables & Documents",
      SOURCES_SNIPPETS: "Sources & Extraits",
      ONTOLOGY_GLOSSARY: "Glossaire & Règles",
      HELP_ACTIONS: "Aide & Raccourcis",
    },
  },
  userAccountAndSettings: {
    triggerAriaLabel: "Ouvrir le menu de mon compte",
    popover: {
      triggerAriaLabel: "Mon compte",
      personalizationLabel: "Personnalisation",
      profileLabel: "Profil",
      settingsLabel: "Paramètres",
      helpMenuLabel: "Aide",
      helpCenterLabel: "Centre d'aide & Guides",
      showcaseLabel: "Présentation d'ORCIA",
      logoutLabel: "Se déconnecter",
    },
    modalTitle: "Paramètres du compte",
    closeButtonLabel: "Fermer (Échap)",
    tabGeneralTitle: "Général",
    tabPersonalizationTitle: "Personnalisation",
    tabAccountSecurityTitle: "Compte & Sécurité",
    tabPassthroughTitle: "Connexions aux outils",
    tabMcpKeysTitle: "Clés IDE & MCP",
    appearanceLabel: "Apparence",
    themeLightLabel: "Clair",
    themeDarkLabel: "Sombre",
    themeSystemLabel: "Système",
    languageLabel: "Langue",
    localeFrLabel: "Français",
    localeEnLabel: "English",
    autoOpenHelpLabel: "Ouverture automatique de l'aide contextuelle",
    notificationsEnabledLabel: "Notifications actives",
    assistantHatLabel: "Casquette métier de Mon Assistant",
    assistantHatOptions: {
      ANALYST_PM_PO: "Product Manager / Métier",
      ARCHITECT: "Architecte Solution & SI",
      TECH_LEAD_DEV: "Référent Technique / Développeur",
      SECURITY_COMPLIANCE: "Sécurité & Conformité",
      BU_LEAD: "Responsable de Direction (BU)",
    },
    assistantToneLabel: "Ton des réponses",
    assistantToneOptions: {
      balanced: "Équilibré (structuré & actionnable)",
      concise: "Concis (synthèse directe)",
      detailed: "Détaillé (technique & approfondi)",
    },
    personalInstructionsLabel: "Instructions personnelles permanentes",
    personalInstructionsPlaceholder:
      "Ex. Privilégier les tableaux de synthèse, citer les sources et signaler les risques...",
    savePersonalizationLabel: "Enregistrer la personnalisation",
    personalizationSavedMessage: "Préférences de personnalisation enregistrées.",
    customizeAssistantRedirectCta: "Ouvrir Mon Assistant →",
    testPassthroughTokenCta: "Tester ma connexion",
    mcpTargetKindLabel: "Cible MCP",
    mcpTokenLabelField: "Libellé de la clé",
    mcpTokenLabelPlaceholder: "Ex. Cursor IDE — Espace Sinistres",
    mcpTargetSlugLabel: "Slug (Espace ou Agent)",
    mcpTargetSlugPlaceholder: "ex. mon-espace",
    mcpExpiryLabel: "Expiration",
    mcpExpiry30Label: "30 jours",
    mcpExpiry90Label: "90 jours",
    mcpRpmLimitLabel: "Plafond RPM",
    generateMcpTokenCta: "Créer une clé d'accès MCP",
    issuedPlaintextWarning:
      "Copiez cette clé maintenant : elle ne sera plus jamais affichée.",
    copyPlaintextCta: "Copier",
    copiedPlaintextLabel: "Copié",
    revokeMcpTokenCta: "Révoquer",
    revokedBadgeLabel: "Révoquée",
    emptyMcpTokensLabel: "Aucune clé IDE/MCP créée pour le moment.",
    targetWholeSpaceLabel: "Tout l'Espace de travail",
    targetSingleAgentLabel: "Un agent spécifique uniquement",
    ideJsonReadyTitle: "Configuration JSON prête pour votre éditeur (VS Code / Cursor / Claude)",
    savingLabel: "Enregistrement...",
    preferencesSavedMessage: "Préférences enregistrées.",
    twoFactorSectionTitle: "Double authentification (2FA)",
    twoFactorConfiguredLabel: "Activée",
    twoFactorOptionalPolicyLabel: "Politique socle : Optionnelle",
    profileIdentityTitle: "Identité & Rôles Actifs",
    profileTeamsFinopsTitle: "Mes équipes & rattachements FinOps",
    profileTeamsReadOnlyBadge: "Lecture seule gouvernée",
    profileTeamsEmptyText: "Aucune équipe opérationnelle explicitement rattachée.",
    profileBillingActiveLabel: "Facturation active",
    profileBillingInactiveLabel: "Sans facturation",
    profileBillingUnitsPrefix: "Unités de facturation associées : ",
    passthroughAttributionTitle: "Attribution nominative des actions d'outils",
    passthroughAttributionSubtitle:
      "Renseignez vos identifiants personnels une seule fois au niveau du socle pour que vos actions Jira, GitLab ou Confluence soient signées en votre nom propre.",
    passthroughTokenSavedMessage: "Jeton personnel enregistré avec succès.",
    passthroughTokenSaveError: "Erreur lors de l'enregistrement du jeton.",
    passthroughTokenRevokedMessage: "Jeton révoqué.",
    passthroughTokenRevokeError: "Erreur lors de la révocation du jeton.",
    passthroughNotConnectedLabel: "Non connecté",
    passthroughLoginPlaceholder: "Identifiant (@login)",
    passthroughTokenPlaceholder: "Jeton d'accès (PAT/Secret)",
    passthroughSaveTokenCta: "Enregistrer mon jeton",
    passthroughCancelCta: "Annuler",
    passthroughNoLoginLabel: "Aucun identifiant associé",
    passthroughReplaceTokenCta: "Remplacer le jeton",
    passthroughConnectTokenCta: "Connecter mon jeton",
    passthroughRevokeTokenCta: "Révoquer",
    passthroughEmptyConnectorsMessage:
      "Aucun connecteur configuré au niveau du socle pour le moment.",
    passwordSecurity: {
      title: "Sécurité & Mot de Passe",
      renewalRequiredBadge: "Renouvellement Requis",
      temporaryPasswordWarning:
        "Vous utilisez un mot de passe temporaire à renouveler obligatoirement.",
      currentPasswordLabel: "Mot de passe actuel", // pragma: allowlist secret
      newPasswordLabel: "Nouveau mot de passe (min. 12 car., Maj/Min/Chiffre)", // pragma: allowlist secret
      confirmPasswordLabel: "Confirmer le nouveau mot de passe", // pragma: allowlist secret
      submitButtonLabel: "Changer mon mot de passe",
      submittingButtonLabel: "Mise à jour...",
      updatedSuccessMessage: "Mot de passe mis à jour avec succès.",
      missingCurrentPasswordError:
        "Veuillez renseigner votre mot de passe actuel.", // pragma: allowlist secret
      weakPasswordError:
        "Le mot de passe doit comporter au moins 12 caractères (min. 1 min, 1 maj, 1 chiffre).",
      unchangedPasswordError:
        "Le nouveau mot de passe doit être différent de l'actuel.", // pragma: allowlist secret
      mismatchPasswordError: "Les deux mots de passe ne correspondent pas.", // pragma: allowlist secret
      actionNotConfiguredError: "Action non configurée.",
      genericError: "Erreur lors de la modification du mot de passe.",
    },
  },
  contextualHelpHybrid: {
    columnHeaderTitle: "Aide Contextuelle",
    centerHeaderTitle: "Centre d'Aide & Guides Pratiques",
    whatForSectionTitle: "À quoi sert cet écran ?",
    stepByStepAccordionTitle: "Comment procéder pas à pas",
    keyTermsAccordionTitle: "Repères & notions utiles",
    faqAccordionTitle: "Questions fréquentes",
    askAssistantOnScreenCta:
      "Poser une question à Mon Assistant sur cet écran →",
    rollbackButtonLabel: "⏪ Version précédente",
    rollbackCompletedPrefix: "Version rétablie :",
    mergedLayersPrefix: "Sources du guide :",
    realExampleTitle: "Un exemple réel",
    commonPitfallsTitle: "Ce qui coince souvent",
    technicalDetailsTitle: "Détails techniques",
    stepsBlockPrefix: "En",
    stepsBlockSuffix: "gestes",
    targetedHelpBadgeLabel: "Aide ciblée",
    askAssistantPrefillTemplate: "Explique-moi comment utiliser l'écran {route} ({title})",
  },
};

export const SHELL_AND_SEARCH_EN_LABELS: ShellAndSearchDictionarySection = {
  fourZoneShell: {
    workspacePrefix: "Space",
    searchTriggerPlaceholder: "Search… (⌘K)",
    contextualHelpButtonLabel: "Help",
    notificationsButtonLabel: "Notifications",
    notificationsDrawerTitle: "Notification Center",
    notificationsEmptyText: "No unread notifications.",
    notificationsVsActivityHint:
      "The Notification Center groups your pending actions and setup prerequisites. To browse the complete audit history of your scope, open the Activity Log.",
    notificationsOpenActivityCta: "Open Activity Log →",
    autonomousNominalGroupTitle: "Nominal automated executions",
    autonomousDefaultTriggerLabel: "Automated under contract",
    sidebarAriaLabel: "Main navigation",
    railCollapseLabel: "Collapse menu",
    railExpandLabel: "Expand menu",
    packSelectorLabel: "Active business domain",
    helpColumnTitle: "Contextual Help",
    helpColumnExpectedTitle: "About this screen",
    helpColumnExpectedBody:
      "Find detailed explanations and practical tips related to your current screen here.",
    helpColumnScrollMoreLabel: "Scroll down for more ↓",
    menuEntries: {
      cockpit: "Cockpit",
      assistant: "My Assistant",
      processes: "My Processes",
      agents: "My Agents",
      spaces: "My Spaces",
      finops: "FinOps",
      configuration: "Configuration",
      help: "Help",
    },
    organizationMenuLabel: "My Organization",
    activityMenuLabel: "Activity Log",
    doubleSelector: {
      teamBuLabel: "Team / Division",
      workspaceLabel: "Space",
      allWorkspacesOption: "All spaces",
    },
    mobileTabs: {
      navAriaLabel: "Mobile navigation",
      cockpit: "Cockpit",
      assistant: "My Assistant",
      decisions: "Decisions",
      menuLabel: "Menu",
    },
    mobileDesktopRecommendedText:
      "Optimized for desktop view: all controls remain accessible below.",
  },
  sidebarFooter: {
    myAccountLabel: "My Account",
    documentationLabel: "Documentation",
  },
  firstBootAdminModal: {
    title: "Create Platform Administrator Account",
    description:
      "No administrator account is registered yet. Create the first Administrator account to configure your organization.",
    firstTimeBadge: "First-Time Setup",
    fullNameLabel: "Full name",
    fullNamePlaceholder: "e.g. Romain",
    emailLabel: "Email address",
    emailPlaceholder: "admin@company.com",
    passwordLabel: "Password", // pragma: allowlist secret
    confirmPasswordLabel: "Confirm password", // pragma: allowlist secret
    showPasswordLabel: "Show password", // pragma: allowlist secret
    hidePasswordLabel: "Hide password", // pragma: allowlist secret
    passwordMismatchError: "Passwords do not match.", // pragma: allowlist secret
    assignedRoleBadge: "Assigned role: Platform Administrator",
    submitCta: "Create Administrator Account",
    missingFieldsHint:
      "Enter full name and email address (with matching password) to create the Administrator account.",
    reopenSetupCta: "Create Administrator Account",
    day0DisabledAdminMissingReason:
      "Create the first Administrator account first to access this section.",
  },
  streamlinedCockpit: {
    zeroDecisionsBanner: "✅ No pending decisions",
    quickAssistantTitle: "Quick access to My Assistant",
    quickAssistantPlaceholder: "Ask a question or prepare a briefing...",
    quickAssistantCta: "Open My Assistant →",
    orientationAssistantTitle: "💬 My Assistant",
    orientationAssistantDesc:
      "Query your document sources with verified citations.",
    orientationProcessesTitle: "☍ My Processes",
    orientationProcessesDesc:
      "Configure and run your business processes step by step.",
    orientationSpacesTitle: "📦 My Spaces",
    orientationSpacesDesc:
      "Manage your sources, deliverables, and team glossary.",
    kpiAnchorsLabel: "Required entries",
    kpiArbitrationsLabel: "Quick decisions",
    kpiReviewsLabel: "Full reviews",
    kpiAlertsLabel: "Alerts",
    filterAllLabel: "All decisions",
    filterShortLabel: "Quick decisions",
    filterHeavyLabel: "Detailed reviews",
    tieBreakInlineBadge: "⚖️ Quick inline decision",
    tieBreakResolvedPrefix: "Decision saved:",
    heavyActionBadge: "🔒 Detailed review required",
    openFocusReviewCta: "Open Review Workshop →",
    focusWorkshopBreadcrumbPrefix: "My Processes › Executions & Decisions ›",
    focusWorkshopCloseCta: "← Back to Cockpit",
    redisLockAcquiredPrefix: "🔒 Handled by you:",
  },
  progressiveAccostage: {
    bannerTitle: "Platform Getting Started Guide",
    welcomeWizardTitle: "Welcome Setup Assistant",
    step1AdminTitle: "Step 1: Platform Administrator Account",
    step2LlmTitle: "Step 2: Connect AI Models (1 model to start, 2 for cross-checked reviews)",
    step3SpaceTitle: "Step 3: 6-step setup path",
    bootstrapTokenLabel: "Initial installation key",
    bootstrapTokenPlaceholder: "Enter the installation key provided at deployment...",
    bootstrapTokenDeniedBanner:
      "Invalid installation key — Please check the key generated during deployment",
    createFirstAdminCta: "Create Platform Administrator account",
    addFirstModelCta: "+ Configure 1st AI model",
    addSecondModelFamilyCta: "+ Add 2nd independent AI provider",
    singleFamilyAmberWarning:
      "⚠️ Only one AI provider configured — Add a 2nd independent provider in Configuration › AI Models to enable cross-checked reviews",
    dualFamilyAd10UnlockedBadge:
      "✅ At least 2 independent AI providers active — Cross-checked reviews enabled",
    assistantTrialReadyBadge:
      "🚀 Ready to start: My Assistant and Cockpit are available",
    progressLabelPrefix: "Onboarding",
    progressFormatTemplate: "{completed} of {total} completed",
    collapseGuideLabel: "Collapse",
    expandGuideLabel: "Expand guide",
    milestoneDoneLabel: "Completed",
    milestoneOpenLabel: "Configure",
    adminInitializedBadge: "Platform administrator initialized",
  },
  topHeaderSearch: {
    modalTitle: "Global Search (⌘K)",
    inputPlaceholder: "Search folders, processes, documents, business terms, or help...",
    scopeScreenLabel: "📍 This screen",
    scopeWorkspaceLabel: "📦 This Space",
    scopeAllWorkspacesLabel: "🌐 All my Spaces",
    speed1SectionTitle: "Exact matches",
    speed2SectionTitle: "Related passages by meaning",
    semanticCloseMatchBadge: "✨ Related passage",
    emptyResultsLabel: "No results found in this scope.",
    previewPaneTitle: "Quick preview (⌘+Enter)",
    deepLinkActionLabel: "Open ↵",
    openHelpColumnActionLabel: "Open Help",
    askAssistantFooterPrefix: "💬 Ask",
    askAssistantFooterSuffix: "to My Assistant →",
    familyLabels: {
      FOLDERS_DISCUSSIONS: "Folders & Discussions",
      PROCESSES_EXECUTIONS: "Processes & Executions",
      AGENTS_TOOLS: "Agents & Tools",
      DELIVERABLES_ARTIFACTS: "Deliverables & Documents",
      SOURCES_SNIPPETS: "Sources & Excerpts",
      ONTOLOGY_GLOSSARY: "Glossary & Rules",
      HELP_ACTIONS: "Help & Shortcuts",
    },
  },
  userAccountAndSettings: {
    triggerAriaLabel: "Open my account menu",
    popover: {
      triggerAriaLabel: "My Account",
      personalizationLabel: "Personalization",
      profileLabel: "Profile",
      settingsLabel: "Settings",
      helpMenuLabel: "Help",
      helpCenterLabel: "Help Center & Guides",
      showcaseLabel: "About ORCIA",
      logoutLabel: "Sign out",
    },
    modalTitle: "Account Settings",
    closeButtonLabel: "Close",
    tabGeneralTitle: "General",
    tabPersonalizationTitle: "Personalization",
    tabAccountSecurityTitle: "Account & Security",
    tabPassthroughTitle: "Tool Connections",
    tabMcpKeysTitle: "IDE & MCP Keys",
    appearanceLabel: "Appearance",
    themeLightLabel: "Light",
    themeDarkLabel: "Dark",
    themeSystemLabel: "System",
    languageLabel: "Language",
    localeFrLabel: "Français",
    localeEnLabel: "English",
    autoOpenHelpLabel: "Automatically open contextual help",
    notificationsEnabledLabel: "Enable notifications",
    assistantHatLabel: "My Assistant Business Hat",
    assistantHatOptions: {
      ANALYST_PM_PO: "Product Manager / Business",
      ARCHITECT: "Solution & Enterprise Architect",
      TECH_LEAD_DEV: "Technical Lead / Developer",
      SECURITY_COMPLIANCE: "Security & Compliance",
      BU_LEAD: "Business Unit Lead",
    },
    assistantToneLabel: "Response tone",
    assistantToneOptions: {
      balanced: "Balanced (structured & actionable)",
      concise: "Concise (direct summary)",
      detailed: "Detailed (deep technical)",
    },
    personalInstructionsLabel: "Permanent personal instructions",
    personalInstructionsPlaceholder:
      "e.g. Prefer summary tables, cite sources, and highlight risks...",
    savePersonalizationLabel: "Save personalization",
    personalizationSavedMessage: "Personalization preferences saved.",
    customizeAssistantRedirectCta: "Open My Assistant →",
    testPassthroughTokenCta: "Test my connection",
    mcpTargetKindLabel: "MCP Target",
    mcpTokenLabelField: "Key label",
    mcpTokenLabelPlaceholder: "e.g. Cursor IDE — Claims Space",
    mcpTargetSlugLabel: "Slug (Space or Agent)",
    mcpTargetSlugPlaceholder: "e.g. my-space",
    mcpExpiryLabel: "Expiration",
    mcpExpiry30Label: "30 days",
    mcpExpiry90Label: "90 days",
    mcpRpmLimitLabel: "RPM cap",
    generateMcpTokenCta: "Create personal MCP key",
    issuedPlaintextWarning:
      "Copy this key now: it will never be shown again.",
    copyPlaintextCta: "Copy",
    copiedPlaintextLabel: "Copied",
    revokeMcpTokenCta: "Revoke",
    revokedBadgeLabel: "Revoked",
    emptyMcpTokensLabel: "No IDE/MCP key created yet.",
    targetWholeSpaceLabel: "Entire Workspace",
    targetSingleAgentLabel: "A single specific agent",
    ideJsonReadyTitle: "JSON configuration ready for your editor (VS Code / Cursor / Claude)",
    savingLabel: "Saving...",
    preferencesSavedMessage: "Preferences saved.",
    twoFactorSectionTitle: "Two-factor authentication (2FA)",
    twoFactorConfiguredLabel: "Enabled",
    twoFactorOptionalPolicyLabel: "Platform policy: Optional",
    profileIdentityTitle: "Identity & Active Roles",
    profileTeamsFinopsTitle: "My Teams & FinOps Allocations",
    profileTeamsReadOnlyBadge: "Governed read-only",
    profileTeamsEmptyText: "No operational team explicitly assigned.",
    profileBillingActiveLabel: "Billing active",
    profileBillingInactiveLabel: "No billing",
    profileBillingUnitsPrefix: "Associated billing units: ",
    passthroughAttributionTitle: "Nominative Action Attribution",
    passthroughAttributionSubtitle:
      "Set up your personal credentials once at platform level so your Jira, GitLab, or Confluence actions are signed under your personal name.",
    passthroughTokenSavedMessage: "Personal token saved successfully.",
    passthroughTokenSaveError: "Error saving token.",
    passthroughTokenRevokedMessage: "Token revoked.",
    passthroughTokenRevokeError: "Error revoking token.",
    passthroughNotConnectedLabel: "Not connected",
    passthroughLoginPlaceholder: "Login (@username)",
    passthroughTokenPlaceholder: "Personal Access Token",
    passthroughSaveTokenCta: "Save token",
    passthroughCancelCta: "Cancel",
    passthroughNoLoginLabel: "No login attached",
    passthroughReplaceTokenCta: "Replace token",
    passthroughConnectTokenCta: "Connect token",
    passthroughRevokeTokenCta: "Revoke",
    passthroughEmptyConnectorsMessage:
      "No platform connectors configured yet.",
    passwordSecurity: {
      title: "Security & Password",
      renewalRequiredBadge: "Renewal Required",
      temporaryPasswordWarning:
        "You are using a temporary password that must be renewed.",
      currentPasswordLabel: "Current password", // pragma: allowlist secret
      newPasswordLabel: "New password (min. 12 chars, upper/lower/digit)", // pragma: allowlist secret
      confirmPasswordLabel: "Confirm new password", // pragma: allowlist secret
      submitButtonLabel: "Change password",
      submittingButtonLabel: "Updating...",
      updatedSuccessMessage: "Password updated successfully.",
      missingCurrentPasswordError: "Please enter your current password.", // pragma: allowlist secret
      weakPasswordError:
        "Password requires 12+ chars with upper, lower, and digit.",
      unchangedPasswordError:
        "New password must differ from current password.", // pragma: allowlist secret
      mismatchPasswordError: "Passwords do not match.", // pragma: allowlist secret
      actionNotConfiguredError: "Action not configured.",
      genericError: "Failed to change password.",
    },
  },
  contextualHelpHybrid: {
    columnHeaderTitle: "Contextual Help",
    centerHeaderTitle: "Help Center & Practical Guides",
    whatForSectionTitle: "What is this screen for?",
    stepByStepAccordionTitle: "How to proceed step by step",
    keyTermsAccordionTitle: "Key concepts & pointers",
    faqAccordionTitle: "Frequently asked questions",
    askAssistantOnScreenCta: "Ask My Assistant about this screen →",
    rollbackButtonLabel: "⏪ Previous version",
    rollbackCompletedPrefix: "Restored version:",
    mergedLayersPrefix: "Guide sources:",
    realExampleTitle: "A real example",
    commonPitfallsTitle: "Common pitfalls",
    technicalDetailsTitle: "Technical details",
    stepsBlockPrefix: "In",
    stepsBlockSuffix: "steps",
    targetedHelpBadgeLabel: "Targeted help",
    askAssistantPrefillTemplate: "Help me understand screen {route} ({title})",
  },
};
