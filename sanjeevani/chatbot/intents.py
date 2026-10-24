import re


INTENTS = {
    "appointment": [
        "appointment",
        "doctor",
        "specialist",
        "book doctor",
        "consult doctor",
        "appointment chahiye",
        "doctor se milna",
        "doctor se appointment",
        "अपॉइंटमेंट",
        "डॉक्टर",
    ],

    "prescription": [
        "prescription",
        "prescription dikhao",
        "meri prescription",
        "prescription dekhni",
        "दवाई की पर्ची",
        "प्रिस्क्रिप्शन",
    ],

    "medicine_order": [
        "medicine order",
        "medicine mangani",
        "medicine chahiye",
        "dawai order",
        "dawai mangani",
        "medicines order",
        "medicine",
        "दवाई मंगानी",
        "दवा",
    ],

    "order_tracking": [
        "order kaha",
        "order kahan",
        "order status",
        "track order",
        "delivery kaha",
        "delivery kahan",
        "mera order",
        "order track",
        "ऑर्डर कहाँ",
        "ऑर्डर स्टेटस",
    ],

    "my_appointments": [
        "my appointment",
        "meri appointment",
        "upcoming appointment",
        "appointments dikhao",
        "appointment dikhao",
        "मेरी अपॉइंटमेंट",
    ],

    "clinic": [
        "clinic",
        "services",
        "service",
        "timing",
        "hours",
        "clinic kaha",
        "clinic kahan",
    ],

    "help": [
        "help",
        "what can you do",
        "kya kar sakte",
        "madad",
        "मदद",
    ],
}


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def detect_intent(text: str) -> str | None:
    text = normalize(text)

    priority = [
        "order_tracking",
        "medicine_order",
        "my_appointments",
        "appointment",
        "prescription",
        "clinic",
        "help",
    ]

    for intent in priority:
        for phrase in INTENTS[intent]:
            if phrase in text:
                return intent

    return None
