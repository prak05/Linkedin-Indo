# RetinaScan AI: Multimodal Diabetic Retinopathy Diagnostic Pipeline

**Domain:** Medical Computer Vision, Ophthalmology, Edge Deep Learning  
**Publication:** KTU B.Tech Research Seminar (October 2026) — *"Privacy-Preserving & Explainable DR Screening: Collaborative Federated Learning & Multi-CAM on Edge Devices"*  
**Live Application:** [https://retina-scan-tau.vercel.app/](https://retina-scan-tau.vercel.app/)  
**Repository:** [https://github.com/prak05/retina-scan](https://github.com/prak05/retina-scan)  

---

## 📌 Executive Overview
Diabetic Retinopathy (DR) is a leading cause of preventable blindness worldwide. Early detection through fundus photography can prevent severe vision loss, but manual examination requires specialized ophthalmologists who are scarce in rural clinics.

**RetinaScan AI** is an explainable multimodal diagnostic pipeline that classifies fundus photographic imagery into 5 stages of Diabetic Retinopathy (No DR, Mild, Moderate, Severe, Proliferative) while generating visual Multi-CAM attention heatmaps indicating retinal microaneurysms, hemorrhages, and hard exudates.

---

## ⚡ Technical Architecture & Engineering Stack
- **Deep Learning Framework:** PyTorch, Torchvision, Albumentations image augmentation pipeline.
- **Backbone Architectures:** Gemma 4, PaliGemma Vision-Language Multimodal models, EfficientNet-B4.
- **Explainability & Verification:** Multi-CAM (Class Activation Mapping) visual heatmaps, TruLens evaluation framework.
- **Deployment:** Vercel frontend, containerized cloud inference backend.

---

## 📊 Research Rigor & Edge Computing Focus
- **Decentralized Privacy:** Designed for collaborative Federated Learning setups where patient fundus images never leave rural hospital nodes.
- **Clinical Interpretability:** Multi-CAM visual heatmaps enable ophthalmologists to verify the exact retinal regions triggering the diagnostic grading.
