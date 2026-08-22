# MedBridge EMR Interoperability Platform

## Description
**MedBridge** is an enterprise-grade, intelligent terminology bridge designed to make traditional medicine (Ayurveda, Siddha, and Unani) digitally interoperable with modern healthcare systems and national digital health standards (ABDM).

- **What was your motivation?** Millions of patients rely on traditional medicine in India, yet their clinical records hit a roadblock when transitioning to modern hospitals, digital EHRs, or applying for health insurance due to a lack of standardized coding.
- **Why did you build this project?** We built MedBridge for Smart India Hackathon to bridge the data divide between ancient medical systems and modern digital health infrastructure, ensuring seamless clinical continuity.
- **What problem does it solve?** Traditional medical diagnoses do not automatically map to modern standardized codes (WHO ICD-11 / TM2 and NAMASTE codes). This causes manual transcription errors, care delays, and insurance claim rejections. MedBridge provides real-time semantic translation into **FHIR-compliant payloads** and automated bulk data migration.
- **What did you learn?** We learned how to design a hybrid search engine combining TF-IDF vectorization with fuzzy string matching, build secure zero-latency asynchronous APIs with FastAPI and Supabase Auth, and format audit-ready clinical reports dynamically using Pandas.

---

## Architecture & Tech Stack
- **Backend:** FastAPI, Python, Pydantic, Pandas, Openpyxl, Scikit-learn (TF-IDF Cosine Similarity)
- **Database:** SQLite (`mappings.db`) for rapid terminology lookup; Supabase for secure Auth & Role Management
- **Frontend:** HTML5, Bootstrap 5, Custom Glassmorphic CSS, Vanilla JavaScript (Web Speech API, Command Palette)
- **Compliance & Standards:** WHO ICD-11 Traditional Medicine Module 2 (TM2), AYUSH NAMASTE Portal Codes, HL7 FHIR R4 Condition Resource standard, ABDM Audit Trail logging.

---

## Project Structure
```text
MedBridge/
│
├── main.py              # FastAPI application & enterprise endpoints
├── search_engine.py     # TF-IDF & fuzzy matching medical translation engine
├── setup_db.py          # Relational database initialization script
├── requirements.txt     # Python project dependencies
├── mappings.db          # Local SQLite mapping database (auto-generated)
├── audit_log.txt        # ABDM real-time compliance transaction logs
├── data/
|   |__ bulk_upload.csv  #
│   └── data.csv         # Master repository of traditional-to-modern medical codes
└── src/ (or root files)
    ├── index.html       # Clinician Portal (Search & FHIR generator)
    ├── admin.html       # Hospital Administrator Portal (Bulk migration & Audit viewer)
    ├── login.html       # Secure Supabase Authentication portal with role toggles
    ├── script.js        # Frontend interaction, voice search, & API connectors
    ├── style.css        # Cyber-medical dark theme & glassmorphic UI styles
    ├── sw.js            # PWA Service Worker for offline resilience
    └── manifest.json    # PWA web app manifest

```

---

## Installation & Local Setup

To run the development environment locally, follow these steps:

1. **Clone the repository:**
```bash
git clone https://github.com/sruthika-19/MedBridge
cd MedBridge

```


2. **Install backend dependencies:**
Ensure you have Python 3.10+ installed, then run:
```bash
python -m pip install -r requirements.txt

```


3. **Initialize and Seed the Database:**
Generate the SQLite database (`mappings.db`) from the master dataset:
```bash
python setup_db.py

```



---

## Usage

1. **Start the FastAPI Backend Server:**
```bash
python -m uvicorn main:app --reload

```


The API will be live at `http://127.0.0.1:8000`.
2. **Launch the Application:**
Open `login.html` in your web browser (or serve it locally) to authenticate via Supabase as a **Clinician** or **Administrator**.

---

## Features

* **Cyber-Medical Terminal UI:** Dark-mode glassmorphic interface featuring custom neon cyan/blue styling and responsive layout.
* **Voice & Text Search:** Integrated Web Speech API (`en-IN`) enabling clinicians to speak diagnoses directly into the search bar.
* **Hybrid Semantic Matching:** Combines Python's `difflib` with `scikit-learn` TF-IDF vectorization to accurately map misspelled or regional terms with calculated confidence scores.
* **Dual Coding Standard Output:** Translates Siddha, Ayurveda, and Unani terms into both **NAMASTE codes** and **WHO ICD-11 / TM2 disease codes**.
* **FHIR Payload Generation:** Serializes search results into structured HL7 FHIR Condition resources with a one-click copy tool.
* **Enterprise Bulk Migration:** Allows hospital admins to drag-and-drop legacy CSV records to instantly generate standardized, auto-fitted Excel (`.xlsx`) compliance reports.
* **ABDM Audit Trail:** Real-time logging of all query transactions to an immutable log file viewable directly within the admin dashboard.
* **Offline-First PWA:** Configured with a Service Worker to ensure robust access in bandwidth-constrained clinics.

---

## Credits

**The HexaDice Team:**

* **Sruthika** - Team Leader, Backend Architecture & UI/UX Design (`@sruthika-19`)
* **Yukthasree** - Frontend Integration & Component Logic
* **Pradeeptha** - Database Architecture & Data Sanitization
* **Raga Varshitha** - Search Logic & Fuzzy Matching Integration
* **Swetha** - Research & Documentation
* **Dharshini** - Product Strategy & Pitch Development

**Data & References:**
Medical standardization mappings based on WHO ICD-11 / TM2 classifications, NAMASTE portal codes, and Ministry of Ayush guidelines.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

```

```