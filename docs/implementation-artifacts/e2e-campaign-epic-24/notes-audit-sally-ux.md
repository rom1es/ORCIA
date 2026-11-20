# 🎨 Contre-Audit Visuel & UX/UI Exhaustif `24.7-sally` — Campagne E2E Figée Epic 24 (`desktop-cockpit`, `1440×900`)

- **Auditrice** : 🎨 **Sally** — UX Designer & Spécialiste UI Direction C (`bmad-architect-worker`)
- **Date** : `2026-11-20`
- **Branche / État inspecté** : `feat/epic-24-remediation-pg18-ux-and-cockpit` (base `303ba27` + réconciliations `Story 24.7`)
- **Périmètre inspecté** : **100 % des `61` captures PNG** existantes sous `./screenshots/` (`55` entrées de [`manifest.jsonl`](./manifest.jsonl) couvrant `24` specs = `52` `passed`, `0` `failed`, `0` `timedOut`, `3` `skipped` `mobile-only`, plus **`6` captures jalons `milestone-*.png`** dont les `3` nouveaux jalons Epic 24) en résolution Desktop `1440×900` strictement verrouillée (`0` débordement vertical hors coquille).
- **Référentiels appliqués** :
  - [`DESIGN.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md) & [`EXPERIENCE.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md)
  - [`sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md`](../../planning-artifacts/sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md) (`UX23-01..17`, `USER24-BUG-1..6`, `REM24-01..12`)
  - [`bilan-execution-tests-e2e-epic-24.md`](./bilan-execution-tests-e2e-epic-24.md) & [`playwright-results.json`](./playwright-results.json)
  - Comparatif : [`notes-audit-sally-ux.md` (Epic 23)](../e2e-campaign-epic-23/notes-audit-sally-ux.md)

---

## 1. Synthèse exécutive & décompte par sévérité (`P0` / `P1` / `P2` / `P3`)

### 1.1 Couverture d'inspection visuelle (`61 / 61` PNG inspectés via `read_file`)

| Indicateur | Volume campagne | Inspectés par Sally (`read_file`) | Taux d'inspection |
| --- | ---: | ---: | ---: |
| **Scénarios `passed`** (`24/24` specs 100 % vertes Desktop) | `52` | `52` | **100 %** |
| **Scénarios `failed` + `timedOut`** | `0` | `0` | **100 %** (`0` échec) |
| **Scénarios `skipped` (`mobile-only`)** (`#14`, `#25`, `#27`) | `3` | `3` | **100 %** |
| **Captures jalons (`milestone-*.png`)** (`3` historiques + `3` Epic 24) | `6` | `6` | **100 %** |
| **Total PNG sur disque (`< 450 KB`, max `274 576` B)** | **`61`** | **`61`** | **`100 %`** |

> **Note de périmètre `CAP-042` / `ACTION_ITEM-23.6` :** Les `3` scénarios `mobile-only` (`#14` `05`, `#25` `12-finops`, `#27` `13-epic-7`) sont volontairement `skipped` sous `--project=desktop-cockpit` et demeurent tracés séparément sous `ACTION_ITEM-23.6` (`P2`) dans [`sprint-status.yaml`](../../sprint-status.yaml).

### 1.2 Verdict Direction C & Comparaison Epic 23 → Epic 24

La transformation visuelle et ergonomique entre la campagne Epic 23 (`44/52`, `1 P0`, `9 P1`, `5 P2`, `2 P3`) et la campagne Epic 24 (`52/52` PASS Desktop, `0` échec) est complète sur l'ensemble des critères bloquants et majeurs :

