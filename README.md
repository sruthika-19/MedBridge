# MedBridge

## Description
   
   **MedBridge** is an intelligent, search-based terminology bridge designed to make traditional medicine (Siddha and Ayurveda) digitally interoperable with modern healthcare systems. 
   
   - **What was your motivation?** Millions of patients rely on traditional medicine in India, yet their medical records hit a roadblock when transitioning to modern hospitals or applying for health insurance. We wanted to eliminate the data silos separating traditional and modern medicine.
   - **Why did you build this project?** We built MedBridge for Smart India Hackathon internal selections to create a seamless digital bridge. The goal is to ensure that no medical data is lost in translation and that traditional treatments can be recognized by national digital health infrastructures.
   - **What problem does it solve?** Traditional medical diagnoses do not directly translate into standardized modern medical codes (WHO ICD-11 / TM2 and NAMASTE codes). This disconnect causes manual translation errors, delays in patient care, and widespread insurance claim rejections. MedBridge instantly maps traditional terms to their exact FHIR-compliant equivalents.
   - **What did you learn?** We learned how to effectively sanitize and parse legacy spreadsheet data into a relational database, build zero-latency APIs using FastAPI with background audit logging, and design a stunning, cinematic "Cyber-Medical Terminal" interface with voice recognition and responsive glassmorphism aesthetics.

## Table of Contents
   
   - [Installation](#installation)
   - [Usage](#usage)
   - [Credits](#credits)
   - [License](#license)
   - [Badges](#badges)
   - [Features](#features)
   - [How to Contribute](#how-to-contribute)
   - [Tests](#tests)

## Installation

   To get the development environment running locally, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/sruthika-19/MedBridge](https://github.com/sruthika-19/MedBridge)
   cd MedBridge
   ```
   
2. **Install backend dependencies:**
   Ensure you have Python 3.10+ installed, then install the required packages:
   ```bash
   python -m pip install fastapi uvicorn
   ```

3. **Initialize the Database:**
   Generate the SQLite database (mappings.db) and populate the tables from the CSV dataset:
   ```bash
   python setup_db.py
   ```

## Usage
   MedBridge is designed to be lightweight and easy to use in resource-constrained clinic environments.
   
   1. **Start the API Server:**
   
   ```bash
   python -m uvicorn main:app --reload
   ```
   The backend will now be live at http://127.0.0.1:8000.
   
   2. **Launch the Frontend:**
   Open the index.html file directly in your web browser (or serve it locally). It connects instantly to your FastAPI backend with zero compilation required.

##  Credits

   **The HexaDice Team:**
   
   - **Sruthika** - Team Leader, Backend Architecture & UI/UX Design(@sruthika-19)
   - **Yukthasree** - Frontend Integration & Component Logic
   - **Pradeeptha** - Database Architecture & Data Sanitization
   - **Raga Varsitha** - Search Logic & Fuzzy Matching Integration
   - **Swetha** - Research &  Documentation
   - **Dharshini** - Product Strategy & Pitch Development

**Data & References:**

   Medical standardization mappings based on WHO ICD-11 / TM2 classifications, NAMASTE portal codes, and Ministry of Ayush guidelines.

##  License
   This project is licensed under the MIT License - see the LICENSE page for details.

##  Badges
## Features
   - **Cyber-Medical Terminal UI:** A gorgeous dark-mode glassmorphic interface featuring a custom 3D isometric block logo/favicon, neon cyan/blue accents, and smooth entrance animations.

   - **Voice & Text Search:** Integrated Web Speech API support (en-IN) allowing clinicians to speak diagnoses directly into the search bar with live visual feedback.

   - **Fuzzy Terminology Search:** Robust backend matching using Python's difflib to accurately map misspelled or approximate traditional terms with calculated confidence scores (High Confidence vs. Review Suggested).

   - **Dual Coding Standard Output:** Instantly bridges Siddha/Ayurveda terms to both NAMASTE codes and WHO ICD-11 / TM2 disease codes.

   - **FHIR Payload Generation & Copy:** Formats search results into structured, standards-compliant JSON FHIR Condition resources with a one-click copy tool and raw payload inspector.

   - **Zero-Latency Async Backend:** Built on FastAPI with background audit logging (audit_log.txt) for tracking search requests cleanly.

   - **Unified Cyber-Glass Status Feedback:** Modern translucent glowing badges and alert containers replacing harsh, legacy solid-color error blocks.

## How to Contribute
   If you would like to contribute to MedBridge (e.g., by adding more traditional medical mappings or improving the search logic):
   
   1. Fork the Project
   
   2. Create your Feature Branch (git checkout -b feature/AmazingFeature)
   
   3. Commit your Changes (git commit -m 'Add some AmazingFeature')
   
   4. Push to the Branch (git push origin feature/AmazingFeature)

   5. Open a Pull Request

## Tests
   You can test the API endpoints directly using FastAPI's built-in interactive documentation.
   
   1. Ensure the local server is running.
   
   2. Navigate to http://127.0.0.1:8000/docs in your browser.
   
   3. Use the Swagger UI to execute test queries against the /sync/{disease_name} endpoint to verify mappings, error messages, and FHIR payloads.
