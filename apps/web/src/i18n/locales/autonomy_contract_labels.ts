import type { AutonomyContractModalLabels } from "@orcia/ui";

export interface AutonomyContractStudioCopy {
  readonly openModalButton: string;
  readonly activeBadgeLabel: string;
  readonly signedSuccessBanner: string;
  readonly revokedSuccessBanner: string;
  readonly loadErrorBanner: string;
  readonly modal: AutonomyContractModalLabels;
  readonly signerRoleLabels: {
    readonly TEAM_LEAD: string;
    readonly BU_LEAD: string;
    readonly PLATFORM_ADMIN: string;
  };
}

export const AUTONOMY_CONTRACT_FR_LABELS: AutonomyContractStudioCopy = {
  openModalButton: "Contrat d'autonomie",
  activeBadgeLabel: "Autonomie signée",
  signedSuccessBanner: "Contrat d'autonomie signé et activé pour ce processus.",
  revokedSuccessBanner: "Contrat d'autonomie révoqué immédiatement.",
  loadErrorBanner: "Impossible de charger le contrat d'autonomie pour cet espace.",
  signerRoleLabels: {
    TEAM_LEAD: "Responsable d'équipe",
    BU_LEAD: "Directeur de pôle",
    PLATFORM_ADMIN: "Administrateur plateforme",
  },
  modal: {
    title: "Contrat d'autonomie",
    description:
      "Définissez le compte de service, les sources autorisées et le plafond budgétaire pour une exécution autonome encadrée.",
    helpButtonLabel: "Comprendre le contrat d'autonomie",
    activeBannerTitle: "Contrat actif",
    signerRolePrefix: "Signé par :",
    serviceAccountLabel: "Compte de service habilité sur cet espace",
    serviceAccountEmptyHint:
      "Aucun compte de service actif n'est encore rattaché à cet espace. Créez-en un dans Mes Espaces › Comptes et accès.",
    readSourcesLabel: "Sources de lecture autorisées",
    writeActionsLabel: "Actions d'écriture autorisées",
    maxCostLabel: "Plafond budgétaire par exécution (USD)",
    tieBreakPolicyLabel: "Règle en cas d'ambiguïté",
    tieBreakOntologyFirst: "Suivre les règles de référence de l'organisation",
    tieBreakDeferAssumption: "Noter une hypothèse explicite et poursuivre",
    tieBreakPauseEscalate: "Suspendre et demander un arbitrage humain",
    criticalBlockedNotice:
      "Ce processus critique exige une validation humaine explicite et ne peut pas être automatisé sans supervision.",
    signButton: "Signer le contrat d'autonomie",
    signingButton: "Signature en cours...",
    revokeButton: "Révoquer le contrat",
    closeButton: "Fermer",
  },
};

export const AUTONOMY_CONTRACT_EN_LABELS: AutonomyContractStudioCopy = {
  openModalButton: "Autonomy contract",
  activeBadgeLabel: "Signed autonomy",
  signedSuccessBanner: "Autonomy contract signed and activated for this process.",
  revokedSuccessBanner: "Autonomy contract immediately revoked.",
  loadErrorBanner: "Unable to load the autonomy contract for this workspace.",
  signerRoleLabels: {
    TEAM_LEAD: "Team Lead",
    BU_LEAD: "Division Lead",
    PLATFORM_ADMIN: "Platform Administrator",
  },
  modal: {
    title: "Autonomy contract",
    description:
      "Configure the service account, allowed sources, and budget ceiling for governed autonomous execution.",
    helpButtonLabel: "Understand the autonomy contract",
    activeBannerTitle: "Active contract",
    signerRolePrefix: "Signed by:",
    serviceAccountLabel: "Authorized service account on this workspace",
    serviceAccountEmptyHint:
      "No active service account is scoped to this workspace yet. Provision one in My Spaces › Accounts & Access.",
    readSourcesLabel: "Allowed read sources",
    writeActionsLabel: "Allowed write actions",
    maxCostLabel: "Budget ceiling per run (USD)",
    tieBreakPolicyLabel: "Rule when ambiguity arises",
    tieBreakOntologyFirst: "Follow organization reference rules first",
    tieBreakDeferAssumption: "Record an explicit assumption and continue",
    tieBreakPauseEscalate: "Pause and request human arbitration",
    criticalBlockedNotice:
      "This critical process requires explicit human approval and cannot run unsupervised.",
    signButton: "Sign autonomy contract",
    signingButton: "Signing...",
    revokeButton: "Revoke contract",
    closeButton: "Close",
  },
};
