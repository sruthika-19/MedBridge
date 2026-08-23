import os
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_ENDPOINT = "https://icdaccessmanagement.who.int/connect/token"
ICD_SEARCH_URL = "https://id.who.int/icd/release/11/2024-01/mms/search"

CLIENT_ID = os.environ.get("WHO_CLIENT_ID")
CLIENT_SECRET = os.environ.get("WHO_CLIENT_SECRET")
SCOPE = "icdapi_access"
REQUEST_TIMEOUT = 10

_token_cache = {"access_token": None, "expires_at": 0.0}

def _strip_markup(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()

def get_who_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] - 30 > now:
        return _token_cache["access_token"]

    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("WHO_CLIENT_ID or WHO_CLIENT_SECRET environment variables are not set.")

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
        "grant_type": "client_credentials",
    }

    response = requests.post(TOKEN_ENDPOINT, data=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    token_data = response.json()

    _token_cache["access_token"] = token_data["access_token"]
    _token_cache["expires_at"] = now + float(token_data.get("expires_in", 3600))
    return _token_cache["access_token"]

def search_who_api(term: str, max_results: int = 1) -> dict:
    try:
        token = get_who_token()
    except Exception as exc:
        return {"status": "error", "message": f"WHO API auth failed: {exc}", "data": []}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Accept-Language": "en",
        "API-Version": "v2",
    }
    params = {"q": term, "useFlexisearch": "true", "flatResults": "true"}

    try:
        response = requests.get(ICD_SEARCH_URL, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {"status": "error", "message": f"WHO API request failed: {exc}", "data": []}

    body = response.json()
    entities = body.get("destinationEntities", [])

    if not entities:
        return {"status": "error", "message": f"No WHO match found for '{term}'.", "data": []}

    results = []
    for entity in entities[:max_results]:
        title = _strip_markup(entity.get("title", ""))
        icd_code = entity.get("theCode") or entity.get("code") or "N/A"
        entity_uri = entity.get("id", "")
        raw_score = entity.get("score")
        confidence = f"{round(float(raw_score) * 100, 1)}%" if raw_score is not None else "85.0%"

        fhir_payload = {
            "resourceType": "Condition",
            "confidenceScore": confidence,
            "modernEquivalent": title or "Live WHO ICD-11 Entity",
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
            },
            "code": {
                "coding": [
                    {
                        "system": "urn:oid:namaste:who_icd11",
                        "code": icd_code,
                        "display": title
                    },
                    {
                        "system": "http://id.who.int/icd/release/11/mms",
                        "code": icd_code,
                        "uri": entity_uri
                    }
                ],
                "text": title,
            },
        }
        results.append(fhir_payload)

    return {"status": "success", "count": len(results), "data": results}
