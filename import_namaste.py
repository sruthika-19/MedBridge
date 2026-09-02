import sqlite3
import pandas as pd


EXCEL_FILENAME = "data/ayu_sat_table_combined.xlsx"
DB_FILENAME = "mappings.db"


def import_namaste():
    conn = None

    try:
        # Read the official NAMASTE Excel file
        df = pd.read_excel(EXCEL_FILENAME)

        # Exact columns present in the official Excel
        required_columns = [
            "rec_id",
            "t_id",
            "term_id",
            "term_devanagari",
            "term_iast",
            "wordtree",
            "parent_id",
            "def_id",
            "w_trans",
            "w_def",
            "refn",
            "sys_id"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing Excel columns: {', '.join(missing_columns)}"
            )

        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()

        # Create the table if it does not already exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS namaste_terms (
                rec_id INTEGER PRIMARY KEY,
                t_id INTEGER,
                term_id TEXT,
                term_devanagari TEXT,
                term_iast TEXT,
                wordtree TEXT,
                parent_id INTEGER,
                def_id INTEGER,
                w_trans TEXT,
                w_def TEXT,
                refn TEXT,
                sys_id INTEGER
            )
        """)

        # Existing database was created before sys_id was added.
        # Add the missing column when necessary.
        existing_columns = [
            row[1]
            for row in cursor.execute(
                "PRAGMA table_info(namaste_terms)"
            ).fetchall()
        ]

        if "sys_id" not in existing_columns:
            cursor.execute(
                "ALTER TABLE namaste_terms ADD COLUMN sys_id INTEGER"
            )

        # Clear old imported NAMASTE records before re-importing
        # so the SQLite table exactly matches the Excel source.
        cursor.execute("DELETE FROM namaste_terms")

        records = []

        for _, row in df.iterrows():
            records.append((
                row["rec_id"],
                row["t_id"],
                row["term_id"],
                row["term_devanagari"],
                row["term_iast"],
                row["wordtree"],
                row["parent_id"],
                row["def_id"],
                row["w_trans"],
                row["w_def"],
                row["refn"],
                row["sys_id"]
            ))

        cursor.executemany("""
            INSERT INTO namaste_terms (
                rec_id,
                t_id,
                term_id,
                term_devanagari,
                term_iast,
                wordtree,
                parent_id,
                def_id,
                w_trans,
                w_def,
                refn,
                sys_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        conn.commit()

        print(f"Success! {len(records)} NAMASTE records imported.")

    except FileNotFoundError:
        print(
            f"Error: Could not find '{EXCEL_FILENAME}'. "
            "Please check that the Excel file is inside the data folder."
        )

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    import_namaste()