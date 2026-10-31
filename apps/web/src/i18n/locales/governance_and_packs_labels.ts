import type {
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
}

export const GOVERNANCE_AND_PACKS_FR_LABELS: GovernanceAndPacksDictionarySection = {
  workspaceFiveTabs: {
    heading: "📦 Mes Espaces — Gouvernance à 5 Sous-Onglets, Dérogations & Réconciliation",
    tabOverview: "1. Vue d'ensemble",
    tabDocumentsSources: "2. Documents & Sources",
    tabDeliverablesArtifacts: "3. Livrables & Artefacts",
    tabGlossaryRules: "4. Glossaire & Règles",
    tabMembersTeam: "5. Membres & Équipe",
    defaultDestinationTitle: "Destination par défaut des livrables :",
    roleReferenceBadge: "📚 RÉFÉRENCE (Autorité)",
    roleActiveBadge: "✏️ ACTIF (Travail)",
    modeReadOnlyBadge: "👁️ Lecture seule",
    modeReadWriteBadge: "✍️ Cible d'écriture",
    waiverSectionTitle: "Dérogations Gouvernées",
    inviolableEnterpriseLockNotice:
      "🔒 Une Directive Entreprise (1_ENTERPRISE) est inviolable — aucune dérogation locale n'est autorisée.",
    externalRebaseTitle:
      "Réconciliation d'Édition Externe",
    humanAmendedBadge: "✍️ [HUMAN_AMENDED_EXTERNAL — Verrouillé contre l'écrasement IA]",
    supersededMemlogNotice:
      "L'historique memlog intermédiaire est marqué [SUPERSEDED_BY_HUMAN_COMMIT].",
    registerWaiverCta: "+ Enregistrer une dérogation (N2/N3)",
  },
  dnaStarlarkGlossary: {
    heading: "🧬 Chaîne Causale ADN (DIRECTIVE ➔ NORME ➔ MÉCANISME Starlark) & Glossaire ✨ À valider",
    generateStarlarkCta: "⚙ Compiler la Norme en Starlark (.star)",
    signAndActivateCta: "✍️ Signer & Activer le Mécanisme",
    runtimeZeroTokenBadge: "⚡ Contrôle déterministe Starlark · 0 token LLM au runtime",
    queueSectionTitle: "✨ Termes & Règles à valider (File FIFO <= 15)",
    inFlowBriefingTitle: "Promotion In-Flow au Briefing 4 Blocs",
    promoteInFlowCheckboxLabel: "Promouvoir dans le glossaire de l'Espace",
    promoteSelectedCta: "✓ Promouvoir la sélection",
    rejectCandidateCta: "✕ Écarter",
  },
  remoteServiceTestBench: {
    heading: "🔌 Banc de Test à Chaud MCP / A2A (4 Étapes) & Exposition MCP Gouvernée (/api/v1/mcp)",
    testAndDiscoverCta: "🔌 Tester & Découvrir",
    activateConnectorCta: "✓ Activer le service distant",
    testWithPersonalTokenCta: "🔑 Tester avec mon jeton personnel (Passthrough)",
    mcpExposureHeading: "Exposition MCP Gouvernée (/api/v1/mcp)",
    exposeMcpToggleLabel: "Exposer en MCP aux IDE externes (Cursor, VS Code, Claude Desktop)",
    mcpIdeBadge: "🔌 MCP_IDE_CLIENT · execute != read",
    ipProtectionNotice:
      "🔒 Protection IP : Les prompts systèmes, graphes YAML et scripts Starlark ne sont jamais exposés par /api/v1/mcp.",
  },
  packBuilderStudio: {
    studioTitle: "🏗️ Atelier Système orcia-pack-builder — Processus 1 à 4",
    agentsSectionTitle: "Agents Spécialisés du Pack Builder",
    humanAnchorSectionTitle: "Processus 1 (create-business-pack) — Ancrage Humain Obligatoire",
    humanAnchorPlaceholder:
      "Décrivez l'intention métier, le domaine cible et les normes structurantes du Pack (>= 30 caractères)...",
    process1CreatePackButtonLabel: "1. Créer le Pack Métier (create-business-pack)",
    process2WhatIfTitle: "2. Simulation d'Impact What-If (evolve-business-pack)",
    runLocksPreservedBadgeLabel: "🔒 run-lock.json actifs intacts (100 % préservés)",
    process3CertifyTitle: "3. Certification Déterministe (certify-pack-tool)",
    certifiedBadgeLabel: "✅ CERTIFIÉ SHA-256",
    process4PromoteButtonLabel: "4. Exporter & Scrubbing depuis l'Espace (export-from-workspace-to-pack)",
  },
  helpArticleGenerator: {
    heading: "❓ Processus 5 (generate-and-attach-help) & Validateur Déterministe",
    triggerRegimeLabel: "Régime de déclenchement :",
    stagedRegimeBadge: "👤 Revue Humaine Staged",
    autonomousRegimeBadge: "⚡ Contrat Autonome",
    validationChecksHeading: "Contrôles déterministes (0 token LLM)",
    checkBoundRoutesLabel: "Routes cibles & ancres # valides",
    checkUiComponentsSectionsLabel: "Composants @orcia/ui & 3 sections obligatoires",
    checkGlossaryZeroSecretLabel: "Alignement Glossaire & 0 donnée sensible/PII", // pragma: allowlist secret
    passedBadge: "PASS",
    failedBadge: "FAIL",
    hotAttachmentHeading: "Rattachement à Chaud & Export Git",
    authorityReferenceBadge: "📚 Autorité : REFERENCE (HELP_ARTICLE)",
    generateAndAttachCta: "⚡ Générer, Valider & Rattacher à chaud",
  },
};

