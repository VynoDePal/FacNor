PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    company_name TEXT NOT NULL,
    company_siren TEXT,
    company_vat_number TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (email LIKE '%@%')
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    client_type TEXT NOT NULL CHECK (client_type IN ('B2B', 'B2C')),
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address_line1 TEXT NOT NULL,
    address_line2 TEXT,
    postal_code TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'France',
    siren TEXT,
    vat_number TEXT,
    contact_full_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, siren),
    CHECK (
        (client_type = 'B2B' AND siren IS NOT NULL AND length(siren) = 9)
        OR (client_type = 'B2C' AND siren IS NULL AND vat_number IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS invoice_sequences (
    user_id INTEGER NOT NULL,
    prefix TEXT NOT NULL DEFAULT 'F',
    last_number INTEGER NOT NULL DEFAULT 0 CHECK (last_number >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, prefix),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    invoice_number TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'issued', 'paid', 'cancelled')),
    currency TEXT NOT NULL DEFAULT 'EUR',
    total_excluding_tax NUMERIC NOT NULL DEFAULT 0 CHECK (total_excluding_tax >= 0),
    total_tax NUMERIC NOT NULL DEFAULT 0 CHECK (total_tax >= 0),
    total_including_tax NUMERIC NOT NULL DEFAULT 0 CHECK (total_including_tax >= 0),
    legal_notice TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    UNIQUE (user_id, invoice_number)
);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    line_order INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    unit_price_excluding_tax NUMERIC NOT NULL CHECK (unit_price_excluding_tax >= 0),
    vat_rate NUMERIC NOT NULL CHECK (vat_rate >= 0),
    line_total_excluding_tax NUMERIC NOT NULL CHECK (line_total_excluding_tax >= 0),
    line_total_tax NUMERIC NOT NULL CHECK (line_total_tax >= 0),
    line_total_including_tax NUMERIC NOT NULL CHECK (line_total_including_tax >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    UNIQUE (invoice_id, line_order)
);

CREATE INDEX IF NOT EXISTS idx_clients_user_id ON clients(user_id);
CREATE INDEX IF NOT EXISTS idx_invoice_sequences_user_id ON invoice_sequences(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice_id ON invoice_lines(invoice_id);
