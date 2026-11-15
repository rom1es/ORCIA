import {
  IAM_DIRECTORY_EN_LABELS,
  IAM_DIRECTORY_FR_LABELS,
  type IamDirectoryLabels,
} from "./iam_accounts_directory_labels";

export type { IamDirectoryLabels };

export interface IamTabDictionarySection {
  readonly roles: Record<
    "PLATFORM_ADMIN" | "SECOPS" | "BU_LEAD" | "TEAM_LEAD" | "CONTRIBUTOR" | "OBSERVER",
    string
  >;
  readonly roleScopes: Record<"GLOBAL" | "BU" | "TEAM" | "WORKSPACE", string>;
  readonly verbs: Record<
    "create" | "read" | "update" | "delete" | "execute" | "grant",
    string
  >;
  readonly directory: IamDirectoryLabels;
  readonly matrix: {
    readonly sectionTitle: string;
    readonly sectionSubtitle: string;
    readonly openRoleMatrixCta: string;
    readonly closeRoleMatrixCta: string;
    readonly secretBannerTitle: string;
    readonly secretBannerBody: string;
    readonly colRole: string;
    readonly colNaturalScope: string;
    readonly colWorkflowsAgents: string;
    readonly colDatasourcesConnectors: string;
    readonly colOrgAndIam: string;
    readonly summaryFullPlatform: string;
    readonly summarySecurityAudit: string;
    readonly summaryBuSupervision: string;
    readonly summaryTeamLead: string;
    readonly summaryContributor: string;
    readonly summaryObserver: string;
  };
  readonly secopsDrawer: {
    readonly toggleTitle: string;
    readonly toggleSubtitle: string;
    readonly secopsBadge: string;
    readonly expandLabel: string;
    readonly collapseLabel: string;
    readonly nonSecopsLockedNotice: string;
    readonly helpTriggerLabel: string;
    readonly beneficiaryTypeLabel: string;
    readonly beneficiaryTypeRole: string;
    readonly beneficiaryTypeAccount: string;
    readonly targetRoleLabel: string;
    readonly targetAccountLabel: string;
    readonly targetScopeLabel: string;
    readonly globalScopeOption: string;
    readonly globalScopeAmberWarning: string;
    readonly buOptgroupLabel: string;
    readonly teamOptgroupLabel: string;
    readonly workspaceOptgroupLabel: string;
    readonly buScopePrefix: string;
    readonly teamScopePrefix: string;
    readonly workspaceScopePrefix: string;
    readonly resourceKindLabel: string;
    readonly resourceKinds: Record<
      "ALL" | "WORKFLOW" | "AGENT" | "DATASOURCE" | "CONNECTOR",
      string
    >;
    readonly effectLabel: string;
    readonly effectAllow: string;
    readonly effectDeny: string;
    readonly effectIsolate: string;
    readonly verbsFieldsetLabel: string;
    readonly autoReadHint: string;
    readonly submitExceptionCta: string;
    readonly emptyGrantsText: string;
    readonly selectedCountLabel: string;
    readonly selectAllGrantsLabel: string;
    readonly deleteSelectedCta: string;
    readonly deleteSingleLabel: string;
    readonly rolePrefix: string;
    readonly userPrefix: string;
    readonly spPrefix: string;
    readonly badgeAllow: string;
    readonly badgeDeny: string;
    readonly badgeIsolated: string;
  };
}

