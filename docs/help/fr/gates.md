---
resource_id: help-base-gates-fr
uri: orcia://system/help/gates/fr
title: "Contrôles Qualité & Validations Humaines : revue par sections"
version: "1.0.0"
lang: fr
layer: BASE
bound_routes:
  - /gates
summary_what_for: "Cet écran pilote les contrôles qualité automatiques, les revues croisées par des modèles indépendants et la validation humaine détaillée section par section avant toute diffusion."
---

## À quoi sert cet écran

Avant qu'un livrable produit par un processus soit validé ou publié vers un outil externe, ORCIA enchaîne trois niveaux de vérification : contrôles automatiques, revue croisée indépendante et validation humaine section par section avec protection contre la validation précipitée.

## En 3 gestes

1. Consultez la synthèse de l'exécution et inspectez les hypothèses retenues ainsi que les éventuels écarts signalés.
2. Parcourez le livrable découpé en sections pour approuver chaque bloc, le co-éditer directement ou demander une correction.
3. Confirmez la décision finale (approbation ou renvoi vers une étape amont) une fois toutes les sections examinées.

## Un exemple réel

Lors de la validation d'une spécification technique, Nadia relit les 4 sections proposées, co-édite directement le paragraphe sécurité pour préciser une exigence, approuve les autres blocs puis finalise la validation afin de déclencher les actions préparées.

## Ce qui coince souvent

- **Une alerte bloque la finalisation immédiate** : si une validation est déclenchée trop rapidement sans examen des sections, ORCIA demande une confirmation explicite pour préserver la qualité du contrôle humain.
- **La revue croisée indépendante indique un seul fournisseur** : ajoutez un second fournisseur IA indépendant dans Configuration › Modèles IA pour activer les revues croisées orthogonales.
- **Une action externe reste en attente** : aucune modification vers Jira, GitLab ou Confluence n'est envoyée tant que l'approbation humaine finale n'est pas signée.