- **Tous les blocages critiques et majeurs (`1 P0` + `9 P1` d'`UX23-01..10`) sont résolus et vérifiés sur les captures PNG.**
- **Les `6` remontées utilisateur `USER24-BUG-1..6` sont toutes vérifiées corrigées visuellement** (zéro bande `#EAF2FB` sous le shell sur `61/61` captures, clic `1. Compte Admin` $\rightarrow$ `/profile` sans `Not Found`, rendu HTML Markdown sur `/help` & Zone 4, onglets horizontaux `Personnalisation`, menu Compte sans doublon `Paramètres`, bannière PAT unique + libellés propres, et disparition totale de `default-ws` à `0` espace).
- **L'inspection sans complaisance des `61` captures relève uniquement `3 P2` (modérés) et `4 P3` (mineurs)** — aucun `P0`, aucun `P1` :

| Sévérité | Epic 23 (`dd2d382`) | Epic 24 (`Story 24.7`) | Écart | Identifiants Epic 24 |
| --- | ---: | ---: | ---: | --- |
| **`P0` — Bloquant** | `1` | **`0`** | **`-1`** | — |
| **`P1` — Majeur** | `9` | **`0`** | **`-9`** | — |
| **`P2` — Modéré** | `5` | **`3`** | **`-2`** | `UX24-01`, `UX24-02`, `UX24-03` |
| **`P3` — Mineur** | `2` | **`4`** | `+2` | `UX24-04`, `UX24-05`, `UX24-06`, `UX24-07` |
| **Total écarts constatés** | **`17`** | **`7`** | **`-10`** | **`0 P0 / 0 P1` — Seuil `Case A` satisfait** |

---

## 2. Vérification de Résolution `UX23-01..17` & `USER24-BUG-1..6`

### 2.1 Vérification des `6` remontées utilisateur (`USER24-BUG-1..6`)

| ID | Description initiale | Preuve visuelle Epic 24 (`read_file`) | Verdict |
| --- | --- | --- | :---: |
| **`USER24-BUG-1`** | Scroll vertical externe révélant une bande vide `#EAF2FB` sous le shell | `61/61` PNG strictement cadrés à `1440×900` (`tokens-shell.css:22-32` `100dvh; overflow: hidden`), `0` bande `#EAF2FB` sous Zone 1/3/4 (cf. `01 #5`, `10 #19/#20`, `11 #22`, `15 #31`, `16 #37`, `18 #43`, `shell #52/#54`). | ✅ **Résolu** |
| **`USER24-BUG-2`** | Clic sur `1. Compte Admin` $\rightarrow$ `/welcome-setup` (`Not Found`) | `01 #5` (`url: http://127.0.0.1:3101/profile`) affiche directement la page `Profil` d'`Alice Admin E2E` (`@alice.admin`, `Administrateur de la plateforme`, KPIs, raccourcis), `0` `Not Found`. | ✅ **Résolu** |
| **`USER24-BUG-3`** | Markdown brut (`**...**`, `` `ⓘ` ``) dans `/help` & Zone 4 | `08 #17` / `18 #45` Zone 4 affiche `via « @ »` sans backtick brut ; `16 #37` `PermissionBrokerCard` rend gras HTML + badges `<code>` + URI décodée ; `ContextualHelpSharedBlocks.tsx` utilise `renderInlineMarkdownNodes` (`21 #51` vérifie `0` `**`/backtick brut et `> 0` `strong, code`). | ✅ **Résolu** |
| **`USER24-BUG-4A`** | Liste verticale + vide blanc ~220 px dans `Paramètres du compte` | `14 #30` et `16 #36` montrent `UserSettingsModalDialog` en onglets horizontaux `.orcia-ds-tabs` (`Général | Personnalisation | Compte & Sécurité | Connexions aux outils | Clés IDE & MCP`) sans aucun vide latéral ni chevauchement. | ✅ **Résolu** |
| **`USER24-BUG-4B`** | Doublon `Paramètres` + `Personnalisation` dans le menu Compte bas-gauche | `SidebarAccountPopover.tsx` supprime `account-popover-settings-btn` et ne conserve que `Personnalisation`, `Profil`, `Aide` et `Se déconnecter` (vérifié dans `14 #30` et tests `authAndOrgHelpers.ts:115`). | ✅ **Résolu** |
| **`USER24-BUG-5`** | Libellé `IDE MCP (SPACE · default) ... · 60 RPM` confus + bannière secret réaffichée | `14 #30` (`VSCode E2E`) prouve après réouverture de la modale l'absence totale de la bannière `lastIssuedPlaintext`, l'affichage épuré `Identifiant : pat_mcp_aynsVt...`, JSON propre et bouton rouge `Révoquer` sans `IDE MCP (SPACE · default)` ni `60 RPM`. | ✅ **Résolu** |
| **`USER24-BUG-6`** | Panneau fantôme `default-ws` à `0` espace & onglet 5 bloqué sur `2. DOCUMENTS & SOURCES` | `11 #21` (`/spaces` Jour 0) montre uniquement l'état vide *"Aucun Espace de Travail ne correspond à ce filtre..."* sans panneau `default-ws` ; `07 #16` et `17 #38` n'affichent le panneau de détail que lorsqu'un espace réel est sélectionné ; `WorkspaceFiveTabsPanels.tsx` commute les 5 onglets. | ✅ **Résolu** |

### 2.2 Vérification des `17` constats Epic 23 (`UX23-01..UX23-17`)

| ID (`Epic 23`) | Sév. initiale | Constat initial | Preuve visuelle Epic 24 (`read_file`) | Verdict |
| --- | :---: | --- | --- | :---: |
| **`UX23-01`** | **`P0`** | Disparition carte/badge Jira `EXECUTED` après F5 sur `/gates` | `06 #15`, `milestone-gates-hitl-drawer.png` et `19 #47` affichent `Point de contrôle : Validé   Jira PAYBUILD-101 : Exécutée` après `reloadColdFromPg`. | ✅ **Résolu** |
| **`UX23-02`** | **`P1`** | Vide blanc ~220 px dans `UserSettingsModalDialog` | `14 #30`, `16 #36` : barre d'onglets horizontale complète, contenu dégagé, `Révoquer` bien espacé. | ✅ **Résolu** |
| **`UX23-03`** | **`P1`** | `AgentDetailAndSandboxModal` hors `OrciaDialog`, `Bloc E` coupé, pas de pied sticky | `08 #17` : modale opaque `#FFFFFF` sur `OrciaDialog` (`max-h-[82vh]`), `Bloc E` entièrement lisible, footer sticky `Sauvegarde automatique active` + `Enregistrer` visible. *(Note mineure slug accentué déplacée en `UX24-04` `P3`).* | ✅ **Résolu** |
| **`UX23-04`** | **`P1`** | Contraste illisible de l'onglet actif `/finops` à vide | `12 #24` : `Par Modèle et Niveau d'effort` en `#FFFFFF` sur `#2563EB` (`tokens-dark.css:13` `#93C5FD` sur `#1E293B` `8,45:1`). | ✅ **Résolu** |
| **`UX23-05`** | **`P1`** | Émoji rouge `❓` + doublon anglais `Federated Catalog` dans `⌘K` | `10 #20` : bouton bleu `#2563EB` avec icône vectorielle blanche `OrciaIcon` + `Ouvrir l'aide`, `0` article anglais dans les résultats FR. | ✅ **Résolu** |
| **`UX23-06`** | **`P1`** | Panneau fantôme `default-ws` sur `/spaces` à `0` espace | `11 #21` : panneau complètement absent à `0` espace. | ✅ **Résolu** |
| **`UX23-07`** | **`P1`** | `Claire Invitée` / `Marc Lead BU` affichés comme `Administrateur de plateforme initialisé` | `14 #29` (`Claire Invitée`) affiche `Administrateur de plateforme initialisé ✓ Alice Admin E2E`, masque `Étape 2` et ne montre que les jalons `4` et `6`. | ✅ **Résolu** |
| **`UX23-08`** | **`P1`** | Enums bruts (`PENDING`, `RUNNING`, `PAUSE_AND_ESCALATE`, `OPT_A_*`, `(AD-24.7)`, `COMPLETED`, `HTTP 403`, `0` nu, `depth=0/1`, `0.5 ms`, Markdown brut Broker) | `03` (`En cours`, `En attente`, `Validé`, `Pause et escalade humaine`, `Retenir cette option`, `Règle fondamentale de structure immuable`), `06 #15` (`Conception des processus...` sans `< 15 s` / `PostgreSQL 18`), `15 #34` (`Prise en charge directe — Relecture en boîte de réception`, `Synchronisation : temps réel`), `16 #35` (`Terminée (100%)` sans `AD-24.7`), `16 #37` (Markdown rendu + URI décodée), `18 #41` (`Aucun élément disponible...`, `Niveau principal :` / `Niveau 1 :`). *(Résidus What-If résiduels isolés en `UX24-03` `P2`).* | ✅ **Résolu** |
| **`UX23-09`** | **`P1`** | `/inbox` mappé sur Assistant, `/showcase` sur Cockpit, `/organization` sous Configuration masquée, `[Espace]` absent | `04 #12` & `15 #34` (`/inbox` : fil `ORCIA > Boîte de Réception` + Zone 4 `/inbox`), `15 #33` (`/organization` : fil `ORCIA > Mon Organisation` + Zone 4 dédiée), `03` / `17 #38` / `20` (segment `[Espace]` dans le fil), `21 #51` (`eight-menu-item-help` vérifié actif à L219 — flash post-reload isolé en `UX24-02` `P2`). | ✅ **Résolu** |
| **`UX23-10`** | **`P1`** | `4 Compéte` coupé, `1 Chaînes` / `1 Sources rattachées`, noms connecteurs/agents bruts | `18 #43` (`4 Compétences` entier, `1 Agent`, `1 Compétence`, `1 Validation`, `0 Chaîne`, `1 Processus`, libellés lisibles `Atlassian Jira`, `Redacteur Documentation Orcia`) & `17 #38` (`1 Source rattachée`). | ✅ **Résolu** |
| **`UX23-11`** | **`P2`** | Troncatures `1440×900` (`Ex : Ajouter un contrôle de p`, `Rechercher un espace ou une équ`, `Plateforme entière (toutes les directi`) | `09 #18` & `20 #48` (`Ex : Ajouter un contrôle...` entier), `07 #16` & `17 #38` (`Rechercher un espace...` entier), `15 #32` (`Plateforme entière (Global)` entier). | ✅ **Résolu** |
| **`UX23-12`** | **`P2`** | Backtick `` `@` `` sur `/agents` et `promotions L4 → L1` sur `/ontology` | `08 #17` & `18 #45` (`via « @ »`), `17 #39` & `milestone-ontology-tripartite-waivers.png` (`de l'Espace à l'Entreprise`). | ✅ **Résolu** |
| **`UX23-13`** | **`P2`** | Bande vide `#EAF2FB` sous `900 px` sur captures `fullPage` | `61/61` PNG à `1440×900` sans aucune bande vide `#EAF2FB`. | ✅ **Résolu** |
| **`UX23-14`** | **`P2`** | KPIs `/finops` empilés sur 1 colonne, `Accostage` déplié coupant CTA Cockpit | `13 #26` & `20 #49` (grille `4` colonnes horizontales + `Journal d'Activité →` aligné) ; `03 #10`, `03 milestone-violet`, `19 #46` (`Accostage 4/6` replié sur 1 ligne, `Ouvrir l'atelier de relecture →` intact). | ✅ **Résolu** |
| **`UX23-15`** | **`P2`** | `Mes Espaces` actif à Jour 0, bouton `Fermer` modale admin, pack dupliqué `/settings`, 2e breadcrumb `/spaces`, 6e onglet `/settings` sur 2e ligne | `shell #53`/`#55` (`Mes Espaces` grisé à Jour 0 + badge `Étape obligatoire · Non ignorable` sans `Fermer`), `18 #42` (plus de ligne active dupliquée en bas), `07 #16` / `17 #38` (zéro 2e breadcrumb interne). *(Le 6e onglet `/settings` reste sur 1 ligne mais est rogné à `Mon Organ` avec Zone 4 ouverte $\rightarrow$ `UX24-01` `P2`).* | ✅ **Résolu** *(hors `UX24-01`)* |
| **`UX23-16`** | **`P3`** | Microcopy (`/ontology` option dupliquée, `/showcase` `3 espaces` / chemin fichier, `Mes  Espaces`, `tiers`, minuscule cassette) | `17 #39` (`Organisation (Global)` unique), `21 #51` (`4 espaces structurés` + `Exporter le site HTML autonome`), `07 #16` (`Mes Espaces`), `16 #35` (`4 paliers cognitifs`), `02 #7` (`Synthèse conforme...`). | ✅ **Résolu** |
| **`UX23-17`** | **`P3`** | Captures `00 #3/#4` & `04 #12` sur splash `Chargement...`, `6` jalons manquants | `00 #3` (`/cockpit`), `00 #4` (`/processes`), `04 #12` (`/inbox`) tous sur surfaces établies + `6` captures `milestone-*.png` présentes (`< 450 KB`). | ✅ **Résolu** |

---

## 3. Constats Résiduels Epic 24 (`0 P0`, `0 P1`, `3 P2`, `4 P3`)

Aucun défaut bloquant (`P0`) ni majeur (`P1`) n'a été observé sur les `61` PNG. Par souci d'exactitude absolue, les **`7` observations résiduelles (`3 P2` + `4 P3`)** constatées directement sur les images sont consignées ci-dessous :

| ID | Sév. | Composant / Fichier | Capture(s) PNG exacte(s) | Constat visuel observé honnêtement | Recommandation |
| --- | :---: | --- | --- | --- | --- |
| **`UX24-01`** | **`P2`** | `SettingsHubView` (`apps/web/src/routes/settings.tsx:137-189`) | `shell #52`, `14 #28`, `15 #32`, `16 #35`, `18 #42` (`/configuration`, `/settings`) | En `1440×900` lorsque la colonne Zone 4 (`340 px`) est ouverte, les `6` onglets forcés en `flexWrap: "nowrap"` débordent légèrement du conteneur horizontal et rognent visuellement le dernier onglet **`Mon Organisation`** en **`Mon Organ`**. | Autoriser `flex-wrap` contrôlé ou raccourcir les libellés / icônes des onglets (`Habilitations`, `Auth`, `Modèles IA`, `Connecteurs`, `Packs`, `Organisation`) pour que les `6` boutons tiennent sans troncature ni scroll horizontal dans `~760 px`. |
| **`UX24-02`** | **`P2`** | `ShellContainer.tsx:82,127` & `21-assistant...spec.ts:237-240` | `21-assistant-citations-v5-audit-help-showcase/...--centre-d-aide...--passed.png` (`#51`, `/showcase`) | Bien que `21 #51` valide `eight-menu-item-help` `data-active="true"` à la L219 avant rechargement, après `reloadClearingStorage(page)` (qui vide `localStorage`) le test n'attend que `orcia-product-showcase-site-view`. Comme `isShowcaseStandalone` évite `<ShellHydratingLoaderView />` alors que `PlatformSetupProvider` n'a pas encore reçu `getAccostageStatus()`, la capture finale saisit la fenêtre transitoire où les `7` entrées hors `Cockpit` (dont `Aide`) apparaissent grisées. | Conserver le dernier état connu ou ne pas appliquer le grisage Jour 0 (`!adminCreated`) tant que `isInitialLoading` de `PlatformSetupProvider` est en cours lorsque l'utilisateur est authentifié, et attendre la stabilisation du rail dans `21 #51` après `reloadClearingStorage`. |
| **`UX24-03`** | **`P2`** | `CockpitUpstreamChallengePanel.tsx` / `what_if_replay.py` | `03-...--milestone-arbitration-tiebreak-amber.png` (`/cockpit`) | La carte d'arbitrage et les boutons (`Pause et escalade humaine`, `Retenir cette option`, `Règle fondamentale de structure immuable`) sont propres, mais la boîte d'aperçu What-If au-dessus conserve **`[Traduction Ontologique -> PM_BUSINESS]`**, **`'delegate-remediation-subworkflow'`**, **`'frame-architecture-intent.human_architecture_intent'`** et **`dependent_on_human_architecture_intent`**. *(Note informative : la 4e carte Cockpit `Gouvernance Human-Led` sur `shell #54` et `10 #19` reste intentionnellement en attente sous le ticket gelé `UX-COCKPIT-DAY0-01`).* | Mapper `target_profile_archetype`, `challenger_step_key` et `section_key` via `formatStepKeyLabel` / dictionnaire de profil dans `translated_summary` et `UpstreamChallengeWhatIfPreviewCard`. |
| **`UX24-04`** | **`P3`** | `normalize_identifier_slug` (`packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_models.py:51-54`) | `08-agents-skills-persistence/...--un-agent-configure...--passed.png` (`#17`) | Le badge de `AgentDetailModalHeader` et la sortie d'exécution affichent **`@agent-e2e-conformit`** (sans `e` final), car le slugifier Python utilise `re.sub(r"[^a-z0-9]+", ...)` sans normalisation `NFKD` des accents, tronquant le `é` de `Conformité` après le retour API (alors que l'aperçu JS produit `@agent-e2e-conformite`). | Ajouter `unicodedata.normalize("NFKD", raw_name).encode("ascii", "ignore").decode("ascii")` dans `normalize_identifier_slug`. |
| **`UX24-05`** | **`P3`** | `WorkflowStudio` (`packages/ui/src/shell/WorkflowStudioSection.tsx`) | `09-pack-builder...--passed.png` (`#18`), `20-process-studio...--passed.png` (`#48`) | Sous `1. Éléments d'entrée & Livrable attendu`, le nom technique du paramètre `Demande_initiale_expression_du_besoin_ou_ticket_d_entr_e_` reste affiché devant le libellé lisible `(Demande initiale (expression du besoin ou ticket d'entrée))`. | Masquer la clé snake_case derrière l'info-bulle technique ou n'afficher que le libellé humain lorsque présent. |
| **`UX24-06`** | **`P3`** | `OntologyAndKbExplorerPanel.tsx`, `SettingsAuthenticationSection.tsx`, `GatesAdaptiveHumanReviewSection.tsx` | `17` (`milestone-ontology-tripartite-waivers.png`, `#40`), `14 #28`, `06 #15`, `19 #47` | - Sur `/ontology` (`17 #40`, `milestone-ontology-tripartite-waivers.png`), les placeholders de la carte gauche sont coupés (`...ou une réfé`, `...confluence://ESPACE/p`) et la boîte rose droite `Surveillance de l'Actualité des Documents` reste vide sous `Mise à jour recommandée` en mode global.<br>- Sur `14 #28`, le sous-titre mentionne `(/LOGIN)` ; sur `06 #15` / `19 #47`, le Bloc 1 affiche `step-architecture-gate`. | Raccourcir les placeholders `/ontology`, afficher un message d'état vide lisible dans la carte droite lorsque `alerts.length === 0`, et humaniser `step-architecture-gate` / `(/LOGIN)`. |
| **`UX24-07`** | **`P3`** | `apps/web/e2e/06-gates-review-and-anti-rubber-stamping.spec.ts:150` | `06-...--milestone-gates-hitl-drawer.png` | La capture nommée `milestone-gates-hitl-drawer.png` immortalise l'écran `/gates` après F5 (prouvant de façon décisive la correction `P0` `UX23-01` `Jira PAYBUILD-101 : Exécutée` ✅) plutôt que le tiroir HITL d'un run V2 dans `/processes` (`InteractiveRunDrawer`). | Ajouter ultérieurement un 7e jalon dédié sur `InteractiveRunDrawer` dans `20-process-studio`. |

