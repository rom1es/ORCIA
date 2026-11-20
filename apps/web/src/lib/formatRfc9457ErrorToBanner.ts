import { OrciaProblemError, type ProblemDetails } from "@orcia/api-client";
import type { SupportedUiLocale } from "./formatters";

export interface FormattedRfc9457Banner {
  readonly title: string;
  readonly message: string;
  readonly remediation: string;
  readonly fullText: string;
  readonly status?: number;
  readonly errorCode?: string;
}

interface ErrorCopyPair {
  readonly fr: { readonly title: string; readonly message: string; readonly remediation: string };
  readonly en: { readonly title: string; readonly message: string; readonly remediation: string };
}

const RFC9457_ACTIONABLE_CATALOG: Record<string, ErrorCopyPair> = {
  ERR_OBSERVER_MODE_READ_ONLY: {
    fr: {
      title: "Action bloquée (mode lecture seule)",
      message: "Votre session est actuellement en mode observateur sur ce périmètre.",
      remediation: "Basculez vers un profil contributeur ou demandez les droits d'édition à un administrateur.",
    },
    en: {
      title: "Action blocked (read-only mode)",
      message: "Your session is currently in read-only observer mode for this scope.",
      remediation: "Switch to a contributor role or request write permissions from an administrator.",
    },
  },
  ERR_SCOPE_ACCESS_DENIED: {
    fr: {
      title: "Accès au périmètre refusé",
      message: "Vous ne disposez pas des droits nécessaires sur cet espace ou cette unité.",
      remediation: "Sélectionnez un espace autorisé ou demandez l'habilitation dans Mon Organisation.",
    },
    en: {
      title: "Scope access denied",
      message: "You do not have sufficient permissions for this space or unit.",
      remediation: "Select an authorized space or request access in My Organization.",
    },
  },
  ERR_READ_SOURCE_DENIED: {
    fr: {
      title: "Lecture de la source non autorisée",
      message: "L'accès au contenu détaillé de cette source est restreint.",
      remediation: "Demandez la permission de lecture des sources au responsable de l'espace.",
    },
    en: {
      title: "Source read access denied",
      message: "Access to this source's detailed content is restricted.",
      remediation: "Request source read access from the space owner.",
    },
  },
  ERR_PERMISSION_BROKER_DENIED: {
    fr: {
      title: "Accès externe intercepté",
      message: "Le connecteur cible exige une habilitation ou un jeton personnel valide.",
      remediation: "Renseignez votre jeton personnel dans Mon Compte ou suivez la procédure d'accès.",
    },
    en: {
      title: "External access intercepted",
      message: "The target connector requires valid authorization or a personal token.",
      remediation: "Configure your personal token in My Account or follow the access request procedure.",
    },
  },
  ERR_HUMAN_ANCHOR_REQUIRED: {
    fr: {
      title: "Validation humaine requise",
      message: "Cette section doit être rédigée et signée manuellement par un responsable humain.",
      remediation: "Saisissez au moins 30 caractères dans la carte d'ancrage violette et signez.",
    },
    en: {
      title: "Human validation required",
      message: "This section must be authored and signed manually by a human owner.",
      remediation: "Enter at least 30 characters in the violet anchor card and sign.",
    },
  },
  ERR_RUBBER_STAMPING_GUARD_TRIGGERED: {
    fr: {
      title: "Contrôle d'attention déclenché",
      message: "La validation a été jugée trop rapide par rapport au volume à relire.",
      remediation: "Confirmez explicitement les hypothèses retenues avant de finaliser la revue.",
    },
    en: {
      title: "Attention guard triggered",
      message: "The approval was submitted too quickly for the volume under review.",
      remediation: "Explicitly confirm the retained assumptions before finalizing the review.",
    },
  },
  ERR_RESOURCE_NOT_FOUND: {
    fr: {
      title: "Ressource introuvable",
      message: "L'élément demandé n'existe plus ou n'est pas encore rattaché à cet espace.",
      remediation: "Actualisez la page ou vérifiez la configuration de l'espace sélectionné.",
    },
    en: {
      title: "Resource not found",
      message: "The requested item no longer exists or is not yet attached to this space.",
      remediation: "Refresh the page or verify the selected space configuration.",
    },
  },
  ERR_VALIDATION_FAILED: {
    fr: {
      title: "Données saisies incomplètes ou invalides",
      message: "Un ou plusieurs champs ne respectent pas le format attendu.",
      remediation: "Vérifiez les champs en surbrillance et corrigez votre saisie avant de réessayer.",
    },
    en: {
      title: "Invalid or incomplete input",
      message: "One or more fields do not match the expected format.",
      remediation: "Review the highlighted fields and adjust your input before retrying.",
    },
  },
  ERR_ONTOLOGY_CONFLICT: {
    fr: {
      title: "Conflit avec un terme de référence",
      message: "Ce terme entre en conflit avec une règle ou définition verrouillée à un niveau supérieur.",
      remediation: "Choisissez un autre libellé ou demandez une dérogation au responsable du glossaire.",
    },
    en: {
      title: "Conflict with reference term",
      message: "This term conflicts with a locked rule or definition at a higher level.",
      remediation: "Choose a different term or request an exception from the glossary owner.",
    },
  },
  ERR_NO_ACTIVE_EMBEDDING_MODEL: {
    fr: {
      title: "Aucun modèle d'indexation sémantique actif",
      message: "L'assistant ne dispose pas encore d'un modèle actif pour rechercher dans vos sources.",
      remediation: "Configurez et activez un modèle d'indexation dans Configuration > Modèles IA.",
    },
    en: {
      title: "No active semantic indexing model",
      message: "The assistant does not yet have an active model to search your sources.",
      remediation: "Configure and activate an indexing model in Settings > AI Models.",
    },
  },
  ERR_UNSAFE_LLM_ENDPOINT_URL: {
    fr: {
      title: "Adresse du fournisseur IA bloquée",
      message: "L'adresse saisie pointe vers une ressource réseau interne protégée.",
      remediation: "Indiquez une adresse HTTPS valide ou un service IA interne autorisé.",
    },
    en: {
      title: "AI provider URL blocked",
      message: "The provided URL targets a protected internal network address.",
      remediation: "Provide a valid HTTPS endpoint or an authorized internal AI service.",
    },
  },
  ERR_TRIGGER_DUPLICATE_KEY: {
    fr: {
      title: "Identifiant de déclencheur déjà utilisé",
      message: "Un déclencheur portant cet identifiant existe déjà dans ce périmètre.",
      remediation: "Saisissez un autre identifiant unique ou laissez le champ vide pour en générer un automatiquement.",
    },
    en: {
      title: "Trigger identifier already in use",
      message: "A trigger with this identifier already exists.",
      remediation: "Enter a different unique identifier or leave the field blank to auto-generate one.",
    },
  },
};

