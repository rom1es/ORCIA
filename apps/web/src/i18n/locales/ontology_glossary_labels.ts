import type { UiOntologyLevel } from "@orcia/ui";

export interface OntologyGlossaryCopy {
  readonly tabExplorer: string;
  readonly tabProposalsPrefix: string;
  readonly addSectionTitle: string;
  readonly addHelpLabel: string;
  readonly termPlaceholder: string;
  readonly defPlaceholder: string;
  readonly addButtonLabel: string;
  readonly addingLabel: string;
  readonly noWritableLevelBanner: string;
  readonly createdSuccessPrefix: string;
  readonly proposedSuccessPrefix: string;
  readonly decisionSuccessApproved: string;
  readonly decisionSuccessRejected: string;
  readonly errorFallback: string;
  readonly proposalsTitle: string;
  readonly proposalsSubtitle: string;
  readonly proposalsEmptyState: string;
  readonly proposeUpButtonLabel: string;
  readonly approveButtonLabel: string;
  readonly rejectButtonLabel: string;
  readonly collisionWarningPrefix: string;
  readonly existingDefinitionLabel: string;
  readonly proposalsMetaProposedBy: string;
  readonly proposalsMetaTarget: string;
  readonly proposalsCommentPlaceholder: string;
  readonly statusPending: string;
  readonly statusApproved: string;
  readonly statusRejected: string;
  readonly levelLabels: Record<UiOntologyLevel, string>;
  readonly helpCenterShowcaseTitle: string;
  readonly helpCenterShowcaseDesc: string;
  readonly helpCenterShowcaseBtnLabel: string;
  readonly helpCenterOverviewTitle: string;
  readonly helpCenterOverviewSummary: string;
  readonly helpCenterStep1: string;
  readonly helpCenterStep2: string;
  readonly helpCenterKeyTerm1: string;
  readonly helpCenterKeyTerm2: string;
  readonly helpCenterKeyTerm3: string;
  readonly helpCenterFaq1: string;
  readonly workspaceGlossaryTitlePrefix: string;
  readonly workspaceGlossaryDefaultPlatformName: string;
  readonly workspaceGlossaryHelpLabel: string;
  readonly workspaceGlossaryTermPlaceholder: string;
  readonly workspaceGlossaryDefPlaceholder: string;
  readonly workspaceGlossaryScopeLabel: string;
  readonly workspaceGlossarySubmitLabel: string;
  readonly workspaceGlossarySubmitDisabledReason: string;
  readonly workspaceGlossaryEmptyTier: string;
  readonly workspaceGlossaryProposedBadge: string;
  readonly workspaceGlossaryPromotedBadge: string;
  readonly workspaceGlossaryProposeTeamOrBu: string;
  readonly workspaceGlossaryProposeOrg: string;
  readonly workspaceGlossaryEnterpriseTitle: string;
  readonly workspaceGlossaryEnterpriseSub: string;
  readonly workspaceGlossaryDomainSub: string;
  readonly workspaceGlossaryTeamSub: string;
  readonly workspaceGlossaryWorkspaceSub: string;
}

