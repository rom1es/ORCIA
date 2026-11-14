/**
 * Story 18.1 — Bilingue FR / EN labels for Workspace Multi-Nature Sources & GitNexus Governance.
 *
 * Strict Direction C token alignment, zero raw string in JSX.
 */

export interface Epic18SourcesLabels {
  filters: {
    all: string;
    docKb: string;
    tracker: string;
    code: string;
    schema: string;
  };
  columns: {
    nature: string;
    alias: string;
    connector: string;
    target: string;
    mode: string;
    freshness: string;
    gitnexus: string;
    actions: string;
  };
  syncModes: {
    webhook: string;
    polling24h: string;
  };
  freshnessStatuses: {
    synced: string;
    stale: string;
    syncError: string;
    pendingInitial: string;
  };
  codegraph: {
    title: string;
    switchLabel: string;
    readyBadge: string;
    indexingBadge: string;
    disabledBadge: string;
    pausedBadge: string;
    serviceAccountLabel: string;
    leadTokenLabel: string;
    leadRequiredTooltip: string;
    switchNotice: string;
  };
  actions: {
    syncBtn: string;
    syncTriggered: string;
    attachSourceBtn: string;
    editSourceBtn: string;
    deleteSourceBtn: string;
    deleteConfirmTitle: string;
    deleteConfirmDesc: string;
    cancelBtn: string;
    confirmDeleteBtn: string;
    saveBtn: string;
    createSuccess: string;
    updateSuccess: string;
    deleteSuccess: string;
    reconcileBtn: string;
    reconciling: string;
    reconcileSuccess: string;
  };
  modal: {
    createTitle: string;
    editTitle: string;
    description: string;
    natureLabel: string;
    natureDoc: string;
    natureTracker: string;
    natureCode: string;
    natureSchema: string;
    aliasLabel: string;
    aliasPlaceholder: string;
    uriLabel: string;
    uriPlaceholder: string;
    targetScopeLabel: string;
    targetRefLabel: string;
    connectorLabel: string;
    connectorNone: string;
    syncModeLabel: string;
    ragIdentityLabel: string;
    ragServiceAccount: string;
    ragReferentUser: string;
    referentUserIdLabel: string;
    serviceAccountIdLabel: string;
    gitnexusSectionTitle: string;
    gitnexusEnableLabel: string;
    gitnexusAuthModeLabel: string;
    gitnexusOwnerUserLabel: string;
    observerBlockedError: string;
    leadRequiredError: string;
  };
  settingsDeportBanner: {
    title: string;
    description: string;
    buttonLabel: string;
  };
}

