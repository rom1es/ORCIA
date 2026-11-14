import {
  ORGANIZATION_MODALS_EN_LABELS,
  ORGANIZATION_MODALS_FR_LABELS,
  type OrganizationCreateModalLabels,
  type OrganizationDeleteModalLabels,
  type OrganizationEditModalLabels,
  type OrganizationMembersModalLabels,
  type OrganizationModalsSection,
} from "./organization_modals_labels";

export type {
  OrganizationCreateModalLabels,
  OrganizationDeleteModalLabels,
  OrganizationEditModalLabels,
  OrganizationMembersModalLabels,
  OrganizationModalsSection,
};

export interface OrganizationTabDictionarySection extends OrganizationModalsSection {
  readonly sectionTitle: string;
  readonly helpTriggerLabel: string;
  readonly openCreateModalCta: string;
  readonly emptyStateText: string;
  readonly pedagogyTitle: string;
  readonly pedagogyBuSummary: string;
  readonly pedagogyTeamSummary: string;
  readonly pedagogyWorkspaceSummary: string;
  readonly openWorkspacesCta: string;
  readonly badges: {
    readonly rootBu: string;
    readonly subBu: string;
    readonly team: string;
    readonly billingActive: string;
    readonly billingDisabled: string;
    readonly leadPrefix: string;
    readonly rootAttachment: string;
    readonly parentAttachmentPrefix: string;
  };
  readonly nouns: {
    readonly memberSingular: string;
    readonly memberPlural: string;
    readonly workspaceSingular: string;
    readonly workspacePlural: string;
    readonly childUnitSingular: string;
    readonly childUnitPlural: string;
    readonly childTeamSingular: string;
    readonly childTeamPlural: string;
  };
  readonly rowActions: {
    readonly edit: string;
    readonly members: string;
    readonly delete: string;
  };
  readonly unknownUserError: string;
  readonly noMatchingKnownUser: string;
  readonly selectKnownUserHint: string;
}

export const ORGANIZATION_TAB_FR_LABELS: OrganizationTabDictionarySection = {
  ...ORGANIZATION_MODALS_FR_LABELS,
  sectionTitle: "Structure de l'Organisation (Directions / BU & Équipes)",
  helpTriggerLabel: "Comprendre la structure Directions (BU), Pôles et Équipes",
  openCreateModalCta: "+ Nouvelle unité",
  emptyStateText: "Aucune unité d'organisation (Direction / BU ou Équipe) configurée.",
  pedagogyTitle: "Repères : Direction / Pôle, Équipe et Espace de travail",
  pedagogyBuSummary:
    "Direction / BU & Pôle (Sous-BU) : structure managériale et périmètre d'héritage des règles.",
  pedagogyTeamSummary:
    "Équipe : collectif humain de travail et centre d'imputation FinOps des appels IA.",
  pedagogyWorkspaceSummary:
    "Espace : dossier métier ou produit rattaché à une équipe, créé et administré dans Mes Espaces.",
  openWorkspacesCta: "Ouvrir Mes Espaces →",
  unknownUserError:
    "L'identifiant saisi ne correspond à aucun utilisateur actif et connu de la plateforme.",
  noMatchingKnownUser: "Aucun utilisateur correspondant trouvé.",
  selectKnownUserHint:
    "Recherchez par nom, identifiant ou adresse e-mail pour sélectionner un compte actif.",
  badges: {
    rootBu: "Direction / BU",
    subBu: "Pôle / Sous-BU",
    team: "ÉQUIPE",
    billingActive: "Facturation FinOps active",
    billingDisabled: "Sans imputation FinOps",
    leadPrefix: "Responsable :",
    rootAttachment: "Racine — Plateforme entière",
    parentAttachmentPrefix: "Rattaché à :",
  },
  nouns: {
    memberSingular: "membre",
    memberPlural: "membres",
    workspaceSingular: "espace",
    workspacePlural: "espaces",
    childUnitSingular: "sous-unité",
    childUnitPlural: "sous-unités",
    childTeamSingular: "Équipe rattachée",
    childTeamPlural: "Équipes rattachées",
  },
  rowActions: {
    edit: "Modifier",
    members: "Membres",
    delete: "Supprimer",
  },
};

export const ORGANIZATION_TAB_EN_LABELS: OrganizationTabDictionarySection = {
  ...ORGANIZATION_MODALS_EN_LABELS,
  sectionTitle: "Organization Structure (Divisions / BUs & Teams)",
  helpTriggerLabel: "Understand Divisions (BUs), Sub-Divisions, and Teams structure",
  openCreateModalCta: "+ New unit",
  emptyStateText: "No organization unit (Division / BU or Team) configured yet.",
  pedagogyTitle: "Reference: Division / Sub-BU, Team, and Workspace",
  pedagogyBuSummary:
    "Division / BU & Sub-BU: management hierarchy and rule inheritance scope.",
  pedagogyTeamSummary:
    "Team: human working collective and FinOps billing center for AI calls.",
  pedagogyWorkspaceSummary:
    "Workspace: business or product space attached to a team, created and managed in My Spaces.",
  openWorkspacesCta: "Open My Spaces →",
  unknownUserError:
    "The entered identifier does not match any active known user on the platform.",
  noMatchingKnownUser: "No matching user found.",
  selectKnownUserHint:
    "Search by name, principal ID, or email address to select an active account.",
  badges: {
    rootBu: "Division / BU",
    subBu: "Sub-Division / Sub-BU",
    team: "TEAM",
    billingActive: "FinOps billing active",
    billingDisabled: "FinOps billing disabled",
    leadPrefix: "Lead:",
    rootAttachment: "Root — Entire platform",
    parentAttachmentPrefix: "Attached to:",
  },
  nouns: {
    memberSingular: "member",
    memberPlural: "members",
    workspaceSingular: "workspace",
    workspacePlural: "workspaces",
    childUnitSingular: "sub-unit",
    childUnitPlural: "sub-units",
    childTeamSingular: "attached Team",
    childTeamPlural: "attached Teams",
  },
  rowActions: {
    edit: "Edit",
    members: "Members",
    delete: "Delete",
  },
};
