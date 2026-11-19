---
resource_id: help-base-activity-fr
uri: orcia://system/help/activity/fr
title: "Journal d'Activité : historique immuable et provenance"
version: "1.0.0"
lang: fr
layer: BASE
bound_routes:
  - /activity
summary_what_for: "Le Journal d'Activité retrace chronologiquement qui a effectué chaque action sur la plateforme, sur quel périmètre, et permet d'exporter le dossier de provenance d'une exécution."
---

## À quoi sert cet écran

Cet écran offre une piste d'audit claire et infalsifiable pour les responsables d'équipe, les auditeurs et les administrateurs. Contrairement au Centre de Notifications qui liste ce qui attend votre action, le Journal d'Activité conserve l'historique complet de tout ce qui a déjà été réalisé.

## En 3 gestes

1. Filtrez l'historique par périmètre d'observation, par auteur (menu déroulant ou recherche rapide), par nombre d'événements ou par période.
2. Parcourez la chronologie : chaque ligne indique la date et l'heure en français, l'auteur, le périmètre et la description lisible de l'action.
3. Cliquez sur « Provenance » sur une exécution pour inspecter les sources et signatures utilisées et exporter le rapport au format JSON ou Markdown.

## Un exemple réel

Lors d'une revue trimestrielle, un responsable sécurité filtre le Journal d'Activité sur les 7 derniers jours pour l'Espace « Paiement », vérifie qui a modifié une règle d'accès et exporte la fiche de provenance d'un livrable validé.

## Ce qui coince souvent

- **Une action récente n'apparaît pas** : vérifiez que le filtre de périmètre en haut de la barre ne restreint pas l'affichage à un autre Espace ou à un autre auteur.
- **Différence entre Notifications et Journal d'Activité** : la cloche Notifications signale ce que vous devez faire maintenant ; le Journal d'Activité archive ce qui a déjà été fait.
- **Un utilisateur non administrateur ne voit pas toute la plateforme** : par sécurité, chacun n'observe que l'historique des Directions, Équipes et Espaces auxquels il est habilité.
