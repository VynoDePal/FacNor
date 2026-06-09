-- Verification script for sequential numbering engine
BEGIN;

-- 1. Create test data
INSERT INTO Users (username, email, password_hash) 
VALUES ('user1', 'user1@test.com', 'hash1'), ('user2', 'user2@test.com', 'hash2');

-- Get IDs of created users
DO $$ 
DECLARE 
    u1_id UUID; 
    u2_id UUID;
BEGIN 
    SELECT id INTO u1_id FROM Users WHERE username = 'user1';
    SELECT id INTO u2_id FROM Users WHERE username = 'user2';

    -- Create clients for these users
    INSERT INTO Clients (user_id, client_type, name) 
    VALUES (u1_id, 'B2B', 'Client 1A'), (u1_id, 'B2B', 'Client 1B'), (u2_id, 'B2C', 'Client 2A');

    -- Create invoices for User 1 (two different clients)
    -- These should follow the same sequence for User 1
    INSERT INTO Invoices (client_id, issue_date, due_date, status, total_amount_excluding_tax, total_tax_amount, total_amount_including_tax)
    SELECT id, CURRENT_DATE, CURRENT_DATE + 30, 'Draft', 100, 20, 120 FROM Clients WHERE name = 'Client 1A';

    INSERT INTO Invoices (client_id, issue_date, due_date, status, total_amount_excluding_tax, total_tax_amount, total_amount_including_tax)
    SELECT id, CURRENT_DATE, CURRENT_DATE + 30, 'Draft', 200, 40, 240 FROM Clients WHERE name = 'Client 1B';

    -- Create invoices for User 2
    INSERT INTO Invoices (client_id, issue_date, due_date, status, total_amount_excluding_tax, total_tax_amount, total_amount_including_tax)
    SELECT id, CURRENT_DATE, CURRENT_DATE + 30, 'Draft', 300, 60, 360 FROM Clients WHERE name = 'Client 2A';
END;
$$;

-- 2. Verify the results
SELECT u.username, i.invoice_number 
FROM Invoices i 
JOIN Clients c ON i.client_id = c.id 
JOIN Users u ON c.user_id = u.id 
ORDER BY u.username, i.invoice_number;

-- Expected Output:
-- user1 | INV-000001
-- user1 | INV-000002
-- user2 | INV-000001

ROLLBACK;
EOF > verify_numbering.sql
-- Verification script for sequential numbering engine
BEGIN;

-- 1. Create test data
INSERT INTO Users (username, email, password_hash) 
VALUES ('user1', 'user1@test.com', 'hash1'), ('user2', 'user2@test.com', 'hash2');

-- Get IDs of created users
DO $$ 
DECLARE 
    u1_id UUID; 
    u2_id UUID;
BEGIN 
    SELECT id INTO u1_id FROM Users WHERE username = 'user1';
    SELECT id INTO u2_id FROM Users WHERE username = 'user2';

    -- Create clients for these users
    INSERT INTO Clients (user_id, client_type, name) 
    VALUES (u1_id, 'B2B', 'Client 1A'), (u1_id, 'B2B', 'Client 1B'), (u2_id, 'B2C', 'Client 2A');

    -- Create invoices for User 1 (two different clients)
    -- These should follow the same sequence for User 1
    INSERT INTO Invoices (client_id, issue_date, due_date, status, total_amount_excluding_tax, total_tax_amount, total_amount_including_tax)
    SELECT id, CURRENT_DATE, CURRENT_DATE + 30, 'Draft', 100, 20, 120 FROM Clients WHERE name = 'Client 1A';

    INSERT INTO Invoices (client_id, issue_date, due_date, status, total_amount_excluding_tax, total_tax_amount, total_amount_including_tax)
    SELECT id, CURRENT_DATE, CURRENT_DATE + 30, 'Draft', 200, 40, 240 FROM Clients WHERE name = 'Client 1B';

    -- Create invoices for User 2
    INSERT INTO Invoices (client_id, issue_date, due_date, status, total_amount_excluding_tax, total_tax_amount, total_amount_including_tax)
    SELECT id, CURRENT_DATE, CURRENT_DATE + 30, 'Draft', 300, 60, 360 FROM Clients WHERE name = 'Client 2A';
END;
$$;

-- 2. Verify the results
SELECT u.username, i.invoice_number 
FROM Invoices i 
JOIN Clients c ON i.client_id = c.id 
JOIN Users u ON c.user_id = u.id 
ORDER BY u.username, i.invoice_number;

-- Expected Output:
-- user1 | INV-000001
-- user1 | INV-000002
-- user2 | INV-000001

ROLLBACK;
