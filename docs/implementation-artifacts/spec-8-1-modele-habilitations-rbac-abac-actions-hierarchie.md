# Spécification d'Implémentation — Story 8.1 : Modèle d'Habilitations Hiérarchique à 6 Verbes (`RBAC/ABAC`), Délégation Bornée & Anti-Lockout (`AD-21`)

- **Story Key** : `8-1-modele-habilitations-rbac-abac-actions-hierarchie`
- **Epic** : `Epic 8` (`AD-21`)
- **Action Items couverts** : `ACTION_ITEM-8.1` (`DENY` prioritaire & `inheritance_block`), `ACTION_ITEM-8.2` (Conditions ABAC contextuelles sur `execute`), `ACTION_ITEM-8.3` (`hidden_when_unauthorized` `HTTP 404` vs découverte passive `locked: true`)

## 1. Critères d'Acceptation & Invariants
1. **6 Verbes Atomiques (`create, read, update, delete, execute, grant`)** :
   - Évaluation hiérarchique le long de `org -> bu -> team -> workspace -> pack -> resource`.
   - `DENY` explicite prioritaire sur tout `ALLOW` hérité ou direct (`ACTION_ITEM-8.1`).
   - `inheritance_block: true` coupe l'héritage ascendant sur les périmètres confidentiels `C3` (`ACTION_ITEM-8.1`).
2. **Conditions ABAC sur `execute` (`ACTION_ITEM-8.2`)** :
   - Évaluation de `allowed_environments` / `env` et `max_tokens_per_run`.
3. **Isolation `execute` sans `read` & Opacité (`ACTION_ITEM-8.3`)** :
   - Un sujet disposant de `execute` sans `read` peut exécuter la ressource mais toute lecture de sa configuration secrète lève `HTTP 403 ERR_SECRET_CONFIG_READ_DENIED`.
   - `hidden_when_unauthorized: true` lève `HTTP 404 ERR_RESOURCE_NOT_FOUND` (aucune fuite d'existence).
   - Sinon, la découverte passive retourne `locked: true`, `can_request_access: true` et permet d'émettre `AccessRequested` dans `domain_events_outbox`.
4. **Confinement de Délégation (`grant`) & Anti-Lockout (`AD-21`)** :
   - $\text{Droits délégués} \subseteq \text{Droits détenus}$ : toute tentative d'escalade lève `HTTP 403 ERR_GRANT_ESCALATION_FORBIDDEN`.
   - Interdiction de supprimer ou révoquer le dernier `PLATFORM_ADMIN` actif ou de désactiver la dernière méthode d'authentification (`HTTP 422 ERR_ADMIN_LOCKOUT_PREVENTED`).
   - Révocation en frontière de `@DBOS.step` (`enforce_step_boundary_execution_guard`).
