# Spécification d'Implémentation — Story 3.4 : Ancrages Humains Obligatoires (`human-led-anchor-card`), Arbitrage Humain Systématique (`arbitration-tiebreak-card`) & Politique de Départage (`tie_break_policy`)

- **Clé de Story** : `3-4-ancrages-humains-obligatoires-human-led-anchor-card-arbitrag`
- **Epic** : `Epic 3` — Orchestration Durable, *Blackboard* Immuable, Agent Assistant & Co-Exécution Humain-IA
- **Statut** : `done`
- **Références** : `FR-4`, `FR-5`, `FR-29`, `AD-3`, `AD-15`, `AD-18`, `AD-19`, `UX-DR3`, `UX-DR6`

---

## 1. Objectif & Périmètre

Verrouiller structurellement et visuellement :
1. **Ancrages Humains Obligatoires (`human-led-anchor-card`, `FR-4`, `UX-DR3`)** :
   - Toute section ou étape marquée `human_authored_required: true` bloque la progression (`ERR_HUMAN_ANCHOR_REQUIRED`, HTTP `422`) tant qu'un opérateur humain authentifié (`author_type="HUMAN"`) n'a pas rédigé et signé au moins `30` caractères (`content_sha256`).
   - Toute tentative d'écriture par une identité agentique (`author_type="AGENT"`) est rejetée avec `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`.
   - Le composant `@orcia/ui` `HumanLedAnchorCard` affiche la bordure Violette exclusive `--color-human-led-violet` (`#6D28D9`), aucun bouton de pré-remplissage IA (`data-ai-generation-forbidden="true"`), et verrouille le bouton d'enregistrement sous `30` caractères.
   - Toute demande « Remplis-le pour moi » adressée à l'Agent Assistant déclenche le refus constitutionnel Layer 1 (`HUMAN_ANCHOR_WRITE_REFUSAL`) accompagné de 3 questions socratiques adaptées au Profil Humain.
2. **Arbitrage Humain Systématique & Politique de Départage (`arbitration-tiebreak-card`, `FR-5`, `FR-29`, `AD-3`, `AD-18`, `UX-DR6`)** :
   - Outil `request_human_arbitration(options_matrix)` évaluant `tie_break_policy` :
     - `PAUSE_AND_ESCALATE` : suspend l'étape (`WAITING_HUMAN_ARBITRATION`, `DBOS.recv`) et publie `HumanArbitrationRequested` dans `domain_events_outbox`.
     - `ONTOLOGY_AXIOM_FIRST` : départage automatiquement si un axiome ontologique `1_ENTERPRISE` ou `2_BU` élimine toutes les options sauf une (`RESOLVED_BY_AXIOM`), sinon bascule en `PAUSE_AND_ESCALATE`.
     - `DEFER_AND_CONTINUE_WITH_ASSUMPTION` : uniquement autorisé sur les sous-workflows non-critiques (`is_critical_path=False`, sinon `HTTP 422 ERR_INVALID_TIE_BREAK_POLICY`), sélectionne l'option recommandée, consigne `[ASSUMPTION]` dans `step_memlog_jsonb` et poursuit l'exécution.
   - Composant `@orcia/ui` `ArbitrationTieBreakCard` (`--color-arbitration-amber` `#D97706`) permettant la sélection 1-clic (`Option A` / `Option B`) ou la saisie d'une `Option C` personnalisée et débloquant immédiatement le moteur (`DBOS.send` / `resume_human_task`).

---

## 2. Architecture & Composants Livrés

- **Migration Alembic `0015_story_3_4`** (`infra/migrations/versions/0015_story_3_4_human_anchors_and_arbitration.py`) : tables `human_anchor_signatures` (`CHECK (char_length(btrim(content_text)) >= 30)`) et `human_arbitration_requests`.
- **Domaine `packages/orcia-core/src/orcia_core/orchestration/human_anchors_and_arbitration.py`** : `HumanAnchorAndArbitrationService`, `validate_human_anchor_submission`, `HumanAnchorSignatureEntity`, `HumanArbitrationRequestEntity`, `ArbitrationOptionItem`.
- **API REST `apps/api/src/orcia_api/routers/blackboard_and_engine.py`** :
  - `POST /api/v1/orchestration/runs/anchors/sign`
  - `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/arbitration`
  - `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/arbitration/resolve`
- **Design System `@orcia/ui` & Cockpit `apps/web`** : `HumanLedAnchorCard.tsx`, `ArbitrationTieBreakCard.tsx`, dictionnaires `fr.ts`/`en.ts`, intégration dans `apps/web/src/features/cockpit/index.tsx`.
