# 🎨 Audit UX/UI Visuel — Campagne E2E Epic 22 (Sally / Story 22.9)

- **Auditrice** : 🎨 **Sally** (UX Designer — `bmad-agent-ux-designer`)
- **Périmètre** : Revue visuelle et ergonomique des captures Playwright issues de la campagne E2E Epic 22 (`feat/epic-22-remediation-pg18-direction-c`, commit `a1bb059`)
- **Référentiels appliqués** :
  - [`DESIGN.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md) (Direction C Sobriété — Coquille 4 Zones, tokens, 19 composants identitaires)
  - [`EXPERIENCE.md`](../../planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md) (6 règles UX, 3 invariants microcopy, Mobile Companion)
  - Les 11 règles fondamentales UX/UI & 3 règles de microcopy de [`GEMINI.md`](../../../GEMINI.md)
  - [`bilan-execution-tests-e2e-epic-22.md`](./bilan-execution-tests-e2e-epic-22.md) & [`manifest.jsonl`](./manifest.jsonl)

---

## 1. Résumé exécutif chiffré

🎨 L'audit visuel porte sur une campagne de **110 scénarios planifiés** (`55` `desktop-cockpit` en `1440×900` + `55` `mobile-companion` en `390×844` / rendu Retina `1024×2216`), dont **110 / 110** disposent de leur capture PNG dans `./screenshots/`.

| Catégorie | Total campagne | Inspectés visuellement par Sally | Taux d'inspection | État visuel dominant |
| --- | ---: | ---: | ---: | --- |
| **Succès (`passed`)** | **7** (`7` desktop, `0` mobile) | **7** | **100 %** | Chargement `/cockpit` (`#1`), Modale Jour 0 (`#2`, `#6`), Cockpit post-admin (`#5`, `#10`), `Mon Assistant` + Dossiers (`#8`, `#9`) |
| **Échecs HTTP `401` directs** | **3** (`3` desktop, `0` mobile) | **3** | **100 %** | Modale Jour 0 silencieuse (`#3`, `#4`), `/assistant` avec bannière d'alerte trompeuse sur `401` (`#7`) |
| **Échecs cascade `beforeEach` (`resetDay0()`)** | **87** (`43` desktop, `44` mobile) | **14** (`6` desktop, `8` mobile) | **16,1 %** *(échantillon couvrant 9 specs)* | Mire `/login` (`Connexion à ORCIA`) — utilisateur résiduel `Alice Admin E2E` en base sans session |
| **Ignorés (`skipped` viewport)** | **13** (`2` desktop, `11` mobile) | **0** *(taille PNG identique aux `/login`)* | — | Mire `/login` capturée au `afterEach` |
| **Total** | **110** | **24** | **21,8 %** | — |

### Constat de couverture UX réel (Angle mort critique Mobile & Écrans Métiers)
- 🎨 **Visibilité effective sur Desktop (`1440×900`)** : seuls **3 écrans** ont été rendus et observables visuellement dans cette campagne :
  1. Le **Cockpit** (`/`, `/cockpit`) — état chargement (`#1`), état Jour 0 avec modale Portal (`#2`, `#3`, `#4`, `#6`), état post-admin (`#5`), état post-exécution (`#10`).
  2. **Mon Assistant** (`/assistant`) — avec bannière d'alerte `401` (`#7`) et état dossier actif + notes (`#8`, `#9`).
  3. La mire **`/login`** (`Connexion à ORCIA`) — état non authentifié en cascade (`#11`–`#110`).
- 🎨 **Angle mort de `100 %` sur Mobile Companion (`0 / 55` PASS) et sur les écrans métiers `04`–`21`** : la panne SQL `resetDay0()` (`RestrictViolationError` sur `DELETE FROM step_executions` dès la fin du scénario `#10`) a empêché l'exécution de **tous** les scénarios `mobile-companion` (`44` échecs `beforeEach` + `11` skips) ainsi que de toutes les specs `04` à `21` et `shell.spec.ts`. Par conséquent, **aucun** écran authentifié mobile (barre basse à 3 onglets, `/finops`, `/processes`, `/assistant`, modale Jour 0 sur mobile) ni aucune surface de revue (`HumanLedAnchorCard`, `ChunkedValidationCard`, `ReviewBriefingGrid`, Studio, `Configuration`) n'a pu être audité visuellement en Epic 22.

---

## 2. Synthèse de conformité Direction C & Invariants UX/UI

| Critère Direction C / Invariant UX | Verdict observé | Évidences visuelles (captures inspectées) |
| --- | :---: | --- |
| **Sidebar 8 entrées non numérotées + sans bouton « Nouvelle discussion »** | ⚠️ **Partiel** | `8` entrées exactes, sans numérotation, après création admin (`#5`, `#7`–`#10`). **Écart** : avant création admin (`#2`–`#4`, `#6`), `Configuration` est masquée (`7` entrées) et `Mes Espaces` reste actif/noir alors que `Mon Assistant`..`FinOps` sont grisés. De plus, la marque cliquable `ORCIA` est dans la `TopHeaderBar` et non en haut de la Sidebar (`DESIGN.md` §2.1). |
| **Double Sélecteur d'Organigramme Empilé (`Équipe / Direction` + `Espace`)** | ✅ **Conforme** *(avec troncature header)* | Empilement propre en haut de Zone 1 (`#2`–`#10`), synchronisé avec le changement de contexte (`Equipe E2E` / `Espace E2E Dossiers PG` en `#9`, `Espace Gouvernance E2E` en `#10`). |
| **TopHeaderBar & Fil d'Ariane (`Breadcrumb`)** | ⚠️ **Partiel** | `ORCIA > Cockpit` / `ORCIA > Mon Assistant` + recherche `⌘K` + `Aide` + `Notifications`. **Écarts** : `Équipe / Direction` absente du fil d'Ariane (`DESIGN.md` §2.1) ; pilule `Espace : Plateforme Globale O...` et placeholder `... ou partout (... ⌘K` tronqués à `1440px` ; compteur **`Notifications 4`** présent dès le Jour 0 avant même toute activité (`#2`–`#5`, `#7`). |
| **Zone 4 — Aide Contextuelle Dynamique (`340px`, sans `Chef1`/`aqwZSX`)** | ❌ **Non conforme** | Aucune fuite `Chef1` / `aqwZSX` ✅. **Mais** : sur `/assistant` (`#7`, `#8`, `#9`), Zone 4 affiche des cartes du **Cockpit** (`ⓘ Décisions en attente et relectures : "Le Cockpit regroupe..."`) ; sur `/cockpit` (`#5`), elle affiche `Les 3 modes de réponse de Mon Assistant` ; le bas de Zone 4 est **tronqué** même sur capture pleine page `1362px` (`#2`, `#5`) ; les blocs prescrits (`EN N GESTES`, encadré ambre `UN EXEMPLE RÉEL`, `CE QUI COINCE SOUVENT`) sont absents au profit de métadonnées techniques (`@1.0.0`, `Sources du guide : BASE → PACK → WORKSPACE (core)`). |
| **Cockpit `<= 3` blocs** | ❌ **Non conforme** | **`6` blocs** sur `#5` (Jour 0 post-admin) et **`7` blocs / zones** sur `#10` (dont formulaire sans titre de lancement tout en bas), dépassant `900px` (`1303px`–`1362px`) et créant une forte redondance (`Accès rapide à Mon Assistant` + tuile `Mon Assistant` + checklist `Étape 3`). |
| **`Accostage X/5` sans `LOCK TABLE...`** | ⚠️ **Partiel** | Aucun texte `LOCK TABLE...` ✅. **Mais** : `Accostage 0/5` affiché **deux fois** en `#5` alors que `Étape 1` est déjà verte (`✓`) ; `Étape 3 : Création de votre premier Espace` liste `1. Modèles IA` (doublon de `Étape 2`) et tronque 3 libellés sur 5 ; l'échelle `X/5` diverge de `1/6` dans `DESIGN.md` et ne comptabilise pas l'Étape 1. |
| **Modales Portal `OrciaDialog`** | ⚠️ **Partiel** | Portal bien centré au-dessus des 4 zones sans coupure par Zone 4 (`#2`, `#3`, `#4`, `#6`) ✅. **Mais** : double bouton `Annuler (Esc)` (haut droite avec bordure noire épaisse + bas gauche), bouton primaire `Créer le compte Administrateur` sans hiérarchie visuelle primaire, et champ `Mot de passe` affichant `••••••••••••••` par défaut. |
| **Mobile Companion & Responsive** | ⚠️ **Non vérifiable au fond** | `0 / 55` PASS sur mobile. Sur la seule mire atteinte (`/login`, 8 captures inspectées), rendu propre sans débordement horizontal à `390×844` (`1024×2216`). Aucun écran authentifié mobile n'a pu être validé. |
| **Langage métier & microcopy (0 `[LAYER_5_*]`, 0 `(!)` bleu, 0 jargon)** | ⚠️ **Partiel** | Zéro `[LAYER_5_*]` et zéro pastille rouge `(!)` dans les boutons bleus ✅. **Mais** : message `401` erroné et technique en `#7` (`(HTTP 401 Unauthorized). Vérifiez que le modèle IA configuré est bien démarré`), jargon `embedding sémantique` (`#7`–`#9`), `BASE → PACK → WORKSPACE (core)` (`#2`–`#4`, `#7`), `(Esc)` (`#2`–`#4`, `#6`). |
| **Contrastes WCAG AA & Typographie** | ⚠️ **Partiel** | Bon contraste sur `/login`, titres `#0F172A`, boutons primaires `#2563EB`. **Points de vigilance** : contraste faible des entrées de menu grisées sans explication visible, contraste de l'alerte ambre `#7` à vérifier, faible différenciation visuelle du bouton d'envoi `#8`/`#9` et du CTA de la modale Jour 0 (`#2`). |

---

## 3. Analyse détaillée capture par capture

### 3.1. Les `7` captures `passed` (`100 %` inspectées)

1. **`#1` — `00-stack-smoke` (`desktop-cockpit`) : Proxy Vite → FastAPI**
   - **Capture** : [`desktop-cockpit--l-api-fastapi-repond-via-le-proxy-vite-navigateur-vite-fastapi--passed.png`](./screenshots/00-stack-smoke/desktop-cockpit--l-api-fastapi-repond-via-le-proxy-vite-navigateur-vite-fastapi--passed.png) (`1440×900`, `3121 ms`, `url: /cockpit`)
   - **Constat 🎨** : Affiche uniquement le texte centré `Chargement de la session...` en petit gris ardoise sur fond `#EAF2FB`. Bien que techniquement attendu si la capture est prise pendant la résolution initiale, l'écran de transition manque de repère identitaire (logo ORCIA discret, indicateur de progression/spinner ou squelette de la coquille 4 zones) — un utilisateur sur connexion lente a l'impression d'une page bloquée (Règle UX #4 : feedback immédiat).

2. **`#2` — `00-stack-smoke` (`desktop-cockpit`) : Modale Premier Administrateur Jour 0**
   - **Capture** : [`desktop-cockpit--apres-reset-jour-0-la-modale-de-premier-administrateur-est-presentee--passed.png`](./screenshots/00-stack-smoke/desktop-cockpit--apres-reset-jour-0-la-modale-de-premier-administrateur-est-presentee--passed.png) (`1440×1362` fullPage, `3632 ms`, `url: /`)
   - **Constat 🎨** :
     - **Portal & Isolation** ✅ : La modale `OrciaDialog` passe proprement au-dessus des 4 zones (Zone 4 grisée derrière le voile, aucune coupure).
     - **Boutons dupliqués & hiérarchie inversée** ❌ : Deux boutons `Annuler (Esc)` coexistent dans la même modale (en haut à droite avec une bordure noire très marquée qui attire tout l'œil, et en bas à gauche). À l'inverse, le CTA principal `Créer le compte Administrateur` ressemble à un bouton secondaire pâle (même apparence qu'`Annuler (Esc)`). De plus, `(Esc)` est un anglicisme dans une interface francophone (`Échap`) et annuler une création obligatoire de Jour 0 laisse un état ambigu.
     - **Champ mot de passe ambigu** ❌ : Le champ `Mot de passe` affiche déjà `••••••••••••••` en gris foncé, donnant l'illusion visuelle d'un mot de passe pré-rempli alors que `Nom complet` (`Ex : Romain`) et `Adresse e-mail` (`admin@entreprise.fr`) ont un rendu plus clair de placeholder.
     - **Fantômes Jour 0 en arrière-plan** ❌ : Le pied de la Sidebar affiche déjà `AP Administrateur de la ... Contributeur` alors qu'aucun compte n'existe en base ; la `TopHeaderBar` affiche déjà **`Notifications 4`** ; `Configuration` est absente (`7` entrées au lieu de `8`) et `Mes Espaces` reste noir/actif tandis que `Mon Assistant`, `Mes Processus`, `Mes Agents` et `FinOps` sont grisés.

3. **`#5` — `01-day0-boot-and-f5-persistence` (`desktop-cockpit`) : Survie F5 du premier admin créé**
   - **Capture** : [`desktop-cockpit--le-premier-administrateur-cree-survit-a-un-f5-sans-localstorage-rehydratation-postgresql--passed.png`](./screenshots/01-day0-boot-and-f5-persistence/desktop-cockpit--le-premier-administrateur-cree-survit-a-un-f5-sans-localstorage-rehydratation-postgresql--passed.png) (`1440×1303` fullPage, `5539 ms`, `url: /`)
   - **Constat 🎨** :
     - **Sidebar 8 entrées & Identité** ✅ : Les 8 entrées exactes (`Cockpit`, `Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `FinOps`, `Configuration`, `Aide`) apparaissent sans numérotation ; le pied gauche affiche `AE Alice Admin E2E / Administrateur de la plate...` (tronqué sur la fin du rôle).
     - **Explosion du Cockpit (`6` blocs > `3` max)** ❌ : La Zone 3 empile 6 blocs sur `1303 px` de hauteur (`403 px` sous la ligne de flottaison `900px`) : (1) barre `Accostage 0/5 ⓘ` + `Contexte actif`, (2) `Guide de Démarrage de la Plateforme`, (3) `✅ Aucune décision en attente`, (4) `Accès rapide à Mon Assistant`, (5) trio `Mon Assistant / Mes Processus / Mes Espaces`, (6) `Aucun Espace de Travail ni processus en cours` + `+ Créer un Espace de Travail`. Plusieurs points d'entrée sont redondants (3 chemins différents vers `Mon Assistant` ou la création d'espace sur un même écran).
     - **Incohérence `Accostage 0/5`** ❌ : `Accostage 0/5` est répété deux fois (barre haute + titre de carte), et reste à **`0/5`** alors que `Étape 1 : Compte Administrateur de la plateforme` affiche `Administrateur de plateforme initialisé ✓ Alice Admin E2E` en vert. Dans `Étape 3 : Création de votre premier Espace`, l'item `1. Modèles IA` fait doublon avec `Étape 2` et 3 libellés sur 5 sont tronqués (`2. Structure Organisationnel...`, `4. Sources Documentaires &...`, `5. Packs Métiers & Atelier de...`).
     - **Troncatures `TopHeaderBar` & Zone 4** ❌ : `Espace : Plateforme Globale O...` et `Rechercher dans cet Espace ou partout ... ⌘K` sont tronqués à `1440px`. Dans Zone 4, la 4e carte (`Les 3 modes de réponse de Mon Assistant`) est coupée en plein texte au bas de la capture et parle de `Mon Assistant` sur la page `Cockpit`.

4. **`#6` — `01-day0-boot-and-f5-persistence` (`desktop-cockpit`) : Retour modale après reset Jour 0**
   - **Capture** : [`desktop-cockpit--apres-reset-jour-0-la-modale-revient-0-utilisateur-en-base--passed.png`](./screenshots/01-day0-boot-and-f5-persistence/desktop-cockpit--apres-reset-jour-0-la-modale-revient-0-utilisateur-en-base--passed.png) (`1440×1362` fullPage, `6148 ms`, `url: /`)
   - **Constat 🎨** : État visuel strictement identique à `#2` — confirme la reproductibilité exacte du retour au Jour 0 et des mêmes défauts de la modale (`Annuler (Esc)` dupliqué, `••••••••••••••`, `Notifications 4`, utilisateur fantôme `AP Administrateur de la ...`, Zone 4 coupée en bas).

5. **`#8` — `02-assistant-streaming-and-folders` (`desktop-cockpit`) : Dossier créé & réhydraté après F5**
   - **Capture** : [`desktop-cockpit--un-dossier-cree-dans-un-espace-est-rehydrate-depuis-l-api-apres-un-vrai-f5-cache-navigat--passed.png`](./screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-dossier-cree-dans-un-espace-est-rehydrate-depuis-l-api-apres-un-vrai-f5-cache-navigat--passed.png) (`1440×900`, `10959 ms`, `url: /assistant`)
   - **Constat 🎨** :
     - **Lisibilité de `Mon Assistant`** ✅ : Interface centrale propre et aérée : carte d'en-tête (`Votre assistant conversationnel appuyé sur vos sources ⓘ`), barre d'actions (`+ Nouvelle conversation`, `Conversations sauvegardées (0)`, `Dossiers (1)`, `⚙ Réglages de Mon Assistant`), bannière ambre claire d'état sans modèle d'indexation avec lien d'action `Configurer un modèle d'embedding →`, et panneau inférieur `Dossier actif : Dossier E2E persistant` avec `Notes épinglées`, `Partager / Visibilité`, `Désélectionner`, champ notes et bouton `#2563EB` `Enregistrer les notes` parfaitement contrasté.
     - **Défauts observés** ❌ :
       - **Pollution de Zone 4 par les cartes du Cockpit** : Sur `/assistant`, la carte #3 de Zone 4 affiche `ⓘ Décisions en attente et relectures — Le Cockpit regroupe uniquement les points qui demandent votre intervention...`, et la carte #4 (`Les 3 modes de réponse de Mon Assistant`) cite des libellés (`« Réponse rapide »`, `« Avec un agent »`, `« Analyse approfondie »`) qui ne correspondent pas au sélecteur visible à l'écran (`Polyvalent · Standard ⌄`). En plus, Zone 4 est coupée net à `900px` sans indication visuelle de défilement.
       - **Jargon résiduel** : `Modèle d'embedding sémantique requis` / `Configurer un modèle d'embedding →` (terme technique `embedding` vs `indexation sémantique`), et `Sources du guide : BASE (core)` / `@1.0.0` dans Zone 4.
       - **Troncature recherche** : Placeholder `Rechercher dans cet Espace ou partout (... ⌘K` coupé en pleine parenthèse ouvrante `(...` !
       - **Cohérence de portée** : `Dossier E2E persistant` est actif alors que la Sidebar gauche indique encore `Plateforme Globale ORCIA` / `Tous les espaces` (contrairement à `#9` où l'espace E2E est sélectionné).

6. **`#9` — `02-assistant-streaming-and-folders` (`desktop-cockpit`) : Dossier survit au redémarrage API**
   - **Capture** : [`desktop-cockpit--un-dossier-survit-au-redemarrage-de-l-api-persistance-postgresql--passed.png`](./screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-dossier-survit-au-redemarrage-de-l-api-persistance-postgresql--passed.png) (`1440×900`, `9930 ms`, `url: /assistant`)
   - **Constat 🎨** : Confirmé cohérent sur le double sélecteur (`Equipe E2E` / `Espace E2E Dossiers PG`) et le fil d'Ariane (`ORCIA > Mon Assistant  Espace : Espace E2E Dossiers PG ⌄`). Mêmes remarques UX que `#8` sur Zone 4 (`Décisions en attente et relectures` hors sujet, coupe en bas, `BASE (core)`, `@1.0.0`), la troncature `partout (... ⌘K` et le terme `embedding`.

7. **`#10` — `03-human-led-anchor-and-arbitration` (`desktop-cockpit`) : Ancrage violet & arbitrage (survie F5)**
   - **Capture** : [`desktop-cockpit--signature-de-l-ancrage-violet-30-car-rejet-agent-422-arbitrage-motive-et-survie-au-f5--passed.png`](./screenshots/03-human-led-anchor-and-arbitration/desktop-cockpit--signature-de-l-ancrage-violet-30-car-rejet-agent-422-arbitrage-motive-et-survie-au-f5--passed.png) (`1440×900`, `11281 ms`, `url: /cockpit`)
   - **Constat 🎨** : Note importante : la capture finale a été prise après retour sur `/cockpit`, donc la carte violette `HumanLedAnchorCard` (`#6D28D9`) et la matrice d'arbitrage ne figurent pas dans ce PNG final (elles ne sont observables qu'en cours de test). Sur l'écran `/cockpit` capturé :
     - **Double sélecteur & Accostage** : `Equipe E2E` / `Espace Gouvernance E2E` bien sélectionnés, mais `Espace : Espace Gouvernance ...` tronqué dans la `TopHeaderBar`. `Accostage 2/5` reflète `2. Structure Organisationnelle ✓` et `3. Espaces de Travail ✓`, mais ignore toujours `Étape 1 ✓`.
     - **Surcharge verticale (`7` éléments / blocs)** ❌ : Le bloc inférieur de lancement rapide (`Espace Gouvernance E2E v` | `Assistant ORCIA (Processus standard) v` | `Intitulé de l'exécution...` | `Démarrer le processus`) s'ajoute à tous les blocs d'accostage et d'accès rapides existants, sans titre ni icône `ⓘ`, et plaque ses contrôles près du bord inférieur à `900px`.

---

### 3.2. Les `3` captures d'échecs `HTTP 401` directs (`100 %` inspectées)

8. **`#3` — `00-stack-smoke` (`desktop-cockpit`) : Story 16.1 inspection chirurgicale (`HTTP 401`)**
   - **Capture** : [`desktop-cockpit--story-16-1-l-inspection-chirurgicale-l1-40-retourne-40-lignes-badge-y-et-bloque-en-rfc-9--failed.png`](./screenshots/00-stack-smoke/desktop-cockpit--story-16-1-l-inspection-chirurgicale-l1-40-retourne-40-lignes-badge-y-et-bloque-en-rfc-9--failed.png) (`1440×900`, `1979 ms`, `url: /cockpit`)
   - **Constat 🎨** : L'assertion E2E portait sur un appel direct `apiGet(request, "/api/v1/sources/inspect-lines...")` avant création de l'admin Jour 0. Visuellement, le navigateur affiche la modale Jour 0 sans erreur UI (cohérent avec un appel API hors DOM). On note toutefois les mêmes défauts de la modale Jour 0 qu'en `#2`, et dans cette capture à `900px` de hauteur on constate que l'écran Cockpit complet dépasse la hauteur du viewport (le bloc `Aucun Espace de Travail ni processus en cours` touche le bord inférieur).

9. **`#4` — `00-stack-smoke` (`desktop-cockpit`) : Story 16.2 moteur réflexif (`HTTP 401`)**
   - **Capture** : [`desktop-cockpit--story-16-2-moteur-reflexif-asyncio-survie-f5-waiting-write-preview-approbation-writeprev--failed.png`](./screenshots/00-stack-smoke/desktop-cockpit--story-16-2-moteur-reflexif-asyncio-survie-f5-waiting-write-preview-approbation-writeprev--failed.png) (`1440×1303` fullPage, `1214 ms`, `url: /cockpit`)
   - **Constat 🎨** : Même contexte que `#3` (appel direct `apiPost(request, "/api/v1/executions/reflexive")` retournant `401` avant initialisation Jour 0). Même état visuel de modale Jour 0 + `Notifications 4` + utilisateur fantôme `AP Administrateur de la ...` + Zone 4 tronquée en bas.

10. **`#7` — `02-assistant-streaming-and-folders` (`desktop-cockpit`) : Tour d'assistant (`HTTP 401` sur `/api/v1/assistant/three-speed/stream`) — DÉFAUT UX MAJEUR**
    - **Capture** : [`desktop-cockpit--un-tour-d-assistant-traverse-le-navigateur-l-api-et-la-cassette-llm-0-et-affiche-une-rep--failed.png`](./screenshots/02-assistant-streaming-and-folders/desktop-cockpit--un-tour-d-assistant-traverse-le-navigateur-l-api-et-la-cassette-llm-0-et-affiche-une-rep--failed.png) (`1440×900`, `5114 ms`, `url: /assistant`)
    - **Constat 🎨 (Critique UX / Microcopy / Récupération d'erreur)** :
      - **Le message affiché à l'utilisateur** dans l'encadré d'alerte ambre est :
        > `⚠ Impossible d'obtenir une réponse de Mon Assistant (HTTP 401 Unauthorized). Vérifiez que le modèle IA configuré est bien démarré.`
      - **Diagnostic UX trompeur (`P0`)** : Lorsque le serveur renvoie **`401 Unauthorized`** (session absente/expirée ou non autorisée), l'interface accuse à tort le **serveur de modèle IA** (*« Vérifiez que le modèle IA configuré est bien démarré »*) au lieu d'informer l'utilisateur d'un **problème de session / d'authentification** ! L'utilisateur (ou l'administrateur) va chercher une panne LLM inexistante.
      - **Fuite de jargon HTTP (`P1`)** : Exposition brute de `(HTTP 401 Unauthorized)` en violation de la règle microcopy #1 (`EXPERIENCE.md` §1.2 / `GEMINI.md`).
      - **Impasse sans sortie de secours (`P1`)** : Aucun bouton d'action dans l'encart d'erreur (pas de `Se reconnecter →`, pas de `Réessayer`) — violation des règles UX #4 (feedback actionnable) et #5 (sorties de secours).
      - **Traitement visuel de l'alerte (`P2`)** : L'encart utilise la teinte ambre (`arbitration-amber`) alors qu'un blocage `401` relève d'une erreur bloquante (`stale-danger` rouge ou bannière de reconnexion dédiée), et le contraste du texte orange/ambre sur fond beige clair mérite un durcissement pour garantir `>= 4,5:1` WCAG AA.
      - **Dérive Zone 4 entre `#7` et `#8`** : En `#7`, Zone 4 titre `Mon Assistant` (court) avec `Sources du guide : BASE → PACK → WORKSPACE (core)`, tandis qu'en `#8`/`#9` elle titre `Mon Assistant : questions, dossiers et citations vérifiées` avec `Sources du guide : BASE (core)`, mais dans les deux cas Zone 4 conserve la carte `ⓘ Décisions en attente et relectures` du Cockpit !

---

### 3.3. Échantillon représentatif des captures d'échecs `beforeEach` (`14` inspectées sur `87`)

Toutes les `87` captures en échec `beforeEach` (`#11`–`#110` hors `13` skips) résultent du blocage SQL de `resetDay0()` (`09_reset_db_first_boot.py` / `reset_day0.py` sur `RestrictViolationError` FK `blackboard_snapshots_step_execution_id_fkey`). L'analyse des tailles de fichiers sur les `110` PNG confirme une homogénéité totale : les `45` captures desktop `beforeEach`/skip font toutes `25 424` octets (`1440×900`) et les `55` captures mobile `beforeEach`/skip font toutes `71 421` octets (`1024×2216`).

#### Échantillon `desktop-cockpit` (`6` captures inspectées — toutes sur `/login` `Connexion à ORCIA`)
- **`#11`** (`04-multi-actor-claim-sse`) : [`desktop-cockpit--a-prend-en-charge-une-tache-b-est-refuse-409-et-un-nouveau-flux-sse-rejoue-l-evenement-5--failed.png`](./screenshots/04-multi-actor-claim-sse/desktop-cockpit--a-prend-en-charge-une-tache-b-est-refuse-409-et-un-nouveau-flux-sse-rejoue-l-evenement-5--failed.png)
- **`#13`** (`05-mobile-companion-and-rgaa`) : [`desktop-cockpit--escape-sur-un-formulaire-modifie-demande-confirmation-avant-d-abandonner-garde-isdirty--failed.png`](./screenshots/05-mobile-companion-and-rgaa/desktop-cockpit--escape-sur-un-formulaire-modifie-demande-confirmation-avant-d-abandonner-garde-isdirty--failed.png)
- **`#28`** (`14-auth-2fa-account-and-profile`) : [`desktop-cockpit--politique-d-authentification-et-bascule-2fa-persistent-apres-f5-en-base-postgresql--failed.png`](./screenshots/14-auth-2fa-account-and-profile/desktop-cockpit--politique-d-authentification-et-bascule-2fa-persistent-apres-f5-en-base-postgresql--failed.png)
- **`#35`** (`16-ai-models-reindex-connectors-and-broker`) : [`desktop-cockpit--jour-0-sans-embedding-garde-ssrf-modeles-chat-embedding-1024-et-reindexation-survivent-a--failed.png`](./screenshots/16-ai-models-reindex-connectors-and-broker/desktop-cockpit--jour-0-sans-embedding-garde-ssrf-modeles-chat-embedding-1024-et-reindexation-survivent-a--failed.png)
- **`#41`** (`18-catalog-packs-wizards-and-mcp-bench`) : [`desktop-cockpit--explorateur-du-catalogue-federe-droits-granulaires-et-definitions-persistent-en-base-apr--failed.png`](./screenshots/18-catalog-packs-wizards-and-mcp-bench/desktop-cockpit--explorateur-du-catalogue-federe-droits-granulaires-et-definitions-persistent-en-base-apr--failed.png)
- **`#52`** (`shell.spec.ts`) : [`desktop-cockpit--presente-les-4-zones-masque-parametres-tant-qu-aucun-platform-admin-n-est-connecte-et-l---failed.png`](./screenshots/shell/desktop-cockpit--presente-les-4-zones-masque-parametres-tant-qu-aucun-platform-admin-n-est-connecte-et-l---failed.png)

#### Échantillon `mobile-companion` (`8` captures inspectées — toutes sur `/login` `Connexion à ORCIA`)
- **`#57`** (`00-stack-smoke` mobile) : [`mobile-companion--apres-reset-jour-0-la-modale-de-premier-administrateur-est-presentee--failed.png`](./screenshots/00-stack-smoke/mobile-companion--apres-reset-jour-0-la-modale-de-premier-administrateur-est-presentee--failed.png)
- **`#62`** (`02-assistant-streaming-and-folders` mobile) : [`mobile-companion--un-tour-d-assistant-traverse-le-navigateur-l-api-et-la-cassette-llm-0-et-affiche-une-rep--failed.png`](./screenshots/02-assistant-streaming-and-folders/mobile-companion--un-tour-d-assistant-traverse-le-navigateur-l-api-et-la-cassette-llm-0-et-affiche-une-rep--failed.png)
- **`#69`** (`05-mobile-companion-and-rgaa` mobile) : [`mobile-companion--aucun-debordement-horizontal-sur-mobile-une-fois-la-plateforme-initialisee--failed.png`](./screenshots/05-mobile-companion-and-rgaa/mobile-companion--aucun-debordement-horizontal-sur-mobile-une-fois-la-plateforme-initialisee--failed.png)
- **`#80`** (`12-finops-and-audit-provenance` mobile) : [`mobile-companion--mobile-finops-et-activity-s-affichent-sans-debordement-horizontal-ni-erreur-serveur--failed.png`](./screenshots/12-finops-and-audit-provenance/mobile-companion--mobile-finops-et-activity-s-affichent-sans-debordement-horizontal-ni-erreur-serveur--failed.png)
- **`#85`** (`14-auth-2fa-account-and-profile` mobile) : [`mobile-companion--popup-mon-compte-parametres-5-onglets-cle-ide-mcp-et-page-profil-survivent-a-un-f5--failed.png`](./screenshots/14-auth-2fa-account-and-profile/mobile-companion--popup-mon-compte-parametres-5-onglets-cle-ide-mcp-et-page-profil-survivent-a-un-f5--failed.png)
- **`#99`** (`18-catalog-packs-wizards-and-mcp-bench` mobile) : [`mobile-companion--parcours-guide-d-initialisation-avec-retour-arriere-survit-a-f5-et-persiste-dans-wizard---failed.png`](./screenshots/18-catalog-packs-wizards-and-mcp-bench/mobile-companion--parcours-guide-d-initialisation-avec-retour-arriere-survit-a-f5-et-persiste-dans-wizard---failed.png)
- **`#107`** (`shell.spec.ts` mobile) : [`mobile-companion--presente-les-4-zones-masque-parametres-tant-qu-aucun-platform-admin-n-est-connecte-et-l---failed.png`](./screenshots/shell/mobile-companion--presente-les-4-zones-masque-parametres-tant-qu-aucun-platform-admin-n-est-connecte-et-l---failed.png)
- **`#110`** (`shell.spec.ts` mobile) : [`mobile-companion--la-modale-jour-0-est-un-dialogue-accessible-qui-bloque-le-shell--failed.png`](./screenshots/shell/mobile-companion--la-modale-jour-0-est-un-dialogue-accessible-qui-bloque-le-shell--failed.png)

#### Ce que révèlent ces `14` captures `beforeEach`
1. **Pourquoi `/login` s'affiche partout** : le scénario `#10` (`03-human-led-anchor-and-arbitration`) ayant créé `Alice Admin E2E` et persisté une ligne `step_executions` + `blackboard_snapshots` en base, l'échec du `resetDay0()` dès `#11` a laissé l'utilisateur administrateur en base. Chaque nouveau contexte Playwright non authentifié navigant vers `/cockpit` est donc proprement redirigé vers la mire de connexion `Connexion à ORCIA` (comportement sécurisé ✅).
2. **Qualité visuelle de `/login` (Desktop & Mobile)** ✅ : Carte blanche centrée sur fond `#EAF2FB`, hiérarchie nette (`Connexion à ORCIA`, sous-titre explicite, labels clairs `Adresse e-mail professionnelle` et `Mot de passe`, bouton plein largeur `#2563EB` `Se connecter` à fort contraste), **zéro débordement horizontal sur `390×844`**.
3. **Points d'amélioration sur `/login`** : absence du logo/identité ORCIA en tête de carte (Règle UX #3) et absence de bouton œil afficher/masquer le mot de passe.
4. **Impact UX de la cascade sur les tests d'erreur `[role="alert"]` et Mobile** : faute d'atteindre les écrans authentifiés (`04`–`21` et les `44` tests mobiles), **aucun** comportement `[role="alert"]` sur mobile, ni la barre d'onglets basse à 3 entrées du Mobile Companion, ni les bannières de redirection Desktop (`Configuration avancée réservée au poste Desktop`) n'ont pu être vérifiés visuellement.

---

## 4. Liste priorisée des défauts visuels / UX (`P0`..`P3`) pour dialogue avec Winston

### `P0` — Bloquants (impact critique sur la compréhension utilisateur ou la vérifiabilité UX)

1. **`P0-UX-1` — Diagnostic erroné, jargon HTTP et impasse sans action sur erreur `401` dans `Mon Assistant`** (`#7`)
   - **Constat** : Sur `HTTP 401`, `/assistant` affiche `⚠ Impossible d'obtenir une réponse de Mon Assistant (HTTP 401 Unauthorized). Vérifiez que le modèle IA configuré est bien démarré.`
   - **Correction attendue** : Différencier explicitement les codes `401/403` des pannes LLM (`502/503/504`) dans le client/handler de `Mon Assistant` : sur `401`, afficher un bandeau d'erreur lisible en français métier (*« Votre session a expiré ou doit être renouvelée pour continuer la conversation. »*, zéro code HTTP brut) avec bouton d'action **`Se reconnecter →`** (et ne plus accuser le modèle IA). Vérifier la présence systématique d'un `role="alert"` accessible et contrasté (`>= 4,5:1`).
2. **`P0-UX-2` — Angle mort visuel total sur Mobile Companion (`0 / 55` PASS) et écrans `04`–`21` suite à la cascade `resetDay0()`** (`#11`–`#110`)
   - **Constat** : Impossible d'auditer visuellement le Mobile Companion authentifié (3 onglets bas, absence de débordement sur `/finops`, `/processes`, `/assistant`, modale Jour 0 mobile) ni les composants identitaires (`HumanLedAnchorCard`, `ChunkedValidationCard`, `ReviewBriefingGrid`, Studio, `Configuration`) tant que `09_reset_db_first_boot.py` échoue sur `blackboard_snapshots_step_execution_id_fkey`.
   - **Action croisée avec Winston** : Prioriser la correction du reset E2E (`Story 23.x`) puis rejouer la campagne complète pour débloquer l'audit visuel de 100 % des écrans Desktop + Mobile.

### `P1` — Majeurs (violations directes de `DESIGN.md` / `EXPERIENCE.md` ou confusion parcours Jour 0)

3. **`P1-UX-3` — Cockpit surchargé (`6` à `7` blocs au lieu de `<= 3` max) et redondances** (`#5`, `#10`)
   - **Constat** : `1303px`–`1362px` de hauteur dès le Jour 0, multipliant les cartes redondantes (`Guide de Démarrage` + `Accès rapide à Mon Assistant` + grille 3 tuiles + `Aucun Espace de Travail` + barre sans titre `Démarrer le processus` en `#10`).
   - **Correction attendue** : Appliquer strictement la règle `<= 3` blocs de `DESIGN.md` (à vide/accostage : `1.` Carte unique d'Accostage + `2.` Décisions en attente + `3.` Accès rapides consolidés), en supprimant le champ `Accès rapide à Mon Assistant` redondant et le bandeau anonyme du bas en `#10` (ou en l'intégrant dans le bloc d'accès rapides).
4. **`P1-UX-4` — Modale Jour 0 : double bouton `Annuler (Esc)`, hiérarchie CTA inversée et masque `••••••••••••••`** (`#2`, `#3`, `#4`, `#6`)
   - **Constat** : Deux boutons `Annuler (Esc)` (dont un en haut à droite à bordure noire dominante), bouton primaire `Créer le compte Administrateur` visuellement fade/secondaire, et champ `Mot de passe` affichant déjà `••••••••••••••`.
   - **Correction attendue** : Supprimer le doublon `Annuler (Esc)` (et évaluer si la modale obligatoire de Jour 0 doit être non-fermable tant qu'aucun admin n'existe, ou n'avoir qu'une croix sobre `×` / libellé français `Échap`) ; donner au CTA `Créer le compte Administrateur` un style primaire cobalt (`#2563EB`, ou désactivé clairement distingué) ; vider le masque `••••••••••••••` au profit d'un placeholder explicite ou vide.
5. **`P1-UX-5` — Zone 4 (`Aide Contextuelle`) désynchronisée de l'écran actif et tronquée en bas** (`#2`, `#5`, `#7`, `#8`, `#9`, `#10`)
   - **Constat** : Sur `/assistant`, Zone 4 affiche encore la fiche Cockpit (`ⓘ Décisions en attente et relectures : "Le Cockpit regroupe..."`) ; sur `/cockpit`, elle affiche `Les 3 modes de réponse de Mon Assistant` dont les noms divergent du sélecteur `Polyvalent · Standard` ; le bas de Zone 4 est coupé sans scroll/indicateur visible, et les 4 blocs prescrits (`EN N GESTES`, encadré ambre `UN EXEMPLE RÉEL`, `CE QUI COINCE SOUVENT`) ne sont pas rendus.
   - **Correction attendue** : Aligner strictement les sections `HelpArticle` affichées dans Zone 4 sur la route courante (`/assistant` ≠ `/cockpit`), rendre le défilement vertical de Zone 4 explicite et restaurer les 4 blocs structurés de `DESIGN.md`.
6. **`P1-UX-6` — Compteur `Accostage 0/5` incohérent et dupliqué + chevauchement Étape 2 / Étape 3** (`#5`, `#10`)
   - **Constat** : `Accostage 0/5` apparaît deux fois et reste à `0/5` alors que `Étape 1` (`Administrateur de plateforme initialisé ✓`) est validée ; `Étape 3 : Création de votre premier Espace` commence par `1. Modèles IA` (doublon de `Étape 2`) et tronque 3 items sur 5.
   - **Correction attendue** : Unifier l'affichage en un seul badge `Accostage X/5` (ou `X/6` aligné `DESIGN.md`), compter réellement la progression dès l'Étape 1, clarifier l'étape 3 sans dupliquer l'étape 2 et donner assez de largeur aux items pour éviter la troncature.
7. **`P1-UX-7` — État Jour 0 pré-admin : utilisateur fantôme `AP Administrateur de la ...`, `Notifications 4` et `Mes Espaces` actif** (`#2`, `#3`, `#4`, `#6`)
   - **Constat** : Avant même la création du premier utilisateur, la Sidebar affiche un profil `AP Administrateur de la ... Contributeur`, `TopHeaderBar` affiche `Notifications 4`, `Configuration` est absente (`7` entrées), tandis que `Mes Espaces` et `Aide` ne sont pas grisées comme le reste du menu.
   - **Correction attendue** : Ne pas afficher d'identité utilisateur ni de badge `Notifications 4` fantômes à `0` utilisateur en base ; verrouiller de manière homogène les entrées nécessitant une authentification/initialisation au Jour 0.

### `P2` — Mineurs / Polissage Microcopy, Troncatures & Contrastes

8. **`P2-UX-8` — Jargon technique résiduel dans l'UI** (`#2`, `#4`, `#7`, `#8`, `#9`)
   - **Constats** : `Modèle d'embedding sémantique requis` / `Configurer un modèle d'embedding →` (remplacer `embedding` par `indexation sémantique`) ; `Sources du guide : BASE → PACK → WORKSPACE (core)` et `@1.0.0` dans Zone 4 (masquer ou vulgariser cette plomberie interne) ; `(Esc)` au lieu de `(Échap)` ; `Assistant ORCIA (Processus standard)` (`#10`).
9. **`P2-UX-9` — Troncatures prématurées à `1440px` dans la `TopHeaderBar` et la Sidebar** (`#2`–`#10`)
   - **Constats** : Pilule `Espace : Plateforme Globale O...` / `Espace Gouvernance ...`, placeholder de recherche `... ou partout (... ⌘K`, rôle `Administrateur de la plate...`, et items d'accostage `2. Structure Organisationnel...` / `4. Sources Documentaires &...` / `5. Packs Métiers & Atelier de...`.
   - **Correction attendue** : Élargir ou simplifier les libellés (ex. raccourcir le placeholder de recherche à `Rechercher... (⌘K)` et supprimer la répétition du sélecteur `Espace` si le double sélecteur Zone 1 fait déjà office de sélecteur).
10. **`P2-UX-10` — Cohérence `TopHeaderBar` / `Zone 1` & Fil d'Ariane** (`#2`–`#10`)
    - **Constats** : Le logo cliquable `ORCIA` réside dans `Zone 2` et non en tête de `Zone 1` (`DESIGN.md` §2.1) ; le fil d'Ariane omet `Équipe / Direction` ; l'écran de chargement initial (`#1`, `Chargement de la session...`) est un texte nu sans logo ni spinner ; la mire `/login` n'affiche ni logo ORCIA ni bouton œil sur le mot de passe.
11. **`P2-UX-11` — Vérification WCAG AA des états désactivés et alertes ambre** (`#2`, `#7`, `#8`, `#9`)
    - **Constats** : Vérifier le ratio `>= 4,5:1` du texte orange/ambre sur fond beige dans l'alerte de `#7`, clarifier le contraste/infobulle des entrées de menu grisées (`Mes Processus`, `Mes Agents`) et l'état visuel du bouton d'envoi `➤` sur `#8`/`#9`.

### `P3` — Améliorations souhaitables (Confort & lisibilité)

12. **`P3-UX-12` — Capture E2E de preuve sur les écrans cibles finaux** (`#10`)
    - **Constat** : Dans `03-human-led-anchor-and-arbitration`, le test repasse par `/cockpit` avant la fin, si bien que la capture finale ne montre pas la carte violette `HumanLedAnchorCard` ni la matrice d'arbitrage (alors même que le test a validé leur fonctionnement). Ajouter ou conserver des captures intermédiaires d'étape faciliterait les futurs audits visuels de Sally sans ralentir la suite.
