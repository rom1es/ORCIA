# Spécification d'Implémentation — Story 4.3 : Gates Humaines Adaptatives, Briefing de Revue 4 Blocs (`review-briefing-grid`), Validation par Découpage (`chunk-validation-card`) & Garde-fou Anti-Rubber-Stamping (`< 15 s`)

- **Clé de Story** : `4-3-gates-humaines-adaptatives-briefing-de-revue-4-blocs-review`
- **Statut** : `done`
- **Epic** : `Epic 4` — Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution (Actions Jira, Sandbox & MCP IDE)
- **Références** : `FR-6`, `FR-19`, `AD-11`, `AD-19`, `UX-DR4`, `UX-DR5`, `UX-DR10`, `SM-C1`

## 1. Objectifs & Périmètre
1. **Migration Alembic `0018_story_4_3_chunk_approvals.py` (`AD-11`, `FR-6`)** :
   - Créer la table `chunk_approvals` (`UUIDv7` PK) stockant par section d'artefact (`chunk_key`, `section_title`, `word_count`, `human_authored_required`, `status` dans `PENDING | APPROVED | CO_EDITED | CHALLENGED`, `reviewer_user_id`, `human_anchor_signature_id`, `challenge_id`, `notes`, `reviewed_at`) avec contrainte `UNIQUE (gate_evaluation_id, chunk_key)`.
2. **Politiques de Gates Humaines Adaptatives (`FR-19`, `AD-11`)** :
   - Supporter les 3 politiques :
     - `mandatory_full` : requiert systématiquement la revue humaine complète par découpage.
     - `risk_or_exception_based` : passe automatiquement (`PASS`, `auto_passed=True`) **si et seulement si** `deterministic_status == "PASS"` **ET** `agentic_score >= 0.85` **ET** `ontology_conflicts == 0` **ET** `stale_warnings == 0` **ET** aucune section ne porte `human_authored_required: true`. Sinon, bascule en `PENDING_HUMAN_REVIEW`.
     - `sampling` : requiert l'intervention humaine dans `20 %` des cas (échantillonnage déterministe par hash SHA-256 de `run_id:step_execution_id` ou tirage forcé si les seuils de `risk_or_exception_based` ne sont pas respectés).
3. **Validation par Découpage (`chunk-validation-card`, `UX-DR5`, `FR-6`)** :
   - Découper tout artefact soumis à une Gate Humaine (ou $> 1\,500$ mots / $> 3$ sections) en sections atomiques (`chunks`).
   - Supporter 3 actions par section :
     - `APPROVE` (*Valider la section*),
     - `CO_EDIT` (*Co-éditer* avec enregistrement d'une signature dans `human_anchor_signatures`),
     - `CHALLENGE` (*Challenger / Rewind amont* suspendant la Gate et déclenchant un challenge amont).
   - Interdire toute approbation globale (`HTTP 422 ERR_UNAPPROVED_CHUNKS_REMAINING`) tant que toutes les sections obligatoires ne sont pas en statut `APPROVED` ou `CO_EDITED` (aucun bouton « Tout Approuver en 1 clic »).
4. **Briefing de Revue 4 Blocs (`review-briefing-grid`, `UX-DR4`) & Garde-fou Anti-Rubber-Stamping (`< 15 s`, `UX-DR10`, `AD-11`)** :
   - Afficher en tête la grille $2 \times 2$ (`1. Résumé Exécutif`, `2. Éléments Clés & Contrôle Transverse`, `3. Décisions Prises`, `4. Hypothèses Retenues` encadré en ambre `--color-arbitration-amber` tant qu'il n'est pas inspecté).
   - Si le valideur soumet une approbation finale sur un artefact $> 1\,000$ mots avec `review_duration_ms < 15000` :
     - Rejeter l'approbation directe avec `HTTP 422 ERR_RUBBER_STAMPING_GUARD_TRIGGERED` tant que `confirm_hypotheses_explicitly` n'est pas fourni,
     - Enregistrer `fast_approval_warning: true` dans `gate_evaluations` lorsque l'utilisateur confirme explicitement les hypothèses via la modale `AntiRubberStampingGuardModal` (`UX-DR10`).
