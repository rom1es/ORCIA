import type { ClientErrorLabels } from "../../lib/clientErrorCodes";

export const CLIENT_ERRORS_FR_LABELS: ClientErrorLabels = {
  ERR_CLIENT_TIMEOUT:
    "Le délai d'attente de {seconds} s est dépassé. Vérifiez votre connexion ou réessayez.",
  ERR_CLIENT_NETWORK:
    "Impossible de joindre le serveur. Vérifiez votre connexion réseau puis réessayez.",
  ERR_CLIENT_ABORTED: "L'opération a été interrompue avant son terme.",
  ERR_CLIENT_SSE_DISCONNECTED:
    "La connexion en temps réel a été interrompue. Veuillez relancer l'opération si besoin.",
  ERR_CLIENT_INVALID_PAYLOAD:
    "Les données reçues du serveur sont invalides ou incomplètes ({detail}).",
  ERR_CLIENT_UNKNOWN:
    "Une erreur inattendue est survenue. Veuillez réessayer dans quelques instants.",
};

export const CLIENT_ERRORS_EN_LABELS: ClientErrorLabels = {
  ERR_CLIENT_TIMEOUT:
    "The {seconds}s timeout expired. Check your connection or try again.",
  ERR_CLIENT_NETWORK:
    "Unable to reach the server. Check your network connection and try again.",
  ERR_CLIENT_ABORTED: "The operation was cancelled before completion.",
  ERR_CLIENT_SSE_DISCONNECTED:
    "The real-time connection was interrupted. Please retry the operation if needed.",
  ERR_CLIENT_INVALID_PAYLOAD:
    "The data received from the server is invalid or incomplete ({detail}).",
  ERR_CLIENT_UNKNOWN:
    "An unexpected error occurred. Please try again in a few moments.",
};
