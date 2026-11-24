import type {
  ShellBreadcrumbsAndScopeDictionary,
  ShellNotificationsDictionary,
} from "./shell_notifications_labels";

export const SHELL_NOTIFICATIONS_FR: ShellNotificationsDictionary = {
  tempPassword: {
    badge: "Sécurité requise",
    title: "Mot de passe temporaire actif — changement requis",
    description:
      "Votre compte utilise un mot de passe temporaire. Pour sécuriser vos accès, définissez un mot de passe personnel dès maintenant.",
    cta: "Changer mon mot de passe →",
  },
  llmMissing: {
    badge: "Prérequis requis",
    title: "Aucun modèle IA configuré (menus Mon Assistant & Mes Agents verrouillés)",
    description:
      "Enregistrez au moins un fournisseur et un modèle IA dans Configuration pour déverrouiller Mon Assistant, Mes Agents et Mes Processus.",
    cta: "Configurer →",
  },
  billingTeamMissing: {
    badge: "Équipe de facturation",
    title: "Aucune Équipe de facturation rattachée (appels IA verrouillés)",
    description:
      "Tout appel IA doit être rattaché à une Équipe de facturation et un Espace de Travail. Créez une Équipe dans Configuration › Organisation et rattachez-y votre compte.",
    cta: "Créer une Équipe →",
  },
  orgMissing: {
    badge: "Organisation",
    title: "Structure d'organisation (Directions / BU & Équipes) à définir",
    description:
      "Créez au moins une Direction (BU) ou une Équipe dans Configuration pour déverrouiller l'attribution des règles d'habilitation.",
    cta: "Structurer →",
  },
  workspaceMissing: {
    badge: "Espace requis",
    title: "Aucun Espace de travail créé (menu Mes Processus verrouillé)",
    description:
      "Créez votre premier Espace de travail (collectif ou privé rattaché à une Équipe de facturation) dans 📦 Mes Espaces pour rattacher vos sources documentaires et lancer des processus.",
    cta: "Créer un Espace →",
  },
  decisionWaiting: {
    badge: "Décision attendue",
    cta: "Ouvrir →",
  },
  inboxTask: {
    openBadge: "Action requise",
    claimedBadge: "Prise en charge",
    cta: "Boîte de réception →",
  },
  autonomous: {
    escalationBadge: "Escalade autonome",
    triggerPausedBadge: "Déclencheur suspendu",
    qualitySampleBadge: "Contrôle qualité",
    sampleDescriptionTemplate: "Dossier tiré au sort pour contrôle qualité ({triggerLabel}).",
    attentionDescriptionTemplate: "Exécution automatisée nécessitant une attention ({triggerLabel}).",
    reviewCta: "Examiner →",
    nominalBadge: "Automatisé sous contrat",
    inspectCta: "Superviser →",
  },
  livePresence: {
    badge: "Présence temps réel",
    claimedTitleTemplate: "Étape prise en charge ({stepExecutionId})",
    releasedTitleTemplate: "Étape libérée ({stepExecutionId})",
    cta: "Voir →",
  },
};

export const SHELL_BREADCRUMBS_AND_SCOPE_FR: ShellBreadcrumbsAndScopeDictionary = {
  breadcrumbs: {
    inbox: "Boîte de Réception",
    studio: "Studio",
    valueStream: "Chaîne de valeur",
    qualityGates: "Validations",
    catalog: "Catalogue",
    glossary: "Glossaire",
    sources: "Sources",
    activityLog: "Journal d'Activité",
    organization: "Mon Organisation",
    guidedWizards: "Assistants Guidés",
    profile: "Profil",
    showcase: "Présentation ORCIA",
    redundantAllSpacesLabels: ["Tous les espaces", "Tous mes espaces"],
  },
  accostageMilestones: {
    firstAdmin: "1. Compte Admin",
    aiModels: "2. Modèles IA",
    organization: "3. Organisation",
    firstTeamSpace: "4. Premier Espace d'équipe",
    firstSource: "5. Première Source",
    firstProcess: "6. Premier Processus",
    activeLayersTemplate: "{count} couches actives",
  },
  disabledMenuReasons: {},
};
