# Plateforme de Facturation Électronique Conforme (France)

Application web de gestion de facturation permettant aux particuliers et entreprises de générer des factures conformes à la réglementation française. Le système automatise la numérotation, le calcul de la TVA et l'exportation PDF tout en assurant la gestion sécurisée des clients et des utilisateurs.

## Objectifs
- Automatiser la création de factures avec calculs de taxes précis
- Garantir la conformité légale française (mentions, numérotation, TVA)
- Centraliser la gestion des clients (B2B et B2C)
- Permettre l'exportation professionnelle de documents en format PDF
- Assurer la sécurité des données via un système d'authentification

## Périmètre
Inclus : Authentification, gestion des profils clients (avec SIREN/TVA pour les entreprises), moteur de création de factures (lignes de produits, quantités, taux de TVA), moteur de numérotation séquentielle, calcul automatique des totaux, filtrage/recherche, export PDF, API REST, Frontend et tests automatisés. Exclu : Paiement en ligne (Stripe/PayPal), gestion des stocks, comptabilité analytique avancée, intégration ERP tierce.

## Contraintes
- Conformité stricte aux mentions légales de facturation française
- Stack technique : Python (Backend), JS/TS (Frontend), Base de données relationnelle
- Architecture : API REST
- Exigence de tests automatisés (Unitaires et Intégration)

## Hypothèses
- La récupération automatique des données SIREN via API externe n'est pas incluse (saisie manuelle)
- L'utilisateur est responsable de la configuration initiale de ses propres taux de TVA
- Le système ne gère pas l'envoi d'emails automatique des factures
- La conformité repose sur les règles de facturation standard en vigueur au moment du développement

## Critères d'acceptation
- [ ] Un utilisateur authentifié peut créer, modifier et supprimer un client.
- [ ] La génération d'une facture produit un numéro unique, séquentiel et sans interruption de séquence.
- [ ] Le calcul (Somme HT + Somme TVA = TTC) est exact à deux décimales près sur chaque facture.
- [ ] L'export PDF contient l'intégralité des mentions légales (identité émetteur/client, date, numéro, détails TVA, totaux).
- [ ] Un client de type 'Entreprise' impose la saisie d'un numéro SIREN ou de TVA.
- [ ] Le filtrage par client ou par plage de dates retourne les résultats correspondants sans erreur.
- [ ] La suite de tests automatisés passe avec un taux de succès de 100% sur la branche principale.
