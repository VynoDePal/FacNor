import sqlite3

from app.database import connect


def table_names(connection):
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return {row[0] for row in rows}


def foreign_keys(connection, table):
    return {(row[2], row[3], row[4]) for row in connection.execute(f"PRAGMA foreign_key_list({table})")}


def test_core_tables_are_created(database_path):
    with sqlite3.connect(database_path) as connection:
        assert {"users", "clients", "invoices", "invoice_lines"}.issubset(table_names(connection))


def test_foreign_keys_link_invoice_model(database_path):
    with sqlite3.connect(database_path) as connection:
        assert ("users", "user_id", "id") in foreign_keys(connection, "clients")
        assert ("users", "user_id", "id") in foreign_keys(connection, "invoices")
        assert ("clients", "client_id", "id") in foreign_keys(connection, "invoices")
        assert ("invoices", "invoice_id", "id") in foreign_keys(connection, "invoice_lines")


def test_b2b_and_b2c_client_rules(database_path):
    with connect(database_path) as connection:
        user_id = connection.execute(
            """
            INSERT INTO users (email, password_hash, full_name, company_name)
            VALUES ('user@example.com', 'hash', 'Marie Martin', 'FacNor Demo')
            """
        ).lastrowid
        connection.execute(
            """
            INSERT INTO clients (
                user_id, client_type, name, address_line1, postal_code, city, siren, vat_number
            ) VALUES (?, 'B2B', 'Entreprise SAS', '1 rue A', '75001', 'Paris', '123456789', 'FR00123456789')
            """,
            (user_id,),
        )
        connection.execute(
            """
            INSERT INTO clients (user_id, client_type, name, address_line1, postal_code, city)
            VALUES (?, 'B2C', 'Jean Dupont', '2 rue B', '69001', 'Lyon')
            """,
            (user_id,),
        )
        try:
            connection.execute(
                """
                INSERT INTO clients (user_id, client_type, name, address_line1, postal_code, city)
                VALUES (?, 'B2B', 'Sans SIREN', '3 rue C', '33000', 'Bordeaux')
                """,
                (user_id,),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("B2B clients must provide a SIREN")


def test_invoice_lines_reference_invoices(database_path):
    with connect(database_path) as connection:
        user_id = connection.execute(
            "INSERT INTO users (email, password_hash, full_name, company_name) VALUES (?, ?, ?, ?)",
            ("issuer@example.com", "hash", "Issuer", "Issuer SAS"),
        ).lastrowid
        client_id = connection.execute(
            """
            INSERT INTO clients (user_id, client_type, name, address_line1, postal_code, city)
            VALUES (?, 'B2C', 'Client', '1 rue Test', '44000', 'Nantes')
            """,
            (user_id,),
        ).lastrowid
        invoice_id = connection.execute(
            """
            INSERT INTO invoices (user_id, client_id, invoice_number, issue_date)
            VALUES (?, ?, '2024-0001', '2024-01-15')
            """,
            (user_id, client_id),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO invoice_lines (
                invoice_id, line_order, description, quantity, unit_price_excluding_tax,
                vat_rate, line_total_excluding_tax, line_total_tax, line_total_including_tax
            ) VALUES (?, 1, 'Prestation', 2, 100, 20, 200, 40, 240)
            """,
            (invoice_id,),
        )
        try:
            connection.execute(
                """
                INSERT INTO invoice_lines (
                    invoice_id, line_order, description, quantity, unit_price_excluding_tax,
                    vat_rate, line_total_excluding_tax, line_total_tax, line_total_including_tax
                ) VALUES (9999, 1, 'Orpheline', 1, 10, 20, 10, 2, 12)
                """
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Invoice lines must reference an existing invoice")
