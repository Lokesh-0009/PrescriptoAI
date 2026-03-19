import re

# ===============================
# Drug Interaction Database
# severity: "minor", "moderate", "major"
# ===============================
DRUG_INTERACTIONS = {
    ("metformin", "amlodipine"): {
        "description": "No clinically significant interaction at standard doses.",
        "severity": "minor",
        "action": "No action required. Continue standard monitoring."
    },
    ("paracetamol", "aspirin"): {
        "description": "Concurrent use may increase gastric mucosal irritation.",
        "severity": "moderate",
        "action": "Administer with food. Monitor for GI discomfort or bleeding signs."
    },
    ("ibuprofen", "diclofenac"): {
        "description": "Combined NSAID therapy significantly increases GI bleeding risk.",
        "severity": "major",
        "action": "AVOID concurrent use. Choose one NSAID only."
    },
    ("warfarin", "aspirin"): {
        "description": "High bleeding risk due to additive anticoagulant and antiplatelet effects.",
        "severity": "major",
        "action": "AVOID combination unless clinically necessary. Monitor INR closely."
    },
    ("ibuprofen", "aspirin"): {
        "description": "Ibuprofen may reduce the cardioprotective effect of low-dose aspirin.",
        "severity": "moderate",
        "action": "If both required, take aspirin 30 min before ibuprofen."
    },
    ("metformin", "insulin"): {
        "description": "Combined use increases the risk of hypoglycemia.",
        "severity": "moderate",
        "action": "Monitor blood glucose closely. Adjust doses as needed."
    },
    ("warfarin", "ibuprofen"): {
        "description": "NSAIDs increase bleeding risk when combined with anticoagulants.",
        "severity": "major",
        "action": "AVOID combination. Use paracetamol for pain relief instead."
    },
    ("ciprofloxacin", "iron"): {
        "description": "Iron reduces ciprofloxacin absorption via chelation.",
        "severity": "moderate",
        "action": "Space doses at least 2 hours apart."
    },
    ("clopidogrel", "omeprazole"): {
        "description": "Omeprazole inhibits CYP2C19, reducing clopidogrel activation.",
        "severity": "moderate",
        "action": "Switch to pantoprazole if PPI is needed."
    },
    ("atenolol", "amlodipine"): {
        "description": "May cause excessive BP reduction and bradycardia.",
        "severity": "moderate",
        "action": "Monitor heart rate and blood pressure regularly."
    },
    ("losartan", "potassium"): {
        "description": "Risk of hyperkalemia with concurrent potassium supplementation.",
        "severity": "major",
        "action": "Monitor serum potassium levels. Avoid potassium supplements unless directed."
    },
    ("azithromycin", "warfarin"): {
        "description": "Azithromycin may enhance anticoagulant effect of warfarin.",
        "severity": "moderate",
        "action": "Monitor INR during and after azithromycin course."
    },
}

# ===============================
# Safe Dosage Limits (mg/day)
# ===============================
SAFE_DOSAGE_LIMITS = {
    "metformin": 2000,
    "amlodipine": 10,
    "paracetamol": 4000,
    "ibuprofen": 3200,
    "diclofenac": 150,
    "amoxicillin": 3000,
    "salbutamol": 800,
    "aspirin": 4000,
    "atorvastatin": 80,
    "azithromycin": 500,
    "ciprofloxacin": 1500,
    "doxycycline": 200,
    "losartan": 100,
    "omeprazole": 40,
    "pantoprazole": 80,
    "atenolol": 100,
    "cetirizine": 10,
    "prednisone": 60,
    "lisinopril": 40,
    "ranitidine": 300,
    "domperidone": 30,
    "clopidogrel": 75,
}

# ===============================
# Extract dosage values from text
# ===============================
def extract_dosage(text):
    if not text:
        return []
    if isinstance(text, list):
        text = " ".join(text)
    text = text.lower()
    return [int(x) for x in re.findall(r"(\d+)\s*mg", text)]

# ===============================
# Drug Interaction Analysis
# Returns list of dicts with severity
# ===============================
def analyze_drug_interactions(medicines):
    interactions = []
    meds = [m.lower() for m in medicines if m != "Not Detected"]

    for i in range(len(meds)):
        for j in range(i + 1, len(meds)):
            pair = (meds[i], meds[j])
            reverse_pair = (meds[j], meds[i])

            data = None
            if pair in DRUG_INTERACTIONS:
                data = DRUG_INTERACTIONS[pair]
            elif reverse_pair in DRUG_INTERACTIONS:
                data = DRUG_INTERACTIONS[reverse_pair]

            if data:
                interactions.append({
                    "drug_a": meds[i].title(),
                    "drug_b": meds[j].title(),
                    "severity": data["severity"],
                    "description": data["description"],
                    "action": data["action"],
                })

    if not interactions:
        interactions.append({
            "drug_a": "",
            "drug_b": "",
            "severity": "none",
            "description": "No harmful drug interactions detected in the prescribed list.",
            "action": "Continue standard monitoring.",
        })

    return interactions

# ===============================
# Dosage Safety Analysis
# Returns list of dicts with status
# ===============================
def analyze_dosage_safety(medicines, dosage_text):
    warnings = []
    extracted_doses = extract_dosage(dosage_text)

    for med in medicines:
        if med == "Not Detected":
            continue
        med_lower = med.lower()

        if med_lower in SAFE_DOSAGE_LIMITS:
            safe_limit = SAFE_DOSAGE_LIMITS[med_lower]

            if extracted_doses:
                prescribed = extracted_doses[0]
                ratio = prescribed / safe_limit

                if prescribed > safe_limit:
                    warnings.append({
                        "medicine": med,
                        "status": "danger",
                        "prescribed": f"{prescribed}mg",
                        "limit": f"{safe_limit}mg/day",
                        "message": f"Prescribed dose EXCEEDS safe daily limit.",
                        "action": f"Reduce to max {safe_limit}mg/day or verify with physician.",
                        "ratio": min(ratio, 1.5),
                    })
                elif ratio > 0.75:
                    warnings.append({
                        "medicine": med,
                        "status": "warning",
                        "prescribed": f"{prescribed}mg",
                        "limit": f"{safe_limit}mg/day",
                        "message": f"Prescribed dose is near upper safe limit.",
                        "action": "Monitor patient closely for adverse effects.",
                        "ratio": ratio,
                    })
                else:
                    warnings.append({
                        "medicine": med,
                        "status": "safe",
                        "prescribed": f"{prescribed}mg",
                        "limit": f"{safe_limit}mg/day",
                        "message": f"Dose is within accepted therapeutic range.",
                        "action": "No action required.",
                        "ratio": ratio,
                    })
            else:
                warnings.append({
                    "medicine": med,
                    "status": "info",
                    "prescribed": "Unknown",
                    "limit": f"{safe_limit}mg/day",
                    "message": "Dosage quantity not detected in prescription text.",
                    "action": "Manual verification recommended.",
                    "ratio": 0,
                })

    if not warnings:
        warnings.append({
            "medicine": "N/A",
            "status": "info",
            "prescribed": "N/A",
            "limit": "N/A",
            "message": "Dosage information insufficient for safety analysis.",
            "action": "Provide clearer prescription for analysis.",
            "ratio": 0,
        })

    return warnings
