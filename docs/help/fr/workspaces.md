---
resource_id: help-base-workspaces-fr
uri: orcia://system/help/workspaces/fr
title: "Détail d'un Espace de travail : sources, packs et règles"
version: "1.1.0"
lang: fr
layer: BASE
bound_routes:
  - /workspaces
  - /workspaces/$wsId
  - /workspaces/$wsId/sources
summary_what_for: "Cette vue gère vos Espaces de travail, leurs sources de connaissances connectées, l'activation et la priorité des packs métiers avec liaison d'emplacements, et le glossaire local."
---

## À quoi sert cet écran

Vous pilotez ici la vie complète d'un Espace de travail : rattachement à son unité d'organisation propriétaire, gestion des sources documentaires et outils externes, activation des packs métiers avec ordre de priorité et liaison des emplacements de connecteurs, suivi des règles applicables et accès direct au Glossaire.

## En 4 gestes

1. Sélectionnez ou créez l'Espace de travail souhaité et vérifiez son unité d'organisation propriétaire ainsi que sa visibilité.
2. Ouvrez l'onglet « Sources » pour connecter un dépôt de code, une documentation ou un suivi de tickets et lancer une synchronisation.
3. Dans « Gouvernance & Packs », activez les packs utiles à l'Espace, ajustez leur ordre de priorité et ouvrez le tiroir d'emplacements pour relier chaque connecteur requis à une source de l'Espace.
4. Consultez l'onglet « Glossaire & Règles » pour vérifier les définitions actives et demander une exception documentée si un projet l'exige.

## Un exemple réel

Avant de lancer la rédaction d'une note d'architecture, Marc ouvre l'Espace « Portail Client », ajoute le dépôt Git du front-end dans l'onglet Sources, relie l'emplacement requis du pack « SDLC » à cette source puis active le pack sur son Espace.

## Ce qui coince souvent

- **Un pack refuse de s'activer sur l'Espace** : vérifiez dans le tiroir d'emplacements que tous les emplacements obligatoires sont bien associés à une source ou un connecteur actif.
- **Une source externe renvoie une erreur de connexion** : vérifiez l'adresse saisie et assurez-vous que vos identifiants personnels sont renseignés dans Mon Compte › Connexions aux outils.
- **Les modifications d'un espace confidentiel sont invisibles ailleurs** : c'est le comportement attendu du cloisonnement pour protéger les données sensibles.
- **Besoin de consulter le glossaire de l'Espace** : ouvrez directement l'onglet « Glossaire » dans Mes Espaces.
