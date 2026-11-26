---
resource_id: help-base-agents-fr
uri: orcia://system/help/agents/fr
title: "Mes Agents : spécialistes IA, compétences et outils"
version: "1.0.0"
lang: fr
layer: BASE
bound_routes:
  - /agents
summary_what_for: "Mes Agents centralise vos agents IA spécialisés et leurs compétences métiers, avec leur posture, leurs garde-fous et leurs droits d'accès aux outils connectés."
---

## À quoi sert cet écran

Cet écran vous permet de créer, paramétrer et tester des agents dédiés à un métier précis (analyse produit, revue documentaire, support sécurité) ainsi que des compétences réutilisables d'un espace à l'autre.

## En 3 gestes

1. Consultez les agents et compétences disponibles : chaque nouvel agent créé ou dupliqué démarre au statut « Brouillon » (« À tester »).
2. Cliquez sur « + Nouvel agent » ou ouvrez la fiche « Configurer & Tester (6 blocs) » pour définir son rôle, ses sources autorisées et ses garde-fous, puis validez explicitement vos modifications via « Enregistrer » en bas à droite.
3. Lancez un essai concluant dans le Banc de Test intégré pour promouvoir l'agent au statut « Actif » (« Validé au Banc de Test ») avant de l'appeler avec @, de l'associer à un processus ou de l'exposer en outil externe.

## Un exemple réel

Yanis crée l'agent « Analyste Conformité DORA » (statut initial « Brouillon »), ajuste ses blocs et clique sur « Enregistrer », puis exécute un test de vérification concluant : l'agent passe « Actif » et devient immédiatement utilisable dans Mon Assistant via « @ » et dans Mes Processus.

## Ce qui coince souvent

- **Un agent n'apparaît pas dans « @ » ou dans Mes Processus** : tant qu'un agent est « Brouillon » ou « À tester », il reste exclu de Mon Assistant, des processus et de l'exposition externe ; exécutez un essai concluant au Banc de Test pour l'activer.
- **La case « Exposer en outil externe » est verrouillée** : seuls les agents personnalisés « Actifs » peuvent être exposés en outil externe (dupliquez d'abord un modèle de pack si vous souhaitez l'exposer).
- **Les menus Agents sont grisés au premier démarrage** : configurez au moins un modèle IA dans Administration › Modèles IA pour débloquer les essais du Banc de Test.
