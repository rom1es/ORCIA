import type { ClientErrorLabels } from "../../lib/clientErrorCodes";

export const CLIENT_ERRORS_FR_LABELS: ClientErrorLabels = {
  ERR_CLIENT_TIMEOUT:
    "Le délai d'attente de {seconds} s est dépassé. Vérifiez votre connexion ou réessayez.",
  ERR_CLIENT_NETWORK:
    "Impossible de joindre le serveur. Vérifiez votre connexion réseau puis réessayez.",
  ERR_CLIENT_ABORTED: "L'opération a été interrompue avant son terme.",
  ERR_CLIENT_SSE_DISCONNECTED:
    "La connexion en temps réel a été interrompue. Veuillez relancer l'opération si besoin.",
  ERR_CLIENT_SSE_EMPTY_BODY:
    "Le flux de réponse en temps réel est vide pour cette opération ({detail}).",
  ERR_CLIENT_HTTP_FALLBACK:
    "Le serveur a renvoyé une réponse inattendue ({detail}). Veuillez réessayer.",
  ERR_CLIENT_INVALID_PAYLOAD:
    "Les données reçues du serveur sont invalides ou incomplètes ({detail}).",
  ERR_CLIENT_NOT_CONFIGURED:
    "Cette action n'est pas configurée dans l'environnement actif ({detail}).",
  ERR_CLIENT_AUTH_HYDRATION_TIMEOUT:
    "La vérification de votre session a dépassé le délai de {seconds} s.",
  ERR_CLIENT_SESSION_EXPIRED:
    "Votre session a expiré ou doit être renouvelée pour continuer la conversation.",
  ERR_CLIENT_AI_UNAVAILABLE:
    "Impossible d'obtenir une réponse de Mon Assistant ({detail}). Vérifiez que le modèle IA configuré est bien démarré.",
  ERR_CLIENT_AI_HUB_COMMUNICATION:
    "Une erreur est survenue lors de la communication avec le hub de modèles IA.",
  ERR_CLIENT_AI_MODEL_ID_REQUIRED:
    "Échec du test : veuillez renseigner l'identifiant du modèle principal (ex. : llama3.2, mistral-large-latest).",
  ERR_CLIENT_AI_ENDPOINT_URL_INVALID:
    "Échec du test : veuillez indiquer une URL d'API valide commençant par https:// ou http://.",
  ERR_CLIENT_AI_API_KEY_REQUIRED:
    "Échec du test : veuillez saisir votre clé d'API ou choisir le mode local ou variable d'environnement.",
  ERR_CLIENT_AI_PROVIDER_UNREACHABLE:
    "Échec du test : impossible de joindre le fournisseur IA.",
  ERR_CLIENT_IAM_NETWORK:
    "Une erreur réseau est survenue lors de la mise à jour des comptes et habilitations.",
  ERR_CLIENT_ORG_UNITS_NETWORK:
    "Une erreur réseau est survenue lors de la mise à jour de l'organigramme.",
  ERR_CLIENT_AUDIT_NETWORK:
    "Une erreur réseau est survenue lors de la communication avec le registre d'audit.",
  ERR_CLIENT_CONNECTORS_LOAD: "Impossible de charger les connecteurs.",
  ERR_CLIENT_CONNECTOR_SAVE: "Erreur lors de l'enregistrement du connecteur.",
  ERR_CLIENT_CONNECTOR_DELETE: "Erreur lors de la suppression du connecteur.",
  ERR_CLIENT_FEDERATED_SEARCH:
    "Erreur lors de la recherche approfondie dans la plateforme ({detail}).",
  ERR_CLIENT_PLATFORM_HYDRATION:
    "Échec du chargement initial de l'état de la plateforme.",
  ERR_CLIENT_CONTEXT_MISSING:
    "Le contexte applicatif requis n'est pas initialisé ({detail}).",
  ERR_CLIENT_PERMISSION_LOAD:
    "Impossible de charger les demandes d'accès ({detail}).",
  ERR_CLIENT_PERMISSION_ACTION:
    "Échec de l'action sur la demande d'accès ({detail}).",
  ERR_CLIENT_PACKS_LOAD:
    "Impossible de charger le registre des packs déclaratifs.",
  ERR_CLIENT_PACKS_HEALTH_REFRESH:
    "Impossible d'actualiser les diagnostics de santé des connecteurs.",
  ERR_CLIENT_PACKS_EXPORT_ZIP:
    "Échec de l'export de l'archive du pack déclaratif.",
  ERR_CLIENT_PACKS_WORKSPACE_REQUIRED:
    "Créez d'abord un espace de travail dans « Mes Espaces » avant d'exporter son pack.",
  ERR_CLIENT_PACKS_HEALTH_DEGRADED:
    "Diagnostics de santé des connecteurs : {detail} connecteur(s) opérationnel(s).",
  ERR_CLIENT_PROCESS_RUN_START:
    "Échec du démarrage de l'exécution ({detail}).",
  ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE:
    "Échec de la validation du livrable ({detail}).",
  ERR_CLIENT_PROCESS_SIMULATION_UNAVAILABLE:
    "Simulation distante indisponible ({detail}). Estimation locale affichée.",
  ERR_CLIENT_HELP_ARTICLE_ATTACHED_LOCAL:
    "Fiche d'aide rattachée localement ({detail}).",
  ERR_CLIENT_WIZARD_LOAD:
    "Impossible de charger vos parcours d'initialisation.",
  ERR_CLIENT_WIZARD_START:
    "Impossible d'ouvrir ce parcours d'initialisation.",
  ERR_CLIENT_WIZARD_STEP_SAVE:
    "Erreur lors de l'enregistrement de l'étape.",
  ERR_CLIENT_WIZARD_STEP_BACK:
    "Impossible de revenir à l'étape précédente.",
  ERR_CLIENT_WIZARD_DEMO_PROVISION:
    "Impossible de provisionner l'espace de démonstration.",
  ERR_CLIENT_WORKSPACE_SOURCE_ACTION:
    "L'opération sur la source documentaire a échoué ({detail}).",
  ERR_CLIENT_UNKNOWN:
    "Une erreur inattendue est survenue. Veuillez réessayer dans quelques instants.",
};
