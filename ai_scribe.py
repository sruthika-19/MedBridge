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

    fhir_entries = []
    
    for term in terms:
        if not isinstance(term, str): 
            continue
            
        search_result = search_disease(term)
        
        if search_result.get("status") == "success" and search_result.get("data"):
            best_match = search_result["data"][0]
            
            fhir_entries.append({
                "fullUrl": f"urn:uuid:condition-{term.lower().replace(' ', '-')}",
                "resource": best_match
            })

    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "total": len(fhir_entries),
        "entry": fhir_entries
    }

    return {
        "status": "success",
        "extractedTerms": terms,
        "bundle": fhir_bundle
    }