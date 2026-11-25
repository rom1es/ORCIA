import { AGENT_GOVERNANCE_STUDIO_LABELS_FR } from "./agents_and_skills_studio_labels_fr";
import type { GovernanceAndPacksDictionarySection } from "./governance_and_packs_labels";

export const GOVERNANCE_AND_PACKS_FR_LABELS: GovernanceAndPacksDictionarySection = {
  workspaceFiveTabs: {
    heading: "Mes Espaces — Sources, Livrables, Glossaire & Équipe",
    tabOverview: "Vue d'ensemble",
    tabDocumentsSources: "Documents & Sources",
    tabDeliverablesArtifacts: "Livrables & Artefacts",
    tabGlossaryRules: "Glossaire & Règles Métiers",
    tabMembersTeam: "Membres & Équipe",
    defaultDestinationTitle: "Emplacement d'enregistrement des livrables :",
    roleReferenceBadge: "RÉFÉRENCE (Document officiel)",
    roleActiveBadge: "TRAVAIL EN COURS",
    modeReadOnlyBadge: "Consultation seule",
    modeReadWriteBadge: "Publication autorisée",
    waiverSectionTitle: "Adaptations et Dérogations Locales",
    inviolableEnterpriseLockNotice:
      "Les règles générales de l'organisation s'appliquent à tous les espaces et ne peuvent pas faire l'objet d'une dérogation locale.",
    externalRebaseTitle:
      "Prise en Compte des Modifications Directes sur vos Documents",
    humanAmendedBadge:
      "Modifié directement par un membre — Protégé contre tout remplacement automatique",
    supersededMemlogNotice:
      "Les brouillons précédents ont été archivés au profit de la dernière modification validée.",
    registerWaiverCta: "+ Demander une adaptation pour cet espace",
    overviewSummaryText:
      "Synthèse des sources rattachées, règles métier, livrables et adaptations locales actives pour cet espace.",
    overviewEmptyStateHint:
      "Cet espace est prêt : rattachez un premier document dans Documents & Sources ou définissez vos règles métier dans le Glossaire.",
    teamBillingLabel: "Équipe de rattachement",
    visibilityLabel: "Visibilité",
    roleLabel: "Rôle effectif",
    phaseLabel: "Phase active",
    emptyDeliverablesText:
      "Aucun document livrable modifié manuellement pour le moment. Les productions suivent l'emplacement d'enregistrement par défaut.",
    deliverablesCatalogTitle: "Livrables validés de l'espace",
    emptyGlossaryRulesText:
      "Aucune adaptation locale active pour le moment sur les règles du glossaire.",
    membersAccessHint:
      "Les invitations et droits d'accès par équipe sont gérés depuis Mon Organisation et le sélecteur d'espace.",
  },
  dnaStarlarkGlossary: {
    heading: "Règles Métiers Automatiques & Termes du Glossaire à Valider",
    generateStarlarkCta: "Générer le contrôle automatique",
    signAndActivateCta: "Valider et activer la règle",
    runtimeZeroTokenBadge:
      "Vérification instantanée sans appel à un modèle IA",
    queueSectionTitle:
      "Nouveaux termes et règles proposés (jusqu'à 15 en attente)",
    inFlowBriefingTitle: "Ajout Rapide au Glossaire lors d'une Relecture",
    promoteInFlowCheckboxLabel: "Ajouter au glossaire officiel de l'Espace",
    promoteSelectedCta: "Valider la sélection",
    rejectCandidateCta: "Écarter",
    emptyCompiledControlText:
      "Aucun contrôle automatique compilé pour cet Espace. Ajoutez une règle métier pour générer et vérifier automatiquement ce contrôle.",
  },
  remoteServiceTestBench: {
    heading: "Connexion et Test d'Outils Externes & Accès depuis un Éditeur",
    testAndDiscoverCta: "Tester la connexion et détecter les actions",
    testingInProgressCta: "Vérification en cours…",
    testingInProgressNotice:
      "Vérification en cours auprès du serveur et enregistrement dans le registre d'audit…",
    activateConnectorCta: "Activer ce service dans l'Espace",
    activateDisabledReason:
      "Validez les 4 étapes du banc d'essai pour activer ce connecteur.",
    testWithPersonalTokenCta: "Tester avec mon compte personnel",
    mcpExposureHeading: "Accès depuis un Éditeur de Code Externe",
    exposeMcpToggleLabel:
      "Permettre l'utilisation depuis un éditeur externe (Cursor, VS Code, Claude Desktop)",
    mcpIdeBadge: "Accès éditeur sécurisé · lecture et exécution distinctes",
    ipProtectionNotice:
      "Confidentialité : Les réglages internes et règles de vérification de vos processus restent protégés.",
    exposedCapabilityLabels: {
      "assistant.ask": "Interroger l'Assistant de l'espace",
      "agent.invoke": "Exécuter un agent spécialisé",
      "agent.list_exposed": "Lister les agents autorisés",
    },
    exposedAgentCapabilityPrefix: "Agent autorisé :",
    stepLabels: {
      "1_NETWORK_TLS_ANTI_SSRF": "Réseau, chiffrement et protection d'adresse",
      "2_AUTHENTICATION": "Authentification et droits d'accès",
      "3_CONTRACT_DISCOVERY": "Découverte des actions exposées",
      "4_HOT_DRY_RUN": "Essai rapide à blanc",
    },
    statusLabels: {
      PASS: "Validé",
      FAIL: "Échec",
      WAITING_USER_PASSTHROUGH_TOKEN: "En attente de jeton personnel",
      SKIPPED: "Ignoré",
    },
  },
  packBuilderStudio: {
    studioTitle: "Création et Évolution de Packs Métiers",
    agentsSectionTitle: "Assistants de Conception du Pack",
    humanAnchorSectionTitle:
      "Étape 1 — Définition des Objectifs du Pack Métier (Rédaction Personnelle)",
    humanAnchorPlaceholder:
      "Décrivez l'objectif métier, le domaine concerné et les règles essentielles du Pack (minimum 30 caractères)...",
    process1CreatePackButtonLabel: "1. Créer le Pack Métier",
    process2WhatIfTitle: "2. Aperçu d'Impact d'une Nouvelle Version",
    runLocksPreservedBadgeLabel:
      "Les processus déjà en cours conservent leur version actuelle sans interruption",
    process3CertifyTitle: "3. Vérification de Conformité et de Sécurité",
    certifiedBadgeLabel: "VÉRIFIÉ ET PRÊT À PUBLIER",
    process4PromoteButtonLabel:
      "4. Transformer les réglages de cet Espace en Pack réutilisable",
    durationMsUnit: "ms",
  },
  helpArticleGenerator: {
    heading: "Rédaction et Mise à Jour des Fiches d'Aide Contextuelle",
    triggerRegimeLabel: "Mode de publication :",
    stagedRegimeBadge: "Avec relecture avant publication",
    autonomousRegimeBadge: "Publication directe après vérification",
    validationChecksHeading: "Vérifications automatiques de qualité",
    checkBoundRoutesLabel: "Écrans ciblés et repères de section valides",
    checkUiComponentsSectionsLabel: "Structure complète en 3 sections claires",
    checkGlossaryZeroSecretLabel:
      "Vocabulaire aligné sur le glossaire et absence de donnée confidentielle", // pragma: allowlist secret
    passedBadge: "CONFORME",
    failedBadge: "À CORRIGER",
    hotAttachmentHeading: "Mise en Ligne Immédiate dans l'Aide Contextuelle",
    authorityReferenceBadge: "Fiche de référence officielle",
    generateAndAttachCta: "Générer, vérifier et publier la fiche d'aide",
    durationMsUnit: "ms",
  },
  agentsAndSkillsManager: {
    heading: "Mes Agents & Compétences",
    subtitle:
      "Créez vos compétences réutilisables, rattachez-les en 1 clic à vos agents spécialisés et exécutez-les immédiatement sur un cas concret.",
    tabsAriaLabel: "Vues Mes Agents et Compétences",
    tabAgents: "Mes Agents",
    tabSkills: "Compétences",
    tabConnections: "Serveurs d'outils & MCP",
    emptyAgentsTitle: "Aucun agent configuré",
    emptyAgentsDescription:
      "Créez votre premier agent ci-dessus pour lui confier des compétences et l'exécuter en 1 clic.",
    emptySkillsTitle: "Aucune compétence enregistrée",
    emptySkillsDescription:
      "Créez votre première compétence ci-dessus pour pouvoir l'exécuter ou la rattacher à vos agents.",
    createAgentSectionTitle: "Créer un Agent spécialisé",
    agentNameLabel: "Nom de l'agent",
    agentNamePlaceholder: "Ex: Analyste Risques Fournisseurs",
    agentRoleLabel: "Rôle & mission métier",
    agentRolePlaceholder:
      "Ex: Évaluer la conformité et les risques contractuels d'un dossier fournisseur",
    agentInstructionsLabel: "Instructions de travail",
    agentInstructionsPlaceholder:
      "Précisez la posture, les étapes d'analyse et les critères de qualité attendus...",
    agentThinkingLevelLabel: "Niveau de réflexion par défaut",
    thinkingLevels: {
      simple: "Rapide (Tâches directes)",
      medium: "Équilibré (Analyse standard)",
      complex: "Approfondi (Arbitrages complexes)",
      auto: "Automatique (Adaptatif)",
    },
    attachedSkillsLabel: "Compétences rattachées",
    noSkillsAvailableHint:
      "Aucune compétence créée pour le moment. Ouvrez l'onglet « Compétences » pour en créer une.",
    createAgentButtonLabel: "+ Enregistrer l'Agent",
    testAgentInputPlaceholder:
      "Saisissez une demande concrète à confier à cet agent...",
    runAgentButtonLabel: "Exécuter l'Agent",
    deleteAgentButtonLabel: "Supprimer",
    mobilizedSkillsLabel: "Compétences mobilisées",
    createSkillSectionTitle: "Créer une Compétence réutilisable",
    skillUsageBanner:
      "Une Compétence est un savoir-faire métier modulaire. Une fois enregistrée, vous pouvez la rattacher en 1 clic à un ou plusieurs Agents, ou l'invoquer directement dans Mon Assistant et vos Processus.",
    skillNameLabel: "Nom de la compétence",
    skillNamePlaceholder: "Ex: Synthèse de conformité fournisseur",
    skillObjectiveLabel: "Objectif métier (Quand utiliser cette compétence ?)",
    skillObjectivePlaceholder:
      "Ex: Vérifier les clauses critiques d'un contrat et signaler les écarts...",
    skillParamsLabel:
      "Paramètres d'entrée attendus (séparés par des virgules)",
    skillParamsPlaceholder: "Ex: contrat, conditions_particulieres",
    skillInstructionsLabel: "Méthode & instructions d'exécution",
    skillInstructionsPlaceholder:
      "Décrivez étape par étape comment traiter la demande et quelles règles vérifier...",
    skillOutputFormatLabel: "Format de résultat attendu",
    skillOutputFormatPlaceholder:
      "Ex: Tableau des risques + recommandation Go / No-Go",
    createSkillButtonLabel: "+ Enregistrer la Compétence",
    testSkillInputPlaceholder:
      "Saisissez un cas de test pour vérifier cette compétence...",
    runSkillButtonLabel: "Tester la Compétence",
    deleteSkillButtonLabel: "Supprimer",
    studio: AGENT_GOVERNANCE_STUDIO_LABELS_FR,
  },
};
