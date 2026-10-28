# Spécification d'Implémentation — Story 3.5 : Challenge Amont Inter-Steps avec Simulation d'Impact (*What-If*) & Replay Ciblé à partir du Step $N$ (incluant Replay Intra-Sous-Workflow)

- **Clé de Story** : `3-5-challenge-amont-inter-steps-avec-simulation-d-impact-what-if`
- **Epic** : `Epic 3` — Orchestration Durable, *Blackboard* Immuable, Agent Assistant & Co-Exécution Humain-IA
- **Statut** : `done`
- **Références** : `FR-7`, `FR-16`, `FR-30`, `AD-2`, `AD-7`, `AD-18`, `AD-19`, `UX-DR7`

---

## 1. Objectif & Périmètre

1. **Challenge Amont Inter-Steps avec Aperçu d'Impact *What-If* (`FR-7`, `AD-7`, `AD-19`, `UX-DR7`)** :
   - Permettre à un contributeur aval (`Antoine` Step 2, `Yanis` Step 3) de contester une section ou règle d'un artefact amont (`target_upstream_step_key`, `challenged_section_key`).
   - Calculer via `ImpactSimulatorService` (traversée du graphe des dépendances `input_uris` `orcia://` des étapes / `blackboard_snapshots` et `ontology_relations`) l'aperçu `UpstreamChallengeImpactPreview` listant :
     - les *Steps* aval invalidés (`invalidated_downstream_step_keys`),
     - les sections d'artefacts impactées (`invalidated_artifact_sections`),
     - les axiomes et concepts d'ontologie impactés (`invalidated_ontology_axiom_keys`),
     - les *Steps* amont préservés (`preserved_upstream_step_keys`, `0` token reconsommé).
   - Traduire automatiquement l'impact technique dans le vocabulaire du profil humain de l'auteur amont (`PM_PO` / `BUSINESS_EXPERT` via `ProfileSemanticTranslator`) et publier `UpstreamChallengeSubmitted` dans `domain_events_outbox`.
2. **Replay Ciblé à partir du Step $N$ & Replay Intra-Sous-Workflow (`FR-16`, `FR-30`, `AD-2`, `AD-18`)** :
   - Endpoint `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/replay` (et alias `/api/v1/runs/{run_id}/steps/{step_key}/replay`).
   - Réutilise strictement le snapshot validé de l'étape $N-1$ et les versions `SHA-256` figées dans `run-lock.json` (`upstream_steps_reexecuted_count == 0`, `upstream_tokens_consumed == 0`).
   - En cas de Replay intra-sous-workflow (`sub_workflow_step_key`), ne rejoue que l'étape $k$ (et suivantes) du sous-workflow enfant sans recalculer les étapes $1..k-1$ de l'enfant ni les étapes $1..N-1$ du workflow parent.
   - Marque les anciens snapshots des étapes $\ge N$ comme `SUPERSEDED` sans jamais muter ni supprimer aucune ligne existante dans `blackboard_snapshots`, et crée une nouvelle branche `ACTIVE`.
3. **Composant Design System `@orcia/ui` `UpstreamChallengeRewindModal` (`UX-DR7`)** :
   - Modale accessible (`role="dialog"`, `aria-modal="true"`, fermeture `Escape`) affichant l'aperçu *What-If*, la traduction ontologique pour le profil amont, la soumission du challenge et le bouton de *Replay ciblé Step N*.