export const ONTOLOGY_GLOSSARY_FR: OntologyGlossaryCopy = {
  tabExplorer: "Explorateur du Glossaire",
  tabProposalsPrefix: "Propositions à valider",
  addSectionTitle: "Ajouter un Terme Métier ou une Règle au Glossaire",
  addHelpLabel: "Comprendre le glossaire métier et les règles de l'organisation",
  termPlaceholder: "Intitulé du terme métier...",
  defPlaceholder: "Définition claire et partagée...",
  addButtonLabel: "+ Ajouter au glossaire",
  addingLabel: "Enregistrement...",
  noWritableLevelBanner:
    "Mode lecture seule ou périmètre sans droit d'écriture directe : vous pouvez consulter le glossaire ou proposer une promotion.",
  createdSuccessPrefix: "Terme enregistré dans le glossaire :",
  proposedSuccessPrefix: "Proposition de promotion soumise pour :",
  decisionSuccessApproved: "Proposition approuvée et terme publié au palier cible.",
  decisionSuccessRejected: "Proposition refusée.",
  errorFallback: "Une erreur est survenue lors de l'opération sur le glossaire.",
  proposalsTitle: "Propositions de promotion à valider",
  proposalsSubtitle:
    "Les propositions montent strictement palier par palier (Espace -> Équipe -> Direction -> Organisation).",
  proposalsEmptyState: "Aucune proposition de promotion en attente pour votre périmètre.",
  proposeUpButtonLabel: "Proposer au niveau supérieur",
  approveButtonLabel: "Approuver",
  rejectButtonLabel: "Refuser",
  collisionWarningPrefix: "Collision détectée au palier cible :",
  existingDefinitionLabel: "Définition existante au palier cible :",
  proposalsMetaProposedBy: "Proposé par :",
  proposalsMetaTarget: "Cible :",
  proposalsCommentPlaceholder: "Commentaire de validation ou motif de refus (optionnel)...",
  statusPending: "En attente de validation",
  statusApproved: "Approuvée",
  statusRejected: "Refusée",
  levelLabels: {
    "1_ENTERPRISE": "1. Organisation (Global)",
    "2_DOMAIN": "2. Direction / Pôle (BU)",
    "3_TEAM": "3. Équipe",
    "3_WORKSPACE": "4. Espace de Travail",
    "4_WORKSPACE": "4. Espace de Travail",
    "4_RUN_EPHEMERAL": "Exécution en cours",
  },
  helpCenterShowcaseTitle: "Site de Présentation & Documentation Vivante d'ORCIA",
  helpCenterShowcaseDesc:
    "Découvrez la vision Human-Led, la double barrière anti-hallucination, le guide des écrans et les choix d'architecture en 3 espaces séparés.",
  helpCenterShowcaseBtnLabel: "Documentation",
  helpCenterOverviewTitle: "Centre d'Aide Contextuelle & Guides Pratiques",
  helpCenterOverviewSummary:
    "Ce centre rassemble les guides pratiques et explications rattachés à vos écrans et à vos Packs métiers.",
  helpCenterStep1:
    "Ouvrez la colonne d'aide ou cliquez sur une icône d'information sur n'importe quel écran pour afficher l'explication dédiée.",
  helpCenterStep2:
    "Utilisez l'outil de création de fiches d'aide dans Mes Processus pour rédiger et publier de nouveaux guides pour vos équipes.",
  helpCenterKeyTerm1: "Fiche de référence : Guide officiel associé à un écran.",
  helpCenterKeyTerm2: "Adaptation par niveau : Guides enrichis par votre métier et votre Espace.",
  helpCenterKeyTerm3: "Vérification de qualité : Contrôle automatique des liens et du vocabulaire.",
  helpCenterFaq1:
    "Comment rétablir la version précédente d'un guide ? Cliquez sur Version précédente.",
  workspaceGlossaryTitlePrefix: "Glossaire & Règles Métiers applicables à",
  workspaceGlossaryDefaultPlatformName: "Plateforme Globale ORCIA",
  workspaceGlossaryHelpLabel: "Comprendre l'héritage du glossaire et la promotion",
  workspaceGlossaryTermPlaceholder: "Nouveau terme ou règle métier (ex: Délai de franchise)...",
  workspaceGlossaryDefPlaceholder: "Définition claire ou consigne à respecter par les agents...",
  workspaceGlossaryScopeLabel: "Portée d'application du terme",
  workspaceGlossarySubmitLabel: "+ Ajouter au glossaire",
  workspaceGlossarySubmitDisabledReason:
    "Saisissez l'intitulé du terme ou de la règle métier pour l'ajouter au glossaire.",
  workspaceGlossaryEmptyTier: "Aucun terme défini à ce niveau.",
  workspaceGlossaryProposedBadge: "En attente de validation",
  workspaceGlossaryPromotedBadge: "Promu",
  workspaceGlossaryProposeTeamOrBu: "Proposer au niveau supérieur",
  workspaceGlossaryProposeOrg: "Proposer à l'Organisation",
  workspaceGlossaryEnterpriseTitle: "Entreprise (Global)",
  workspaceGlossaryEnterpriseSub: "Socle commun de l'organisation",
  workspaceGlossaryDomainSub: "Vocabulaire et règles de votre Direction",
  workspaceGlossaryTeamSub: "Termes partagés par l'équipe",
  workspaceGlossaryWorkspaceSub: "Termes spécifiques à cet espace",
};