---

## 4. Inspection Visuelle Détaillée par Lot & Jalons (`61 / 61` PNG)

### 4.1 Les `6` Captures Jalons (`milestone-*.png`)
1. `03-...--milestone-human-led-anchor-violet.png` (`/cockpit`, `199 119 B`) : Shell `1440×900` complet, fil `ORCIA > Equipe E2E > Espace Gouvernance E2E > Cockpit` avec `[Espace]`, badges traduits `En cours` & `En attente`, carte Violet `#6D28D9` `RÉDACTION PERSONNELLE OBLIGATOIRE` `(0/30)` sans aucun bouton IA, bouton `Ouvrir l'atelier de relecture →` non coupé ✅.
2. `03-...--milestone-arbitration-tiebreak-amber.png` (`/cockpit`, `263 623 B`) : Carte Ambre `#D97706` `ARBITRAGE REQUIS`, `Règle de départage: Pause et escalade humaine`, Option A vs Option B, boutons `Retenir cette option`, `Règle fondamentale de structure immuable` ✅ *(résidus What-If `UX24-03` notés en `P2`)*.
3. `06-...--milestone-gates-hitl-drawer.png` (`/gates`, `265 728 B`) : **`Point de contrôle : Validé   Jira PAYBUILD-101 : Exécutée`** présent dans l'interface après `reloadColdFromPg`, grille 4 blocs propre, `Hypothèses relues` vert, Section 1 `Approuvé`, zéro jargon `< 15 s` ou `PostgreSQL 18` ✅ *(`UX24-07` `P3`)*.
4. `11-...--milestone-login-screen-and-password-eye.png` (`/login`, `29 236 B`) : Mire Direction C centrée, champs vides avec icône œil `OrciaPasswordInput`, bouton `#2563EB` `Se connecter`, `0` alerte ✅.
5. `17-...--milestone-ontology-tripartite-waivers.png` (`/ontology`, `238 251 B`) : Option `Organisation (Global)` dédupliquée, Zone 4 `de l'Espace à l'Entreprise`, liens tripartite affichés ✅ *(`UX24-06` `P3`)*.
6. `20-...--milestone-vsm-11-steps.png` (`/processes/.../vsm`, `253 262 B`) : Fil `ORCIA > Equipe E2E > Espace Studio V2 > Mes Processus > Chaîne de valeur`, `vsm-mon-compte-idea-to-prod · v2.0.0`, onglets `Aujourd'hui | Avec les agents | Comparer`, graphe complet des **11 étapes (`01`..`11`)** et boucles de retour principales/secondaires parfaitement lisibles ✅.

