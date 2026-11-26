---
resource_id: help-base-assistant-fr
uri: orcia://system/help/assistant/fr
title: "Mon Assistant : questions, dossiers et citations vérifiées"
version: "1.0.0"
lang: fr
layer: BASE
bound_routes:
  - /assistant
summary_what_for: "Mon Assistant répond à vos questions à partir des documents de votre Espace actif, cite chaque source vérifiée et organise vos échanges en dossiers thématiques avec notes permanentes."
---

## À quoi sert cet écran

Cet écran vous offre un compagnon conversationnel ancré sur les connaissances de votre équipe. Vous pouvez poser une question directe, solliciter un agent spécialisé avec @, classer vos échanges par dossiers ou enregistrer une réponse comme point de départ d'un processus.

## En 3 gestes

1. Choisissez votre modèle (Rapide, Polyvalent ou Raisonnement avancé) et votre mode de réflexion (Standard ou Approfondi — ex. « Polyvalent · Standard ») via le sélecteur à côté du bouton d'envoi.
2. Ouvrez « Réglages de Mon Assistant » si vous souhaitez personnaliser le ton, le format ou vos consignes personnelles (laissées libres par défaut), puis validez explicitement avec « Enregistrer » en bas à droite de la fenêtre.
3. Rédigez votre question (tapez @ pour appeler un agent actif ou / pour déclencher une compétence) ou ouvrez « Dossiers » pour attacher l'échange à un sujet et y épingler des notes permanentes.

## Un exemple réel

Marc sélectionne l'Espace « Produit Paiement », ajuste son format préféré dans les réglages puis clique sur « Enregistrer » (le bouton devient « Fermer » dès la confirmation), ouvre le dossier « Conformité 2026 », puis demande une synthèse des risques : Mon Assistant répond avec des pastilles de citations cliquables pointant vers les documents exacts de l'Espace.

## Ce qui coince souvent

- **La zone de saisie est verrouillée** : vérifiez qu'un modèle d'analyse documentaire et un modèle de dialogue sont configurés dans Administration › Modèles IA.
- **Aucune pastille de citation n'apparaît dans la réponse** : lorsque votre question ne s'appuie sur aucun document ou terme du glossaire de l'Espace (par exemple une simple salutation), Mon Assistant répond naturellement sans inventer de référence.
- **Un brouillon propose une mise à jour vers un outil externe** : par sécurité, Mon Assistant n'écrit jamais directement dans vos outils ; confirmez l'action ou poursuivez dans un processus gouverné.
- **Des réglages modifiés ne sont pas pris en compte** : vérifiez d'avoir cliqué sur « Enregistrer » dans « Réglages de Mon Assistant » (cliquer sur « Annuler » annule uniquement vos saisies non enregistrées) ou sur « Enregistrer les notes » dans le dossier actif.
