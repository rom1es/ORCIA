import type {
  EightFixedMenuKey,
  UiContextualHelpArticleView,
  UiContextualHelpSectionItem,
} from "@orcia/ui";

export interface BuildContextualHelpArticleParams {
  readonly activeMenuKey: EightFixedMenuKey;
  readonly pathname: string | undefined;
  readonly locale: "fr" | "en";
  readonly title: string;
  readonly defaultSummary: string;
}

const CONFIGURATION_SECTIONS_FR: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "iam-org-tree",
    title: "Structure de l'organisation (Directions / BU & Espaces)",
    body: "Organisez votre entreprise en Directions (BU) puis en Espaces de travail (équipes ou projets). Un élément ne peut être supprimé que s'il ne contient aucun sous-espace ni règle d'accès rattachée.",
    category: "steps",
  },
  {
    sectionId: "iam-role-grants",
    title: "Règles d'accès : Qui ? et Sur quoi ?",
    body: "Chaque règle associe un bénéficiaire (Rôle ou Utilisateur, ex. Rôle : Chef1) à un périmètre cible (Plateforme entière, Direction / BU ou Espace, ex. aqwZSX) et précise les habilitations attribuées (Créer, Lire / Voir les secrets, Modifier, Supprimer, Exécuter / Utiliser, Déléguer des droits).",
    category: "terms",
  },
  {
    sectionId: "iam-target-scope",
    title: "Qu'est-ce que le Périmètre cible (« Sur quoi ? ») ?",
    body: "Le périmètre cible désigne l'endroit précis de votre organisation où s'applique la règle d'habilitation : soit toute la plateforme, soit une Direction (BU) entière et ses équipes, soit un seul Espace de travail (équipe/projet). Par exemple, donner un droit à « Product Manager » sur le périmètre cible « Espace : MonCompte » signifie que ce droit ne s'exercera que dans l'espace MonCompte, sans donner accès aux autres espaces de l'entreprise.",
    category: "terms",
  },
  {
    sectionId: "iam-inheritance-block",
    title: "Effet de la règle (Autoriser, Interdire, Isoler ce périmètre)",
    body: "« Autoriser » accorde les actions cochées. « Interdire » est toujours prioritaire. « Isoler ce périmètre » coupe les accès généraux hérités de la Direction parente pour un espace confidentiel.",
    category: "terms",
  },
  {
    sectionId: "connectors-overview",
    title: "Connexion à vos outils et sources documentaires",
    body: "Enregistrez vos espaces documentaires, suivis de projets ou dépôts de code. Vos clés d'accès sont protégées dès l'enregistrement et ne sont jamais ré-affichées en clair.",
    category: "steps",
  },
  {
    sectionId: "ai-models-overview",
    title: "Modèles IA : Fournisseur, URL d'API, Authentification & Test de connexion",
    body: "Pour chaque niveau d'usage (Simple, Standard, Approfondi), renseignez : 1) le Fournisseur IA (ex. Anthropic, OpenAI, Mistral AI, Ollama local), 2) l'identifiant du modèle principal (et un modèle de secours optionnel), 3) l'URL de l'API (ex. https://api.anthropic.com/v1 ou http://localhost:11434/v1), et 4) le mode d'authentification (Clé d'API secrète, Variable serveur ou Serveur local sans clé). Cliquez sur « 🔌 Tester la connexion au modèle » avant d'enregistrer pour vérifier immédiatement la réponse du serveur.",
    category: "steps",
  },
  {
    sectionId: "packs-overview",
    title: "Packs métiers prêts à l'emploi",
    body: "Les Packs métiers sont fournis par la plateforme (ou conçus dans Mes Processus) et regroupent des processus, des agents spécialisés et un glossaire métier. Choisissez un périmètre (Plateforme entière, Direction ou Espace) puis activez ou désactivez le Pack en 1 clic.",
    category: "terms",
  },
  {
    sectionId: "workflows-overview",
    title: "Atelier de processus et règles de qualité",
    body: "Visualisez et adaptez l'enchaînement des étapes d'un processus. Les étapes marquées en violet demandent obligatoirement une rédaction personnelle avant de poursuivre.",
    category: "steps",
  },
  {
    sectionId: "audit-overview",
    title: "Journal d'activité et suivi budgétaire",
    body: "Consultez l'historique horodaté des décisions validées et définissez un plafond de dépense par espace pour éviter tout dépassement imprévu.",
    category: "faq",
  },
];

