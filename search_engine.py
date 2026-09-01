import sqlite3

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from who_service import search_who_api
from medicine_twin import get_medicine_twin_data
from mapping_validator import validate_mapping
from mapping_cache import get_cached_mapping, save_mapping_cache


DB_FILE = "mappings.db"


def search_disease(term_query, system_filter=None):
    """
    Searches for a traditional medical disease term
    and maps it to a standardized clinical representation.
    """

    # ---------------------------------------------------------
    # 1. INPUT VALIDATION
    # ---------------------------------------------------------

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

    query = term_query.strip().lower()

    # ---------------------------------------------------------
    # 2. CHECK CACHE
    # ---------------------------------------------------------

    cached_mapping = get_cached_mapping(query)

    if cached_mapping:
        cached_payload = build_cached_fhir_payload(cached_mapping)

        cached_payload["validation"] = {
            "validation_status": cached_mapping.get(
                "validation_status",
                "validated"
            ),
            "reason": cached_mapping.get(
                "reason",
                "Mapping retrieved from validated cache"
            )
        }

        return {
            "status": "success",
            "count": 1,
            "source": "cache",
            "data": [cached_payload]
        }

    # ---------------------------------------------------------
    # 3. DATABASE SEARCH
    # ---------------------------------------------------------

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if (
        system_filter
        and system_filter.strip()
        and system_filter.lower() != "all"
    ):
        cursor.execute("""
            SELECT
                system,
                traditional_term,
                namaste_code,
                tm2_code,
                aliases
            FROM icd_mappings
            WHERE LOWER(system) = LOWER(?)
        """, (system_filter.strip(),))
    else:
        cursor.execute("""
            SELECT
                system,
                traditional_term,
                namaste_code,
                tm2_code,
                aliases
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

    # ---------------------------------------------------------
    # 4. PREPARE DOCUMENTS FOR TF-IDF
    # ---------------------------------------------------------

    documents = []
    doc_row_mapping = []

    for row in rows:
        traditional_term = row[1]
        aliases = row[4] or ""

        combined_text = (
            f"{traditional_term} "
            f"{aliases.replace('|', ' ')}"
        )

        documents.append(combined_text)
        doc_row_mapping.append(row)

    # ---------------------------------------------------------
    # 5. TF-IDF SIMILARITY
    # ---------------------------------------------------------

    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english"
        )

        tfidf_matrix = vectorizer.fit_transform(documents)
        query_vector = vectorizer.transform([query])

        cosine_scores = cosine_similarity(
            query_vector,
            tfidf_matrix
        ).flatten()

    except ValueError:
        cosine_scores = [0] * len(rows)

    # ---------------------------------------------------------
    # 6. GET TOP 3 CANDIDATES
    # ---------------------------------------------------------

    top_indices = cosine_scores.argsort()[::-1][:3]

    candidates = []

    for idx in top_indices:
        score = float(cosine_scores[idx])

        row = doc_row_mapping[idx]

        traditional_term = row[1]
        aliases = row[4] or ""

        traditional_term_lower = traditional_term.lower()

        aliases_list = [
            alias.strip().lower()
            for alias in aliases.split("|")
            if alias.strip()
        ]

        # Exact traditional term
        if query == traditional_term_lower:
            confidence = 98.0

        # Exact alias
        elif query in aliases_list:
            confidence = 95.0

        # TF-IDF similarity
        elif score > 0.1:
            confidence = round(score * 100, 1)

            if confidence > 90:
                confidence = 90.0

        else:
            continue

        candidates.append({
            "score": confidence,
            "confidence": confidence,
            "index": idx,
            "row": row
        })

    # ---------------------------------------------------------
    # 7. SORT CANDIDATES
    # ---------------------------------------------------------

    candidates.sort(
        key=lambda candidate: candidate["score"],
        reverse=True
    )

    # ---------------------------------------------------------
    # 8. VALIDATE BEST MAPPING
    # ---------------------------------------------------------

    if candidates:

        best_candidate = candidates[0]
        best_row = best_candidate["row"]

        namaste_data = {
            "code": best_row[2],
            "term": best_row[1]
        }

        icd11_data = {
            "code": best_row[3],
            "term": best_row[1]
        }

        validation = validate_mapping(
            namaste_data,
            icd11_data,
            candidates
        )

        # -----------------------------------------------------
        # 9. BUILD RESULTS
        # -----------------------------------------------------

        matched_data = []

        for candidate in candidates:

            row = candidate["row"]
            confidence = candidate["confidence"]

            payload = build_fhir_payload(
                row,
                confidence
            )

            # Validation information
            if candidate is best_candidate:
                payload["validation"] = validation.to_dict()

            else:
                payload["validation"] = {
                    "validation_status": "candidate",
                    "reason": "Alternative candidate mapping"
                }

            matched_data.append(payload)

        # -----------------------------------------------------
        # 10. SAVE ONLY VALIDATED BEST MAPPING TO CACHE
        # -----------------------------------------------------

        if validation.status == "validated":

            save_mapping_cache({
                "term": query,
                "system": best_row[0],
                "namaste_code": best_row[2],
                "namaste_term": best_row[1],
                "icd11_code": best_row[3],
                "icd11_term": best_row[1],
                "confidence": best_candidate["confidence"],
                "validation_status": validation.status,
                "reason": validation.reason
            })

        return {
            "status": "success",
            "count": len(matched_data),
            "source": "local",
            "data": matched_data
        }

    # ---------------------------------------------------------
    # 11. WHO FALLBACK
    # ---------------------------------------------------------

    who_res = search_who_api(term_query)

    if who_res.get("status") == "success":
        return who_res

    # ---------------------------------------------------------
    # 12. NO RESULT
    # ---------------------------------------------------------

    return {
        "status": "error",
        "message": (
            f"No reliable clinical mapping found for "
            f"'{term_query}' locally or via WHO API."
        ),
        "data": []
    }


def build_cached_fhir_payload(cached):
    """
    Builds a FHIR payload from a cached validated mapping.
    """

    system = cached.get("system") or "unknown"
    traditional_term = cached.get("namaste_term") or cached.get("term")
    namaste_code = cached.get("namaste_code")
    icd11_code = cached.get("icd11_code")
    confidence = cached.get("confidence", 0)

    twin_data = get_medicine_twin_data(
        traditional_term
    )

    modern_term = get_modern_equivalent(
        traditional_term
    )

    return {
        "resourceType": "Condition",
        "confidenceScore": f"{confidence}%",
        "modernEquivalent": modern_term,
        "medicineTwin": {
            "activeIngredients": twin_data.get(
                "ingredients",
                []
            ),
            "traditionalUses": twin_data.get(
                "traditional_uses",
                []
            ),
            "riskRadar": twin_data.get(
                "risk_warnings",
                []
            )
        },
        "clinicalStatus": {
            "coding": [
                {
                    "system": (
                        "http://terminology.hl7.org/"
                        "CodeSystem/condition-clinical"
                    ),
                    "code": "active"
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": (
                        f"urn:oid:namaste:{system.lower()}"
                    ),
                    "code": namaste_code,
                    "display": traditional_term
                },
                {
                    "system": (
                        "http://id.who.int/icd/"
                        "release/11/mms"
                    ),
                    "code": icd11_code
                }
            ],
            "text": traditional_term
        }
    }


def build_fhir_payload(row, confidence):
    """
    Builds the FHIR Condition payload.
    """

    system = row[0]
    traditional_term = row[1]
    namaste = row[2]
    tm2 = row[3]

    modern_term = get_modern_equivalent(
        traditional_term
    )

    twin_data = get_medicine_twin_data(
        traditional_term
    )

    return {
        "resourceType": "Condition",

        "confidenceScore": f"{confidence}%",

        "modernEquivalent": modern_term,

        "medicineTwin": {
            "activeIngredients": twin_data.get(
                "ingredients",
                []
            ),
            "traditionalUses": twin_data.get(
                "traditional_uses",
                []
            ),
            "riskRadar": twin_data.get(
                "risk_warnings",
                []
            )
        },

        "clinicalStatus": {
            "coding": [
                {
                    "system": (
                        "http://terminology.hl7.org/"
                        "CodeSystem/condition-clinical"
                    ),
                    "code": "active"
                }
            ]
        },

        "code": {
            "coding": [
                {
                    "system": (
                        f"urn:oid:namaste:{system.lower()}"
                    ),
                    "code": namaste,
                    "display": traditional_term
                },
                {
                    "system": (
                        "http://id.who.int/icd/"
                        "release/11/mms"
                    ),
                    "code": tm2
                }
            ],
            "text": traditional_term
        }
    }


def get_modern_equivalent(traditional_term):
    """
    Converts traditional medical terminology
    into a standardized clinical equivalent.
    """

    modern_mapping = {

        # 1-10
        "jvara": "Pyrexia / Fever",
        "suram": "Pyrexia / Fever",
        "humma": "Pyrexia / Fever",
        "kasa": "Cough / Bronchitis",
        "shwasa": "Bronchial Asthma / Dyspnea",
        "irumal": "Cough",
        "su-al": "Cough",
        "hikka": "Hiccups",
        "pandu": "Anemia / Iron Deficiency Anemia",
        "manjal noi": "Jaundice / Viral Hepatitis",

        # 11-20
        "yarqan": "Jaundice / Viral Hepatitis",
        "aruchi": "Anorexia / Loss of Appetite",
        "ajirana": "Indigestion",
        "mandham": "Indigestion",
        "su-e-hazm": "Indigestion",
        "atisara": "Acute Diarrhea / Gastroenteritis",
        "kazhichal": "Diarrhea",
        "ishal": "Diarrhea",
        "grahani": "Malabsorption Syndrome / IBS",
        "chardi": "Emesis / Nausea and Vomiting",

        # 21-30
        "vanti": "Vomiting",
        "qai": "Vomiting",
        "mutraghata": "Urinary Retention",
        "neerizhivu": "Diabetes Mellitus",
        "zayabetus": "Diabetes Mellitus",
        "prameha": "Diabetes Mellitus / Metabolic Disorder",
        "sandhigata vata": "Osteoarthritis",
        "azhal keel vayu": "Osteoarthritis",
        "waja-ul-mafasil": "Arthritis / Joint Pain",
        "gridhrasi": "Sciatica / Lumbar Radiculopathy",

        # 31-40
        "ardita": "Facial Paralysis",
        "ajal kirkrippu": "Dermatitis",
        "sadra-o-dwar": "Skin Disorder",
        "kandu": "Itching / Pruritus",
        "kampavata": "Parkinsonism / Tremors",
        "sori": "Scabies / Itching",
        "hikka-e-jild": "Skin Inflammation",
        "dadru": "Ringworm / Tinea",
        "vellai noi": "Leucorrhea",
        "bars": "Vitiligo",

        # 41-50
        "shotha": "Edema / Inflammatory Swelling",
        "neeradai": "Cold / Rhinitis / Nasal Congestion",
        "raktapitta": "Bleeding Disorder / Thrombocytopenia",
        "gunmam": "Gastritis / Acidity",
        "nazla": "Common Cold / Catarrh",
        "vatarakta": "Gouty Arthritis",
        "karappan": "Eczema / Dermatitis",
        "warm": "Inflammation / Swelling",
        "pakshaghata": "Stroke / Paralysis",
        "soolai": "Colic / Abdominal Pain",

        # 51-62
        "uqr": "Infertility",
        "unmada": "Psychosis / Mental Disorder",
        "vali noi": "Neurological Disorder",
        "khafaqan": "Palpitation",
        "shirashoola": "Headache / Migraine",
        "siraneer": "Urinary Dysfunction",
        "suda": "Headache",
        "bhagna": "Bone Fracture",
        "ootha noi": "Dropsy / Edema",
        "amraz-e-jild": "Skin Disease",
        "ashmari": "Kidney Stones / Renal Calculi",
        "kayam": "Fatigue / Body Weakness"
    }

    return modern_mapping.get(
        traditional_term.lower(),
        "Standardized Clinical Presentation"
    )