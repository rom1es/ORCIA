---
id: spaces-sources
title: Connecter et synchroniser vos sources documentaires et outils
version: 1.1.0
lang: fr
layer: BASE
bound_routes:
  - /mes-espaces/$id/sources
  - /spaces/sources
  - /workspaces
  - /settings
---

## À quoi sert cet écran ?

Cet écran vous permet de rattacher les sources de connaissances de votre équipe (dépôts de code, espaces documentaires, suivis de projets ou bases de données) à votre **Espace de travail** et de définir où vos livrables validés sont enregistrés par défaut.

## Comment procéder pas à pas

1. Choisissez le type de source à connecter (code, documentation, suivi de projets ou base de données) et donnez-lui un nom clair pour votre équipe.
2. Indiquez le mode de connexion : **Compte personnel de chaque membre** (chaque utilisateur n'accède qu'aux documents auxquels il a droit) ou **Compte partagé d'équipe** (approuvé par un administrateur).
3. Rédigez une courte justification métier, signez l'ajout et vérifiez la connexion en un clic.

## Repères & notions utiles

- **Source de référence vs Document de travail** : Une source de référence sert de base officielle de lecture ; un document de travail accueille vos livrables en cours de préparation.
- **Connexion sous votre compte personnel** : Garantit qu'aucun membre ne peut lire un document confidentiel auquel il n'a pas accès dans l'outil d'origine.
- **Cloisonnement d'un espace confidentiel** : Empêche la remontée automatique des contenus d'un espace sensible vers les niveaux parents de l'organisation.

## Questions fréquentes

- **Quel est le lien entre une entité de l'organisation (Direction, Équipe) et un Espace de travail ?** L'organisation (Entreprise $\rightarrow$ Direction $\rightarrow$ Équipe) décrit *qui vous êtes* (l'organigramme auquel sont rattachés les membres), tandis que l'**Espace de travail** décrit *sur quoi vous travaillez* (un projet, un produit ou un chantier où sont connectées vos sources documentaires et exécutés vos processus). Chaque Espace de travail appartient à une Équipe ou une Direction propriétaire (une même équipe peut gérer plusieurs espaces), peut inviter d'autres équipes à collaborer, et hérite des règles de son équipe et de sa direction (sauf s'il est configuré en mode confidentiel isolé).
- **Comment accéder à l'explication d'un réglage précis ?** Cliquez sur l'icône `ⓘ` située à côté de l'intitulé : cette colonne d'aide s'ouvre et met directement en évidence la section correspondante.
- **Que se passe-t-il si un document est modifié directement dans notre outil externe ?** Vos modifications directes sont toujours préservées et ne sont jamais écrasées par un brouillon automatique.
