# Prompt Maître Unifié à copier-coller dans Antigravity (v3)

Copiez et collez le bloc ci-dessous dans **Antigravity** pour exécuter simultanément la **simplification des packages (`orcia-connectors` + `packs/` déclaratifs)** et le **Process Studio v2** :

```
@antigravity /orchestrate-epic

Context & Authority:
Tu interviens sur le monorepo ORCIA. Nous réalisons conjointement la simplification architecturale des Packs/Connecteurs (Epic 10) et le déploiement de l'ORCIA Process Studio v2 (Epic 9).
Les documents de spécification de référence sont :
- `specs/epic-10-packs-simplification/00-principes-packs-et-epic-simplification.md`
- `specs/epic-09-process-studio/00-epic-brief-and-stories.md`
- `specs/epic-09-process-studio/01-ux-ascii-wireframes.md`
- `specs/epic-09-process-studio/02-backend-architecture-and-schemas.md`
- `specs/epic-09-process-studio/03-antigravity-tasks-breakdown.md`
Le prototype fonctionnel de référence pour le contenu métier SDLC est `Workflow agentique 2.html`.

7 Règles d'Or Architecturales Non-Négociables :
1. Simplification des Packages Python (`packages/`) : Il ne doit subsister que 2 packages Python backend dans `packages/` :
   - `packages/orcia-core` (qui absorbe `orcia-kernel` dans `orcia_core.kernel`, gère DBOS, le Permission Broker, les 4 runners déterministes génériques de Gates, le stockage S3 Claim-Check et le `DeclarativePackLoader`).
   - `packages/orcia-connectors` (qui regroupe tous les connecteurs techniques : Jira, Confluence, Git, SQL et Client MCP derrière l'interface unique `OrciaConnectorProtocol` à 4 méthodes : `healthcheck`, `read`, `preview_write`, `execute_write`).
2. Packs 100 % Déclaratifs (`packs/<domaine>/`) : Un Pack métier ne contient AUCUN code Python ni React. Convertis et déplace `packages/orcia-pack-sdlc` et `packages/orcia-pack-builder` vers les dossiers déclaratifs `packs/sdlc/` et `packs/orcia-docs/` (fichiers YAML et Markdown uniquement), puis supprime définitivement `packages/orcia-pack-sdlc/`, `packages/orcia-pack-builder/` et `packages/orcia-kernel/`.
3. Zéro Fuite Métier dans `orcia-core` : Aucun mot-clé `jira`, `confluence`, `git`, `prd`, `wsjf`, `rovo`, `copilot` ou `safe` ne doit exister dans `packages/orcia-core`.
4. Séparation Chaîne de Valeur (Macro-VSM) vs Workflows Unitaires Bornés : La chaîne de 11 étapes du POC HTML est chargée depuis `packs/sdlc/workflows/vsm-mon-compte-idea-to-prod.yaml` (`ValueStreamMapSpec`), et chaque étape outillée pointe vers un workflow DBOS court et autonome (`wf-01-qualification-prd.yaml`, `wf-03-etude-architecture.yaml`, `wf-06-decoupe-us.yaml`, `wf-08-dev-external-gate.yaml`).
5. Zéro "Agent Orchestrateur" lisant le chat (ADR-01 & ADR-02) : Toutes les transitions entre sous-étapes sont pilotées par `DeterministicSubStepSpec` et des signaux DBOS (`DBOS.recv`).
6. Pipeline de Gates (ADR-06) : Les 4 runners déterministes génériques s'exécutent toujours en premier avec auto-remédiation bornée (max 3 essais) avant d'invoquer les agents contradicteurs/évaluateurs probabilistes.
7. Claim-Check S3 & Idempotence Cyclique : Tout artefact ou diff > 4 Ko est stocké dans SeaweedFS via `ClaimCheckPointer(s3_uri, sha256, byte_size)`. Toute clé d'idempotence d'étape inclut `:iter-{iteration}` pour permettre les boucles de retour en mode `corrections`.

Execution Plan:
Exécute dans l'ordre strict les tâches `TASK-01` à `TASK-08` décrites dans `specs/epic-09-process-studio/03-antigravity-tasks-breakdown.md`.
Valide chaque tâche par `ruff check`, `pytest`, `pnpm lint` et `pnpm typecheck`, en commençant immédiatement par `TASK-01`.
```
