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
