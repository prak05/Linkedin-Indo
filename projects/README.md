# 🚀 Engineering Projects & Systems Portfolio

A curated, evidence-verified catalog of engineering systems, GovTech solutions, clinical AI platforms, and cloud infrastructure engineered by **[Prakhar Sharma](https://github.com/prak05)**. Every project below is integrated into LinkedIn Indo's **Perplexity Vector Knowledge Base** (`knowledge.db`) for zero-hallucination RAG drafting and technical citations.

---

## 🏛️ Flagship Systems Matrix

| Project | Domain | Architecture / Tech Stack | Impact & Accolades | Documentation |
|---|---|---|---|---|
| **[KSERC AI Truing-Up Engine](kserc-truing-up.md)** | GovTech & Regulatory AI | Python, Claude 3.5 Sonnet, Vertex AI, Google Cloud Run, PDF.js | Statutory utility tariff engine automating 500+ page audited petition reviews for Kerala power utilities. | [`kserc-truing-up.md`](kserc-truing-up.md) |
| **[MediScribe 2.0](mediscribe-clinical-ai.md)** | Healthcare & Clinical AI | TypeScript, React, Vite, Node.js, Express, Gemini, Claude 3.5 | Ambient clinician EHR scribe converting consultation audio into zero-hallucination SOAP notes. **UST SIGHT 3.0 Showcase**. | [`mediscribe-clinical-ai.md`](mediscribe-clinical-ai.md) |
| **[MedBuddy Clinical RAG](medbuddy-clinical-rag.md)** | Medical Retrieval | Python, Streamlit, LlamaIndex, BM25 + Vector Cosine Engine | Dense + sparse clinical literature QA engine. **1st Place Winner at Gravity IEDC-MCET Cluster Ideathon**. | [`medbuddy-clinical-rag.md`](medbuddy-clinical-rag.md) |
| **[Agri-Smart Pro](agri-smart-irrigation.md)** | IoT & Precision Agritech | Python, scikit-learn (`MultiOutputClassifier`), IoT Sensors, GCP | Multi-parcel precision irrigation system. **National Top 1.1% Finalist (Top 40 / 3,668)** in AICTE-Shell India Skills4Future. | [`agri-smart-irrigation.md`](agri-smart-irrigation.md) |
| **[Fasal Saarthi: Kushal Kisan](fasal-saarthi-ai.md)** | Agritech & AutoAI | IBM Watsonx AutoAI, Flask, Python, REST APIs | 7-parameter soil/weather crop recommendation engine with 95%+ classification accuracy. | [`fasal-saarthi-ai.md`](fasal-saarthi-ai.md) |
| **[RetinaScan Diagnostic AI](retinascan-ai.md)** | Medical Vision & Federated ML | Gemma 4, PaliGemma Multimodal, PyTorch, TruLens, Vercel | Multimodal Diabetic Retinopathy screening with Multi-CAM explainability maps. Published in KTU B.Tech Research Seminar. | [`retinascan-ai.md`](retinascan-ai.md) |
| **[OmniPrice ML Engine](omniprice-ml-engine.md)** | FinTech & Cloud ML | AWS S3, SageMaker Serverless, Python, XGBoost | Sub-40ms P99 price elasticity and revenue forecasting engine. | [`omniprice-ml-engine.md`](omniprice-ml-engine.md) |
| **[Yugality LegalTech Mesh](yugality-legaltech.md)** | LegalTech & Compliance | Python, FastAPI, Document AI, Next.js, PostgreSQL | Contract intelligence & legal regulatory automation. Backed by **IIT Patna IC** & **Startup Bihar**. | [`yugality-legaltech.md`](yugality-legaltech.md) |
| **[WhatsApp-MCP](whatsapp-mcp.md)** | Agent Tooling & Protocols | TypeScript, Model Context Protocol (MCP), Baileys | Production MCP server enabling AI coding agents to dispatch real-time alerts and monitor communication threads. | [`whatsapp-mcp.md`](whatsapp-mcp.md) |
| **[SGSSS Smart Grid](sgsss-smart-grid.md)** | CleanTech & Embedded IoT | Embedded C, ESP32, Python, Time-Series Telemetry | Autonomous solar microgrid monitoring and real-time load distribution node. | [`sgsss-smart-grid.md`](sgsss-smart-grid.md) |
| **[PrakVerse Identity Mesh](prakverse-identity-mesh.md)** | Identity & Local Knowledge | Python, SQLite FTS5, Hybrid Vector Cosine, Perplexity UI | Local-first single-source-of-truth professional knowledge engine and career asset compiler. | [`prakverse-identity-mesh.md`](prakverse-identity-mesh.md) |

---

## ✦ Integration with LinkedIn Indo RAG

Every document in this directory is ingested into the local SQLite FTS5 vector engine (`~/.local/share/linkedin-indo/vectordb/knowledge.db`) under the category `projects`:

1. **Instant Retrieval**: Live sub-10ms queries in the header **Knowledge ✦** terminal.
2. **Fact Grounding**: Verified technical metrics, real links, and exact team roles are injected into post drafts to guarantee zero invented facts.
3. **One-Click Snippet Insert**: Quote directly from project specs into LinkedIn drafting topics.
