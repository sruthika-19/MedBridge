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
        "activeIngredients": ["Nilavembu", "Guduchi", "Parpata"],
        "traditionalUses": ["Antipyretic", "Immunomodulator"],
        "riskRadar": ["None significant, monitor hydration"]
    },
    "suram": {
        "activeIngredients": ["Nilavembu", "Parpata"],
        "traditionalUses": ["Fever Reducer"],
        "riskRadar": ["None significant"]
    },
    "kasa": {
        "activeIngredients": ["Tulsi", "Licorice (Mulethi)"],
        "traditionalUses": ["Bronchodilator", "Expectorant"],
        "riskRadar": ["⚠️ AI Alert: Licorice can cause potassium depletion if taken with Diuretics"]
    },
    "irumal": {
        "activeIngredients": ["Adathoda", "Tulsi"],
        "traditionalUses": ["Cough relief"],
        "riskRadar": ["None significant"]
    },
    "sandhigata vata": {
        "activeIngredients": ["Ashwagandha", "Guggulu", "Shallaki"],
        "traditionalUses": ["Anti-inflammatory", "Joint Lubrication"],
        "riskRadar": ["⚠️ AI Alert: Ashwagandha + Blood Thinners = Bleeding Risk"]
    },
    "prameha": {
        "activeIngredients": ["Gymnema sylvestre", "Curcuma longa", "Emblica officinalis"],
        "traditionalUses": ["Management of diabetes mellitus", "Metabolic syndrome"],
        "riskRadar": ["⚠️ AI Alert: Combining with insulin/metformin may cause severe hypoglycemia."]
    },

    "shoola": {
        "activeIngredients": ["Zingiber officinale", "Ferula foetida", "Trachyspermum ammi"],
        "traditionalUses": ["Relief of acute abdominal colic", "Management of indigestion"],
        "riskRadar": ["⚠️ AI Alert: Combining with synthetic NSAIDs increases gastrointestinal bleeding risks."]
    },
    "gunmam": {
        "activeIngredients": ["Cuminum cyminum", "Zingiber officinale", "Rock Salt"],
        "traditionalUses": ["Gastritis and acidity management"],
        "riskRadar": ["⚠️ AI Alert: May interact with proton pump inhibitors."]
    },
    "pandu": {
        "activeIngredients": ["Punarnava", "Amalaki", "Guduchi"],
        "traditionalUses": ["Management of iron-deficiency anemia and chronic fatigue"],
        "riskRadar": ["⚠️ AI Alert: Combining traditional iron remedies with modern supplements can cause iron toxicity."]
    }
}

def get_medicine_twin_data(trad_term):
    if not groq_api_key:
        return {"activeIngredients": ["API Key Missing"], "traditionalUses": [""], "riskRadar": [""]}
        
    term_key = trad_term.lower()

    if term_key in ai_risk_cache:
        return ai_risk_cache[term_key]
        
    print(f"⚠️ CACHE MISS! Firing live AI request for: {term_key}")
    
    prompt = f"""
    You are an expert pharmacology AI. Analyze the traditional medical term: "{trad_term}".
    Return a valid JSON object with exactly these three keys:
    1. "activeIngredients": Array of 2-3 traditional herbs.
    2. "traditionalUses": Array of 1-2 primary clinical uses.
    3. "riskRadar": Array of 1-2 severe warnings if mixed with modern allopathic drugs. Start warning with '⚠️ AI Alert:'.
    Return ONLY a valid JSON object. Do not include markdown code blocks, backticks, or extra text.
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
            "activeIngredients": ["Data unavailable"],
            "traditionalUses": ["Data unavailable"],
            "riskRadar": ["⚠️ System could not fetch interaction risks."]
        }