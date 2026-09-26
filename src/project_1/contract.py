import json


MAX_RATIONALE_WORDS = 30
MAX_ANSWER_WORDS = 100
REQUIRED_KEYS = {
    "answer",
    "fields",
    "urgency_level",
    "urgency_rationale"
}
REQUIRED_FIELDS_SUBFIELDS = {
    "person_name",
    "reference_number",
    "amount",
    "date",
}


def validate(raw_response: str) -> dict:
    """Validate a raw model response against the
    output contract. Returns a dict with a 'valid'
    boolean and a list of 'violations'."""
    violations: list[str] = []

    # 1. Must be parseable JSON.
    stripped = raw_response.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return {
            "valid": False,
            "violations": ["Response is not valid JSON"],
        }

    # 2. Must be a dict (not a list or scalar).
    if not isinstance(parsed, dict):
        return {
            "valid": False,
            "violations": ["Response is not a JSON object"],
        }

    # 3. Must contain exactly the required keys.
    actual_keys = set(parsed.keys())
    if actual_keys != REQUIRED_KEYS:
        missing = REQUIRED_KEYS - actual_keys
        extra = actual_keys - REQUIRED_KEYS
        if missing:
            violations.append(f"Missing keys: {missing}")
        if extra:
            violations.append(f"Extra keys: {extra}")

    # Check fiels keys
    actual_subfields = set(parsed.get("fields", {}).keys())
    if actual_subfields != REQUIRED_FIELDS_SUBFIELDS:
        missing = REQUIRED_FIELDS_SUBFIELDS - actual_subfields
        extra = actual_subfields - REQUIRED_FIELDS_SUBFIELDS
        if missing:
            violations.append(f"Missing subfields in 'fields': {missing}")
        if extra:
            violations.append(f"Extra subfields in 'fields': {extra}")
    
    
    # 5. Urgency level must be one of the valid categories.
    cat = parsed.get("urgency_level")
    if not isinstance(cat, str) or cat not in {"routine", "urgent", "time_sensitive"}:
        violations.append(f"Invalid urgency_level: '{cat}'")
    

    # 6. Answer must be a string of at most
    #    100 words.
    answer = parsed.get("answer", "")
    if isinstance(answer, str):
        word_count = len(answer.split())
        if word_count == 0:
            violations.append("Answer is empty")
        elif word_count > MAX_ANSWER_WORDS:
            violations.append(
                f"Answer has {word_count} words (max {MAX_ANSWER_WORDS})"
            )
    else:
        violations.append("Answer is not a string")


    # 7. Rationale must be a string of at most
        #    30 words.
        rationale = parsed.get("rationale", "")
        if isinstance(rationale, str):
            word_count = len(rationale.split())
            if word_count == 0:
                violations.append("Rationale is empty")
            elif word_count > MAX_RATIONALE_WORDS:
                violations.append(
                    f"Rationale has {word_count} words (max {MAX_RATIONALE_WORDS})"
                )
        else:
            violations.append("Rationale is not a string")
    
    # 8. Subfields must be strings (or None for optional fields).
    for subfield in actual_subfields:
        if not isinstance(subfield, str) and subfield is not None:
            violations.append(f"Subfield '{subfield}' is not a string or None")         
            
            
            
            
    return {
        "valid": len(violations) == 0,
        "violations": violations,
    }