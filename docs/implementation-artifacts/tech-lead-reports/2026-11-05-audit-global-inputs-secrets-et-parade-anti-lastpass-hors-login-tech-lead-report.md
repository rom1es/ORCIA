# Rapport d'Implémentation Tech Lead : Audit Global des Champs de Saisie & Secrets (`@orcia/ui` / `apps/web`) et Parade Anti-LastPass / Gestionnaires de Mots de Passe (Hors `/login`)

**Date** : 2026-11-05  
**Périmètre** : `packages/ui` (`@orcia/ui`) & `apps/web` — Audit exhaustif des 35 composants contenant des formulaires (`<form>`), champs de saisie (`<input>`) et zones de texte (`<textarea>`), neutralisation de l'injection DOM LastPass / 1Password / Bitwarden / Dashlane hors mire de connexion (`/login`), et normalisation de l'affichage des familles de modèles IA (`family-a` / `family-b`)  
**Auteurs** : Binôme **Sally** (`bmad-agent-ux-designer`, UX/UI Specialist) & **Winston** (`bmad-agent-architect`, System Architect & Tech Lead)  
**Statut** : 🟢 TERMINÉ & VÉRIFIÉ (`9/9` tâches Turbo `lint` / `typecheck` / `test` vertes, `0` finding `lint_spine.py`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Implémentation)

### 1.1 Contexte & Problématique Métier / Technique (Dialogue Sally & Winston)

Lors de la configuration d'un fournisseur de modèles IA dans **`/settings` $\rightarrow$ Modèles IA** ([`SettingsAiModelsSection.tsx`](../../../../apps/web/src/routes/SettingsAiModelsSection.tsx)), l'extension navigateur **LastPass** (ainsi que les gestionnaires de mots de passe tiers : 1Password, Bitwarden, Dashlane) injecte son icône `[...|]` à droite des champs :
1. **`2. Identifiant du modèle principal`** (`<input type="text" data-testid="llm-primary-model-input" />`) ;
2. **`Clé d'API / Jeton secret`** (`<input type="password" data-testid="llm-api-key-input" />`).

De plus, lors de la soumission du formulaire (`Enregistrer la règle de routage IA`), le navigateur et LastPass proposent d'enregistrer le couple *(Modèle principal = identifiant utilisateur, Clé d'API = mot de passe)* dans le coffre de mots de passe personnel de l'utilisateur.

Par ailleurs, dans le tableau **« Règles de routage IA enregistrées »** en bas de la même page, lorsqu'une entrée issue d'un état initial comporte `modelFamily: "family-a"` ou `"family-b"`, la colonne **Fournisseur** affiche encore la chaîne technique brute `family-a` au lieu d'un libellé métier lisible (`Fournisseur principal` / `Fournisseur secondaire`).

#### Dialogue d'Analyse entre Sally (UX/UI) et Winston (Architecte)

