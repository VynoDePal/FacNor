-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE Users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Clients Table
CREATE TABLE Clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    client_type VARCHAR(10) NOT NULL CHECK (client_type IN ('B2B', 'B2C')),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    vat_number VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- Invoices Table
CREATE TABLE Invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('Draft', 'Sent', 'Paid', 'Overdue', 'Cancelled')),
    currency VARCHAR(3) DEFAULT 'EUR' NOT NULL,
    tax_rate DECIMAL(5, 2) DEFAULT 20.00,
    total_amount_excluding_tax DECIMAL(15, 2) NOT NULL,
    total_tax_amount DECIMAL(15, 2) NOT NULL,
    total_amount_including_tax DECIMAL(15, 2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_client FOREIGN KEY (client_id) REFERENCES Clients(id) ON DELETE CASCADE
);

-- InvoiceItems Table
CREATE TABLE InvoiceItems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID NOT NULL,
    description VARCHAR(255) NOT NULL,
    quantity DECIMAL(15, 2) NOT NULL,
    unit_price DECIMAL(15, 2) NOT NULL,
    tax_rate DECIMAL(5, 2) NOT NULL,
    line_total_excluding_tax DECIMAL(15, 2) NOT NULL,
    line_tax_amount DECIMAL(15, 2) NOT NULL,
    line_total_including_tax DECIMAL(15, 2) NOT NULL,
    CONSTRAINT fk_invoice FOREIGN KEY (invoice_id) REFERENCES Invoices(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX idx_clients_user_id ON Clients(user_id);
CREATE INDEX idx_invoices_client_id ON Invoices(client_id);
CREATE INDEX idx_invoice_items_invoice_id ON InvoiceItems(invoice_id);

-- Sequential Numbering Engine
-- Table to track per-user sequences
CREATE TABLE InvoiceSequences (
    user_id UUID PRIMARY KEY REFERENCES Users(id) ON DELETE CASCADE,
    current_value INTEGER NOT NULL DEFAULT 0,
    prefix VARCHAR(10) DEFAULT 'INV-',
    CONSTRAINT positive_sequence CHECK (current_value >= 0)
);

-- Function to generate the next invoice number
CREATE OR REPLACE FUNCTION fn_generate_invoice_number(p_client_id UUID) 
RETURNS VARCHAR(50) AS \$$
DECLARE
    v_user_id UUID;
    v_next_val INTEGER;
    v_prefix VARCHAR(10);
BEGIN
    -- Get the user_id for the given client
    SELECT user_id INTO v_user_id FROM Clients WHERE id = p_client_id;
    
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Client not found for the given ID';
    END IF;

    -- Atomically increment and get the next value for the user
    -- Use row-level locking to prevent gaps and race conditions
    INSERT INTO InvoiceSequences (user_id, current_value)
    VALUES (v_user_id, 1)
    ON CONFLICT (user_id) 
    DO UPDATE SET current_value = InvoiceSequences.current_value + 1
    RETURNING current_value, prefix INTO v_next_val, v_prefix;

    -- Return the formatted invoice number (e.g., INV-0001)
    RETURN v_prefix || LPAD(v_next_val::TEXT, 6, '0');
END;
\$$ LANGUAGE plpgsql;

-- Trigger to automatically populate invoice_number before insertion
CREATE OR REPLACE FUNCTION fn_invoice_number_trigger() 
RETURNS TRIGGER AS \$$
BEGIN
    -- Only generate if invoice_number is not provided
    IF NEW.invoice_number IS NULL THEN
        NEW.invoice_number := fn_generate_invoice_number(NEW.client_id);
    END IF;
    RETURN NEW;
END;
\$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_invoice_number
BEFORE INSERT ON Invoices
FOR EACH ROW
EXECUTE FUNCTION fn_invoice_number_trigger();