const CONFIGURATION_SECTIONS_EN: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "iam-org-tree",
    title: "Organization structure (Divisions / BUs & Workspaces)",
    body: "Structure your company into Divisions (BUs) and Workspaces (teams or projects). An item can only be deleted once no child workspaces or access rules depend on it.",
    category: "steps",
  },
  {
    sectionId: "iam-role-grants",
    title: "Access rules: Who? and On what?",
    body: "Each rule links a beneficiary (Role or User, e.g. Role: Chef1) to a target scope (Entire platform, BU, or Workspace, e.g. aqwZSX) and specifies granted permissions (Create, Read / View secrets, Update, Delete, Execute / Use, Delegate rights).",
    category: "terms",
  },
  {
    sectionId: "iam-target-scope",
    title: "What is Target scope ('On what?')?",
    body: "The target scope identifies the exact level of your organization where the permission rule applies: either the entire platform, a whole Division (BU) and its teams, or a single Workspace (team/project). For instance, granting a permission to 'Product Manager' on target scope 'Space: MyAccount' means that right only applies inside MyAccount, without granting access to other spaces.",
    category: "terms",
  },
  {
    sectionId: "iam-inheritance-block",
    title: "Rule effect (Allow, Deny, Isolate this scope)",
    body: "'Allow' grants the selected actions. 'Deny' always takes priority. 'Isolate this scope' stops broad permissions inherited from a parent BU on a confidential workspace.",
    category: "terms",
  },
  {
    sectionId: "connectors-overview",
    title: "Connecting your tools and document sources",
    body: "Register your documentation spaces, project trackers, or code repositories. Access keys are protected upon saving and never displayed in plain text again.",
    category: "steps",
  },
  {
    sectionId: "ai-models-overview",
    title: "AI Models: Provider, API URL, Authentication & Connection Test",
    body: "For each usage level (Simple, Standard, In-Depth), specify: 1) AI Provider (e.g. Anthropic, OpenAI, Mistral AI, local Ollama), 2) primary model ID (and optional backup model), 3) API Endpoint URL (e.g. https://api.anthropic.com/v1 or http://localhost:11434/v1), and 4) authentication mode (Secret API Key, Server environment variable, or Keyless local server). Click '🔌 Test model connection' before saving to verify server response.",
    category: "steps",
  },
  {
    sectionId: "packs-overview",
    title: "Ready-to-use Business Packs",
    body: "Business Packs are provided by the platform (or authored in My Processes) and bundle processes, specialized agents, and a domain glossary. Select a target scope (Entire Platform, Division, or Workspace) and enable or disable a Pack in 1 click.",
    category: "terms",
  },
  {
    sectionId: "workflows-overview",
    title: "Process studio and quality rules",
    body: "Inspect and tailor the sequence of process steps. Steps highlighted in violet require personal human authoring before the process can continue.",
    category: "steps",
  },
  {
    sectionId: "audit-overview",
    title: "Activity log and budget tracking",
    body: "Review the timestamped history of validated decisions and set a spending cap per workspace to prevent unexpected overruns.",
    category: "faq",
  },
];

