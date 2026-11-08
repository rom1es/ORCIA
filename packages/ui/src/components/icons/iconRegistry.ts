import type { EightFixedMenuKey } from "../../primitives/FourZoneDirectionCShell";
import type { UiModuleKey, UiScopeLevel } from "../../shell/types";

export type OrciaIconCategory =
  | "navigation"
  | "action"
  | "status"
  | "chevron"
  | "scope"
  | "assistant"
  | "governance";

export type OrciaIconName =
  | "cockpit"
  | "assistant"
  | "processes"
  | "agents"
  | "spaces"
  | "finops"
  | "activity"
  | "configuration"
  | "help"
  | "vocabulary"
  | "home"
  | "dna"
  | "rocket"
  | "brandLogo"
  | "search"
  | "notifications"
  | "user"
  | "close"
  | "check"
  | "checkFilled"
  | "cross"
  | "crossFilled"
  | "warning"
  | "alertBadge"
  | "infoBadge"
  | "infoSymbol"
  | "chevronDown"
  | "chevronRight"
  | "caretDown"
  | "caretRight"
  | "play"
  | "playOutline"
  | "stopSquare"
  | "stopButton"
  | "regenerate"
  | "restore"
  | "rollback"
  | "copy"
  | "like"
  | "dislike"
  | "moreHorizontal"
  | "externalLink"
  | "arrowDown"
  | "arrowUp"
  | "hourglass"
  | "folder"
  | "pin"
  | "laptop"
  | "workspaceFolder"
  | "document"
  | "globe"
  | "organizationBu"
  | "divisionBuilding"
  | "team"
  | "lock"
  | "keyLock"
  | "pack"
  | "tools"
  | "brain"
  | "sparkles"
  | "target"
  | "lightning"
  | "shield"
  | "scale"
  | "pen"
  | "eye"
  | "clock"
  | "locationPin"
  | "sun"
  | "moon"
  | "plug"
  | "compass"
  | "desktop"
  | "statusHealthy"
  | "statusWarning"
  | "statusError"
  | "plus"
  | "minus"
  | "times"
  | "money"
  | "moneyBag"
  | "book"
  | "bookOpen"
  | "books"
  | "lightbulb"
  | "arrowLeft"
  | "arrowRight"
  | "thumbUp"
  | "thumbDown"
  | "undo"
  | "promoteUp"
  | "divisionLandmark"
  | "menuAssistant"
  | "menuProcesses"
  | "menuActivity"
  | "cmdkShortcut"
  | "bulletDot";

export interface OrciaIconDefinition {
  glyph: string;
  readonly category: OrciaIconCategory;
  readonly description: string;
}

/**
 * Single Source of Truth for all UI icons across `@orcia/ui` and consuming web views.
 * Modifying any `glyph` entry in `ORCIA_ICONS` immediately updates every
 * component, button, menu entry, badge, and header that consumes it.
 */
