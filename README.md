# FacNor

Application web de gestion de factures normalisées pour des particuliers et des
entreprises, conforme aux exigences de la facturation électronique française :
mentions légales obligatoires, numérotation séquentielle et continue, calcul de
la TVA, identité émetteur/client.

Fonctionnalités attendues :
- gérer des clients (particuliers et entreprises avec SIREN/TVA) ;
- créer et éditer des factures avec lignes (quantité, prix unitaire HT, taux de TVA) ;
- numéroter automatiquement les factures de façon séquentielle ;
- calculer les totaux HT/TVA/TTC ;
- exporter une facture en PDF ;
- lister/filtrer factures et clients ;
- authentification des utilisateurs.

Stack : backend Python (API REST) + frontend JS/TS + base de données relationnelle.
Le code doit être testé (tests automatisés).
