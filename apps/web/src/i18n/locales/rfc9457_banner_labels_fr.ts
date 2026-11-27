import type { Rfc9457BannerDictionary } from "./rfc9457_banner_labels";

export const RFC9457_BANNER_FR_LABELS: Rfc9457BannerDictionary = {
  catalog: {
    ERR_OBSERVER_MODE_READ_ONLY: {
      title: "Action bloquée (mode lecture seule)",
      message: "Votre session est actuellement en mode observateur sur ce périmètre.",
      remediation:
        "Basculez vers un profil contributeur ou demandez les droits d'édition à un administrateur.",
    },
    ERR_SCOPE_ACCESS_DENIED: {
      title: "Accès au périmètre refusé",
      message: "Vous ne disposez pas des droits nécessaires sur cet espace ou cette unité.",
      remediation:
        "Sélectionnez un périmètre d'équipe ou d'espace autorisé, ou contactez un administrateur de division ou de plateforme.",
    },
    ERR_READ_SOURCE_DENIED: {
      title: "Lecture de la source non autorisée",
      message: "L'accès au contenu détaillé de cette source est restreint.",
      remediation:
        "Demandez la permission de lecture des sources au responsable de l'espace.",
    },
    ERR_PERMISSION_BROKER_DENIED: {
      title: "Accès externe intercepté",
      message: "Le connecteur cible exige une habilitation ou un jeton personnel valide.",
      remediation:
        "Renseignez votre jeton personnel dans Mon Compte ou suivez la procédure d'accès.",
    },
    ERR_HUMAN_ANCHOR_REQUIRED: {
      title: "Validation humaine requise",
      message: "Cette section doit être rédigée et signée manuellement par un responsable humain.",
      remediation:
        "Saisissez au moins 30 caractères dans la carte d'ancrage violette et signez.",
    },
    ERR_RUBBER_STAMPING_GUARD_TRIGGERED: {
      title: "Contrôle d'attention déclenché",
      message: "La validation a été jugée trop rapide par rapport au volume à relire.",
      remediation:
        "Confirmez explicitement les hypothèses retenues avant de finaliser la revue.",
    },
    ERR_RESOURCE_NOT_FOUND: {
      title: "Ressource introuvable",
      message: "L'élément demandé n'existe plus ou n'est pas encore rattaché à cet espace.",
      remediation:
        "Actualisez la page ou vérifiez la configuration de l'espace sélectionné.",
    },
    ERR_VALIDATION_FAILED: {
      title: "Données saisies incomplètes ou invalides",
      message: "Un ou plusieurs champs ne respectent pas le format attendu.",
      remediation:
        "Vérifiez les champs en surbrillance et corrigez votre saisie avant de réessayer.",
    },
    ERR_ONTOLOGY_CONFLICT: {
      title: "Conflit avec un terme de référence",
      message:
        "Ce terme entre en conflit avec une règle ou définition verrouillée à un niveau supérieur.",
      remediation:
        "Choisissez un autre libellé ou demandez une dérogation au responsable du glossaire.",
    },
    ERR_NO_ACTIVE_EMBEDDING_MODEL: {
      title: "Aucun modèle d'indexation sémantique actif",
      message:
        "L'ajout ou l'indexation de sources documentaires nécessite un modèle d'embedding actif.",
      remediation:
        "Configurez et activez un modèle d'embedding dans Administration > Modèles IA.",
    },
    ERR_TIER_MODEL_NOT_CONFIGURED: {
      title: "Aucun modèle de dialogue IA configuré",
      message:
        "Aucun modèle de dialogue actif n'est configuré pour répondre dans Mon Assistant.",
      remediation:
        "Configurez et activez un modèle IA de dialogue dans Administration > Modèles IA.",
    },
    ERR_UNSAFE_LLM_ENDPOINT_URL: {
      title: "Adresse du fournisseur IA bloquée",
      message: "L'adresse saisie pointe vers une ressource réseau interne protégée.",
      remediation:
        "Indiquez une adresse HTTPS valide ou un service IA interne autorisé.",
    },
    ERR_TRIGGER_DUPLICATE_KEY: {
      title: "Identifiant de déclencheur déjà utilisé",
      message: "Un déclencheur portant cet identifiant existe déjà dans ce périmètre.",
      remediation:
        "Saisissez un autre identifiant unique ou laissez le champ vide pour en générer un automatiquement.",
    },
    ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED: {
      title: "Visibilité d'espace personnel verrouillée",
      message:
        "Un espace personnel privé ne peut pas être converti en espace d'équipe sur place.",
      remediation: "Créez un nouvel espace collectif si vous souhaitez partager avec l'équipe.",
    },
    ERR_PACK_SLOT_UNBOUND: {
      title: "Connecteur obligatoire non raccordé",
      message: "Un ou plusieurs connecteurs requis par ce pack doivent être associés avant activation ou exécution.",
      remediation: "Ouvrez le panneau des connecteurs du pack et sélectionnez les sources attendues.",
    },
    ERR_PACK_CLOSURE_INCOMPLETE: {
      title: "Dépendances du pack incomplètes",
      message: "Certains éléments sélectionnés référencent des ressources manquantes ou en brouillon.",
      remediation: "Ajoutez les éléments manquants ou activez l'inclusion automatique avant publication.",
    },
    ERR_PACK_PII_OR_INFRA_LEAK: {
      title: "Export bloqué pour protection des données",
      message: "Des données nominatives, clés secrètes ou adresses internes ont été détectées dans le contenu.",
      remediation: "Retirez ces références sensibles des instructions avant d'exporter l'archive.",
    },
    ERR_ENTITY_REFERENCED_BY_PACK_DRAFT: {
      title: "Élément référencé par un pack en brouillon",
      message: "Cet élément est actuellement inclus dans un ou plusieurs packs personnalisés en cours de préparation.",
      remediation: "Confirmez le détachement des brouillons concernés pour finaliser la suppression.",
    },
    ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN: {
      title: "Archive refusée (script exécutable interdit)",
      message: "Le pack contient des fichiers exécutables ou scripts non autorisés.",
      remediation: "Supprimez tout script exécutable et conservez uniquement des fichiers déclaratifs.",
    },
    ERR_PACK_INVALID_ARCHIVE: {
      title: "Archive de pack invalide",
      message: "Le fichier fourni n'est pas une archive de pack valide ou son manifeste est incomplet.",
      remediation: "Vérifiez la structure de votre archive et réessayez l'importation.",
    },
    ERR_PACK_VERSION_CONFLICT: {
      title: "Conflit de version de pack",
      message: "Une version différente de ce pack existe déjà pour ce périmètre.",
      remediation: "Incrémentez le numéro de version ou remplacez le brouillon existant.",
    },
    ERR_PACK_SYSTEM_DELETE_FORBIDDEN: {
      title: "Suppression de pack système refusée",
      message: "Les packs système fournis par la plateforme ne peuvent pas être désinstallés.",
      remediation: "Désactivez simplement le pack sur les espaces qui n'en ont pas besoin.",
    },
    ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS: {
      title: "Ressource verrouillée par une exécution active",
      message: "Ce pack ou connecteur est utilisé par des exécutions en cours.",
      remediation: "Attendez la fin des exécutions actives avant de supprimer la ressource.",
    },
  },
  statusFallbacks: {
    401: {
      title: "Session expirée",
      message: "Votre session n'est plus valide pour accéder à cette ressource{target}.",
      remediation: "Reconnectez-vous puis relancez l'opération.",
    },
    403: {
      title: "Autorisation insuffisante",
      message: "Vous n'avez pas les droits requis pour modifier cette ressource{target}.",
      remediation:
        "Vérifiez votre périmètre actif ou demandez une habilitation à votre administrateur.",
    },
    404: {
      title: "Ressource introuvable",
      message: "La ressource demandée{target} est introuvable ou a été supprimée.",
      remediation: "Rechargez la vue ou sélectionnez un élément existant.",
    },
    409: {
      title: "Conflit d'état",
      message: "Cette ressource{target} a déjà été prise en charge ou modifiée entre-temps.",
      remediation: "Actualisez les données avant de renouveler votre action.",
    },
    422: {
      title: "Validation métier refusée",
      message: "Les informations fournies{target} ne respectent pas les règles attendues.",
      remediation: "Corrigez les champs signalés puis validez à nouveau.",
    },
    503: {
      title: "Service temporairement indisponible",
      message: "Le service requis{target} est momentanément indisponible.",
      remediation: "Patientez quelques instants puis réessayez.",
    },
    default: {
      title: "Échec de l'opération",
      message: "L'opération{target} n'a pas pu aboutir.",
      remediation: "Vérifiez votre saisie ou réessayez dans quelques instants.",
    },
  },
  quotedTargetPattern: " (« {resource} »)",
  prepositionTargetPattern: " pour « {resource} »",
  fallbackOperationTarget: " pour cette opération",
  resourceSuffixPattern: " (Ressource : {resource})",
  sanitizeReplacements: {
    readOnlyObserver: "lecture seule",
    humanAuthoredRequired: "validation humaine requise",
    autonomousContract: "mode autonome",
    highCritical: "critique",
  },
};
