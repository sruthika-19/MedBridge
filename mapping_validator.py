class ValidationResult:
    def __init__(self, status, reason=""):
        self.status = status
        self.reason = reason

    def to_dict(self):
        return {
            "validation_status": self.status,
            "reason": self.reason
        }


def check_ambiguity(candidates):
    """
    Returns True when the top two candidates are within
    5 confidence points of each other.
    """

    if not candidates or len(candidates) < 2:
        return False

    try:
        first_score = float(
            candidates[0].get("matchScore", 0)
        )
        second_score = float(
            candidates[1].get("matchScore", 0)
        )
    except (TypeError, ValueError):
        return False

    return abs(first_score - second_score) <= 5


def validate_mapping(namaste, icd11, candidates=None):
    """
    Validate a NAMASTE -> ICD-11 mapping.

    Important:
    Finding a WHO ICD-11 candidate does NOT automatically
    make the mapping authoritative.

    A mapping is considered validated only when its
    mappingStatus is explicitly 'official'.
    """

    # ---------------------------------------------------------
    # 1. NAMASTE must exist
    # ---------------------------------------------------------

    if not namaste:
        return ValidationResult(
            "invalid",
            "NAMASTE mapping is missing"
        )

    namaste_code = (
        namaste.get("code")
        or namaste.get("term_id")
    )

    namaste_term = (
        namaste.get("term")
        or namaste.get("traditionalTerm")
        or namaste.get("term_iast")
    )

    if not namaste_code:
        return ValidationResult(
            "invalid",
            "NAMASTE terminology identifier is missing"
        )

    if not namaste_term:
        return ValidationResult(
            "invalid",
            "NAMASTE term is missing"
        )

    # ---------------------------------------------------------
    # 2. ICD-11 must exist
    # ---------------------------------------------------------

    if not icd11:
        return ValidationResult(
            "invalid",
            "ICD-11 mapping is missing"
        )

    icd11_code = icd11.get("code")

    icd11_term = (
        icd11.get("term")
        or icd11.get("title")
        or icd11.get("display")
    )

    if not icd11_code:
        return ValidationResult(
            "invalid",
            "ICD-11 code is missing"
        )

    if not icd11_term:
        return ValidationResult(
            "invalid",
            "ICD-11 title is missing"
        )

    # ---------------------------------------------------------
    # 3. Ambiguity check
    # ---------------------------------------------------------

    if candidates and check_ambiguity(candidates):
        return ValidationResult(
            "needs_review",
            "Top candidates have similar confidence scores"
        )

    # ---------------------------------------------------------
    # 4. Only official mappings are validated
    # ---------------------------------------------------------

    mapping_status = (
        namaste.get("mappingStatus")
        or namaste.get("mapping_status")
        or "candidate"
    )

    if mapping_status != "official":
        return ValidationResult(
            "needs_review",
            "ICD-11 result is a candidate mapping and "
            "does not have authoritative crosswalk evidence"
        )

    # ---------------------------------------------------------
    # 5. Official mapping
    # ---------------------------------------------------------

    return ValidationResult(
        "validated",
        "Mapping passed validation as an official mapping"
    )