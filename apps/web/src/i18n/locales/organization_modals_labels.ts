export interface OrganizationCreateModalLabels {
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
  readonly ontologyLeadLabel: string;
  readonly ontologyLeadPlaceholder: string;
  readonly cancelButton: string;
  readonly submitButton: string;
}

export interface OrganizationEditModalLabels {
  readonly title: string;
  readonly description: string;
  readonly nameLabel: string;
  readonly parentLabel: string;
  readonly parentSearchPlaceholder: string;
  readonly parentNoMatchLabel: string;
  readonly parentTruncatedHint: string;
  readonly rootParentOption: string;
  readonly billingCheckboxLabel: string;
  readonly leadLabel: string;
  readonly leadPlaceholder: string;
  readonly ontologyLeadLabel: string;
  readonly ontologyLeadPlaceholder: string;
  readonly cancelButton: string;
  readonly saveButton: string;
}

export interface OrganizationInviteModalLabels {
  readonly title: string;
  readonly description: string;
  readonly targetUnitLabel: string;
  readonly emailLabel: string;
  readonly emailPlaceholder: string;
  readonly displayNameLabel: string;
  readonly displayNamePlaceholder: string;
  readonly roleLabel: string;
  readonly roleOptions: {
    readonly TEAM_MEMBER: string;
    readonly OBSERVER: string;
    readonly TEAM_LEAD: string;
    readonly BU_LEAD: string;
    readonly ONTOLOGY_LEAD: string;
  };
  readonly securityHint: string;
  readonly cancelButton: string;
  readonly submitButton: string;
}

export interface OrganizationMembersModalLabels {
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
  readonly memberTruncatedHint: string;
  readonly newMemberButtonLabel: string;
  readonly newMemberCreatedFeedback: string;
}

export interface OrganizationDeleteModalLabels {
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
}

export interface OrganizationModalsSection {
  readonly createModal: OrganizationCreateModalLabels;
  readonly editModal: OrganizationEditModalLabels;
  readonly membersModal: OrganizationMembersModalLabels;
  readonly deleteModal: OrganizationDeleteModalLabels;
  readonly inviteModal: OrganizationInviteModalLabels;
}

export const ORGANIZATION_MODALS_FR_LABELS: OrganizationModalsSection = {
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
    leadPlaceholder: "Rechercher un membre par nom (ex. : Claire Martin)...",
    ontologyLeadLabel: "Référent(s) Glossaire de la BU (optionnel)",
    ontologyLeadPlaceholder: "Rechercher un référent glossaire par nom ou e-mail...",
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
    leadLabel: "Responsable(s) de l'unité",
    leadPlaceholder: "Rechercher par nom, identifiant ou e-mail...",
    ontologyLeadLabel: "Référent(s) Glossaire (BU uniquement)",
    ontologyLeadPlaceholder: "Rechercher un référent glossaire par nom ou e-mail...",
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
    leadPlaceholder: "Rechercher un membre par nom (ex. : Claire Martin)...",
    clearLeadButton: "Effacer le responsable",
    addMemberLabel: "Ajouter un membre à l'unité",
    addMemberPlaceholder: "Rechercher un collaborateur par nom...",
    addMemberButton: "+ Ajouter le membre",
    membersListTitle: "Membres rattachés",
    emptyMembersText: "Aucun membre rattaché à cette unité pour le moment.",
    removeMemberButton: "Retirer",
    cancelButton: "Annuler",
    saveButton: "Enregistrer les membres",
    memberTruncatedHint: "collaborateurs non affichés. Saisissez des lettres pour affiner.",
    newMemberButtonLabel: "+ Nouveau membre",
    newMemberCreatedFeedback: "Nouveau membre créé et rattaché avec succès.",
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
  inviteModal: {
    title: "Inviter un utilisateur dans mon périmètre",
    description:
      "Créez un compte collaborateur et rattachez-le immédiatement à une unité de votre périmètre.",
    targetUnitLabel: "Unité cible (Direction / BU ou Équipe)",
    emailLabel: "Adresse e-mail professionnelle",
    emailPlaceholder: "Ex. : camille.laurent@entreprise.fr",
    displayNameLabel: "Nom complet",
    displayNamePlaceholder: "Ex. : Camille Laurent",
    roleLabel: "Rôle attribué sur l'unité",
    roleOptions: {
      TEAM_MEMBER: "Membre d'Équipe (Contributeur)",
      OBSERVER: "Observateur (Lecture seule)",
      TEAM_LEAD: "Responsable d'Équipe",
      BU_LEAD: "Co-responsable de Direction (BU)",
      ONTOLOGY_LEAD: "Référent Glossaire (BU)",
    },
    securityHint:
      "Délégation bornée : seuls les rôles opérationnels de votre périmètre peuvent être attribués (jamais PLATFORM_ADMIN ni SECOPS).",
    cancelButton: "Annuler",
    submitButton: "+ Inviter et rattacher",
  },
};

export const ORGANIZATION_MODALS_EN_LABELS: OrganizationModalsSection = {
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
    leadPlaceholder: "Search directory member by name (e.g. Claire Martin)...",
    ontologyLeadLabel: "BU Glossary Lead(s) (optional)",
    ontologyLeadPlaceholder: "Search glossary lead by name or email...",
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
    leadLabel: "Unit lead(s)",
    leadPlaceholder: "Search by name, principal ID, or email...",
    ontologyLeadLabel: "Glossary Lead(s) (BU only)",
    ontologyLeadPlaceholder: "Search glossary lead by name or email...",
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
    leadPlaceholder: "Search directory member by name (e.g. Claire Martin)...",
    clearLeadButton: "Clear lead",
    addMemberLabel: "Add a member to this unit",
    addMemberPlaceholder: "Search collaborator by name...",
    addMemberButton: "+ Add member",
    membersListTitle: "Attached members",
    emptyMembersText: "No member attached to this unit yet.",
    removeMemberButton: "Remove",
    cancelButton: "Cancel",
    saveButton: "Save members",
    memberTruncatedHint: "members hidden. Type letters to narrow down.",
    newMemberButtonLabel: "+ New member",
    newMemberCreatedFeedback: "New member created and attached successfully.",
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
  inviteModal: {
    title: "Invite a user within my scope",
    description:
      "Create a collaborator account and immediately attach it to a unit in your scope.",
    targetUnitLabel: "Target unit (Division / BU or Team)",
    emailLabel: "Work email address",
    emailPlaceholder: "e.g. camille.laurent@company.com",
    displayNameLabel: "Full name",
    displayNamePlaceholder: "e.g. Camille Laurent",
    roleLabel: "Role assigned on this unit",
    roleOptions: {
      TEAM_MEMBER: "Team Member (Contributor)",
      OBSERVER: "Observer (Read-only)",
      TEAM_LEAD: "Team Lead",
      BU_LEAD: "Co-Division Lead (BU)",
      ONTOLOGY_LEAD: "Glossary Lead (BU)",
    },
    securityHint:
      "Scoped delegation: only operational roles within your subtree can be assigned (never PLATFORM_ADMIN or SECOPS).",
    cancelButton: "Cancel",
    submitButton: "+ Invite & attach",
  },
};