export const GOVERNANCE_AND_PACKS_EN_LABELS: GovernanceAndPacksDictionarySection = {
  workspaceFiveTabs: {
    heading: "📦 My Spaces — 5-Sub-Tab Governance, Waivers & External Rebase",
    tabOverview: "1. Overview",
    tabDocumentsSources: "2. Documents & Sources",
    tabDeliverablesArtifacts: "3. Deliverables & Artifacts",
    tabGlossaryRules: "4. Glossary & Rules",
    tabMembersTeam: "5. Members & Team",
    defaultDestinationTitle: "Default deliverables destination:",
    roleReferenceBadge: "📚 REFERENCE (Authority)",
    roleActiveBadge: "✏️ ACTIVE (Working)",
    modeReadOnlyBadge: "👁️ Read-only",
    modeReadWriteBadge: "✍️ Write target",
    waiverSectionTitle: "Governed Exception Waivers",
    inviolableEnterpriseLockNotice:
      "🔒 An Enterprise Directive (1_ENTERPRISE) is inviolable — no local waiver is permitted.",
    externalRebaseTitle:
      "External Edit Reconciliation",
    humanAmendedBadge: "✍️ [HUMAN_AMENDED_EXTERNAL — Locked against AI overwrite]",
    supersededMemlogNotice:
      "Intermediate memlog history is marked [SUPERSEDED_BY_HUMAN_COMMIT].",
    registerWaiverCta: "+ Register exception waiver (N2/N3)",
  },
  dnaStarlarkGlossary: {
    heading: "🧬 DNA Causal Chain (DIRECTIVE ➔ NORM ➔ Starlark MECHANISM) & ✨ Pending Glossary",
    generateStarlarkCta: "⚙ Compile Norm to Starlark (.star)",
    signAndActivateCta: "✍️ Sign & Activate Mechanism",
    runtimeZeroTokenBadge: "⚡ Deterministic Starlark check · 0 runtime LLM tokens",
    queueSectionTitle: "✨ Terms & Rules to validate (FIFO Queue <= 15)",
    inFlowBriefingTitle: "In-Flow 4-Block Briefing Promotion",
    promoteInFlowCheckboxLabel: "Promote to Space glossary",
    promoteSelectedCta: "✓ Promote selected",
    rejectCandidateCta: "✕ Dismiss",
  },
  remoteServiceTestBench: {
    heading: "🔌 Hot MCP / A2A Test Bench (4 Steps) & Governed MCP Exposure (/api/v1/mcp)",
    testAndDiscoverCta: "🔌 Test & Discover",
    activateConnectorCta: "✓ Activate remote service",
    testWithPersonalTokenCta: "🔑 Test with my personal token (Passthrough)",
    mcpExposureHeading: "Governed MCP Exposure (/api/v1/mcp)",
    exposeMcpToggleLabel: "Expose via MCP to external IDEs (Cursor, VS Code, Claude Desktop)",
    mcpIdeBadge: "🔌 MCP_IDE_CLIENT · execute != read",
    ipProtectionNotice:
      "🔒 IP Protection: System prompts, YAML graphs, and Starlark scripts are never exposed via /api/v1/mcp.",
  },
  packBuilderStudio: {
    studioTitle: "🏗️ System Studio orcia-pack-builder — Processes 1 to 4",
    agentsSectionTitle: "Specialized Pack Builder Agents",
    humanAnchorSectionTitle: "Process 1 (create-business-pack) — Mandatory Human Anchor",
    humanAnchorPlaceholder:
      "Describe the business intent, target domain, and structuring norms of the Pack (>= 30 chars)...",
    process1CreatePackButtonLabel: "1. Create Business Pack (create-business-pack)",
    process2WhatIfTitle: "2. What-If Impact Simulation (evolve-business-pack)",
    runLocksPreservedBadgeLabel: "🔒 Active run-lock.json untouched (100% preserved)",
    process3CertifyTitle: "3. Deterministic Certification (certify-pack-tool)",
    certifiedBadgeLabel: "✅ CERTIFIED SHA-256",
    process4PromoteButtonLabel: "4. Export & Scrub from Space (export-from-workspace-to-pack)",
  },
  helpArticleGenerator: {
    heading: "❓ Process 5 (generate-and-attach-help) & Deterministic Validator",
    triggerRegimeLabel: "Trigger regime:",
    stagedRegimeBadge: "👤 Staged Human Review",
    autonomousRegimeBadge: "⚡ Autonomous Contract",
    validationChecksHeading: "Deterministic Checks (0 LLM tokens)",
    checkBoundRoutesLabel: "Valid target routes & # anchors",
    checkUiComponentsSectionsLabel: "@orcia/ui components & 3 mandatory sections",
    checkGlossaryZeroSecretLabel: "Glossary alignment & 0 sensitive data/PII", // pragma: allowlist secret
    passedBadge: "PASS",
    failedBadge: "FAIL",
    hotAttachmentHeading: "Hot Attachment & Git Export",
    authorityReferenceBadge: "📚 Authority: REFERENCE (HELP_ARTICLE)",
    generateAndAttachCta: "⚡ Generate, Validate & Hot-Attach",
  },
};
