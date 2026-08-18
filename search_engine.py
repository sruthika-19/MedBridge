import sqlite3
import difflib

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

    for row in rows:

        traditional_term = row[1].lower()
        aliases = row[4] or ""
        alias_list = [
            alias.strip().lower()
            for alias in aliases.split("|")
            if alias.strip()
        ]
        if query == traditional_term or query in alias_list:
            return build_response(row, 100.0)

    possible_matches = []

    for row in rows:
        traditional_term = row[1].lower()
        aliases = row[4] or ""
        alias_list = [
            alias.strip().lower()
            for alias in aliases.split("|")
            if alias.strip()
        ]

        score = difflib.SequenceMatcher(
            None,
            query,
            traditional_term
        ).ratio()

        possible_matches.append(
            (score, row)
        )

        for alias in alias_list:

            score = difflib.SequenceMatcher(
                None,
                query,
                alias
            ).ratio()

            possible_matches.append(
                (score, row)
            )

    possible_matches.sort(
        key=lambda x: x[0],
        reverse=True
    )

    best_score, best_row = possible_matches[0]

    confidence = round(best_score * 100, 1)

    if confidence < 50:

        return {
            "status": "error",
            "message": (
                f"No reliable mapping found for "
                f"'{term_query}'. Please check the term."
            ),
            "data": []
        }

    return build_response(
        best_row,
        confidence
    )


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
                    "system":
                    "http://terminology.hl7.org/"
                    "CodeSystem/condition-clinical",

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