import type { TranslationDictionary } from "../types";

export const frDictionary: TranslationDictionary = {
  locale: "fr",
  shell: {
    brandTitle: "ORCIA",
    brandSubtitle: "",
    sidebarNavigationAriaLabel: "Navigation Globale à 7 Modules",
    sidebarToggleExpandLabel: "Déplier le menu latéral",
    sidebarToggleCollapseLabel: "Replier le menu latéral",
    scopeSwitcherButtonLabel: "Sélecteur de périmètre (⌘W)",
    scopeSwitcherDialogTitle: "Sélecteur de Périmètre Hiérarchique (⌘W)",
    scopeSwitcherCloseLabel: "Fermer",
    scopeLevels: {
      GLOBAL: "Plateforme Globale",
      BU: "BU / Tribu",
      TEAM: "Équipe",
      WORKSPACE: "Workspace Solution",
    },
    accessModes: {
      CONTRIBUTOR_ACTION_REQUIRED: "Contributeur (Action requise)",
      READ_ONLY_OBSERVER: "Consultation seule (Observateur)",
    },
    modules: {
      cockpit: "Cockpit & Chat",
      inbox: "Boîte & Mes Runs",
      catalog: "Catalogue Fédéré",
      ontology: "Ontologie & KB",
      gates: "Gates & Habilitations",
      finops: "FinOps & Audit",
      admin: "Administration & Pilotage des Workspaces",
      bootstrap: "Initialisation & Onboarding",
    },
    staleWarningBadgeLabel: "! [STALE_WARNING]",
    humanProfilePrefixLabel: "Profil Humain",
    assistantDockTitle: "Agent Assistant & Permission Broker",
    assistantDockSubtitle: "Exécution Passthrough gouvernée",
    assistantDockToggleExpandLabel: "Déplier le Dock Assistant",
    assistantDockToggleCollapseLabel: "Replier le Dock Assistant",
    assistantPermissionBrokerReadyLabel: "Permission Broker actif",
    assistantInputPlaceholder: "Poser une question à l'Assistant ou diagnostiquer un accès 403...",
    assistantSendLabel: "Envoyer à l'Assistant",
    localeSwitchLabel: "Langue",
    topbarSearchAriaLabel: "Recherche globale",
    topbarSearchPlaceholder: "Rechercher... (⌘K)",
    darkModeToggleLabel: "🌙 Mode sombre",
    mobileNavigationAriaLabel: "Navigation Compagnon Mobile",
    mobileTabs: {
      inbox: "🔔 Inbox",
      chat: "💬 Arbitrage/Chat",
      briefing: "📄 Briefing",
    },
  },
  humanAnchor: {
    badgeTitle: "✍️ ANCRAGE HUMAIN OBLIGATOIRE (human_authored_required: true)",
    authorLabel: "Auteur humain",
    placeholderText: "Saisissez vos hypothèses structurantes (rédaction humaine obligatoire)...",
    submitLabel: "Signer l'ancrage humain",
    defaultSectionTitle: "Intentions & Contraintes Architecturales",
    defaultAuthorName: "Architecte / Tech Lead",
    defaultValue: "Isolation hexagonale stricte et contrat OpenAPI 3.1 sans dérive (0-diff).",
  },
  arbitrationTieBreak: {
    badgeTitle: "⚖️ ARBITRAGE HUMAIN REQUIS (WAITING_FOR_HUMAN_ARBITRATION)",
    policyPrefixLabel: "Politique tie_break_policy",
    recommendedBadgeLabel: "★ Recommandé",
    prosLabel: "Avantages",
    consLabel: "Inconvénients",
    siImpactLabel: "Impact SI",
    finopsImpactLabel: "FinOps",
    justificationPlaceholder: "Justification ou orientation complémentaire (optionnel)...",
    selectOptionButtonLabel: "Choisir cette option",
    resolvedBannerPrefix: "✅ Décision d'arbitrage enregistrée dans le Blackboard",
    defaultQuestionTitle: "Garantie de taux FX multi-devises : Taux Spot 15 min vs Taux Bloqué 48h",
    defaultContextSummary:
      "Deux options techniques et métier équivalentes détectées par l'Agent Exécuteur (FR-5, UX-DR6).",
  },
  workspaceTopology: {
    panelTitle: "Arbre d'Équipes (OrgUnit), Workspaces Multi-Sources & 5 Permissions Dissociées",
    panelSubtitle:
      "Authentification Hybride Bi-Mode (OIDC + Locale Argon2id/TOTP), Roll-up ascendant et isolation inter-Workspaces.",
    personaSelectorLabel: "Simuler la persona RBAC active",
    personas: {
      karim: "Karim — PLATFORM_ADMIN (Entreprise)",
      claire: "Claire — BU_DIRECTOR (Roll-up Observateur)",
      marc: "Marc — TEAM_LEAD (Sous-Équipe Checkout)",
      nadia: "Nadia — CONTRIBUTOR (Développeuse)",
      partenaire: "Partenaire Externe (Invité Workspace 1)",
    },
    finopsRollupPrefix: "Roll-up FinOps consolidé",
    confidentialExcludedNotice:
      "Les Workspaces marqués CONFIDENTIAL_RESTRICTED bloquent tout Roll-up ascendant sur le contenu métier.",
    datasourcesCountPrefix: "Sources fédérées rattachées",
    catalogPermissionsTitle: "5 Permissions Dissociées du Catalogue & Protection Boîte Noire",
    sourceMaskedBadgeLabel: "🔒 Source masquée (READ_SOURCE=False)",
    sourceOpenBadgeLabel: "📖 Source accessible (READ_SOURCE=True)",
    inspectSourceButtonLabel: "Inspecter la source",
    sourceDeniedErrorBanner: "HTTP 403 ERR_READ_SOURCE_DENIED — Permission READ_SOURCE requise",
    sourceAllowedBannerPrefix: "HTTP 200 OK — Source autorisée",
    mutationGuardButtonLabel: "Tester ScopeAccessGuard (Mutation)",
    mutationAllowedBanner: "HTTP 200 OK — Mutation autorisée (Contributeur)",
    mutationDeniedObserverBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Mutation rejetée en mode Observateur",
  },
  catalogExplorer: {
    panelTitle: "Catalogue Fédéré Multi-Sources, Cache CAS SHA-256 & Surcharges à 4 Niveaux",
    panelSubtitle:
      "Résolution à la volée (< 50 ms sur cache chaud cas/<sha256>), cycle de publication gouverné et Adaptateur BMAD.",
    filterAllSchemesLabel: "Tous les schémas",
    maskedSourceBadgeLabel: "🔒 Source masquée",
    openSourceBadgeLabel: "📖 Source ouverte",
    resolveCasButtonLabel: "Résoudre CAS (< 50 ms)",
    casResolvedBannerPrefix: "HTTP 200 OK — Objet immuable résolu",
    promoteScopeButtonLabel: "Promouvoir la portée",
    promotedBannerPrefix: "HTTP 200 OK — Portée promue",
    promoteDeniedObserverBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Promotion refusée en mode Observateur",
    overrideSectionTitle: "Fusion Déclarative à 4 Niveaux (Base -> Team -> Workspace -> User)",
    overrideSectionSubtitle:
      "Hiérarchie pure non mutante avec génération déterministe du manifeste cryptographique run-lock.json.",
    overrideLayers: {
      base: "1. Base (db://workflow)",
      teamParent: "2a. Équipe Parente (Architecture)",
      teamSub: "2b. Sous-Équipe (Checkout)",
      workspace: "3. Workspace (3 git + 2 jira + 2 confluence)",
      user: "4. Utilisateur (Marc Tech Lead)",
    },
    runLockTitle: "Manifeste run-lock.json (Sources épinglées SHA-256)",
    bmadAdapterTitle: "Adaptateur BMAD sans perte (SKILL.md + customize.toml + steps/*.md)",
    bmadImportButtonLabel: "Importer un Pack BMAD",
    bmadImportedBanner:
      "HTTP 200 OK — Pack BMAD converti en WorkflowDefinitionEntity (source_format=BMAD_PACK) et épinglé dans cas/<sha256>",
    workflowStudio: {
      studioTitle:
        "Studio Workflow-as-Code YAML/JSON (SUB_WORKFLOW <= 3), Discipline Intention -> Code & Gabarits Multi-Audience",
      studioSubtitle:
        "Validation statique par numéro de ligne, garde-fou HIGH_CRITICAL vs AUTONOMOUS_CONTRACT et épinglage récursif sub_workflow_locks.",
      validateNominalLabel: "Valider DAG nominal (depth=2 <= 3)",
      simulateCriticalAutonomousLabel: "Tester HIGH_CRITICAL + AUTONOMOUS_CONTRACT (422)",
      simulateMissingIntentionLabel: "Tester écriture code sans Intention amont (422)",
      simulateMaxDepthLabel: "Tester SUB_WORKFLOW depth=4 > 3 (422)",
      validDagBanner:
        "HTTP 200 OK — DAG valide : 3 étapes topologiques, Intention -> Code respecté, max_nesting_depth=2 <= 3",
      criticalAutonomousErrorBanner:
        "HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE [Ligne 6] — Un workflow HIGH_CRITICAL ne peut pas utiliser AUTONOMOUS_CONTRACT",
      missingIntentionErrorBanner:
        "HTTP 422 ERR_INTENTION_BEFORE_CODE_REQUIRED [Ligne 18] — Étape writes_code=true sans étape amont declares_intention=true",
      maxDepthErrorBanner:
        "HTTP 422 ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED [Ligne 24] — Profondeur SUB_WORKFLOW 4 > 3",
      templatePreviewTitle:
        "Compilateur de Gabarit d'Artefact Multi-Audience (tpl-architecture-decision-record)",
      humanMarkdownTabLabel: "Vue Humaine (Markdown + Chunks)",
      agentSchemaTabLabel: "Vue Agent (JSON Schema Ontologie)",
      sampleHumanMarkdown:
        "## 1. Intention Stratégique & Arbitrage Humain [✍️ ANCRE HUMAINE OBLIGATOIRE]\nIntention directrice pour **Claims Core Engine** (Ticket `PAY-142`)",
      sampleAgentJsonSchema:
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","x-bound-ontology-terms":["Actif Stratégique","Exemption 3DS Frictionless TRA"]}',
      subWorkflowLocksTitle: "Arbre récursif sub_workflow_locks épinglé dans run-lock.json",
    },
  },
  permissionBroker: {
    cardBadgeTitle: "⚠️ PERMISSION BROKER",
    passthroughBadgeLabel: "Identité : passthrough",
    servicePrincipalBadgeLabel: "Identité : service_principal",
    targetUriLabel: "Source externe bloquée",
    requiredRoleLabel: "Rôle ou groupe requis (KB)",
    approverTeamLabel: "Équipe approbatrice",
    slaHoursPrefix: "SLA",
    rfcHintLabel: "Indice RFC 9457 (permission_broker_hint)",
    jiraRequestButtonLabel: "Demander l'accès dans Atlassian Jira",
    pauseStepButtonLabel: "Mettre en pause",
    replayStepButtonLabel: "Rejouer l'étape",
    pausedStateBanner: "⏸️ Étape mise en pause en attente de validation Jira",
    replayedStateBanner: "✅ Accès débloqué — Étape rejouée avec succès (REPLAYED)",
    simulatorTitle:
      "Exécution Passthrough vs Service Principal & Permission Broker IA connecté à Jira",
    simulatorSubtitle:
      "Interception des refus 401/403, résolution KB Markdown/YAML, ouverture automatique du Dock droit et Replay Step N.",
    simulateGitDenialLabel: "Simuler 403 Git (passthrough)",
    simulateConfluenceDenialLabel: "Simuler 403 Confluence (passthrough)",
    simulateJiraDenialLabel: "Simuler 403 Jira SecOps (passthrough)",
    simulateConfusedDeputyLabel: "Tester Service Principal non approuvé",
    confusedDeputyBlockedBanner:
      "HTTP 403 ERR_CONFUSED_DEPUTY_BLOCKED — Exécution service_principal bloquée sans approbation admin",
    observerDeniedBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Action Permission Broker refusée en mode Observateur",
  },
  bootstrapOnboarding: {
    panelTitle: "Workflows Système d'Amorçage Gouverné Jour 0 & Onboarding Autonome d'Équipe",
    panelSubtitle:
      "6 workflows pré-embarqués (orcia://system/bootstrap/*), orthogonalité LLM (>= 2 familles), self-service TEAM_LEAD et Ancre Humaine.",
    orthogonalityTitle: "Gate Jour 0 (init-organization) — ModelRouterService (>= 2 familles LLM)",
    orthogonalityPassBadge: "Orthogonalité LLM vérifiée (3 familles : anthropic-claude, mistral-large, openai-gpt)",
    orthogonalityFailBanner:
      "HTTP 422 ERR_MODEL_ORTHOGONALITY_VIOLATION — Au moins 2 familles LLM orthogonales sont requises",
    simulateSingleFamilyLabel: "Tester 1 seule famille LLM (Rejet 422)",
    simulateDualFamilyLabel: "Valider >= 2 familles LLM orthogonales",
    initWorkspaceTitle: "Onboarding Autonome d'Équipe & Multi-Workspaces (init-workspace, TEAM_LEAD)",
    initWorkspaceButtonLabel: "Exécuter init-workspace (Multi-Workspaces)",
    initWorkspaceSuccessBanner:
      "HTTP 200 OK — Équipe, 2 Workspaces solutions, surcharges 4 niveaux et invitations créés sans ticket IT",
    initDatasourceTitle: "Rattachement Gouverné Multi-Sources (init-datasource) & Ancre Humaine",
    initDatasourceButtonLabel: "Publier la source fédérée (init-datasource)",
    initDatasourceSuccessBanner:
      "HTTP 200 OK — Source publiée dans le Catalogue Fédéré avec Ancre Humaine signée et TTL de fraîcheur",
    humanAnchorErrorBanner:
      "HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED — Justification humaine (>= 30 car.) et signature obligatoires",
    initUserTitle: "Onboarding Première Connexion & Liaison Passthrough AES-256-GCM (init-user)",
    initUserButtonLabel: "Exécuter init-user (Liaison Passthrough)",
    initUserSuccessBanner:
      "HTTP 200 OK — Profil Humain confirmé & jetons Passthrough (Git, Jira, Confluence) chiffrés AES-256-GCM",
    observerDeniedBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Exécution d'amorçage refusée en mode Observateur",
    humanAnchorCardLabels: {
      badgeTitle: "✍️ ANCRAGE HUMAIN OBLIGATOIRE (human_authored_required: true)",
      authorLabel: "Signataire humain",
      sectionTitle: "Justification de sécurité & périmètre du connecteur fédéré",
      placeholderText: "Rédigez la justification humaine obligatoire (>= 30 caractères)...",
      signatureLabel: "Signature cryptographique / nominative de l'auteur humain",
      signaturePlaceholder: "Ex: Marc (Tech Lead Checkout)",
      submitLabel: "Signer l'ancre humaine",
    },
  },
  ontologyExplorer: {
    panelTitle: "Explorateur d'Ontologie à 4 Niveaux, Simulateur What-If & Graphe Tripartite",
    panelSubtitle:
      "Héritage CTE (Entreprise -> Domaine -> Équipe/Workspace -> Run), RAG Hybride halfvec(1024)+BM25 et alertes [STALE_WARNING].",
    emptyStateMessage:
      "Aucun concept ontologique ni document indexé dans l'état initial (0 donnée par défaut). Utilisez init-workspace ou init-datasource pour alimenter l'ontologie et la base RAG.",
    columns: {
      "1_ENTERPRISE": "1. Entreprise (Global)",
      "2_DOMAIN": "2. Domaine (BU)",
      "3_TEAM": "3a. Équipe (Arbre)",
      "3_WORKSPACE": "3b. Workspace Solution",
      "4_RUN_EPHEMERAL": "4. Run Éphémère (Branche)",
    },
    profileSelectorLabel: "Traduction Profil Humain :",
    whatIfButtonLabel: "Simuler l'Impact (What-If)",
    promoteButtonLabel: "Promouvoir le concept",
    promotedBannerPrefix: "Simulation What-If exécutée pour :",
    immutableConflictBanner: "ERR_ONTOLOGY_CONFLICT (HTTP 422) : axiome parent immutable=true inviolable.",
    hybridRagTitle: "Recherche RAG Hybride (halfvec(1024) + BM25 RRF)",
    hybridRagSearchPlaceholder: "Rechercher un concept, ticket Jira (PAY-142) ou symbole AST...",
    hybridRagSearchButtonLabel: "Rechercher",
    tripartiteTitle: "Graphe Tripartite Multi-Sources (Confluence <-> Jira <-> Git)",
    staleAlertsTitle: "Brique data-freshness & Alertes [STALE_WARNING]",
    docObsoleteBadgeLabel: "[DOC_OBSOLETE_SUSPECTED]",
  },
  modulePages: {
    cockpit: {
      subtitle: "Espace de co-conception Human-Led, Agent-Accelerated",
      description:
        "Pilotez vos Workflows durables, rédigez les Ancres Humaines Obligatoires et arbitrez les matrices de décision.",
      uriBadgeExample: "orcia://system/workflows/assistant-agent",
    },
    inbox: {
      subtitle: "Boîte de Notifications Unifiée & Verrouillage Temps Réel (< 500ms)",
      description:
        "Consultez vos Workflow Runs actifs en mode Contributeur ou Observateur et prenez en charge les étapes en attente.",
      uriBadgeExample: "orcia://runs/active/inbox",
    },
    catalog: {
      subtitle: "Catalogue Fédéré Multi-Sources & Cache CAS SHA-256",
      description:
        "Explorez les ressources fédérées (git://, jira://, confluence://, db://, nexus://) et les surcharges à 4 niveaux.",
      uriBadgeExample: "git://orcia-core/skills/bmad-pack@sha256:8f4e2b",
    },
    ontology: {
      subtitle: "Ontologie Dynamique à 4 Niveaux & Base de Connaissances RAG",
      description:
        "Gouvernez les concepts (Entreprise, Domaine, Équipe/Workspace, Run Éphémère) et résolvez les alertes [STALE_WARNING].",
      uriBadgeExample: "confluence://ARCHI/ontology-v1@v12",
    },
    gates: {
      subtitle: "Gates Déterministes, Agentiques Cross-Model & Permission Broker",
      description:
        "Auditez les évaluations en DAG de lentilles orthogonales et débloquez les refus 401/403 via Jira.",
      uriBadgeExample: "jira://IAM/PERM-403",
    },
    finops: {
      subtitle: "Journal d'Audit Immuable & Coupe-Circuit Budgétaire FinOps",
      description:
        "Suivez la consommation de tokens par modèle/étape et vérifiez la lignée cryptographique run-lock.json.",
      uriBadgeExample: "db://orcia/audit_ledger",
    },
    admin: {
      subtitle: "Centre de Pilotage Unifié des Workspaces & Unités Organisationnelles",
      description:
        "Administrez l'arbre d'équipes (OrgUnit), les Workspaces Solutions multi-sources et leurs habilitations.",
      uriBadgeExample: "orcia://system/workspaces/topology",
    },
    bootstrap: {
      subtitle: "Workflows Système d'Amorçage Jour 0 & Onboarding d'Équipe",
      description:
        "Initialisez l'organisation (init-organization), les Workspaces (init-workspace), les sources fédérées et les utilisateurs.",
      uriBadgeExample: "orcia://system/bootstrap/init-workspace",
    },
  },
  upstreamChallengeModal: {
    modalTitle: "Challenge Amont & Simulation d'Impact What-If (UX-DR7)",
    modalSubtitle:
      "Contestez une règle d'un artefact amont, inspectez le graphe d'impact aval et déclenchez un Replay ciblé Step N (0 token reconsommé en amont).",
    targetStepLabel: "Step amont ciblé",
    sectionKeyLabel: "Section / Règle contestée",
    reasonLabel: "Justification technique ou métier du Challenge (>= 10 car.)",
    reasonPlaceholder: "Expliquez l'incohérence détectée vis-à-vis de l'artefact amont...",
    whatIfTitle: "Aperçu de Simulation d'Impact (What-If Impact Preview — AD-7)",
    invalidatedStepsLabel: "Steps aval invalidés",
    invalidatedSectionsLabel: "Sections d'artefacts impactées",
    invalidatedAxiomsLabel: "Axiomes d'Ontologie concernés",
    preservedStepsLabel: "Steps amont préservés (run-lock.json SHA-256)",
    translatedSummaryLabel: "Traduction Ontologique pour l'auteur amont",
    submitChallengeCta: "Envoyer le Challenge Amont (Outbox)",
    replayStepCta: "Relancer Replay ciblé Step N (0 token amont)",
    closeCta: "Fermer",
    challengeSubmittedFeedback: "Challenge Amont transmis via domain_events_outbox ✓",
    replayTriggeredFeedback: "Replay ciblé Step N exécuté (branche ACTIVE créée, anciens snapshots SUPERSEDED) ✓",
  },
  humanGates: {
    briefing: {
      gridTitle: "Briefing de Revue Cognitive (4 Blocs — UX-DR4)",
      block1Title: "1. Résumé Exécutif",
      block2Title: "2. Éléments Clés & Contrôle Transverse",
      block3Title: "3. Décisions Prises",
      block4Title: "4. Hypothèses Retenues",
      inspectHypothesesButtonLabel: "Marquer les hypothèses comme inspectées",
      hypothesesInspectedBadgeLabel: "Bloc 4 inspecté",
      hypothesesPendingBadgeLabel: "Inspection requise (Bloc 4)",
    },
    chunkValidation: {
      sectionListTitle: "Validation par Découpage (UX-DR5 — Zéro bouton Tout Approuver)",
      keyboardNavHint: "Navigation clavier : Alt + ↑ / ↓",
      approveSectionLabel: "Valider la section",
      coEditSectionLabel: "Co-éditer (SHA-256)",
      challengeSectionLabel: "Challenger / Rewind amont",
      finalizeGateButtonLabel: "Approuver la Gate Humaine",
      pendingSectionsNotice:
        "Chaque section obligatoire et le Bloc 4 (Hypothèses Retenues) doivent être validés individuellement.",
      guardModalTitle: "Garde-fou Anti-Rubber-Stamping (< 15 s — UX-DR10)",
      guardModalDescription:
        "Approbation soumise en moins de 15 secondes sur un artefact > 1 000 mots. Confirmez explicitement les hypothèses retenues (fast_approval_warning: true).",
      guardConfirmCheckboxLabel:
        "Je confirme avoir vérifié les hypothèses retenues et les sections critiques",
      guardConfirmButtonLabel: "Confirmer et enregistrer l'approbation",
      guardCancelButtonLabel: "Reprendre la lecture",
    },
  },
};
