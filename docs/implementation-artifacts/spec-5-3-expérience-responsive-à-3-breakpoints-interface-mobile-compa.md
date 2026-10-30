# Spécification Technique — Story 5.3 (`5-3-expérience-responsive-à-3-breakpoints-interface-mobile-compa`)

## 1. Périmètre & Exigences Couvertes
- **User Story** : `5-3-expérience-responsive-à-3-breakpoints-interface-mobile-compa`
- **Exigences fonctionnelles & architecturales** : `UX-DR16`, `NFR-A11Y-1`, `NFR-TEST-1`, `AD-17`.
- **Composants livrés** :
  1. **Système Responsive 3 Breakpoints (`packages/ui/src/primitives/MobileCompanionView.tsx`)** :
     - **Desktop (`>= 1280px`)** : 3-column Bento layout complet.
     - **Laptop (`768px - 1279px`)** : 2-column layout adaptatif.
     - **Mobile Companion (`< 768px`, ex. `390x844`)** : vue mono-colonne pilotée par une barre d'onglets basse à 3 entrées :
       - `🔔 Inbox` (tri & prise en charge atomique *Claim* des notifications)
       - `💬 Arbitrage/Chat` (résolution d'arbitrage humain & interaction avec l'Agent Assistant)
       - `📄 Briefing` (lecture du Briefing de Revue en 4 blocs & approbation granulaire par découpage)
  2. **Restriction Explicite des Fonctionnalités Desktop-Only sur Mobile (`UX-DR16`)** :
     - Blocage explicite de l'édition de manifestes YAML *Workflow-as-Code*, de la co-édition lourde d'artefacts multi-pages et du module *7. Administration* sur viewport `< 768px`, affichant la bannière dédiée *"Fonctionnalité réservée au poste Desktop"*.
  3. **Conformité Accessibilité WCAG 2.2 AA (`NFR-A11Y-1`)** :
     - Badges sémantiques multi-signaux (**Couleur sémantique + Icône dédiée + Libellé textuel explicite** : `✍️ Ancrage Humain`, `⚖️ Arbitrage IA`, `🛡️ Gate`, `🚨 Obsolète`).
     - Annonces temps réel via régions `aria-live="polite"` pour les notifications, *Claims* SSE et streaming de l'Agent Assistant.
