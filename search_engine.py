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
            "message": (
                "Invalid clinical search term. "
                "Please enter a valid diagnosis name."
            ),
            "data": []
        }

    query = term_query.strip().lower()

    # ---------------------------------------------------------
    # 2. CHECK MAPPING CACHE
    # ---------------------------------------------------------

    cached_mapping = get_cached_mapping(query)

    if cached_mapping:

        cached_payload = build_cached_fhir_payload(
            cached_mapping
        )

        cached_payload["validation"] = {
            "validation_status": cached_mapping.get(
                "validationStatus",
                "validated"
            ),
            "reason": "Mapping retrieved from validated cache"
        }

        return {
            "status": "success",
            "count": 1,
            "source": "cache",
            "cache": {
                "hit": True,
                "source": "mapping_cache"
            },
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

        cursor.execute(
            """
            SELECT
                system,
                traditional_term,
                namaste_code,
                tm2_code,
                aliases
            FROM icd_mappings
            WHERE LOWER(system) = LOWER(?)
            """,
            (system_filter.strip(),)
        )

    else:

        cursor.execute(
            """
            SELECT
                system,
                traditional_term,
                namaste_code,
                tm2_code,
                aliases
            FROM icd_mappings
            """
        )

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

        traditional_term = row[1] or ""
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

        tfidf_matrix = vectorizer.fit_transform(
            documents
        )

        query_vector = vectorizer.transform(
            [query]
        )

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

        traditional_term = row[1] or ""
        aliases = row[4] or ""

        traditional_term_lower = (
            traditional_term.lower()
        )

        aliases_list = [
            alias.strip().lower()
            for alias in aliases.split("|")
            if alias.strip()
        ]

        # -----------------------------------------------------
        # Exact traditional term
        # -----------------------------------------------------

        if query == traditional_term_lower:

            confidence = 98.0

        # -----------------------------------------------------
        # Exact alias
        # -----------------------------------------------------

        elif query in aliases_list:

            confidence = 95.0

        # -----------------------------------------------------
        # TF-IDF similarity
        # -----------------------------------------------------

        elif score > 0.1:

            confidence = round(
                score * 100,
                1
            )

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

        # -----------------------------------------------------
        # NAMASTE DATA
        # -----------------------------------------------------

        namaste_data = {
            "code": best_row[2],
            "term": best_row[1]
        }

        # -----------------------------------------------------
        # ICD-11 DATA
        #
        # tm2_code is the standardized code stored in
        # icd_mappings.
        #
        # Your current icd_mappings table does not contain an
        # ICD-11 title column, so we do NOT incorrectly copy
        # traditional_term as the ICD-11 title.
        # -----------------------------------------------------

        icd11_data = {
            "code": best_row[3],
            "term": None
        }

        # -----------------------------------------------------
        # RUN VALIDATION
        # -----------------------------------------------------

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

            # -------------------------------------------------
            # Validation information
            # -------------------------------------------------

            if candidate is best_candidate:

                payload["validation"] = (
                    validation.to_dict()
                )

            else:

                payload["validation"] = {
                    "validation_status": "candidate",
                    "reason": (
                        "Alternative candidate mapping"
                    )
                }

            matched_data.append(payload)

        # -----------------------------------------------------
        # 10. SAVE ONLY VALIDATED MAPPING TO CACHE
        # -----------------------------------------------------

        if validation.status == "validated":

            cache_mapping = {
                "inputTerm": term_query,

                "normalizedTerm": query,

                # -------------------------------------------------
                # Source terminology
                #
                # The current icd_mappings table does not contain
                # rec_id, sys_id, term_id, parent_id, term_iast,
                # w_trans, w_def and refn.
                #
                # Therefore only the available system/term data
                # is filled here.
                # -------------------------------------------------

                "sourceRecord": {
                    "recId": None,
                    "sysId": best_row[0],
                    "termId": None,
                    "parentId": None,
                    "termIast": best_row[1],
                    "translation": None,
                    "definition": None,
                    "reference": None
                },

                # -------------------------------------------------
                # Traditional terminology
                # -------------------------------------------------

                "traditionalTerm": {
                    "term": best_row[1],
                    "system": best_row[0]
                },

                # -------------------------------------------------
                # NAMASTE
                # -------------------------------------------------

                "namaste": {
                    "code": best_row[2],
                    "term": best_row[1]
                },

                # -------------------------------------------------
                # ICD-11
                # -------------------------------------------------

                "icd11": {
                    "code": best_row[3],
                    "title": None,
                    "uri": None
                },

                # -------------------------------------------------
                # Matching information
                # -------------------------------------------------

                "matchScore": (
                    best_candidate["confidence"] / 100
                ),

                "matchType": (
                    "exact"
                    if best_candidate["confidence"] >= 95
                    else "similarity"
                ),

                "matchStatus": "matched",

                # -------------------------------------------------
                # Mapping / validation
                # -------------------------------------------------

                "mappingStatus": "mapped",

                "validationStatus": validation.status,

                # -------------------------------------------------
                # Source
                # -------------------------------------------------

                "source": "local",

                "sourceVersion": "1.0"
            }

            save_mapping_cache(
                cache_mapping
            )

        # -----------------------------------------------------
        # 11. RETURN LOCAL RESULTS
        # -----------------------------------------------------

        return {
            "status": "success",
            "count": len(matched_data),
            "source": "local",
            "cache": {
                "hit": False
            },
            "data": matched_data
        }

    # ---------------------------------------------------------
    # 12. WHO FALLBACK
    # ---------------------------------------------------------

    who_res = search_who_api(term_query)

    if who_res.get("status") == "success":
        return who_res

    # ---------------------------------------------------------
    # 13. NO RESULT
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

    # ---------------------------------------------------------
    # New mapping_cache structure
    # ---------------------------------------------------------

    traditional = (
        cached.get("traditionalTerm") or {}
    )

    namaste = (
        cached.get("namaste") or {}
    )

    icd11 = (
        cached.get("icd11") or {}
    )

    system = (
        traditional.get("system")
        or "unknown"
    )

    traditional_term = (
        traditional.get("term")
        or namaste.get("term")
        or cached.get("inputTerm")
        or ""
    )

    namaste_code = namaste.get("code")

    icd11_code = icd11.get("code")

    confidence = cached.get(
        "matchScore",
        0
    )

    # matchScore is stored as 0-1
    # but older data may contain 0-100.
    if confidence is None:
        confidence = 0

    try:
        confidence = float(confidence)

        if confidence <= 1:
            confidence = confidence * 100

    except (ValueError, TypeError):
        confidence = 0

    confidence = round(
        confidence,
        1
    )

    # ---------------------------------------------------------
    # Medicine Twin
    # ---------------------------------------------------------

    twin_data = get_medicine_twin_data(
        traditional_term
    )

    # ---------------------------------------------------------
    # Modern equivalent
    # ---------------------------------------------------------

    modern_term = get_modern_equivalent(
        traditional_term
    )

    # ---------------------------------------------------------
    # Build FHIR response
    # ---------------------------------------------------------

    coding = []

    # NAMASTE coding
    if namaste_code:

        coding.append({
            "system": (
                f"urn:oid:namaste:{system.lower()}"
            ),
            "code": namaste_code,
            "display": traditional_term
        })

    # ICD-11 coding
    if icd11_code:

        icd11_coding = {
            "system": (
                "http://id.who.int/icd/"
                "release/11/mms"
            ),
            "code": icd11_code
        }

        # Only include title if we actually have one.
        if icd11.get("title"):
            icd11_coding["display"] = (
                icd11.get("title")
            )

        if icd11.get("uri"):
            icd11_coding["userSelected"] = False

        coding.append(
            icd11_coding
        )

    return {
        "resourceType": "Condition",

        "confidenceScore": (
            f"{confidence}%"
        ),

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
            "coding": coding,
            "text": traditional_term
        }
    }


def build_fhir_payload(row, confidence):
    """
    Builds the FHIR Condition payload from a local
    icd_mappings database row.
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

    coding = []

    # ---------------------------------------------------------
    # NAMASTE coding
    # ---------------------------------------------------------

    if namaste:

        coding.append({
            "system": (
                f"urn:oid:namaste:{system.lower()}"
            ),
            "code": namaste,
            "display": traditional_term
        })

    # ---------------------------------------------------------
    # ICD-11 coding
    # ---------------------------------------------------------

    if tm2:

        coding.append({
            "system": (
                "http://id.who.int/icd/"
                "release/11/mms"
            ),
            "code": tm2
        })

    return {
        "resourceType": "Condition",

        "confidenceScore": (
            f"{confidence}%"
        ),

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
            "coding": coding,
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