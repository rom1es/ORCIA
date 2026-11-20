import {
  IAM_TAB_EN_LABELS,
  IAM_TAB_FR_LABELS,
  type IamTabDictionarySection,
} from "./iam_accounts_labels";
import {
  ORGANIZATION_TAB_EN_LABELS,
  ORGANIZATION_TAB_FR_LABELS,
  type OrganizationTabDictionarySection,
} from "./organization_tab_labels";

export interface AdminAndStudioDictionarySection {
  readonly settingsHub: {
    readonly hubTitle: string;
    readonly hubSubtitle: string;
    readonly tabs: {
      readonly organization: string;
      readonly iam: string;
      readonly authentication: string;
      readonly models: string;
      readonly connectors: string;
      readonly packs: string;
    };
    readonly lockedSectionNotice: string;
    readonly requestAccessLabel: string;
    readonly readOnlyRestrictedTitle: string;
    readonly readOnlyRestrictedBody: string;
    readonly openMyAccountCta: string;
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
      readonly subtitle: string;
      readonly resumeBannerText: string;
      readonly stepCounterPrefix: string;
      readonly stepCounterConnector: string;
      readonly stepBackButton: string;
      readonly validateAndContinueButton: string;
      readonly completedBadgeText: string;
      readonly demoWorkspaceButton: string;
      readonly citationLabel: string;
      readonly disabledStepReason: string;
      readonly profileLabels: {
        readonly sdlc_tech_lead: string;
        readonly ops_manager: string;
        readonly secops_admin: string;
      };
    };
    readonly organizationTab: OrganizationTabDictionarySection;
    readonly iamTab: IamTabDictionarySection;
  };
}

export const ADMIN_AND_STUDIO_FR_LABELS: AdminAndStudioDictionarySection = {
  settingsHub: {
    hubTitle: "Administration de la plateforme",
    hubSubtitle:
      "Gérez les comptes et habilitations, l'authentification, les modèles IA, les connecteurs externes et les packs métiers.",
    tabs: {
      organization: "Organisation",
      iam: "Comptes & Habilitations",
      authentication: "Authentification",
      models: "Modèles IA",
      connectors: "Connecteurs",
      packs: "Packs Métiers",
    },
    lockedSectionNotice:
      "Cette section est affichée en lecture seule — un droit d'administration est nécessaire pour la modifier.",
    requestAccessLabel: "Demander l'accès à un administrateur",
    readOnlyRestrictedTitle: "Accès en lecture seule sur l'administration de la plateforme",
    readOnlyRestrictedBody:
      "Votre rôle actuel ne permet pas de modifier les paramètres globaux ou organisationnels. Pour gérer vos préférences personnelles (apparence, langue, rôle par défaut, clés d'accès personnelles), ouvrez Mon Compte.",
    openMyAccountCta: "Ouvrir Mon Compte",
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
      subtitle: "Vous accompagne étape par étape pour configurer votre environnement.",
      resumeBannerText: "Votre progression a été restaurée là où vous vous étiez arrêté",
      stepCounterPrefix: "Étape",
      stepCounterConnector: "sur",
      stepBackButton: "← Étape précédente",
      validateAndContinueButton: "Valider et continuer",
      completedBadgeText: "Configuration terminée",
      demoWorkspaceButton: "Créer un espace d'exemple prêt à l'emploi",
      citationLabel: "Source documentaire vérifiée",
      disabledStepReason: "Complétez la vérification de l'étape en cours pour continuer.",
      profileLabels: {
        sdlc_tech_lead: "Création d'un Espace de travail d'équipe",
        ops_manager: "Connexion d'une source documentaire ou outil",
        secops_admin: "Configuration initiale de l'organisation",
      },
    },
    organizationTab: ORGANIZATION_TAB_FR_LABELS,
    iamTab: IAM_TAB_FR_LABELS,
  },
};

export const ADMIN_AND_STUDIO_EN_LABELS: AdminAndStudioDictionarySection = {
  settingsHub: {
    hubTitle: "Platform Administration",
    hubSubtitle:
      "Manage user accounts and permissions, authentication, AI models, external connectors, and business packs.",
    tabs: {
      organization: "Organization",
      iam: "Accounts & Permissions",
      authentication: "Authentication",
      models: "AI Models",
      connectors: "Connectors",
      packs: "Business Packs",
    },
    lockedSectionNotice:
      "This section is displayed in read-only mode — administrator permissions are required to edit it.",
    requestAccessLabel: "Request access from an administrator",
    readOnlyRestrictedTitle: "Read-only access on platform administration",
    readOnlyRestrictedBody:
      "Your current role does not allow modifying global or organizational settings. To manage your personal preferences (theme, language, default role, personal access keys), open My Account.",
    openMyAccountCta: "Open My Account",
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
      subtitle: "Guides you step by step to set up your environment.",
      resumeBannerText: "Your progress was restored from where you left off",
      stepCounterPrefix: "Step",
      stepCounterConnector: "of",
      stepBackButton: "← Previous step",
      validateAndContinueButton: "Validate and continue",
      completedBadgeText: "Setup completed",
      demoWorkspaceButton: "Create a ready-to-use sample workspace",
      citationLabel: "Verified document source",
      disabledStepReason: "Complete the current step verification to continue.",
      profileLabels: {
        sdlc_tech_lead: "Team Workspace Setup",
        ops_manager: "Connect a Document Source or Tool",
        secops_admin: "Initial Organization Setup",
      },
    },
    organizationTab: ORGANIZATION_TAB_EN_LABELS,
    iamTab: IAM_TAB_EN_LABELS,
  },
};
