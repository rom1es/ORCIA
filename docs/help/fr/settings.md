---
resource_id: help-base-settings-fr
uri: orcia://system/help/settings/fr
title: "Configuration : accès, authentification, modèles IA et packs"
version: "1.0.0"
lang: fr
layer: BASE
bound_routes:
  - /settings
  - /configuration
  - /settings/packs
  - /settings/ai-models
  - /bootstrap
summary_what_for: "Configuration centralise les réglages de la plateforme : comptes et habilitations, connexion SSO et double authentification, fournisseurs de modèles IA, connecteurs d'outils et packs métiers."
---

## À quoi sert cet écran

Réservé aux administrateurs, aux responsables sécurité et aux architectes selon leurs droits, cet écran structure le socle technique et de gouvernance d'ORCIA. Vous y accédez aussi à « Mon Organisation » pour gérer vos Directions (BU) et Équipes.

## En 4 gestes

1. Ouvrez « Comptes & Habilitations » pour inviter des membres, consulter la matrice des 7 rôles ou créer des règles ciblées (« Qui ? » et « Sur quoi ? »).
2. Dans « Authentification », choisissez le mode de connexion (local ou SSO d'entreprise) et la politique de double authentification.
3. Dans « Modèles IA », renseignez vos fournisseurs (dialogue et recherche documentaire), puis cliquez sur « Tester la connexion » avant d'enregistrer.
4. Dans « Connecteurs » et « Packs métiers », enregistrez vos outils socles et activez les packs prêts à l'emploi sur vos périmètres.

## Un exemple réel

Lors de l'installation initiale, Alice ouvre Administration › Modèles IA, ajoute son fournisseur principal et un modèle de recherche documentaire, teste la connexion avec succès, puis passe à « Mon Organisation » pour créer la Direction Produit et l'Équipe Paiement.

## Ce qui coince souvent

- **Une clé secrète n'apparaît plus après enregistrement** : par sécurité, les jetons et clés API sont protégés en écriture seule et ne sont jamais ré-affichés en clair.
- **Un utilisateur ne voit pas certains onglets** : l'affichage s'adapte automatiquement au rôle actif (par exemple, seul le Responsable Sécurité peut créer des exceptions d'isolation).
- **Mon Assistant signale qu'aucun modèle d'analyse documentaire n'est actif** : ajoutez un modèle dédié à l'indexation documentaire au niveau Plateforme globale.
