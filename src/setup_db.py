import sqlite3
import csv

def create_database():
    csv_filename = "data.csv"
    db_filename = "mappings.db"
    
    try:
        # 1. Connect to SQLite database
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()

        # 2. Drop and recreate table
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

        # 3. Read and clean the CSV data
        data_to_insert = []
        with open(csv_filename, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            next(reader)  
            
            for row in reader:
                if len(row) >= 5: 
                    # Stripping whitespace is critical to prevent FastAPI search bugs
                    data_to_insert.append((
                        row[1].strip(), 
                        row[2].strip(), 
                        row[3].strip(), 
                        row[4].strip()
                    ))
        
        # 4. Insert data efficiently in bulk
        cursor.executemany('''
            INSERT INTO icd_mappings (system, traditional_term, namaste_code, tm2_code)
            VALUES (?, ?, ?, ?)
        ''', data_to_insert)

        # 5. Commit changes
        conn.commit()
        print(f"Success! {len(data_to_insert)} records cleanly inserted into '{db_filename}'.")
        
    except FileNotFoundError:
        print(f"Error: Could not find '{csv_filename}'. Please ensure it is in the same folder.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure connection closes safely to prevent database locking
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_database()