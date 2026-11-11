export interface AdminAndStudioDictionarySection {
  readonly settingsHub: {
    readonly hubTitle: string;
    readonly hubSubtitle: string;
    readonly tabs: {
      readonly organization: string;
      readonly iam: string;
      readonly models: string;
      readonly connectors: string;
      readonly packs: string;
    };
    readonly lockedSectionNotice: string;
    readonly requestAccessLabel: string;
    readonly readOnlyRestrictedTitle: string;
    readonly readOnlyRestrictedBody: string;
    readonly openMyAccountCta: string;
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
    readonly organizationTab: {
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
        readonly cancelButton: string;
        readonly confirmDeleteButton: string;
      };
    };
  };
}

export const ADMIN_AND_STUDIO_FR_LABELS: AdminAndStudioDictionarySection = {
  settingsHub: {
    hubTitle: "Configuration de la Plateforme & Organisation",
    hubSubtitle:
      "Gérez l'organigramme de vos directions et équipes, les comptes et habilitations, les modèles IA, les connecteurs externes et les packs métiers.",
    tabs: {
      organization: "Organisation",
      iam: "Comptes & Habilitations",
      models: "Modèles IA",
      connectors: "Connecteurs & SSO",
      packs: "Packs Métiers",
    },
    lockedSectionNotice:
      "Cette section est affichée en lecture seule — un droit d'administration est nécessaire pour la modifier.",
    requestAccessLabel: "Demander l'accès à un administrateur",
    readOnlyRestrictedTitle: "Accès en lecture seule sur la configuration de la plateforme",
    readOnlyRestrictedBody:
      "Votre rôle actuel ne permet pas de modifier les paramètres globaux ou organisationnels. Pour gérer vos préférences personnelles (apparence, langue, rôle par défaut, clés d'accès personnelles), ouvrez Mon Compte.",
    openMyAccountCta: "Ouvrir Mon Compte",
    secretFieldLabels: {
      configuredBadge: "Configuré",
      unconfiguredBadge: "Non configuré",
      fingerprintLabel: "Identifiant de clé enregistrée",
      keepButton: "Conserver",
      replaceButton: "Remplacer",
      clearButton: "Effacer",
      inputPlaceholder: "Saisir la nouvelle clé secrète...", // pragma: allowlist secret
    },
    tierLabels: {
      simple: "Simple",
      medium: "Standard",
      complex: "Approfondi",
      auto: "Automatique (selon la demande)",
      autoResolvedPrefix: "niveau choisi :",
    },
    effortLabels: {
      default: "Par défaut",
      fast: "Rapide",
      balanced: "Équilibré",
      deep: "Approfondi",
    },
    studioLabels: {
      prePromptButton: "Consignes de l'assistant",
      contractButton: "Données attendues",
      triggersButton: "Déclencheurs",
      dryRunButton: "▷ Tester à blanc",
      forkButton: "Créer une nouvelle version",
      publishButton: "Publier la version",
      readOnlyPublishedHint: "Version publiée (non modifiable directement)",
      layersBadgePrefix: "NIVEAUX",
      inputsZoneTitle: "1. Informations d'Entrée & Contexte",
      capabilitiesZoneTitle: "2. Étapes & Agents Mobilisés",
      deliverablesZoneTitle: "3. Livrables & Vérifications",
      enabledStatusLabel: "Actif",
      skippedStatusLabel: "Désactivé",
      deleteActionLabel: "Retirer",
    },
    wizardLabels: {
      title: "Assistants Guidés de Configuration",
      resumeBannerText: "Votre progression a été restaurée là où vous vous étiez arrêté",
      stepCounterPrefix: "Étape",
      validateAndContinueButton: "Valider et continuer",
      completedBadgeText: "Configuration terminée",
      demoWorkspaceButton: "Créer un espace d'exemple prêt à l'emploi",
      citationLabel: "Source documentaire vérifiée",
    },
    organizationTab: {
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
          "Déplacez ou supprimez d'abord les sous-unités et espaces rattachés ci-dessus avant de supprimer cette unité.",
        cancelButton: "Annuler",
        confirmDeleteButton: "Confirmer la suppression",
      },
    },
  },
};

export const ADMIN_AND_STUDIO_EN_LABELS: AdminAndStudioDictionarySection = {
  settingsHub: {
    hubTitle: "Platform Configuration & Organization",
    hubSubtitle:
      "Manage your organization units and teams, user accounts and permissions, AI models, external connectors, and business packs.",
    tabs: {
      organization: "Organization",
      iam: "Accounts & Permissions",
      models: "AI Models",
      connectors: "Connectors & SSO",
      packs: "Business Packs",
    },
    lockedSectionNotice:
      "This section is displayed in read-only mode — administrator permissions are required to edit it.",
    requestAccessLabel: "Request access from an administrator",
    readOnlyRestrictedTitle: "Read-only access on platform configuration",
    readOnlyRestrictedBody:
      "Your current role does not allow modifying global or organizational settings. To manage your personal preferences (theme, language, default role, personal access keys), open My Account.",
    openMyAccountCta: "Open My Account",
    secretFieldLabels: {
      configuredBadge: "Configured",
      unconfiguredBadge: "Not configured",
      fingerprintLabel: "Saved key identifier",
      keepButton: "Keep",
      replaceButton: "Replace",
      clearButton: "Clear",
      inputPlaceholder: "Enter new secret key...", // pragma: allowlist secret
    },
    tierLabels: {
      simple: "Simple",
      medium: "Standard",
      complex: "In-Depth",
      auto: "Automatic (based on request)",
      autoResolvedPrefix: "selected level:",
    },
    effortLabels: {
      default: "Default",
      fast: "Fast",
      balanced: "Balanced",
      deep: "In-Depth",
    },
    studioLabels: {
      prePromptButton: "Assistant instructions",
      contractButton: "Expected data",
      triggersButton: "Triggers",
      dryRunButton: "▷ Run test preview",
      forkButton: "Create new version",
      publishButton: "Publish version",
      readOnlyPublishedHint: "Published version (read-only)",
      layersBadgePrefix: "LEVELS",
      inputsZoneTitle: "1. Input Information & Context",
      capabilitiesZoneTitle: "2. Steps & Assigned Agents",
      deliverablesZoneTitle: "3. Deliverables & Checks",
      enabledStatusLabel: "Enabled",
      skippedStatusLabel: "Disabled",
      deleteActionLabel: "Remove",
    },
    wizardLabels: {
      title: "Guided Setup Assistants",
      resumeBannerText: "Your progress was restored from where you left off",
      stepCounterPrefix: "Step",
      validateAndContinueButton: "Validate and continue",
      completedBadgeText: "Setup completed",
      demoWorkspaceButton: "Create a ready-to-use sample workspace",
      citationLabel: "Verified document source",
    },
    organizationTab: {
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
          "Move or delete the attached child units and workspaces listed above before deleting this unit.",
        cancelButton: "Cancel",
        confirmDeleteButton: "Confirm delete",
      },
    },
  },
};