> **🎨 Sally (UX Designer)** :
> « Winston, regarde ce qui se passe sur l'écran *Modèles IA* (`/settings`) et potentiellement sur tous nos écrans d'administration (`Connecteurs`, `Jetons MCP`, `Accostage Jour 0`, ` Atelier de Processus`, `Mes Agents`, `Mes Espaces`) :
> 1. Dès qu'un formulaire contient un `<input type="password">` — comme `Clé d'API / Jeton secret` dans [`SettingsAiModelsSection.tsx`](../../../../apps/web/src/routes/SettingsAiModelsSection.tsx), [`SecretField.tsx`](../../../../packages/ui/src/primitives/SecretField.tsx), [`ProgressiveDay0AccostageBanner.tsx`](../../../../packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx) ou la modale d'amorçage Jour 0 dans [`ShellContainer.tsx`](../../../../apps/web/src/components/ShellContainer.tsx) — l'heuristique de LastPass scanne tout le `<form>` parent.
> 2. Elle repère le `<input type="password">`, l'assimile à un mot de passe de compte utilisateur, puis remonte dans le DOM pour trouver le `<input type="text">` précédent (`2. Identifiant du modèle principal`, ou l'URI du connecteur, ou l'identifiant technique) et le baptise *"Nom d'utilisateur"* !
> 3. Pire encore : LastPass ignore fréquemment `autocomplete="off"` dès lors que `type="password"` est présent dans le DOM, et injecte ses conteneurs flottants `div[data-lastpass-icon-root]` par-dessus nos champs Direction C.
> 4. En revanche, sur notre mire d'authentification [`/login`](../../../../apps/web/src/routes/login.tsx) ([`BiModeLoginView.tsx`](../../../../packages/ui/src/primitives/BiModeLoginView.tsx)), l'utilisateur **doit** pouvoir utiliser LastPass / 1Password / Bitwarden pour remplir son adresse e-mail professionnelle et son mot de passe local ! »

> **🏗️ Winston (System Architect)** :
> « Diagnostic 100 % exact, Sally. Pour éradiquer définitivement ce comportement sur l'ensemble d'ORCIA tout en préservant `/login`, un simple `autocomplete="off"` local ne suffit pas. Nous devons déployer une **défense en profondeur à 4 verrous complémentaires** sur **100 % des composants `.tsx`** de `packages/ui/src` et `apps/web/src` :
> 1. **Verrou 1 — Attributs explicites anti-gestionnaires de mots de passe sur tous les `<form>`, `<input>` et `<textarea>` hors `/login`** :
>    - Sur chaque `<form>` hors `/login` : `autoComplete="off" data-lpignore="true" data-form-type="other"`.
>    - Sur chaque `<input>` et `<textarea>` hors `/login` : `autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"`.
> 2. **Verrou 2 — Suppression totale de `type="password"` hors `/login` au profit de `type="text"` + masquage CSS par disques (`.orcia-masked-secret-input`)** :
>    - Les 4 champs de secrets techniques hors `/login` (`llm-api-key-input` dans `SettingsAiModelsSection.tsx`, `secret-field-write-only-input` dans `SecretField.tsx`, `welcome-setup-bootstrap-token-input` dans `ProgressiveDay0AccostageBanner.tsx`, et `first-boot-admin-password-input` dans `ShellContainer.tsx`) passent en `type="text"` avec la classe `.orcia-masked-secret-input` (`-webkit-text-security: disc; text-security: disc;` + style inline `WebkitTextSecurity: "disc"` et `spellCheck={false}`).
>    - Sans `<input type="password">` dans le DOM hors `/login`, l'heuristique de capture d'identifiants de LastPass/Chrome/Firefox/Safari ne se déclenche jamais, ni sur le secret, ni sur le champ texte précédent (`2. Identifiant du modèle principal`), ni à la soumission du formulaire.
> 3. **Verrou 3 — Neutralisation CSS globale de l'overlay DOM LastPass dans [`tokens.css`](../../../../packages/ui/src/styles/tokens.css)** :
>    - Masquage forcé (`display: none !important; visibility: hidden !important; pointer-events: none !important;`) de `div[data-lastpass-icon-root]` et `div[data-lastpass-root]` partout sauf à l'intérieur de `[data-allow-password-manager="true"]`, `[data-testid="bi-mode-login-view"]` et `[data-testid="login-page-container"]`.
> 4. **Verrou 4 — Sanctuarisation explicite de `/login` ([`BiModeLoginView.tsx`](../../../../packages/ui/src/primitives/BiModeLoginView.tsx) & [`login.tsx`](../../../../apps/web/src/routes/login.tsx))** :
>    - `data-allow-password-manager="true"` sur le conteneur de la page `/login`, la vue `BiModeLoginView` et le formulaire d'authentification locale.
>    - `autoComplete="username"` sur `login-local-email`, `type="password"` + `autoComplete="current-password"` sur `login-local-password` (sans `data-lpignore`), et `autoComplete="one-time-code"` sur `login-local-totp`. »

---

### 1.2 Analyse d'Impact GitNexus

Conformément au protocole Tech Lead ORCIA, nous avons exécuté `gitnexus_impact` (`direction: "upstream"`, `repo: "/home/romain/Documents/Projects/ORCIA"`) sur les primitives impactées :

