/**
 * BMad i18n labels for AI Models Hub (`/settings/ai-models`, `Story 17.5`).
 */

export interface AiModelsHubDictionary {
  readonly title: string;
  readonly subtitle: string;
  readonly connectModelBtn: string;
  readonly emptyTitle: string;
  readonly emptyDescription: string;
  readonly emptyCta: string;
  readonly coverageTitle: string;
  readonly coverageAllConfigured: string;
  readonly coverageMissingTiers: string;
  readonly countLabel: string;
  readonly countLabelPlural: string;
  readonly colModel: string;
  readonly colTier: string;
  readonly colEndpoint: string;
  readonly colSecret: string;
  readonly colHealth: string;
  readonly colActions: string;
  readonly testConnectionBtn: string;
  readonly testingStatus: string;
  readonly menuActions: string;
  readonly menuEdit: string;
  readonly menuRotateKey: string;
  readonly menuToggleActive: string;
  readonly menuDelete: string;
  readonly modalCreateTitle: string;
  readonly modalEditTitle: string;
  readonly modalRotateTitle: string;
  readonly modalDescription: string;
  readonly providerLabel: string;
  readonly geminiProtocolLabel: string;
  readonly geminiModeB: string;
  readonly geminiModeA: string;
  readonly tierLabel: string;
  readonly effortLabel: string;
  readonly displayNameLabel: string;
  readonly displayNamePlaceholder: string;
  readonly primaryModelLabel: string;
  readonly primaryModelPlaceholderGeneric: string;
  readonly primaryModelPlaceholderMistral: string;
  readonly primaryModelPlaceholderOllama: string;
  readonly fallbackModelLabel: string;
  readonly fallbackModelPlaceholder: string;
  readonly endpointUriLabel: string;
  readonly authModeLabel: string;
  readonly authModeApiKey: string;
  readonly authModeEnvVar: string;
  readonly authModeNoneLocal: string;
  readonly envVarNameLabel: string;
  readonly envVarNamePlaceholder: string;
  readonly saveAndTestBtn: string;
  readonly saveOnlyBtn: string;
  readonly updateBtn: string;
  readonly cancelBtn: string;
  readonly deleteDialogTitle: string;
  readonly deleteDialogDescription: string;
  readonly deleteDialogBlockedNotice: string;
  readonly deleteDialogActiveRunsNotice: string;
  readonly drainBtn: string;
  readonly confirmDeleteBtn: string;
  readonly healthOperational: string;
  readonly healthDegraded: string;
  readonly healthError: string;
  readonly healthUntested: string;
  readonly secretServerEnv: string;
  readonly secretLocalNoAuth: string;
  readonly usageLabel: string;
  readonly usageChat: string;
  readonly usageEmbedding: string;
  readonly activeEmbeddingBadge: string;
  readonly colUsage: string;
  readonly anthropicNoEmbeddingWarning: string;
  readonly modelDiscoveryNoMatch: string;
  readonly modelDiscoveryRefresh: string;
  readonly modelDiscoveryLoading: string;
  readonly modelDiscoveryFreeformHint: string;
  readonly chatBadge: string;
  readonly embeddingBadge: string;
  readonly deleteSummaryProvider: string;
  readonly deleteSummaryModel: string;
  readonly deleteSummaryTier: string;
  readonly deleteImpactLoading: string;
  readonly deleteImpactWorkflowsCount: string;
  readonly deleteImpactRemainingModels: string;
  readonly deleteImpactActiveRunsCount: string;
  readonly deleteFailedError: string;
  readonly menuEnable: string;
  readonly menuDisable: string;
  readonly drainingBadge: string;
  readonly providerPrimaryLabel: string;
  readonly providerSecondaryLabel: string;
  readonly highPrecisionSuffix: string;
  readonly backupPrefix: string;
  readonly secretApiKeySaved: string;
  readonly secretApiKey: string;
  readonly secretApiKeyCreatePlaceholder: string;
  readonly secretApiKeyEditPlaceholder: string;
  readonly closeErrorLabel: string;
  readonly testTimeoutError: string;
  readonly reindexPanel: {
    readonly title: string;
    readonly activeModelPrefix: string;
    readonly chunksUnit: string;
    readonly documentsUnit: string;
    readonly indexedChunksLabel: string;
    readonly noActiveModel: string;
    readonly relaunchBtn: string;
    readonly launchSuccess: string;
    readonly launchFailedPrefix: string;
    readonly statuses: {
      readonly IDLE: string;
      readonly PENDING: string;
      readonly IN_PROGRESS: string;
      readonly COMPLETED: string;
      readonly FAILED: string;
      readonly CANCELLED: string;
    };
  };
}

