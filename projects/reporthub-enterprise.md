# ReportHub: Enterprise Reporting & Dynamic PDF Synthesis Platform

**Domain:** Business Intelligence, Document Engineering, Cloud Automation  
**Repository:** [https://github.com/prak05/ReportHub](https://github.com/prak05/ReportHub)  

---

## 📌 Executive Overview
Enterprise financial auditing and resource planning require deterministic, dynamic generation of branded PDF reports, invoice batches, and budget reconciliation sheets from heterogeneous data streams without degrading OLTP database throughput.

**ReportHub** is an asynchronous reporting microservice pipeline engineered with Python, WeasyPrint, and AWS Lambda, enabling sub-second multi-tenant document generation and automated stakeholder dispatch.

---

## ⚡ Technical Architecture & Engineering Stack
- **Document Engine:** WeasyPrint (HTML/CSS to PDF rendering engine), OpenPyXL, Pandas for tabular data transformation.
- **Cloud Architecture:** AWS Lambda, Amazon S3 for artifact persistence, Decoupled Worker queues.
- **API & Protocol:** FastAPI / FastMCP integration for automated agentic report generation.

---

## 📊 Key Highlights & Scalability
- **Sub-Second Generation:** Generates multi-page formatted financial audits in under 1 second per document.
- **Dual-Branch Safe:** Hardened git release workflow preserving validated schemas.
- **Multi-Tenant Isolation:** Dynamic styling and schema adaptation per organizational tenant.
