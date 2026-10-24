from .buttons import main_menu, button, back_button


def welcome():
    return {
        "message": (
            "Hi 👋 I'm Sanjeevani AI. "
            "I can help with appointments, prescriptions, "
            "medicine orders and delivery tracking."
        ),
        "buttons": main_menu(),
    }


def out_of_scope():
    return {
        "message": (
            "Main sirf Sanjeevani Clinic se related help ke liye "
            "available hoon. Aap appointments, doctors, prescriptions, "
            "medicines ya orders ke baare mein pooch sakte hain."
        ),
        "buttons": main_menu(),
    }


def help_response():
    return {
        "message": "Aap kya karna chahte hain?",
        "buttons": main_menu(),
    }


def appointment_start():
    return {
        "message": "Bilkul. Aap kis specialist se appointment lena chahte hain?",
        "buttons": [
            button("Neurologist", "specialty:Neurologist"),
            button("Cardiologist", "specialty:Cardiologist"),
            button("Dermatologist", "specialty:Dermatologist"),
            *back_button(),
        ],
    }


def prescription_start():
    return {
        "message": "Main aapki prescriptions check karta hoon.",
        "buttons": [
            button("Latest Prescription", "prescription:latest"),
            button("All Prescriptions", "prescription:all"),
            *back_button(),
        ],
    }


def medicine_start():
    return {
        "message": (
            "Medicine order karne ke liye pehle prescription "
            "select karni hogi."
        ),
        "buttons": [
            button("Latest Prescription", "medicine:latest"),
            button("View Prescriptions", "medicine:prescriptions"),
            *back_button(),
        ],
    }


def tracking_start():
    return {
        "message": "Aapke orders check kar raha hoon.",
        "buttons": [
            button("My Orders", "orders:mine"),
            *back_button(),
        ],
    }


def clinic_services():
    return {
        "message": (
            "Sanjeevani Clinic mein aap doctors, appointments, "
            "prescriptions, medicines aur delivery services use kar sakte hain."
        ),
        "buttons": main_menu(),
    }
