import type {
  EightFixedMenuKey,
  UiContextualHelpArticleView,
} from "@orcia/ui";
import {
  getContextualHelpSectionsForRoute,
  normalizeCanonicalHelpRoute,
} from "./_contextualHelpSections";

export interface BuildContextualHelpArticleParams {
  readonly activeMenuKey: EightFixedMenuKey;
  readonly pathname: string | undefined;
  readonly locale: "fr" | "en";
  readonly title: string;
  readonly defaultSummary: string;
}

interface RouteFallbackNarrative {
  readonly summaryWhatFor: string;
  readonly steps: readonly string[];
  readonly realExampleText: string;
  readonly commonPitfallsItems: readonly string[];
}

const ROUTE_FALLBACKS_FR: Readonly<Record<string, RouteFallbackNarrative>> = {
  "/cockpit": {
    summaryWhatFor:
      "Le Cockpit regroupe au même endroit les décisions qui attendent votre validation, le lancement rapide de processus et l'avancement du démarrage de la plateforme.",
    steps: [
      "Vérifiez votre contexte actif (Équipe ou Espace) en haut de la barre latérale gauche pour filtrer les décisions affichées.",
      "Suivez le guide d'accostage si une étape de mise en route reste ouverte, ou lancez directement un processus depuis la barre d'action.",
      "Traitez les demandes en attente : rédigez votre cadrage humain ou tranchez entre les options proposées en motivant votre choix.",
    ],
    realExampleText:
      "Après une analyse automatisée de conformité, Nadia ouvre le Cockpit le matin, voit un arbitrage en attente entre deux options d'architecture, saisit sa justification en une phrase et valide : le processus reprend immédiatement jusqu'au livrable final.",
    commonPitfallsItems: [
      "Le bouton de validation reste grisé sur la carte violette : vérifiez que votre rédaction personnelle comporte bien au moins 30 caractères.",
      "Aucun espace disponible pour lancer un processus : créez d'abord un Espace de travail dans « Mes Espaces » et rattachez-le à une Équipe.",
    ],
  },
  "/assistant": {
    summaryWhatFor:
      "Mon Assistant répond à vos questions à partir des documents de votre Espace actif, cite chaque source vérifiée et organise vos échanges en dossiers thématiques avec notes permanentes.",
    steps: [
      "Choisissez votre modèle (Rapide, Polyvalent ou Raisonnement avancé) et votre mode de réflexion (Standard ou Approfondi — ex. « Polyvalent · Standard ») via le sélecteur à côté du bouton d'envoi.",
      "Rédigez votre question (tapez @ pour appeler un agent ou / pour déclencher une compétence) puis envoyez.",
      "Ouvrez « Dossiers » si vous souhaitez attacher l'échange à un sujet précis et y épingler des consignes permanentes.",
    ],
    realExampleText:
      "Marc sélectionne l'Espace « Produit Paiement », ouvre le dossier « Conformité 2026 » contenant ses consignes permanentes, puis demande une synthèse des risques : Mon Assistant répond avec des pastilles de citations cliquables pointant vers les documents exacts de l'Espace.",
    commonPitfallsItems: [
      "La zone de saisie est verrouillée : vérifiez qu'un modèle d'analyse documentaire et un modèle de dialogue sont configurés dans Configuration › Modèles IA.",
      "Les notes du dossier ne semblent pas prises en compte : cliquez sur « Enregistrer les notes » dans le tiroir du dossier actif avant de poser votre question.",
    ],
  },
  "/inbox": {
    summaryWhatFor:
      "La Boîte de Réception rassemble les tâches prises en charge, les demandes de relecture et les alertes d'équipe de votre Espace actif pour coordonner le travail sans doublon.",
    steps: [
      "Vérifiez votre Espace actif dans la barre latérale gauche pour filtrer les notifications affichées.",
      "Prenez en charge une tâche disponible afin de prévenir le reste de l'équipe que vous vous en occupez.",
      "Libérez la tâche si vous devez la réassigner ou ouvrez directement le Cockpit pour finaliser la décision.",
    ],
    realExampleText:
      "Lorsqu'une analyse de conformité arrive en attente de relecture dans l'Espace « Produit Paiement », Nadia clique sur « Prendre en charge » depuis la Boîte de Réception : ses collègues voient aussitôt que la revue est en cours, évitant tout double traitement.",
    commonPitfallsItems: [
      "Aucune tâche affichée dans la liste : vérifiez qu'un Espace de travail est bien sélectionné ou qu'un processus a généré une attente d'équipe.",
      "Vous cherchez l'historique complet des opérations passées : ouvrez le Journal d'Activité pour consulter l'historique détaillé.",
    ],
  },
  "/spaces": {
    summaryWhatFor:
      "Mes Espaces regroupe vos Espaces de travail collectifs, privés ou confidentiels, leurs sources documentaires, les règles héritées de votre unité d'organisation et l'accès au Glossaire métier.",
    steps: [
      "Filtrez la vue entre « Tous », « Espaces d'Équipe » et « Mes Espaces Privés », ou créez un nouvel Espace rattaché à une Équipe existante.",
      "Ouvrez un Espace pour ajuster son niveau de confidentialité (Standard, Confidentiel isolé ou Privé) et sa phase de cycle de vie.",
      "Accédez aux onglets « Sources » pour connecter vos documents, ou cliquez sur « Glossaire métier » pour consulter les définitions de l'Espace.",
    ],
    realExampleText:
      "L'équipe Sinistres crée un Espace « Audit Partenaire Q4 » rattaché à la Direction Opérations, le place en mode Confidentiel isolé afin qu'aucune personne extérieure n'y accède, puis y connecte le dossier de suivi dédié.",
    commonPitfallsItems: [
      "Quelle est la différence entre une unité d'organisation et un Espace de travail ? L'unité d'organisation définit qui travaille et porte le budget, l'Espace de travail porte vos sources et livrables.",
      "Impossible de créer un Espace collectif : assurez-vous qu'au moins une Équipe a été créée au préalable dans Configuration › Mon Organisation.",
    ],
  },
};

