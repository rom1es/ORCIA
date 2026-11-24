import type { CategoryAControllersDictionary } from "./category_a_controller_labels";

export const CATEGORY_A_CONTROLLER_FR_LABELS: CategoryAControllersDictionary = {
  assistantThinking: {
    code: [
      {
        stepCode: "STEP_1_SPEC_EDGE_CASES",
        label: "Spécification et cas limites",
        durationMs: 1100,
        intermediateOutput:
          "Cadrage des entrées/sorties, complexité et cas particuliers pour la demande.",
      },
      {
        stepCode: "STEP_2_IMPLEMENTATION_DESIGN",
        label: "Conception de l'implémentation",
        durationMs: 1400,
        intermediateOutput: "Structuration du code et choix techniques adaptés.",
      },
      {
        stepCode: "STEP_3_VERIFICATION_EXAMPLE",
        label: "Vérification et exemple d'usage",
        durationMs: 900,
        intermediateOutput: "Contrôle de validité et préparation d'un cas de test.",
      },
    ],
    explain: [
      {
        stepCode: "STEP_1_KEY_POINTS_EXTRACTION",
        label: "Extraction des points clés",
        durationMs: 1100,
        intermediateOutput: "Repérage des idées principales et de la structure.",
      },
      {
        stepCode: "STEP_2_WORKSPACE_CONTEXT_CROSS",
        label: "Croisement avec le contexte de l'espace",
        durationMs: 1300,
        intermediateOutput: "Mise en regard avec le glossaire et les règles métiers.",
      },
      {
        stepCode: "STEP_3_PEDAGOGICAL_STRUCTURING",
        label: "Structuration pédagogique",
        durationMs: 900,
        intermediateOutput: "Organisation claire de l'explication.",
      },
    ],
    compare: [
      {
        stepCode: "STEP_1_EVALUATION_CRITERIA",
        label: "Critères d'évaluation",
        durationMs: 1000,
        intermediateOutput: "Définition des axes de comparaison pertinents.",
      },
      {
        stepCode: "STEP_2_OPTIONS_AND_RISKS",
        label: "Analyse des options et points de vigilance",
        durationMs: 1400,
        intermediateOutput: "Pesée des avantages et limites de chaque piste.",
      },
      {
        stepCode: "STEP_3_ARGUED_RECOMMENDATION",
        label: "Recommandation argumentée",
        durationMs: 900,
        intermediateOutput: "Synthèse décisionnelle structurée.",
      },
    ],
    fallback: [
      {
        stepCode: "STEP_1_REQUEST_FRAMING",
        label: "Cadrage de la demande",
        durationMs: 1000,
        intermediateOutput: "Identification des objectifs et du périmètre de la question.",
      },
      {
        stepCode: "STEP_2_DEEP_ANALYSIS_SOURCES",
        label: "Analyse approfondie et sources",
        durationMs: 1400,
        intermediateOutput: "Exploration détaillée des éléments de réponse et références.",
      },
      {
        stepCode: "STEP_3_RESPONSE_CONSOLIDATION",
        label: "Consolidation de la réponse",
        durationMs: 900,
        intermediateOutput: "Mise en forme structurée et synthétique.",
      },
    ],
  },
  cockpit: {
    defaultArbitrationJustification:
      "Décision humaine motivée enregistrée depuis le Cockpit.",
  },
  finopsResources: {
    dashboard: "Tableau de bord FinOps",
    budgetCeiling: "Plafond budgétaire",
    budgetOverride: "Dérogation budgétaire",
    recommendation: "Recommandation FinOps",
    remoteQuota: "Quota de service distant",
    circuitReset: "Réarmement du connecteur",
    autonomousReview: "Audit exécution autonome",
  },
  connectors: {
    registeredSuccess: "Connecteur d'entreprise enregistré au niveau du socle.",
    deletedSuccess: "Connecteur supprimé.",
  },
  packsRegistry: {
    healthEmpty:
      "Diagnostics de santé MCP actualisés : aucun connecteur requis configuré.",
    healthAllOk:
      "Diagnostics de santé MCP actualisés : {healthy}/{total} connecteurs requis opérationnels.",
    archiveExported: "Archive déclarative {archive} générée.",
    workspaceOptionPrefix: "Espace : {name}",
  },
  processes: {
    executionDefaultName: "Exécution",
    defaultReturnRemarks:
      "Préciser les hypothèses de gain métier sur le segment professionnel.",
    writePreviewPrompt:
      "Vérification avant publication externe : veuillez confirmer la création dans l'outil cible (Jira / Confluence).",
    stepApprovedAdvance: "Étape « {step} » validée. Passage à « {nextStep} ».",
    stepActivatedWord: "activée",
    stepSkippedWord: "ignorée",
    readyForFinalSignoff:
      "Toutes les étapes et les vérifications de qualité sont conformes. Vous pouvez valider et publier le livrable final.",
    deliverableApprovedBanner:
      "Dossier validé et signé : le livrable final est enregistré et publié.",
    deliverableDiffSavedBanner: "Modifications enregistrées sur le livrable.",
    returnLoopMarkdown:
      "## Reprise sur corrections (Cycle {cycle} → Étape {step})\nCommentaires pris en compte : {remarks}",
    returnLoopBanner:
      "Dossier renvoyé vers l'Étape {step} avec vos commentaires de correction (Cycle {cycle}).",
    processResource: "Processus",
    processSaveResource: "Enregistrement du processus",
    delegatedAgentsUpdated: "Liste des agents spécialisés mobilisables mise à jour.",
    subStepDraftUpdated: "Étape « {step} » {state} dans votre copie de travail.",
    executionModeSwitched: "Mode de réalisation basculé sur « {mode} ».",
    externalIdeLabel: "Réalisation dans l'IDE / Git de l'équipe",
    nativeOrciaLabel: "Exécution guidée dans ORCIA",
    draftSavedBanner: "Brouillon enregistré ({version}).",
    publishedBanner: "Processus publié et activé (version {version}).",
    whatIfDoneBanner:
      "Simulation à blanc terminée : {count} étape(s) vérifiée(s), aucune modification envoyée aux outils externes.",
    packCreatedBanner:
      "✅ Pack Métier « {slug} » créé et enregistré avec l'intention métier fournie.",
    assetPromotedBanner:
      "✅ Composant promu avec succès vers le Pack Métier « {pack} ».",
    helpArticleAttachedBanner:
      "✅ Fiche d'aide « {article} » générée, vérifiée et rattachée à l'écran.",
  },
  workspaceSources: {
    updated: "Source modifiée.",
    attached: "Source rattachée.",
    syncTriggered: "✅ Synchronisation déclenchée ({status}).",
    deleted: "✅ Source détachée.",
    gitNexusEnabled: "✅ GitNexus activé.",
    gitNexusDisabled: "GitNexus désactivé.",
    referentRenewed: "Référent renouvelé.",
    reconciled:
      "✅ Fraîcheur réconciliée ({evaluated} évaluées, {stale} désynchronisées).",
    coldStartBanner:
      "Attribution nominative : vos droits Jira / GitLab s'appliquent.",
    myAccountCta: "👤 Mon Compte › Mes Connexions",
    sourcesTitle: "Sources de « {name} »",
    newReferentPlaceholder: "Nouveau référent (e-mail)...",
    confirmRenewalCta: "Valider le renouvellement",
    cancelCta: "Annuler",
  },
  wizards: {
    profileSelectorAriaLabel: "Choisir un Parcours de Configuration Guidé",
  },
};
