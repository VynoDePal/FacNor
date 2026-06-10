-- Database schema for FacNor
-- SQLite used for development

-- Clients table
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    email TEXT,
    adresse TEXT,
    siat_siren TEXT, -- SIRET or SIREN for companies
    tva_intracommunautaire TEXT,
    type_client TEXT CHECK(type_client IN ('particulier', 'entreprise')) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Factures table
CREATE TABLE IF NOT EXISTS factures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    client_id INTEGER NOT NULL,
    date_facture DATE NOT NULL,
    date_echeance DATE,
    statut TEXT CHECK(statut IN ('brouillon', 'envoyee', 'payee', 'annulee')) DEFAULT 'brouillon',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

-- Lignes de facture table
CREATE TABLE IF NOT EXISTS lignes_facture (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facture_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantite REAL NOT NULL CHECK(quantite > 0),
    prix_unitaire_ht REAL NOT NULL CHECK(prix_unitaire_ht >= 0),
    taux_tva REAL NOT NULL CHECK(taux_tva >= 0),
    FOREIGN KEY (facture_id) REFERENCES factures(id) ON DELETE CASCADE
);