const ROUTE_FALLBACKS_EN: Readonly<Record<string, RouteFallbackNarrative>> = {
  "/cockpit": {
    summaryWhatFor:
      "The Cockpit brings together decisions awaiting your review, quick process launches, and your platform onboarding progress in one place.",
    steps: [
      "Check your active context (Team or Space) at the top of the left sidebar to filter visible decisions.",
      "Follow the onboarding guide if setup steps remain open, or launch a process directly from the action bar.",
      "Handle pending items: write your human framing anchor or resolve option tie-breaks with a short justification.",
    ],
    realExampleText:
      "After an automated compliance check, Nadia opens the Cockpit in the morning, sees a pending choice between two architecture options, writes a one-sentence justification, and confirms: the process immediately resumes to completion.",
    commonPitfallsItems: [
      "The submit button on the violet card stays disabled: verify that your personal authoring text has at least 30 characters.",
      "No workspace available to start a process: create a Workspace first in \"My Spaces\" and link it to a Team.",
    ],
  },
  "/assistant": {
    summaryWhatFor:
      "My Assistant answers questions grounded in your active Workspace documents, cites every verified source, and organizes discussions into folders with permanent notes.",
    steps: [
      "Choose your model (Fast, Versatile, or Advanced Reasoning) and your thinking mode (Standard or In-Depth — e.g. \"Versatile · Standard\") using the selector next to the send button.",
      "Type your question (use @ to mention an agent or / to run a skill) and send.",
      "Open \"Folders\" to attach your conversation to a topic and pin permanent instructions that stay active across questions.",
    ],
    realExampleText:
      "Marc selects the \"Payments Product\" Space, opens the \"2026 Compliance\" folder with its pinned guidelines, and asks for a risk summary: My Assistant responds with clickable citation pills pointing straight to the verified Space documents.",
    commonPitfallsItems: [
      "The prompt input is locked: verify that both a document indexing model and a chat model are configured in Configuration › AI Models.",
      "Folder notes do not seem applied: click \"Save notes\" inside the active folder drawer before sending your next question.",
    ],
  },
  "/inbox": {
    summaryWhatFor:
      "The Inbox gathers claimed tasks, review requests, and team alerts for your active Space so your team coordinates work without duplication.",
    steps: [
      "Check your active Space in the left sidebar to filter the displayed notifications.",
      "Claim an available task so teammates immediately know you are handling it.",
      "Release the task if you need to hand it off, or open the Cockpit directly to finalize the decision.",
    ],
    realExampleText:
      "When a compliance review arrives in the \"Payments Product\" Space, Nadia clicks \"Claim\" in the Inbox: her teammates instantly see the review is in progress, preventing duplicate work.",
    commonPitfallsItems: [
      "No tasks appear in the list: verify that a Space is selected or that a process has emitted a team notification.",
      "Looking for the full historical audit trail: open the Activity Log to inspect past operations.",
    ],
  },
  "/spaces": {
    summaryWhatFor:
      "My Spaces gathers your team, private, or confidential Workspaces, their document sources, rules inherited from your organizational unit, and access to the Business Glossary.",
    steps: [
      "Filter between \"All\", \"Team Spaces\", and \"My Private Spaces\", or create a new Workspace linked to an existing Team.",
      "Open a Workspace to adjust its confidentiality level (Standard, Confidential isolated, or Private) and lifecycle phase.",
      "Use the \"Sources\" tab to connect your documents, or click \"Business Glossary\" to inspect and enrich Space definitions.",
    ],
    realExampleText:
      "The Claims team creates a \"Q4 Partner Audit\" Space linked to Operations, sets it to Confidential isolated so no external user can read it, and connects its dedicated tracking folder.",
    commonPitfallsItems: [
      "Difference between an organizational unit and a Workspace: the organizational unit defines who works and owns the budget; the Workspace holds your sources and deliverables.",
      "Cannot create a team Space: make sure at least one Team exists first in Configuration › My Organization.",
    ],
  },
};