export const AI_MODELS_HUB_FR: AiModelsHubDictionary = {
  title: "Modèles IA & Fournisseurs Cognitifs",
  subtitle:
    "Supervisez la connectivité, chiffrez les clés d'API (AES-256) et configurez les 4 paliers d'inférence de la plateforme.",
  connectModelBtn: "+ Connecter un modèle",
  emptyTitle: "Aucun modèle IA configuré",
  emptyDescription:
    "Connectez un fournisseur (Anthropic, OpenAI, Mistral, Google Gemini ou local) pour activer l'inférence des assistants et workflows.",
  emptyCta: "Connecter un premier modèle",
  coverageTitle: "Couverture des 4 paliers cognitifs",
  coverageAllConfigured: "Tous les paliers cognitifs sont opérationnels",
  coverageMissingTiers: "Paliers à compléter :",
  countLabel: "modèle configuré",
  countLabelPlural: "modèles configurés",
  colModel: "Modèle & Fournisseur",
  colTier: "Palier Cognitif",
  colEndpoint: "Endpoint API",
  colSecret: "Authentification", // pragma: allowlist secret
  colHealth: "Santé & Latence",
  colActions: "Actions",
  testConnectionBtn: "Tester",
  testingStatus: "En cours",
  menuActions: "Menu d'actions",
  menuEdit: "Modifier la configuration",
  menuRotateKey: "Remplacer la clé d'API",
  menuToggleActive: "Activer / Désactiver",
  menuDelete: "Supprimer le modèle",
  modalCreateTitle: "Connecter un nouveau modèle IA",
  modalEditTitle: "Modifier la configuration du modèle",
  modalRotateTitle: "Remplacer la clé d'API secrète",
  modalDescription:
    "Les clés d'accès sont protégées par chiffrement fort côté serveur et ne sont jamais réaffichées en clair.",
  providerLabel: "Fournisseur",
  geminiProtocolLabel: "Protocole Google Gemini",
  geminiModeB: "Mode standard Google",
  geminiModeA: "Passerelle compatible standard",
  tierLabel: "Niveau de modèle",
  effortLabel: "Niveau d'effort",
  displayNameLabel: "Libellé affiché",
  displayNamePlaceholder: "Ex. Claude 3.7 Sonnet (Défaut)",
  primaryModelLabel: "Identifiant du modèle principal",
  primaryModelPlaceholderGeneric: "Identifiant exact publié par le fournisseur",
  primaryModelPlaceholderMistral: "ex. : mistral-large-latest",
  primaryModelPlaceholderOllama: "ex. : llama3.2",
  fallbackModelLabel: "Modèle de secours (optionnel)",
  fallbackModelPlaceholder: "Modèle de secours optionnel",
  endpointUriLabel: "Adresse du service fournisseur",
  authModeLabel: "Mode d'authentification",
  authModeApiKey: "Clé d'API (Jeton secret)",
  authModeEnvVar: "Variable d'environnement du serveur",
  authModeNoneLocal: "Sans clé (Serveur local / Réseau interne)",
  envVarNameLabel: "Nom de la variable serveur",
  envVarNamePlaceholder: "Ex. CLE_SERVEUR",
  saveAndTestBtn: "Enregistrer et tester la connexion",
  saveOnlyBtn: "Enregistrer uniquement",
  updateBtn: "Mettre à jour le modèle",
  cancelBtn: "Annuler",
  deleteDialogTitle: "Supprimer le modèle IA",
  deleteDialogDescription: "Cette action retirera le modèle de la liste des fournisseurs disponibles.",
  deleteDialogBlockedNotice:
    "Suppression bloquée : ce modèle est l'unique fournisseur actif pour ce niveau et des processus publiés en dépendent.",
  deleteDialogActiveRunsNotice:
    "Des exécutions en cours utilisent ce modèle. Vous pouvez le retirer progressivement pour laisser les tâches actives se terminer.",
  drainBtn: "Retirer progressivement",
  confirmDeleteBtn: "Supprimer définitivement",
  healthOperational: "Opérationnel",
  healthDegraded: "Dégradé",
  healthError: "Erreur",
  healthUntested: "Non testé",
  secretServerEnv: "Variable serveur", // pragma: allowlist secret
  secretLocalNoAuth: "Réseau local (sans clé)", // pragma: allowlist secret
  usageLabel: "Rôle / Usage du modèle",
  usageChat: "Dialogue & Rédaction assistée",
  usageEmbedding: "Indexation sémantique des documents",
  activeEmbeddingBadge: "Modèle d'indexation actif (global)",
  colUsage: "Rôle",
  anthropicNoEmbeddingWarning:
    "Anthropic ne propose pas de service d'indexation sémantique. Choisissez OpenAI, Mistral, Gemini ou Ollama.",
  modelDiscoveryNoMatch: "Aucun modèle trouvé auprès du fournisseur",
  modelDiscoveryRefresh: "Découvrir les modèles",
  modelDiscoveryLoading: "Découverte...",
  modelDiscoveryFreeformHint: "Vous pouvez saisir un identifiant librement",
  chatBadge: "Dialogue",
  embeddingBadge: "Indexation",
  deleteSummaryProvider: "Fournisseur",
  deleteSummaryModel: "Modèle",
  deleteSummaryTier: "Palier",
  deleteImpactLoading: "Analyse d'impact en cours",
  deleteImpactWorkflowsCount: "Processus impactés",
  deleteImpactRemainingModels: "Autres modèles actifs sur ce palier",
  deleteImpactActiveRunsCount: "Exécutions actives épinglant ce modèle",
  deleteFailedError: "La suppression du modèle a échoué.",
  menuEnable: "Activer",
  menuDisable: "Désactiver",
  drainingBadge: "Drainage",
  providerPrimaryLabel: "Fournisseur principal",
  providerSecondaryLabel: "Fournisseur secondaire",
  highPrecisionSuffix: "haute précision",
  backupPrefix: "secours",
  secretApiKeySaved: "Clé d'API enregistrée",
  secretApiKey: "Clé d'API",
  secretApiKeyCreatePlaceholder: "Saisir la clé d'API secrète...", // pragma: allowlist secret
  secretApiKeyEditPlaceholder: "Laisser vide pour conserver la clé enregistrée (••••••••)...", // pragma: allowlist secret
  closeErrorLabel: "Fermer l'erreur",
  testTimeoutError: "Délai d'attente dépassé (16 s) : le fournisseur IA n'a pas répondu à temps.",
  reindexPanel: {
    title: "Réindexation Sémantique & Corpus Vectoriel",
    activeModelPrefix: "Modèle actif :",
    chunksUnit: "extraits",
    documentsUnit: "document(s)",
    indexedChunksLabel: "extraits indexés",
    noActiveModel: "Aucun modèle de recherche sémantique actif",
    relaunchBtn: "Relancer la réindexation",
    launchSuccess: "Réindexation globale lancée avec succès.",
    launchFailedPrefix: "Échec du lancement :",
    statuses: {
      IDLE: "Prêt",
      PENDING: "En attente",
      IN_PROGRESS: "En cours",
      COMPLETED: "Terminée",
      FAILED: "Échec",
      CANCELLED: "Annulée",
    },
  },
};

export { AI_MODELS_HUB_EN } from "./ai_models_hub_labels_en";
