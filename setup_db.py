import sqlite3
import csv

def create_database():
    csv_filename = "data/data.csv"
    db_filename = "mappings.db"
    
    try:
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()

        cursor.execute('DROP TABLE IF EXISTS icd_mappings')
        
        cursor.execute('''
            CREATE TABLE icd_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                system TEXT,
                traditional_term TEXT NOT NULL,
                namaste_code TEXT,
                tm2_code TEXT NOT NULL
            )
        ''')

        data_to_insert = []
        with open(csv_filename, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            next(reader)  
            
            for row in reader:
                if len(row) >= 5: 
                    data_to_insert.append((
                        row[1].strip(), 
                        row[2].strip(), 
                        row[3].strip(), 
                        row[4].strip()
                    ))
        
        cursor.executemany('''
            INSERT INTO icd_mappings (system, traditional_term, namaste_code, tm2_code)
            VALUES (?, ?, ?, ?)
        ''', data_to_insert)

        conn.commit()
        print(f"Success! {len(data_to_insert)} records cleanly inserted into '{db_filename}'.")
        
    except FileNotFoundError:
        print(f"Error: Could not find '{csv_filename}'. Please ensure it is in the same folder.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_database()