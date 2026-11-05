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
    body: "Chaque règle associe un bénéficiaire (Rôle ou Utilisateur, ex. ROLE:Chef1) à un périmètre cible (Plateforme Globale, BU ou Espace, ex. aqwZSX) et précise les actions permises (créer, lire, modifier, supprimer, utiliser, déléguer).",
    category: "terms",
  },
  {
    sectionId: "iam-inheritance-block",
    title: "Effet de la règle (Autoriser, Interdire, Cloisonner)",
    body: "« Autoriser » accorde les actions choisies. « Interdire » est toujours prioritaire. « Cloisonner l'héritage » (INHERITANCE_BLOCK) coupe les accès généraux hérités de la BU parente pour un espace confidentiel.",
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
    title: "Niveaux de modèles IA (Simple, Standard, Approfondi)",
    body: "Associez un modèle IA principal (et un modèle de secours) à chaque niveau de besoin. En configurant au moins deux fournisseurs indépendants, vous activez les revues croisées automatiques.",
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
    body: "Each rule links a beneficiary (Role or User, e.g. ROLE:Chef1) to a target scope (Global Platform, BU, or Workspace, e.g. aqwZSX) and specifies allowed actions (create, read, update, delete, execute, grant).",
    category: "terms",
  },
  {
    sectionId: "iam-inheritance-block",
    title: "Rule effect (Allow, Deny, Block inheritance)",
    body: "'Allow' grants the selected actions. 'Deny' always takes priority. 'Block parent inheritance' (INHERITANCE_BLOCK) stops broad permissions inherited from a parent BU on a confidential workspace.",
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
    title: "AI model levels (Simple, Standard, In-Depth)",
    body: "Assign a primary AI model (and a backup model) to each analysis level. Configuring at least two independent providers unlocks cross-checked reviews.",
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
        ? "Cet écran structure votre organisation (BU et Espaces), pilote vos règles d'habilitation (les 6 actions : create, read, update, delete, execute, grant), vos modèles IA et vos connecteurs."
        : "This screen structures your organization (BUs and Workspaces), governs permission rules (the 6 actions: create, read, update, delete, execute, grant), AI models, and connectors.",
      stepByStepItems: isFr
        ? [
            "1. Créez vos BU (Directions / Pôles), puis créez vos Espaces (Équipes) en les rattachant à leur BU parente. La suppression est protégée tant que des éléments y sont rattachés.",
            "2. Dans Habilitations, indiquez Qui ? (Bénéficiaire : Rôle ou Utilisateur, ex: ROLE:Chef1) et Sur quoi ? (Périmètre cible : GLOBAL, BU ou Espace, ex: aqwZSX).",
            "3. Cochez les actions autorisées (ou Tous) et choisissez l'effet (ALLOW, DENY ou INHERITANCE_BLOCK). Utilisez les cases à cocher de la liste pour supprimer une ou plusieurs règles.",
          ]
        : [
            "1. Create your BUs (Business Units), then create your Workspaces (Teams) linked to their parent BU. Deletion is protected while dependent items exist.",
            "2. In Permissions, specify Who? (Beneficiary: Role or User, e.g. ROLE:Chef1) and On what? (Target scope: GLOBAL, BU, or Workspace, e.g. aqwZSX).",
            "3. Check allowed actions (or All) and choose the effect (ALLOW, DENY, or INHERITANCE_BLOCK). Use the list checkboxes to delete one or more rules.",
          ],
      keyTermsItems: isFr
        ? [
            "BU vs Espace (Équipe) : Une BU est une direction ou pôle métier qui regroupe plusieurs Espaces. Un Espace correspond à une équipe ou un périmètre de travail rattaché à une BU.",
            "Protection contre les suppressions accidentelles : Impossible de supprimer une BU ou un Espace tant que des sous-espaces ou des règles d'habilitation y sont rattachés.",
            "Qui ? (Bénéficiaire) vs Sur quoi ? (Périmètre cible) : Dans « ROLE:Chef1 → aqwZSX », Chef1 est le Bénéficiaire (le rôle ou l'utilisateur qui reçoit le droit) et aqwZSX est le Périmètre cible (la BU, l'Espace ou la ressource sur laquelle s'applique ce droit).",
            "Les 6 actions d'habilitation : create (créer), read (consulter la configuration), update (modifier), delete (supprimer), execute (utiliser un agent/modèle/connecteur sans voir ses clés secrètes), grant (déléguer ses droits).",
            "ALLOW (Autoriser) : Accorde explicitement les actions cochées au bénéficiaire sur le périmètre cible.",
            "DENY (Interdire — prioritaire) : Refuse explicitement les actions cochées. Un refus l'emporte toujours sur une autorisation.",
            "INHERITANCE_BLOCK (Bloquer l'héritage parent) : Coupe la transmission automatique des droits hérités des niveaux supérieurs (Plateforme Globale ou BU parente) sur ce périmètre, afin de repartir d'une feuille blanche locale.",
          ]
        : [
            "BU vs Workspace (Team): A BU is a business division grouping multiple Workspaces. A Workspace is a team scope linked to a parent BU.",
            "Accidental deletion protection: A BU or Workspace cannot be deleted while child workspaces or permission rules still depend on it.",
            "Who? (Beneficiary) vs On what? (Target scope): In 'ROLE:Chef1 → aqwZSX', Chef1 is the Beneficiary (the role or user receiving the right) and aqwZSX is the Target scope (the BU, Workspace, or resource).",
            "The 6 permission actions: create, read (view configuration), update, delete, execute (run an agent/model/connector without viewing secret keys), grant (delegate rights).",
            "ALLOW: Explicitly grants the checked actions to the beneficiary on the target scope.",
            "DENY (Priority override): Explicitly denies the checked actions. DENY always overrides any ALLOW.",
            "INHERITANCE_BLOCK (Block parent inheritance): Stops automatic inheritance of permissions from parent levels (Global Platform or parent BU) on this scope, starting from a clean local slate.",
          ],
      faqItems: isFr
        ? [
            "Pourquoi ne puis-je pas supprimer une BU ou un Espace ? → Pour éviter d'isoler des Espaces enfants ou des règles d'habilitation qui y font référence. Supprimez ou détachez d'abord les éléments dépendants.",
            "Quelle est la différence entre execute et read ? → execute permet d'utiliser un modèle IA ou un connecteur dans un processus sans pouvoir afficher sa clé secrète (read).",
            "Quand utiliser INHERITANCE_BLOCK ? → Lorsqu'un Espace confidentiel ne doit plus hériter des accès larges accordés au niveau de sa BU parente.",
          ]
        : [
            "Why can't I delete a BU or Workspace? → To prevent isolating child Workspaces or permission rules that reference it. Remove dependent items first.",
            "What is the difference between execute and read? → execute lets a user run an AI model or connector without viewing its secret key (read).",
            "When should I use INHERITANCE_BLOCK? → When a confidential Workspace must stop inheriting broad permissions granted at its parent BU level.",
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
