import sqlite3

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from who_service import search_who_api
from medicine_twin import get_medicine_twin_data

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
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if system_filter and system_filter.strip() and system_filter.lower() != "all":
        cursor.execute("""
            SELECT system, traditional_term, namaste_code, tm2_code, aliases
            FROM icd_mappings
            WHERE LOWER(system) = LOWER(?)
        """, (system_filter.strip(),))
    else:
        cursor.execute("""
            SELECT system, traditional_term, namaste_code, tm2_code, aliases
            FROM icd_mappings
        """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "status": "error",
            "errorCode": "DATABASE_ERROR",
            "message": "Database is empty.",
            "data": []
        }
        
    matched_data = search_local_mappings(normalized_term, rows)

    if matched_data:
        return {
            "status": "success",
            "count": len(matched_data),
            "data": matched_data
        }

    # If it's a modern clinical term not in the local traditional dataset, instantly query WHO
    who_res = search_who_api(normalized_term)
    if who_res.get("status") == "success":
        return who_res

    return {
        "status": "error",
        "errorCode": "TERM_NOT_FOUND",
        "message": f"No reliable clinical mapping found for '{normalized_term}' locally or via WHO API.",
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