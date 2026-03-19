import re
from difflib import SequenceMatcher

MEDICINES = [
    "paracetamol", "glucophage", "metformin",
    "amoxicillin", "ibuprofen", "amlodipine",
    "aspirin", "atorvastatin", "diclofenac",
    "warfarin", "omeprazole", "pantoprazole",
    "atenolol", "salbutamol", "insulin",
    "cetirizine", "azithromycin", "ciprofloxacin",
    "doxycycline", "prednisone", "losartan",
    "lisinopril", "clopidogrel", "ranitidine",
    "domperidone", "ondansetron", "folic acid",
    "iron", "calcium", "multivitamin",
]

SYMPTOMS = {
    "Diabetes": ["sugar", "diabetes", "glucose", "hba1c"],
    "Blood pressure": ["bp", "pressure", "hypertension"],
    "Fever": ["fever", "temperature"],
    "Pain": ["pain", "ache", "headache"],
    "Infection": ["infection", "antibiotic"],
    "Asthma": ["asthma", "wheezing", "breathlessness"],
    "Gastric": ["gastric", "acidity", "acid reflux"],
    "Anemia": ["anemia", "hemoglobin", "hb low"],
}

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def extract_entities(text):
    text = text.lower()
    medicines, symptoms, dosage = set(), set(), set()

    # Medicine extraction (fuzzy)
    words = re.findall(r"[a-zA-Z]+", text)
    for word in words:
        for med in MEDICINES:
            if similar(word, med) >= 0.75:
                medicines.add(med.capitalize())

    # Dosage patterns
    if "after food" in text:
        dosage.add("After Food")
    if "before food" in text:
        dosage.add("Before Food")
    
    # Frequency patterns like 1-0-1, 1-1-1, 0-0-1, etc.
    freq_matches = re.findall(r"\b([0-2]-[0-2]-[0-2])\b", text)
    for fm in freq_matches:
        dosage.add(f"Frequency: {fm}")
    
    # mg-based dosage (e.g., 500mg, 250 mg)
    mg_matches = re.findall(r"(\d+)\s*mg", text)
    for mg in mg_matches:
        dosage.add(f"{mg}mg")

    # Symptom extraction
    for symptom, keys in SYMPTOMS.items():
        for k in keys:
            if k in text:
                symptoms.add(symptom)
                break

    if not medicines:
        medicines.add("Not Detected")
    if not dosage:
        dosage.add("Not Detected")
    if not symptoms:
        symptoms.add("Not Detected")

    return {
        "medicines": list(medicines),
        "dosage": list(dosage),
        "symptoms": list(symptoms)
    }
