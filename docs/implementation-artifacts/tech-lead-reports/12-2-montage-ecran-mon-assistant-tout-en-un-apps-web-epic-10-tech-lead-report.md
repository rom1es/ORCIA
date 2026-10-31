# Rapport d'Analyse & Plan d'Implémentation Tech Lead — `Story 12.2` : Montage de l'Écran « Mon Assistant » Tout-en-Un dans `apps/web` (`Epic 10` : 3 Vitesses, Dossiers `📁`, Citations `[S1]/[G1]/[O1]` & Gouvernance 4 Niveaux)

- **Clé de la Story** : `12-2-montage-ecran-mon-assistant-tout-en-un-apps-web-epic-10`
- **Epic** : `Epic 12` — Intégration Bout-en-Bout du Portail SPA (`apps/web`)
- **Date** : `2026-10-31`
- **Auteur** : Agent Tech Lead / Dev Senior (Antigravity)
- **Statut** : `done`
- **Références Architecture & UX** : `AD-6`, `AD-10`, `AD-15`, `FR-5`, `UX-DR6`, `draft-ux-principes-et-architecture-2026-10-30.md` (Section 2 — `Mon Assistant`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Avant Codage)

### 1.1 Contexte & Problématique Métier / Technique
Lorsqu'un utilisateur clique sur l'entrée `💬 Mon Assistant` (`/assistant`) de la coquille 4 zones Direction C (`FourZoneDirectionCShell`), le portail `apps/web` rend `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`). Jusqu'à présent, ce panneau n'affichait que la boîte de notifications de runs (`inbox-feature-panel`) sans monter les 4 briques de l'écran « Mon Assistant » Tout-en-Un livrées dans `@orcia/ui` au cours de l'Epic 10 :
1. **`AssistantFoldersAndCollaborativeThreadView`** (Story 10.4) : Barre à 3 onglets (`💬 Discussion active`, `📁 Dossiers (N)`, `🕘 Historique & Recherche`), continuité mémoire Couche 5 (`📌 Notes du dossier`), passerelle `☍ Lancer un Processus à partir de ce dossier →`, partage collaboratif (`🔒 Privé | 👥 Partagé | 📦 Espace`) et bandeau de verrou de tour Redis (`✍️ {Prénom} interroge l'assistant...`).
2. **`AssistantSpeedSelectorAndStreamView`** (Story 10.2) : Sélecteur conversationnel à 3 vitesses (`⚡ Rapide`, `@Agent / /Skill`, `🧠 Approfondi`), cache Redis 5 couches (`TTL 300s`, `< 5 ms`) et journal de progression temps réel (`TTFT < 1.2s`).
3. **`AssistantCitationPillsAndArtifactCard`** (Story 10.3) : Pastilles de citation déterministes (`[S1]`, `[G1]`, `[O1]`), filtrage dynamique `READ_SOURCE` (`🔒 Source restreinte — Demander l'accès`) et carte d'artefact structurée protégée par le Verrou V5 (`AD-15`).
4. **`AssistantGovernanceModalAndStudio`** (Story 10.1) : Modale Mode A à 3 onglets (`👤 Mes préférences`, `📦 Réglages de l'Espace`, `👁️ Assemblage complet`) et Studio Graphique Mode B sous les bornes immuables `🔒 AssistantHarness` (`AD-15`).

### 1.2 Analyse d'Impact GitNexus (Symboles, Appels & Risques)
- **Requête `gitnexus_impact` (`InboxFeaturePanel`, `direction: "upstream"`)** :
  - Appelant direct : `ModuleWorkspaceView` (`apps/web/src/components/ModuleWorkspaceView.tsx`) lorsque `moduleKey === "inbox"` (routes `/assistant` et `/inbox`).
  - Les tests existants dans `apps/web/src/__tests__/i18n-and-shell.test.tsx` vérifient `inbox-feature-panel`, `inbox-amber-counter`, `inbox-uri-badge`, `inbox-filter-*`, `inbox-empty-state` et `inbox-go-cockpit-btn`. Nous préservons 100 % de ces `data-testid` tout en montant l'écran complet « Mon Assistant » Tout-en-Un.

### 1.3 Opportunités de Factorisation & Contrôle de Volumétrie (< 350 Lignes)
- Extension de [`apps/web/src/i18n/locales/epic10_labels.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/i18n/locales/epic10_labels.ts) avec `assistantSpeedStream`, `assistantCitations` et `assistantFolders` (parité récursive 100 % FR/EN).
- Montage modulaire dans [`apps/web/src/features/inbox/index.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/index.tsx) (`< 300` lignes, zéro couleur hexadécimale, zéro import inter-feature).

---

## 2. Plan d'Implémentation

### 2.1 Dictionnaire i18n Bilingue (`apps/web/src/i18n/locales/epic10_labels.ts`)
- Ajout des sections typées `assistantSpeedStream` (`AssistantSpeedSelectorAndStreamViewLabels`), `assistantCitations` (`AssistantCitationPillsAndArtifactCardLabels`) et `assistantFolders` (`AssistantFoldersAndCollaborativeThreadViewLabels`) dans `EPIC10_FR_LABELS` et `EPIC10_EN_LABELS`.

### 2.2 Montage de `Mon Assistant` Tout-en-Un (`apps/web/src/features/inbox/index.tsx`)
- Intégration interactive des 4 primitives `@orcia/ui` :
  - `AssistantFoldersAndCollaborativeThreadView` (navigation dossiers `📁`, édition des notes épinglées Couche 5, partage `PRIVATE | SHARED_SELECTED | WORKSPACE_OPEN`, passerelle vers `/processes`),
  - `AssistantSpeedSelectorAndStreamView` (bascule `⚡ Rapide` / `@Agent` / `🧠 Approfondi`, envoi de prompt mettant à jour la réponse citée),
  - `AssistantCitationPillsAndArtifactCard` (sources `[S1]` ouverte et `[S2]` restreinte `READ_SOURCE=false`, glossaire `[G1]`, outil `[O1]`, carte d'artefact Verrou V5 avec passerelle vers `/processes`),
  - Bouton `⚙ Réglages de l'assistant (4 niveaux)` permettant d'afficher/masquer `AssistantGovernanceModalAndStudio` (Mode A 3 onglets + Mode B Studio Graphique sous bornes `🔒 AssistantHarness`).

---

## 3. Bilan des Modifications & Résultats (Après Implémentation)

### 3.1 Fichiers Créés ou Modifiés
| Fichier | Nature | Rôle |
|---|---|---|
| `apps/web/src/i18n/locales/epic10_labels.ts` | Modifié | Dictionnaires bilingues FR/EN pour les 4 briques de l'Epic 10 |
| `apps/web/src/features/inbox/index.tsx` | Modifié | Montage de l'écran « Mon Assistant » Tout-en-Un (`/assistant` & `/inbox`) |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modifié | Test d'intégration Vitest vérifiant le rendu et les interactions de `Mon Assistant` (`/assistant`) |

### 3.2 Validation des Couches de Tests (`AD-17`) & Qualité
- **Parité i18n FR/EN** : `100 %` (`collectNestedKeys`).
- **Zéro couleur hexadécimale & Isolation Feature-Sliced (`M11`, `AD-19`)** : `PASS`.
- **Suite `@orcia/ui` & `@orcia/web`** : `pnpm turbo run lint typecheck test` `0` erreur.
