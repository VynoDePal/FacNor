# Système de Facturation Normalisée (Conformité France)

Application web de gestion de facturation conforme aux normes légales françaises, permettant la création, le suivi et l'exportation de factures pour les particuliers et les entreprises.

## Objectifs
- Automatiser la génération de factures avec numérotation séquentielle et continue
- Assurer la conformité légale des mentions obligatoires et des calculs de TVA
- Centraliser la gestion des clients (B2B et B2C)
- Permettre l'exportation professionnelle de documents au format PDF

## Périmètre
Inclus : Authentification utilisateur, gestion CRUD clients (avec SIREN/TVA), moteur de création de factures avec lignes de détails, calcul automatique des totaux, filtrage/recherche, export PDF, API REST et tests automatisés. Exclu : Paiement en ligne (Stripe/PayPal), gestion de la comptabilité analytique, gestion des stocks, multi-devises.

## Contraintes
- Stack technique : Python (Backend API REST), JS/TS (Frontend), Base de données relationnelle
- Conformité stricte aux règles de numérotation et de mentions légales françaises
- Obligation de couverture par des tests automatisés
- Architecture découplée Frontend/Backend

## Hypothèses
- L'application gère uniquement la devise Euro (€)
- L'utilisateur est responsable de la validité des informations légales saisies (SIREN, adresse)
- Le système est destiné à un usage mono-utilisateur ou multi-utilisateurs avec isolation des données par compte

## Critères d'acceptation
- [ ] Le système génère un numéro de facture unique et séquentiel sans interruption de séquence lors de la création.
- [ ] Le calcul (Quantité * Prix Unitaire HT * Taux TVA) est mathématiquement exact pour chaque ligne et pour le total TTC.
- [ ] Le fichier PDF exporté contient l'intégralité des mentions légales (Identité émetteur/client, SIREN, TVA, dates, numérotation).
- [ ] Un utilisateur non authentifié reçoit une erreur 401/403 lors de toute tentative d'accès aux endpoints de l'API.
- [ ] La recherche par SIREN ou nom de client retourne les résultats correspondants en moins de 500ms.
- [ ] La suite de tests automatisés passe avec succès (Green) sur le backend et le frontend avant tout déploiement.
