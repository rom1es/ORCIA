# Spécification d'Implémentation — Story 8.4 : Hub des Connecteurs (`/settings/connectors`), Garde-fous d'Ingestion (`C0-C3`, `0 char`, PII) & Test de Réciprocité RAG (`AD-21`, `UX-DR19`)

- **Story Key** : `8-4-hub-connecteurs-et-gestion-des-secrets`
- **Epic** : `Epic 8` (`AD-21`, `UX-DR19`)

## 1. Critères d'Acceptation & Invariants
1. **Test de Connexion Fail-Fast (`< 5 s`)** :
   - `POST /api/v1/settings/connectors/{id}/test-connection` exécute un contrôle borné à `5 000 ms` et retourne `HEALTHY | DEGRADED | UNREACHABLE` avec latence et diagnostic.
2. **Garde-fous d'Ingestion Documentaire (`UX-DR19`)** :
   - Classification obligatoire `C0_C2_STANDARD` vs `C3_CONFIDENTIAL_RESTRICTED` : toute tentative d'ingérer un document `C3` dans un Workspace `STANDARD` est rejetée avec `HTTP 403 ERR_C3_WORKSPACE_REQUIRED`.
   - Linter OCR `0 char` : tout document vide ou scan non océrisé est rejeté en fail-fast avec `HTTP 422 ERR_EMPTY_OR_UNREADABLE_DOCUMENT`.
   - Détecteur PII (`EMAIL`, `IBAN`, `PHONE`, `NIR`) : met l'ingestion en pause `WAITING_FOR_PII_ARBITRATION` avec 3 choix explicites (`PSEUDONYMIZE`, `INDEX_AS_IS_AUDITED`, `CANCEL_IMPORT`).
3. **Test de Réciprocité RAG en 1 Clic (`Vérifier qu'il répond`)** :
   - `POST /api/v1/settings/connectors/documents/{id}/verify-reciprocity` vérifie que la réponse cite explicitement l'URI du document et son `chunk_id`.
