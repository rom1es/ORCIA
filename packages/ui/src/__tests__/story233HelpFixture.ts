import type {
  ContextualHelpColumnAndCenterLabels,
  UiContextualHelpArticleView,
} from "../index";

export const HELP_LABELS_FR: ContextualHelpColumnAndCenterLabels = {
  columnHeaderTitle: "Aide contextuelle",
  centerHeaderTitle: "Centre d'Aide",
  whatForSectionTitle: "À quoi sert cet écran ?",
  stepByStepAccordionTitle: "Pas-à-pas",
  keyTermsAccordionTitle: "Termes clés",
  faqAccordionTitle: "Questions fréquentes",
  askAssistantOnScreenCta: "Poser une question à Mon Assistant →",
  rollbackButtonLabel: "Revenir à la version précédente",
  rollbackCompletedPrefix: "Version restaurée :",
  mergedLayersPrefix: "Sources du guide :",
  realExampleTitle: "Un exemple réel",
  commonPitfallsTitle: "Ce qui coince souvent",
  technicalDetailsTitle: "Détails techniques",
  versionLabel: "Version",
  layerLabels: {
    BASE: "Base",
    PACK: "Pack",
    WORKSPACE: "Espace",
    USER: "Utilisateur",
  },
  stepsBlockPrefix: "En",
  stepsBlockSuffix: "gestes",
  targetedHelpBadgeLabel: "Aide ciblée",
};

export const SAMPLE_ASSISTANT_ARTICLE: UiContextualHelpArticleView = {
  resourceId: "help-base-assistant-fr",
  uri: "orcia://system/help/assistant/fr",
  title: "Mon Assistant : questions, dossiers et citations vérifiées",
  version: "1.0.0",
  lang: "fr",
  layer: "BASE",
  packName: "core",
  boundRoutes: ["/assistant", "/inbox"],
  summaryWhatFor:
    "Mon Assistant répond à vos questions à partir des documents de votre Espace actif.",
  stepByStepItems: [
    "Choisissez votre modèle et votre mode de réflexion (Polyvalent · Standard ou Approfondi).",
    "Rédigez votre question avec @ pour appeler un agent.",
    "Classez l'échange dans un dossier thématique.",
  ],
  keyTermsItems: [],
  faqItems: [],
  realExampleText:
    "Marc sélectionne son Espace, ouvre le dossier Conformité et obtient des citations cliquables.",
  commonPitfallsItems: [
    "La zone de saisie est verrouillée : configurez un modèle de dialogue dans Modèles IA.",
    "Les notes du dossier ne sont pas appliquées : cliquez sur Enregistrer les notes.",
  ],
  casKey: "cas/1234",
  sha256: "1234",
};
