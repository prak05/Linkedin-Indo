# OmniPrice ML Engine: Serverless Price Elasticity & Dynamic Valuation

**Domain:** Cloud-Native Machine Learning, Quantitative FinTech, Serverless Systems  
**Repository:** [https://github.com/prak05/OmniPrice-ML-Engine](https://github.com/prak05/OmniPrice-ML-Engine)  

---

## 📌 Executive Overview
E-commerce and enterprise supply chains face volatile demand curves driven by competitor pricing, seasonal trends, and inventory holding costs. Static pricing rules fail to capture non-linear demand shifts.

**OmniPrice ML Engine** is a serverless, high-throughput machine learning pipeline built on Amazon Web Services that computes dynamic price elasticity coefficients and predicts optimal price points to maximize gross margin.

---

## ⚡ Technical Architecture & Engineering Stack
- **Cloud Infrastructure:** AWS S3 (feature store / dataset lake), AWS Lambda, Amazon API Gateway.
- **Model Training & Deployment:** Amazon SageMaker Serverless Inference endpoints running optimized XGBoost and LightGBM models.
- **Data Engineering:** Python, Pandas, Polars for low-latency batch feature transformation.

---

## 📊 Key Highlights & Cloud Scalability
- **Sub-40ms P99 Latency:** High-throughput serverless endpoint capable of handling real-time checkout pricing requests.
- **Zero Idle Costs:** Deployed on SageMaker Serverless Inference to scale down to zero during off-peak hours.
- **Cold Start Optimization:** Custom lightweight inference runtime minimizing container spin-up overhead.
