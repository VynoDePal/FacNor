PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    company_name TEXT,
    siren TEXT CHECK (siren IS NULL OR (length(siren) = 9 AND siren GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]')),
    vat_number TEXT CHECK (vat_number IS NULL OR vat_number GLOB 'FR[0-9A-Z][0-9A-Z][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    address TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'France',
    siren TEXT CHECK (siren IS NULL OR (length(siren) = 9 AND siren GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]')),
    vat_number TEXT CHECK (vat_number IS NULL OR vat_number GLOB 'FR[0-9A-Z][0-9A-Z][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS invoice_sequences (
    user_id INTEGER PRIMARY KEY,
    next_number INTEGER NOT NULL DEFAULT 1 CHECK (next_number > 0),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    invoice_number TEXT NOT NULL,
    issue_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'issued', 'paid', 'cancelled')),
    currency TEXT NOT NULL DEFAULT 'EUR',
    total_excluding_tax INTEGER NOT NULL DEFAULT 0 CHECK (total_excluding_tax >= 0),
    total_tax INTEGER NOT NULL DEFAULT 0 CHECK (total_tax >= 0),
    total_including_tax INTEGER NOT NULL DEFAULT 0 CHECK (total_including_tax >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    UNIQUE (user_id, sequence_number),
    UNIQUE (user_id, invoice_number)
);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    line_order INTEGER NOT NULL CHECK (line_order > 0),
    description TEXT NOT NULL,
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    unit_price_excluding_tax INTEGER NOT NULL CHECK (unit_price_excluding_tax >= 0),
    vat_rate NUMERIC NOT NULL CHECK (vat_rate >= 0),
    total_excluding_tax INTEGER NOT NULL CHECK (total_excluding_tax >= 0),
    total_tax INTEGER NOT NULL CHECK (total_tax >= 0),
    total_including_tax INTEGER NOT NULL CHECK (total_including_tax >= 0),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    UNIQUE (invoice_id, line_order)
);

CREATE INDEX IF NOT EXISTS idx_clients_user_id ON clients(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice_id ON invoice_lines(invoice_id);
