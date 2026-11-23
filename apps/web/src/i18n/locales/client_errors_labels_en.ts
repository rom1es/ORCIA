import type { ClientErrorLabels } from "../../lib/clientErrorCodes";

export const CLIENT_ERRORS_EN_LABELS: ClientErrorLabels = {
  ERR_CLIENT_TIMEOUT:
    "The {seconds}s timeout expired. Check your connection or try again.",
  ERR_CLIENT_NETWORK:
    "Unable to reach the server. Check your network connection and try again.",
  ERR_CLIENT_ABORTED: "The operation was cancelled before completion.",
  ERR_CLIENT_SSE_DISCONNECTED:
    "The real-time connection was interrupted. Please retry the operation if needed.",
  ERR_CLIENT_SSE_EMPTY_BODY:
    "The real-time response stream is empty for this operation ({detail}).",
  ERR_CLIENT_HTTP_FALLBACK:
    "The server returned an unexpected response ({detail}). Please try again.",
  ERR_CLIENT_INVALID_PAYLOAD:
    "The data received from the server is invalid or incomplete ({detail}).",
  ERR_CLIENT_NOT_CONFIGURED:
    "This action is not configured in the active environment ({detail}).",
  ERR_CLIENT_AUTH_HYDRATION_TIMEOUT:
    "Session verification timed out after {seconds}s.",
  ERR_CLIENT_SESSION_EXPIRED:
    "Your session has expired or needs to be renewed to continue the conversation.",
  ERR_CLIENT_AI_UNAVAILABLE:
    "⚠️ Could not get a response from My Assistant ({detail}). Please check that your configured AI model is running.",
  ERR_CLIENT_AI_HUB_COMMUNICATION:
    "An error occurred while communicating with the AI models hub.",
  ERR_CLIENT_AI_MODEL_ID_REQUIRED:
    "❌ Test failed: please enter the primary model identifier (e.g. llama3.2, mistral-large-latest).",
  ERR_CLIENT_AI_ENDPOINT_URL_INVALID:
    "❌ Test failed: please enter a valid API URL starting with https:// or http://.",
  ERR_CLIENT_AI_API_KEY_REQUIRED:
    "❌ Test failed: please enter your API key or select local server or environment variable mode.",
  ERR_CLIENT_AI_PROVIDER_UNREACHABLE:
    "❌ Test failed: unable to contact the AI provider.",
  ERR_CLIENT_IAM_NETWORK:
    "A network error occurred while updating accounts and permissions.",
  ERR_CLIENT_ORG_UNITS_NETWORK:
    "A network error occurred while updating the organization hierarchy.",
  ERR_CLIENT_AUDIT_NETWORK:
    "A network error occurred while communicating with the audit ledger.",
  ERR_CLIENT_CONNECTORS_LOAD: "Failed to load connectors.",
  ERR_CLIENT_CONNECTOR_SAVE: "Error registering connector.",
  ERR_CLIENT_CONNECTOR_DELETE: "Error deleting connector.",
  ERR_CLIENT_FEDERATED_SEARCH:
    "Deep search failed across the platform ({detail}).",
  ERR_CLIENT_PLATFORM_HYDRATION:
    "Failed to hydrate initial platform state.",
  ERR_CLIENT_CONTEXT_MISSING:
    "Required application context is not initialized ({detail}).",
  ERR_CLIENT_PERMISSION_LOAD:
    "⚠️ Failed to load access requests ({detail}).",
  ERR_CLIENT_PERMISSION_ACTION:
    "⚠️ Access request action failed ({detail}).",
  ERR_CLIENT_PACKS_LOAD:
    "Unable to load the declarative packs registry.",
  ERR_CLIENT_PACKS_HEALTH_REFRESH:
    "Unable to refresh connector healthchecks.",
  ERR_CLIENT_PACKS_EXPORT_ZIP:
    "Failed to export declarative pack archive.",
  ERR_CLIENT_PACKS_WORKSPACE_REQUIRED:
    "Create a workspace in 'My Spaces' before exporting its pack.",
  ERR_CLIENT_PACKS_HEALTH_DEGRADED:
    "Connector healthchecks: {detail} connector(s) operational.",
  ERR_CLIENT_PROCESS_RUN_START:
    "Failed to start run ({detail}).",
  ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE:
    "Deliverable approval failed ({detail}).",
  ERR_CLIENT_PROCESS_SIMULATION_UNAVAILABLE:
    "Remote simulation unavailable ({detail}). Showing local estimate.",
  ERR_CLIENT_HELP_ARTICLE_ATTACHED_LOCAL:
    "⚠️ Help article attached locally ({detail}).",
  ERR_CLIENT_WIZARD_LOAD:
    "Unable to load your guided setup sessions.",
  ERR_CLIENT_WIZARD_START:
    "Unable to start this guided setup session.",
  ERR_CLIENT_WIZARD_STEP_SAVE:
    "Failed to save guided setup step.",
  ERR_CLIENT_WIZARD_STEP_BACK:
    "Unable to step back to the previous step.",
  ERR_CLIENT_WIZARD_DEMO_PROVISION:
    "Unable to provision demo workspace.",
  ERR_CLIENT_WORKSPACE_SOURCE_ACTION:
    "⚠️ Document source operation failed ({detail}).",
  ERR_CLIENT_UNKNOWN:
    "An unexpected error occurred. Please try again in a few moments.",
};
