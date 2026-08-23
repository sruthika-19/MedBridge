import os
import json
from google import genai
from google.genai import types
from search_engine import search_disease
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") 

if not api_key:
    print("CRITICAL ERROR: GEMINI_API_KEY is missing! Check your .env file.")

# NEW: Initialize the client using the new SDK
client = genai.Client(api_key=api_key)

def extract_and_bundle_notes(doctor_paragraph: str):
    prompt = f"""
    You are an expert clinical AI assistant. Extract ONLY the medical conditions, diseases, and symptoms from the following text.
    Do NOT extract general words, timeframes, or locations (like 'clinic', 'weeks', 'severe', 'patient').
    
    You MUST return a valid JSON array of strings representing the extracted terms.
    Example: ["jvara", "kasa", "prameha"]
    
    Text: "{doctor_paragraph}"
    """
    
    try:
        # NEW: generate_content uses the client.models syntax now
        response = client.models.generate_content(
            model='gemini-3.6-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        raw_text = response.text.strip()
        print(f"RAW AI RESPONSE: {raw_text}") 
        
        # Strip Markdown if the AI stubbornly includes it
        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            print(f"CLEANED TEXT: {raw_text}")

        # Safely parse the JSON
        terms = json.loads(raw_text)
        
        if isinstance(terms, dict):
            for key, val in terms.items():
                if isinstance(val, list):
                    terms = val
                    break
            else:
                terms = []

    except Exception as e:
        error_message = str(e)
        print(f"AI Extraction Error: {error_message}")
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