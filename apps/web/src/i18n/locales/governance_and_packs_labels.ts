import type {
  AgentsAndSkillsManagerLabels,
  DnaStarlarkAndGlossaryLabels,
  HelpArticleGeneratorAndValidatorLabels,
  PackBuilderProcessesStudioLabels,
  RemoteServiceTestBenchLabels,
  WorkspaceFiveTabsLabels,
} from "@orcia/ui";

export interface GovernanceAndPacksDictionarySection {
  readonly workspaceFiveTabs: WorkspaceFiveTabsLabels;
  readonly dnaStarlarkGlossary: DnaStarlarkAndGlossaryLabels;
  readonly remoteServiceTestBench: RemoteServiceTestBenchLabels;
  readonly packBuilderStudio: PackBuilderProcessesStudioLabels;
  readonly helpArticleGenerator: HelpArticleGeneratorAndValidatorLabels;
  readonly agentsAndSkillsManager: AgentsAndSkillsManagerLabels;
}

export const GOVERNANCE_AND_PACKS_FR_LABELS: GovernanceAndPacksDictionarySection = {
  workspaceFiveTabs: {
    heading: "📦 Mes Espaces — Sources, Livrables, Glossaire & Équipe",
    tabOverview: "1. Vue d'ensemble",
    tabDocumentsSources: "2. Documents & Sources",
    tabDeliverablesArtifacts: "3. Livrables & Documents Produits",
    tabGlossaryRules: "4. Glossaire & Règles Métiers",
    tabMembersTeam: "5. Membres & Équipe",
    defaultDestinationTitle: "Emplacement d'enregistrement des livrables :",
    roleReferenceBadge: "📚 RÉFÉRENCE (Document officiel)",
    roleActiveBadge: "✏️ TRAVAIL EN COURS",
    modeReadOnlyBadge: "👁️ Consultation seule",
    modeReadWriteBadge: "✍️ Publication autorisée",
    waiverSectionTitle: "Adaptations et Dérogations Locales",
    inviolableEnterpriseLockNotice:
      "🔒 Les règles générales de l'organisation s'appliquent à tous les espaces et ne peuvent pas faire l'objet d'une dérogation locale.",
    externalRebaseTitle:
      "Prise en Compte des Modifications Directes sur vos Documents",
    humanAmendedBadge: "✍️ Modifié directement par un membre — Protégé contre tout remplacement automatique",
    supersededMemlogNotice:
      "Les brouillons précédents ont été archivés au profit de la dernière modification validée.",
    registerWaiverCta: "+ Demander une adaptation pour cet espace",
  },
  dnaStarlarkGlossary: {
    heading: "🧬 Règles Métiers Automatiques & Termes du Glossaire à Valider",
    generateStarlarkCta: "⚙ Générer le contrôle automatique",
    signAndActivateCta: "✍️ Valider et activer la règle",
    runtimeZeroTokenBadge: "⚡ Vérification instantanée sans appel à un modèle IA",
    queueSectionTitle: "✨ Nouveaux termes et règles proposés (jusqu'à 15 en attente)",
    inFlowBriefingTitle: "Ajout Rapide au Glossaire lors d'une Relecture",
    promoteInFlowCheckboxLabel: "Ajouter au glossaire officiel de l'Espace",
    promoteSelectedCta: "✓ Valider la sélection",
    rejectCandidateCta: "✕ Écarter",
  },
  remoteServiceTestBench: {
    heading: "🔌 Connexion et Test d'Outils Externes & Accès depuis un Éditeur",
    testAndDiscoverCta: "🔌 Tester la connexion et détecter les actions",
    activateConnectorCta: "✓ Activer ce service dans l'Espace",
    testWithPersonalTokenCta: "🔑 Tester avec mon compte personnel",
    mcpExposureHeading: "Accès depuis un Éditeur de Code Externe",
    exposeMcpToggleLabel: "Permettre l'utilisation depuis un éditeur externe (Cursor, VS Code, Claude Desktop)",
    mcpIdeBadge: "🔌 Accès éditeur sécurisé · lecture et exécution distinctes",
    ipProtectionNotice:
      "🔒 Confidentialité : Les réglages internes et règles de vérification de vos processus restent protégés.",
  },
  packBuilderStudio: {
    studioTitle: "🏗️ Création et Évolution de Packs Métiers",
    agentsSectionTitle: "Assistants de Conception du Pack",
    humanAnchorSectionTitle: "Étape 1 — Définition des Objectifs du Pack Métier (Rédaction Personnelle)",
    humanAnchorPlaceholder:
      "Décrivez l'objectif métier, le domaine concerné et les règles essentielles du Pack (minimum 30 caractères)...",
    process1CreatePackButtonLabel: "1. Créer le Pack Métier",
    process2WhatIfTitle: "2. Aperçu d'Impact d'une Nouvelle Version",
    runLocksPreservedBadgeLabel: "🔒 Les processus déjà en cours conservent leur version actuelle sans interruption",
    process3CertifyTitle: "3. Vérification de Conformité et de Sécurité",
    certifiedBadgeLabel: "✅ VÉRIFIÉ ET PRÊT À PUBLIER",
    process4PromoteButtonLabel: "4. Transformer les réglages de cet Espace en Pack réutilisable",
  },
  helpArticleGenerator: {
    heading: "❓ Rédaction et Mise à Jour des Fiches d'Aide Contextuelle",
    triggerRegimeLabel: "Mode de publication :",
    stagedRegimeBadge: "👤 Avec relecture avant publication",
    autonomousRegimeBadge: "⚡ Publication directe après vérification",
    validationChecksHeading: "Vérifications automatiques de qualité",
    checkBoundRoutesLabel: "Écrans ciblés et repères de section valides",
    checkUiComponentsSectionsLabel: "Structure complète en 3 sections claires",
    checkGlossaryZeroSecretLabel: "Vocabulaire aligné sur le glossaire et absence de donnée confidentielle", // pragma: allowlist secret
    passedBadge: "CONFORME",
    failedBadge: "À CORRIGER",
    hotAttachmentHeading: "Mise en Ligne Immédiate dans l'Aide Contextuelle",
    authorityReferenceBadge: "📚 Fiche de référence officielle",
    generateAndAttachCta: "⚡ Générer, vérifier et publier la fiche d'aide",
  },
  agentsAndSkillsManager: {
    heading: "🤖 Mes Agents & Compétences (Skills)",
    subtitle:
      "Créez vos compétences réutilisables, rattachez-les en 1 clic à vos agents spécialisés et exécutez-les immédiatement sur un cas concret.",
    tabAgents: "🤖 Mes Agents",
    tabSkills: "🛠️ Compétences (Skills)",
    tabConnections: "🔌 Serveurs d'outils & MCP",
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
      simple: "⚡ Rapide (Tâches directes)",
      medium: "⚖️ Équilibré (Analyse standard)",
      complex: "🧠 Approfondi (Arbitrages complexes)",
      auto: "✨ Automatique (Adaptatif)",
    },
    attachedSkillsLabel: "Compétences (Skills) rattachées",
    noSkillsAvailableHint:
      "Aucune compétence créée pour le moment. Ouvrez l'onglet « 🛠️ Compétences (Skills) » pour en créer une.",
    createAgentButtonLabel: "+ Enregistrer l'Agent",
    testAgentInputPlaceholder: "Saisissez une demande concrète à confier à cet agent...",
    runAgentButtonLabel: "▶ Exécuter l'Agent",
    deleteAgentButtonLabel: "Supprimer",
    mobilizedSkillsLabel: "Compétences mobilisées",
    createSkillSectionTitle: "Créer une Compétence (Skill) réutilisable",
    skillUsageBanner:
      "💡 Une Compétence (Skill) est un savoir-faire métier modulaire. Une fois enregistrée, vous pouvez la rattacher en 1 clic à un ou plusieurs Agents, ou l'invoquer directement dans Mon Assistant et vos Processus.",
    skillNameLabel: "Nom de la compétence",
    skillNamePlaceholder: "Ex: Synthèse de conformité fournisseur",
    skillObjectiveLabel: "Objectif métier (Quand utiliser cette compétence ?)",
    skillObjectivePlaceholder:
      "Ex: Vérifier les clauses critiques d'un contrat et signaler les écarts...",
    skillParamsLabel: "Paramètres d'entrée attendus (séparés par des virgules)",
    skillParamsPlaceholder: "Ex: contrat, conditions_particulieres",
    skillInstructionsLabel: "Méthode & instructions d'exécution",
    skillInstructionsPlaceholder:
      "Décrivez étape par étape comment traiter la demande et quelles règles vérifier...",
    skillOutputFormatLabel: "Format de résultat attendu",
    skillOutputFormatPlaceholder: "Ex: Tableau des risques + recommandation Go / No-Go",
    createSkillButtonLabel: "+ Enregistrer la Compétence",
    testSkillInputPlaceholder: "Saisissez un cas de test pour vérifier cette compétence...",
    runSkillButtonLabel: "▶ Tester la Compétence",
    deleteSkillButtonLabel: "Supprimer",
  },
};

