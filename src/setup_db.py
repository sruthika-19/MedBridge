import csv
import sqlite3

def create_database():
    conn = sqlite3.connect("mappings.db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS diseases")

    cursor.execute("""
    CREATE TABLE diseases (
        id INTEGER PRIMARY KEY,
        system TEXT,
        traditional_term TEXT,
        namaste_code TEXT,
        tm2_code TEXT
    )
    """)

    with open("data.csv", "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        next(reader)

        for row in reader:
            if len(row) == 5:
                cursor.execute("""
                INSERT INTO diseases
                (id, system, traditional_term, namaste_code, tm2_code)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4]
                ))

    conn.commit()
    conn.close()

    print("Database mappings.db created successfully!")

if __name__ == "__main__":
    create_database()