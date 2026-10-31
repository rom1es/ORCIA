export interface AdminAndStudioDictionarySection {
  readonly settingsHub: {
    readonly hubTitle: string;
    readonly hubSubtitle: string;
    readonly tabs: {
      readonly iam: string;
      readonly connectors: string;
      readonly aiModels: string;
      readonly packs: string;
      readonly workflows: string;
      readonly audit: string;
    };
    readonly lockedSectionNotice: string;
    readonly requestAccessLabel: string;
    readonly secretFieldLabels: {
      readonly configuredBadge: string;
      readonly unconfiguredBadge: string;
      readonly fingerprintLabel: string;
      readonly keepButton: string;
      readonly replaceButton: string;
      readonly clearButton: string;
      readonly inputPlaceholder: string;
    };
    readonly tierLabels: {
      readonly simple: string;
      readonly medium: string;
      readonly complex: string;
      readonly auto: string;
      readonly autoResolvedPrefix: string;
    };
    readonly effortLabels: {
      readonly default: string;
      readonly fast: string;
      readonly balanced: string;
      readonly deep: string;
    };
    readonly studioLabels: {
      readonly prePromptButton: string;
      readonly contractButton: string;
      readonly triggersButton: string;
      readonly dryRunButton: string;
      readonly forkButton: string;
      readonly publishButton: string;
      readonly readOnlyPublishedHint: string;
      readonly layersBadgePrefix: string;
      readonly inputsZoneTitle: string;
      readonly capabilitiesZoneTitle: string;
      readonly deliverablesZoneTitle: string;
      readonly enabledStatusLabel: string;
      readonly skippedStatusLabel: string;
      readonly deleteActionLabel: string;
    };
    readonly wizardLabels: {
      readonly title: string;
      readonly resumeBannerText: string;
      readonly stepCounterPrefix: string;
      readonly validateAndContinueButton: string;
      readonly completedBadgeText: string;
      readonly demoWorkspaceButton: string;
      readonly citationLabel: string;
    };
  };
}

export const ADMIN_AND_STUDIO_FR_LABELS: AdminAndStudioDictionarySection = {
  settingsHub: {
    hubTitle: "Hub de Paramétrage Post-Jour 0 & Gouvernance 6 Verbes (/settings/*)",
    hubSubtitle:
      "Administration unifiée IAM RBAC/ABAC, Connecteurs write-only (SecretStatus), Routage Cognitif Abstrait (simple/medium/complex/auto), Registre des Packs et Studio Visuel.",
    tabs: {
      iam: "Habilitations (IAM 6 verbes)",
      connectors: "Connecteurs & Réciprocité RAG",
      aiModels: "Modèles IA & Tiers Cognitifs",
      packs: "Packs Métiers",
      workflows: "Studio Visuel (Couches & Contrat)",
      audit: "Audit & Replay Outbox",
    },
    lockedSectionNotice:
      "Ressource visible en découverte passive — habilitation update/grant requise.",
    requestAccessLabel: "Demander l'accès (Outbox)",
    secretFieldLabels: {
      configuredBadge: "Configuré",
      unconfiguredBadge: "Non configuré",
      fingerprintLabel: "Empreinte SHA-256 salée",
      keepButton: "Conserver",
      replaceButton: "Remplacer",
      clearButton: "Effacer",
      inputPlaceholder: "Saisir la nouvelle valeur write-only...", // pragma: allowlist secret
    },
    tierLabels: {
      simple: "Simple",
      medium: "Moyen",
      complex: "Complexe",
      auto: "Auto (Escalade déterministe)",
      autoResolvedPrefix: "résolu :",
    },
    effortLabels: {
      default: "Défaut",
      fast: "Rapide",
      balanced: "Équilibré",
      deep: "Approfondi",
    },
    studioLabels: {
      prePromptButton: "Pré-prompt IA",
      contractButton: "Contrat du workflow",
      triggersButton: "Déclencheurs",
      dryRunButton: "▷ Tester (What-If isolé)",
      forkButton: "Modifier (Fork SemVer)",
      publishButton: "Publier la révision",
      readOnlyPublishedHint: "Révision publiée immuable (lecture seule)",
      layersBadgePrefix: "COUCHES",
      inputsZoneTitle: "1. Entrées & Contexte",
      capabilitiesZoneTitle: "2. Capacités & Agents internes",
      deliverablesZoneTitle: "3. Livrables & Contrôles de sortie",
      enabledStatusLabel: "Actif",
      skippedStatusLabel: "SKIPPED",
      deleteActionLabel: "Retirer",
    },
    wizardLabels: {
      title: "Assistants d'Initialisation Guidés et Durables (DBOS)",
      resumeBannerText: "Session reprise automatiquement au point de sauvegarde DBOS",
      stepCounterPrefix: "Étape",
      validateAndContinueButton: "Valider l'étape (Check Fail-Fast)",
      completedBadgeText: "Initialisation terminée",
      demoWorkspaceButton: "Provisionner Démo Zero Empty-State (1-clic)",
      citationLabel: "Preuve de réciprocité RAG",
    },
  },
};

