---
resource_id: help-base-spaces-sources-fr
uri: orcia://system/help/spaces-sources/fr
title: "Sources & Documents de l'Espace"
version: "1.0.0"
lang: fr
layer: BASE
bound_routes:
  - /mes-espaces/$id/sources
  - /spaces
  - /cockpit
summary_what_for: "Cet écran permet de raccorder et d'indexer les sources documentaires de votre Espace."
---
### Pas-à-pas
1. Cliquez sur **+ Rattacher une source** pour lier un dépôt Git, Jira ou Confluence.
2. Vérifiez l'indicateur de fraîcheur (`freshness_ttl_days`).

### Termes clés
- **Espace** : Périmètre projet isolant vos sources, livrables et glossaire métier.
- **Passthrough** : Exécution sous votre propre identité personnelle chiffrée `AES-256-GCM`.

### Questions fréquentes
- **Comment rafraîchir une source ?** Utilisez le bouton de synchronisation ou un webhook temps réel.
