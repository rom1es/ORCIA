export interface ShellScopeOptionsLabels {
  readonly groupPrivateSuffix: string;
  readonly groupTeamUnitSuffix: string;
  readonly groupSharedWorkspacePrefix: string;
  readonly groupSharedWorkspaceSuffix: string;
  readonly groupSupervisionSuffix: string;
  readonly privateSpacePrefix: string;
  readonly teamPrefix: string;
  readonly sharedSpacePrefix: string;
  readonly buPrefix: string;
  readonly personalGroupLabel: string;
  readonly otherSpacesGroupLabel: string;
  readonly allMySpacesOption: string;
  readonly workspaceLabel: string;
  readonly disabledReasons: {
    readonly adminMissing: string;
    readonly assistant: string;
    readonly agents: string;
    readonly processes: string;
    readonly finops: string;
  };
}

export const SHELL_SCOPE_OPTIONS_FR: ShellScopeOptionsLabels = {
  groupPrivateSuffix: "Mes Espaces Privés",
  groupTeamUnitSuffix: "Mes Équipes & Espaces · Équipe",
  groupSharedWorkspacePrefix: "Espace ·",
  groupSharedWorkspaceSuffix: "Mes Équipes & Espaces",
  groupSupervisionSuffix: "Supervision Organisation",
  privateSpacePrefix: "Espace privé · ",
  teamPrefix: "Équipe · ",
  sharedSpacePrefix: "Espace · ",
  buPrefix: "Direction (BU) · ",
  personalGroupLabel: "Personnel",
  otherSpacesGroupLabel: "Autres espaces",
  allMySpacesOption: "Tous mes espaces",
  workspaceLabel: "Espace actif",
  disabledReasons: {
    adminMissing: "Créez d'abord le premier compte Administrateur pour accéder à cette section.",
    assistant:
      "Configurez au moins un modèle IA et rattachez une Équipe de facturation dans Administration pour activer Mon Assistant.",
    agents:
      "Configurez un modèle IA ou activez un Pack et rattachez une Équipe de facturation dans Administration pour déverrouiller Mes Agents.",
    processes:
      "Créez un Espace de Travail rattaché à une Équipe de facturation et configurez un modèle IA pour activer Mes Processus.",
    finops:
      "Configurez un modèle IA ou créez un Espace de Travail rattaché à une Équipe pour consulter le suivi des coûts.",
  },
};

export const SHELL_SCOPE_OPTIONS_EN: ShellScopeOptionsLabels = {
  groupPrivateSuffix: "My Private Spaces",
  groupTeamUnitSuffix: "My Teams & Spaces · Team",
  groupSharedWorkspacePrefix: "Workspace ·",
  groupSharedWorkspaceSuffix: "My Teams & Spaces",
  groupSupervisionSuffix: "Organization Supervision",
  privateSpacePrefix: "Private workspace · ",
  teamPrefix: "Team · ",
  sharedSpacePrefix: "Workspace · ",
  buPrefix: "Division (BU) · ",
  personalGroupLabel: "Personal",
  otherSpacesGroupLabel: "Other spaces",
  allMySpacesOption: "All my spaces",
  workspaceLabel: "Active space",
  disabledReasons: {
    adminMissing: "Create the first Administrator account first to access this section.",
    assistant:
      "Configure at least one AI model and attach a billing Team in Administration to enable My Assistant.",
    agents:
      "Configure an AI model or enable a Pack and attach a billing Team in Administration to unlock My Agents.",
    processes:
      "Create a Workspace attached to a billing Team and configure an AI model to enable My Processes.",
    finops:
      "Configure an AI model or create a Workspace attached to a Team to view cost tracking.",
  },
};

export const SHELL_SCOPE_OPTIONS_BY_LOCALE: Readonly<Record<"fr" | "en", ShellScopeOptionsLabels>> = {
  fr: SHELL_SCOPE_OPTIONS_FR,
  en: SHELL_SCOPE_OPTIONS_EN,
};
