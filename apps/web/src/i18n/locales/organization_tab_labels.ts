export interface OrganizationTabDictionarySection {
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
  readonly createModal: {
    readonly title: string;
    readonly description: string;
    readonly kindLabel: string;
    readonly kindBuOption: string;
    readonly kindTeamOption: string;
    readonly nameLabel: string;
    readonly nameBuPlaceholder: string;
    readonly nameTeamPlaceholder: string;
    readonly slugLabel: string;
    readonly slugPlaceholder: string;
    readonly parentLabel: string;
    readonly parentSearchPlaceholder: string;
    readonly parentNoMatchLabel: string;
    readonly parentTruncatedHint: string;
    readonly rootParentOption: string;
    readonly parentBuOptionPrefix: string;
    readonly billingCheckboxLabel: string;
    readonly leadLabel: string;
    readonly leadPlaceholder: string;
    readonly cancelButton: string;
    readonly submitButton: string;
  };
  readonly editModal: {
    readonly title: string;
    readonly description: string;
    readonly nameLabel: string;
    readonly parentLabel: string;
    readonly parentSearchPlaceholder: string;
    readonly parentNoMatchLabel: string;
    readonly parentTruncatedHint: string;
    readonly rootParentOption: string;
    readonly billingCheckboxLabel: string;
    readonly cancelButton: string;
    readonly saveButton: string;
  };
  readonly membersModal: {
    readonly titlePrefix: string;
    readonly description: string;
    readonly leadLabel: string;
    readonly leadBuHint: string;
    readonly leadTeamHint: string;
    readonly leadPlaceholder: string;
    readonly clearLeadButton: string;
    readonly addMemberLabel: string;
    readonly addMemberPlaceholder: string;
    readonly addMemberButton: string;
    readonly membersListTitle: string;
    readonly emptyMembersText: string;
    readonly removeMemberButton: string;
    readonly cancelButton: string;
    readonly saveButton: string;
  };
  readonly deleteModal: {
    readonly titlePrefix: string;
    readonly description: string;
    readonly finopsWarningText: string;
    readonly blockedNonEmptyTitle: string;
    readonly blockedNonEmptyHint: string;
    readonly deleteDependenciesHeading: string;
    readonly deleteDependencySubUnitPrefix: string;
    readonly deleteDependencyWorkspacePrefix: string;
    readonly deleteOpenWorkspacesAction: string;
    readonly cancelButton: string;
    readonly confirmDeleteButton: string;
  };
  readonly unknownUserError: string;
  readonly noMatchingKnownUser: string;
  readonly selectKnownUserHint: string;
}

export const ORGANIZATION_TAB_FR_LABELS: OrganizationTabDictionarySection = {
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
  createModal: {
    title: "Créer une unité organisationnelle",
    description:
      "Ajoutez une Direction (BU), un Pôle / Sous-BU ou une Équipe dans l'arborescence de la plateforme.",
    kindLabel: "Type d'unité",
    kindBuOption: "Direction / Pôle (BU)",
    kindTeamOption: "Équipe",
    nameLabel: "Nom de l'unité",
    nameBuPlaceholder: "Ex. : Direction Produit, Pôle Paiements...",
    nameTeamPlaceholder: "Ex. : Équipe Core IA, Équipe Conformité...",
    slugLabel: "Identifiant court (optionnel)",
    slugPlaceholder: "Généré automatiquement si laissé vide (ex. : direction-produit)",
    parentLabel: "Unité parente de rattachement",
    parentSearchPlaceholder: "Rechercher une organisation parente...",
    parentNoMatchLabel: "Aucune organisation trouvée",
    parentTruncatedHint: "organisations non affichées. Saisissez des lettres pour affiner.",
    rootParentOption: "Racine — Direction de premier niveau (Plateforme entière)",
    parentBuOptionPrefix: "Direction / Pôle :",
    billingCheckboxLabel: "Activer l'imputation FinOps sur cette unité",
    leadLabel: "Responsable de l'unité (optionnel)",
    leadPlaceholder: "Identifiant ou e-mail du responsable (ex. : claire.martin@entreprise.fr)",
    cancelButton: "Annuler",
    submitButton: "+ Créer l'unité",
  },
  editModal: {
    title: "Modifier l'unité organisationnelle",
    description:
      "Mettez à jour le nom, le rattachement hiérarchique ou le statut d'imputation FinOps.",
    nameLabel: "Nom de l'unité",
    parentLabel: "Unité parente de rattachement",
    parentSearchPlaceholder: "Rechercher une organisation parente...",
    parentNoMatchLabel: "Aucune organisation trouvée",
    parentTruncatedHint: "organisations non affichées. Saisissez des lettres pour affiner.",
    rootParentOption: "Racine — Direction de premier niveau (Plateforme entière)",
    billingCheckboxLabel: "Activer l'imputation FinOps sur cette unité",
    cancelButton: "Annuler",
    saveButton: "Enregistrer les modifications",
  },
  membersModal: {
    titlePrefix: "Gouvernance & Membres —",
    description:
      "Désignez le responsable de l'unité et gérez la liste des comptes membres rattachés.",
    leadLabel: "Responsable de l'unité",
    leadBuHint: "Responsable de Direction / Pôle (supervision BU)",
    leadTeamHint: "Responsable d'Équipe (supervision d'équipe & budget)",
    leadPlaceholder: "Identifiant ou e-mail du responsable...",
    clearLeadButton: "Effacer le responsable",
    addMemberLabel: "Ajouter un membre à l'unité",
    addMemberPlaceholder: "Identifiant ou e-mail du collaborateur...",
    addMemberButton: "+ Ajouter le membre",
    membersListTitle: "Membres rattachés",
    emptyMembersText: "Aucun membre rattaché à cette unité pour le moment.",
    removeMemberButton: "Retirer",
    cancelButton: "Annuler",
    saveButton: "Enregistrer les membres",
  },
  deleteModal: {
    titlePrefix: "Supprimer l'unité —",
    description:
      "Cette opération retire définitivement l'unité de l'organigramme si aucune sous-unité ni aucun espace n'y sont rattachés.",
    finopsWarningText:
      "Attention FinOps : l'imputation FinOps est active sur cette unité. Vérifiez qu'aucun budget ou suivi de coûts en cours ne dépend de ce centre d'imputation avant de confirmer.",
    blockedNonEmptyTitle: "Suppression impossible : unité non vide",
    blockedNonEmptyHint:
      "Déplacez ou supprimez les éléments listés ci-dessus avant de confirmer la suppression.",
    deleteDependenciesHeading: "Éléments rattachés à déplacer ou supprimer :",
    deleteDependencySubUnitPrefix: "Sous-unité",
    deleteDependencyWorkspacePrefix: "Espace",
    deleteOpenWorkspacesAction: "Gérer les espaces rattachés",
    cancelButton: "Annuler",
    confirmDeleteButton: "Confirmer la suppression",
  },
};