const GENERAL_SECTIONS_FR: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "module-overview",
    title: "Repères de cet écran",
    body: "Cet écran présente les éléments rattachés à votre Espace actif. Vous pouvez changer d'Espace à tout moment depuis le sélecteur situé en haut à gauche.",
    category: "whatFor",
  },
  {
    sectionId: "cockpit-decisions",
    title: "Décisions en attente et relectures",
    body: "Le Cockpit regroupe uniquement les points qui demandent votre intervention : rédactions personnelles, arbitrages rapides entre deux options ou relectures détaillées de livrables.",
    category: "steps",
  },
  {
    sectionId: "assistant-modes",
    title: "Les 3 modes de réponse de Mon Assistant",
    body: "Choisissez « Réponse rapide » pour une question directe, « Avec un agent » pour mobiliser un outil connecté, ou « Analyse approfondie » pour croiser plusieurs points de vue avec citations vérifiées.",
    category: "steps",
  },
  {
    sectionId: "workspace-sources",
    title: "Sources de référence et documents de travail",
    body: "Rattachez vos sources documentaires à votre Espace et définissez où vos livrables validés doivent être enregistrés par défaut.",
    category: "terms",
  },
  {
    sectionId: "glossary-rules",
    title: "Glossaire métier et règles automatiques",
    body: "Définissez les termes clés de votre équipe et transformez vos règles métiers en vérifications automatiques exécutées à chaque étape.",
    category: "terms",
  },
];

const GENERAL_SECTIONS_EN: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "module-overview",
    title: "Screen overview",
    body: "This screen displays items linked to your active Workspace. You can switch Workspaces at any time using the selector in the top-left header.",
    category: "whatFor",
  },
  {
    sectionId: "cockpit-decisions",
    title: "Pending decisions and reviews",
    body: "The Cockpit gathers only items requiring your input: personal authoring entries, quick choices between two options, or detailed deliverable reviews.",
    category: "steps",
  },
  {
    sectionId: "assistant-modes",
    title: "My Assistant's 3 response modes",
    body: "Pick 'Fast response' for a direct question, 'With an agent' to use a connected tool, or 'In-depth analysis' to cross-check multiple perspectives with verified citations.",
    category: "steps",
  },
  {
    sectionId: "workspace-sources",
    title: "Reference sources and working documents",
    body: "Connect your document sources to your Workspace and choose where approved deliverables should be saved by default.",
    category: "terms",
  },
  {
    sectionId: "glossary-rules",
    title: "Business glossary and automated rules",
    body: "Define your team's key terms and turn business rules into automated checks executed at every step.",
    category: "terms",
  },
];

