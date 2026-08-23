# MedBridge

### EMR Interoperability Platform for Traditional Medicine

**MedBridge** is a healthcare interoperability platform that translates traditional medicine terminology from **Ayurveda, Siddha, and Unani** into standardized digital healthcare representations using **WHO ICD-11/TM2, NAMASTE terminology, and HL7 FHIR R4**.

The platform is designed to reduce terminology mismatches between traditional medicine systems and modern Electronic Medical Records (EMRs), enabling more consistent clinical data exchange and structured healthcare interoperability.

---

## Overview

Traditional medicine records often use terminology that is not directly compatible with standardized digital healthcare systems. This creates challenges when patient information needs to be transferred between traditional medicine providers, modern hospitals, EMRs, and other healthcare applications.

**MedBridge addresses this interoperability gap by providing:**

* Intelligent terminology matching
* WHO ICD-11/TM2 and NAMASTE code mapping
* Confidence-based search results
* FHIR R4 `Condition` resource generation
* Bulk legacy-record migration
* Role-based authentication
* Audit logging
* Offline-capable Progressive Web App (PWA) support

---

## Key Features

### 1. Intelligent Terminology Search

MedBridge uses a hybrid matching approach combining:

* **TF-IDF vectorization**
* **Cosine similarity**
* **Fuzzy string matching**

This helps identify relevant standardized terms even when the input contains spelling variations, regional terminology, or minor differences.

Each result is accompanied by a **confidence score** to help users assess the quality of the suggested mapping.

---

### 2. Traditional Medicine Code Mapping

The platform supports terminology from:

* Ayurveda
* Siddha
* Unani

and maps these terms to standardized representations including:

* **NAMASTE terminology**
* **WHO ICD-11 Traditional Medicine Module 2 (TM2)**

---

### 3. FHIR R4 Resource Generation

Mapped clinical information can be transformed into structured **HL7 FHIR R4 `Condition` resources**.

Example workflow:

```text
Traditional Medicine Term
          ↓
   Search & Matching
          ↓
   Confidence Scoring
          ↓
 NAMASTE / ICD-11 TM2
          ↓
    FHIR R4 Condition
          ↓
      EMR System
```

This provides a structured format suitable for integration with modern healthcare applications.

---

### 4. Bulk Data Migration

Hospital administrators can process legacy medical records through CSV uploads.

The migration workflow supports:

* CSV file upload
* Bulk terminology matching
* Standardized code generation
* Data transformation
* Excel report generation
* Automated spreadsheet formatting

This reduces the manual effort required to standardize large collections of legacy records.

---

### 5. Role-Based Access

MedBridge provides separate application workflows for:

**Clinicians**

* Search medical terminology
* Review mapping results
* View confidence scores
* Generate FHIR resources

**Administrators**

* Perform bulk migration
* Review audit logs
* Monitor system activity
* Manage administrative workflows

Authentication and role management are implemented using **Supabase Auth**.

---

### 6. Audit Logging

MedBridge maintains transaction-level audit records for terminology searches and system operations.

The audit mechanism provides visibility into:

* Search activity
* Mapping requests
* Transaction history
* Administrative operations

---

### 7. Voice Search

The clinician interface supports voice-based terminology input using the **Web Speech API**.

The application is configured for Indian English (`en-IN`) speech recognition, allowing clinicians to enter terminology through voice as well as text.

---

### 8. Offline-Capable PWA

MedBridge follows a Progressive Web App architecture using:

* Service Worker
* Web App Manifest
* Browser-based caching

This improves usability in environments where network connectivity may be limited or intermittent.

---

# Architecture

```text
                         ┌──────────────────────┐
                         │   Clinician / Admin  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Web Application    │
                         │ HTML + Bootstrap + JS│
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      FastAPI API     │
                         │   Python Backend     │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    ▼               ▼                ▼
             ┌────────────┐ ┌─────────────┐ ┌──────────────┐
             │  Search    │ │ Terminology │ │ Authentication│
             │   Engine   │ │   Database  │ │ & Roles      │
             └─────┬──────┘ └──────┬──────┘ └──────────────┘
                   │               │
                   └───────┬───────┘
                           ▼
                  ┌──────────────────┐
                  │ Mapping & Scoring │
                  └────────┬─────────┘
                           │
                           ▼
             ┌────────────────────────────┐
             │ NAMASTE + ICD-11 / TM2     │
             └──────────────┬─────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │   FHIR R4 JSON   │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Modern EMR / HIS │
                  └──────────────────┘
```

---

# Technology Stack

