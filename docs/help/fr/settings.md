---
resource_id: help-base-settings-fr
uri: orcia://system/help/settings/fr
title: "Configuration : accès, authentification, modèles IA et packs"
version: "1.1.0"
lang: fr
layer: BASE
bound_routes:
  - /settings
  - /configuration
  - /settings/packs
  - /settings/ai-models
  - /bootstrap
summary_what_for: "Configuration centralise les réglages de la plateforme : comptes et habilitations, connexion SSO et double authentification, fournisseurs de modèles IA, connecteurs d'outils et packs métiers déclaratifs."
---

## À quoi sert cet écran

Réservé aux administrateurs, aux responsables sécurité et aux architectes selon leurs droits, cet écran structure le socle technique et de gouvernance d'ORCIA. L'onglet « Packs métiers » et la vue dédiée permettent aussi d'importer des archives `.zip`, de composer un pack personnalisé, de vérifier la complétude de ses dépendances et d'exporter un pack assaini réutilisable dans un autre espace.

## En 4 gestes

1. Ouvrez « Comptes & Habilitations » pour inviter des membres, consulter la matrice des 7 rôles ou créer des règles ciblées (« Qui ? » et « Sur quoi ? »).
2. Dans « Authentification », choisissez le mode de connexion (local ou SSO d'entreprise) et la politique de double authentification.
3. Dans « Modèles IA », renseignez vos fournisseurs (dialogue et recherche documentaire), puis cliquez sur « Tester la connexion » avant d'enregistrer.
4. Dans « Connecteurs » et « Packs métiers », importez une archive `.zip`, composez et publiez un pack sur mesure, exportez une archive assainie, puis activez les packs sur un Espace en reliant leurs emplacements de connecteurs requis.

## Un exemple réel

Lors de l'installation initiale, Alice ouvre Administration › Modèles IA, ajoute son fournisseur principal et un modèle de recherche documentaire, teste la connexion avec succès, puis ouvre « Packs métiers » pour composer un pack personnalisé, l'exporter en `.zip` et l'importer dans un nouvel Espace de travail.

## Ce qui coince souvent

- **Une clé secrète n'apparaît plus après enregistrement** : par sécurité, les jetons et clés API sont protégés en écriture seule et ne sont jamais ré-affichés en clair.
- **Un export ou une publication de pack signale des dépendances manquantes** : cochez l'inclusion automatique des dépendances dans le compositeur ou passez les agents référencés au statut « Actif ».
- **L'export `.zip` refuse une description ou une source** : retirez toute adresse courriel interne, clé d'accès ou hôte privé afin de conserver un pack strictement portable ; les sources réelles se branchent ensuite dans le tiroir d'emplacements de chaque Espace.
- **L'activation d'un pack sur un Espace reste bloquée** : ouvrez le tiroir d'emplacements du pack pour associer chaque emplacement obligatoire à une source ou un connecteur actif de l'Espace.
