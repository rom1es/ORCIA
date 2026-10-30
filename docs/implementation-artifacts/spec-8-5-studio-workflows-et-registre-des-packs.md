# Spécification d'Implémentation — Story 8.5 : Studio Visuel de Workflows (`Contrat`, `Pré-prompt`, `COUCHES · N`) & Registre des Packs Métiers (`AD-21`, `UX-DR18`)

- **Story Key** : `8-5-studio-workflows-et-registre-des-packs`
- **Epic** : `Epic 8` (`AD-20`, `AD-21`, `UX-DR18`)

## 1. Critères d'Acceptation & Invariants
1. **5 Onglets de Cycle de Vie & Fork Immuable SemVer** :
   - Onglets `PUBLISHED`, `DRAFT`, `TRASH`, `ACTIVE_RUNS`, `PAUSED_ARBITRATION` avec compteurs temps réel.
   - Toute révision `PUBLISHED` (`v1.0.0`) est immuable ; cliquer sur `Modifier` crée un fork `v1.1.0-draft` dans `DRAFT`.
2. **Barre Supérieure de Gouvernance (`<WorkflowTopGovernanceBar />`)** :
   - `Pré-prompt IA` épinglé par empreinte `sha256`.
   - `Contrat du workflow` : paramètres typés `p_1..p_n` liés à l'Ontologie et sections Markdown obligatoires vérifiées par Gate déterministe de structure.
   - `▷ Tester` : exécution *What-If* isolée (`external_writes_count == 0`).
3. **Moindre Privilège par Étape & Inspecteur `<LayersInspectorPopover />` (`COUCHES · N`)** :
   - Liaison connecteur par étape en mode `READ_ONLY` vs `READ_WRITE_STAGED`.
   - Les nœuds composites `SUB_WORKFLOW` exposent leurs sous-couches en 3 zones (`Entrées`, `Capacités`, `Livrables`) avec bascule `enabled: false -> SKIPPED` sans rompre le DAG parent.
4. **Registre des Packs Métiers (`/settings/packs`)** :
   - Statuts `ACTIVE`, `DISABLED`, `DRAINING`, `ORPHANED` et garde `HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`.
