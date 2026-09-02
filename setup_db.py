import sqlite3


def create_database():
    db_filename = "mappings.db"

    try:
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()

        # Preserve the existing icd_mappings table.
        # Do not drop or recreate it.

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS namaste_terms (
                id INTEGER PRIMARY KEY,
                system TEXT,
                term_id TEXT,
                parent_id TEXT,
                term TEXT,
                code TEXT,
                short_definition TEXT,
                long_definition TEXT,
                reference TEXT,
                source TEXT,
                source_version TEXT
            )
        """)

        conn.commit()
        print(f"Success! Database '{db_filename}' is ready.")
        print("Table 'namaste_terms' is ready.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    create_database()
