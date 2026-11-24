import type { TranslationDictionary } from "../types";

export const CORE_SHELL_FR_LABELS: Pick<
  TranslationDictionary,
  "shell" | "humanAnchor" | "arbitrationTieBreak" | "modulePages"
> = {
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
    placeholderText:
      "Saisissez vos orientations et hypothèses structurantes (rédaction personnelle requise)...",
    submitLabel: "Valider et signer ma saisie",
    defaultSectionTitle: "Intentions & Orientations Métier",
    defaultAuthorName: "Responsable référent",
    defaultValue: "Définition des objectifs prioritaires et des critères d'acceptation attendus.",
  },
  arbitrationTieBreak: {
    badgeTitle: "⚖️ ARBITRAGE REQUIS",
    policyPrefixLabel: "Règle de départage",
    policyLabels: {
      pauseAndEscalate: "Pause et escalade humaine",
      ontologyAxiomFirst: "Règle métier prioritaire",
      deferWithAssumption: "Poursuivre sous hypothèse",
    },
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
      uriBadgeExample: "Administration",
    },
  },
};
