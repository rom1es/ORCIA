export interface AdminAndStudioDictionarySection {
  readonly settingsHub: {
    readonly hubTitle: string;
    readonly hubSubtitle: string;
    readonly tabs: {
      readonly iam: string;
      readonly connectors: string;
      readonly aiModels: string;
      readonly packs: string;
      readonly workflows: string;
      readonly audit: string;
    };
    readonly lockedSectionNotice: string;
    readonly requestAccessLabel: string;
    readonly secretFieldLabels: {
      readonly configuredBadge: string;
      readonly unconfiguredBadge: string;
      readonly fingerprintLabel: string;
      readonly keepButton: string;
      readonly replaceButton: string;
      readonly clearButton: string;
      readonly inputPlaceholder: string;
    };
    readonly tierLabels: {
      readonly simple: string;
      readonly medium: string;
      readonly complex: string;
      readonly auto: string;
      readonly autoResolvedPrefix: string;
    };
    readonly effortLabels: {
      readonly default: string;
      readonly fast: string;
      readonly balanced: string;
      readonly deep: string;
    };
    readonly studioLabels: {
      readonly prePromptButton: string;
      readonly contractButton: string;
      readonly triggersButton: string;
      readonly dryRunButton: string;
      readonly forkButton: string;
      readonly publishButton: string;
      readonly readOnlyPublishedHint: string;
      readonly layersBadgePrefix: string;
      readonly inputsZoneTitle: string;
      readonly capabilitiesZoneTitle: string;
      readonly deliverablesZoneTitle: string;
      readonly enabledStatusLabel: string;
      readonly skippedStatusLabel: string;
      readonly deleteActionLabel: string;
    };
    readonly wizardLabels: {
      readonly title: string;
      readonly resumeBannerText: string;
      readonly stepCounterPrefix: string;
      readonly validateAndContinueButton: string;
      readonly completedBadgeText: string;
      readonly demoWorkspaceButton: string;
      readonly citationLabel: string;
    };
  };
}

export const ADMIN_AND_STUDIO_FR_LABELS: AdminAndStudioDictionarySection = {
  settingsHub: {
    hubTitle: "Configuration de la Plateforme & Organisation",
    hubSubtitle:
      "Gérez la structure de votre organisation, les droits d'accès, les sources connectées, les modèles IA et les modèles de processus.",
    tabs: {
      iam: "Organisation & Habilitations",
      connectors: "Sources & Connecteurs",
      aiModels: "Modèles IA",
      packs: "Packs Métiers",
      workflows: "Atelier de Processus",
      audit: "Journal d'Activité",
    },
    lockedSectionNotice:
      "Cette section est affichée en lecture seule — un droit d'administration est nécessaire pour la modifier.",
    requestAccessLabel: "Demander l'accès à un administrateur",
    secretFieldLabels: {
      configuredBadge: "Configuré",
      unconfiguredBadge: "Non configuré",
      fingerprintLabel: "Identifiant de clé enregistrée",
      keepButton: "Conserver",
      replaceButton: "Remplacer",
      clearButton: "Effacer",
      inputPlaceholder: "Saisir la nouvelle clé secrète...", // pragma: allowlist secret
    },
    tierLabels: {
      simple: "Simple",
      medium: "Standard",
      complex: "Approfondi",
      auto: "Automatique (selon la demande)",
      autoResolvedPrefix: "niveau choisi :",
    },
    effortLabels: {
      default: "Par défaut",
      fast: "Rapide",
      balanced: "Équilibré",
      deep: "Approfondi",
    },
    studioLabels: {
      prePromptButton: "Consignes de l'assistant",
      contractButton: "Données attendues",
      triggersButton: "Déclencheurs",
      dryRunButton: "▷ Tester à blanc",
      forkButton: "Créer une nouvelle version",
      publishButton: "Publier la version",
      readOnlyPublishedHint: "Version publiée (non modifiable directement)",
      layersBadgePrefix: "NIVEAUX",
      inputsZoneTitle: "1. Informations d'Entrée & Contexte",
      capabilitiesZoneTitle: "2. Étapes & Agents Mobilisés",
      deliverablesZoneTitle: "3. Livrables & Vérifications",
      enabledStatusLabel: "Actif",
      skippedStatusLabel: "Désactivé",
      deleteActionLabel: "Retirer",
    },
    wizardLabels: {
      title: "Assistants Guidés de Configuration",
      resumeBannerText: "Votre progression a été restaurée là où vous vous étiez arrêté",
      stepCounterPrefix: "Étape",
      validateAndContinueButton: "Valider et continuer",
      completedBadgeText: "Configuration terminée",
      demoWorkspaceButton: "Créer un espace d'exemple prêt à l'emploi",
      citationLabel: "Source documentaire vérifiée",
    },
  },
};

export const ADMIN_AND_STUDIO_EN_LABELS: AdminAndStudioDictionarySection = {
  settingsHub: {
    hubTitle: "Platform Configuration & Organization",
    hubSubtitle:
      "Manage your organization structure, access permissions, connected sources, AI models, and process templates.",
    tabs: {
      iam: "Organization & Permissions",
      connectors: "Sources & Connectors",
      aiModels: "AI Models",
      packs: "Business Packs",
      workflows: "Process Studio",
      audit: "Activity Log",
    },
    lockedSectionNotice:
      "This section is displayed in read-only mode — administrator permissions are required to edit it.",
    requestAccessLabel: "Request access from an administrator",
    secretFieldLabels: {
      configuredBadge: "Configured",
      unconfiguredBadge: "Not configured",
      fingerprintLabel: "Saved key identifier",
      keepButton: "Keep",
      replaceButton: "Replace",
      clearButton: "Clear",
      inputPlaceholder: "Enter new secret key...", // pragma: allowlist secret
    },
    tierLabels: {
      simple: "Simple",
      medium: "Standard",
      complex: "In-Depth",
      auto: "Automatic (based on request)",
      autoResolvedPrefix: "selected level:",
    },
    effortLabels: {
      default: "Default",
      fast: "Fast",
      balanced: "Balanced",
      deep: "In-Depth",
    },
    studioLabels: {
      prePromptButton: "Assistant instructions",
      contractButton: "Expected data",
      triggersButton: "Triggers",
      dryRunButton: "▷ Run test preview",
      forkButton: "Create new version",
      publishButton: "Publish version",
      readOnlyPublishedHint: "Published version (read-only)",
      layersBadgePrefix: "LEVELS",
      inputsZoneTitle: "1. Input Information & Context",
      capabilitiesZoneTitle: "2. Steps & Assigned Agents",
      deliverablesZoneTitle: "3. Deliverables & Checks",
      enabledStatusLabel: "Enabled",
      skippedStatusLabel: "Disabled",
      deleteActionLabel: "Remove",
    },
    wizardLabels: {
      title: "Guided Setup Assistants",
      resumeBannerText: "Your progress was restored from where you left off",
      stepCounterPrefix: "Step",
      validateAndContinueButton: "Validate and continue",
      completedBadgeText: "Setup completed",
      demoWorkspaceButton: "Create a ready-to-use sample workspace",
      citationLabel: "Verified document source",
    },
  },
};
