def button(label: str, value: str):
    return {
        "label": label,
        "value": value,
        "type": "button",
    }


def main_menu():
    return [
        button("📅 Appointments", "appointment"),
        button("💊 Prescriptions", "prescription"),
        button("🛒 Order Medicine", "medicine_order"),
        button("📦 Track Order", "order_tracking"),
        button("🏥 Clinic Services", "clinic"),
    ]


def yes_no():
    return [
        button("Yes", "yes"),
        button("No", "no"),
    ]


def back_button():
    return [button("← Back", "back")]
