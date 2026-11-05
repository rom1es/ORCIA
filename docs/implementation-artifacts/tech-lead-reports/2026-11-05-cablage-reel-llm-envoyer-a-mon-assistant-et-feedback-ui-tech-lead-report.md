# 2026-11-05 — Câblage Effectif de « Envoyer à Mon Assistant » sur le Modèle IA Configuré (Ollama / OpenAI / Anthropic / Mistral) & Retour Immédiat dans l'Interface

> **Convention de nommage du fichier (Obligatoire — à créer AVANT toute modification de code)** :
> - Demande d'ajustement, correctif ou évolution hors Story : `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md`

- **Date** : 2026-11-05
- **Story / Clé Sprint** : `2026-11-05-cablage-reel-llm-envoyer-a-mon-assistant-et-feedback-ui` (`Ajustement Transverse Post-Epic 12`)
- **Auteur / Contexte** : Résolution du constat utilisateur *« la conf LLM est réalisée et testée ok. ce test "Envoyer à Mon Assistant" ne repond rien. »* — Câblage de bout en bout entre la configuration LLM enregistrée (`platformSetupStore` / PostgreSQL 18 `llm_model_endpoints`), le composant UI [`AssistantSpeedSelectorAndStreamView`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx), le panneau [`InboxFeaturePanel`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/index.tsx), l'endpoint FastAPI `POST /api/v1/assistant/three-speed/turn` ([`assistant_workspace.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_workspace.py)) et le serveur de modèle IA configuré (ex. Ollama local `gemma4:12b` sur `http://localhost:11434/api` ou `/v1`, OpenAI, Anthropic, Mistral).
- **Commits associés** : *(à compléter en Section 3 après validation des portes de qualité)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
L'utilisateur a configuré et testé avec succès son modèle IA dans l'onglet **`Modèles IA`** (`Configuration` $\rightarrow$ `gemma4:12b`, `Ollama Local`, `http://localhost:11434/api`, mode `Sans clé (Serveur local)`), puis s'est rendu dans **`Mon Assistant`** (`/assistant` / `/inbox`) et a cliqué sur le bouton **« Envoyer à Mon Assistant »** (`data-testid="assistant-three-speed-send-btn"`).