export function buildContextualHelpArticle({
  activeMenuKey,
  pathname,
  locale,
  title,
  defaultSummary,
}: BuildContextualHelpArticleParams): UiContextualHelpArticleView {
  const isFr = locale === "fr";
  const canonicalRoute = normalizeCanonicalHelpRoute(pathname);
  const routeSections = getContextualHelpSectionsForRoute(pathname, locale);

  if (canonicalRoute === "/settings") {
    return {
      resourceId: "help-base-settings",
      uri: `orcia://system/help/settings/${locale}`,
      title,
      version: "",
      lang: locale,
      layer: "BASE",
      packName: "core",
      boundRoutes: [pathname ?? "/settings"],
      summaryWhatFor: isFr
        ? "Cet écran structure votre organisation (Directions / BU et Équipes), gère l'annuaire des comptes et pilote vos règles d'habilitation, vos modèles IA et vos connecteurs."
        : "This screen structures your organization (BUs and Teams), manages the accounts directory, and governs permission rules, AI models, and connectors.",
      stepByStepItems: isFr
        ? [
            "Gérez vos comptes utilisateurs et comptes techniques dans l'annuaire, puis consultez la matrice des 7 rôles officiels.",
            "Dans Exceptions & Isolation SecOps, indiquez Qui ? (Rôle ou Compte) et choisissez Sur quoi ? (Périmètre cible).",
            "Dans Modèles IA, renseignez vos fournisseurs (dialogue et recherche documentaire) puis testez la connexion avant d'enregistrer.",
          ]
        : [
            "Manage human and service accounts in the directory, then review the native 7-role matrix.",
            "In SecOps Exceptions & Isolation, specify Who? (Role or Account) and select On what? (Target scope).",
            "In AI Models, configure your chat and document indexing providers and test the connection before saving.",
          ],
      realExampleText: isFr
        ? "Lors de l'installation initiale, Alice ouvre Configuration › Modèles IA, ajoute son fournisseur principal et un modèle de recherche documentaire, teste la connexion avec succès, puis passe à « Mon Organisation » pour créer la Direction Produit et l'Équipe Paiement."
        : "During initial setup, Alice opens Configuration › AI Models, adds her primary provider and an indexing model, tests the connection, then opens My Organization to create the Product Division and Payments Team.",
      commonPitfallsItems: isFr
        ? [
            "Une clé secrète n'apparaît plus après enregistrement : par sécurité, les jetons et clés API sont protégés en écriture seule et ne sont jamais ré-affichés en clair.",
            "Impossible de supprimer une Direction ou une Équipe : détachez d'abord les Équipes et règles d'habilitation qui y font référence.",
          ]
        : [
            "A secret key disappears after saving: for security, API keys and tokens are strictly write-only and never displayed again.",
            "Cannot delete a Division or Team: remove dependent child Teams or permission rules first.",
          ],
      keyTermsItems: [],
      faqItems: [],
      sections: routeSections,
      casKey: "",
      sha256: "",
      previousVersion: null,
    };
  }

  const narrative = (isFr ? ROUTE_FALLBACKS_FR : ROUTE_FALLBACKS_EN)[canonicalRoute];

  return {
    resourceId: `help-${activeMenuKey}`,
    uri: `orcia://system/help/${activeMenuKey}/${locale}`,
    title,
    version: "",
    lang: locale,
    layer: "BASE",
    packName: "core",
    boundRoutes: [pathname ?? canonicalRoute],
    summaryWhatFor: narrative?.summaryWhatFor ?? defaultSummary,
    stepByStepItems: narrative?.steps ?? (
      isFr
        ? [
            "Vérifiez votre Espace ou périmètre actif dans la barre latérale gauche.",
            "Utilisez la recherche globale (⌘K) pour retrouver rapidement vos documents et processus.",
            "Consultez les actions principales de cet écran et sollicitez Mon Assistant si besoin.",
          ]
        : [
            "Verify your active Space or scope in the left sidebar.",
            "Use global search (⌘K) to quickly find documents and processes.",
            "Review the main actions on this screen and ask My Assistant if needed.",
          ]
    ),
    realExampleText: narrative?.realExampleText ?? null,
    commonPitfallsItems: narrative?.commonPitfallsItems ?? [],
    keyTermsItems: [],
    faqItems: [],
    sections: routeSections,
    casKey: "",
    sha256: "",
    previousVersion: null,
  };
}
