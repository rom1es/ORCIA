import type { ShowcasePublicDictionary } from "./showcase_labels";
import { SHOWCASE_CHANGELOG_FR } from "./showcase_changelog_labels";

export const SHOWCASE_LABELS_FR: ShowcasePublicDictionary = {
  heroTitle: "Site de Présentation & Documentation Vivante d'ORCIA",
  heroSubtitle:
    "Explorez ORCIA à travers 4 espaces structurés : Vision & Pilotage Humain, Guide Fonctionnel des 9 Écrans, Architecture & Choix Techniques sous le capot et Historique des Évolutions synchronisé.",
  heroHelpLabel:
    "Comprendre l'organisation en 4 onglets du site de présentation ORCIA",
  syncedBadgePrefix: "Synchronisé :",
  exportStandaloneButton: "⬇ Exporter le site HTML autonome",
  exportBannerMessage:
    "Export HTML5 autonome prêt : fichier téléchargé pour consultation hors ligne.",
  tabsAriaLabel: "Navigation des 4 espaces du site de présentation ORCIA",
  tabMacroLabel: "1. Vision & Pilotage Humain (Macro)",
  tabFeaturesLabel: "2. Fonctionnalités & Écrans (Guide Fonctionnel)",
  tabArchitectureLabel: "3. Architecture & Choix Techniques (Sous le Capot)",
  tabChangelogLabelTemplate: "4. Historique des Évolutions ({count})",
  macro: {
    whyTitle:
      "1.1 Pourquoi ORCIA ? Orchestrer Processus, Contexte documentaire et Agents spécialisés sous conduite humaine",
    whySubtitle:
      "Sortir des discussions éphémères isolées pour bâtir des livrables d'entreprise fiables, traçables et gouvernés par vos équipes.",
    whyCards: [
      {
        title: "Processus Métiers Structurés",
        description:
          "Vos travaux complexes avancent étape par étape selon des contrats de livrables précis, capables de se mettre en pause le temps d'une décision humaine et de reprendre sans jamais perdre le fil.",
      },
      {
        title: "Contexte Documentaire & Glossaire Vivant",
        description:
          "Chaque étape s'appuie exclusivement sur les sources documentaires rattachées à votre Espace de travail et sur le glossaire métier officiel de votre organisation, avec alerte immédiate si un document est obsolète.",
      },
      {
        title: "Agents Spécialisés Gouvernés",
        description:
          "Des agents dotés de compétences ciblées préparent les analyses, vérifient la cohérence et synthétisent les options, tout en respectant strictement les droits d'accès de chaque collaborateur.",
      },
    ],
    humanLedTitle:
      "1.2 Le Principe Fondateur « Human-Led » : L'Humain aux Commandes, jamais Spectateur",
    humanLedSubtitle:
      "Quatre verrous méthodologiques garantissent que l'intelligence artificielle prépare et éclaire le travail sans jamais déposséder l'expert humain de sa responsabilité.",
    humanAnchorCard: {
      title:
        "1. Ancrages de Rédaction Humaine obligatoires (identité visuelle Violette)",
      badge: "Exclusivité Humaine",
      description:
        "L'intention initiale, les objectifs stratégiques et les hypothèses structurantes appartiennent exclusivement à l'auteur humain. Identifiées par une couleur Violette dédiée dans toute l'application, ces sections ne peuvent jamais être rédigées ni altérées par un agent IA.",
    },
    antiRubberStampingCard: {
      title: "2. Zéro validation machinale (« Anti-Validation Fantôme »)",
      badge: "Lecture Active",
      description:
        "Fini les pavés de 20 pages validés sans être lus : chaque étape produit une synthèse de décision en 4 blocs (Résumé, Éléments clés, Décisions prises, Hypothèses retenues), exige une validation section par section (Approuver / Co-éditer / Contester) et vérifie le respect d'un temps minimal de lecture active.",
    },
    humanArbitrationCard: {
      title:
        "3. Arbitrage humain systématique en cas de dilemme ou de contradiction",
      badge: "Pause & Options",
      description:
        "Lorsqu'un agent détecte une contradiction entre deux documents de référence ou fait face à plusieurs options d'architecture équivalentes, il a l'interdiction d'inventer un compromis implicite : le processus se met en pause et présente clairement la matrice de choix à l'humain.",
    },
    noWildWritesCard: {
      title: "4. Aucune modification sauvage des outils de l'entreprise",
      badge: "Actions Préparées",
      description:
        "Aucune publication ni mise à jour dans vos outils externes ne peut partir directement d'une discussion rapide : les actions externes sont toujours préparées en attente d'accord humain. Et si un collaborateur modifie ensuite un document hors plateforme, ORCIA respecte et intègre ses modifications sans jamais les écraser.",
    },
    doubleBarrierTitle:
      "1.3 La Double Barrière Anti-Hallucination & Anti-Propagation d'Erreurs (Déterministe + Probabiliste)",
    doubleBarrierSubtitle:
      "Comment ORCIA brise l'effet boule de neige où une erreur dès l'étape 1 contamine tout le reste d'un processus.",
    snowballWarningPrefix:
      "Le piège des chaînes d'IA classiques (l'effet boule de neige) : ",
    snowballWarningBody:
      "lorsqu'un premier agent commet une légère approximation ou cite une source inexistante en étape 1, l'agent de l'étape 2 la prend pour une vérité établie, et l'étape 3 construit tout un livrable erroné dessus. ORCIA bloque cette propagation grâce à trois barrières successives :",
    deterministicBarrier: {
      badge: "Barrière n°1 · Certitude 100 % · Coût 0 €",
      title: "Les Contrôles Déterministes (Instantanés & Mathématiques)",
      items: [
        "Vérification exacte de la structure du livrable et de toutes les sections obligatoires attendues.",
        "Exécution automatique des règles métiers codifiées du glossaire de votre organisation.",
        "Détection immédiate de toute dérive par rapport aux modèles de référence de l'entreprise.",
        "Contrôle mathématique que chaque citation ([S1], [G1], [O1]) pointe vers un document réel et accessible.",
      ],
    },
    probabilisticBarrier: {
      badge: "Barrière n°2 · Regard Indépendant · 5 Angles",
      title: "Les Contrôles Probabilistes Croisés (Zéro Juge et Partie)",
      items: [
        "Interdiction absolue pour un modèle IA de valider son propre travail : le vérificateur appartient obligatoirement à une famille de modèles différente du rédacteur.",
        "Purge complète des brouillons de raisonnement intermédiaires pour ne juger que le livrable factuel.",
        "Analyse parallèle sous 5 angles indépendants : alignement avec l'étape 1, vérification factuelle assertion par assertion, cas limites, conformité métier/sécurité et synthèse.",
      ],
    },
    rewindBarrier: {
      badge: "Barrière n°3 · Simulation & Recalcul Ciblé",
      title:
        "La Remise en Cause Amont (« Et si on corrigeait l'étape précédente ? »)",
      items: [
        "À tout moment, un expert peut remettre en question une hypothèse ou une règle issue d'une étape antérieure.",
        "Le simulateur affiche avant exécution la liste exacte des étapes et livrables qui seront impactés.",
        "Le recalcul repart uniquement de l'étape corrigée en conservant tout le travail validé en amont, sans jamais perdre l'historique.",
      ],
    },
    orgPacksTitle:
      "1.4 Gouvernance par l'Organisation Réelle & Activation en 1 Clic des Packs Métiers",
    orgPacksSubtitle:
      "Une hiérarchie naturelle (Plateforme entière ➔ Directions / BU ➔ Équipes ➔ Espaces de travail) enrichie par des Packs Métiers prêts à l'emploi.",
    orgHierarchyCard: {
      title:
        "Hiérarchie d'Organisation : Plateforme entière ➔ Directions (BU) ➔ Équipes",
      description:
        "Les directives d'entreprise s'appliquent automatiquement à toute l'organisation, chaque Direction (BU) ou Équipe y ajoute ses normes métiers, et chaque Espace de travail rassemble les sources et exécutions d'un projet ou produit précis.",
    },
    packsCard: {
      title: "Packs Métiers Prêts à l'Emploi & Déduplication Intelligente",
      description:
        "Un Pack Métier regroupe des processus, des agents spécialisés, des règles de contrôle et des guides d'aide cohérents pour un métier donné. Il s'active ou se désactive en 1 clic sur le périmètre de votre choix.",
    },
  },
  features: {
    devicesTitle:
      "Volet A — Les 6 Dispositifs Concrets du Pilotage Humain (Human-Led) et de la Fiabilité dans l'Interface",
    devicesSubtitle:
      "Chaque garantie méthodologique se traduit par un composant visuel immédiatement reconnaissable par les équipes.",
    device1HumanAnchor: {
      title:
        "1. Carte d'Ancrage Humain (identité visuelle Violette réservée à la rédaction humaine)",
      badge: "Dispositif 1",
      description:
        "Signale visuellement les sections que seul un être humain peut rédiger et signer (objectifs, contraintes, contrat d'autonomie). Tant que l'auteur humain n'a pas saisi et signé son intention, l'étape ne peut pas démarrer.",
    },
    device2Arbitration: {
      title: "2. Carte d'Arbitrage en 1 Clic",
      badge: "Dispositif 2",
      description:
        "Expose clairement un dilemme ou une contradiction entre deux sources en comparant les options, leurs impacts et leurs preuves. Le décideur tranche en 1 clic ou ajoute sa propre directive.",
    },
    device3BriefingGrid: {
      title: "3. Grille de Relecture en 4 Blocs & Validation par Section",
      badge: "Dispositif 3",
      description:
        "Synthétise tout livrable en 4 encadrés (Résumé, Éléments clés, Décisions prises, Hypothèses retenues) accompagnés du découpage du document où chaque section est Approuvée, Co-éditée ou Contestée.",
    },
    device4ImpactSimulator: {
      title: "4. Simulateur d'Impact Amont & Retour en Arrière Ciblé",
      badge: "Dispositif 4",
      description:
        "Permet de corriger une décision prise lors d'une étape précédente en visualisant d'abord toutes les étapes aval impactées, puis en relançant uniquement la branche concernée.",
    },
    device5VerifiedCitations: {
      title: "5. Citations Vérifiées ([S1], [G1], [O1]) & Glossaire Métier (À valider)",
      badge: "Dispositif 5",
      description:
        "Relie chaque affirmation aux sources documentaires ([S1]), aux termes du glossaire ([G1]) et aux vérifications d'outils ([O1]). Les nouveaux termes métiers proposés sont plafonnés à 15 dans la file « À valider ».",
    },
    device6TeamClaim: {
      title:
        "6. Prise en Charge Exclusive en Équipe & Niveaux d'Observation (Contributeur vs Observateur)",
      badge: "Dispositif 6",
      description:
        "Évite que deux membres d'une équipe ne modifient la même étape en même temps grâce à un badge de prise en charge en temps réel, et protège les périmètres supervisés en lecture seule (Observateur).",
    },
    screensTitle: "Volet B — Les 9 Écrans du Menu d'ORCIA expliqués un par un",
    screensSubtitle:
      "Cliquez sur « Ouvrir cet écran » pour naviguer directement vers la fonctionnalité correspondante dans l'application.",
    screens: [
      {
        id: "cockpit",
        title: "1. ◈ Cockpit",
        route: "/cockpit",
        summary:
          "Tableau de bord opérationnel réunissant vos décisions humaines en attente, l'état d'avancement initial et le démarrage rapide de processus.",
        keyActions: [
          "Traiter en 1 clic les arbitrages urgents sans quitter le tableau de bord",
          "Ouvrir l'atelier de relecture approfondie d'une étape avec réservation exclusive",
          "Démarrer une nouvelle exécution de processus sur l'Espace actif",
        ],
        openRouteLabel: "Ouvrir /cockpit →",
      },
      {
        id: "assistant",
        title: "2. Mon Assistant",
        route: "/assistant",
        summary:
          "Espace conversationnel à 3 vitesses d'exécution, organisé en dossiers thématiques partageables avec citations vérifiées et personnalisation à 4 niveaux.",
        keyActions: [
          "Choisir entre réponse rapide, appel d'un agent ou compétence, et réflexion approfondie",
          "Vérifier chaque fait grâce aux pastilles de citation [S1], [G1] et [O1]",
          "Classer et partager les fils de discussion dans des dossiers Privés, Partagés ou d'Espace",
        ],
        openRouteLabel: "Ouvrir /assistant →",
      },
      {
        id: "processes",
        title: "3. Mes Processus",
        route: "/processes",
        summary:
          "Atelier de création et de suivi des processus métiers étape par étape, studio de Packs Métiers et générateur de guides d'aide.",
        keyActions: [
          "Construire un processus guidé avec ses instructions, son contrat de livrable et ses étapes",
          "Assembler et certifier un Pack Métier complet avec simulation d'impact",
          "Rédiger et rattacher à chaud une fiche d'aide contextuelle à n'importe quel écran",
        ],
        openRouteLabel: "Ouvrir /processes →",
      },
      {
        id: "agents",
        title: "4. Mes Agents",
        route: "/agents",
        summary:
          "Catalogue et gestion de vos agents spécialisés, de vos compétences réutilisables et banc de test des connexions aux services externes.",
        keyActions: [
          "Créer un agent spécialisé et lui rattacher des compétences métiers en 1 clic",
          "Tester immédiatement un agent ou une compétence sur un cas concret",
          "Qualifier et éprouver à chaud un service externe en 4 étapes de sécurité",
        ],
        openRouteLabel: "Ouvrir /agents →",
      },
      {
        id: "spaces",
        title: "5. Mes Espaces",
        route: "/spaces",
        summary:
          "Centre de pilotage de vos espaces de travail en 5 sous-onglets : exécutions, sources documentaires, glossaire et règles métiers, réconciliation externe et équipe.",
        keyActions: [
          "Gérer le cycle de vie du glossaire métier et valider les règles proposées (plafond de 15 termes)",
          "Inspecter et réconcilier les modifications effectuées par les humains dans leurs outils externes",
          "Piloter les sources documentaires rattachées et les exceptions acquittées",
        ],
        openRouteLabel: "Ouvrir /spaces →",
      },
      {
        id: "finops",
        title: "6. Suivi des Coûts",
        route: "/finops",
        summary:
          "Suivi budgétaire transparent des consommations par direction, par espace, par processus et par étape, avec plafonds et coupe-circuit automatique.",
        keyActions: [
          "Visualiser la répartition des coûts par espace de travail et par exécution",
          "Définir des plafonds budgétaires préventifs par exécution et par déclencheur",
          "Autoriser explicitement une extension de budget lorsqu'une étape est mise en pause",
        ],
        openRouteLabel: "Ouvrir /finops →",
      },
      {
        id: "activity",
        title: "7. Journal d'Activité",
        route: "/activity",
        summary:
          "Historique horodaté et inaltérable de toutes les actions réalisées sur la plateforme, filtré par défaut sur votre niveau d'observation actif.",
        keyActions: [
          "Consulter qui a réalisé quelle action, à quelle seconde et sur quel périmètre",
          "Filtrer instantanément par périmètre observé, par auteur, par volume (50 à 500) ou par période",
          "Revenir en 1 clic au périmètre d'observation de votre session connectée",
        ],
        openRouteLabel: "Ouvrir /activity →",
      },
      {
        id: "settings",
        title: "8. Configuration",
        route: "/settings",
        summary:
          "Administration unifiée de l'arborescence d'organisation, des habilitations, des modèles IA avec test de connectivité, des connecteurs et des Packs Métiers.",
        keyActions: [
          "Structurer les Directions (BU) et Équipes puis attribuer les droits sur chaque périmètre cible",
          "Configurer les fournisseurs de modèles IA et tester en direct la connexion",
          "Activer ou désactiver en 1 clic les Packs Métiers sur la plateforme, une Direction ou un Espace",
        ],
        openRouteLabel: "Ouvrir /settings →",
      },
      {
        id: "help",
        title: "9. Aide Contextuelle & Recherche Globale (⌘K)",
        route: "/help",
        summary:
          "Centre d'aide contextuelle accessible depuis la barre supérieure via le bouton Aide, glossaire partagé et recherche instantanée à 2 vitesses (⌘K).",
        keyActions: [
          "Cliquer sur le bouton Aide en haut à droite pour ouvrir et parcourir l'explication ciblée dans la colonne droite",
          "Rechercher instantanément (⌘K) dans les dossiers, les processus, le glossaire et les guides",
          "Restaurer en 1 clic la version précédente d'un guide d'aide ou interroger Mon Assistant sur l'écran actif",
        ],
        openRouteLabel: "Ouvrir /help →",
      },
    ],
  },
  changelog: SHOWCASE_CHANGELOG_FR,
};
