import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("CRITICAL ERROR: GROQ_API_KEY is missing! Check your .env file.")

client = Groq(api_key=groq_api_key)

# The Dedicated Cache
ai_risk_cache = {
    "jvara": {
        "ingredients": ["Nilavembu", "Guduchi", "Parpata"],
        "traditional_uses": ["Antipyretic", "Immunomodulator"],
        "risk_warnings": ["None significant, monitor hydration"]
    },
    "suram": {
        "ingredients": ["Nilavembu", "Parpata"],
        "traditional_uses": ["Fever Reducer"],
        "risk_warnings": ["None significant"]
    },
    "kasa": {
        "ingredients": ["Tulsi", "Licorice (Mulethi)"],
        "traditional_uses": ["Bronchodilator", "Expectorant"],
        "risk_warnings": ["⚠️ AI Alert: Licorice can cause potassium depletion if taken with Diuretics"]
    },
    "irumal": {
        "ingredients": ["Adathoda", "Tulsi"],
        "traditional_uses": ["Cough relief"],
        "risk_warnings": ["None significant"]
    },
    "sandhigata vata": {
        "ingredients": ["Ashwagandha", "Guggulu", "Shallaki"],
        "traditional_uses": ["Anti-inflammatory", "Joint Lubrication"],
        "risk_warnings": ["⚠️ AI Alert: Ashwagandha + Blood Thinners = Bleeding Risk"]
    },
    "prameha": {
        "ingredients": ["Gymnema sylvestre", "Curcuma longa", "Emblica officinalis"],
        "traditional_uses": ["Management of diabetes mellitus", "Metabolic syndrome"],
        "risk_warnings": ["⚠️ AI Alert: Combining with insulin/metformin may cause severe hypoglycemia."]
    },

    "shoola": {
        "ingredients": ["Zingiber officinale", "Ferula foetida", "Trachyspermum ammi"],
        "traditional_uses": ["Relief of acute abdominal colic", "Management of indigestion"],
        "risk_warnings": ["⚠️ AI Alert: Combining with synthetic NSAIDs increases gastrointestinal bleeding risks."]
    },
    "gunmam": {
        "ingredients": ["Cuminum cyminum", "Zingiber officinale", "Rock Salt"],
        "traditional_uses": ["Gastritis and acidity management"],
        "risk_warnings": ["⚠️ AI Alert: May interact with proton pump inhibitors."]
    },
    "pandu": {
        "ingredients": ["Punarnava", "Amalaki", "Guduchi"],
        "traditional_uses": ["Management of iron-deficiency anemia and chronic fatigue"],
        "risk_warnings": ["⚠️ AI Alert: Combining traditional iron remedies with modern supplements can cause iron toxicity."]
    }
}

def get_medicine_twin_data(trad_term):
    if not groq_api_key:
        return {"ingredients": ["API Key Missing"], "traditional_uses": [""], "risk_warnings": [""]}
        
    term_key = trad_term.lower()

    if term_key in ai_risk_cache:
        return ai_risk_cache[term_key]
        
    print(f"⚠️ CACHE MISS! Firing live AI request for: {term_key}")
    
    prompt = f"""
    You are an expert pharmacology AI. Analyze the traditional medical term: "{trad_term}".
    Return a valid JSON object with exactly these three keys:
    1. "ingredients": Array of 2-3 traditional herbs.
    2. "traditional_uses": Array of 1-2 primary clinical uses.
    3. "risk_warnings": Array of 1-2 severe warnings if mixed with modern allopathic drugs. Start warning with '⚠️ AI Alert:'.
    """
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a clinical pharmacology expert that outputs strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        raw_text = completion.choices[0].message.content.strip()
        data = json.loads(raw_text)
        ai_risk_cache[term_key] = data
        return data

    except Exception as e:
        error_msg = str(e)
        print(f"Risk Radar Groq Error: {error_msg}")
        return {
            "ingredients": ["Data unavailable"],
            "traditional_uses": ["Data unavailable"],
            "risk_warnings": ["⚠️ System could not fetch interaction risks."]
        }