function resolveStatusFallback(
  status: number | undefined,
  locale: SupportedUiLocale,
  resourceLabel?: string,
): { title: string; message: string; remediation: string } {
  const target = resourceLabel
    ? locale === "fr"
      ? ` (« ${resourceLabel} »)`
      : ` ("${resourceLabel}")`
    : "";

  switch (status) {
    case 401:
      return locale === "fr"
        ? {
            title: "Session expirée",
            message: `Votre session n'est plus valide pour accéder à cette ressource${target}.`,
            remediation: "Reconnectez-vous puis relancez l'opération.",
          }
        : {
            title: "Session expired",
            message: `Your session is no longer valid to access this resource${target}.`,
            remediation: "Sign in again and retry the operation.",
          };
    case 403:
      return locale === "fr"
        ? {
            title: "Autorisation insuffisante",
            message: `Vous n'avez pas les droits requis pour modifier cette ressource${target}.`,
            remediation: "Vérifiez votre périmètre actif ou demandez une habilitation à votre administrateur.",
          }
        : {
            title: "Insufficient permissions",
            message: `You lack the required permissions to modify this resource${target}.`,
            remediation: "Check your active scope or request access from your administrator.",
          };
    case 404:
      return locale === "fr"
        ? {
            title: "Ressource introuvable",
            message: `La ressource demandée${target} est introuvable ou a été supprimée.`,
            remediation: "Rechargez la vue ou sélectionnez un élément existant.",
          }
        : {
            title: "Resource not found",
            message: `The requested resource${target} could not be found or was deleted.`,
            remediation: "Reload the view or select an existing item.",
          };
    case 409:
      return locale === "fr"
        ? {
            title: "Conflit d'état",
            message: `Cette ressource${target} a déjà été prise en charge ou modifiée entre-temps.`,
            remediation: "Actualisez les données avant de renouveler votre action.",
          }
        : {
            title: "State conflict",
            message: `This resource${target} has already been claimed or modified.`,
            remediation: "Refresh the view before retrying your action.",
          };
    case 422:
      return locale === "fr"
        ? {
            title: "Validation métier refusée",
            message: `Les informations fournies pour${target || " cette opération"} ne respectent pas les règles attendues.`,
            remediation: "Corrigez les champs signalés puis validez à nouveau.",
          }
        : {
            title: "Business validation failed",
            message: `The provided input for${target || " this operation"} does not meet validation rules.`,
            remediation: "Fix the highlighted fields and submit again.",
          };
    case 503:
      return locale === "fr"
        ? {
            title: "Service temporairement indisponible",
            message: `Le service requis pour${target || " cette opération"} est momentanément indisponible.`,
            remediation: "Patientez quelques instants puis réessayez.",
          }
        : {
            title: "Service temporarily unavailable",
            message: `The service required for${target || " this operation"} is temporarily unavailable.`,
            remediation: "Wait a moment and retry.",
          };
    default:
      return locale === "fr"
        ? {
            title: "Échec de l'opération",
            message: `L'opération${target} n'a pas pu aboutir.`,
            remediation: "Vérifiez votre saisie ou réessayez dans quelques instants.",
          }
        : {
            title: "Operation failed",
            message: `The operation${target} could not be completed.`,
            remediation: "Verify your input or try again shortly.",
          };
  }
}