| Symbole Cible | Fichier | `impactedCount` | Risque GitNexus | Appelants Directs (`d=1`) & Indirects (`d=2`) |
| :--- | :--- | :---: | :---: | :--- |
| `SecretField` | `packages/ui/src/primitives/SecretField.tsx` | `4` | `LOW` | `SettingsHubView` (`apps/web/src/routes/settings.tsx`), tests unitaires `epic8_primitives.test.tsx`, `i18n-and-shell.test.tsx` |
| `BiModeLoginView` | `packages/ui/src/primitives/BiModeLoginView.tsx` | `3` | `LOW` | `LoginRouteComponent` (`apps/web/src/routes/login.tsx`), tests unitaires `epic5_primitives.test.tsx`, `i18n-and-shell.test.tsx` |

Aucun contrat d'API publique (props TypeScript des composants `@orcia/ui` ou schémas OpenAPI `@orcia/api-client`) n'est cassé : les ajouts d'attributs HTML (`autoComplete`, `data-lpignore`, `data-1p-ignore`, `data-bwignore`, `data-form-type`, `className="orcia-masked-secret-input"`) sont rétrocompatibles à 100 %.

---

### 1.3 Inventaire Exhaustif des 35 Fichiers `.tsx` Audités (`packages/ui/src` & `apps/web/src`)

L'audit statique intégral de tous les fichiers `.tsx` du monorepo révèle **35 fichiers** contenant des balises `<form`, `<input`, ou `<textarea` (dont **5 occurrences** de `type="password"` dans tout le dépôt) :

#### A. Audit des 5 occurrences de `type="password"` dans le dépôt

| # | Fichier | `data-testid` | Rôle du champ | Décision Architecturale & UX |
| :-: | :--- | :--- | :--- | :--- |
| 1 | `packages/ui/src/primitives/BiModeLoginView.tsx:185` | `login-local-password` | Mot de passe de connexion de l'utilisateur sur `/login` | ✅ **CONSERVER `type="password"`** + `autoComplete="current-password"` + `data-allow-password-manager="true"` (aucun `data-lpignore`) |
| 2 | `apps/web/src/routes/SettingsAiModelsSection.tsx:455` | `llm-api-key-input` | Clé d'API / Jeton secret du fournisseur IA (`/settings`) | 🔒 **CONVERTIR en `type="text"`** + `.orcia-masked-secret-input` (`WebkitTextSecurity: "disc"`) + attributs anti-LastPass |
| 3 | `packages/ui/src/primitives/SecretField.tsx:160` | `secret-field-write-only-input` | Secret de connecteur write-only (`/settings` Connecteurs) | 🔒 **CONVERTIR en `type="text"`** + `.orcia-masked-secret-input` (`WebkitTextSecurity: "disc"`) + attributs anti-LastPass |
| 4 | `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx:188` | `welcome-setup-bootstrap-token-input` | Jeton d'amorçage technique Jour 0 (`ORCIA_BOOTSTRAP_TOKEN`) | 🔒 **CONVERTIR en `type="text"`** + `.orcia-masked-secret-input` (`WebkitTextSecurity: "disc"`) + attributs anti-LastPass |
| 5 | `apps/web/src/components/ShellContainer.tsx:406` | `first-boot-admin-password-input` | Secret d'amorçage dans la modale d'initialisation Jour 0 | 🔒 **CONVERTIR en `type="text"`** + `.orcia-masked-secret-input` (`WebkitTextSecurity: "disc"`) + attributs anti-LastPass |

#### B. Inventaire complet des 23 fichiers de `packages/ui/src`

