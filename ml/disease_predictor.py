def predict_disease(symptoms, text):
    """
    Rule-based Disease Risk Prediction with Calculated Confidence
    Aligned with AI Health Risk & Safety Analyzer abstract
    """

    text = text.lower()
    symptoms = [s.lower() for s in symptoms]

    results = []

    def add_risk(name, score, reason):
        confidence = min(score, 95)
        results.append({
            "disease": name,
            "confidence": confidence,
            "reason": reason
        })

    # -------------------------------
    # Diabetes Risk
    # -------------------------------
    diabetes_score = 0
    if "diabetes" in symptoms:
        diabetes_score += 40
    if "sugar" in text or "glucose" in text or "hba1c" in text:
        diabetes_score += 35
    if "metformin" in text or "insulin" in text:
        diabetes_score += 25

    if diabetes_score >= 40:
        add_risk("Diabetes Risk", diabetes_score, "Glucose / diabetic indicators found")

    # -------------------------------
    # Blood Pressure / Hypertension
    # -------------------------------
    bp_score = 0
    if "blood pressure" in symptoms or "hypertension" in text:
        bp_score += 40
    if "bp" in text:
        bp_score += 25
    if "amlodipine" in text or "atenolol" in text:
        bp_score += 25

    if bp_score >= 40:
        add_risk("Blood Pressure Risk", bp_score, "BP-related indicators detected")

    # -------------------------------
    # Infection / Fever
    # -------------------------------
    infection_score = 0
    if "fever" in symptoms or "temperature" in text:
        infection_score += 40
    if "infection" in text or "antibiotic" in text:
        infection_score += 30
    if "amoxicillin" in text:
        infection_score += 20

    if infection_score >= 40:
        add_risk("Possible Infection / Fever", infection_score, "Infection markers detected")

    # -------------------------------
    # Heart Disease Risk
    # -------------------------------
    heart_score = 0
    if "chest pain" in text or "angina" in text:
        heart_score += 40
    if "ecg" in text or "cardiac" in text:
        heart_score += 30
    if "heart" in text:
        heart_score += 15

    if heart_score >= 45:
        add_risk("Heart Disease Risk", heart_score, "Cardiac indicators detected")

    # -------------------------------
    # Kidney Disorder Risk
    # -------------------------------
    kidney_score = 0
    if "creatinine" in text or "urea" in text:
        kidney_score += 40
    if "kidney" in text or "dialysis" in text:
        kidney_score += 30

    if kidney_score >= 40:
        add_risk("Kidney Disorder Risk", kidney_score, "Renal function indicators detected")

    # -------------------------------
    # Liver Disorder Risk
    # -------------------------------
    liver_score = 0
    if "sgpt" in text or "sgot" in text or "alt" in text or "ast" in text:
        liver_score += 40
    if "bilirubin" in text or "liver" in text:
        liver_score += 30

    if liver_score >= 40:
        add_risk("Liver Disorder Risk", liver_score, "Abnormal liver enzyme indicators")

    # -------------------------------
    # Asthma / Respiratory
    # -------------------------------
    asthma_score = 0
    if "asthma" in text or "wheezing" in text:
        asthma_score += 40
    if "salbutamol" in text or "inhaler" in text:
        asthma_score += 30

    if asthma_score >= 40:
        add_risk("Asthma / Respiratory Risk", asthma_score, "Respiratory medication detected")

    # -------------------------------
    # Anemia
    # -------------------------------
    anemia_score = 0
    if "anemia" in text:
        anemia_score += 40
    if "hb" in text or "hemoglobin" in text:
        anemia_score += 30
    if "iron" in text or "folic acid" in text:
        anemia_score += 20

    if anemia_score >= 40:
        add_risk("Anemia Risk", anemia_score, "Low hemoglobin indicators")

    # -------------------------------
    # Gastric / Acidity
    # -------------------------------
    gastric_score = 0
    if "gastric" in text or "acidity" in text:
        gastric_score += 40
    if "pantoprazole" in text or "omeprazole" in text:
        gastric_score += 30

    if gastric_score >= 40:
        add_risk("Gastric / Acidity Risk", gastric_score, "Acid suppression medication")

    # -------------------------------
    # Pain / Inflammation
    # -------------------------------
    pain_score = 0
    if "pain" in symptoms:
        pain_score += 40
    if "ibuprofen" in text or "diclofenac" in text:
        pain_score += 30

    if pain_score >= 40:
        add_risk("Pain / Inflammatory Condition", pain_score, "Analgesic usage detected")

    # -------------------------------
    # Fallback
    # -------------------------------
    if not results:
        results.append({
            "disease": "No Major Disease Risk Detected",
            "confidence": 90,
            "reason": "No strong clinical indicators found"
        })

    return results
