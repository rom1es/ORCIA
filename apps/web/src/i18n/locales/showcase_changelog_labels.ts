import type { ShowcasePublicDictionary } from "./showcase_labels";

export const SHOWCASE_CHANGELOG_FR: ShowcasePublicDictionary["changelog"] = {
  statsTitle:
    "4.1 Métriques Vivantes du Dépôt ORCIA (Synchronisées automatiquement)",
  statsSubtitle:
    "Ces compteurs sont extraits automatiquement du code source réel et vérifiés en intégration continue.",
  activeRoutesStatLabel: "Routes Web Actives",
  uiPrimitivesStatLabel: "Primitives d'interface",
  alembicMigrationsStatLabel: "Migrations de base",
  techLeadReportsStatLabel: "Rapports Tech Lead",
  verifiedCapabilitiesStatLabel: "Capacités Vérifiées",
  installedPacksTitleTemplate: "Packs Métiers Installés ({count})",
  installedPacksHelpLabel:
    "Comprendre les Packs Métiers détectés dans le dépôt",
  stackVersionsTitleTemplate: "Versions de la Stack ({count} briques)",
  reportsTimelineTitleTemplate:
    "4.2 Chronologie Vivante des Rapports Tech Lead ({filtered} / {total})",
  reportsTimelineSubtitle:
    "Extraite automatiquement de l'index des rapports Tech Lead du dépôt.",
  searchPlaceholder:
    "Filtrer l'historique par date, Story, domaine ou mot-clé...",
};

export const SHOWCASE_CHANGELOG_EN: ShowcasePublicDictionary["changelog"] = {
  statsTitle:
    "4.1 Live ORCIA Repository Metrics (Automatically Synchronized)",
  statsSubtitle:
    "These counters are automatically extracted from the live source tree and verified in continuous integration.",
  activeRoutesStatLabel: "Active Web Routes",
  uiPrimitivesStatLabel: "UI Primitives",
  alembicMigrationsStatLabel: "Database Migrations",
  techLeadReportsStatLabel: "Tech Lead Reports",
  verifiedCapabilitiesStatLabel: "Verified Capabilities",
  installedPacksTitleTemplate: "Installed Business Packs ({count})",
  installedPacksHelpLabel:
    "Understand Business Packs detected in the repository",
  stackVersionsTitleTemplate: "Locked Stack Versions ({count} items)",
  reportsTimelineTitleTemplate:
    "4.2 Living Tech Lead Reports Timeline ({filtered} / {total})",
  reportsTimelineSubtitle:
    "Automatically extracted from the repository Tech Lead reports index.",
  searchPlaceholder:
    "Filter changelog by date, Story, domain, or keyword...",
};
