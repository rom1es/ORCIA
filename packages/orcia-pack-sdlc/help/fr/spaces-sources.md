---
resource_id: help-pack-sdlc-spaces-sources-fr
uri: orcia://packs/orcia-pack-sdlc/help/spaces-sources/fr
title: "Sources SDLC (Git, Jira & Confluence) de l'Espace"
version: "1.1.0"
lang: fr
layer: PACK
pack_name: orcia-pack-sdlc
bound_routes:
  - /mes-espaces/$id/sources
  - /spaces
summary_what_for: "Raccordez vos dépôts Git, projets Jira et espaces Confluence pour alimenter le graphe tripartite SDLC."
---
### Pas-à-pas
1. Associez votre dépôt Git principal et votre projet Jira de sprint.
2. Activez la détection automatique d'obsolescence (`[STALE_WARNING]`) entre Confluence et Git.

### Termes clés
- **Graphe Tripartite** : Liens causaux vérifiés entre pages Confluence, tickets Jira et commits Git.
- **Ancrage Humain** : Décision d'architecture rédigée et signée par un humain (`human_authored_required`).

### Questions fréquentes
- **Pourquoi un ticket Jira est-il en mode Staged ?** Les transitions Jira sont pré-validées et exécutées uniquement après approbation de la Gate.
