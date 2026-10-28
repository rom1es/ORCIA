# Spécification d'Implémentation — Story 3.2e : Séparation Core et Pack SDLC (`orcia-pack-sdlc`), Interface de Connecteur Universelle (`ConnectorPort`) & Hygiène des Seeds

- **Story Key** : `3-2e-séparation-core-et-pack-sdlc-orcia-pack-sdlc-interface-de-co`
- **Epic** : Epic 3 — Moteur d'Exécution Durable, Gouvernance Adaptive & Résilience
- **Décisions liées** : `AD-20`, `AD-19`, `AD-5`, `AD-6`, `AD-8`, `AD-16`, `DEC-SEED-01`, `DEC-P0-01`, `DEC-P0-02`
- **Statut** : `done`

---

## 1. Objectif &Périmètre

1. **Étape 0 (`AC-E0` — `DEC-SEED-01`)** : Déplacer l'intégralité des manifestes YAML de démo (`DEFAULT_*_WORKFLOW_YAML`), du gabarit ADR (`DEFAULT_ADR_TEMPLATE_SEED`) et du peuplement RAG (`populate_rag_test_dataset`) hors de `orcia_core.orchestration.seeds` et `orcia_core.rag` vers `orcia_core.bootstrap.{orchestration_seeds,rag_seeds}`.
2. **`AC-E1` (5e package `uv` `packages/orcia-pack-sdlc` + 4e contrat `import-linter`)** : Créer `packages/orcia-pack-sdlc` enregistrant ses extensions via `importlib.metadata.entry_points` (`orcia.connectors`, `orcia.workflow_policies`, `orcia.memlog_markers`, `orcia.catalog_formats`, `orcia.rag_indexers`) et verrouiller par un 4e contrat `import-linter` (`type = forbidden`) l'absence totale d'import de `orcia_pack_sdlc` depuis `orcia_kernel` et `orcia_core`.
3. **`AC-E2` (Zéro vocabulaire SDLC dans `orcia-kernel` & `orcia-core/orchestration`)** : Remplacer `MemlogMarkerType = Literal[...]` par un registre dynamique `str` à espace de noms (`sdlc.bug_code_suspected`, `sdlc.doc_obsolete_suspected` + alias de compatibilité `BUG_CODE_SUSPECTED`, `DOC_OBSOLETE_SUSPECTED`), ajouter `tags: tuple[str, ...]` et `policies: tuple[str, ...]` sur `WorkflowStepSpec`, et lever `UnknownWorkflowPolicyError` (`ERR_UNKNOWN_WORKFLOW_POLICY`, RFC 9457) sur toute politique non enregistrée.
4. **`AC-E3` & `AC-E4` (`ConnectorPort`, suppression des `Literal` de schémas & connecteur tiers `sap://` `< 150` lignes)** : Définir `ConnectorPort` (`capabilities`, `fetch`, `invoke` idempotent, `health`, `map_error`) dans `orcia_kernel.ports`, supprimer `ALLOWED_SCHEMES` et les 4 `Literal` codés en dur (`FederatedScheme`, `DatasourceScheme`, `BrokerConnectorScheme`, `KbDocumentEntity.source_scheme`), livrer `tests/fixtures/plugins/orcia_connector_sap_fake` (`130` lignes) et la suite `tests/conformance/connector_port/`.
5. **`AC-E5` (Migrations Alembic `0013` Expand & `0014` Contract)** : Créer la table `connector_schemes` peuplée par upsert idempotent, attacher 4 clés étrangères `NOT VALID` puis `VALIDATE CONSTRAINT` (`0013`), et supprimer les 4 contraintes `CHECK` figées (`0014`), avec `downgrade()` testé sur conteneur `PostgreSQL 18` réel contenant des lignes existantes.
