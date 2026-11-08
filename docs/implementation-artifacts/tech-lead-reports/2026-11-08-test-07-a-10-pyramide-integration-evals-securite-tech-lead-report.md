# 2026-11-08 — TEST-07 à TEST-10 : intégration HTTP→PG18, evals, sécurité, traçabilité test ↔ capacité

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-test-07-a-10-pyramide-tests` (`Ajustement Transverse` — tests, `Epic 13`, tickets `TEST-07`, `TEST-08`, `TEST-09`, `TEST-10`)
- **Capacité(s)** : `none (hygiène/NFR)` — classification `hygiène` ; référence des tests dans `capabilities.yaml` (champ `tests:`)
- **Branche dédiée** : `test/e2e-coverage-plan`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)
- Audit pyramide `AD-17` : 2 fichiers d'intégration sur 17 passaient par HTTP (TEST-07) ; aucun dossier `tests/evals` (TEST-08) ; couche Sécurité/Red-Team absente (TEST-09) ; aucune traçabilité test ↔ capacité (TEST-10).
- Impact GitNexus : nul (tests + `infra/scripts/capabilities_registry.py`). Aucun code applicatif modifié.

## 2. Plan d'Implémentation
- TEST-07 : `tests/integration/test_http_vertical_day0_and_agents_postgres18.py` (`AsyncClient` + `ASGITransport` → `SELECT` PG18).
- TEST-08 : `tests/evals/golden/citations.jsonl` + `test_citations_golden_dataset.py` (0 $, seuils bloquants).
- TEST-09 : `tests/security/test_api_security_baseline.py` (SSRF, identité inconnue, RFC 9457, sonde BUG-E2E-04).
- TEST-10 : champ `tests:` / `verification: runtime` validé par `capabilities_registry.py` (TDD, +3 tests) ; `site:check` affiche la couverture.

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

| Ticket | Résultat | Reste à faire |
| :--- | :--- | :--- |
| TEST-07 | ✅ 2 tests verticaux verts : premier admin (POST → `SELECT users`, Argon2id, 409 au 2ᵉ appel) ; création d'agent (POST → `SELECT catalog_items`) | **Partiel** : refonte HTTP des tests `story_9_*`, `10_*`, `11_*` non faite → ticket maintenu `in-progress` |
| TEST-08 | ✅ 8 tests (7 cas dorés + seuil « 0 citation fantôme conservée ») | Evals assistant (refus constitutionnel FR-4) et extraction ontologique non couverts |
| TEST-09 | ✅ 14 tests : SSRF (8 bloquées / 3 autorisées), persona inconnue → 404 problem+json, 422 + `trace_id` ; sonde du défaut BUG-E2E-04 (fallback `marc`) | Observateur `READ_ONLY_OBSERVER` sur toutes les mutations, IDOR inter-périmètres, `hidden_when_unauthorized`, secrets jamais en clair |
| TEST-10 | ✅ champ `tests:` validé (fichiers existants, `runtime` ⇒ test), 20/54 capacités `live` référencent un test | Référencer aussi les tests unitaires existants ; seuil bloquant progressif |

- Constat : `is_safe_llm_endpoint_url` bloque en dur `*.example.com` (règle non documentée) et n'interdit pas les plages privées RFC 1918 — conforme à la règle 4 d'`AGENTS.md` (métadonnées seulement), à qualifier.
- Vérifications : `pytest tests/security tests/evals` 22 passés ; `pytest` intégration HTTP→PG18 vert ; `ruff` + `mypy --strict` verts sur le registre ; `pnpm site:check` OK.
