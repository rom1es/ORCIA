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

| Ticket | Résultat | Statut |
| :--- | :--- | :--- |
| TEST-07 | ✅ 5 tests verticaux `AsyncClient(ASGITransport)` → `SELECT` PG18 verts : premier admin (POST → `SELECT users`, Argon2id, 409 au 2ᵉ appel) ; création d'agent ; `PUT/GET /api/v1/bootstrap/platform-setup-state` (`platform_settings`, `org_units`, `workspaces`, `llm_model_endpoints`) ; compétences & LLM progressif ; `pack-builder`, aide à chaud, préférences, gouvernance Mode A et dossiers Assistant (`catalog_items` + `domain_events_outbox`) | `done` |
| TEST-08 | ✅ 16 tests evals à `0 $` (`citations.jsonl` + `assistant_and_ontology.jsonl` : `0` citation fantôme conservée, refus constitutionnel `FR-4` sur ancre humaine, adaptation aux profils humains, orthogonalité `AD-10`, détection `ERR_ONTOLOGY_CONFLICT` sur axiome `L1`) | `done` |
| TEST-09 | ✅ 21 tests dans `tests/security/test_api_security_baseline.py` : SSRF (8 bloquées / 3 autorisées), persona inconnue → 404 problem+json, 422 + `trace_id`, rejet `403 ERR_OBSERVER_MODE_READ_ONLY` de l'observatrice `claire` sur les routes de mutation, anti-escalade RBAC (`403 ERR_GRANT_ESCALATION_FORBIDDEN`), masquage `CONFIDENTIAL_RESTRICTED`, non-fuite du secret canari (`DEC-SEC-01`) et sonde `BUG-E2E-04` | `done` |
| TEST-10 & CAP-ACT-5 | ✅ champ `tests:` obligatoire sur toute capacité `live` (`54/54` capacités `live` couvertes, `0` sans test), statistiques `capabilitiesCount` / `liveCapabilitiesCount` / `verifiedCapabilitiesCount` exposées dans `OrciaShowcaseManifestStats` (`@orcia/ui`) et `pnpm site:check` OK | `done` |

- Constat : `is_safe_llm_endpoint_url` bloque en dur `*.example.com` (règle non documentée) et n'interdit pas les plages privées RFC 1918 — conforme à la règle 4 d'`AGENTS.md` (métadonnées seulement), à qualifier.
- Vérifications : `pytest tests/security tests/evals` 22 passés ; `pytest` intégration HTTP→PG18 vert ; `ruff` + `mypy --strict` verts sur le registre ; `pnpm site:check` OK.