export const ORCIA_ICONS: Record<OrciaIconName, OrciaIconDefinition> = {
  cockpit: { glyph: "◈", category: "navigation", description: "Cockpit Direction C" },
  assistant: { glyph: "💬", category: "navigation", description: "Mon Assistant & Discussion" },
  processes: { glyph: "☍", category: "navigation", description: "Mes Processus & Workflows" },
  agents: { glyph: "🤖", category: "navigation", description: "Agents IA" },
  spaces: { glyph: "📦", category: "navigation", description: "Espaces & Packs Métiers" },
  finops: { glyph: "📊", category: "navigation", description: "Coûts FinOps & Métriques" },
  activity: { glyph: "📜", category: "navigation", description: "Journal d'Activité" },
  configuration: { glyph: "⚙", category: "navigation", description: "Configuration & Réglages" },
  help: { glyph: "❓", category: "navigation", description: "Aide Contextuelle" },
  vocabulary: { glyph: "📖", category: "navigation", description: "Vocabulaire & Glossaire" },
  home: { glyph: "🏠", category: "navigation", description: "Accueil Cockpit" },
  dna: { glyph: "🧬", category: "navigation", description: "Ontologie & ADN Métier" },
  rocket: { glyph: "🚀", category: "navigation", description: "Amorçage & Déploiement" },
  brandLogo: { glyph: "❖", category: "navigation", description: "Emblème ORCIA" },
  search: { glyph: "🔍", category: "action", description: "Recherche globale" },
  notifications: { glyph: "🔔", category: "navigation", description: "Centre de notifications" },
  user: { glyph: "👤", category: "navigation", description: "Profil utilisateur" },
  close: { glyph: "✕", category: "action", description: "Fermer / Écarter" },
  check: { glyph: "✓", category: "status", description: "Validé / Actif" },
  checkFilled: { glyph: "✅", category: "status", description: "Succès confirmé" },
  cross: { glyph: "✗", category: "status", description: "Rejeté / Invalide" },
  crossFilled: { glyph: "❌", category: "status", description: "Échec critique" },
  warning: { glyph: "⚠️", category: "status", description: "Avertissement" },
  alertBadge: { glyph: "!", category: "status", description: "Indicateur de prérequis sur bouton désactivé" },
  infoBadge: { glyph: "i", category: "action", description: "Déclencheur d'aide contextuelle" },
  infoSymbol: { glyph: "ⓘ", category: "action", description: "Symbole d'aide contextuelle" },
  chevronDown: { glyph: "⌄", category: "chevron", description: "Déplier / Menu déroulant" },
  chevronRight: { glyph: "›", category: "chevron", description: "Étape repliée / Chemin" },
  caretDown: { glyph: "▾", category: "chevron", description: "Accordéon ouvert / Sélecteur" },
  caretRight: { glyph: "▸", category: "chevron", description: "Accordéon fermé / Sous-menu" },
  play: { glyph: "▶", category: "action", description: "Envoyer / Exécuter" },
  playOutline: { glyph: "▷", category: "action", description: "Tester à blanc (Dry-run)" },
  stopSquare: { glyph: "■", category: "action", description: "Arrêter la génération" },
  stopButton: { glyph: "⏹", category: "status", description: "Génération interrompue" },
  regenerate: { glyph: "↻", category: "action", description: "Régénérer / Actualiser" },
  restore: { glyph: "↺", category: "action", description: "Restaurer la configuration par défaut" },
  rollback: { glyph: "⏪", category: "action", description: "Version précédente / Challenge amont" },
  copy: { glyph: "📋", category: "action", description: "Copier dans le presse-papiers" },
  like: { glyph: "👍", category: "assistant", description: "Bonne réponse" },
  dislike: { glyph: "👎", category: "assistant", description: "Réponse à améliorer" },
  moreHorizontal: { glyph: "⋯", category: "action", description: "Plus d'options / Détails" },
  externalLink: { glyph: "↗", category: "action", description: "Ouvrir le lien externe" },
  arrowDown: { glyph: "↓", category: "action", description: "Défiler vers le bas" },
  arrowUp: { glyph: "⬆️", category: "action", description: "Promouvoir au niveau supérieur" },
  hourglass: { glyph: "⏳", category: "status", description: "Exécution en cours" },
  folder: { glyph: "📁", category: "assistant", description: "Dossier thématique" },
  pin: { glyph: "📌", category: "assistant", description: "Note permanente épinglée" },
  laptop: { glyph: "💻", category: "assistant", description: "Poste local / IDE MCP" },
  workspaceFolder: { glyph: "🗂️", category: "scope", description: "Espace de travail / Dossier ORCIA" },
  document: { glyph: "📄", category: "assistant", description: "Document / Brouillon" },
  globe: { glyph: "🌐", category: "scope", description: "Portée Globale / Site Vitrine" },
  organizationBu: { glyph: "🏢", category: "scope", description: "Entreprise / Direction (BU)" },
  divisionBuilding: { glyph: "🏛️", category: "scope", description: "Direction / Division" },
  team: { glyph: "👥", category: "scope", description: "Équipe & Membres" },
  lock: { glyph: "🔒", category: "governance", description: "Privé / Verrouillé" },
  keyLock: { glyph: "🔐", category: "governance", description: "Authentification SSO / Sécurité" },
  pack: { glyph: "📦", category: "scope", description: "Pack Métier" },
  tools: { glyph: "🛠️", category: "assistant", description: "Compétence / Outils" },
  brain: { glyph: "🧠", category: "assistant", description: "Niveau de réflexion" },
  sparkles: { glyph: "✨", category: "assistant", description: "Audit IA / Recherche sémantique" },
  target: { glyph: "🎯", category: "governance", description: "Objectif / Focus Espace" },
  lightning: { glyph: "⚡", category: "action", description: "Action rapide / Exécution directe" },
  shield: { glyph: "🛡️", category: "governance", description: "Gouvernance / Gate de sécurité" },
  scale: { glyph: "⚖️", category: "governance", description: "Arbitrage humain" },
  pen: { glyph: "✍️", category: "governance", description: "Ancrage humain / Co-édition" },
  eye: { glyph: "👁️", category: "governance", description: "Mode Observateur (Lecture seule)" },
  clock: { glyph: "🕒", category: "status", description: "Horodatage / Historique" },
  locationPin: { glyph: "📍", category: "scope", description: "Périmètre d'exécution" },
  sun: { glyph: "☀️", category: "action", description: "Thème clair" },
  moon: { glyph: "🌙", category: "action", description: "Thème sombre" },
  plug: { glyph: "🔌", category: "action", description: "Connecteur / Test de connexion" },
  compass: { glyph: "🧭", category: "navigation", description: "Tiroir de guidage" },
  desktop: { glyph: "🖥️", category: "navigation", description: "Vue Bureau complète" },
  statusHealthy: { glyph: "🟢", category: "status", description: "Service opérationnel" },
  statusWarning: { glyph: "🟡", category: "status", description: "Alerte modérée" },
  statusError: { glyph: "🔴", category: "status", description: "Service en erreur" },
  plus: { glyph: "+", category: "action", description: "Ajouter / Ouvrir le menu plus" },
  minus: { glyph: "−", category: "action", description: "Replier" },
  times: { glyph: "×", category: "action", description: "Retirer l'élément" },
  money: { glyph: "💰", category: "governance", description: "Budget / Coût FinOps" },
  moneyBag: { glyph: "💰", category: "governance", description: "Budget / Coût FinOps" },
  book: { glyph: "📖", category: "navigation", description: "Glossaire & Règles" },
  bookOpen: { glyph: "📖", category: "navigation", description: "Glossaire & Règles ouvert" },
  books: { glyph: "📚", category: "navigation", description: "Sources & Documentation" },
  lightbulb: { glyph: "💡", category: "assistant", description: "Conseil / Astuce" },
  arrowLeft: { glyph: "←", category: "action", description: "Retour" },
  arrowRight: { glyph: "→", category: "action", description: "Suivant / Cible" },
  thumbUp: { glyph: "👍", category: "assistant", description: "Bonne réponse" },
  thumbDown: { glyph: "👎", category: "assistant", description: "Réponse à améliorer" },
  undo: { glyph: "↺", category: "action", description: "Restaurer l'état initial" },
  promoteUp: { glyph: "⬆️", category: "action", description: "Promouvoir au niveau supérieur" },
  divisionLandmark: { glyph: "🏛️", category: "scope", description: "Direction / Division" },
  menuAssistant: { glyph: "💬", category: "navigation", description: "Mon Assistant" },
  menuProcesses: { glyph: "☍", category: "navigation", description: "Mes Processus" },
  menuActivity: { glyph: "📜", category: "navigation", description: "Journal d'Activité" },
  cmdkShortcut: { glyph: "⌘K", category: "action", description: "Raccourci Recherche Globale" },
  bulletDot: { glyph: "·", category: "chevron", description: "Séparateur ponctuel" },
};

export function getOrciaIconDefinition(name: OrciaIconName): OrciaIconDefinition {
  return ORCIA_ICONS[name];
}

export function getOrciaIconGlyph(name: OrciaIconName): string {
  return ORCIA_ICONS[name].glyph;
}

export const ORCIA_EIGHT_MENU_ICON_NAMES: Record<EightFixedMenuKey, OrciaIconName> = {
  cockpit: "cockpit",
  assistant: "assistant",
  processes: "processes",
  agents: "agents",
  spaces: "spaces",
  finops: "finops",
  configuration: "configuration",
  help: "help",
};

export const ORCIA_MODULE_ICON_NAMES: Record<UiModuleKey, OrciaIconName> = {
  cockpit: "home",
  inbox: "notifications",
  catalog: "pack",
  ontology: "dna",
  gates: "shield",
  finops: "finops",
  admin: "configuration",
  bootstrap: "rocket",
};

export const ORCIA_SCOPE_LEVEL_ICON_NAMES: Record<UiScopeLevel, OrciaIconName> = {
  GLOBAL: "globe",
  BU: "organizationBu",
  TEAM: "team",
  WORKSPACE: "workspaceFolder",
};
