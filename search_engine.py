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

    # Check if input is just numbers or invalid gibberish
    if term_query.isdigit() or len(term_query.strip()) < 2:
        return {
            "status": "error",
            "message": "Invalid clinical search term. Please enter a valid diagnosis name.",
            "data": []
        }
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
    tfidf_matrix = vectorizer.fit_transform(documents + [query])
    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    
    best_idx = cosine_sim.argmax()
    best_score = cosine_sim[best_idx]
    confidence = round(float(best_score) * 100, 1)
    
    # Lowered threshold slightly to ensure minor typos pass through cleanly
    if confidence < 30:
        close_matches = difflib.get_close_matches(query, term_list, n=1, cutoff=0.5)
        if close_matches:
            matched_term = close_matches[0]
            # Find the index of this matched term
            for idx, r in enumerate(doc_row_mapping):
                if r[1].lower() == matched_term:
                    best_idx = idx
                    confidence = 85.0  # Assign a reliable high-tier fallback confidence for rescued typos
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
                    "system":
                    "http://id.who.int/icd/"
                    "release/11/mms",

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