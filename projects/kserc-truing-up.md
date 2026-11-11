# KSERC Autonomous Regulatory Agent (ARA) & AI Truing-Up Engine

**Domain:** GovTech, Regulatory Tariff Computing & Legal AI  
**Role:** System Architect & Lead Engineer  
**Institution:** Kerala State Electricity Regulatory Commission (KSERC)  
**Repository:** [https://github.com/prak05/kserc-truing-up](https://github.com/prak05/kserc-truing-up)  
**Live Production URL:** [https://kserc-trueup-engine-464030854609.asia-south1.run.app](https://kserc-trueup-engine-464030854609.asia-south1.run.app)  

---

## 📌 Executive Overview
The Kerala State Electricity Regulatory Commission (KSERC) governs electricity tariffs, power utility regulations, and licensing across the state of Kerala. Annually, licensees (such as the Kerala State Electricity Board Ltd. — KSEBL) submit voluminous 500+ page audited petition filings ("Truing-Up Petitions") detailing operating expenses, capital additions, depreciation, interest and finance charges, return on equity (RoE), and power purchase agreements.

The **KSERC AI Truing-Up Engine** is a specialized GovTech automation system engineered to ingest, reconcile, and audit statutory utility financial filings against prior regulatory commission orders and regulatory norms.

---

## ⚡ Technical Architecture & Engineering Stack
- **Backend & Core Engine:** Python 3.11+, FastAPI, PyMuPDF, pdfplumber, NumPy, Pandas.
- **LLM Reasoning & Extraction:** Anthropic Claude 3.5 Sonnet / Google Vertex AI Gemini 1.5 Pro via structured JSON output schemas.
- **Frontend & Document Inspection:** Vanilla JavaScript, PDF.js dual-pane synchronized document reader, Tailwind CSS.
- **Infrastructure & Deployment:** Google Cloud Run (containerized serverless), Docker, Secret Manager, Cloud Build.

---

## 📊 Key Features & Performance Metrics
- **Automated Mathematical Reconciliation:** Extracts and cross-checks tabular claims (RoE, Interest on Loans, Depreciation, O&M Expenses) against normative regulatory ceiling formulas.
- **Precedent Citations & Disallowance Tracking:** Cross-references petition line items against prior tariff orders, flagging unapproved capital expenditures.
- **Zero-Hallucination Guardrails:** Employs strict citation bounding where every calculation links back to an exact PDF page and table cell coordinate.
- **Throughput:** Reduces the preliminary technical petition review cycle from **3 weeks of manual auditing to under 15 minutes** of automated mathematical verification.
