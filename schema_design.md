# Database Schema Design

## Overview
This schema is designed for an invoicing system supporting both B2B and B2C clients.

## Tables

### 1. `Users`
Stores information about the users who manage the invoicing system.
- `id`: UUID (Primary Key)
- `username`: VARCHAR(255) (Unique, Not Null)
- `email`: VARCHAR(255) (Unique, Not Null)
- `password_hash`: VARCHAR(255) (Not Null)
- `created_at`: TIMESTAMP (Default: CURRENT_TIMESTAMP)
- `updated_at`: TIMESTAMP (Default: CURRENT_TIMESTAMP)

### 2. `Clients`
Stores client information. Supports B2B (Business to Business) and B2C (Business to Consumer).
- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key -> Users.id, Not Null)
- `client_type`: VARCHAR(10) (Check: 'B2B', 'B2C', Not Null)
- `name`: VARCHAR(255) (Not Null) - Company name for B2B, Full name for B2C
- `email`: VARCHAR(255)
- `phone`: VARCHAR(50)
- `address`: TEXT
- `vat_number`: VARCHAR(50) (Nullable, used for B2B)
- `created_at`: TIMESTAMP (Default: CURRENT_TIMESTAMP)
- `updated_at`: TIMESTAMP (Default: CURRENT_TIMESTAMP)

### 3. `Invoices`
Stores the main invoice header information.
- `id`: UUID (Primary Key)
- `client_id`: UUID (Foreign Key -> Clients.id, Not Null)
- `invoice_number`: VARCHAR(50) (Unique, Not Null)
- `issue_date`: DATE (Not Null)
- `due_date`: DATE (Not Null)
- `status`: VARCHAR(20) (Check: 'Draft', 'Sent', 'Paid', 'Overdue', 'Cancelled', Not Null)
- `currency`: VARCHAR(3) (Default: 'EUR', Not Null)
- `tax_rate`: DECIMAL(5, 2) (Default: 20.00)
- `total_amount_excluding_tax`: DECIMAL(15, 2) (Not Null)
- `total_tax_amount`: DECIMAL(15, 2) (Not Null)
- `total_amount_including_tax`: DECIMAL(15, 2) (Not Null)
- `notes`: TEXT
- `created_at`: TIMESTAMP (Default: CURRENT_TIMESTAMP)
- `updated_at`: TIMESTAMP (Default: CURRENT_TIMESTAMP)

### 4. `InvoiceItems`
Stores the line items for each invoice.
- `id`: UUID (Primary Key)
- `invoice_id`: UUID (Foreign Key -> Invoices.id, Not Null, ON DELETE CASCADE)
- `description`: VARCHAR(255) (Not Null)
- `quantity`: DECIMAL(15, 2) (Not Null)
- `unit_price`: DECIMAL(15, 2) (Not Null)
- `tax_rate`: DECIMAL(5, 2) (Not Null)
- `line_total_excluding_tax`: DECIMAL(15, 2) (Not Null)
- `line_tax_amount`: DECIMAL(15, 2) (Not Null)
- `line_total_including_tax`: DECIMAL(15, 2) (Not Null)

## Relations
- **Users 1 : N Clients**: A user can manage multiple clients.
- **Clients 1 : N Invoices**: A client can have multiple invoices.
- **Invoices 1 : N InvoiceItems**: An invoice consists of one or more line items.
