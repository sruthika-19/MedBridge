from typing import List, Dict, Optional


# Synthetic/demo patients only
PATIENTS: Dict[str, dict] = {
    "P001": {
        "patient_id": "P001",
        "name": "Arun Kumar",
        "age": 42,
        "gender": "Male",
        "conditions": [],
        "namaste_codes": [],
        "icd11_codes": []
    },
    "P002": {
        "patient_id": "P002",
        "name": "Meena Devi",
        "age": 35,
        "gender": "Female",
        "conditions": [],
        "namaste_codes": [],
        "icd11_codes": []
    },
    "P003": {
        "patient_id": "P003",
        "name": "Karthik Raj",
        "age": 58,
        "gender": "Male",
        "conditions": [],
        "namaste_codes": [],
        "icd11_codes": []
    }
}


def get_all_patients() -> List[dict]:
    """Return all synthetic patients."""
    return list(PATIENTS.values())


def get_patient(patient_id: str) -> Optional[dict]:
    """Return one synthetic patient."""
    return PATIENTS.get(patient_id)


def add_condition_to_patient(
    patient_id: str,
    condition: str,
    namaste_code: Optional[str] = None,
    icd11_code: Optional[str] = None
) -> Optional[dict]:
    """Attach a mapped condition to a synthetic patient."""

    patient = PATIENTS.get(patient_id)

    if not patient:
        return None

    if condition and condition not in patient["conditions"]:
        patient["conditions"].append(condition)

    if namaste_code and namaste_code not in patient["namaste_codes"]:
        patient["namaste_codes"].append(namaste_code)

    if icd11_code and icd11_code not in patient["icd11_codes"]:
        patient["icd11_codes"].append(icd11_code)

    return patient