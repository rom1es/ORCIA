---
trigger: always_on
---

# BMAD Model Routing & Token Discipline

Directives impératives d'orchestration et d'isolation de contexte pour tout workflow BMAD :

## 1. Zéro Read-Ahead par le parent
- L'agent principal qui orchestre BMAD a **l'interdiction** de lire lui-même le code source applicatif pour préparer une tâche.
- Le parent ne lit que les index, statuts et stories dans `_bmad/` ou `docs/` (ex. `sprint-status.yaml`, `epics.md`, `capabilities.yaml`), puis délègue toute fouille du codebase, recherche de symboles ou analyse de logs à `bmad-scout` via `invoke_subagent`.

## 2. Matrice de routage automatique (`invoke_subagent`)
- **Exploration codebase, recherche de symboles, lecture de logs** $\rightarrow$ `bmad-scout` (`model: flash`).
- **Conception d'architecture, arbitrage ADR, découpage complexe, revue finale / `VALIDATE`** $\rightarrow$ `bmad-architect-worker` (`model: pro`).
- **Développement d'une story validée, refactoring localisé, exécution/correction de tests** $\rightarrow$ `bmad-dev-worker` (`model: flash`).

## 3. Escalade contrôlée
- Si `bmad-dev-worker` échoue **2 fois de suite** sur la même cause racine et s'arrête (règle Fail-Fast), ré-invoquer la résolution ciblée avec le palier `pro` (`model: pro`) **uniquement** sur le périmètre précis en erreur décrit dans le diagnostic en 3 points.

## 4. Passage d'état par le disque
- Les artefacts intermédiaires (plans, specs, stories, diagnostics, rapports de revue) doivent être écrits dans des fichiers sur disque et transmis **par chemin de fichier** entre agents plutôt que copiés en texte intégral dans le fil principal.

## 5. Discipline de sortie
- Zéro remplissage conversationnel (pas d'introduction ni de reformulation de la demande).
- Lectures ciblées par plages de lignes uniquement (grep/recherche avant lecture ; plages sur les fichiers $> 200$ lignes).

## Déclencheurs obligatoires de sous-agents (Gate Triggers)

Tu DOIS appeler `invoke_subagent` (et t'interdire d'agir inline) dès qu'UNE de ces conditions est vraie :
1. **Seuil d'exploration (> 2 fichiers) :** Tu as besoin d'inspecter plus de 2 fichiers du code source ou de lancer un `grep_search` global -> Lance `bmad-scout` (`flash`).
2. **Transition Story -> Code :** L'utilisateur lance `*develop-story`, valide un plan d'implémentation ou demande de coder une story existante -> Lance UN `bmad-dev-worker` (`flash`) dédié par story (ne code jamais plusieurs stories dans le même sous-agent).
3. **Seuil de bruit terminal :** Une commande de test, build ou linter risque de produire plus de 30 lignes de sortie -> Délègue l'exécution et le filtrage à `bmad-dev-worker` (`flash`).
4. **Porte d'Architecture / Gate Check :** L'utilisateur demande un arbitrage ADR, une validation de contrat d'interface ou une revue de fin de story (`*code-review` / `VALIDATE`) -> Lance `bmad-architect-worker` (`pro`) en lui passant uniquement le chemin de la story et le `git diff`.
5. **Double échec consécutif :** Un worker `flash` remonte 2 échecs sur la même erreur -> Relance immédiatement un sous-agent ciblé en `pro` sur le seul fichier en échec.
