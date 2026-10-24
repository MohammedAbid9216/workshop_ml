from .intents import normalize


OUT_OF_SCOPE = [
    "python",
    "programming",
    "coding",
    "cricket",
    "football",
    "movie",
    "joke",
    "politics",
    "stock market",
    "weather",
    "homework",
    "math",
    "2+2",
]


def is_clinic_scope(text: str, active_workflow: bool = False) -> bool:
    text = normalize(text)

    # Short replies can be valid workflow responses.
    if active_workflow and (
        len(text.split()) <= 5
        or text in {
            "yes",
            "no",
            "haan",
            "nahi",
            "ok",
            "okay",
            "back",
            "cancel",
            "next",
            "yes please",
            "haan ji",
        }
    ):
        return True

    for phrase in OUT_OF_SCOPE:
        if phrase in text:
            return False

    clinic_terms = [
        "doctor",
        "appointment",
        "medicine",
        "medicine",
        "dawai",
        "prescription",
        "order",
        "delivery",
        "clinic",
        "symptom",
        "pain",
        "fever",
        "patient",
        "health",
        "hospital",
        "specialist",
        "neurologist",
        "cardiologist",
        "dermatologist",
    ]

    return any(term in text for term in clinic_terms)



def in_scope(text: str, active_workflow: bool = False) -> bool:
    """Backward-compatible alias for is_clinic_scope."""
    return is_clinic_scope(text, active_workflow)
