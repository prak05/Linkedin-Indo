# VisagePass: Real-Time Facial Vector Recognition & Attendance Mesh

**Domain:** Computer Vision, Biometric Security, High-Throughput Edge Systems  
**Repository:** [https://github.com/prak05/VisagePass-Biometric-Attendance](https://github.com/prak05/VisagePass-Biometric-Attendance)  

---

## 📌 Executive Overview
Legacy RFID and card-based attendance logging suffer from proxy punching, physical wear, and friction in high-throughput enterprise or educational environments.

**VisagePass** is an automated biometric attendance infrastructure utilizing real-time facial feature vector extraction, cosine similarity indexing, and PostgreSQL PGVector database persistence for instantaneous identity verification.

---

## ⚡ Technical Architecture & Vision Pipeline
- **Facial Detection & Embeddings:** OpenCV Haar cascades / MTCNN face alignment paired with deep ResNet embedding backbones (128-d/512-d feature vectors).
- **Vector Database & Storage:** PostgreSQL with PGVector extension for sub-millisecond nearest neighbor search.
- **Application Core:** Python 3.11+, SQLAlchemy, FastAPI backend with real-time RTSP camera stream ingestion.

---

## 📊 Key Highlights & Security
- **Sub-200ms Verification:** Real-time video frame processing with high-accuracy identity resolution.
- **Spoofing Resistance:** Motion and blink liveness verification heuristics preventing photo replay attacks.
- **Automated Audit Logging:** Immutable attendance records and departure timestamps formatted for HRMS integration.
