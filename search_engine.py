import sqlite3

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from who_service import search_who_api
from medicine_twin import get_medicine_twin_data
from search_namaste import search_namaste
from mapping_validator import validate_mapping

DB_FILE = "mappings.db"

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

def normalize_term(term):
    if not term:
        return None

    return " ".join(term.lower().strip().split())


def normalize_for_match(term):
    """
    Normalize terminology for comparison.

    Removes common terminal punctuation/markers used in
    NAMASTE transliteration such as visarga (ḥ) and colon.
    """
    if not term:
        return ""

    value = term.lower().strip()

    # Remove common Sanskrit transliteration markers at the end
    value = value.rstrip("ḥ:")

    # Normalize whitespace
    value = " ".join(value.split())

    return value

def search_local_mappings(normalized_term, rows):
    """
    Search local icd_mappings using exact, alias,
    and TF-IDF similarity matching.
    """
    documents = []
    doc_row_mapping = []

    for row in rows:
        trad_term = row[1]
        aliases = row[4] or ""

        combined_text = f"{trad_term} {aliases.replace('|', ' ')}"
        documents.append(combined_text)
        doc_row_mapping.append(row)

    if not documents:
        return []

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english"
    )

    tfidf_matrix = vectorizer.fit_transform(documents)
    query_vector = vectorizer.transform([normalized_term])

    cosine_scores = cosine_similarity(
        query_vector,
        tfidf_matrix
    ).flatten()

    top_indices = cosine_scores.argsort()[::-1][:3]

    matched_data = []

    for idx in top_indices:
        score = cosine_scores[idx]
        row = doc_row_mapping[idx]

        trad_term = row[1].lower()

        aliases_list = [
            alias.strip().lower()
            for alias in (row[4] or "").split("|")
            if alias.strip()
        ]

        if normalized_term == trad_term:
            confidence = 98.0

        elif normalized_term in aliases_list:
            confidence = 95.0

        elif score > 0.1:
            confidence = round(float(score) * 100, 1)

            if confidence > 90:
                confidence = 90.0

        else:
            continue

        matched_data.append(
            build_fhir_payload(row, confidence)
        )

    return matched_data

def search_namaste_mappings(normalized_term, system_filter=None):
    """
    Search the official NAMASTE terminology table first.

    Returns NAMASTE candidates in the format expected
    by the MedBridge search pipeline.
    """

    namaste_results = search_namaste(
        normalized_term,
        system=system_filter
    )

    if not namaste_results:
        return []

    matched_data = []

    for result in namaste_results:
        term_iast = result.get("term_iast")
        wordtree = result.get("wordtree")
        translation = result.get("w_trans")
        definition = result.get("w_def")

        # Prefer the traditional term itself.
        traditional_term = term_iast or wordtree

        if not traditional_term:
            continue

        # Existing MedBridge mappings can provide a modern
        # clinical concept when we already know the term.
        modern_term = modern_mapping.get(
            normalized_term,
            translation or definition or "Standardized Clinical Concept"
        )

        input_for_match = normalize_for_match(normalized_term)
        term_iast_for_match = normalize_for_match(term_iast)
        wordtree_for_match = normalize_for_match(wordtree)

        if input_for_match in (
            term_iast_for_match,
            wordtree_for_match
        ):
            match_type = "exact"
        else:
            match_type = "candidate"

        matched_data.append({
            "rec_id": result.get("rec_id"),
            "t_id": result.get("t_id"),
            "term_id": result.get("term_id"),
            "term_devanagari": result.get("term_devanagari"),
            "term_iast": term_iast,
            "wordtree": wordtree,
            "parent_id": result.get("parent_id"),
            "def_id": result.get("def_id"),
            "w_trans": translation,
            "w_def": definition,
            "refn": result.get("refn"),
            "sys_id": result.get("sys_id"),
            "traditionalTerm": traditional_term,
            "modernEquivalent": modern_term,
            "matchType": match_type
        })

    return matched_data[:3]