export const GOVERNANCE_AND_PACKS_EN_LABELS: GovernanceAndPacksDictionarySection = {
  workspaceFiveTabs: {
    heading: "📦 My Spaces — Sources, Deliverables, Glossary & Team",
    tabOverview: "1. Overview",
    tabDocumentsSources: "2. Documents & Sources",
    tabDeliverablesArtifacts: "3. Deliverables & Produced Documents",
    tabGlossaryRules: "4. Glossary & Business Rules",
    tabMembersTeam: "5. Members & Team",
    defaultDestinationTitle: "Default save location for deliverables:",
    roleReferenceBadge: "📚 REFERENCE (Official document)",
    roleActiveBadge: "✏️ WORK IN PROGRESS",
    modeReadOnlyBadge: "👁️ Read-only",
    modeReadWriteBadge: "✍️ Publishing allowed",
    waiverSectionTitle: "Local Adaptations and Exceptions",
    inviolableEnterpriseLockNotice:
      "🔒 Organization-wide rules apply to all workspaces and cannot be bypassed locally.",
    externalRebaseTitle:
      "Syncing Direct Edits Made to Your Documents",
    humanAmendedBadge: "✍️ Edited directly by a team member — Protected against automatic overwrite",
    supersededMemlogNotice:
      "Previous drafts have been archived in favor of the latest validated edit.",
    registerWaiverCta: "+ Request a local adaptation for this space",
  },
  dnaStarlarkGlossary: {
    heading: "🧬 Automated Business Rules & Glossary Terms to Review",
    generateStarlarkCta: "⚙ Generate automated check",
    signAndActivateCta: "✍️ Confirm and activate rule",
    runtimeZeroTokenBadge: "⚡ Instant verification without calling an AI model",
    queueSectionTitle: "✨ Suggested new terms and rules (up to 15 pending)",
    inFlowBriefingTitle: "Quick Glossary Addition During Review",
    promoteInFlowCheckboxLabel: "Add to the official Space glossary",
    promoteSelectedCta: "✓ Approve selected",
    rejectCandidateCta: "✕ Dismiss",
  },
  remoteServiceTestBench: {
    heading: "🔌 External Tool Connection Testing & Code Editor Access",
    testAndDiscoverCta: "🔌 Test connection and discover actions",
    activateConnectorCta: "✓ Enable this service in the Space",
    testWithPersonalTokenCta: "🔑 Test with my personal account",
    mcpExposureHeading: "External Code Editor Access",
    exposeMcpToggleLabel: "Allow usage from an external code editor (Cursor, VS Code, Claude Desktop)",
    mcpIdeBadge: "🔌 Secure editor access · separate read and execute permissions",
    ipProtectionNotice:
      "🔒 Confidentiality: Internal process settings and verification rules remain protected.",
  },
  packBuilderStudio: {
    studioTitle: "🏗️ Business Pack Creation and Evolution",
    agentsSectionTitle: "Pack Design Assistants",
    humanAnchorSectionTitle: "Step 1 — Define Business Pack Goals (Personal Authoring)",
    humanAnchorPlaceholder:
      "Describe the business goal, target domain, and key rules for this Pack (at least 30 characters)...",
    process1CreatePackButtonLabel: "1. Create Business Pack",
    process2WhatIfTitle: "2. New Version Impact Preview",
    runLocksPreservedBadgeLabel: "🔒 In-progress executions keep their current version without interruption",
    process3CertifyTitle: "3. Compliance and Security Verification",
    certifiedBadgeLabel: "✅ VERIFIED AND READY TO PUBLISH",
    process4PromoteButtonLabel: "4. Turn this Space's settings into a reusable Pack",
  },
  helpArticleGenerator: {
    heading: "❓ Authoring and Updating Contextual Help Articles",
    triggerRegimeLabel: "Publishing mode:",
    stagedRegimeBadge: "👤 Review before publishing",
    autonomousRegimeBadge: "⚡ Publish directly after checks",
    validationChecksHeading: "Automated quality checks",
    checkBoundRoutesLabel: "Valid target screens and section anchors",
    checkUiComponentsSectionsLabel: "Complete structure with 3 clear sections",
    checkGlossaryZeroSecretLabel: "Vocabulary aligned with glossary and zero confidential data", // pragma: allowlist secret
    passedBadge: "PASSED",
    failedBadge: "NEEDS FIX",
    hotAttachmentHeading: "Immediate Publishing to Contextual Help",
    authorityReferenceBadge: "📚 Official reference guide",
    generateAndAttachCta: "⚡ Generate, verify, and publish help guide",
  },
  agentsAndSkillsManager: {
    heading: "🤖 My Agents & Skills",
    subtitle:
      "Create reusable business skills, attach them in 1 click to your specialized agents, and execute them immediately on concrete tasks.",
    tabAgents: "🤖 My Agents",
    tabSkills: "🛠️ Skills",
    tabConnections: "🔌 Tool Servers & MCP",
    emptyAgentsTitle: "No agent configured yet",
    emptyAgentsDescription:
      "Create your first agent above to attach skills and run it in 1 click.",
    emptySkillsTitle: "No skills saved yet",
    emptySkillsDescription:
      "Create your first skill above to test it or attach it to your agents.",
    createAgentSectionTitle: "Create a specialized Agent",
    agentNameLabel: "Agent name",
    agentNamePlaceholder: "e.g., Supplier Risk Analyst",
    agentRoleLabel: "Business role & mission",
    agentRolePlaceholder: "e.g., Evaluate compliance and contractual risks in supplier files",
    agentInstructionsLabel: "Working instructions",
    agentInstructionsPlaceholder:
      "Specify the posture, analysis steps, and expected quality criteria...",
    agentThinkingLevelLabel: "Default thinking depth",
    thinkingLevels: {
      simple: "⚡ Fast (Direct tasks)",
      medium: "⚖️ Balanced (Standard analysis)",
      complex: "🧠 Deep (Complex trade-offs)",
      auto: "✨ Automatic (Adaptive)",
    },
    attachedSkillsLabel: "Attached Skills",
    noSkillsAvailableHint:
      "No skills created yet. Open the '🛠️ Skills' tab to create your first reusable skill.",
    createAgentButtonLabel: "+ Save Agent",
    testAgentInputPlaceholder: "Enter a concrete request to assign to this agent...",
    runAgentButtonLabel: "▶ Run Agent",
    deleteAgentButtonLabel: "Delete",
    mobilizedSkillsLabel: "Mobilized skills",
    createSkillSectionTitle: "Create a reusable Skill",
    skillUsageBanner:
      "💡 A Skill is a modular business capability. Once saved, you can attach it in 1 click to one or more Agents, or invoke it directly in My Assistant and your Processes.",
    skillNameLabel: "Skill name",
    skillNamePlaceholder: "e.g., Supplier compliance summary",
    skillObjectiveLabel: "Business goal (When to use this skill?)",
    skillObjectivePlaceholder:
      "e.g., Check critical contract clauses and highlight deviations...",
    skillParamsLabel: "Expected input parameters (comma-separated)",
    skillParamsPlaceholder: "e.g., contract, special_terms",
    skillInstructionsLabel: "Execution method & instructions",
    skillInstructionsPlaceholder:
      "Describe step by step how to process the input and which rules to verify...",
    skillOutputFormatLabel: "Expected output format",
    skillOutputFormatPlaceholder: "e.g., Risk summary table + Go / No-Go recommendation",
    createSkillButtonLabel: "+ Save Skill",
    testSkillInputPlaceholder: "Enter a sample input to test this skill...",
    runSkillButtonLabel: "▶ Test Skill",
    deleteSkillButtonLabel: "Delete",
  },
};
