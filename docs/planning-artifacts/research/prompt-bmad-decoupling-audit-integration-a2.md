# Prompt BMAD : intégrer l'audit de découplage (Story 3.2e et action_items)

> **Skill principal : `bmad-correct-course`.** Il s'agit d'un changement important en cours de sprint, qui touche le PRD, l'architecture et les epics.
> Il est suivi de `bmad-architecture` (mode *update*), `bmad-create-epics-and-stories` (mise à jour) et `bmad-sprint-planning` (mode *validate/fix*), puis d'une vérification finale.
> Les étapes sont **séquentielles**. Je valide à chaque pause ⏸️.

---

## Contexte et documents d'entrée (à lire en premier)
- **Audit de référence** : `docs/planning-artifacts/research/architecture-decoupling-audit-2026-10-28.md`. Il contient la note de découplage 2/5, les fuites L1 à L11, les risques K1 à K9, le plan P0-1 à P2-2 et les preuves `fichier:ligne`.
- Proposition de changement de sprint en vigueur : `docs/planning-artifacts/sprint-change-proposal-2026-10-27.md` (avec l'avenant A1).
- Spine : `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md` et `architecture.md`.
- PRD : `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md` · Epics : `docs/planning-artifacts/epics.md` · Suivi : `docs/implementation-artifacts/sprint-status.yaml`.
- Règles : `AGENTS.md` (Tech Lead, ne jamais modifier une story `done`, migrations Expand → Contract, GitNexus limité à `repo: "ORCIA"`, commandes Python via `.venv/bin/`).

**État actuel** :
- stories `3.2a`, `3.2s`, `3.2b` et `3.2c` en `done` ;
- `3.2d` (front Vite) en cours, avec des modifications non commitées dans `apps/web` et `packages/api-client` : **ne pas y toucher** ;
- `3.3` en `backlog`.

Langue des livrables : **français**.

### Décisions déjà prises (ne pas les rouvrir)
- Q1 = 1A (packages `uv`), Q2 = 2A (outbox indépendante du moteur), Q3 = 3A (plugins `entry_points` dans le processus, MCP hors processus), Q4 = 4A (un seul schéma `public`), Q5 = pas de Rust au MVP.
- Monolithe modulaire (AD-19) : **pas de microservices**.

---

## Étape 0 : vérifier les constats de l'audit (obligatoire avant toute décision)
Avec `gitnexus_context`, `gitnexus_impact` (`direction: upstream`) et `.venv/bin/python`, **confirmer ou infirmer** chacun des points suivants, preuve à l'appui :
1. **K3, l'exécution réelle est absente** :
   - `orchestration/engine.py:L258-L275` produit un livrable simulé ;
   - `orchestration/_internal/dbos_engine.py:L231-L251` écrit un contenu figé ;
   - `_ACTIVE_ENGINE` est global et `DBOS._recover_pending_workflows()` (API privée) est appelé ;
   - aucun des deux moteurs n'est branché dans `apps/api/src/orcia_api/dependencies.py`.
2. **L1 à L6, le vocabulaire SDLC est dans le kernel, le modèle, le validateur et le moteur** : `orcia_kernel/enums.py:L54-L61`, `orchestration/models.py:L22` et `L71-L73`, `yaml_validator.py:L158-L185`, `engine.py:L349-L388`.
3. **K2, la liste des types de source est fermée et recopiée** : `ALLOWED_SCHEMES` et 4 types `Literal`, plus 4 contraintes `CHECK` en base (`0002:L98`, `L174` ; `0004:L25`, `L61`).
4. **Ce que charge l'import** : `import orcia_core.orchestration` charge `catalog.bmad_adapter` et `permissions.broker`.

> ⚠️ **Écart à traiter** : `3.2b` est en `done`, et son commit (`fb7d460`) annonce un « DBOS engine », alors que l'étape durable reste figée. **Ne pas rouvrir `3.2b`.** Consigner l'écart dans la proposition (section « Écarts de livraison constatés ») et le reprendre dans `3.2e`. Ajouter un `action_item` `PROC-01` pour renforcer la *Definition of Done* : un run réel de bout en bout via l'API est exigé dès qu'une story touche le moteur.

**Livrable** : un tableau « Constat → confirmé ou infirmé → preuve » et les risques GitNexus. **Signaler tout risque HIGH ou CRITICAL.**

---

## Étape 1 : `bmad-correct-course`, proposition de changement (Avenant A2)
Produire **l'avenant A2 (28/10/2026)** dans `sprint-change-proposal-2026-10-27.md`.

### 1.1 Positionnement et PRD
- Rendre explicite le principe **« Core agnostique et packs métier »** : le SDLC devient **le premier pack** (`orcia-pack-sdlc`), pas le Core.
- Proposer les ajouts au PRD :
  - **NFR-EXT-1** : un connecteur s'ajoute sans modifier le Core, en moins de 150 lignes et en moins d'une demi-journée ;
  - **NFR-SEC-4** : aucun secret ne doit se retrouver dans les tables ou les logs (test du secret témoin) ;
  - **NFR-ISO-1** : le Core s'exécute sans le pack SDLC.
- Vérifier la cohérence avec FR-13 (intention → code) : la règle **reste en vigueur pour le SDLC**, mais elle est portée par le pack.

### 1.2 Nouvelle Story 3.2e (P0, avant 3.3)
**« Séparation Core et pack SDLC, interface de connecteur unique, exécution réelle des étapes et taxonomie d'erreurs »**. Elle regroupe P0-1 à P0-4 de l'audit, soit environ 13 à 16 jours.

> Si l'effort dépasse un sprint, **découper** en `3.2e` (P0-1 et P0-2 : pack SDLC et interface de connecteur) et `3.2f` (P0-3 et P0-4 : exécution réelle et erreurs), en justifiant le découpage.

| Bloc | Contenu attendu |
|---|---|
| **P0-1 Pack SDLC** | Créer `packages/orcia-pack-sdlc`. `writes_code`, `declares_intention`, `reverse_doc_from_code` et `mode` deviennent des `tags` ou `policies` génériques. FR-13 devient un plugin `orcia.workflow_policies`. `MemlogMarkerType` devient une chaîne avec espace de noms (`sdlc.*`) validée par un registre. `bmad_adapter`, les régimes RAG code et Jira, l'audit documentation-vs-code et le graphe tripartite passent dans le pack. Les chaînes de démonstration sont retirées du moteur. |
| **P0-2 Interface de connecteur unique** | `ConnectorPort` dans `orcia_kernel` (`capabilities`, `fetch`, `invoke(…, idempotency_key)`, `health`, `map_error`). Registre `orcia.connectors` **branché** sur `FederatedUriResolver`. Une **seule source de vérité** pour les types de source. Les `CHECK` en base sont remplacés par une table `connector_schemes` et une clé étrangère (**migration Expand → Contract**, nouvelle révision, jamais de modification d'une révision existante). Kit de tests de conformité. |
| **P0-3 Exécution réelle** | Registre `orcia.step_executors` (`AGENT`, `SKILL`, `SUB_WORKFLOW`, `HUMAN_TASK`, `HTTP_ACTION`). L'étape DBOS appelle l'exécuteur. Le moteur simulé est supprimé et ses tests sont repris en non-régression. `_ACTIVE_ENGINE` et l'appel à l'API privée DBOS sont supprimés. Branchement dans `dependencies.py` et dans le worker. |
| **P0-4 Erreurs et relances** | Dans `orcia_kernel.errors` : `TransientInfraError(retry_after_s)`, `RateLimitedError`, `UpstreamTimeoutError`, `FunctionalConnectorError`, `PolicyDeniedError`, `PermanentInfraError`. Un `ConnectorInvoker`, exécuté comme étape durable DBOS : relances sur les seules erreurs passagères, respect de `Retry-After`, coupe-circuit par connecteur, idempotence, budget AD-12. |

**Critères d'acceptation obligatoires (testables)** :
- nouveau contrat `import-linter` : `orcia_kernel` et `orcia_core` n'importent jamais `orcia_pack_sdlc` ;
- `grep -riE "writes_code|BUG_CODE|DOC_OBSOLETE|brownfield|confluence|git://|jira" packages/orcia-kernel packages/orcia-core/src/orcia_core/orchestration` ne remonte rien ;
- un connecteur factice `sap://` ajouté **sans modifier aucun fichier du Core**, en moins de 150 lignes, et qui passe le kit de conformité ;
- run **réel** de bout en bout via l'API, reprise après redémarrage, 0 contenu simulé ;
- erreur 429 → relances puis succès ; erreur fonctionnelle → 0 relance et passage en arbitrage ; coupe-circuit ouvert après N échecs ;
- **job CI `core-without-sdlc`** : le workflow Finance « Rapprochement de factures », avec un connecteur ERP factice, s'exécute **avec le pack SDLC désinstallé** (P2-2) ;
- couverture ≥ 90 % et les 5 couches de tests (AD-17).

### 1.3 `action_items` P1 et P2 (rattachés aux stories existantes)
| ID | Titre | Rattachement | Dépendance |
|---|---|---|---|
| `DEC-SEC-01` | `SecretRef` non sérialisable, `SecretProviderPort` (fusionner ou relier à `SEC-03`), masquage structlog, liste blanche pour l'outbox et l'audit, **test du secret témoin** (tables `dbos.*`, `audit_ledger`, `domain_events_outbox`, `step_executions` et logs), suppression de la valeur par défaut écrite en dur dans `litellm_adapter.py:L31` | `4.2` (PII) / `SEC-03` | `3.2e` (P0-2, P0-4) |
| `DEC-ACC-01` | `AccessRequestChannelPort` (Jira devient un adaptateur) ; `jira_request_url` remplacé par `request_url` générique (Expand → Contract) | Epic 1 (dette) / `4.4` | `3.2e` (P0-2) |
| `DEC-CONC-01` | `ResourceLeasePort` (bail PostgreSQL et jeton de fencing), files DBOS par classe de ressource, ordre d'acquisition canonique, délais d'expiration, détection des attentes cycliques parent-enfant | `5.1` (prise en charge et verrous, AD-4) | `3.2e` (P0-3) |
| `DEC-CTX-01` | `ContextSourcePort` (JSON, CAS, document), `VectorStorePort`, régimes d'indexation en plugins `orcia.indexers` | `3.3` (Assistant) | `3.2e` (P0-1, P0-2) |
| `DEC-SEED-01` | Sortir les données de démonstration de `rag/__init__.py` et `orchestration/seeds.py` vers `bootstrap` ou les fixtures | `3.2e` (étape 0) | — |
| `PROC-01` | *Definition of Done* renforcée : run réel de bout en bout exigé pour toute story qui touche le moteur | Processus | — |

### 1.4 Ordre des stories
```
3.2c (done) ─┬─> 3.2e [3.2f] (Core agnostique) ─> 3.3 ─> 3.4 ─> 3.5 ─> Epic 4 …
3.2d (en cours, en parallèle, non impactée) ───┘
```
- Vérifier que **3.3, 4.1, 4.2, 5.1 et 7.x** dépendent bien de `3.2e`, et ajuster leurs critères d'acceptation **sans modifier les stories `done`**.
- Estimer l'impact sur le calendrier et les risques (notamment la migration des contraintes `CHECK` sur des données existantes et la reprise des tests du moteur simulé).

⏸️ **Pause : je valide l'avenant A2.**

---

## Étape 2 : `bmad-architecture`, mode *update*
- **Nouvel AD-20** « Core agnostique et packs métier » : frontières, registres (`orcia.connectors`, `orcia.step_executors`, `orcia.workflow_policies`, `orcia.indexers`), espace de noms des marqueurs, règle « aucun vocabulaire métier dans le kernel et l'orchestration ».
- **Amender** :
  - AD-5 (types de source ouverts, `connector_schemes`) ;
  - AD-12 (taxonomie d'erreurs, `ConnectorInvoker`, budget de relances) ;
  - AD-13 et AD-2 (exécuteurs d'étape réels, suppression de l'état global et de l'API privée DBOS) ;
  - AD-6 (`SecretRef`, `SecretProviderPort`, canal de demande d'accès générique) ;
  - AD-4 (baux de ressources et fencing) ;
  - AD-19 (contrat `import-linter` sur le pack SDLC).
- Tableau des capacités et de leur emplacement : FR-13 rattachée à `orcia-pack-sdlc`.
- Lint obligatoire, **0 finding** :
  `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`

---

## Étape 3 : `bmad-create-epics-and-stories`, mise à jour
- Rédiger dans `epics.md` la **Story 3.2e** (et `3.2f` en cas de découpage) : récit, critères d'acceptation Given/When/Then reprenant ceux du §1.2, AD concernés, dépendances, 5 couches de tests.
- Ajuster les critères d'acceptation et les dépendances de `3.3`, `4.1`, `4.2`, `4.4`, `5.1` et `7.x`.
- Ajouter **NFR-EXT-1, NFR-SEC-4 et NFR-ISO-1** à l'inventaire des exigences d'`epics.md`, avec leur traçabilité.
- **Interdit** : modifier les sections des stories `done` (`3.1`, `3.2`, `3.2a`, `3.2s`, `3.2b`, `3.2c`) ainsi que `3.2d` (en cours).

---

## Étape 4 : `bmad-sprint-planning`, mode *validate/fix*
- `sprint-status.yaml` : ajouter `3-2e-…` (et `3-2f-…`) en `ready-for-dev` après `3-2d` ; ajouter les `action_items` `DEC-*` et `PROC-01` (identifiant, titre, action, priorité, `depends_on`, `ad_ref`, `story_ref`, responsable, statut, epic) ; mettre à jour `last_updated`.
- Lancer :
  `.venv/bin/python .agent/skills/bmad-sprint-planning/scripts/sprint_plan.py validate --status-file docs/implementation-artifacts/sprint-status.yaml`

---

## Étape 5 : vérification finale (obligatoire, recommencer jusqu'à obtenir CONFORME)
Lancer `bmad-review` (lentilles *verification gaps* et *structure*) sur le diff des étapes 1 à 4, puis ajouter à la proposition la section **« Vérification Avenant A2 »**.

### 5.1 Matrice de traçabilité (aucune case vide)
| ID de l'audit | Élément | Décision (Retenu / Différé / Rejeté + justification) | AD | Story ou action_item | Critère d'acceptation vérifiable | Preuve (fichier:ligne) |
|---|---|---|---|---|---|---|
| L1 à L11 | Fuites de vocabulaire | | | | | |
| K1 à K9 | Risques de couplage | | | | | |
| P0-1 à P0-4 | Actions prioritaires | | | | | |
| P1-1 à P1-4 | Actions P1 | | | | | |
| P2-1, P2-2 | Données de démonstration, preuve sur un vertical | | | | | |
| §3.1 à §3.4 | Erreurs, secrets, mémoire, concurrence | | | | | |
| Écart 3.2b | Livraison du « DBOS engine » non conforme | | | | | |

### 5.2 Contrôles automatiques (sorties collées)
- [ ] `lint_spine.py` : 0 finding
- [ ] `sprint_plan.py validate` : `valid: true`
- [ ] `grep -n "AD-20" ARCHITECTURE-SPINE.md` : présent ; AD-2, 4, 5, 6, 12, 13 et 19 amendés (lignes citées)
- [ ] `grep -nE "NFR-EXT-1|NFR-SEC-4|NFR-ISO-1" prd.md epics.md` : présents et reliés à leur story
- [ ] Chaque story `3.2e` (et `3.2f`) et chaque `DEC-*` est présente à la fois dans `epics.md` et dans `sprint-status.yaml`
- [ ] Aucun cycle de `depends_on` ; toutes les `story_ref` existent
- [ ] `git diff` sur les sections des stories `done` et de `3.2d` : **0 ligne modifiée**
- [ ] `git diff --stat` : seuls la proposition, `prd.md`, la spine, `architecture.md`, `epics.md` et `sprint-status.yaml` sont modifiés. Les fichiers de `apps/web` et `packages/api-client` liés à `3.2d` restent inchangés par ce travail.

### 5.3 Résultat attendu
- Un verdict **CONFORME / NON CONFORME**, avec la liste des éléments manquants. En cas de NON CONFORME : corriger, puis relancer l'étape 5.
- Les fichiers modifiés, les questions ouvertes restantes et la **prochaine action** : `bmad-build` sur `3.2e` dès que `3.2d` est livrée (ou en parallèle si la capacité le permet).