def search_disease(term_query, system_filter=None):
    if not term_query or not term_query.strip():
        return {
            "status": "error",
            "errorCode": "INVALID_INPUT",
            "message": "Search term cannot be empty.",
            "data": []
        }

    normalized_term = normalize_term(term_query)

    if normalized_term.isdigit() or len(normalized_term) < 2:
        return {
            "status": "error",
            "errorCode": "INVALID_INPUT",
            "message": "Invalid clinical search term. Please enter a valid diagnosis name.",
            "data": []
        }

    # ---------------------------------------------------------
    # 1. SEARCH OFFICIAL NAMASTE TERMINOLOGY FIRST
    # ---------------------------------------------------------

    namaste_results = search_namaste_mappings(
        normalized_term,
        system_filter
    )

    if namaste_results:

        final_results = []

        # Use the strongest NAMASTE candidate first
        for namaste in namaste_results:

            modern_term = namaste.get(
                "modernEquivalent"
            )

            # -------------------------------------------------
            # 2. SEARCH WHO ICD-11
            # -------------------------------------------------

            who_query = modern_term or normalized_term

            who_res = search_who_api(who_query)

            icd11_data = None

            if (
                who_res.get("status") == "success"
                and who_res.get("data")
            ):
                who_result = who_res["data"][0]

                coding = (
                    who_result
                    .get("code", {})
                    .get("coding", [])
                )

                # Find the actual WHO ICD-11 coding
                for coding_item in coding:
                    if coding_item.get("system") == (
                        "http://id.who.int/icd/release/11/mms"
                    ):
                        icd11_data = {
                            "code": coding_item.get("code"),
                            "term": (
                                coding_item.get("display")
                                or who_result.get("modernEquivalent")
                            ),
                            "uri": coding_item.get("uri")
                        }
                        break

            # -------------------------------------------------
            # 3. VALIDATE NAMASTE → ICD-11
            # -------------------------------------------------

            if icd11_data:
                validation_input = {
                    **namaste,
                    "mappingStatus": "candidate"
                }

                validation = validate_mapping(
                    validation_input,
                    icd11_data
                )

                validation_data = validation.to_dict()

            else:
                validation_data = {
                    "validation_status": "invalid",
                    "reason": "No ICD-11 candidate found"
                }

            # -------------------------------------------------
            # 4. BUILD COMBINED RESULT
            # -------------------------------------------------

            result = {
                "inputTerm": term_query,
                "normalizedTerm": normalized_term,

                "sourceRecord": {
                    "recId": namaste.get("rec_id"),
                    "sysId": namaste.get("sys_id"),
                    "termId": namaste.get("term_id"),
                    "parentId": namaste.get("parent_id"),
                    "termIast": namaste.get("term_iast"),
                    "translation": namaste.get("w_trans"),
                    "definition": namaste.get("w_def"),
                    "reference": namaste.get("refn")
                },

                "traditionalTerm": {
                    "term": namaste.get("traditionalTerm"),
                    "system": (
                        str(namaste.get("sys_id"))
                        if namaste.get("sys_id") is not None
                        else None
                    ),
                    "code": namaste.get("term_id")
                },

                "namaste": {
                    "code": namaste.get("term_id"),
                    "term": namaste.get("traditionalTerm"),
                    "source": "NAMASTE",
                    "sourceVersion": None
                },

                "icd11": (
                    {
                        "code": icd11_data.get("code"),
                        "title": icd11_data.get("term"),
                        "uri": icd11_data.get("uri"),
                        "source": "WHO ICD-11"
                    }
                    if icd11_data
                    else None
                ),

                # Current exact match gets a high score.
                # Candidate matches use a lower score until
                # a proper ranked scoring layer is integrated.
                "matchScore": (
                    98.0
                    if namaste.get("matchType") == "exact"
                    else 80.0
                ),

                "matchType": namaste.get(
                    "matchType",
                    "candidate"
                ),

                "mappingStatus": (
                    "candidate"
                    if icd11_data
                    else "unverified"
                ),

                "validationStatus": validation_data[
                    "validation_status"
                ],

                "source": "MEDBRIDGE_DERIVED",

                "sourceVersion": None,

                "evidence": [
                    "Official NAMASTE terminology found"
                ]
            }

            if icd11_data:
                result["evidence"].append(
                    "WHO ICD-11 candidate found"
                )

            result["evidence"].append(
                validation_data["reason"]
            )

            final_results.append(result)

        return {
            "status": "success",
            "count": len(final_results),
            "data": final_results
        }

    # ---------------------------------------------------------
    # 5. TEMPORARY LEGACY FALLBACK
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

    if rows:
        matched_data = search_local_mappings(
            normalized_term,
            rows
        )

        if matched_data:
            return {
                "status": "success",
                "count": len(matched_data),
                "data": matched_data
            }

    # ---------------------------------------------------------
    # 6. WHO FALLBACK
    # ---------------------------------------------------------

    who_query = modern_mapping.get(
        normalized_term,
        normalized_term
    )

    who_res = search_who_api(who_query)

    if who_res.get("status") == "success":
        return who_res

    return {
        "status": "error",
        "errorCode": "TERM_NOT_FOUND",
        "message": (
            f"No reliable clinical mapping found for "
            f"'{normalized_term}' locally or via WHO API."
        ),
        "data": []
    }

def build_fhir_payload(row, confidence):
    system = row[0]
    trad_term = row[1]
    namaste = row[2]
    tm2 = row[3]

    

    modern_term = modern_mapping.get(trad_term.lower(), "Standardized Clinical Presentation")

    twin_data = get_medicine_twin_data(trad_term)

    return {
        "resourceType": "Condition",
        "confidenceScore": f"{confidence}%",
        "modernEquivalent": modern_term,
        
        # 🚀 INJECTED: The Medicine Twin & Risk Radar Payload
        "medicineTwin": {
            "activeIngredients": twin_data.get("activeIngredients", []),
            "traditionalUses": twin_data.get("traditionalUses", []),
            "riskRadar": twin_data.get("riskRadar", [])
        },
        
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
        },
        "code": {
            "coding": [
                {"system": f"urn:oid:namaste:{system.lower()}", "code": namaste, "display": trad_term},
                {"system": "http://id.who.int/icd/release/11/mms", "code": tm2}
            ],
            "text": trad_term
        }
    }