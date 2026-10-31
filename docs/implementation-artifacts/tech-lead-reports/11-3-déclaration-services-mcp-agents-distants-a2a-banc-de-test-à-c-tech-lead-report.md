# Rapport Tech Lead — Story 11.3 : Déclaration Guidée des Services / Serveurs MCP & `@Agents Distants (MCP / A2A)`, Exposition MCP Gouvernée (`/api/v1/mcp`) et Banc de Test à Chaud en 4 Étapes (`🔌`)

## 1. Analyse du Besoin & Étude d'Impact Tech Lead

### 1.1 Contexte & Problématique
La **Story 11.3** livre deux capacités symétriques autour des protocoles MCP et A2A (`Principes M.1, M.2 & M.4`) :
1. **Banc de Test & Découverte Automatique à Chaud en 4 Étapes (`🔌`, `POST /api/v1/settings/connectors/test-and-discover`)** :
   - **Étape 1 (`1. Réseau, TLS & Anti-SSRF`)** : Validation DNS/TLS et blocage de toute IP privée, loopback ou metadata cloud (`169.254.169.254`, `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) non explicitement autorisée ;
   - **Étape 2 (`2. Authentification`)** : Validation du secret via `SecretProviderPort` ; en mode **`Passthrough` (`AD-6`)** sans jeton personnel de l'administrateur, affiche **`🟠 En attente de jeton utilisateur (Passthrough)`** (`WAITING_USER_PASSTHROUGH_TOKEN`), **sans bloquer le bouton `Activer`** dès lors que les étapes 1 et 3 sont vertes (`can_activate = True`) ;
   - **Étape 3 (`3. Découverte Automatique du Contrat`)** : Qualification automatique de chaque outil découvert en **`👁️ Lecture seule`** (`READ_ONLY`) vs **`✍️ Écriture -> Action Staged obligatoire (AD-3)`** (`WRITE_STAGED_REQUIRED`) ;
   - **Étape 4 (`4. 💬 Essai Rapide à Chaud (Dry-Run)`)** : Exécution d'un appel de test en lecture seule borné par un **timeout strict de `5 s`**, une **taille maximale de réponse de `1 Mo`** (`1_048_576` octets) et tracé sous `actor_type: ADMIN_CONNECTION_TEST` (`run_id: null`), retournant les métriques FinOps `_meta.usage`.
2. **Exposition MCP Gouvernée des Agents Locaux & de `Mon Assistant` (`/api/v1/mcp/spaces/{ws_slug}`, `/api/v1/mcp/agents/{agent_slug}`)** sous les **7 Verrous Matériels de Sécurité (`Principe M.4`)** :
   - Validation `pat_mcp_*` scopé (`SHA-256`) ;
   - Identité `Passthrough` obligatoire (`AD-6`) ;
   - Protection de la propriété intellectuelle (`execute` $\neq$ `read`, masquage intégral du `system_prompt` Couches 1–4, des `SecretRef` et des snippets `[S1]` restreints -> `[S1 · 🔒 Source restreinte]`) ;
   - Traversée de `🔒 AssistantHarness` & `PiiReversibleScrubber` + anti-citation fantôme ;
   - Sanctuarisation des Ancrages Humains (`HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`) et Mode Observateur (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`) ;
   - Mutations externes en `Action Staged` uniquement ;
   - Quotas FinOps `_meta.usage`, badge `💻 Appelé via MCP (IDE)` et trace `actor_type: MCP_IDE_CLIENT`.

### 1.2 Analyse d'Impact GitNexus
- `gitnexus_impact({target: "GovernedMcpServerService", direction: "upstream", repo: "ORCIA"})` : `risk: LOW`, `impactedCount: 1`.

---

## 2. Plan d'Implémentation

### 2.1 Noyau Hexagonal (`packages/orcia-core`)
- `packages/orcia-core/src/orcia_core/orchestration/remote_test_bench_and_mcp_exposure.py` : `RemoteServiceTestBenchAndGovernedMcpService` implémentant le banc de test 4 étapes (Anti-SSRF, Passthrough non-bloquant, qualification `READ_ONLY` vs `WRITE_STAGED_REQUIRED`, Dry-Run `< 5 s` / `<= 1 MB` `ADMIN_CONNECTION_TEST`) et l'exposition MCP gouvernée avec ses 7 verrous matériels.

### 2.2 Backend FastAPI & SDK OpenAPI (`apps/api`)
- Schémas dans `apps/api/src/orcia_api/schemas/epic11_mcp_test_bench.py` et endpoints dans `apps/api/src/orcia_api/routers/epic11_mcp_and_test_bench.py`.

### 2.3 Interface SPA Direction C (`packages/ui`)
- Primitive `@orcia/ui` `RemoteServiceTestBenchAndMcpExposureView.tsx` (`remote-service-test-bench`) affichant les 4 étapes temps réel, le badge `🟠 En attente de jeton utilisateur (Passthrough)`, l'interrupteur `🔌 Exposer en MCP` et les 7 verrous matériels.

---

## 3. Bilan des Modifications & Résultats

| Fichier | Action | Rôle |
|---|---|---|
| `packages/orcia-core/src/orcia_core/orchestration/remote_test_bench_and_mcp_exposure.py` | Créé | Banc de test 4 étapes & Serveur MCP gouverné (7 verrous matériels) |
| `apps/api/src/orcia_api/schemas/epic11_mcp_test_bench.py` | Créé | Schémas OpenAPI 3.1 Story 11.3 |
| `apps/api/src/orcia_api/routers/epic11_mcp_and_test_bench.py` | Créé | Endpoints `/api/v1/settings/connectors/test-and-discover` & `/api/v1/mcp/*` |
| `packages/ui/src/primitives/RemoteServiceTestBenchAndMcpExposureView.tsx` | Créé | Primitive Direction C `@orcia/ui` (`remote-service-test-bench`) |
| `tests/unit/test_epic_11_story_11_3_test_bench_and_mcp_exposure.py` | Créé | Tests unitaires & contrat API FastAPI |
| `tests/integration/test_story_11_3_mcp_and_test_bench_postgres18_redis.py` | Créé | Tests d'intégration réels PG18 + Redis 7.4 `testcontainers` |
