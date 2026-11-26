---
resource_id: help-base-agents-fr
uri: orcia://system/help/agents/fr
title: "Mes Agents : spécialistes IA, compétences et outils"
version: "1.1.0"
lang: fr
layer: BASE
bound_routes:
  - /agents
summary_what_for: "Mes Agents centralise vos agents IA spécialisés et leurs compétences métiers (y compris ceux fournis par vos packs actifs), avec leur posture, leurs garde-fous et leurs droits d'accès aux outils connectés."
---

## À quoi sert cet écran

Cet écran vous permet de créer, paramétrer et tester des agents dédiés à un métier précis (analyse produit, revue documentaire, support sécurité), de consulter les spécialistes fournis par les packs activés sur votre Espace, ainsi que des compétences réutilisables.

## En 3 gestes

1. Consultez les agents et compétences disponibles : chaque nouvel agent créé ou dupliqué démarre au statut « Brouillon » (« À tester »), tandis que les entrées issues d'un pack affichent leur badge de provenance.
2. Cliquez sur « + Nouvel agent » ou ouvrez la fiche « Configurer & Tester (6 blocs) » pour définir son rôle, ses sources autorisées et ses garde-fous, puis validez explicitement vos modifications via « Enregistrer » en bas à droite.
3. Lancez un essai concluant dans le Banc de Test intégré pour promouvoir l'agent au statut « Actif » avant de l'appeler avec « @ » (ou « @pack/agent » en cas de doublon), de l'associer à un processus ou de l'inclure dans un pack personnalisé.

## Un exemple réel

Yanis crée l'agent « Analyste Conformité DORA » (statut initial « Brouillon »), ajuste ses blocs et clique sur « Enregistrer », puis exécute un test de vérification concluant : l'agent passe « Actif » et devient immédiatement utilisable dans Mon Assistant et dans ses packs personnalisés.

## Ce qui coince souvent

- **Un agent n'apparaît pas dans les suggestions ou dans Mes Processus** : tant qu'un agent est « Brouillon » ou « À tester », il reste exclu de Mon Assistant, des processus et de la publication d'un pack ; exécutez un essai concluant au Banc de Test pour l'activer.
- **La suppression d'un agent ou d'une compétence demande une confirmation de détachement** : l'élément est référencé dans un ou plusieurs brouillons de packs personnalisés ; confirmez le détachement explicite pour le retirer proprement des brouillons puis le supprimer.
- **La case « Exposer en outil externe » est verrouillée** : seuls les agents personnalisés « Actifs » peuvent être exposés en outil externe (dupliquez d'abord un modèle de pack si vous souhaitez l'exposer).
- **Les menus Agents sont grisés au premier démarrage** : configurez au moins un modèle IA dans Administration › Modèles IA pour débloquer les essais du Banc de Test.
