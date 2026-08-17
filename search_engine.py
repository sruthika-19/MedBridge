import sqlite3
import difflib

DB_FILE = "mappings.db"

def search_disease(term_query):
    if not term_query or not term_query.strip():
        return {"status": "error", "message": "Search term cannot be empty.", "data": []}

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT system, traditional_term, namaste_code, tm2_code FROM icd_mappings")
    all_rows = cursor.fetchall()
    conn.close()

    if not all_rows:
        return {"status": "error", "message": "Database is empty.", "data": []}

    term_list = [row[1].lower() for row in all_rows]
    term_query_lower = term_query.lower().strip()
    
    closest_matches = difflib.get_close_matches(term_query_lower, term_list, n=1, cutoff=0.6)

    if not closest_matches:
        return {"status": "error", "message": f"No valid mapping found for '{term_query}'. Please check spelling.", "data": []}

    best_match_str = closest_matches[0]

    confidence = round(difflib.SequenceMatcher(None, term_query_lower, best_match_str).ratio() * 100, 1)

    matched_row = next(row for row in all_rows if row[1].lower() == best_match_str)
    system, trad_term, namaste, tm2 = matched_row

    fhir_payload = {
        "resourceType": "Condition",
        "confidenceScore": f"{confidence}%",
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
        },
        "code": {
            "coding": [
                {
                    "system": f"urn:oid:namaste:{system.lower()}",
                    "code": namaste,
                    "display": trad_term
                },
                {
                    "system": "http://id.who.int/icd/release/11/mms",
                    "code": tm2
                }
            ],
            "text": trad_term
        }
    }

    return {"status": "success", "count": 1, "data": [fhir_payload]}