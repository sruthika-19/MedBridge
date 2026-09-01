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
    Checks whether the top two candidates have similar confidence scores.

    A difference of 5 or less is considered ambiguous.
    """

    if not candidates or len(candidates) < 2:
        return False

    first_score = float(candidates[0].get("score", 0))
    second_score = float(candidates[1].get("score", 0))

    difference = abs(first_score - second_score)

    return difference <= 5


def validate_mapping(namaste, icd11, candidates=None):
    """
    Validates a NAMASTE to ICD-11 mapping.

    namaste:
        Dictionary containing code and term.

    icd11:
        Dictionary containing code and term.

    candidates:
        Ranked candidate mappings with confidence scores.
    """

    # Check NAMASTE
    if not namaste:
        return ValidationResult(
            "invalid",
            "NAMASTE mapping is missing"
        )

    # Check ICD-11
    if not icd11:
        return ValidationResult(
            "invalid",
            "ICD-11 mapping is missing"
        )

    # Check NAMASTE code
    if not namaste.get("code"):
        return ValidationResult(
            "invalid",
            "NAMASTE code is missing"
        )

    # Check NAMASTE term
    if not namaste.get("term"):
        return ValidationResult(
            "invalid",
            "NAMASTE term is missing"
        )

    # Check ICD-11 code
    if not icd11.get("code"):
        return ValidationResult(
            "invalid",
            "ICD-11 code is missing"
        )

    # Check ICD-11 term
    if not icd11.get("term"):
        return ValidationResult(
            "invalid",
            "ICD-11 term is missing"
        )

    # Check ambiguity
    if candidates and check_ambiguity(candidates):
        return ValidationResult(
            "needs_review",
            "Top candidates have similar confidence scores"
        )

    return ValidationResult(
        "validated",
        "Mapping passed validation"
    )