export const ADMIN_AND_STUDIO_EN_LABELS: AdminAndStudioDictionarySection = {
  settingsHub: {
    hubTitle: "Post-Day-0 Settings Hub & 6-Verb Governance (/settings/*)",
    hubSubtitle:
      "Unified IAM 6-verb RBAC/ABAC, write-only Connectors (SecretStatus), Abstract Cognitive Routing (simple/medium/complex/auto), Business Pack Registry, and Visual Studio.",
    tabs: {
      iam: "Permissions (6-Verb IAM)",
      connectors: "Connectors & RAG Reciprocity",
      aiModels: "AI Models & Cognitive Tiers",
      packs: "Business Packs",
      workflows: "Visual Studio (Layers & Contract)",
      audit: "Audit & Outbox Replay",
    },
    lockedSectionNotice:
      "Resource visible via passive discovery — update/grant permission required.",
    requestAccessLabel: "Request access (Outbox)",
    secretFieldLabels: {
      configuredBadge: "Configured",
      unconfiguredBadge: "Unconfigured",
      fingerprintLabel: "Salted SHA-256 fingerprint",
      keepButton: "Keep",
      replaceButton: "Replace",
      clearButton: "Clear",
      inputPlaceholder: "Enter new write-only secret value...", // pragma: allowlist secret
    },
    tierLabels: {
      simple: "Simple",
      medium: "Medium",
      complex: "Complex",
      auto: "Auto (Deterministic Escalation)",
      autoResolvedPrefix: "resolved:",
    },
    effortLabels: {
      default: "Default",
      fast: "Fast",
      balanced: "Balanced",
      deep: "Deep",
    },
    studioLabels: {
      prePromptButton: "AI Pre-prompt",
      contractButton: "Workflow Contract",
      triggersButton: "Triggers",
      dryRunButton: "▷ Test (Isolated What-If)",
      forkButton: "Edit (SemVer Fork)",
      publishButton: "Publish revision",
      readOnlyPublishedHint: "Immutable published revision (read-only)",
      layersBadgePrefix: "LAYERS",
      inputsZoneTitle: "1. Inputs & Context",
      capabilitiesZoneTitle: "2. Capabilities & Internal Agents",
      deliverablesZoneTitle: "3. Deliverables & Output Checks",
      enabledStatusLabel: "Enabled",
      skippedStatusLabel: "SKIPPED",
      deleteActionLabel: "Remove",
    },
    wizardLabels: {
      title: "Profile-Guided Durable Onboarding Wizards (DBOS)",
      resumeBannerText: "Session automatically resumed from DBOS checkpoint",
      stepCounterPrefix: "Step",
      validateAndContinueButton: "Validate step (Fail-Fast Check)",
      completedBadgeText: "Onboarding completed",
      demoWorkspaceButton: "Provision 1-Click Zero Empty-State Demo",
      citationLabel: "RAG Reciprocity Citation",
    },
  },
};