export const EPIC18_SOURCES_LABELS_FR: Epic18SourcesLabels = {
  filters: {
    all: "Toutes",
    docKb: "Connaissances",
    tracker: "Backlog & Tickets",
    code: "Code & Contrats",
    schema: "Schémas SQL",
  },
  columns: {
    nature: "Nature",
    alias: "Nom / Source",
    connector: "Connecteur",
    target: "Cible & Réf",
    mode: "Mode de synchro",
    freshness: "Fraîcheur & Empreinte",
    gitnexus: "GitNexus (AST & Graphe)",
    actions: "Actions",
  },
  syncModes: {
    webhook: "Webhook push",
    polling24h: "Sonde 24h",
  },
  freshnessStatuses: {
    synced: "À jour",
    stale: "Désynchronisé",
    syncError: "Erreur synchro",
    pendingInitial: "Initialisation en attente",
  },
  codegraph: {
    title: "Graphe de code souverain GitNexus",
    switchLabel: "Activer GitNexus pour ce dépôt",
    readyBadge: "Prêt (AST + Dépendances)",
    indexingBadge: "Indexation en cours...",
    disabledBadge: "Désactivé",
    pausedBadge: "En pause — Jeton responsable à renouveler",
    serviceAccountLabel: "Compte de service",
    leadTokenLabel: "Jeton du responsable",
    leadRequiredTooltip:
      "L'activation du graphe GitNexus requiert un rôle Responsable d'espace (TEAM_LEAD, BU_LEAD, PLATFORM_ADMIN ou SECOPS).",
    switchNotice: "Indexation déterministe AST légère (0 $ LLM, lecture seule)",
  },
  actions: {
    syncBtn: "Synchroniser",
    syncTriggered: "Synchronisation déclenchée avec succès",
    attachSourceBtn: "+ Rattacher une Source",
    editSourceBtn: "Modifier",
    deleteSourceBtn: "Supprimer",
    deleteConfirmTitle: "Détacher la source",
    deleteConfirmDesc:
      "Êtes-vous sûr de vouloir détacher cette source de l'espace ? Les index associés seront désactivés.",
    cancelBtn: "Annuler",
    confirmDeleteBtn: "Confirmer la suppression",
    saveBtn: "Enregistrer la source",
    createSuccess: "Source rattachée avec succès",
    updateSuccess: "Source mise à jour avec succès",
    deleteSuccess: "Source supprimée avec succès",
    reconcileBtn: "Vérifier fraîcheur",
    reconciling: "Vérification en cours...",
    reconcileSuccess: "Fraîcheur des sources réconciliée avec succès.",
  },
  modal: {
    createTitle: "Rattacher une Source à l'Espace",
    editTitle: "Modifier la Source de l'Espace",
    description:
      "Configurez la nature de la ressource, son rattachement connecteur et ses options d'indexation.",
    natureLabel: "Nature de la source",
    natureDoc: "Base documentaire & Connaissances (Confluence, Docs)",
    natureTracker: "Gestion de tickets & Backlog (Jira, Linear)",
    natureCode: "Code source & Contrats (Git, Dépôts)",
    natureSchema: "Schéma relationnel DDL (PostgreSQL, SQL)",
    aliasLabel: "Nom / Alias de la source",
    aliasPlaceholder: "ex: repo-paiements, spec-checkout",
    uriLabel: "Adresse ou URI",
    uriPlaceholder: "ex: git://gitlab.entreprise.io/pay/core.git",
    targetScopeLabel: "Périmètre / Projet cible (optionnel)",
    targetRefLabel: "Branche / Version cible (optionnel)",
    connectorLabel: "Connecteur socle homologué",
    connectorNone: "Aucun connecteur socle (connexion libre)",
    syncModeLabel: "Mode de synchronisation",
    ragIdentityLabel: "Identité d'indexation RAG",
    ragServiceAccount: "Compte de service",
    ragReferentUser: "Membre référent de l'équipe",
    referentUserIdLabel: "Identifiant du membre référent",
    serviceAccountIdLabel: "Identifiant du compte de service",
    gitnexusSectionTitle: "Options GitNexus (Code source uniquement)",
    gitnexusEnableLabel: "Activer le graphe de code déterministe GitNexus",
    gitnexusAuthModeLabel: "Mode d'authentification GitNexus",
    gitnexusOwnerUserLabel: "Identifiant du Responsable d'espace (titulaire du jeton)",
    observerBlockedError: "Action refusée : espace en mode observateur (lecture seule).",
    leadRequiredError:
      "Action réservée aux Responsables d'espace (TEAM_LEAD, BU_LEAD, PLATFORM_ADMIN, SECOPS).",
  },
  settingsDeportBanner: {
    title: "Déport des Sources dans les Espaces d'Équipe",
    description:
      "L'administration générale des connecteurs d'entreprise reste sous /settings. Les sources documentaires et dépôts sont désormais gouvernés directement par chaque équipe sous /workspaces/$wsId/sources.",
    buttonLabel: "Accéder aux Sources de l'Espace",
  },
};

