# Fasal Saarthi: AI-Powered Precision Crop Recommendation

**Domain:** Agritech, Decision Support Systems & Automated Machine Learning  
**Collaboration:** Edunet Foundation & IBM SkillsBuild AI Domain  
**Repository:** [https://github.com/prak05/EDUNET-AI-CLOUD-FASAL-SAARTHU-KUSHAL-KISAN](https://github.com/prak05/EDUNET-AI-CLOUD-FASAL-SAARTHU-KUSHAL-KISAN)  

---

## 📌 Executive Overview
Soil chemical composition (Nitrogen, Phosphorus, Potassium, pH) coupled with localized climate variability (annual rainfall, temperature, relative humidity) dictates crop survivability and yield. Smallholder farmers often lack the soil chemistry expertise to select the highest-yielding crop variety.

**Fasal Saarthi** is an end-to-end intelligent crop recommendation service that ingests multi-dimensional soil chemistry and weather telemetry to output ranked, high-confidence crop cultivation recommendations with detailed agronomic guidelines.

---

## ⚡ Technical Architecture & Engineering Stack
- **Model Training & Optimization:** IBM Watsonx AutoAI pipeline evaluating ensemble decision trees, LightGBM, and XGBoost with automated hyperparameter tuning.
- **Backend & API:** Python 3.10, Flask, Gunicorn, RESTful JSON API.
- **Deployment & Client Interface:** Cloud-hosted containerized service with responsive mobile-friendly web UI.

---

## 📊 Performance & Validation Metrics
- **Accuracy Benchmark:** Achieved **95.8% classification accuracy** across 22 distinct regional agricultural crop classes.
- **Inference Latency:** Sub-25ms response time for multi-parameter inputs.
- **Validation:** Developed under the IBM SkillsBuild Student Ambassador program in partnership with AICTE.
