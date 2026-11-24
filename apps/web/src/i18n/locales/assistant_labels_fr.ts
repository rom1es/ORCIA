import type { AssistantDictionarySection } from "./assistant_labels";
import {
  ASSISTANT_GOVERNANCE_LABELS_FR,
  ASSISTANT_SPEED_STREAM_LABELS_FR,
} from "./assistant_stream_labels_fr";

export const ASSISTANT_FR_LABELS: AssistantDictionarySection = {
  assistantGovernance: ASSISTANT_GOVERNANCE_LABELS_FR,
  assistantSpeedStream: ASSISTANT_SPEED_STREAM_LABELS_FR,
  assistantCitations: {
    freshnessFreshBadge: "✅ Source à jour",
    freshnessStaleBadge: "⚠️ Source à vérifier",
    restrictedSourcePillSuffix: "🔒 Accès restreint",
    requestAccessCta: "Demander l'accès",
    unverifiedCitationBadge: "Référence à confirmer",
    artifactCardTitlePrefix: "📄 Brouillon de Document",
    linesLabel: "Lignes",
    draftBadgeLabel: "@draft",
    copyArtifactCta: "📋 Copier",
    exportArtifactCta: "⬇ Télécharger (.md)",
    saveDraftCta: "💾 Enregistrer le brouillon",
    continueInProcessCta: "☍ Poursuivre dans un Processus avec validation →",
    v5LockNoticeText:
      "🔒 Pour garantir la qualité, toute publication vers vos outils partagés passe par une étape de validation.",
  },
  assistantFoldersSync: {
    workspaceRequired:
      "⚠️ Créez ou sélectionnez d'abord un Espace de travail pour enregistrer vos dossiers.",
    loadFailed: (detail: string) => `⚠️ Impossible de charger vos dossiers (${detail}).`,
    saveFailed: (detail: string) => `⚠️ Le dossier n'a pas pu être enregistré (${detail}).`,
  },
  assistantFolders: {
    tab1ActiveDiscussionTitle: "💬 Discussion en cours",
    tab2FoldersTitlePrefix: "📁 Dossiers",
    tab3HistorySearchTitle: "🕘 Historique & Recherche",
    activeFolderPillPrefix: "📁 Dossier actif :",
    pinnedNotesButtonLabel: "📌 Notes épinglées",
    launchProcessFromFolderCta: "☍ Démarrer un Processus à partir de ce dossier →",
    shareButtonLabel: "👥 Partager / Visibilité",
    visibilityPrivateLabel: "🔒 Privé (Moi uniquement)",
    visibilitySharedSelectedLabel: "👥 Partagé (Membres choisis)",
    visibilityWorkspaceOpenLabel: "📦 Visible par tout l'Espace",
    restrictedSourcesWarningText:
      "⚠️ Ce dossier cite des sources protégées : chaque lecteur ne verra que les extraits auxquels son compte a accès.",
    searchPlaceholder: "Rechercher dans vos discussions, dossiers et brouillons...",
    clearActiveFolderCta: "Désélectionner",
    noActiveFolderHint:
      "Aucun dossier actif sélectionné. Créez ou cliquez sur un dossier ci-dessous pour activer ses notes.",
    permanentNotesTitleTemplate:
      "Notes permanentes du dossier « {title} » (injectées dans chaque question)",
    notesSavedBadgeLabel: "Notes enregistrées et actives",
    notesTextareaPlaceholder:
      "Ex. : Toujours répondre avec des exemples structurés et respecter le glossaire métier...",
    notesEnrichHint:
      "Les notes enregistrées enrichissent automatiquement vos questions dans ce dossier.",
    saveNotesCta: "Enregistrer les notes",
    newFolderTitlePlaceholder: "Titre du nouveau dossier thématique...",
    defaultNewFolderTitlePrefix: "Dossier thématique #",
    newFolderCta: "+ Nouveau dossier",
    activeAccountPrefix: "Compte actif :",
    collaborativeSendCta: "Envoyer",
  },
  assistantNoEmbeddingModel: {
    bannerTitle: "Dialogue direct actif · Recherche documentaire inactive",
    bannerDescription:
      "Le dialogue direct et le glossaire sont actifs. La recherche documentaire nécessite un modèle d'indexation sémantique.",
    configureCta: "Configurer dans Modèles IA →",
  },
  assistantNoChatModel: {
    bannerTitle: "Modèle de dialogue IA requis",
    bannerDescription:
      "Aucun modèle de dialogue (chat) actif n'est configuré sur la plateforme. Configurez au moins un modèle chat pour utiliser Mon Assistant.",
    configureCta: "Configurer un modèle IA →",
  },
  assistantRagNotice: {
    noEmbeddingTitle: "Dialogue direct & glossaire actifs · Recherche documentaire inactive",
    noEmbeddingDescription:
      "Aucun modèle d'indexation sémantique n'est configuré. Vous pouvez échanger normalement avec Mon Assistant ; la recherche dans les documents nécessite un modèle d'embedding.",
    configureEmbeddingCta: "Configurer dans Administration › Modèles IA →",
    reindexingTitle: "Dialogue direct & glossaire actifs · Réindexation documentaire en cours",
    reindexingDescription:
      "Le corpus documentaire est en cours de réindexation sémantique. Le dialogue direct reste actif ; la recherche documentaire reprendra automatiquement à la fin.",
    reindexFailedTitle: "Dialogue direct actif · Réindexation documentaire interrompue",
    reindexFailedDescription:
      "La réindexation sémantique du corpus documentaire a échoué. Le dialogue direct avec Mon Assistant reste disponible.",
    relaunchReindexCta: "Relancer la réindexation",
    checkEmbeddingCta: "Vérifier le modèle d'embedding →",
  },
  assistantStreamErrors: {
    sessionExpiredMessage:
      "Votre session a expiré ou doit être renouvelée pour continuer la conversation.",
    reconnectCta: "Se reconnecter →",
    aiUnavailableMessage: (detail?: string) =>
      detail
        ? `⚠️ Impossible d'obtenir une réponse de Mon Assistant (${detail}). Vérifiez que le modèle IA configuré est bien démarré.`
        : "⚠️ Le service d'IA est temporairement indisponible. Vérifiez que le modèle IA configuré est bien démarré.",
  },
  assistantToolTrace: {
    heading: "Outils de l'espace sollicités",
    runningLabel: "En cours",
    executedLabel: "Terminé",
    deniedLabel: "Refusé",
    errorLabel: "Erreur",
    approvalRequiredLabel: "Validation requise",
    inspectLinesLabel: "Inspecter les lignes",
    durationSuffix: "ms",
  },
  assistantApprovalCard: {
    heading: "Validation humaine requise avant application",
    targetLabel: "Cible",
    workflowLabel: "Processus",
    humanAnchorLabel: "Votre justification de validation (requise)",
    humanAnchorPlaceholder: "Indiquez la raison de votre approbation...",
    humanAnchorRequiredError:
      "Veuillez saisir une brève justification avant d'approuver cette action.",
    approveCta: "Approuver et poursuivre",
    rejectCta: "Refuser",
    approvedStatusLabel: "Approuvé — poursuivi dans le processus",
    rejectedStatusLabel: "Refusé",
    openProcessCta: "Ouvrir le processus →",
  },
};
