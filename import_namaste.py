import sqlite3
import pandas as pd


EXCEL_FILENAME = "data/ayu_sat_table_combined.xlsx"
DB_FILENAME = "mappings.db"


def import_namaste():
    try:
        df = pd.read_excel(EXCEL_FILENAME)

        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()

        records = []

        for _, row in df.iterrows():
            records.append((
                row["rec_id"],
                row["sys_id"],
                row["term_id"],
                row["parent_id"],
                row["term_iast"],
                None,
                row["w_trans"],
                row["w_def"],
                row["refn"],
                "NAMASTE",
                None
            ))

        cursor.executemany("""
            INSERT OR REPLACE INTO namaste_terms
            (
                id,
                system,
                term_id,
                parent_id,
                term,
                code,
                short_definition,
                long_definition,
                reference,
                source,
                source_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    import_namaste()
