# Spécification d'Implémentation — Story 4.2 : Gates Agentiques avec Orthogonalité des Modèles, Pseudonymisation PII Réversible (`PiiReversibleScrubber`) & DAG de 5 Lentilles (dont `fact_verification`) + `DEC-SEC-01` / `SEC-03`

- **Clé de Story** : `4-2-gates-agentiques-avec-orthogonalité-des-modèles-pseudonymisa`
- **Actions Associées** : `DEC-SEC-01`, `SEC-03`
- **Statut** : `done`
- **Epic** : `Epic 4` — Pipeline Tri-Modal des Gates, Validation Cognitive par Découpage & Écosystème d'Exécution (Actions Jira, Sandbox & MCP IDE)
- **Références** : `FR-18`, `AD-6`, `AD-10`, `AD-12`, `AD-19`, `NFR-SEC-2`, `NFR-SEC-4`

## 1. Objectifs & Périmètre
1. **Orthogonalité des Modèles, Purge de la Chain-of-Thought & Routage Souverain (`FR-18`, `AD-10`)** :
   - Garantir par construction que `evaluator_model_family != executor_model_family` lors de toute évaluation par une Gate Agentique (ex. `anthropic` $\rightarrow$ `google` ou `openai`), en levant `ModelOrthogonalityViolationError` (`HTTP 422 ERR_MODEL_ORTHOGONALITY_VIOLATED`) en cas de violation.
   - Purger intégralement la chaîne de raisonnement interne (*Chain-of-Thought* : balises `<thinking>...</thinking>`, `[THOUGHT]`, champs `reasoning_content` / `chain_of_thought`, traces intermédiaires) avant envoi aux 4 lentilles indépendantes afin d'éliminer le biais d'auto-complaisance et d'ancrage cognitif.
   - Router automatiquement tout artefact classifié `SENSITIVE` ou `RESTRICTED` par l'Ontologie vers un modèle local souverain (`local/ollama-*` ou `local/vllm-*`).
2. **Pseudonymisation PII Réversible à la Volée (`PiiReversibleScrubber`, `NFR-SEC-2`)** :
   - Lorsque `anonymize_pii_reversible: true`, remplacer les données personnelles et secrets (adresses e-mail, numéros de téléphone, IBAN, NIR/SSN, jetons/clés API et entités nommées déclarées) par des jetons déterministes (`[PII_EMAIL_1]`, `[PII_PHONE_1]`, `[PII_IBAN_1]`, `[PII_SECRET_1]`, `[PII_ENTITY_1]`) stockés dans un coffre par `run_id` (Redis avec TTL ou mémoire isolée par `run_id`), puis ré-hydrater localement la réponse de l'évaluateur au retour.
3. **DAG d'Évaluation à 5 Lentilles (`AD-10`, `FR-18`)** :
   - Exécuter en parallèle et sans visibilité croisée les **4 Lentilles Indépendantes** :
     1. `transverse_alignment_step1` (*Lentille 1 — Alignement Transverse Étape 1*) : vérifie que l'artefact du Step $N$ ne contredit aucune exigence ou invariant du `PRD` (Step 1) ou de l'`Architecture` (Step 2).
     2. `fact_verification` (*Lentille 2 — Vérification Atomique de Faits*) : décompose l'artefact en assertions factuelles atomiques, confronte chacune à l'*Ontologie (N1..N4)* et aux *KBs* épinglées avec un score de confiance (`0..1`), et bloque toute assertion sous le seuil configuré (`fact_confidence_threshold`, défaut `0.80`) ou contredisant un axiome ontologique.
     3. `adversarial_edge_cases` (*Lentille 3 — Attaque Adversariale & Edge-Cases*).
     4. `domain_and_security_compliance` (*Lentille 4 — Conformité Domaine & Sécurité*).
   - Exécuter ensuite la *Lentille 5 — Synthèse & Structure* (`synthesis_and_structure`) qui consolide `lens_findings_jsonb`, intègre `step_memlog_jsonb`, calcule `agentic_score`, structure le **Briefing de Revue en 4 blocs** (`briefing_4blocks_jsonb`) et publie `GateEvaluated` (`gate_type="AGENTIC"`) dans `domain_events_outbox` (`AD-19`).
4. **Sécurité des Secrets : `SecretRef`, `SecretProviderPort` (Enveloppe DEK/KEK), `ConnectorInvoker`, Masquage Structlog & Test du Secret Témoin (`DEC-SEC-01`, `SEC-03`, `NFR-SEC-4`)** :
   - Introduire `SecretRef` (non sérialisable en clair dans `repr`, `str`, JSON, Pydantic et DBOS) et `SecretProviderPort` (avec chiffrement par enveloppe DEK/KEK par Workspace et journalisation immuable des rotations de clés dans `audit_ledger`).
   - Supprimer la valeur par défaut `sk-orcia-local` de `packages/orcia-core/src/orcia_core/bootstrap/_internal/litellm_adapter.py:L31` et faire transiter les appels fournisseur par `ConnectorInvoker` (relances passagères, `Retry-After`, budget `AD-12`).
   - Ajouter le processeur de masquage `structlog` et la liste blanche sur l'outbox et l'audit, validés par le **test du secret témoin (canari)** garantissant `0` occurrence du secret canari dans `dbos.*`, `audit_ledger`, `domain_events_outbox`, `step_executions` et les journaux `structlog`.
