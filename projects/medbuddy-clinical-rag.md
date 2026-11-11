# MedBuddy: Evidence-Based Clinical Literature RAG Engine

**Domain:** Medical Retrieval-Augmented Generation (RAG) & Evidence-Based Healthcare  
**Accolade:** **1st Place Winner** at Gravity IEDC-MCET Cluster Ideathon  
**Repository:** [https://github.com/prak05/MedBuddy](https://github.com/prak05/MedBuddy)  

---

## 📌 Executive Overview
Clinical guidelines and medical literature evolve continuously, making it challenging for practitioners and students to quickly retrieve authoritative medical protocols during diagnosis. General LLMs frequently hallucinate drug interactions, contraindications, and treatment steps.

**MedBuddy** is an evidence-grounded clinical question-answering system combining BM25 lexical search with dense vector embeddings to retrieve, cross-verify, and cite accredited peer-reviewed medical publications and clinical textbooks.

---

## ⚡ Technical Architecture & Engineering Stack
- **Framework & Orchestration:** Python, LlamaIndex, LangChain, Streamlit.
- **Hybrid Retrieval Engine:** Reciprocal Rank Fusion (RRF) combining BM25 keyword retrieval and dense sentence-transformer embeddings.
- **Data Ingestion:** Chunked medical compendiums, pharmacology manuals, and treatment protocols with source metadata tracking.

---

## 📊 Key Highlights & Verification
- **Dual-Pane Citations:** Displays answers alongside the exact paragraph, page, and journal DOI from which the recommendation was derived.
- **Conflict Resolution:** Highlights conflicting clinical trial outcomes across different treatment modalities rather than hallucinating a consensus.
- **Demonstrated Efficacy:** Awarded First Prize at the Gravity IEDC-MCET Cluster Ideathon for practical applicability in primary healthcare centers.