1. [`packages/ui/src/primitives/BiModeLoginView.tsx`](../../../../packages/ui/src/primitives/BiModeLoginView.tsx) — **Exception `/login`** : ajout de `data-allow-password-manager="true"`, `autoComplete="username"` sur `login-local-email`, `type="password"` + `autoComplete="current-password"` sur `login-local-password`, `autoComplete="one-time-code"` sur `login-local-totp`.
2. [`packages/ui/src/primitives/SecretField.tsx`](../../../../packages/ui/src/primitives/SecretField.tsx) — 1 `<input>` secret write-only (`type="text"`, `.orcia-masked-secret-input`, `WebkitTextSecurity: "disc"`, attributs anti-LastPass).
3. [`packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx`](../../../../packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx) — 2 `<input>` (e-mail Jour 0 + jeton d'amorçage converti en `type="text"` masqué `.orcia-masked-secret-input`, attributs anti-LastPass).
4. [`packages/ui/src/components/AgentsAndSkillsManagerView.tsx`](../../../../packages/ui/src/components/AgentsAndSkillsManagerView.tsx) — 2 `<form>`, 10 `<input>`, 2 `<textarea>` (création et exécution d'Agents et de Compétences).
5. [`packages/ui/src/primitives/ArbitrationTieBreakCard.tsx`](../../../../packages/ui/src/primitives/ArbitrationTieBreakCard.tsx) — 1 `<input>` (justification d'arbitrage humain).
6. [`packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx`](../../../../packages/ui/src/primitives/AssistantFoldersAndCollaborativeThreadView.tsx) — 2 `<input>`, 1 `<textarea>` (notes de dossier, titre d'artefact, message collaboratif).
7. [`packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx`](../../../../packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx) — 2 `<input>`, 2 `<textarea>` (rôle métier, instructions personnelles, règles d'équipe, format de réponse).
8. [`packages/ui/src/primitives/AssistantGovernanceStudioModeB.tsx`](../../../../packages/ui/src/primitives/AssistantGovernanceStudioModeB.tsx) — 1 `<input>` (libellé de nœud du graphe Assistant).
9. [`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`](../../../../packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx) — 1 `<input>` (cible `@Agent` ou `/Skill`).
10. [`packages/ui/src/primitives/ChunkValidationCard.tsx`](../../../../packages/ui/src/primitives/ChunkValidationCard.tsx) — 1 `<input>` (motif de contestation de section).
11. [`packages/ui/src/primitives/CommandPaletteModal.tsx`](../../../../packages/ui/src/primitives/CommandPaletteModal.tsx) — 1 `<input>` (recherche palette de commandes `⌘K`).
12. [`packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx`](../../../../packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx) — 1 `<input>` (énoncé de norme métier ADN).
13. [`packages/ui/src/primitives/HumanLedAnchorCard.tsx`](../../../../packages/ui/src/primitives/HumanLedAnchorCard.tsx) — 1 `<textarea>`, 1 `<input>` (intention stratégique humaine et confirmation).
14. [`packages/ui/src/primitives/PackBuilderProcessesStudioView.tsx`](../../../../packages/ui/src/primitives/PackBuilderProcessesStudioView.tsx) — 1 `<textarea>` (cadrage humain du Pack métier).
15. [`packages/ui/src/primitives/RemoteServiceTestBenchAndMcpExposureView.tsx`](../../../../packages/ui/src/primitives/RemoteServiceTestBenchAndMcpExposureView.tsx) — 1 `<input>` (URL du service distant MCP / A2A).
16. [`packages/ui/src/primitives/ScopedPromptBox.tsx`](../../../../packages/ui/src/primitives/ScopedPromptBox.tsx) — 1 `<input>` (requête rapide Assistant).
17. [`packages/ui/src/primitives/StreamlinedCockpitView.tsx`](../../../../packages/ui/src/primitives/StreamlinedCockpitView.tsx) — 1 `<input>` (décision personnalisée d'arbitrage).
18. [`packages/ui/src/primitives/TopHeaderSearchCommand.tsx`](../../../../packages/ui/src/primitives/TopHeaderSearchCommand.tsx) — 1 `<input>` (recherche globale en-tête `⌘K`).
19. [`packages/ui/src/primitives/UpstreamChallengeRewindModal.tsx`](../../../../packages/ui/src/primitives/UpstreamChallengeRewindModal.tsx) — 1 `<textarea>` (motif de retour amont).
20. [`packages/ui/src/primitives/UserSettingsModalTabs.tsx`](../../../../packages/ui/src/primitives/UserSettingsModalTabs.tsx) — 4 `<input>` (nom complet, fuseau horaire, nom du jeton MCP, périmètre autorisé).
21. [`packages/ui/src/shell/AppShellTopbar.tsx`](../../../../packages/ui/src/shell/AppShellTopbar.tsx) — 1 `<input>` (filtre d'espace de travail).
22. [`packages/ui/src/shell/AssistantDock.tsx`](../../../../packages/ui/src/shell/AssistantDock.tsx) — 1 `<form>`, 1 `<input>` (message dock Assistant).
23. [`packages/ui/src/shell/OntologyAndKbExplorerPanel.tsx`](../../../../packages/ui/src/shell/OntologyAndKbExplorerPanel.tsx) — 1 `<input>` (recherche documentaire).

#### C. Inventaire complet des 12 fichiers de `apps/web/src`

1. [`apps/web/src/routes/login.tsx`](../../../../apps/web/src/routes/login.tsx) — **Exception `/login`** : ajout de `data-testid="login-page-container"` et `data-allow-password-manager="true"`.
2. [`apps/web/src/routes/SettingsAiModelsSection.tsx`](../../../../apps/web/src/routes/SettingsAiModelsSection.tsx) — 1 `<form>`, 5 `<input>` (`llm-custom-family-input`, `llm-primary-model-input`, `llm-fallback-model-input`, `llm-endpoint-url-input`, et `llm-api-key-input` converti en `type="text"` masqué `.orcia-masked-secret-input`) + normalisation de `family-a` / `family-b` via `formatModelFamilyDisplay()`.
3. [`apps/web/src/components/ShellContainer.tsx`](../../../../apps/web/src/components/ShellContainer.tsx) — 1 `<form>`, 3 `<input>` dans la modale d'initialisation Jour 0 (`first-boot-admin-email-input`, `first-boot-admin-name-input`, `first-boot-admin-password-input` converti en `type="text"` masqué `.orcia-masked-secret-input`).
4. [`apps/web/src/components/SimplifiedProcessBuilderSection.tsx`](../../../../apps/web/src/components/SimplifiedProcessBuilderSection.tsx) — 1 `<form>`, 4 `<input>`, 1 `<textarea>` (atelier de processus).
5. [`apps/web/src/features/cockpit/index.tsx`](../../../../apps/web/src/features/cockpit/index.tsx) — 1 `<form>`, 1 `<input>` (lancement de processus).
6. [`apps/web/src/features/ontology/index.tsx`](../../../../apps/web/src/features/ontology/index.tsx) — 1 `<form>`, 2 `<input>` (ajout de terme au glossaire métier).
7. [`apps/web/src/features/workspaces/index.tsx`](../../../../apps/web/src/features/workspaces/index.tsx) — 1 `<form>`, 2 `<input>` (création d'espace de travail).
8. [`apps/web/src/routes/SettingsIamOrganizationSection.tsx`](../../../../apps/web/src/routes/SettingsIamOrganizationSection.tsx) — 1 `<form>`, 5 `<input>` (règles d'habilitation IAM).
9. [`apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx`](../../../../apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx) — 1 `<form>`, 2 `<input>` (création d'unité d'organisation BU).
10. [`apps/web/src/routes/SettingsPacksSection.tsx`](../../../../apps/web/src/routes/SettingsPacksSection.tsx) — 1 `<form>` (activation de Pack métier).
11. [`apps/web/src/routes/SettingsSecondaryTabsSection.tsx`](../../../../apps/web/src/routes/SettingsSecondaryTabsSection.tsx) — 3 `<form>`, 8 `<input>` + normalisation de `family-a` / `family-b`.
12. [`apps/web/src/routes/wizards.tsx`](../../../../apps/web/src/routes/wizards.tsx) — 5 `<input>` (assistants de configuration guidée).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune modification de schéma SQL PostgreSQL 18 requise (les clés d'API restent hachées/chiffrées côté serveur et ne transitent jamais en clair en lecture).

### 2.2 Noyau Hexagonal & Workers Python
- Aucune modification requise dans `packages/orcia-core` ou `apps/worker`.

### 2.3 Backend FastAPI & Contrats OpenAPI
- Aucune modification des routes HTTP ou du SDK `@orcia/api-client`.

### 2.4 Design System (`@orcia/ui`) & Interface SPA (`apps/web`)
1. **CSS Global ([`packages/ui/src/styles/tokens.css`](../../../../packages/ui/src/styles/tokens.css))** :
   - Ajout de la classe `.orcia-masked-secret-input` (`-webkit-text-security: disc; text-security: disc; font-family: var(--font-mono); letter-spacing: 0.08em;`).
   - Ajout des sélecteurs de neutralisation des overlays DOM LastPass (`div[data-lastpass-icon-root]`, `div[data-lastpass-root]`) hors `[data-allow-password-manager="true"]`, `[data-testid="bi-mode-login-view"]` et `[data-testid="login-page-container"]`.
2. **Composants `@orcia/ui` (23 fichiers)** :
   - Sanctuarisation de [`BiModeLoginView.tsx`](../../../../packages/ui/src/primitives/BiModeLoginView.tsx) pour `/login` (`data-allow-password-manager="true"`, `autoComplete="username"`, `type="password"` + `autoComplete="current-password"`, `autoComplete="one-time-code"`).
   - Conversion de `SecretField.tsx` et `ProgressiveDay0AccostageBanner.tsx` en `type="text"` + `.orcia-masked-secret-input` + `WebkitTextSecurity: "disc"`.
   - Application systématique des attributs anti-LastPass/1Password/Bitwarden sur tous les `<form>`, `<input>` et `<textarea>` des 22 fichiers hors `/login`.
3. **Écrans & Composants `apps/web` (12 fichiers)** :
   - Sanctuarisation de [`apps/web/src/routes/login.tsx`](../../../../apps/web/src/routes/login.tsx) (`data-testid="login-page-container" data-allow-password-manager="true"`).
   - Conversion de `llm-api-key-input` dans [`SettingsAiModelsSection.tsx`](../../../../apps/web/src/routes/SettingsAiModelsSection.tsx) et de `first-boot-admin-password-input` dans [`ShellContainer.tsx`](../../../../apps/web/src/components/ShellContainer.tsx) en `type="text"` + `.orcia-masked-secret-input` + `WebkitTextSecurity: "disc"`.
   - Normalisation de l'affichage de `modelFamily` (`"family-a"` $\rightarrow$ `"Fournisseur principal"` / `"Primary provider"`, `"family-b"` $\rightarrow$ `"Fournisseur secondaire"` / `"Secondary provider"`) dans `SettingsAiModelsSection.tsx` et `SettingsSecondaryTabsSection.tsx`.
   - Application systématique des attributs anti-LastPass/1Password/Bitwarden sur tous les `<form>`, `<input>` et `<textarea>` des 11 fichiers hors `/login`.
4. **Tests Automatisés de Non-Régression ([`apps/web/src/__tests__/i18n-and-shell.test.tsx`](../../../../apps/web/src/__tests__/i18n-and-shell.test.tsx))** :
   - Test d'audit statique AST/source scannant 100 % des fichiers `.tsx` de `packages/ui/src` et `apps/web/src` pour garantir :
     - `0` occurrence de `type="password"` hors `BiModeLoginView.tsx` ;
     - présence de `data-lpignore="true"` et `autoComplete="off"` sur chaque `<input`, `<textarea` et `<form` hors `BiModeLoginView.tsx`.
   - Tests DOM sur `/settings` (`Modèles IA`), `/login` (`BiModeLoginView`) et la normalisation de `family-a`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Modifiés (`37` fichiers)

| Domaine / Package | Fichier | Nature des Modifications |
| :--- | :--- | :--- |
| **`@orcia/ui` Styles** | `packages/ui/src/styles/tokens.css` | Ajout de `.orcia-masked-secret-input` (`-webkit-text-security: disc; text-security: disc;`) et neutralisation CSS globale de `div[data-lastpass-icon-root]` / `div[data-lastpass-root]` hors `/login` (`[data-allow-password-manager="true"]`). |
| **`@orcia/ui` Login** | `packages/ui/src/primitives/BiModeLoginView.tsx` | Sanctuarisation de `/login` : `data-allow-password-manager="true"` sur la section, le formulaire et les champs, `autoComplete="username"` sur l'e-mail, `type="password"` + `autoComplete="current-password"` sur le mot de passe, `autoComplete="one-time-code"` sur le TOTP. |
| **`@orcia/ui` Secrets** | `packages/ui/src/primitives/SecretField.tsx` | Conversion de `secret-field-write-only-input` de `type="password"` vers `type="text"` avec `.orcia-masked-secret-input`, `WebkitTextSecurity: "disc"`, `spellCheck={false}` et attributs anti-LastPass/1Password/Bitwarden. |
| **`@orcia/ui` Jour 0** | `packages/ui/src/primitives/ProgressiveDay0AccostageBanner.tsx` | Conversion de `welcome-setup-bootstrap-token-input` vers `type="text"` + `.orcia-masked-secret-input` + `WebkitTextSecurity: "disc"` et attributs anti-LastPass sur les 2 champs. |
| **`@orcia/ui` Composants & Primitives (20 fichiers)** | `AgentsAndSkillsManagerView.tsx`, `ArbitrationTieBreakCard.tsx`, `AssistantFoldersAndCollaborativeThreadView.tsx`, `AssistantGovernanceModalAndStudio.tsx`, `AssistantGovernanceStudioModeB.tsx`, `AssistantSpeedSelectorAndStreamView.tsx`, `ChunkValidationCard.tsx`, `CommandPaletteModal.tsx`, `DnaStarlarkCompilerAndGlossaryLifecycleView.tsx`, `HumanLedAnchorCard.tsx`, `PackBuilderProcessesStudioView.tsx`, `RemoteServiceTestBenchAndMcpExposureView.tsx`, `ScopedPromptBox.tsx`, `StreamlinedCockpitView.tsx`, `TopHeaderSearchCommand.tsx`, `UpstreamChallengeRewindModal.tsx`, `UserSettingsModalTabs.tsx`, `AppShellTopbar.tsx`, `AssistantDock.tsx`, `OntologyAndKbExplorerPanel.tsx` | Ajout systématique de `autoComplete="off" data-lpignore="true" data-form-type="other"` sur tous les `<form>` et de `autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"` sur tous les `<input>` et `<textarea>`. |
| **`apps/web` Login** | `apps/web/src/routes/login.tsx` | Ajout de `data-testid="login-page-container"` et `data-allow-password-manager="true"` sur le conteneur de la route `/login`. |
| **`apps/web` Modèles IA** | `apps/web/src/routes/SettingsAiModelsSection.tsx` & `SettingsSecondaryTabsSection.tsx` | Conversion de `llm-api-key-input` vers `type="text"` + `.orcia-masked-secret-input` (`WebkitTextSecurity: "disc"`), attributs anti-LastPass sur le `<form>` et les 5 `<input>` (notamment `2. Identifiant du modèle principal`), et normalisation de `family-a` / `family-b` en `Fournisseur principal` / `Fournisseur secondaire` (`Primary provider` / `Secondary provider` en EN). |
| **`apps/web` Jour 0** | `apps/web/src/components/ShellContainer.tsx` | Conversion de `first-boot-admin-password-input` vers `type="text"` + `.orcia-masked-secret-input` (`WebkitTextSecurity: "disc"`) et attributs anti-LastPass sur le `<form>` et les 3 `<input>`. |
| **`apps/web` Écrans & Routes (8 fichiers)** | `SimplifiedProcessBuilderSection.tsx`, `features/cockpit/index.tsx`, `features/ontology/index.tsx`, `features/workspaces/index.tsx`, `routes/SettingsIamOrganizationSection.tsx`, `routes/SettingsOrganizationUnitsBlock.tsx`, `routes/SettingsPacksSection.tsx`, `routes/wizards.tsx` | Ajout systématique des attributs anti-LastPass/1Password/Bitwarden sur tous les `<form>`, `<input>` et `<textarea>`. |
| **Tests Automatisés** | `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Ajout du test d'audit statique couvrant 100 % des fichiers `.tsx` de `packages/ui/src` et `apps/web/src` + tests DOM sur `/settings` (`Modèles IA`), normalisation de `family-a`, et préservation de `/login`. |

---

### 3.2 Métriques Chiffrées & Validation des Gates

- **Occurrences de `type="password"` hors `BiModeLoginView.tsx` (`/login`)** : **`0`** (contre `4` auparavant).
- **Balises auditées et protégées hors `/login`** :
  - $\ge 14$ formulaires `<form>` (`autoComplete="off" data-lpignore="true" data-form-type="other"`) ;
  - $\ge 65$ champs `<input>` (`autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"`) ;
  - $\ge 8$ zones `<textarea>` (`autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"`).
- **Exécution des Gates CI** :
  - `pnpm turbo run lint typecheck test` : **`9/9` tâches réussies** (`@orcia/api-client`, `@orcia/ui`, `@orcia/web`), `21/21` suites de tests `i18n-and-shell.test.tsx` vertes.
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **`All checks passed! 518 files already formatted`**.
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py` : **`{"ok": true, "total_findings": 0}`**.
  - `gitnexus_detect_changes` : **`risk_level: "none"`**, aucune rupture de contrat inter-modules.