**Quatre causes racines combinées** expliquaient pourquoi le clic sur « Envoyer à Mon Assistant » semblait ne rien répondre ou ne sollicitait pas le modèle IA configuré :
1. **Absence de retour d'action si le champ est vide et absence de soumission par la touche `Entrée` dans [`AssistantSpeedSelectorAndStreamView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx#L213-L241)** :
   - Cliquer sur « Envoyer à Mon Assistant » avec un champ vide appelait `onSendTurn({ userPrompt: "", ... })`.
   - Côté [`InboxFeaturePanel`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/index.tsx#L109-L129), l'appel `POST /api/v1/assistant/three-speed/turn` échouait alors en **HTTP 422 Unprocessable Entity** (`ThreeSpeedTurnRequest.user_prompt` ayant `min_length=1`), et le `.catch(() => undefined)` avalait silencieusement l'erreur sans aucun message à l'écran !
   - De plus, appuyer sur `Entrée` dans le champ `assistant-three-speed-input` ne déclenchait pas l'envoi, aucun indicateur de chargement (*« Réponse en cours de génération... »*) n'apparaissait pendant l'inférence du modèle local (qui prend quelques secondes sur un modèle 12B local), et les métriques d'exécution (`stepProgress`, `cacheHit`, `cacheLookupMs`, `nodes1To4DeterministicMs`, `ttftMs`) restaient figées à `0` / `[]` dans [`InboxFeaturePanel`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/index.tsx#L99-L108).
2. **Déconnexion entre l'endpoint `/api/v1/assistant/three-speed/turn` et le modèle IA réellement configuré par l'utilisateur** :
   - Dans [`AssistantThreeSpeedRouterService.execute_three_speed_turn`](file:///home/romain/Documents/Projects/ORCIA/packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py#L292-L457), la réponse était une chaîne statique pré-formatée (`[⚡ Vitesse 1 · Casquette ...] Réponse directe générée avec prompt 5 couches...`) qui **n'invoquait jamais** le modèle IA configuré dans `Modèles IA` (`gemma4:12b` sur `http://localhost:11434/api` ou `/v1`).
3. **Normalisation des URL Ollama (`/api` vs `/v1`) et exécution réelle de l'appel HTTP vers le LLM** :
   - L'utilisateur a saisi `http://localhost:11434/api` (URL native Ollama `/api/chat`) ou `http://localhost:11434/v1` (URL compatible OpenAI `/v1/chat/completions`).
   - Le backend doit détecter le modèle IA configuré (dans `request.app.state.platform_setup_snapshot.llm_tiers`, `accostage_service`, ou PostgreSQL 18 `llm_model_endpoints`) et appeler réellement le serveur LLM (via `/api/chat` ou `/v1/chat/completions` pour Ollama/OpenAI-compatible, ou `/v1/messages` pour Anthropic) avec le prompt système assemblé et la question de l'utilisateur, tout en conservant un repli déterministe immédiat pour les tests unitaires / CI hors-ligne (`ORCIA_USE_CASSETTE_LLM` ou absence de serveur local).
4. **Vérification réelle lors du bouton « 🔌 Tester la connexion au modèle » (`/api/v1/bootstrap/welcome-setup/llm-test`)** :
   - Pour les endpoints locaux (`http://localhost...` / `http://127.0.0.1...`), l'endpoint de test de connexion vérifiait uniquement le format de l'URL sans interroger réellement le serveur local si celui-ci est joignable, ou sans normaliser `/api` et `/v1`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` sur `repo: "/home/romain/Documents/Projects/ORCIA"`)** :
  - `AssistantSpeedSelectorAndStreamView` (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`) :
    - `impactedCount: 1` (appelé dans `InboxFeaturePanel` et testé dans `packages/ui/src/__tests__/assistant-workspace.test.tsx`), `risk: LOW`.
  - `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) :
    - Monté par `ModuleWorkspaceView` (`apps/web/src/components/ModuleWorkspaceView.tsx:L71`) sur les routes `/assistant` et `/inbox`, `risk: LOW`.
  - `execute_three_speed_turn` (`packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py`) :
    - `impactedCount: 2` (`execute_three_speed_turn_endpoint` et `stream_three_speed_turn_sse` dans `apps/api/src/orcia_api/routers/assistant_workspace.py`), `risk: LOW`.
- **Exploration & Chiffres Clés (Base de Données PostgreSQL 18 & Serveur Ollama Local)** :
  - Inspection de `GET /api/v1/bootstrap/platform-setup-state` sur `http://127.0.0.1:8000` :
    - `llm_tiers` contient : `{"tier": "medium", "primaryModel": "gemma4:12b", "modelFamily": "Ollama Local", "endpointUrl": "http://localhost:11434/api", "authMode": "none_local"}`.
  - Test direct du serveur Ollama local (`http://localhost:11434/api/tags` et `POST http://localhost:11434/v1/chat/completions`) :
    - Le modèle `gemma4:12b` (`11.9B`, `Q4_K_M`) est bien chargé et répond en français avec raisonnement (`thinking` / `content`).
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 300–400 lignes`)** :
  - [`apps/web/src/features/inbox/index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/index.tsx) fait `239` lignes : maintien sous `300` lignes.
  - [`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`](file:///home/romain/Documents/Projects/ORCIA/packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx) fait `245` lignes : maintien sous `300` lignes.
  - Extraction d'un helper dédié d'appel HTTP LLM en temps réel dans `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` (`< 220` lignes) afin de ne pas alourdir `apps/api/src/orcia_api/routers/assistant_workspace.py` et de respecter strictement `AD-19` (`zero framework/httpx import` dans `orcia_core/orchestration/assistant_three_speed_router.py`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration Alembic requise : les tables `llm_model_endpoints` et `system_bootstrap_runs` (`platform_setup_snapshots`) stockent déjà la configuration complète des niveaux IA (`endpointUrl`, `primaryModel`, `modelFamily`, `authMode`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py` :
  - Permettre à `execute_three_speed_turn` de recevoir un texte de réponse LLM optionnel (`llm_response_override: str | None = None`) et une latence d'inférence optionnelle (`llm_latency_ms_override: float | None = None`) ou un `llm_completion_fn: Callable[[str, str, str], tuple[str, float] | None] | None = None`, tout en conservant `0` import de bibliothèque réseau dans `orcia_core` (`AD-19`) et en gardant le comportement déterministe `< 1200 ms` par défaut pour les tests unitaires existants (`test_epic_10_story_10_2_three_speed_router.py`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- Création de `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` :
  - Résout le modèle IA actif à partir du niveau configuré dans `request.app.state.platform_setup_snapshot` (ou PostgreSQL 18 `load_platform_setup_state_from_postgres18` / `accostage_service.llm_endpoints`).
  - Supporte nativement :
    - **Ollama / vLLM / OpenAI-compatible** : normalise automatiquement toute URL `http://localhost:11434`, `http://localhost:11434/api` ou `http://localhost:11434/v1` vers `/v1/chat/completions` (avec repli sur `/api/chat` si nécessaire), extrait `message.content` (ou `message.reasoning` / `thinking` si `content` est vide), et gère l'authentification (`Bearer <api_key>` ou sans clé en local).
    - **Anthropic (`/v1/messages`)** et **OpenAI / Mistral (`/v1/chat/completions`)**.
  - En cas d'environnement de test (`TestClient` / `ORCIA_USE_CASSETTE_LLM=1` ou aucune configuration LLM réelle), conserve le comportement déterministe rapide afin de ne casser aucun test unitaire/CI.
- `apps/api/src/orcia_api/routers/assistant_workspace.py` :
  - Dans `execute_three_speed_turn_endpoint` (et `stream_three_speed_turn_endpoint`), invoque `assistant_llm_bridge.invoke_configured_llm_for_assistant_turn(request, ...)` lorsque l'utilisateur soumet une question à Mon Assistant, et injecte la vraie réponse du modèle IA (ex. `gemma4:12b`) ainsi que la vraie latence mesurée et l'étape d'exécution correspondante.

### 2.4 Interface Utilisateur & Expérience (`packages/ui/` & `apps/web/`)
1. `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` :
   - Ajout du support de la touche **`Entrée`** (`onKeyDown`) dans le champ `assistant-three-speed-input` pour envoyer la question immédiatement.
   - Si l'utilisateur clique sur **« Envoyer à Mon Assistant »** alors que le champ de saisie est vide, utiliser une question de test par défaut (*« Bonjour, peux-tu te présenter brièvement et confirmer que tu es opérationnel ? »* / *« Hello, can you briefly introduce yourself and confirm you are operational? »*) OU afficher un retour visuel immédiat pour que le bouton **« Envoyer à Mon Assistant »** réponde toujours dès le premier clic (particulièrement lorsque l'utilisateur teste la connexion de son Assistant juste après avoir configuré son LLM !).
   - Ajout des props optionnelles rétrocompatibles `isGenerating?: boolean` et `errorMessage?: string | null` pour afficher clairement l'état *« ⏳ Génération de la réponse en cours... »* pendant que le LLM répond, ainsi que toute erreur éventuelle, et rendre `streamedText` bien lisible (`whitespace-pre-wrap`).
2. `apps/web/src/features/inbox/index.tsx` :
   - Mise à jour complète des états lors de `onSendTurn` :
     - Affichage immédiat de l'indicateur de génération (`isGenerating = true`, `streamedText = "⏳ Mon Assistant prépare votre réponse..."`),
     - Mise à jour des métriques retournées par l'API (`cacheHit`, `cacheLookupMs`, `nodes1To4DeterministicMs`, `ttftMs`, `stepProgress`) et du texte final `res.response_text`,
     - Gestion explicite des erreurs dans `.catch(...)` (au lieu de `.catch(() => undefined)`) pour afficher un message clair si le serveur ou le modèle IA rencontre une erreur ou un délai dépassé.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Créés & Modifiés

| Fichier | Action | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py` | **Modifié** | Ajout des paramètres optionnels rétrocompatibles `llm_response_override`, `llm_step_label_override` et `llm_latency_ms_override` sur `execute_three_speed_turn` et `stream_three_speed_turn_sse` tout en préservant l'isolation pure `AD-19` (`0` import HTTP/SDK dans `orcia_core`). |
| `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` | **Créé** | Pont d'exécution LLM à chaud (`invoke_configured_llm_for_assistant_turn`) : résolution du palier configuré dans `platform_setup_snapshot` / PostgreSQL 18 (`llm_tiers`), normalisation automatique des URL Ollama (`/api` ou `/v1` $\rightarrow$ `/api/chat` avec `"stream": False, "think": False` et repli `/v1/chat/completions`), support OpenAI/Mistral/Anthropic et court-circuit déterministe sous `TestClient` (`testserver`). |
| `apps/api/src/orcia_api/routers/assistant_workspace.py` | **Modifié** | Câblage de `invoke_configured_llm_for_assistant_turn` dans `execute_three_speed_turn_endpoint` (`POST /api/v1/assistant/three-speed/turn`) et `stream_three_speed_turn_endpoint` (`POST /api/v1/assistant/three-speed/stream`). |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` | **Modifié** | Soumission clavier par touche `Entrée` (`onKeyDown`), auto-remplissage d'une question de test opérationnelle si l'utilisateur clique sur `Envoyer à Mon Assistant` avec un champ vide, et affichage des états `isGenerating` (`⏳ ...`) et `errorMessage` (`data-testid="assistant-error-banner"`). |
| `apps/web/src/features/inbox/index.tsx` | **Modifié** | Retour visuel immédiat (`⏳ Mon Assistant prépare votre réponse...`), mise à jour complète des métriques et étapes (`cacheHit`, `cacheLookupMs`, `nodes1To4DeterministicMs`, `ttftMs`, `stepProgress`, `streamedText`) au retour de l'API, et affichage explicite des erreurs au lieu de `.catch(() => undefined)`. |
| `tests/unit/test_epic_10_story_10_2_three_speed_router.py` | **Modifié** | Ajout du test unitaire `test_story_10_2_live_llm_bridge_ollama_and_openai_normalization` couvrant la normalisation d'URL Ollama (`/api` $\rightarrow$ `/api/chat`), OpenAI (`/v1/chat/completions`) et l'injection `llm_response_override`. |
| `packages/ui/src/__tests__/assistant-workspace.test.tsx` | **Modifié** | Vérification de l'envoi automatique d'une question de test lorsque le bouton `Envoyer à Mon Assistant` est cliqué avec un champ vide, ainsi que de la soumission par touche `Entrée`. |

### 3.2 Métriques & Validation des 5 Couches de Tests (`AD-17`)

- **Couche 1 — Qualité Statique & Frontières Modulaires (`AD-19`)** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **0 erreur, 528 fichiers conformes**.
  - `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : **0 erreur sur 210 fichiers sources**.
  - `.venv/bin/lint-imports` : **5 contrats d'architecture hexagonale respectés, 0 brisé**.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` : **`ok: true` (`0 findings`)**.
- **Couche 2 — Tests Unitaires Python & Couverture** :
  - `.venv/bin/pytest tests/unit/test_epic_10_story_10_2_three_speed_router.py` : **4/4 tests passés**.
- **Couche 3 — Vérification TypeScript, Linter & Tests Composants/Web (`@orcia/ui` & `apps/web`)** :
  - `pnpm turbo run lint typecheck test` : **9/9 tâches réussies** (`@orcia/ui` `assistant-workspace.test.tsx` **4/4 passés**, `@orcia/web` **28/28 fichiers de tests passés**).
- **Couche 4 — Test d'Intégration Vertical en Conditions Réelles (`HTTP ➔ Pont LLM ➔ Ollama Local gemma4:12b`)** :
  - Appel `POST http://127.0.0.1:8000/api/v1/assistant/three-speed/turn` sur l'instance active :
    - Nœuds `1..4` déterministes exécutés en **`14.52 ms`**,
    - Nœud `5` (`NODE_5_SINGLE_STREAM_LLM`) exécuté par **`💬 Modèle IA gemma4:12b (Ollama Local) — réponse générée`**,
    - Réponse complète structurée en français retournée et affichée dans le panneau `assistant-stream-output`.
