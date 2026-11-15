export interface IamDirectoryLabels {
  readonly sectionTitle: string;
  readonly sectionSubtitle: string;
  readonly createAccountCta: string;
  readonly openRoleMatrixCta: string;
  readonly emptyText: string;
  readonly humanBadge: string;
  readonly servicePrincipalBadge: string;
  readonly authLocalBootstrap: string;
  readonly authFederated: string;
  readonly authServiceToken: string;
  readonly statusActive: string;
  readonly statusInvited: string;
  readonly statusDisabled: string;
  readonly teamsPrefix: string;
  readonly noTeamsAssigned: string;
  readonly editButton: string;
  readonly resetPasswordButton: string;
  readonly deleteButton: string;
  readonly modalCreateTitle: string;
  readonly modalEditTitle: string;
  readonly modalDescription: string;
  readonly kindLabel: string;
  readonly kindHumanOption: string;
  readonly kindServicePrincipalOption: string;
  readonly displayNameLabel: string;
  readonly displayNamePlaceholder: string;
  readonly emailOrPrincipalLabel: string;
  readonly emailPlaceholder: string;
  readonly principalSpPlaceholder: string;
  readonly statusLabel: string;
  readonly rolesFieldsetLabel: string;
  readonly rolesHelperText: string;
  readonly teamsFieldsetLabel: string;
  readonly noTeamsAvailableHint: string;
  readonly ledBusFieldsetLabel: string;
  readonly ledBusFieldsetHint: string;
  readonly noBusAvailableHint: string;
  readonly ledTeamsFieldsetLabel: string;
  readonly ledTeamsFieldsetHint: string;
  readonly ledBusPrefix: string;
  readonly ledBusPluralPrefix: string;
  readonly noLedBusAssigned: string;
  readonly ledTeamSingularPrefix: string;
  readonly ledTeamsPluralPrefix: string;
  readonly noLedTeamsAssigned: string;
  readonly memberTeamSingularPrefix: string;
  readonly memberTeamsPluralPrefix: string;
  readonly cancelButton: string;
  readonly saveCreateButton: string;
  readonly saveEditButton: string;
}

export const IAM_DIRECTORY_FR_LABELS: IamDirectoryLabels = {
  sectionTitle: "1. Annuaire des Comptes & Attribution des Rôles",
  sectionSubtitle:
    "Gérez les comptes utilisateurs humains et techniques, leurs rôles officiels et leur rattachement aux équipes.",
  createAccountCta: "+ Nouveau compte",
  openRoleMatrixCta: "Consulter la matrice des 6 rôles",
  emptyText: "Aucun compte enregistré dans l'annuaire.",
  humanBadge: "Utilisateur",
  servicePrincipalBadge: "Compte technique",
  authLocalBootstrap: "Compte initial local",
  authFederated: "SSO d'entreprise",
  authServiceToken: "Jeton de service",
  statusActive: "Actif",
  statusInvited: "Invité",
  statusDisabled: "Désactivé",
  teamsPrefix: "Équipes :",
  noTeamsAssigned: "Aucune équipe rattachée",
  editButton: "Modifier",
  resetPasswordButton: "Mot de passe", // pragma: allowlist secret
  deleteButton: "Supprimer",
  modalCreateTitle: "Créer ou inviter un compte",
  modalEditTitle: "Modifier les rôles et équipes du compte",
  modalDescription:
    "Sélectionnez strictement parmi les 6 rôles officiels de la plateforme. Au moins un Administrateur Plateforme actif est garanti à tout moment.",
  kindLabel: "Nature du compte",
  kindHumanOption: "Utilisateur humain",
  kindServicePrincipalOption: "Compte technique (service)",
  displayNameLabel: "Nom complet ou libellé du service",
  displayNamePlaceholder: "Ex. : Claire Martin, Connecteur Sync...",
  emailOrPrincipalLabel: "Adresse e-mail ou identifiant technique",
  emailPlaceholder: "Ex. : prenom.nom",
  principalSpPlaceholder: "Ex. : sp-indexing-worker",
  statusLabel: "Statut du compte",
  rolesFieldsetLabel: "Rôles officiels attribués (liste fermée)",
  rolesHelperText:
    "Un compte peut cumuler plusieurs rôles (ex. : Administrateur Plateforme + Responsable Sécurité au démarrage, dissociables ultérieurement).",
  teamsFieldsetLabel: "Équipes rattachées (membre)",
  noTeamsAvailableHint: "Aucune équipe n'est encore créée dans l'onglet Organisation.",
  ledBusFieldsetLabel: "Directions (BU) supervisées",
  ledBusFieldsetHint:
    "Sélectionnez les Directions / BUs dont ce compte est responsable. Vous pouvez également créer le compte avant de rattacher les BUs.",
  noBusAvailableHint: "Aucune Direction (BU) n'est encore créée dans l'onglet Organisation.",
  ledTeamsFieldsetLabel: "Équipes dirigées",
  ledTeamsFieldsetHint: "Sélectionnez les équipes dont ce compte est responsable.",
  ledBusPrefix: "Direction (BU) :",
  ledBusPluralPrefix: "Directions (BU) :",
  noLedBusAssigned: "aucune assignée",
  ledTeamSingularPrefix: "Équipe dirigée :",
  ledTeamsPluralPrefix: "Équipes dirigées :",
  noLedTeamsAssigned: "aucune assignée",
  memberTeamSingularPrefix: "Équipe :",
  memberTeamsPluralPrefix: "Équipes :",
  cancelButton: "Annuler",
  saveCreateButton: "+ Enregistrer le compte",
  saveEditButton: "Enregistrer les modifications",
};

