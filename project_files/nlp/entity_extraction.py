import re
from difflib import SequenceMatcher
from transformers import pipeline

# Load the Medical NER pipeline
try:
    print("Loading AI Medical Entity Extraction Model (d4data/biomedical-ner-all)...")
    med_ner = pipeline("ner", model="d4data/biomedical-ner-all", aggregation_strategy="simple")
except Exception as e:
    print(f"Warning: Could not load NER model. Falling back to dictionary. Error: {e}")
    med_ner = None



MEDICINES = [
    "acetaminophen", "paracetamol", "albuterol", "salbutamol", "amlodipine", "amoxicillin", 
    "aspirin", "atorvastatin", "azithromycin", "cephalexin", "ciprofloxacin", "citalopram", 
    "clopidogrel", "diclofenac", "doxycycline", "escitalopram", "fluoxetine", "fluticasone", 
    "gabapentin", "glipizide", "glucophage", "hydrochlorothiazide", "ibuprofen", "insulin", 
    "levothyroxine", "lisinopril", "loratadine", "losartan", "metformin", "metoprolol", 
    "montelukast", "omeprazole", "ondansetron", "pantoprazole", "prednisone", "sertraline", 
    "simvastatin", "tramadol", "trazodone", "warfarin", "zolpidem", "atenolol", "cetirizine", 
    "ranitidine", "domperidone", "folic acid", "iron", "calcium", "multivitamin", "vitamins",
    "rosuvastatin", "venlafaxine", "duloxetine", "bupropion", "meloxicam", "methotrexate",
    "clonazepam", "alprazolam", "carvedilol", "clonidine", "spironolactone", "furosemide", 
    "pravastatin", "ezetimibe", "allopurinol", "topiramate", "valproate", "lamotrigine", 
    "quetiapine", "risperidone", "aripiprazole", "olanzapine", "levetiracetam", "celecoxib", 
    "naproxen", "tizanidine", "cyclobenzaprine", "baclofen", "hydroxychloroquine", 
    "sulfasalazine", "azathioprine", "tacrolimus", "mycophenolate", "cyclosporine", 
    "sirolimus", "everolimus", "dexamethasone", "hydrocortisone", "methylprednisolone",
    "fludrocortisone", "levocetirizine", "fexofenadine", "diphenhydramine", "hydroxyzine",
    "promethazine", "prochlorperazine", "metoclopramide", "granisetron", "bactrim", 
    "clindamycin", "cefuroxime", "cefdinir", "ceftriaxone", "penicillin", "ampicillin", 
    "piperacillin", "meropenem", "vancomycin", "linezolid", "daptomycin", "levofloxacin", 
    "moxifloxacin", "clarithromycin", "erythromycin", "tetracycline", "minocycline", 
    "nitrofurantoin", "fosfomycin", "metronidazole", "fluconazole", "ketoconazole", 
    "itraconazole", "voriconazole", "posaconazole", "isavuconazole", "caspofungin", 
    "micafungin", "anidulafungin", "acyclovir", "valacyclovir", "famciclovir", "oseltamivir", 
    "zanamivir", "baloxavir", "remdesivir", "paxlovid", "molnupiravir", "baricitinib", 
    "tocilizumab", "sarilumab", "anakinra", "canakinumab", "secukinumab", "ixekizumab", 
    "brodalumab", "ustekinumab"
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
    text_processed = text.lower()
    medicines, symptoms, dosage = set(), set(), set()

    # --- PHASE 1: Deep Learning NER Extraction ---
    if med_ner:
        try:
            entities = med_ner(text)
            for entity in entities:
                grp = entity.get("entity_group", "")
                word = entity.get("word", "").title()
                
                if grp in ["Medication", "Detailed_description", "Diagnostic_procedure"]:
                    if len(word) > 3:
                        medicines.add(word)
                elif grp in ["Sign_symptom", "Disease_disorder", "Biological_structure"]:
                    if len(word) > 3:
                        symptoms.add(word)
                elif grp == "Dosage":
                    dosage.add(word)
        except Exception as e:
            print(f"NER Error: {e}")

    # --- PHASE 2: Fallback / Enhancement with Local Dictionary ---
    # Medicine extraction (fuzzy)
    words = re.findall(r"[a-zA-Z]+", text_processed)
    for word in words:
        for med in MEDICINES:
            if similar(word, med) >= 0.75:
                med_title = med.capitalize()
                if med_title not in medicines:
                    medicines.add(med_title)

    # Dosage patterns
    if "after food" in text_processed:
        dosage.add("After Food")
    if "before food" in text_processed:
        dosage.add("Before Food")
    
    # Frequency patterns like 1-0-1, 1-1-1, 0-0-1, etc.
    freq_matches = re.findall(r"\b([0-2]-[0-2]-[0-2])\b", text_processed)
    for fm in freq_matches:
        dosage.add(f"Frequency: {fm}")
    
    # mg-based dosage (e.g., 500mg, 250 mg)
    mg_matches = re.findall(r"(\d+)\s*mg", text_processed)
    for mg in mg_matches:
        dosage.add(f"{mg}mg")

    # Symptom extraction
    for symptom, keys in SYMPTOMS.items():
        for k in keys:
            if k in text_processed:
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

