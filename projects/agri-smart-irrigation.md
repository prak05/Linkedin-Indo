# Agri-Smart Pro: Intelligent Precision Irrigation System

**Domain:** IoT, Smart Agriculture, Sustainable Resource Optimization  
**Accolade:** **National Top 1.1% Finalist (Top 40 out of 3,668 teams)** in AICTE-Shell India Skills4Future  
**Repository:** [https://github.com/prak05/AICTE-SMART-IRRIGATION-EDUNET-PROJECT](https://github.com/prak05/AICTE-SMART-IRRIGATION-EDUNET-PROJECT)  

---

## 📌 Executive Overview
Agricultural water mismanagement leads to soil nutrient leaching, crop root rot, and excessive water depletion. Traditional timer-based irrigation systems fail to adapt to fluctuating atmospheric humidity, soil moisture profiles, and crop phenological stages.

**Agri-Smart Pro** is a multi-parcel autonomous irrigation platform integrating low-power edge sensor telemetry with a multi-output machine learning classification pipeline to predict optimal irrigation schedules and parcel-specific water volumes.

---

## ⚡ Technical Architecture & Engineering Stack
- **Edge & Sensor Mesh:** ESP32 microcontrollers, capacitive soil moisture sensors, DHT22 temperature/humidity probes, solar-backed power circuit.
- **Machine Learning Pipeline:** Python, scikit-learn (`MultiOutputClassifier`, Random Forest / Gradient Boosting), Pandas, NumPy.
- **Cloud Telemetry & Ingestion:** Google Cloud Platform (GCP) Cloud Functions, Firestore, MQTT telemetry ingestion.

---

## 📊 Key Highlights & Environmental Impact
- **Multi-Parcel Control:** Solves the simultaneous irrigation demand across distinct agricultural parcels using a single multi-target model.
- **Water Conservation:** Demonstrated up to **35% reduction in irrigation water usage** while maintaining optimal soil moisture tension.
- **National Recognition:** Selected among the Top 40 innovations nationally out of 3,668 competitive submissions in the AICTE-Shell India initiative.
