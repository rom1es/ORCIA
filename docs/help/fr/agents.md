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

1. Consultez la liste des agents et compétences déjà actifs sur votre Espace ou votre organisation.
2. Cliquez sur « + Nouvel agent » pour définir son rôle, son niveau de réflexion par défaut, ses sources autorisées et ses garde-fous.
3. Ouvrez la fiche d'un agent pour lancer un essai à blanc et vérifier ses réponses avant de l'associer à un processus.

## Un exemple réel

Yanis crée l'agent « Analyste Conformité DORA », lui attribue uniquement la lecture du référentiel réglementaire de son Espace et l'interdiction d'écrire dans les outils externes sans accord humain, puis l'appelle directement depuis Mon Assistant via « @ ».

## Ce qui coince souvent

- **Un agent n'apparaît pas dans les suggestions « @ » de Mon Assistant** : vérifiez que l'agent est bien publié sur votre Espace ou sur une portée englobant votre équipe.
- **Une compétence refuse d'accéder à un outil externe** : contrôlez les autorisations d'outils associées à l'agent et l'état de vos connexions personnelles dans Mon Compte.
- **Les menus Agents sont grisés au premier démarrage** : configurez au moins un modèle IA dans Administration › Modèles IA pour débloquer les essais.
