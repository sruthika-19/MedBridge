import os
import json
import uuid

from groq import Groq
from search_engine import search_disease
from dotenv import load_dotenv

from patient_module import get_patient


load_dotenv()


# ============================================================
# GROQ CONFIGURATION
# ============================================================

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    print(
        "CRITICAL ERROR: GROQ_API_KEY is missing! "
        "Check your .env file."
    )

client = Groq(api_key=groq_api_key)


# ============================================================
# FHIR PATIENT RESOURCE
# ============================================================

def build_fhir_patient(patient: dict) -> dict:
    """
    Convert a MedBridge synthetic patient into
    a FHIR R4 Patient resource.
    """

    gender = patient.get("gender", "").lower()

    if gender not in ["male", "female", "other", "unknown"]:
        gender = "unknown"

    return {
        "resourceType": "Patient",
        "id": patient["patient_id"],
        "identifier": [
            {
                "system": "https://medbridge.example/patient-id",
                "value": patient["patient_id"]
            }
        ],
        "name": [
            {
                "text": patient["name"]
            }
        ],
        "gender": gender
    }


# ============================================================
# FHIR ENCOUNTER RESOURCE
# ============================================================

def build_fhir_encounter(
    patient_id: str,
    encounter_id: str
) -> dict:
    """
    Create a FHIR R4 Encounter linked to the patient.
    """

    return {
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


# ============================================================
# FHIR CONDITION RESOURCE
# ============================================================

def build_fhir_condition(
    condition_resource: dict,
    patient_id: str,
    encounter_id: str,
    condition_id: str
) -> dict:
    """
    Convert the mapping result into a FHIR R4 Condition
    and establish Patient/Encounter relationships.
    """

    condition = dict(condition_resource)

    # Ensure the resource is identified as a FHIR Condition
    condition["resourceType"] = "Condition"
    condition["id"] = condition_id

    # Link Condition -> Patient
    condition["subject"] = {
        "reference": f"Patient/{patient_id}"
    }

    # Link Condition -> Encounter
    condition["encounter"] = {
        "reference": f"Encounter/{encounter_id}"
    }

    return condition


# ============================================================
# AI SCRIBE + FHIR BUNDLE
# ============================================================

def extract_and_bundle_notes(
    doctor_paragraph: str,
    patient_id: str = "P001"
):
    """
    Extract medical terms from clinical notes,
    map them using MedBridge terminology services,
    and generate a FHIR bundle containing:

        Patient
          ↓
        Encounter
          ↓
        Condition(s)
    """

    # --------------------------------------------------------
    # GET PATIENT
    # --------------------------------------------------------

    patient = get_patient(patient_id)

    if patient is None:
        return {
            "status": "error",
            "extractedTerms": [],
            "message": f"Patient {patient_id} not found.",
            "bundle": None
        }


    # --------------------------------------------------------
    # AI EXTRACTION PROMPT
    # --------------------------------------------------------

    prompt = f"""
    You are an expert clinical AI assistant specializing in
    both modern medicine and Indian traditional medical
    terminology.

    Extract all medical conditions, diseases, symptoms, or
    traditional terms from the following text.

    CRITICAL:
    This includes English terms, Sanskrit terms such as
    'jvara', and transliterated regional Indian terms such
    as Tamil words like 'irumal' for cough and 'suram' for
    fever.

    If the text is a single symptom or term, extract it directly.

    Do NOT extract general words, timeframes, or locations
    such as 'clinic', 'weeks', 'severe', or 'patient'.

    You MUST return a valid JSON object containing an array
    of strings under the key "terms".

    Example:
    {{"terms": ["irumal", "jvara", "kasa"]}}

    Text: "{doctor_paragraph}"
    """


    # --------------------------------------------------------
    # AI TERM EXTRACTION
    # --------------------------------------------------------

    try:

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content":
                        "You are a precise clinical terminology "
                        "extraction assistant that outputs strictly "
                        "valid JSON with a 'terms' key."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={
                "type": "json_object"
            },
            temperature=0.1
        )

        raw_text = (
            completion
            .choices[0]
            .message
            .content
            .strip()
        )

        print(
            f"RAW GROQ RESPONSE: {raw_text}"
        )

        parsed_data = json.loads(raw_text)


        # Safely extract terms
        if isinstance(parsed_data, list):

            terms = parsed_data

        elif isinstance(parsed_data, dict):

            terms = parsed_data.get(
                "terms",
                []
            )

            if not terms:

                for key, value in parsed_data.items():

                    if isinstance(value, list):

                        terms = value
                        break

        else:

            terms = []


    except Exception as e:

        error_message = str(e)

        print(
            f"Groq Extraction Error: {error_message}"
        )

        # Local fallback
        known_terms = [
            "jvara",
            "suram",
            "kasa",
            "irumal",
            "sandhigata vata",
            "prameha",
            "shoola",
            "gunmam",
            "pandu",
            "anxiety"
        ]

        terms = [
            term
            for term in known_terms
            if term in doctor_paragraph.lower()
        ]


        if not terms:

            return {
                "status": "error",
                "extractedTerms": [],
                "message":
                    f"AI FAILED: {error_message}",
                "bundle": None
            }


    # --------------------------------------------------------
    # CREATE FHIR IDs
    # --------------------------------------------------------

    encounter_id = (
        f"encounter-{uuid.uuid4().hex[:8]}"
    )


    # --------------------------------------------------------
    # CREATE PATIENT RESOURCE
    # --------------------------------------------------------

    patient_resource = build_fhir_patient(
        patient
    )


    # --------------------------------------------------------
    # CREATE ENCOUNTER RESOURCE
    # --------------------------------------------------------

    encounter_resource = build_fhir_encounter(
        patient_id=patient_id,
        encounter_id=encounter_id
    )


    # --------------------------------------------------------
    # FHIR ENTRIES
    # --------------------------------------------------------

    fhir_entries = []


    # Patient
    fhir_entries.append(
        {
            "fullUrl":
                f"urn:uuid:{patient_id}",

            "resource":
                patient_resource
        }
    )


    # Encounter
    fhir_entries.append(
        {
            "fullUrl":
                f"urn:uuid:{encounter_id}",

            "resource":
                encounter_resource
        }
    )


    # --------------------------------------------------------
    # MAP EACH EXTRACTED TERM
    # --------------------------------------------------------

    mapped_conditions = []

    for term in terms:

        if not isinstance(term, str):
            continue

        term = term.strip()

        if not term:
            continue


        search_result = search_disease(
            term
        )


        if (
            search_result.get("status")
            == "success"
            and search_result.get("data")
        ):

            best_match = search_result["data"][0]


            condition_id = (
                f"condition-"
                f"{uuid.uuid4().hex[:8]}"
            )


            condition_resource = (
                build_fhir_condition(
                    condition_resource=best_match,
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    condition_id=condition_id
                )
            )


            fhir_entries.append(
                {
                    "fullUrl":
                        f"urn:uuid:{condition_id}",

                    "resource":
                        condition_resource
                }
            )


            mapped_conditions.append(
                {
                    "term": term,
                    "status": "mapped",
                    "condition": condition_resource
                }
            )

        else:

            mapped_conditions.append(
                {
                    "term": term,
                    "status": "unmapped"
                }
            )


    # --------------------------------------------------------
    # FHIR R4 BUNDLE
    # --------------------------------------------------------

    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "total": len(fhir_entries),
        "entry": fhir_entries
    }


    # --------------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------------

    return {
        "status": "success",
        "patient": {
            "patient_id": patient["patient_id"],
            "name": patient["name"]
        },
        "extractedTerms": terms,
        "mappedConditions": mapped_conditions,
        "bundle": fhir_bundle
    }