### 4.2 Couverture complète des `24` specs (`#1`–`#55`)
- **`00-stack-smoke` (`#1`–`#4`)** : Modale Jour 0 opaque avec badge `Étape obligatoire · Non ignorable` sans `Fermer` (`#1`, `#2`) ; `#3` stabilisé sur `/cockpit` (`Accostage 1/6`), `#4` stabilisé sur `/processes` — **disparition totale du splash de chargement** ✅.
- **`01-day0-boot` (`#5`–`#6`)** : `#5` prouve l'atterrissage direct sur **`/profile`** (`USER24-BUG-2` ✅) sans bande `#EAF2FB` ; `#6` prouve le retour de la modale Jour 0 après `pnpm db:reset`.
- **`02-assistant` (`#7`–`#9`)** : `#7` démarre avec majuscule `"Synthèse conforme..."`, barre d'actions propre ; `#8` & `#9` montrent les dossiers persistés `Dossier E2E persistant` / `Dossier E2E PostgreSQL` + bannière `Modèle de recherche sémantique requis`.
- **`03-human-led` (`#10`)** : `Accostage 4/6` replié sur 1 ligne (`> Déplier le guide`), 4 compteurs KPI en 4 colonnes, `En cours` / `Validé`, CTA entier ✅.
- **`04-multi-actor-claim-sse` (`#11`–`#12`)** : `#11` sur `/login`, `#12` stabilisé sur **`/inbox`** avec aide contextuelle dédiée `Boîte de Réception : notifications, prises en charge et décisions d'équipe` ✅.
- **`05-mobile-companion-and-rgaa` (`#13`–`#14`)** : `#13` encart ambre RGAA `Modifications non enregistrées` propre ; `#14` `skipped` (`mobile-only`, `ACTION_ITEM-23.6`).
- **`06-gates` (`#15`) & `19-orchestration` (`#46`–`#47`)** : `Point de contrôle : Validé   Jira PAYBUILD-101 : Exécutée` persisté sur `#15` et `#47` ✅ ; `/cockpit` compacté sur `#46` ✅.
- **`07-spaces` (`#16`) & `11-screens-smoke` (`#21`–`#22`)** : `#16` carte `Espace E2E Comptabilité` nette, zéro double breadcrumb, placeholder `Rechercher un espace...` entier, `Mes Espaces` sans espace double ; `#21` (`/spaces` à `0` espace) exempt de tout `default-ws` ✅ ; `#22` sur `/cockpit` `1440×900` sans `#EAF2FB`.
- **`08-agents` (`#17`)** : `AgentDetailAndSandboxModal` dans `OrciaDialog`, `Bloc E` intact, footer sticky `Enregistrer`, Zone 4 `via « @ »` ✅ *(`UX24-04` `P3` `@agent-e2e-conformit`)*.
- **`09-pack-builder` (`#18`) & `20-process-studio` (`#48`–`#49`)** : Studio `Ex : Ajouter un contrôle...` non coupé (`#18`, `#48`) ; `/finops` 4 KPIs en 4 colonnes + table `wf-01-qualification-prd` `Opérationnel` (`#49`) ✅ *(`UX24-05` `P3`)*.
- **`10-command-palette-search` (`#19`–`#20`)** : Palette `⌘K` sans émoji `❓` (icône `OrciaIcon` blanche sur `#2563EB`), résultats exclusivement en français, zéro `#EAF2FB` ✅.
- **`12-epic16` (`#23`), `12-finops` (`#24`–`#25`), `13-epic-7` (`#26`–`#27`)** : `#23` trace réflexive propre sur `/processes` ; `#24` contraste `#FFFFFF` sur `#2563EB` (`Par Modèle et Niveau d'effort`) + `Journal d'Activité →` aligné ; `#26` 4 KPIs sur 4 colonnes ; `#25`/`#27` `skipped` (`mobile-only`).
- **`14-auth` (`#28`–`#30`)** : `#28` politique locale/2FA propre *(`UX24-01` `P2` + `(/LOGIN)` `P3`)* ; `#29` (`Claire Invitée`) affiche `Alice Admin E2E` et filtre à 2 jalons ; `#30` `UserSettingsModalDialog` onglets horizontaux + onglet `Clés IDE & MCP` sans bannière secret réaffichée ni `IDE MCP (SPACE · default)` / `60 RPM` ✅.
- **`15-organization-iam-secops-inbox-and-observer` (`#31`–`#34`)** : `#31` (`Marc Lead BU`) propre `Accostage 2/6` ; `#32` `Plateforme entière (Global)` entier *(`UX24-01` `P2`)* ; `#33` (`Oscar Observateur`) fil `ORCIA > Mon Organisation` ; `#34` (`/inbox`) fil `ORCIA > Boîte de Réception`, `Prise en charge directe — Relecture en boîte de réception`, `Synchronisation : temps réel` ✅.
- **`16-ai-models-reindex-connectors-and-broker` (`#35`–`#37`)** : `#35` `Terminée (100%)` et `4 paliers cognitifs` sans `AD-24.7` ; `#36` onglet `Connexions aux outils` horizontal sans vide vertical ; `#37` `PermissionBrokerCard` avec Markdown HTML rendu et URI décodée ✅.
- **`17-workspace` (`#38`–`#40`)** : `#38` `1 Source rattachée`, fil `ORCIA > Espace CodeGraph E2E > Mes Espaces > Sources` ; `#39` option `Organisation (Global)` unique + Zone 4 `de l'Espace à l'Entreprise` ; `#40` graphe tripartite persisté.
- **`18-catalog-packs-wizards-and-mcp-bench` (`#41`–`#45`)** : `#41` `/catalog` sans `0` nu ni `depth=0/1` ; `#42` pack unique sans ligne dupliquée ; `#43` `/settings/packs` `4 Compétences`, `1 Agent`, `1 Compétence`, `1 Validation`, `0 Chaîne`, libellés humains ; `#44` `/wizards` propre ; `#45` `/agents` onglet MCP propre.
- **`21-assistant-citations-v5-audit-help-showcase` (`#50`–`#51`)** : `#50` `/assistant` épuré ; `#51` `/showcase` `4 espaces structurés` + `Exporter le site HTML autonome` sans chemin interne ✅ *(flash transitoire de grisage post-reload noté en `UX24-02` `P2`)*.
- **`shell.spec.ts` (`#52`–`#55`)** : `#52` `/configuration` *(`UX24-01` `P2`)* ; `#53` & `#55` toutes entrées hors `Cockpit` grisées à Jour 0 (y compris `Mes Espaces`), modale non fermable ; `#54` `/cockpit` post-admin `1440×900` complet ✅.

---

## 5. Conclusion Sally (`0 P0`, `0 P1`)

**Verdict UX/UI :** **`0` écart `P0`, `0` écart `P1`** sur l'ensemble des `61` captures PNG (`100 %` inspectées). Toutes les remédiations `UX23-01..17` et `USER24-BUG-1..6` sont visuellement confirmées. Les `3 P2` et `4 P3` mineurs identifiés n'entravent aucun parcours métier et sont orientés vers un lot d'hygiène UX post-clôture (en parallèle d'`ACTION_ITEM-23.6` Mobile Companion). **Accord UX complet pour la clôture `Case A` de l'Epic 24.**
