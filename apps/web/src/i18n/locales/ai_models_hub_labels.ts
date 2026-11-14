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
  readonly fallbackModelLabel: string;
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
  coverageTitle: "Couverture des 4 tiers cognitifs",
  coverageAllConfigured: "Tous les tiers cognitifs sont opérationnels",
  coverageMissingTiers: "Tiers à compléter :",
  countLabel: "modèle configuré",
  countLabelPlural: "modèles configurés",
  colModel: "Modèle & Fournisseur",
  colTier: "Tier Cognitif",
  colEndpoint: "Endpoint API",
  colSecret: "Authentification", // pragma: allowlist secret
  colHealth: "Santé & Latence",
  colActions: "Actions",
  testConnectionBtn: "Tester",
  testingStatus: "Test en cours...",
  menuActions: "Menu d'actions",
  menuEdit: "Modifier la configuration",
  menuRotateKey: "Remplacer la clé d'API",
  menuToggleActive: "Activer / Désactiver",
  menuDelete: "Supprimer le modèle",
  modalCreateTitle: "Connecter un nouveau modèle IA",
  modalEditTitle: "Modifier la configuration du modèle",
  modalRotateTitle: "Remplacer la clé d'API secrète",
  modalDescription:
    "Les clés d'API sont chiffrées en AES-256-GCM et ne sont jamais renvoyées en clair vers l'interface.",
  providerLabel: "Fournisseur",
  geminiProtocolLabel: "Protocole Google Gemini",
  geminiModeB: "API Native Gemini (Mode B · /v1beta)",
  geminiModeA: "Passerelle Compatible OpenAI (Mode A · /v1beta/openai)",
  tierLabel: "Palier Cognitif",
  effortLabel: "Niveau d'effort",
  displayNameLabel: "Libellé affiché",
  displayNamePlaceholder: "Ex. Claude 3.7 Sonnet (Défaut)",
  primaryModelLabel: "Identifiant du modèle principal",
  fallbackModelLabel: "Modèle de secours (optionnel)",
  endpointUriLabel: "URL de l'endpoint API",
  authModeLabel: "Mode d'authentification",
  authModeApiKey: "Clé d'API (Jeton secret)",
  authModeEnvVar: "Variable d'environnement du serveur",
  authModeNoneLocal: "Sans clé (Serveur local / Réseau interne)",
  envVarNameLabel: "Nom de la variable serveur",
  envVarNamePlaceholder: "Ex. ANTHROPIC_API_KEY",
  saveAndTestBtn: "Enregistrer et tester la connexion",
  saveOnlyBtn: "Enregistrer uniquement",
  updateBtn: "Mettre à jour le modèle",
  cancelBtn: "Annuler",
  deleteDialogTitle: "Supprimer le modèle IA",
  deleteDialogDescription: "Cette action retirera le modèle de la liste des fournisseurs disponibles.",
  deleteDialogBlockedNotice:
    "Suppression bloquée : ce modèle est l'unique fournisseur actif pour ce tier et des workflows publiés en dépendent.",
  deleteDialogActiveRunsNotice:
    "Des exécutions en cours épinglent ce modèle. Vous pouvez le mettre en drainage pour terminer les runs actifs.",
  drainBtn: "Mettre en drainage",
  confirmDeleteBtn: "Supprimer définitivement",
  healthOperational: "Opérationnel",
  healthDegraded: "Dégradé",
  healthError: "Erreur",
  healthUntested: "Non testé",
  secretServerEnv: "Variable serveur", // pragma: allowlist secret
  secretLocalNoAuth: "Réseau local (sans clé)", // pragma: allowlist secret
};

export const AI_MODELS_HUB_EN: AiModelsHubDictionary = {
  title: "AI Models & Cognitive Providers",
  subtitle:
    "Supervise connectivity, encrypt API keys (AES-256) and manage the platform's 4 inference tiers.",
  connectModelBtn: "+ Connect a model",
  emptyTitle: "No AI models configured",
  emptyDescription:
    "Connect a provider (Anthropic, OpenAI, Mistral, Google Gemini, or local) to enable inference for assistants and workflows.",
  emptyCta: "Connect first model",
  coverageTitle: "4 cognitive tiers coverage",
  coverageAllConfigured: "All cognitive tiers are operational",
  coverageMissingTiers: "Missing tiers:",
  countLabel: "model configured",
  countLabelPlural: "models configured",
  colModel: "Model & Provider",
  colTier: "Cognitive Tier",
  colEndpoint: "API Endpoint",
  colSecret: "Authentication", // pragma: allowlist secret
  colHealth: "Health & Latency",
  colActions: "Actions",
  testConnectionBtn: "Test",
  testingStatus: "Testing...",
  menuActions: "Actions menu",
  menuEdit: "Edit configuration",
  menuRotateKey: "Replace API key",
  menuToggleActive: "Enable / Disable",
  menuDelete: "Delete model",
  modalCreateTitle: "Connect a new AI model",
  modalEditTitle: "Edit model configuration",
  modalRotateTitle: "Replace secret API key",
  modalDescription:
    "API keys are encrypted using AES-256-GCM and are never returned in plaintext to the user interface.",
  providerLabel: "Provider",
  geminiProtocolLabel: "Google Gemini Protocol",
  geminiModeB: "Gemini Native API (Mode B · /v1beta)",
  geminiModeA: "OpenAI Compatible Bridge (Mode A · /v1beta/openai)",
  tierLabel: "Cognitive Tier",
  effortLabel: "Effort level",
  displayNameLabel: "Display name",
  displayNamePlaceholder: "e.g. Claude 3.7 Sonnet (Default)",
  primaryModelLabel: "Primary model identifier",
  fallbackModelLabel: "Fallback model (optional)",
  endpointUriLabel: "API Endpoint URL",
  authModeLabel: "Authentication mode",
  authModeApiKey: "API Key (Secret token)", // pragma: allowlist secret
  authModeEnvVar: "Server environment variable",
  authModeNoneLocal: "No key (Local server / Internal network)",
  envVarNameLabel: "Server variable name",
  envVarNamePlaceholder: "e.g. ANTHROPIC_API_KEY",
  saveAndTestBtn: "Save and test connection",
  saveOnlyBtn: "Save only",
  updateBtn: "Update model",
  cancelBtn: "Cancel",
  deleteDialogTitle: "Delete AI model",
  deleteDialogDescription: "This will remove the model from the list of available providers.",
  deleteDialogBlockedNotice:
    "Deletion blocked: this model is the sole active provider for this tier and published workflows depend on it.",
  deleteDialogActiveRunsNotice:
    "Active workflow executions are pinned to this model. You can drain it to let active runs finish.",
  drainBtn: "Drain model",
  confirmDeleteBtn: "Delete permanently",
  healthOperational: "Operational",
  healthDegraded: "Degraded",
  healthError: "Error",
  healthUntested: "Untested",
  secretServerEnv: "Server variable", // pragma: allowlist secret
  secretLocalNoAuth: "Local network (no key)", // pragma: allowlist secret
};
