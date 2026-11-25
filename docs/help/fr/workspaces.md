---
resource_id: help-base-workspaces-fr
uri: orcia://system/help/workspaces/fr
title: "Détail d'un Espace de travail : sources, règles et livrables"
version: "1.0.0"
lang: fr
layer: BASE
bound_routes:
  - /workspaces
  - /workspaces/$wsId
  - /workspaces/$wsId/sources
summary_what_for: "Cette vue gère vos Espaces de travail, leurs sources de connaissances connectées, les dérogations de règles d'architecture et le glossaire local."
---

## À quoi sert cet écran

Vous pilotez ici la vie complète d'un Espace de travail : rattachement à son unité d'organisation propriétaire, gestion des sources documentaires et outils externes, suivi de la chaîne de règles applicables et accès direct au Glossaire.

## En 3 gestes

1. Sélectionnez ou créez l'Espace de travail souhaité et vérifiez son unité d'organisation propriétaire ainsi que sa visibilité.
2. Ouvrez l'onglet « Sources » pour connecter un dépôt de code, une documentation ou un suivi de tickets et lancer une synchronisation.
3. Consultez l'onglet « Glossaire & Règles » pour vérifier les définitions actives et demander une exception documentée si un projet l'exige.

## Un exemple réel

Avant de lancer la rédaction d'une note d'architecture, Marc ouvre l'Espace « Portail Client », ajoute le dépôt Git du front-end dans l'onglet Sources et vérifie que les termes métiers de l'équipe sont bien hérités.

## Ce qui coince souvent

- **Une source externe renvoie une erreur de connexion** : vérifiez l'adresse saisie et assurez-vous que vos identifiants personnels sont renseignés dans Mon Compte › Connexions aux outils.
- **Les modifications d'un espace confidentiel sont invisibles ailleurs** : c'est le comportement attendu du cloisonnement pour protéger les données sensibles.
- **Besoin de consulter le glossaire de l'Espace** : ouvrez directement l'onglet « Glossaire » dans Mes Espaces.
