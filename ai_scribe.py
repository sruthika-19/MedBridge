import os
import json
from groq import Groq
from search_engine import search_disease
from dotenv import load_dotenv

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("CRITICAL ERROR: GROQ_API_KEY is missing! Check your .env file.")

client = Groq(api_key=groq_api_key)

def extract_and_bundle_notes(doctor_paragraph: str):
    prompt = f"""
    You are an expert clinical AI assistant specializing in both modern medicine and Indian traditional medical terminology. 
    Extract all medical conditions, diseases, symptoms, or traditional terms from the following text.
    CRITICAL: This includes English terms, Sanskrit terms (like jvara), and transliterated regional Indian terms (such as Tamil words like 'irumal' for cough, 'suram' for fever, etc.). 
    If the text is a single symptom or term, extract it directly.
    
    Do NOT extract general words, timeframes, or locations (like 'clinic', 'weeks', 'severe', 'patient').
    
    You MUST return a valid JSON object containing an array of strings under the key "terms".
    Example: {{"terms": ["irumal", "jvara", "kasa"]}}
    
    Text: "{doctor_paragraph}"
"""
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a precise clinical terminology extraction assistant that outputs strictly valid JSON with a 'terms' key."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        raw_text = completion.choices[0].message.content.strip()
        print(f"RAW GROQ RESPONSE: {raw_text}") 
        
        parsed_data = json.loads(raw_text)
        
        # Extract terms safely from JSON response
        if isinstance(parsed_data, list):
            terms = parsed_data
        elif isinstance(parsed_data, dict):
            terms = parsed_data.get("terms", [])
            if not terms:
                for key, val in parsed_data.items():
                    if isinstance(val, list):
                        terms = val
                        break
        else:
            terms = []

    except Exception as e:
        error_message = str(e)
        print(f"Groq Extraction Error: {error_message}")
        # Smart fallback to local keyword matching if any network glitch occurs
        known_terms = ["jvara", "suram", "kasa", "irumal", "sandhigata vata", "prameha", "shoola", "gunmam", "pandu", "anxiety"]
        terms = [t for t in known_terms if t in doctor_paragraph.lower()]
        
        if not terms:
            return {
                "status": "error",
                "extractedTerms": [],
                "message": f"AI FAILED: {error_message}",
                "bundle": None
            }

        # ---------------------------------------------------------
    # FHIR PATIENT
    # Synthetic patient for demonstration purposes
    # ---------------------------------------------------------

    patient_id = "patient-demo-001"

    patient_resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "system": "urn:medbridge:synthetic-patient",
                "value": patient_id
            }
        ],
        "name": [
            {
                "text": "Demo Patient"
            }
        ],
        "gender": "unknown"
    }

    # ---------------------------------------------------------
    # FHIR ENCOUNTER
    # ---------------------------------------------------------

    encounter_id = "encounter-demo-001"

    encounter_resource = {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        }
    }

    # ---------------------------------------------------------
    # FHIR CONDITIONS
    # ---------------------------------------------------------

    fhir_entries = []

    for index, term in enumerate(terms, start=1):

        if not isinstance(term, str):
            continue

        search_result = search_disease(term)

        if (
            search_result.get("status") != "success"
            or not search_result.get("data")
        ):
            continue

        mapping = search_result["data"][0]

        namaste = mapping.get("namaste") or {}
        icd11 = mapping.get("icd11") or {}
        traditional = mapping.get("traditionalTerm") or {}

        # Do not create a FHIR Condition for an unmapped term.
        # Prevents fake 0% / empty-code conditions from appearing in AI Scribe.
        if not namaste.get("code") and not icd11.get("code"):
            continue

        condition_id = f"condition-demo-{index}"
        coding = []

        # -----------------------------------------------------
        # NAMASTE coding
        # -----------------------------------------------------

        if namaste.get("code"):
            coding.append({
                "system": "https://terminology.ayush.gov.in/namaste",
                "code": namaste.get("code"),
                "display": namaste.get("term")
            })

        # -----------------------------------------------------
        # WHO ICD-11 coding
        # -----------------------------------------------------

        if icd11.get("code"):
            coding.append({
                "system": "http://id.who.int/icd/release/11/mms",
                "code": icd11.get("code"),
                "display": icd11.get("title")
            })

        condition_resource = {
            "resourceType": "Condition",
            "id": condition_id,

            "subject": {
                "reference": f"Patient/{patient_id}"
            },

            "encounter": {
                "reference": f"Encounter/{encounter_id}"
            },

            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                        "display": "Active"
                    }
                ]
            },

            "code": {
                "coding": coding,
                "text": (
                    traditional.get("term")
                    or mapping.get("inputTerm")
                )
            },

            # Keep MedBridge mapping information as extensions
            # rather than pretending these are native FHIR fields.
            "extension": [
                {
                    "url": "https://medbridge.local/fhir/StructureDefinition/match-score",
                    "valueDecimal": float(
                        mapping.get("matchScore", 0)
                    )
                },
                {
                    "url": "https://medbridge.local/fhir/StructureDefinition/match-type",
                    "valueString": mapping.get(
                        "matchType",
                        "candidate"
                    )
                },
                {
                    "url": "https://medbridge.local/fhir/StructureDefinition/mapping-status",
                    "valueString": mapping.get(
                        "mappingStatus",
                        "candidate"
                    )
                },
                {
                    "url": "https://medbridge.local/fhir/StructureDefinition/validation-status",
                    "valueString": mapping.get(
                        "validationStatus",
                        "not_checked"
                    )
                }
            ]
        }

        fhir_entries.append({
            "fullUrl": f"urn:uuid:{condition_id}",
            "resource": condition_resource
        })

    # ---------------------------------------------------------
    # FHIR BUNDLE
    # ---------------------------------------------------------

    fhir_bundle = {
        "resourceType": "Bundle",
        "id": "medbridge-demo-bundle-001",
        "type": "collection",

        "total": (
            2 + len(fhir_entries)
        ),

        "entry": [
            {
                "fullUrl": f"urn:uuid:{patient_id}",
                "resource": patient_resource
            },
            {
                "fullUrl": f"urn:uuid:{encounter_id}",
                "resource": encounter_resource
            },
            *fhir_entries
        ]
    }

    return {
        "status": "success",
        "extractedTerms": terms,
        "bundle": fhir_bundle
    }