function sanitizeDetailText(raw: string | undefined): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  // Strip raw technical enum codes from detail text when showing to users
  return trimmed
    .replace(/\bREAD_ONLY_OBSERVER\b/g, "lecture seule")
    .replace(/\bhuman_authored_required\b/g, "validation humaine requise")
    .replace(/\bAUTONOMOUS_CONTRACT\b/g, "mode autonome")
    .replace(/\bHIGH_CRITICAL\b/g, "critique")
    .replace(/\bERR_[A-Z0-9_]+\b/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function formatRfc9457ErrorToBanner(
  error: unknown,
  locale: SupportedUiLocale = "fr",
  resourceLabel?: string,
): FormattedRfc9457Banner {
  let problem: Partial<ProblemDetails> | null = null;
  if (error instanceof OrciaProblemError) {
    problem = error.problem;
  } else if (
    typeof error === "object" &&
    error !== null &&
    ("error_code" in error || "status" in error || "detail" in error)
  ) {
    problem = error as Partial<ProblemDetails>;
  }

  if (problem) {
    const code = problem.error_code;
    const status = typeof problem.status === "number" ? problem.status : undefined;
    const catalogEntry = code ? RFC9457_ACTIONABLE_CATALOG[code] : undefined;
    if (catalogEntry) {
      const copy = locale === "en" ? catalogEntry.en : catalogEntry.fr;
      const resourceSuffix = resourceLabel
        ? locale === "fr"
          ? ` (Ressource : ${resourceLabel})`
          : ` (Resource: ${resourceLabel})`
        : "";
      const hint = sanitizeDetailText(problem.permission_broker_hint ?? undefined);
      const remediation = hint || copy.remediation;
      const message = `${copy.message}${resourceSuffix}`;
      return {
        title: copy.title,
        message,
        remediation,
        fullText: `${copy.title} — ${message} ${remediation}`,
        status,
        errorCode: code,
      };
    }

    const fallback = resolveStatusFallback(status, locale, resourceLabel);
    const sanitizedDetail = sanitizeDetailText(problem.detail);
    const message = sanitizedDetail && sanitizedDetail.length > 8 ? sanitizedDetail : fallback.message;
    const hint = sanitizeDetailText(problem.permission_broker_hint ?? undefined);
    const remediation = hint || fallback.remediation;
    return {
      title: fallback.title,
      message,
      remediation,
      fullText: `${fallback.title} — ${message} ${remediation}`,
      status,
      errorCode: code,
    };
  }

  const rawMsg =
    error instanceof Error
      ? sanitizeDetailText(error.message)
      : typeof error === "string"
        ? sanitizeDetailText(error)
        : null;
  const fallback = resolveStatusFallback(undefined, locale, resourceLabel);
  const message = rawMsg || fallback.message;
  return {
    title: fallback.title,
    message,
    remediation: fallback.remediation,
    fullText: `${fallback.title} — ${message} ${fallback.remediation}`,
  };
}