export const IAM_DIRECTORY_EN_LABELS: IamDirectoryLabels = {
  sectionTitle: "1. Accounts Directory & Role Assignment",
  sectionSubtitle:
    "Manage human user accounts and technical service accounts, their official roles, and team memberships.",
  createAccountCta: "+ New account",
  openRoleMatrixCta: "View 6-role matrix",
  emptyText: "No account registered in the directory.",
  humanBadge: "User",
  servicePrincipalBadge: "Service account",
  authLocalBootstrap: "Initial local account",
  authFederated: "Enterprise SSO",
  authServiceToken: "Service token",
  statusActive: "Active",
  statusInvited: "Invited",
  statusDisabled: "Disabled",
  teamsPrefix: "Teams:",
  noTeamsAssigned: "No team assigned",
  editButton: "Edit",
  resetPasswordButton: "Password", // pragma: allowlist secret
  deleteButton: "Delete",
  modalCreateTitle: "Create or invite an account",
  modalEditTitle: "Edit account roles and teams",
  modalDescription:
    "Select strictly from the 6 official platform roles. At least one active Platform Administrator is enforced at all times.",
  kindLabel: "Account type",
  kindHumanOption: "Human user",
  kindServicePrincipalOption: "Technical service account",
  displayNameLabel: "Full name or service label",
  displayNamePlaceholder: "e.g. Claire Martin, Sync Connector...",
  emailOrPrincipalLabel: "Email address or service identifier",
  emailPlaceholder: "e.g. firstname.lastname",
  principalSpPlaceholder: "e.g. sp-indexing-worker",
  statusLabel: "Account status",
  rolesFieldsetLabel: "Assigned official roles (closed list)",
  rolesHelperText:
    "An account may hold multiple roles (e.g. Platform Administrator + Security Officer at initial setup, separable later).",
  teamsFieldsetLabel: "Assigned teams (member)",
  noTeamsAvailableHint: "No team has been created yet in the Organization tab.",
  ledBusFieldsetLabel: "Supervised Divisions (BU)",
  ledBusFieldsetHint:
    "Select Divisions / BUs supervised by this account. You can also create the account before attaching BUs.",
  noBusAvailableHint: "No Division (BU) has been created yet in the Organization tab.",
  ledTeamsFieldsetLabel: "Led teams",
  ledTeamsFieldsetHint: "Select teams led by this account.",
  ledBusPrefix: "Division (BU):",
  ledBusPluralPrefix: "Divisions (BU):",
  noLedBusAssigned: "none assigned",
  ledTeamSingularPrefix: "Led team:",
  ledTeamsPluralPrefix: "Led teams:",
  noLedTeamsAssigned: "none assigned",
  memberTeamSingularPrefix: "Team:",
  memberTeamsPluralPrefix: "Teams:",
  cancelButton: "Cancel",
  saveCreateButton: "+ Save account",
  saveEditButton: "Save changes",
};
