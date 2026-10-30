# Spécification d'Implémentation — Story 8.2 : Abstraction des Tiers Cognitifs LLM (`simple|medium|complex|auto`), Effort & Routage Déterministe (`AD-21`, `PROC-01`)

- **Story Key** : `8-2-abstraction-llm-tiers-routage-auto`
- **Epic** : `Epic 8` (`AD-21`, `AD-10`, `AD-12`, `PROC-01`)

## 1. Critères d'Acceptation & Invariants
1. **Tiers Cognitifs Abstraits & Effort (`UX-DR17`)** :
   - Les workflows et l'interface utilisateur manipulent exclusivement `inference_tier IN ('simple', 'medium', 'complex', 'auto')` et `effort IN ('default', 'fast', 'balanced', 'deep')` ; aucun nom de modèle physique n'est codé en dur dans les DAGs.
2. **Escalade Déterministe `auto` & Idempotence DBOS (`inference_attempts`)** :
   - En mode `auto`, l'escalade `simple -> medium -> complex` persiste chaque sous-tentative dans `inference_attempts` via une clé d'idempotence `"{run_id}:{step_execution_id}:attempt-{idx}"`.
   - En cas de replay DBOS après crash/redémarrage, les tentatives déjà enregistrées sont relues sans ré-invoquer le LLM.
3. **Orthogonalité `AD-10`, Quotas Hiérarchiques & Épinglage (`409`)** :
   - Vérification `assert_model_orthogonality` entre modèle générateur et modèle évaluateur.
   - Plafonds budgétaires hiérarchiques (`GLOBAL -> BU -> TEAM -> WORKSPACE`).
   - Suppression d'un mapping épinglé par un run actif refusée avec `HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` (modes `reject`, `drain`, `force`).
4. **Preuve `PROC-01`** :
   - Cycle durable complet vérifié : démarrage -> escalade `auto` (`simple` -> `medium`) -> pause d'arbitrage humain -> replay après redémarrage (`0` doublon LLM) -> reprise -> `COMPLETED`.
