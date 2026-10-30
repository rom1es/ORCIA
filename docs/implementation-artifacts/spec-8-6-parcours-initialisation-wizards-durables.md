# Spécification d'Implémentation — Story 8.6 : Parcours d'Initialisation Guidés par Profil (Wizards Durables DBOS) & Workspace Démo Zero Empty-State (`AD-21`, `UX-DR20`)

- **Story Key** : `8-6-parcours-initialisation-wizards-durables`
- **Epic** : `Epic 8` (`AD-16`, `AD-21`, `UX-DR20`)

## 1. Critères d'Acceptation & Invariants
1. **3 Assistants Durables Guidés par Profil (`wizard_sessions`)** :
   - Parcours en 5 étapes pour `sdlc_tech_lead`, `ops_manager` et `secops_admin`.
   - Persistance durable dans `wizard_sessions` associée à un `dbos_workflow_id` permettant la reprise exacte à l'étape $k/5$ après fermeture d'onglet ou reconnexion.
2. **Zéro Secret en Clair dans `wizard_sessions`** :
   - Toute clé sensible (`password`, `secret`, `api_key`, `private_key`) passée dans `state_jsonb` est rejetée ; les secrets transitent exclusivement par `SecretInputSpec` et `SecretProviderPort` (`SecretRef`).
3. **Validation Fail-Fast par Étape & Réciprocité RAG Finale** :
   - Chaque étape valide son check fail-fast avant d'avancer, et l'étape 5 valide la réciprocité RAG.
4. **Workspace de Démonstration Pré-rempli (*Zero Empty-State Demo*)** :
   - Provisionnement idempotent en 1 clic (`POST /api/v1/wizards/demo-workspace`) avec `0` secret en clair (`plaintext_secrets_count == 0`).
