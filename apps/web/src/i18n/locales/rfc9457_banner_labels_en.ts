import type { Rfc9457BannerDictionary } from "./rfc9457_banner_labels";

export const RFC9457_BANNER_EN_LABELS: Rfc9457BannerDictionary = {
  catalog: {
    ERR_OBSERVER_MODE_READ_ONLY: {
      title: "Action blocked (read-only mode)",
      message: "Your session is currently in read-only observer mode for this scope.",
      remediation:
        "Switch to a contributor role or request write permissions from an administrator.",
    },
    ERR_SCOPE_ACCESS_DENIED: {
      title: "Scope access denied",
      message: "You do not have sufficient permissions for this space or unit.",
      remediation:
        "Select an authorized space or request access in My Organization.",
    },
    ERR_READ_SOURCE_DENIED: {
      title: "Source read access denied",
      message: "Access to this source's detailed content is restricted.",
      remediation: "Request source read access from the space owner.",
    },
    ERR_PERMISSION_BROKER_DENIED: {
      title: "External access intercepted",
      message: "The target connector requires valid authorization or a personal token.",
      remediation:
        "Configure your personal token in My Account or follow the access request procedure.",
    },
    ERR_HUMAN_ANCHOR_REQUIRED: {
      title: "Human validation required",
      message: "This section must be authored and signed manually by a human owner.",
      remediation: "Enter at least 30 characters in the violet anchor card and sign.",
    },
    ERR_RUBBER_STAMPING_GUARD_TRIGGERED: {
      title: "Attention guard triggered",
      message: "The approval was submitted too quickly for the volume under review.",
      remediation:
        "Explicitly confirm the retained assumptions before finalizing the review.",
    },
    ERR_RESOURCE_NOT_FOUND: {
      title: "Resource not found",
      message: "The requested item no longer exists or is not yet attached to this space.",
      remediation: "Refresh the page or verify the selected space configuration.",
    },
    ERR_VALIDATION_FAILED: {
      title: "Invalid or incomplete input",
      message: "One or more fields do not match the expected format.",
      remediation: "Review the highlighted fields and adjust your input before retrying.",
    },
    ERR_ONTOLOGY_CONFLICT: {
      title: "Conflict with reference term",
      message: "This term conflicts with a locked rule or definition at a higher level.",
      remediation:
        "Choose a different term or request an exception from the glossary owner.",
    },
    ERR_NO_ACTIVE_EMBEDDING_MODEL: {
      title: "No active semantic indexing model",
      message:
        "Adding or indexing document sources requires an active embedding model.",
      remediation:
        "Configure and activate an embedding model in Administration > AI Models.",
    },
    ERR_TIER_MODEL_NOT_CONFIGURED: {
      title: "No chat AI model configured",
      message: "No active chat model is configured to answer in My Assistant.",
      remediation:
        "Configure and activate a chat AI model in Administration > AI Models.",
    },
    ERR_UNSAFE_LLM_ENDPOINT_URL: {
      title: "AI provider URL blocked",
      message: "The provided URL targets a protected internal network address.",
      remediation: "Provide a valid HTTPS endpoint or an authorized internal AI service.",
    },
    ERR_TRIGGER_DUPLICATE_KEY: {
      title: "Trigger identifier already in use",
      message: "A trigger with this identifier already exists.",
      remediation:
        "Enter a different unique identifier or leave the field blank to auto-generate one.",
    },
  },
  statusFallbacks: {
    401: {
      title: "Session expired",
      message: "Your session is no longer valid to access this resource{target}.",
      remediation: "Sign in again and retry the operation.",
    },
    403: {
      title: "Insufficient permissions",
      message: "You lack the required permissions to modify this resource{target}.",
      remediation: "Check your active scope or request access from your administrator.",
    },
    404: {
      title: "Resource not found",
      message: "The requested resource{target} could not be found or was deleted.",
      remediation: "Reload the view or select an existing item.",
    },
    409: {
      title: "State conflict",
      message: "This resource{target} has already been claimed or modified.",
      remediation: "Refresh the view before retrying your action.",
    },
    422: {
      title: "Business validation failed",
      message: "The provided input{target} does not meet validation rules.",
      remediation: "Fix the highlighted fields and submit again.",
    },
    503: {
      title: "Service temporarily unavailable",
      message: "The service required{target} is temporarily unavailable.",
      remediation: "Wait a moment and retry.",
    },
    default: {
      title: "Operation failed",
      message: "The operation{target} could not be completed.",
      remediation: "Verify your input or try again shortly.",
    },
  },
  quotedTargetPattern: ' ("{resource}")',
  prepositionTargetPattern: ' for "{resource}"',
  fallbackOperationTarget: " for this operation",
  resourceSuffixPattern: " (Resource: {resource})",
  sanitizeReplacements: {
    readOnlyObserver: "read-only mode",
    humanAuthoredRequired: "human validation required",
    autonomousContract: "autonomous mode",
    highCritical: "critical",
  },
};