export const ORGANIZATION_TAB_EN_LABELS: OrganizationTabDictionarySection = {
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
  createModal: {
    title: "Create an organizational unit",
    description:
      "Add a Division (BU), a Sub-Division / Sub-BU, or a Team into the platform hierarchy.",
    kindLabel: "Unit type",
    kindBuOption: "Division / Sub-BU (BU)",
    kindTeamOption: "Team",
    nameLabel: "Unit name",
    nameBuPlaceholder: "e.g. Product Division, Payments Sub-BU...",
    nameTeamPlaceholder: "e.g. Core AI Team, Compliance Team...",
    slugLabel: "Short identifier (optional)",
    slugPlaceholder: "Auto-generated if left blank (e.g. product-division)",
    parentLabel: "Parent unit",
    parentSearchPlaceholder: "Search parent organization...",
    parentNoMatchLabel: "No organization found",
    parentTruncatedHint: "organizations hidden. Type letters to narrow down.",
    rootParentOption: "Root — Top-level Division (Entire platform)",
    parentBuOptionPrefix: "Division / Sub-BU:",
    billingCheckboxLabel: "Enable FinOps cost allocation on this unit",
    leadLabel: "Unit lead (optional)",
    leadPlaceholder: "Lead user ID or email (e.g. claire.martin@company.com)",
    cancelButton: "Cancel",
    submitButton: "+ Create unit",
  },
  editModal: {
    title: "Edit organizational unit",
    description:
      "Update the unit name, parent hierarchy attachment, or FinOps billing status.",
    nameLabel: "Unit name",
    parentLabel: "Parent unit",
    parentSearchPlaceholder: "Search parent organization...",
    parentNoMatchLabel: "No organization found",
    parentTruncatedHint: "organizations hidden. Type letters to narrow down.",
    rootParentOption: "Root — Top-level Division (Entire platform)",
    billingCheckboxLabel: "Enable FinOps cost allocation on this unit",
    cancelButton: "Cancel",
    saveButton: "Save changes",
  },
  membersModal: {
    titlePrefix: "Governance & Members —",
    description:
      "Assign the unit lead and manage the list of attached member accounts.",
    leadLabel: "Unit lead",
    leadBuHint: "Division / Sub-BU Lead (BU supervision)",
    leadTeamHint: "Team Lead (team & budget supervision)",
    leadPlaceholder: "Lead user ID or email...",
    clearLeadButton: "Clear lead",
    addMemberLabel: "Add a member to this unit",
    addMemberPlaceholder: "Teammate user ID or email...",
    addMemberButton: "+ Add member",
    membersListTitle: "Attached members",
    emptyMembersText: "No member attached to this unit yet.",
    removeMemberButton: "Remove",
    cancelButton: "Cancel",
    saveButton: "Save members",
  },
  deleteModal: {
    titlePrefix: "Delete unit —",
    description:
      "This permanently removes the unit from the organization tree if no child unit or workspace is attached.",
    finopsWarningText:
      "FinOps Warning: FinOps billing is enabled on this unit. Ensure no active budget or cost tracking depends on this billing center before confirming.",
    blockedNonEmptyTitle: "Deletion blocked: unit is not empty",
    blockedNonEmptyHint:
      "Move or delete the items listed above before confirming deletion.",
    deleteDependenciesHeading: "Attached items to move or delete:",
    deleteDependencySubUnitPrefix: "Sub-unit",
    deleteDependencyWorkspacePrefix: "Workspace",
    deleteOpenWorkspacesAction: "Manage attached workspaces",
    cancelButton: "Cancel",
    confirmDeleteButton: "Confirm delete",
  },
};