export const EPIC18_SOURCES_LABELS_EN: Epic18SourcesLabels = {
  filters: {
    all: "All",
    docKb: "Knowledge",
    tracker: "Backlog & Tickets",
    code: "Code & Contracts",
    schema: "SQL Schemas",
  },
  columns: {
    nature: "Nature",
    alias: "Name / Source",
    connector: "Connector",
    target: "Target & Ref",
    mode: "Sync mode",
    freshness: "Freshness & Fingerprint",
    gitnexus: "GitNexus (AST & Graph)",
    actions: "Actions",
  },
  syncModes: {
    webhook: "Webhook push",
    polling24h: "24h Probe",
  },
  freshnessStatuses: {
    synced: "Up to date",
    stale: "Stale",
    syncError: "Sync error",
    pendingInitial: "Initial sync pending",
  },
  codegraph: {
    title: "Sovereign code graph GitNexus",
    switchLabel: "Enable GitNexus for this repository",
    readyBadge: "Ready (AST + Graph)",
    indexingBadge: "Indexing in progress...",
    disabledBadge: "Disabled",
    pausedBadge: "Paused — Lead token renewal required",
    serviceAccountLabel: "Service Account",
    leadTokenLabel: "Lead Personal Token",
    leadRequiredTooltip:
      "Enabling GitNexus requires a Workspace Lead role (TEAM_LEAD, BU_LEAD, PLATFORM_ADMIN or SECOPS).",
    switchNotice: "Deterministic lightweight AST indexing (0 $ LLM, read-only)",
  },
  actions: {
    syncBtn: "Synchronize",
    syncTriggered: "Synchronization triggered successfully",
    attachSourceBtn: "+ Attach a Source",
    editSourceBtn: "Edit",
    deleteSourceBtn: "Delete",
    deleteConfirmTitle: "Detach source",
    deleteConfirmDesc:
      "Are you sure you want to detach this source from the workspace? Associated indexes will be deactivated.",
    cancelBtn: "Cancel",
    confirmDeleteBtn: "Confirm deletion",
    saveBtn: "Save source",
    createSuccess: "Source attached successfully",
    updateSuccess: "Source updated successfully",
    deleteSuccess: "Source removed successfully",
    reconcileBtn: "Check freshness",
    reconciling: "Checking freshness...",
    reconcileSuccess: "Source freshness reconciled successfully.",
  },
  modal: {
    createTitle: "Attach a Source to Workspace",
    editTitle: "Edit Workspace Source",
    description:
      "Configure resource nature, connector attachment, and indexing options.",
    natureLabel: "Source nature",
    natureDoc: "Knowledge base & Documents (Confluence, Docs)",
    natureTracker: "Issue tracker & Backlog (Jira, Linear)",
    natureCode: "Source code & Contracts (Git, Repos)",
    natureSchema: "Relational schema DDL (PostgreSQL, SQL)",
    aliasLabel: "Source Name / Alias",
    aliasPlaceholder: "e.g. payments-repo, checkout-spec",
    uriLabel: "Address or URI",
    uriPlaceholder: "e.g. git://gitlab.enterprise.io/pay/core.git",
    targetScopeLabel: "Target scope / project (optional)",
    targetRefLabel: "Target branch / version (optional)",
    connectorLabel: "Approved enterprise connector",
    connectorNone: "No enterprise connector (standalone)",
    syncModeLabel: "Sync mode",
    ragIdentityLabel: "RAG index identity",
    ragServiceAccount: "Service account",
    ragReferentUser: "Team referent member",
    referentUserIdLabel: "Referent member identifier",
    serviceAccountIdLabel: "Service account identifier",
    gitnexusSectionTitle: "GitNexus Options (Source code only)",
    gitnexusEnableLabel: "Enable GitNexus deterministic code graph",
    gitnexusAuthModeLabel: "GitNexus authentication mode",
    gitnexusOwnerUserLabel: "Workspace Lead identifier (token owner)",
    observerBlockedError: "Action denied: workspace is in read-only observer mode.",
    leadRequiredError:
      "Action restricted to Workspace Leads (TEAM_LEAD, BU_LEAD, PLATFORM_ADMIN, SECOPS).",
  },
  settingsDeportBanner: {
    title: "Relocation of Sources to Team Workspaces",
    description:
      "Enterprise connector platform administration remains under /settings. Document sources and code repositories are now directly governed by teams within each Workspace under /workspaces/$wsId/sources.",
    buttonLabel: "Go to Workspace Sources",
  },
};
