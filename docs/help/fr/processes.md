---
resource_id: help-base-processes-fr
uri: orcia://system/help/processes/fr
title: "Mes Processus : catalogue, studio et chaîne de valeur"
version: "1.0.0"
lang: fr
layer: BASE
bound_routes:
  - /processes
  - /processes/studio/$workflowId
  - /processes/vsm/$vsmId
  - /processes/runs/$runId
summary_what_for: "Mes Processus sépare vos validations en cours, le catalogue de processus métiers et la chaîne de valeur, et ouvre chaque exécution dans une vue Focus dédiée à la décision humaine."
---

## À quoi sert cet écran

Cet écran est structuré en trois onglets (« Validations & Exécutions », « Processus métiers » et « Chaîne de valeur »). Tant qu'aucune exécution n'attend votre décision, vous arrivez directement sur le catalogue « Processus métiers ». Chaque exécution s'ouvre sur une page dédiée mettant au premier plan l'action attendue, le livrable et le raisonnement repliable de l'agent.

## En 3 gestes

1. Parcourez l'onglet « Processus métiers » (affiché par défaut lorsqu'aucune validation n'est en attente) pour consulter ou lancer un processus sur votre Espace actif.
2. Cliquez sur « Ouvrir le Studio » pour ajuster les instructions, les agents actifs autorisés et les points de validation, puis enregistrez et publiez votre version.
3. Ouvrez une exécution dans la vue Focus (bannière d'action unique en haut, livrable principal à gauche, raisonnement repliable à droite) pour valider l'étape, demander une correction ciblée ou mettre en pause.

## Un exemple réel

Claire ouvre « Mes Processus » sur son Espace, lance « Qualification de demande & Note de cadrage » puis examine la page d'exécution dédiée : le bandeau supérieur lui propose l'unique action attendue pour approuver l'étape pendant que le livrable reste entièrement lisible sans être masqué par la trace de raisonnement.

## Ce qui coince souvent

- **Un processus refuse de démarrer** : vérifiez qu'un modèle de dialogue actif est configuré dans Administration › Modèles IA et qu'au moins une source est rattachée à l'Espace actif (ou renseignez une consigne d'entrée).
- **Un processus reste à l'état de brouillon** : cliquez sur « Publier » dans le Studio pour le rendre actif sur votre Espace.
- **Le Studio recommande un écran d'ordinateur sur mobile** : vous pouvez consulter une exécution et répondre aux validations sur téléphone, mais la conception complète des blocs est optimisée pour un poste de bureau.
- **Une étape demande des ajustements** : cliquez sur « Demander une correction » dans le bandeau supérieur de la vue d'exécution pour cibler l'étape à reprendre avec vos remarques.
