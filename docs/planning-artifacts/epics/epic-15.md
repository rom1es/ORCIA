## Epic 15: Simplification Architecturale des Packs & Connecteurs (`packages/orcia-connectors`, Fusion `orcia-kernel` dans `orcia-core` & Packs 100 % Déclaratifs `packs/<domaine>/`) (`specs/epic-10-packs-simplification/`)

Simplifier radicalement l'architecture Python backend autour de **2 uniques packages Python** dans `packages/` (`packages/orcia-core` qui absorbe `orcia-kernel` dans `orcia_core.kernel`, et `packages/orcia-connectors` qui unifie Jira, Confluence, Git, SQL et MCP derrière `OrciaConnectorProtocol` à 4 méthodes) et convertir tous les Packs métiers en **bundles 100 % déclaratifs (YAML + Markdown, zéro code Python/React)** sous `packs/sdlc/` et `packs/orcia-docs/`.

### Story 15.1: Création de `packages/orcia-connectors` (`OrciaConnectorProtocol`) & Fusion de `orcia-kernel` dans `orcia-core` (`TASK-01`)
- **CA-15.1.1 (Contrat Unique à 4 Méthodes)** : `OrciaConnectorProtocol` (`healthcheck`, `read`, `preview_write`, `execute_write`) et adaptateurs `atlassian_jira.py`, `atlassian_confluence.py`, `git_provider.py`, `sql_readonly.py`, `mcp_client_bridge.py` vérifiant la signature `SignedApprovalToken` du *Permission Broker*.
- **CA-15.1.2 (2 Packages Python Uniques dans `packages/`)** : Absorption de `packages/orcia-kernel` dans `packages/orcia-core/src/orcia_core/kernel/` et suppression de `packages/orcia-kernel/`.

### Story 15.2: Chargeur `DeclarativePackLoader`, Exportateur `.zip` & Conversion Déclarative `packs/sdlc/` et `packs/orcia-docs/` (`TASK-02` & `TASK-03`)
- **CA-15.2.1 (Packs 100 % Déclaratifs)** : Chargement à chaud via `DeclarativePackLoader` de `packs/sdlc/` et `packs/orcia-docs/` (YAML + Markdown uniquement) et suppression définitive de `packages/orcia-pack-sdlc/` et `packages/orcia-pack-builder/`.
- **CA-15.2.2 (Export d'Espace en Archive `.zip` de Pack)** : `POST /api/v1/packs/export/{workspace_id}` exportant les Agents, Skills, Gates et Workflows sous forme d'archive déclarative `.zip`.

### Story 15.3: Écran `/settings/packs` Simplifié (`PacksRegistryPage.tsx`) & Monitoring Temps Réel des Connecteurs Requis (`TASK-06`)
- **CA-15.3.1 (Registre des Packs Déclaratifs & Healthcheck Connecteurs)** : Affichage des Packs chargés depuis `packs/`, de leur `bundle_sha256`, des compteurs d'objets, du statut `healthcheck()` de leurs `required_connectors` et du bouton d'export `.zip`.
