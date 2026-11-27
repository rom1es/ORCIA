## Epic 14: ORCIA Process Studio v2 — Cartographie VSM (`ValueStreamMapSpec`), Studio Agentique Déterministe à 5 Blocs (`Control-M`), Gates Multi-Niveaux Auto-Heal (3x) & Portail HITL 4 Actions (`specs/epic-09-process-studio/`)

Déployer l'**ORCIA Process Studio v2** en séparant la **Cartographie de Chaîne de Valeur (`ValueStreamMapSpec`)** (vue macro de gouvernance en 4 phases, 11 étapes, 5 points de passage humains et 8 boucles de retour extraite de `Workflow agentique 2.html`) et les **Workflows DBOS Unitaires et Bornés (`WorkflowDefinitionV2`)** (`wf-01-qualification-prd`, `wf-03-etude-architecture`, `wf-06-decoupe-us`, `wf-08-dev-external-gate`), avec zéro « Agent Orchestrateur » lisant le chat (`DeterministicSubStepSpec` + `DBOS.recv`), support des modes `NATIVE_ORCIA` et `EXTERNAL_DELEGATED_GATE`, stockage S3 `ClaimCheckPointer` (`> 4 Ko`), idempotence cyclique `:iter-{iteration}` et Studio 5 blocs façon Control-M assisté par Co-pilote.

### Story 14.1: Modèle Agnostique `orcia-core` (VSM + Workflows Bornés + Claim-Check S3) & Seed Déclaratif `packs/sdlc/`
- **CA-14.1.1 (Zéro fuite SDLC dans Core)** : Aucun mot-clé métier SDLC (`jira`, `confluence`, `git`, `prd`, `wsjf`, `rovo`, `copilot`, `safe`) dans `packages/orcia-core` (`tests/unit/core/test_core_domain_isolation.py`).
- **CA-14.1.2 (Immuabilité & Fork Draft)** : Toute modification d'un workflow `PUBLISHED` crée une branche `vX.Y.Z-draft` sans impacter les exécutions DBOS actives.
- **CA-14.1.3 (Claim-Check obligatoire)** : Tout livrable d'étape ou diff `> 4 Ko` est persisté dans SeaweedFS avec empreinte `SHA-256` (`ClaimCheckPointer`).

### Story 14.2: Vue Cartographie de Chaîne de Valeur (Macro-VSM) & Comparaison 3 États (`/processes/vsm/$vsmId`)
- **CA-14.2.1 (Commutateur 3 États en Consultation)** : Bascule fluide `Aujourd'hui | Avec les agents | Comparer`.
- **CA-14.2.2 (Boucles de retour SVG sans collision)** : Tracé dynamique des boucles principales et secondaires (`ReturnLoopsSvgOverlay.tsx`), fiche modale à 6 onglets (`StepDetailSheet.tsx`), opportunités `P1..P3` et mode `Présenter`.
- **CA-14.2.3 (Pont VSM ➔ Workflow Exécutable)** : Ouverture directe du Workflow dans le Studio 5 Blocs ou lancement/suivi d'exécution unitaire.

### Story 14.3: Studio de Conception de Workflow (5 Blocs Control-M + Co-pilote Gauche + Sous-Étapes DBOS `/processes/studio/$workflowId`)
- **CA-14.3.1 (Co-pilote & Suggestions Catalogue)** : `StudioCopilotSidebar.tsx` suggérant les `Toolboxes MCP`, `Skills` et `Gates` du Pack actif avec attachement `[+]`.
- **CA-14.3.2 (Séquence de Sous-Étapes Déterministes DBOS)** : Enchaînement de $N$ sous-étapes séparées par des jalons DBOS (`requires_human_checkpoint`) et bypass unitaire (`enabled: false` $\rightarrow$ `SKIPPED`).
- **CA-14.3.3 (Modes `NATIVE_ORCIA` vs `EXTERNAL_DELEGATED_GATE`)** : Configuration du mode natif ORCIA ou sas externe délégué (IDE Copilot / Rovo / Webhook).

### Story 14.4: Pipeline Ordonné de Gates (4 Runners Déterministes Génériques Auto-Heal 3x ➔ Probabilistes) & Test Mode What-If
- **CA-14.4.1 (Ordre Inviolable & Auto-Heal)** : Exécution des 4 runners génériques (`markdown_contract_runner`, `json_schema_runner`, `cli_sandbox_runner`, `catalog_invariant_runner`) avec auto-remédiation bornée à `max_self_heal_retries = 3`.
- **CA-14.4.2 (Gates Probabilistes Conditionnées)** : Exécution des Hunters contradictoires uniquement si 100 % des Gates déterministes sont `NOMINAL`.
- **CA-14.4.3 (Exécution Sandbox What-If)** : Simulation isolée sans `execute_write` externe retournant `ImpactAssessmentResult`.

### Story 14.5: Les 5 Dispositifs d'Interaction Humaine (HITL) & Boucles de Reprise Itératives (`InteractiveRunDrawer.tsx`)
- **CA-14.5.1 (Write-Preview Gate Obligatoire)** : Interception de toute écriture externe via `preview_write()` (`WritePreviewCard`) et exigence d'un `SignedApprovalToken` du *Permission Broker* avant `execute_write()`.
- **CA-14.5.2 (Arbitrage Souverain à 4 Actions sur Diff S3)** : `APPROVE` (Accepter & Signer), `AMEND_DIFF` (Amender directement le Diff S3), `REJECT_AND_LOOP` (Refuser & Choisir la boucle de retour), `SUSPEND_SLA` (Suspendre le SLA).
- **CA-14.5.3 (Incrémentation d'itération sur Boucle de Retour)** : Clé d'idempotence `f"{run_id}:{sub_step.id}:iter-{iteration}"` et réinjection des remarques en mode `corrections`.