export const IAM_TAB_FR_LABELS: IamTabDictionarySection = {
  roles: {
    PLATFORM_ADMIN: "Administrateur Plateforme", SECOPS: "Responsable Sécurité (SecOps)",
    BU_LEAD: "Responsable de Direction (BU)", TEAM_LEAD: "Responsable d'Équipe",
    CONTRIBUTOR: "Contributeur", OBSERVER: "Observateur",
  },
  roleScopes: {
    GLOBAL: "Plateforme entière", BU: "Direction / Pôle (BU)",
    TEAM: "Équipe", WORKSPACE: "Espace de travail",
  },
  verbs: {
    create: "Créer", read: "Consulter les ressources", update: "Modifier",
    delete: "Supprimer", execute: "Exécuter / Utiliser", grant: "Déléguer des droits",
  },
  directory: IAM_DIRECTORY_FR_LABELS,
  matrix: {
    sectionTitle: "Matrice des 6 Rôles Officiels de la Plateforme",
    sectionSubtitle:
      "Synthèse claire des droits natifs par périmètre. Vous n'avez aucune règle manuelle à créer pour le fonctionnement courant.",
    openRoleMatrixCta: "Voir la matrice des 6 rôles",
    closeRoleMatrixCta: "Fermer",
    secretBannerTitle: "Confidentialité absolue des secrets (saisie seule)", // pragma: allowlist secret
    secretBannerBody:
      "Aucun rôle — pas même Administrateur Plateforme ou Responsable Sécurité — ne permet de relire ou d'afficher une clé secrète après son enregistrement. Les secrets peuvent uniquement être définis, remplacés ou effacés.",
    colRole: "Rôle officiel",
    colNaturalScope: "Périmètre naturel",
    colWorkflowsAgents: "Processus & Agents",
    colDatasourcesConnectors: "Sources & Connecteurs",
    colOrgAndIam: "Organisation & Habilitations",
    summaryFullPlatform: "Administration complète de la plateforme et de l'organigramme",
    summarySecurityAudit: "Politiques de sécurité, audit de conformité et exceptions d'accès",
    summaryBuSupervision: "Pilotage des équipes, budgets et espaces de sa Direction (BU)",
    summaryTeamLead: "Animation d'équipe, validation des livrables et délégation locale",
    summaryContributor: "Exécution des processus, usage de l'assistant et contribution métier",
    summaryObserver: "Consultation uniquement — aucune modification ni exécution",
  },
  secopsDrawer: {
    toggleTitle: "2. Exceptions & Isolation de Périmètre (Avancé — SecOps)",
    toggleSubtitle:
      "Réservé aux cas particuliers : isoler un espace confidentiel, interdire une action précise ou accorder une dérogation ciblée.",
    secopsBadge: "Gouvernance SecOps",
    expandLabel: "Déplier le panneau",
    collapseLabel: "Replier le panneau",
    nonSecopsLockedNotice:
      "Consultation seule : seul un compte disposant du rôle Responsable Sécurité (SecOps) peut créer ou supprimer des exceptions d'accès et des règles d'isolation.",
    helpTriggerLabel: "Comprendre les exceptions et l'isolation de périmètre",
    beneficiaryTypeLabel: "Type de bénéficiaire",
    beneficiaryTypeRole: "Un rôle officiel",
    beneficiaryTypeAccount: "Un compte précis de l'annuaire",
    targetRoleLabel: "Rôle bénéficiaire",
    targetAccountLabel: "Compte bénéficiaire",
    targetScopeLabel: "Périmètre cible (« Sur quoi ? »)",
    globalScopeOption: "Plateforme entière (toutes les directions et espaces)",
    globalScopeAmberWarning:
      "Attention : cette exception s'appliquera à l'ensemble de la plateforme. Préférez une Direction, une Équipe ou un Espace précis lorsque c'est possible.",
    buOptgroupLabel: "Directions & Pôles (BU)",
    teamOptgroupLabel: "Équipes",
    workspaceOptgroupLabel: "Espaces de travail",
    buScopePrefix: "Direction / BU :",
    teamScopePrefix: "Équipe :",
    workspaceScopePrefix: "Espace :",
    resourceKindLabel: "Famille de ressources concernée",
    resourceKinds: {
      ALL: "Toutes les ressources du périmètre",
      WORKFLOW: "Processus uniquement",
      AGENT: "Agents & compétences uniquement",
      DATASOURCE: "Sources documentaires uniquement",
      CONNECTOR: "Connecteurs externes uniquement",
    },
    effectLabel: "Effet de la règle",
    effectAllow: "Autoriser (dérogation ciblée)",
    effectDeny: "Interdire (prioritaire sur tout rôle)",
    effectIsolate: "Isoler ce périmètre (couper l'héritage parent)",
    verbsFieldsetLabel: "Actions concernées par l'exception",
    autoReadHint:
      "« Consulter les ressources » est automatiquement maintenu dès qu'une action de création, modification, suppression ou exécution est cochée.",
    submitExceptionCta: "+ Ajouter l'exception",
    emptyGrantsText: "Aucune exception ni règle d'isolation active.",
    selectedCountLabel: "sélection",
    selectAllGrantsLabel: "Tout sélectionner",
    deleteSelectedCta: "Supprimer la sélection",
    deleteSingleLabel: "Supprimer",
    rolePrefix: "Rôle",
    userPrefix: "Compte",
    spPrefix: "Service",
    badgeAllow: "Autorisé",
    badgeDeny: "Interdit",
    badgeIsolated: "Périmètre isolé",
  },
};

