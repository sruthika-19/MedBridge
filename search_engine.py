import sqlite3
import difflib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DB_FILE = "mappings.db"

def search_disease(term_query):
    if not term_query or not term_query.strip():
        return {
            "status": "error",
            "message": "Search term cannot be empty.",
            "data": []
        }

    if term_query.isdigit() or len(term_query.strip()) < 2:
        return {
            "status": "error",
            "message": "Invalid clinical search term. Please enter a valid diagnosis name.",
            "data": []
        }
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT system, traditional_term,
               namaste_code, tm2_code, aliases
        FROM icd_mappings
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "status": "error",
            "message": "Database is empty.",
            "data": []
        }

    query = term_query.lower().strip()

    documents = []
    doc_row_mapping = []
    term_list = []
    for row in rows:
        trad_term = row[1]
        aliases = row[4] or ""
        combined_text = f"{trad_term} {aliases.replace('|', ' ')}"
        documents.append(combined_text)
        doc_row_mapping.append(row)
        term_list.append(trad_term.lower())

        if query == trad_term.lower():
            return build_response(row, confidence=98.0)

    close_matches = difflib.get_close_matches(query, term_list, n=1, cutoff=0.45)
    if close_matches and len(query) <= 8:
        matched_term = close_matches[0]
        for idx, r in enumerate(doc_row_mapping):
            if r[1].lower() == matched_term:
                # Give it a high confidence score since difflib found a close spelling
                return build_response(r, confidence=92.5)

    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
    tfidf_matrix = vectorizer.fit_transform(documents + [query])
    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    
    best_idx = cosine_sim.argmax()
    best_score = cosine_sim[best_idx]

    if best_score < 0.12:
        return {
            "status": "error",
            "message": f"No reliable clinical mapping found for '{term_query}'. Please check the term.",
            "data": []
        }
    
    scaled_confidence = (float(best_score) * 45) + 55
    confidence = round(min(scaled_confidence, 96.0), 1)
    
    if confidence < 50:
        close_matches = difflib.get_close_matches(query, term_list, n=1, cutoff=0.4)
        if close_matches:
            matched_term = close_matches[0]
            for idx, r in enumerate(doc_row_mapping):
                if r[1].lower() == matched_term:
                    best_idx = idx
                    confidence = 85.0  # Solid rescued-typo score
                    break
        else:
            return {
                "status": "error",
                "message": f"No reliable mapping found for '{term_query}'. Please check the term.",
                "data": []
            }
        
    return build_response(doc_row_mapping[best_idx], confidence)

def build_response(row, confidence):
    system = row[0]
    trad_term = row[1]
    namaste = row[2]
    tm2 = row[3]

    fhir_payload = {
        "resourceType": "Condition",
        "confidenceScore": f"{confidence}%",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"
                }
            ]
        },

        "code": {
            "coding": [

                {
                    "system":
                    f"urn:oid:namaste:{system.lower()}",
                    "code": namaste,
                    "display": trad_term
                },

                {
                    "system":"http://id.who.int/icd/release/11/mms",
                    "code": tm2
                }
            ],
            "text": trad_term
        }
    }

    return {
        "status": "success",
        "count": 1,
        "data": [fhir_payload]
    }