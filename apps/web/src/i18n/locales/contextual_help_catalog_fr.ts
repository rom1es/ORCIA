import type { ContextualHelpDictionarySection } from "./contextual_help_labels";
import {
  CONFIGURATION_SECTIONS_FR,
  SECTIONS_BY_ROUTE_FR,
  WORKFLOW_SECTIONS_FR,
} from "./contextual_help_sections_fr";

export const CONTEXTUAL_HELP_FR: ContextualHelpDictionarySection = {
  configurationSections: CONFIGURATION_SECTIONS_FR,
  workflowSections: WORKFLOW_SECTIONS_FR,
  sectionsByRoute: SECTIONS_BY_ROUTE_FR,
  settingsArticle: {
    summaryWhatFor:
      "Cet écran structure votre organisation (Directions / BU et Équipes), gère l'annuaire des comptes et pilote vos règles d'habilitation, vos modèles IA et vos connecteurs.",
    stepByStepItems: [
      "Gérez vos comptes utilisateurs et comptes techniques dans l'annuaire, puis consultez la matrice des 7 rôles officiels.",
      "Dans Exceptions & Isolation SecOps, indiquez Qui ? (Rôle ou Compte) et choisissez Sur quoi ? (Périmètre cible).",
      "Dans Modèles IA, renseignez vos fournisseurs (dialogue et recherche documentaire) puis testez la connexion avant d'enregistrer.",
    ],
    realExampleText:
      "Lors de l'installation initiale, Alice ouvre Configuration › Modèles IA, ajoute son fournisseur principal et un modèle de recherche documentaire, teste la connexion avec succès, puis passe à « Mon Organisation » pour créer la Direction Produit et l'Équipe Paiement.",
    commonPitfallsItems: [
      "Une clé secrète n'apparaît plus après enregistrement : par sécurité, les jetons et clés API sont protégés en écriture seule et ne sont jamais ré-affichés en clair.",
      "Impossible de supprimer une Direction ou une Équipe : détachez d'abord les Équipes et règles d'habilitation qui y font référence.",
    ],
  },
  routeFallbacks: {
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
  },
  defaultSteps: [
    "Vérifiez votre Espace ou périmètre actif dans la barre latérale gauche.",
    "Utilisez la recherche globale (⌘K) pour retrouver rapidement vos documents et processus.",
    "Consultez les actions principales de cet écran et sollicitez Mon Assistant si besoin.",
  ],
  routeTitleFallbacks: {
    inbox: "Boîte de Réception",
    showcase: "Présentation ORCIA",
    organization: "Mon Organisation",
  },
};