export const IAM_TAB_EN_LABELS: IamTabDictionarySection = {
  roles: {
    PLATFORM_ADMIN: "Platform Administrator", SECOPS: "Security Officer (SecOps)",
    BU_LEAD: "Division Lead (BU)", TEAM_LEAD: "Team Lead",
    CONTRIBUTOR: "Contributor", OBSERVER: "Observer",
  },
  roleScopes: {
    GLOBAL: "Entire platform", BU: "Division / Sub-BU",
    TEAM: "Team", WORKSPACE: "Workspace",
  },
  verbs: {
    create: "Create", read: "Read & view resources", update: "Update",
    delete: "Delete", execute: "Execute / Use", grant: "Delegate rights",
  },
  directory: IAM_DIRECTORY_EN_LABELS,
  matrix: {
    sectionTitle: "Platform 6 Official Roles Matrix",
    sectionSubtitle:
      "Clear overview of native permissions per scope. No manual rule is needed for standard operations.",
    openRoleMatrixCta: "View 6-role matrix",
    closeRoleMatrixCta: "Close",
    secretBannerTitle: "Strict write-only secret confidentiality", // pragma: allowlist secret
    secretBannerBody:
      "No role — not even Platform Administrator or Security Officer — can ever read or display a secret key after saving. Secrets can only be set, replaced, or cleared.",
    colRole: "Official role",
    colNaturalScope: "Natural scope",
    colWorkflowsAgents: "Processes & Agents",
    colDatasourcesConnectors: "Sources & Connectors",
    colOrgAndIam: "Organization & Permissions",
    summaryFullPlatform: "Full platform and organization tree administration",
    summarySecurityAudit: "Security policies, compliance audit, and access exceptions",
    summaryBuSupervision: "Supervises teams, budgets, and spaces across its Division (BU)",
    summaryTeamLead: "Leads team operations, deliverable sign-off, and local delegation",
    summaryContributor: "Runs processes, uses the assistant, and contributes deliverables",
    summaryObserver: "Read-only consultation — no edits or executions",
  },
  secopsDrawer: {
    toggleTitle: "2. Scope Exceptions & Isolation (Advanced — SecOps)",
    toggleSubtitle:
      "Reserved for special cases: isolate a confidential workspace, deny a specific action, or grant a targeted override.",
    secopsBadge: "SecOps Governance",
    expandLabel: "Expand panel",
    collapseLabel: "Collapse panel",
    nonSecopsLockedNotice:
      "Read-only view: only an account holding the Security Officer (SecOps) role can create or remove access exceptions and isolation rules.",
    helpTriggerLabel: "Understand scope exceptions and isolation",
    beneficiaryTypeLabel: "Beneficiary type",
    beneficiaryTypeRole: "An official role",
    beneficiaryTypeAccount: "A specific directory account",
    targetRoleLabel: "Beneficiary role",
    targetAccountLabel: "Beneficiary account",
    targetScopeLabel: "Target scope ('On what?')",
    globalScopeOption: "Entire platform (all divisions and workspaces)",
    globalScopeAmberWarning:
      "Warning: this exception applies to the entire platform. Prefer a specific Division, Team, or Workspace whenever possible.",
    buOptgroupLabel: "Divisions & Sub-BUs",
    teamOptgroupLabel: "Teams",
    workspaceOptgroupLabel: "Workspaces",
    buScopePrefix: "Division / BU:",
    teamScopePrefix: "Team:",
    workspaceScopePrefix: "Workspace:",
    resourceKindLabel: "Target resource family",
    resourceKinds: {
      ALL: "All resources in scope",
      WORKFLOW: "Processes only",
      AGENT: "Agents & skills only",
      DATASOURCE: "Document sources only",
      CONNECTOR: "External connectors only",
    },
    effectLabel: "Rule effect",
    effectAllow: "Allow (targeted override)",
    effectDeny: "Deny (overrides any role)",
    effectIsolate: "Isolate this scope (block parent inheritance)",
    verbsFieldsetLabel: "Actions covered by this exception",
    autoReadHint:
      "'Read & view resources' is automatically kept checked whenever create, update, delete, or execute is selected.",
    submitExceptionCta: "+ Add exception",
    emptyGrantsText: "No active exception or isolation rule.",
    selectedCountLabel: "selected",
    selectAllGrantsLabel: "Select all",
    deleteSelectedCta: "Delete selected",
    deleteSingleLabel: "Delete",
    rolePrefix: "Role",
    userPrefix: "Account",
    spPrefix: "Service",
    badgeAllow: "Allowed",
    badgeDeny: "Denied",
    badgeIsolated: "Isolated scope",
  },
};