export function buildContextualHelpArticle({
  activeMenuKey,
  pathname,
  locale,
  title,
  defaultSummary,
}: BuildContextualHelpArticleParams): UiContextualHelpArticleView {
  const isFr = locale === "fr";
  const isConfigurationScreen =
    activeMenuKey === "configuration" ||
    pathname === "/settings" ||
    pathname === "/configuration";

  if (isConfigurationScreen) {
    return {
      resourceId: `help-${activeMenuKey}`,
      uri: `orcia://packs/core/help/${activeMenuKey}/${locale}`,
      title,
      version: "1.0.0",
      lang: locale,
      layer: "PACK",
      packName: "orcia-core",
      boundRoutes: [pathname ?? "/settings"],
      summaryWhatFor: isFr
        ? "Cet écran structure votre organisation (Directions / BU et Espaces), pilote vos règles d'habilitation (Créer, Lire / Voir les secrets, Modifier, Supprimer, Exécuter / Utiliser, Déléguer des droits), vos modèles IA et vos connecteurs."
        : "This screen structures your organization (BUs and Workspaces), governs permission rules (Create, Read / View secrets, Update, Delete, Execute / Use, Delegate rights), AI models, and connectors.",
      stepByStepItems: isFr
        ? [
            "1. Créez d'abord au moins une Direction (BU) ou un Espace (Équipe) dans la section 1. La section 2 se déverrouille dès qu'une unité d'organisation existe.",
            "2. Dans Habilitations, indiquez Qui ? (Bénéficiaire : Rôle ou Utilisateur, ex: Rôle : Chef1) et choisissez Sur quoi ? (Périmètre cible : Plateforme entière, Direction / BU ou Espace, ex: aqwZSX).",
            "3. Cochez les habilitations à attribuer (ou Tous) et choisissez l'effet de la règle (Autoriser, Interdire ou Isoler ce périmètre). Utilisez les cases à cocher de la liste pour supprimer une ou plusieurs règles.",
          ]
        : [
            "1. First create at least one Division (BU) or Workspace (Team) in section 1. Section 2 unlocks as soon as an organization unit exists.",
            "2. In Permissions, specify Who? (Beneficiary: Role or User, e.g. Role: Chef1) and select On what? (Target scope: Entire platform, BU, or Workspace, e.g. aqwZSX).",
            "3. Check the permissions to grant (or All) and choose the rule effect (Allow, Deny, or Isolate this scope). Use the list checkboxes to delete one or more rules.",
          ],
      keyTermsItems: isFr
        ? [
            "BU vs Espace (Équipe) : Une Direction (BU) est un pôle métier qui regroupe plusieurs Espaces. Un Espace correspond à une équipe ou un projet rattaché à une Direction.",
            "Protection contre les suppressions accidentelles : Impossible de supprimer une Direction (BU) ou un Espace tant que des sous-espaces ou des règles d'habilitation y sont rattachés.",
            "Qui ? (Bénéficiaire) vs Sur quoi ? (Périmètre cible) : Dans « Rôle : Chef1 → aqwZSX », Chef1 est le Bénéficiaire (le rôle ou l'utilisateur qui reçoit le droit) et aqwZSX est le Périmètre cible (la Direction, l'Espace ou toute la plateforme où s'applique ce droit).",
            "Qu'est-ce que le Périmètre cible (« Sur quoi ? ») ? : Le périmètre cible désigne l'endroit précis de votre organisation où s'applique la règle d'habilitation : soit toute la plateforme, soit une Direction (BU) entière et ses équipes, soit un seul Espace de travail.",
            "Les 6 habilitations : Créer, Lire / Voir les secrets (consulter la configuration), Modifier, Supprimer, Exécuter / Utiliser (utiliser un agent, modèle ou connecteur sans voir ses clés secrètes), Déléguer des droits.",
            "Autoriser : Accorde explicitement les actions cochées au bénéficiaire sur le périmètre cible.",
            "Interdire (prioritaire) : Bloque explicitement ces actions. Une interdiction l'emporte toujours sur une autorisation.",
            "Isoler ce périmètre (INHERITANCE_BLOCK) : N'applique pas les droits hérités de la Direction parente ou de la plateforme sur cet espace confidentiel, afin de repartir d'une feuille blanche locale.",
          ]
        : [
            "BU vs Workspace (Team): A BU is a business division grouping multiple Workspaces. A Workspace is a team scope linked to a parent BU.",
            "Accidental deletion protection: A BU or Workspace cannot be deleted while child workspaces or permission rules still depend on it.",
            "Who? (Beneficiary) vs On what? (Target scope): In 'Role: Chef1 → aqwZSX', Chef1 is the Beneficiary (the role or user receiving the right) and aqwZSX is the Target scope (the BU, Workspace, or entire platform).",
            "What is Target scope ('On what?')?: The target scope identifies the exact level of your organization where the permission rule applies: the entire platform, a Division (BU), or a single Workspace.",
            "The 6 permissions: Create, Read / View secrets, Update, Delete, Execute / Use (run an agent/model/connector without viewing secret keys), Delegate rights.",
            "Allow: Explicitly grants the checked actions to the beneficiary on the target scope.",
            "Deny (Priority override): Explicitly blocks the checked actions. Deny always overrides any Allow.",
            "Isolate this scope (INHERITANCE_BLOCK): Stops automatic inheritance of permissions from parent levels (Entire platform or parent BU) on this scope, starting from a clean local slate.",
          ],
      faqItems: isFr
        ? [
            "Pourquoi la section 2 est-elle grisée au démarrage ? → Tant qu'aucune Direction (BU) ni aucun Espace n'est créé dans la section 1, il n'existe aucun périmètre d'organisation sur lequel appliquer des règles.",
            "Pourquoi ne puis-je pas supprimer une BU ou un Espace ? → Pour éviter d'isoler des Espaces enfants ou des règles d'habilitation qui y font référence. Supprimez ou détachez d'abord les éléments dépendants.",
            "Quelle est la différence entre Exécuter / Utiliser et Lire / Voir les secrets ? → Exécuter / Utiliser permet de mobiliser un modèle IA ou un connecteur dans un processus sans pouvoir afficher sa clé secrète.",
            "Quand choisir « Isoler ce périmètre » ? → Lorsqu'un Espace confidentiel ne doit plus hériter des accès larges accordés au niveau de sa Direction (BU) parente.",
          ]
        : [
            "Why is section 2 greyed out initially? → Until at least one Division (BU) or Space is created in section 1, there is no organizational scope to attach rules to.",
            "Why can't I delete a BU or Workspace? → To prevent isolating child Workspaces or permission rules that reference it. Remove dependent items first.",
            "What is the difference between Execute / Use and Read / View secrets? → Execute / Use lets a user run an AI model or connector without viewing its secret key.",
            "When should I use 'Isolate this scope'? → When a confidential Workspace must stop inheriting broad permissions granted at its parent BU level.",
          ],
      sections: isFr ? CONFIGURATION_SECTIONS_FR : CONFIGURATION_SECTIONS_EN,
      casKey: "cas/help_contextual_v1",
      sha256: "sha256_contextual_help_v1",
      previousVersion: "0.9.0",
    };
  }

  return {
    resourceId: `help-${activeMenuKey}`,
    uri: `orcia://packs/core/help/${activeMenuKey}/${locale}`,
    title,
    version: "1.0.0",
    lang: locale,
    layer: "PACK",
    packName: "orcia-core",
    boundRoutes: [pathname ?? "/cockpit"],
    summaryWhatFor: defaultSummary,
    stepByStepItems: isFr
      ? [
          "1. Sélectionnez votre Espace de travail actif dans la barre supérieure.",
          "2. Utilisez la recherche globale (⌘K) ou Mon Assistant pour interroger vos documents.",
          "3. Traitez vos décisions en attente ou lancez un processus étape par étape.",
        ]
      : [
          "1. Select your active Workspace in the top header bar.",
          "2. Use global search (⌘K) or My Assistant to query your documents.",
          "3. Resolve pending decisions or start a step-by-step process.",
        ],
    keyTermsItems: isFr
      ? [
          "Rédaction personnelle (Violet) : Étape réservée à votre saisie directe pour fixer les objectifs.",
          "Validation préalable : Toute modification dans vos outils externes vous est présentée pour accord avant envoi.",
          "Règle métier : Directive de votre équipe vérifiée automatiquement à chaque étape.",
        ]
      : [
          "Personal authoring (Violet): Step reserved for your direct input to set goals.",
          "Prior review: Any change to external tools is shown for your approval before sending.",
          "Business rule: Team guideline automatically checked at every step.",
        ],
    faqItems: isFr
      ? [
          "Comment adapter le ton de Mon Assistant ? → Cliquez sur ⚙ Réglages de Mon Assistant.",
          "Où voir le détail d'une option de l'écran ? → Cliquez sur l'icône ⓘ à côté de l'intitulé pour afficher son explication ici.",
        ]
      : [
          "How do I adjust My Assistant's tone? → Click ⚙ My Assistant Settings.",
          "Where can I read more about a screen option? → Click the ⓘ icon next to any heading to display its explanation here.",
        ],
    sections: isFr ? GENERAL_SECTIONS_FR : GENERAL_SECTIONS_EN,
    casKey: "cas/help_contextual_v1",
    sha256: "sha256_contextual_help_v1",
    previousVersion: "0.9.0",
  };
}
