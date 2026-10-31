# Rapport Tech Lead — Story 10.2 : Garantie de Latence (`TTFT < 1.2s`), Cache Redis du Prompt Assemblé & 3 Vitesses Conversationnelles

- **Story Key** : `10-2-garantie-de-latence-ttft-1-2s-cache-redis-prompt-assemblé-3-v`
- **Epic** : `Epic 10 — Mon Assistant All-in-One (Compagnon Gouverné, 3 Vitesses, Citations & Dossiers)`
- **Date** : `2026-10-31`
- **Statut** : `done`
- **Auteur** : Tech Lead / Senior Dev Agent (`AD-15`, `AD-19`, `NFR-PERF-1`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Problématique
Pour éviter que le DAG à 5 nœuds de `orcia://system/workflows/assistant-agent` (`Story 3.3`) et l'assemblage du harnais à 5 couches (`Story 10.1`) ne dégradent l'interactivité conversationnelle (`NFR-PERF-1` : `TTFT < 1.2 s` en mode standard), **Story 10.2** met en œuvre :
1. **Un cache Redis dédié au prompt système assemblé à 5 couches** (`assistant:prompt:<workspace_id>:<user_id>:<hat>`, `TTL = 300s`, lecture `< 5 ms`) avec invalidation déterministe sur :
   - Événement Outbox `SettingsChanged` (`domain_events_outbox`),
   - Modification d'une surcharge `workspace_customization_overrides` (`USER`, `WORKSPACE`, `TEAM`),
   - Promotion d'un terme au Glossaire de l'Espace (`GLOSSARY_PROMOTED`).
2. **Trois vitesses conversationnelles explicites** :
   - **Vitesse 1 (`⚡ Rapide` / `SPEED_1_FAST`, défaut)** : Nœuds `1..4` exécutés comme fonctions déterministes pures en `< 80 ms` (`0` appel LLM intermédiaire) + **1 seul appel LLM en streaming SSE** au Nœud `5` (`TTFT < 1.2 s`).
   - **Vitesse 2 (`@Agent` / `/Skill` / `SPEED_2_AGENT_TOOLS`)** : Déclenchée par mention `@Agent` ou `/Skill` ; diffusion SSE temps réel de l'étape d'interrogation (`🔍 Interrogation de Jira...`, `⚙️ Invocation du connecteur...`) et appel `ConnectorInvoker` (`TTFT < 2.5 s`).
   - **Vitesse 3 (`🧠 Approfondi` / `SPEED_3_DEEP_AUDIT`)** : Déclenchée par la pilule `🧠 Approfondi` ; active la planification LLM intermédiaire, la vérification multi-facettes (`AD-10`) et l'affichage de la progression étape par étape.

### 1.2 Analyse d'Impact GitNexus (`repo: "ORCIA"`)
- `gitnexus_impact({target: "AssistantAgentService", direction: "upstream", repo: "ORCIA"})` : `risk: LOW` (`impactedCount: 2` — `orchestration/__init__.py` et `assistant_governance.py`).
- `gitnexus_impact({target: "AssistantFourLevelGovernanceService", direction: "upstream", repo: "ORCIA"})` : `risk: UNKNOWN` (nouveau service `Story 10.1`, appelé uniquement par `dependencies.py` et `epic10_assistant.py`).
- Afin de respecter la limite de `300–400` lignes par fichier et `AD-19` (`0` import `redis` dans `orcia_core`), nous créons `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py` avec un protocole pur `AssembledPromptCachePort` injectable (adaptable à Redis 7.4 en production et `testcontainers` ou en mémoire pour les tests unitaires).

### 1.3 Opportunités de Factorisation & Dette Technique
- Réutilisation directe de `AssistantFourLevelGovernanceService.assemble_five_layers_preview` (`Story 10.1`) pour construire le payload du cache `assistant:prompt:<workspace_id>:<user_id>:<hat>`.
- Aucune dette technique résiduelle identifiée.

---

## 2. Plan d'Implémentation

### 2.1 Base de Données & Cache Redis (`infra/migrations/`)
- Pas de nouvelle table SQL requise (les événements d'invalidation passent par la table existante `domain_events_outbox` et les surcharges par `workspace_customization_overrides`).
- Clé Redis : `assistant:prompt:{workspace_id}:{user_id}:{hat}` (`SETEX 300`).

### 2.2 Noyau Hexagonal (`packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py`)
- `AssembledPromptCachePort` (protocole `get`, `set_with_ttl`, `delete_by_prefix`).
- `AssistantThreeSpeedRouterService` :
  - `get_or_assemble_cached_prompt(workspace_id, user_id, hat)` (`cache_hit: bool`, `lookup_latency_ms: float < 5.0`, `ttl_seconds = 300`).
  - `invalidate_prompt_cache(workspace_id, reason, user_id=None)` déclenché sur `SETTINGS_CHANGED`, `OVERRIDE_UPDATED` ou `GLOSSARY_PROMOTED`.
  - `execute_three_speed_turn(...)` et `stream_three_speed_turn_sse(...)` gérant `SPEED_1_FAST`, `SPEED_2_AGENT_TOOLS` et `SPEED_3_DEEP_AUDIT`.

### 2.3 Backend FastAPI (`apps/api/src/orcia_api/routers/epic10_assistant.py`)
- `POST /api/v1/assistant/three-speed/turn`
- `POST /api/v1/assistant/three-speed/stream`
- `POST /api/v1/assistant/three-speed/invalidate-cache`

### 2.4 Interface SPA (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`)
- Sélecteur de vitesse (`⚡ Rapide`, `🛠️ @Agent / /Skill`, `🧠 Approfondi`), badge Cache Redis (`⚡ Cache 5 couches < 5 ms · HIT/MISS`), chronomètre `TTFT` et journal temps réel des étapes (`🔍 Interrogation de Jira...`, `🔬 Vérification multi-facettes AD-10...`).

---

## 3. Bilan des Modifications & Résultats

| Fichier | Action | Rôle |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py` | Créé | Cache `assistant:prompt:<ws>:<user>:<hat>` (`TTL 300s`) + routeur 3 vitesses |
| `apps/api/src/orcia_api/schemas/assistant.py` | Modifié | Schémas `ThreeSpeedTurnRequest/Response`, `InvalidatePromptCacheRequest/Response` |
| `apps/api/src/orcia_api/routers/epic10_assistant.py` | Modifié | Endpoints `/three-speed/turn`, `/three-speed/stream`, `/three-speed/invalidate-cache` |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` | Créé | Primitive UI `@orcia/ui` Direction C pour les 3 vitesses conversationnelles |
| `tests/unit/test_epic_10_story_10_2_three_speed_router.py` | Créé | Tests unitaires & API des 3 vitesses + invalidation du cache |
| `tests/integration/test_story_10_2_redis_prompt_cache_and_outbox.py` | Créé | Test d'intégration réel Redis 7.4 + PostgreSQL 18 (`testcontainers`) |
| `packages/ui/src/__tests__/epic10-assistant.test.tsx` | Modifié | Test Vitest de `AssistantSpeedSelectorAndStreamView` |
