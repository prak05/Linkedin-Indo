# MediScribe 2.0: Ambient Clinical Intelligence & Physician EHR Documentation

**Domain:** Healthcare, Clinical AI & Electronic Health Records (EHR)  
**Accolade:** Selected for **UST SIGHT 3.0 National Showcase** (UST Global & Kerala Startup Mission)  
**Repository:** [https://github.com/prak05/MediScribe-2.0](https://github.com/prak05/MediScribe-2.0)  

---

## 📌 Executive Overview
Physician burnout is predominantly driven by excessive Electronic Health Record (EHR) data entry, with doctors spending up to 2 hours documenting clinical notes for every 1 hour of patient interaction. 

**MediScribe 2.0** is an ambient clinical intelligence platform that listens to natural doctor-patient audio consultations in real-time, differentiates multi-speaker dialogue, and synthesizes structured, audit-ready clinical documentation (SOAP notes, ICD-10 coding, prescription summaries, and clinical follow-ups) with zero hallucination.

---

## ⚡ Technical Architecture & Engineering Stack
- **Frontend:** TypeScript, React 18, Vite, Tailwind CSS, Lucide Icons.
- **Audio Processing & Streaming:** Web Audio API, MediaRecorder, Opus chunk streaming, WebSockets.
- **AI Synthesis Pipeline:** Multi-modal pipeline utilizing Google Gemini 1.5 Pro and Anthropic Claude 3.5 Sonnet with medical prompt grounding.
- **Standards Compliance:** FHIR (Fast Healthcare Interoperability Resources) JSON format, ICD-10-CM diagnostic code cross-referencing.

---

## 📊 Key Highlights & Clinical Rigor
- **SOAP Note Synthesis:** Automatically categorizes multi-turn conversations into Subjective (patient complaints, history of present illness), Objective (vital signs, physical exam observations), Assessment (differential diagnosis), and Plan (pharmacotherapy, investigations).
- **Hallucination Mitigation:** Employs negative prompt constraints preventing the generation of unmentioned symptoms or unverified drug dosages.
- **Doctor-in-the-Loop Verification:** Provides an interactive dual-pane UI where clinicians can review, edit, and digitally sign notes before EHR commitment.
