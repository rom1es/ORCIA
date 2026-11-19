import type {
  EightFixedMenuKey,
  UiContextualHelpArticleView,
} from "@orcia/ui";
import {
  CONFIGURATION_SECTIONS_EN,
  CONFIGURATION_SECTIONS_FR,
  GENERAL_SECTIONS_EN,
  GENERAL_SECTIONS_FR,
} from "./_contextualHelpSections";

export interface BuildContextualHelpArticleParams {
  readonly activeMenuKey: EightFixedMenuKey;
  readonly pathname: string | undefined;
  readonly locale: "fr" | "en";
  readonly title: string;
  readonly defaultSummary: string;
}

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
    pathname === "/configuration" ||
    pathname === "/organization";

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
        ? "Cet écran structure votre organisation (Directions / BU et Équipes), gère l'annuaire des comptes et pilote vos règles d'habilitation (Créer, Consulter les ressources, Modifier, Supprimer, Exécuter / Utiliser, Déléguer des droits), vos modèles IA et vos connecteurs."
        : "This screen structures your organization (BUs and Teams), manages the accounts directory, and governs permission rules (Create, Read & view resources, Update, Delete, Execute / Use, Delegate rights), AI models, and connectors.",
      stepByStepItems: isFr
        ? [
            "1. Gérez vos comptes utilisateurs et comptes techniques dans l'annuaire, puis consultez la matrice des 7 rôles officiels de la plateforme.",
            "2. Dans Exceptions & Isolation SecOps, indiquez Qui ? (Rôle ou Compte, ex: Rôle : Responsable Produit) et choisissez Sur quoi ? (Périmètre cible : Plateforme entière, Direction / BU, Équipe ou Espace de travail, ex: Équipe Paiement).",
            "3. Cochez les habilitations à attribuer et choisissez l'effet de la règle (Autoriser, Interdire ou Isoler ce périmètre). Utilisez les cases à cocher de la liste pour supprimer une ou plusieurs règles.",
          ]
        : [
            "1. Manage human and service accounts in the directory, then review the native 7-role matrix.",
            "2. In SecOps Exceptions & Isolation, specify Who? (Role or Account, e.g. Role: Product Manager) and select On what? (Target scope: Entire platform, BU, Team, or Workspace, e.g. Payments Team).",
            "3. Check the permissions to grant and choose the rule effect (Allow, Deny, or Isolate this scope). Use the list checkboxes to delete one or more rules.",
          ],
      keyTermsItems: isFr
        ? [
            "BU vs Équipe vs Espace de travail : Une Direction (BU) est un pôle métier qui regroupe plusieurs Équipes. Une Équipe est une unité d'organisation rattachée à une Direction, tandis qu'un Espace de travail (géré dans 📦 Mes Espaces) héberge les sources et exécutions d'un projet ou produit.",
            "Protection contre les suppressions accidentelles : Impossible de supprimer une Direction (BU) ou une Équipe tant que des Équipes rattachées ou des règles d'habilitation y font référence.",
            "Qui ? (Bénéficiaire) vs Sur quoi ? (Périmètre cible) : Dans « Rôle : Responsable Produit → Équipe Paiement », Responsable Produit est le Bénéficiaire (le rôle ou l'utilisateur qui reçoit le droit) et Équipe Paiement est le Périmètre cible (la Direction, l'Équipe, l'Espace de travail ou toute la plateforme où s'applique ce droit).",
            "Qu'est-ce que le Périmètre cible (« Sur quoi ? ») ? : Le périmètre cible désigne l'endroit précis de votre organisation où s'applique la règle d'habilitation : soit toute la plateforme, soit une Direction (BU) entière et ses équipes, soit une Équipe, soit un seul Espace de travail.",
            "Les 6 habilitations : Créer, Consulter les ressources (métadonnées et configuration hors secrets — aucun secret n'est jamais lisible après enregistrement), Modifier, Supprimer, Exécuter / Utiliser, Déléguer des droits.",
            "Autoriser : Accorde explicitement les actions cochées au bénéficiaire sur le périmètre cible.",
            "Interdire (prioritaire) : Bloque explicitement ces actions. Une interdiction l'emporte toujours sur une autorisation.",
            "Isoler ce périmètre (INHERITANCE_BLOCK) : N'applique pas les droits hérités de la Direction parente ou de la plateforme sur cette Équipe ou cet Espace confidentiel, afin de repartir d'une feuille blanche locale.",
          ]
        : [
            "BU vs Team vs Workspace: A BU is a business division grouping multiple Teams. A Team is an organizational unit linked to a parent BU, whereas a Workspace (managed in 📦 My Workspaces) hosts the sources and runs of a project or product.",
            "Accidental deletion protection: A BU or Team cannot be deleted while child Teams or permission rules still depend on it.",
            "Who? (Beneficiary) vs On what? (Target scope): In 'Role: Product Manager → Payments Team', Product Manager is the Beneficiary (the role or user receiving the right) and Payments Team is the Target scope (the BU, Team, Workspace, or entire platform).",
            "What is Target scope ('On what?')?: The target scope identifies the exact level of your organization where the permission rule applies: the entire platform, a Division (BU), a Team, or a single Workspace.",
            "The 6 permissions: Create, Read & view resources (metadata and configuration without secrets — secret keys are write-only and never readable after saving), Update, Delete, Execute / Use, Delegate rights.",
            "Allow: Explicitly grants the checked actions to the beneficiary on the target scope.",
            "Deny (Priority override): Explicitly blocks the checked actions. Deny always overrides any Allow.",
            "Isolate this scope (INHERITANCE_BLOCK): Stops automatic inheritance of permissions from parent levels (Entire platform or parent BU) on this scope, starting from a clean local slate.",
          ],
      faqItems: isFr
        ? [
            "Pourquoi le volet Exceptions & Isolation SecOps est-il réservé aux responsables sécurité ? → Pour confiner la création d'exceptions fines et de blocages d'héritage aux titulaires du rôle Responsable Sécurité (SecOps).",
            "Pourquoi ne puis-je pas supprimer une BU ou une Équipe ? → Pour éviter d'isoler des Équipes rattachées ou des règles d'habilitation qui y font référence. Supprimez ou détachez d'abord les éléments dépendants.",
            "Quelle est la différence entre Exécuter / Utiliser et Consulter les ressources ? → Exécuter / Utiliser permet de mobiliser un modèle IA ou un connecteur dans un processus ; Consulter les ressources affiche la configuration sans jamais exposer les clés secrètes (strictement non lisibles après enregistrement).",
            "Quand choisir « Isoler ce périmètre » ? → Lorsqu'une Équipe ou un Espace confidentiel ne doit plus hériter des accès larges accordés au niveau de sa Direction (BU) parente.",
          ]
        : [
            "Why is the SecOps Exceptions & Isolation drawer restricted to security officers? → To confine fine-grained exceptions and inheritance blocks to Security Officer (SecOps) role holders.",
            "Why can't I delete a BU or Team? → To prevent isolating child Teams or permission rules that reference it. Remove dependent items first.",
            "What is the difference between Execute / Use and Read & view resources? → Execute / Use lets a user run an AI model or connector; Read & view resources displays configuration metadata while secrets remain strictly write-only and never readable.",
            "When should I use 'Isolate this scope'? → When a confidential Team or Workspace must stop inheriting broad permissions granted at its parent BU level.",
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
