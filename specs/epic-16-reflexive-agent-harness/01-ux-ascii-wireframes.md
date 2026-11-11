---
document_type: UX_SPECIFICATION_AND_ASCII_WIREFRAMES
epic_id: EPIC-16
version: "2.1.0"
target_app: "packages/ui (@orcia/ui — Radix UI, OrciaIcon, tokens.css) & apps/web (React 19, TanStack Router)"
---

# Spécifications UX/UI & Maquettes ASCII (v2.1) — Trace Réflexive Unifiée & Choix Métier « Objectif vs Jalons »

Conformément aux décisions verrouillées avec **Sally (`🎨`)** et **Winston (`🏗️`)** :
1. **Zéro terme technique** dans l'UI, les badges et l'aide contextuelle (`0` mention de `DBOS`, `asyncio`, `SQL`, `Redis`, `SSE`, `Claim-Check`, `déterministe`, `non-déterministe`).
2. **Aucun bandeau moteur parasite** dans `Mon Assistant` ; conservation exclusive des **2 modes** `Standard` et `Approfondi`.
3. **Composants visuels purs dans `packages/ui`** (`<AgentExecutionTrace />` et `<SourceLineInspectorDrawer />`), icônes centralisées `<OrciaIcon />`, fermeture `Échap` RGAA, et substitution propre dans le Shell 4 Zones sans écraser la colonne centrale.
4. **Séparation explicite** entre **`■`** (*Arrêter immédiatement*) dans la barre de saisie et **`[Synthétiser maintenant]`** dans le pied de la trace active.

---

## ÉCRAN 1 : « Mon Assistant » (`/assistant`) — Trace Unifiée Repliable & Tiroir d'Inspection de Lignes

```text
+----------------------------------------------------------------------------------------------------------------------+
| [ORCIA]  Espace : [ 📦 Espace · Mon Compte v ]                                                     [🔎 ⌘K] [❓] [👤] |
+----------------------------------------------------------------------------------------------------------------------+
| [≡] |  CONVERSATION ACTIVE                                                        | 📄 EXTRAIT DE SOURCE             |
|     |-----------------------------------------------------------------------------|----------------------------------|
|  🏠 |  +-----------------------------------------------------------------------+  | capabilities.yaml          [✕]   |
| >💬 |  | Prépare l'analyse d'impact et vérifie le registre des capacités       |  | Référentiel : crl-back           |
|  📦 |  +-----------------------------------------------------------------------+  | Lignes inspectées : #L200-561    |
|  🤖 |                                                                             |----------------------------------|
|  ☍  |  Vérification des sources et du registre des capacités ⌄                    |  199 |     max_attempts: 3       |
|  🛡️ |    Réflexion pendant 13 s ›                                                 | >200 | capabilities:             |
|  ⚙️ |    Vérification : état du dépôt et branche active ›                         | >201 |   revocation_check:       |
|  ❓ |    Analysé · [M↓] TECH-LEAD-REPORT-TEMPLATE.md #L1-101                      | >202 |     mode: strict_crl      |
|     |    Analysé · [Y]  capabilities.yaml #L1-200                                 | >203 |     timeout_ms: 1500      |
|     |    Analysé · [Y]  capabilities.yaml #L200-561  ◄── [Cliqué : ouvert]        |  ... | ...                       |
|     |    Réflexion pendant 7 s ›                                                  | >560 |     append_only: true     |
|     |    ◌ Analyse en cours…                        [Synthétiser maintenant]      | >561 |     hash_algo: sha256     |
|     |-----------------------------------------------------------------------------|----------------------------------|
|     | [Approfondi ▾] [ @Agent ] [ /Compétence ]                                   | [Copier l'extrait #L200-561]     |
|     | [ Posez une question ou demandez une action…                          ] [■] | [Ouvrir la source d'origine]     |
+----------------------------------------------------------------------------------------------------------------------+
```

---

## ÉCRAN 2 : Atelier `Mes Processus` (`/processes/studio/$workflowId`) — Architecture 5 Blocs Conservée

Les Blocs 1, 3, 4 et 5 restent invariants ; le sélecteur de pilotage adapte le **Bloc 2** sans perte de saisie en brouillon :

```text
+----------------------------------------------------------------------------------------------------------------------+
| [ORCIA]  Atelier de Processus · Audit et mise à jour documentaire                         Statut : [En préparation]  |
+----------------------------------------------------------------------------------------------------------------------+
|  COMMENT SOUHAITEZ-VOUS PILOTER CE PROCESSUS ?                                                                       |
|  +========================================================+ +------------------------------------------------------+ |
|  | (●) Processus piloté par l'objectif (adaptatif)        | | ( ) Processus piloté par les jalons (étapes garant.) | |
|  | Vous fixez le résultat attendu et les agents           | | Vous fixez l'ordre précis des étapes, les validations| |
|  | mobilisables ; l'enchaînement des recherches s'adapte  | | humaines attendues et les boucles de reprise sur     | |
|  | aux éléments découverts.                               | | toute la durée du dossier.                           | |
|  +========================================================+ +------------------------------------------------------+ |
|                                                                                                                      |
|  BLOC 1 · ENTRÉES & CONTRAT DE SORTIE (Sections attendues)                                                           |
|  BLOC 2 · OBJECTIF CONFIÉ & ÉQUIPE D'AGENTS MOBILISABLES :                                                           |
|    • Objectif métier * : [ Inspecter les évolutions récentes, détecter les écarts avec la documentation et...     ]  |
|    • Agents mobilisables : [@CRL-Étude-Architecture ×] [@Rédacteur-Documentation-Orcia ×] [+ Ajouter un agent]       |
|  BLOC 3 · OUTILS & COMPÉTENCES AUTORISÉS                                                                             |
|  BLOC 4 · CONTRÔLES QUALITÉ AUTOMATIQUES & CONTRADICTOIRES                                                           |
|  BLOC 5 · VALIDATION HUMAINE & CONFIRMATION AVANT ÉCRITURE EXTERNE                                                   |
+----------------------------------------------------------------------------------------------------------------------+
```
