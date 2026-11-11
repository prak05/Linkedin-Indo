# Financial Fraud Prediction Model: Imbalanced Learning & Transaction Anomaly Detection

**Domain:** Quantitative FinTech, Imbalanced Machine Learning, Anomaly Detection  
**Repository:** [https://github.com/prak05/Financial-Fraud-Prediction-Model](https://github.com/prak05/Financial-Fraud-Prediction-Model)  

---

## 📌 Executive Overview
High-frequency transaction systems encounter severe class imbalance (often <0.1% fraudulent events), causing traditional classification algorithms to suffer from high false-negative rates and catastrophic financial risk.

**Financial Fraud Prediction Model** provides a resilient anomaly detection architecture utilizing SMOTE-NC rebalancing, cost-sensitive ensemble trees, and automated decision-boundary thresholding to detect deceptive transaction patterns in real time.

---

## ⚡ Technical Architecture & ML Stack
- **Resampling & Balancing:** SMOTE-NC (Synthetic Minority Over-sampling Technique for Nominal and Continuous features).
- **Model Ensembles:** XGBoost, LightGBM, Random Forest with cost-sensitive loss formulations.
- **Evaluation Framework:** Scikit-Learn, Precision-Recall AUC (PR-AUC), ROC-AUC, SHAP (Shapley Additive Explanations).

---

## 📊 Key Highlights & Model Validation
- **99.9% ROC-AUC Performance:** Delivers superior discriminative power across extreme class imbalance benchmarks.
- **False Negative Suppression:** Custom utility scoring prioritizing recall on high-value unauthorized transactions.
- **Interpretable Predictions:** Integrated SHAP summary plots highlighting fraud risk factors for compliance officers.
