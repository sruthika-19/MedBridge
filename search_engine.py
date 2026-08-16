import sqlite3

DB_FILE = "mappings.db"

def search_disease(term_query):
    if not term_query or not term_query.strip():
        return {"status": "error", "message": "Search term cannot be empty.", "data": []}

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    query = """
        SELECT system, traditional_term, namaste_code, tm2_code
        FROM icd_mappings
        WHERE traditional_term LIKE ? OR namaste_code LIKE ?
    """
    search_param = f"%{term_query}%"
    cursor.execute(query, (search_param, search_param))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"status": "error", "message": f"No mapping found for '{term_query}'.", "data": []}

    results = [
        {"system": r[0], "traditional_term": r[1], "namaste_code": r[2], "tm2_code": r[3]}
        for r in rows
    ]
    return {"status": "success", "count": len(results), "data": results}