export const ONTOLOGY_GLOSSARY_EN: OntologyGlossaryCopy = {
  tabExplorer: "Glossary Explorer",
  tabProposalsPrefix: "Proposals to review",
  addSectionTitle: "Add a Business Term or Rule to the Glossary",
  addHelpLabel: "Understand the business glossary and organization rules",
  termPlaceholder: "Business term name...",
  defPlaceholder: "Clear shared definition...",
  addButtonLabel: "+ Add to glossary",
  addingLabel: "Saving...",
  noWritableLevelBanner:
    "Read-only mode or scope without direct write permission: you can browse the glossary or propose a promotion.",
  createdSuccessPrefix: "Term saved to the glossary:",
  proposedSuccessPrefix: "Promotion proposal submitted for:",
  decisionSuccessApproved: "Proposal approved and term published to the target tier.",
  decisionSuccessRejected: "Proposal rejected.",
  errorFallback: "An error occurred while updating the glossary.",
  proposalsTitle: "Promotion proposals awaiting review",
  proposalsSubtitle:
    "Proposals progress strictly tier by tier (Workspace -> Team -> Division -> Organization).",
  proposalsEmptyState: "No promotion proposals pending for your scope.",
  proposeUpButtonLabel: "Propose to upper tier",
  approveButtonLabel: "Approve",
  rejectButtonLabel: "Reject",
  collisionWarningPrefix: "Collision detected at target tier:",
  existingDefinitionLabel: "Existing definition at target tier:",
  proposalsMetaProposedBy: "Proposed by:",
  proposalsMetaTarget: "Target:",
  proposalsCommentPlaceholder: "Review comment or rejection reason (optional)...",
  statusPending: "Pending review",
  statusApproved: "Approved",
  statusRejected: "Rejected",
  levelLabels: {
    "1_ENTERPRISE": "1. Organization (Global)",
    "2_DOMAIN": "2. Division / Department (BU)",
    "3_TEAM": "3. Team",
    "3_WORKSPACE": "4. Workspace",
    "4_WORKSPACE": "4. Workspace",
    "4_RUN_EPHEMERAL": "Current execution",
  },
  helpCenterShowcaseTitle: "ORCIA Living Product & Architecture Showcase Site",
  helpCenterShowcaseDesc:
    "Explore the Human-Led vision, double anti-hallucination barrier, screen guide, and engineering architecture across 3 separated spaces.",
  helpCenterShowcaseBtnLabel: "Documentation",
  helpCenterOverviewTitle: "Contextual Help Center & Practical Guides",
  helpCenterOverviewSummary:
    "This center gathers practical guides and explanations bound to your screens and Business Packs.",
  helpCenterStep1:
    "Open the help column or click an info icon on any screen to display the dedicated explanation.",
  helpCenterStep2:
    "Use the help guide authoring tool in My Processes to write and publish new guides for your teams.",
  helpCenterKeyTerm1: "Reference guide: Official guide linked to a screen.",
  helpCenterKeyTerm2: "Level customization: Guides enriched by your domain and Workspace.",
  helpCenterKeyTerm3: "Quality check: Automated verification of links and terminology.",
  helpCenterFaq1: "How can I restore the previous version of a guide? Click Previous version.",
  workspaceGlossaryTitlePrefix: "Business Glossary & Rules applicable to",
  workspaceGlossaryDefaultPlatformName: "Global Platform ORCIA",
  workspaceGlossaryHelpLabel: "Understand glossary inheritance and promotion",
  workspaceGlossaryTermPlaceholder: "New business term or rule...",
  workspaceGlossaryDefPlaceholder: "Clear definition or rule for agents...",
  workspaceGlossaryScopeLabel: "Term application scope",
  workspaceGlossarySubmitLabel: "+ Add to glossary",
  workspaceGlossarySubmitDisabledReason:
    "Enter the business term or rule name to add it to the glossary.",
  workspaceGlossaryEmptyTier: "No term defined at this level.",
  workspaceGlossaryProposedBadge: "Pending review",
  workspaceGlossaryPromotedBadge: "Promoted",
  workspaceGlossaryProposeTeamOrBu: "Propose to upper tier",
  workspaceGlossaryProposeOrg: "Propose to Organization",
  workspaceGlossaryEnterpriseTitle: "Enterprise (Global)",
  workspaceGlossaryEnterpriseSub: "Organization shared foundation",
  workspaceGlossaryDomainSub: "Division vocabulary & rules",
  workspaceGlossaryTeamSub: "Team shared terms",
  workspaceGlossaryWorkspaceSub: "Workspace-specific terms",
};
