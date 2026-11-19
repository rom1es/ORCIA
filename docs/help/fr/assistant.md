---
resource_id: help-base-assistant-fr
uri: orcia://system/help/assistant/fr
title: "Mon Assistant : questions, dossiers et citations vérifiées"
version: "1.0.0"
lang: fr
layer: BASE
bound_routes:
  - /assistant
  - /inbox
summary_what_for: "Mon Assistant répond à vos questions à partir des documents de votre Espace actif, cite chaque source vérifiée et organise vos échanges en dossiers thématiques avec notes permanentes."
---

## À quoi sert cet écran

Cet écran vous offre un compagnon conversationnel ancré sur les connaissances de votre équipe. Vous pouvez poser une question directe, solliciter un agent spécialisé avec `@`, classer vos échanges par dossiers ou enregistrer une réponse comme point de départ d'un processus.

## En 3 gestes

1. Choisissez votre niveau d'analyse via le sélecteur de modèle et d'effort (Rapide, Équilibré ou Approfondi) à côté du bouton d'envoi.
2. Rédigez votre question (tapez `@` pour appeler un agent ou `/` pour déclencher une compétence) puis envoyez.
3. Ouvrez « Dossiers » si vous souhaitez attacher l'échange à un sujet précis et y épingler des consignes permanentes.

## Un exemple réel

Marc sélectionne l'Espace « Produit Paiement », ouvre le dossier « Conformité 2026 » contenant ses consignes permanentes, puis demande une synthèse des risques : Mon Assistant répond avec des pastilles de citations cliquables pointant vers les documents exacts de l'Espace.

## Ce qui coince souvent

- **La zone de saisie est verrouillée** : vérifiez qu'un modèle d'analyse documentaire et un modèle de dialogue sont configurés dans Configuration › Modèles IA.
- **Un brouillon propose une mise à jour vers un outil externe** : par sécurité, Mon Assistant n'écrit jamais directement dans vos outils ; confirmez l'action ou poursuivez dans un processus gouverné.
- **Les notes du dossier ne semblent pas prises en compte** : cliquez sur « Enregistrer les notes » dans le tiroir du dossier actif avant de poser votre question.