| Category                  | Technologies                                            |
| ------------------------- | ------------------------------------------------------- |
| **Backend**               | Python, FastAPI, Pydantic                               |
| **Search & Matching**     | Scikit-learn, TF-IDF, Cosine Similarity, Fuzzy Matching |
| **Data Processing**       | Pandas, Openpyxl                                        |
| **Database**              | SQLite                                                  |
| **Authentication**        | Supabase Auth                                           |
| **Frontend**              | HTML5, Bootstrap 5, Vanilla JavaScript                  |
| **Voice Input**           | Web Speech API                                          |
| **Healthcare Standard**   | HL7 FHIR R4                                             |
| **Terminology Standards** | WHO ICD-11/TM2, NAMASTE                                 |
| **PWA**                   | Service Worker, Web App Manifest                        |
| **Development**           | Git, GitHub                                             |

---

# Project Structure

```text
MedBridge/
│
├── main.py                  # FastAPI application and API endpoints
├── search_engine.py         # TF-IDF and fuzzy matching engine
├── setup_db.py              # Database initialization and seeding
├── requirements.txt         # Python dependencies
├── mappings.db              # SQLite terminology database
├── audit_log.txt            # Application audit log
│
├── data/
│   ├── data.csv             # Master terminology dataset
│   └── bulk_upload.csv      # Bulk migration test data
│
└── src/
    ├── index.html           # Clinician interface
    ├── admin.html           # Administrator interface
    ├── login.html           # Authentication interface
    ├── script.js            # Frontend logic and API integration
    ├── style.css            # Application styling
    ├── sw.js                # PWA service worker
    └── manifest.json        # PWA configuration
```

---

# Installation

## Prerequisites

* Python 3.10+
* Git
* Modern web browser

## 1. Clone the Repository

```bash
git clone https://github.com/sruthika-19/MedBridge.git
cd MedBridge
```

## 2. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

## 3. Initialize the Database

```bash
python setup_db.py
```

This creates and populates the local SQLite terminology database.

## 4. Start the Backend

```bash
python -m uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

## 5. Launch the Frontend

Open `login.html` in a modern web browser or serve the `src/` directory through a local development server.

---

# Application Workflow

### Clinician Workflow

```text
Login
  ↓
Enter Traditional Medicine Term
  ↓
Text / Voice Search
  ↓
Hybrid Terminology Matching
  ↓
Review Confidence Score
  ↓
View NAMASTE + ICD-11/TM2 Mapping
  ↓
Generate FHIR R4 Resource
  ↓
Copy / Integrate with EMR
```

### Administrator Workflow

```text
Login
  ↓
Upload Legacy CSV
  ↓
Bulk Terminology Processing
  ↓
Standardized Code Mapping
  ↓
Generate Excel Report
  ↓
Review Audit Records
```

---

# Example FHIR Output

A mapped diagnosis can be represented as a FHIR R4 `Condition` resource:

```json
{
  "resourceType": "Condition",
  "code": {
    "coding": [
      {
        "system": "http://hl7.org/fhir/sid/icd-11",
        "code": "EXAMPLE",
        "display": "Standardized Diagnosis"
      }
    ],
    "text": "Traditional Medicine Diagnosis"
  }
}
```

> **Note:** The actual coding system URI and terminology codes should correspond to the validated terminology source used by the deployment.

---

# Data & Standards

MedBridge is designed around established healthcare interoperability and terminology standards, including:

* **WHO ICD-11**
* **WHO Traditional Medicine Module 2 (TM2)**
* **AYUSH NAMASTE terminology**
* **HL7 FHIR R4**
* **ABDM interoperability principles**

The terminology dataset and mappings should be validated against the latest authoritative releases before clinical or production deployment.

---

# Team

## The HexaDice

| Member             | Responsibility                            |
| ------------------ | ----------------------------------------- |
| **Sruthika**       | Team Lead, Backend Architecture & UI/UX   |
| **Yukthasree**     | Frontend Integration & Component Logic    |
| **Pradeeptha**     | Database Architecture & Data Sanitization |
| **Raga Varshitha** | Search Logic & Fuzzy Matching             |
| **Swetha**         | Research & Documentation                  |
| **Dharshini**      | Product Strategy & Pitch Development      |

---

# Development Highlights

Through MedBridge, the team worked on:

* Healthcare terminology interoperability
* Semantic search and information retrieval
* FHIR resource generation
* REST API development
* Authentication and role management
* Bulk healthcare data processing
* Audit logging
* Progressive Web App development
* Healthcare data standardization

---

# Future Scope

Potential extensions include:

* Multilingual Indian-language terminology support
* Transformer-based medical terminology matching
* Integration with hospital EMR/HIS systems
* Cloud-based terminology services
* Advanced consent and access-control mechanisms
* Expanded terminology coverage
* Automated terminology validation
* Healthcare analytics and monitoring
* Integration with additional ABDM ecosystem services

---

# License

This project is licensed under the **MIT License**.

---

## Smart India Hackathon

**MedBridge** was developed as a Smart India Hackathon project with the objective of improving interoperability between traditional medicine records and modern digital healthcare systems.

> **Bridging Traditional Medicine and Digital Healthcare.**
