# MedBridge

## Description
   
   **MedBridge** is an intelligent, search-based terminology bridge designed to make traditional Ayurvedic medicine digitally interoperable with modern healthcare systems. 
   
   - **What was your motivation?** Millions of patients rely on traditional Ayurvedic medicine in India, yet their medical records hit a roadblock when transitioning to modern hospitals or applying for health insurance. We wanted to eliminate the data silos separating traditional and modern medicine.
   - **Why did you build this project?** We built MedBridge for the Smart India Hackathon 2026 to create a seamless digital bridge. The goal is to ensure that no medical data is lost in translation and that traditional treatments can be recognized by national digital health infrastructures.
   - **What problem does it solve?** Traditional Ayurvedic diagnoses do not directly translate into standardized modern medical codes (WHO ICD-11). This disconnect causes manual translation errors, delays in patient care, and widespread insurance claim rejections. MedBridge instantly maps Ayurvedic terms to their exact ICD-11 equivalents.
   - **What did you learn?** We learned how to effectively sanitize and parse legacy spreadsheet data into a relational database, build zero-latency APIs using FastAPI, and design a lightweight, clinic-ready frontend that does not require heavy compute resources.

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
   git clone https://github.com/sruthika-19/MedBridge
   cd MedBridge
   ```
   
2. **Install backend dependencies:**
   Ensure you have Python 3.8+ installed, then install the required packages:
   ```bash
   python -m pip install fastapi uvicorn
   ```

3. **Initialize the Database:**
   Generate the SQLite database (mappings.db) and populate the tables from the provided dataset:
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
   Open the index.html file in your preferred web browser. The interface will automatically connect to your local server without needing a separate frontend framework to be compiled.

##  Credits
   **The MedBridge Team:**
   
   - **Sruthika** - Team Lead & Backend Developer (@sruthika-19)
   - **Yukthasree** - Frontend Engineering & UI/UX
   - **Pradeeptha** - Database Architecture & Data Sanitization
   - **Raga Varsitha** - Search Logic & API Integration
   - **Swetha** - Frontend Resource Research
   - **Dharshini** - Product Strategy & Pitch Development

**Data & References:**

   Medical standardization mappings based on WHO ICD-11 classifications and Ministry of Ayush guidelines.

##  License
   This project is licensed under the MIT License - see the LICENSE page for details.

##  Badges
## Features
   - Instant Terminology Search: Fast and lightweight querying of traditional terms.
   
   - ICD-11 Mapping: Directly links Ayurvedic terms to modern medical billing and diagnosis codes.
   
   - Zero-Latency Architecture: Built on FastAPI and SQLite for immediate retrieval.
   
   - Accessible UI: A clean, responsive web interface that runs smoothly on any clinic computer, regardless of age or hardware limits.

## How to Contribute
   If you would like to contribute to MedBridge (e.g., by adding more traditional medical mappings or improving the NLP search logic):
   
   1. Fork the Project
   
   2. Create your Feature Branch (git checkout -b feature/AmazingFeature)
   
   3. Commit your Changes (git commit -m 'Add some AmazingFeature')
   
   4. Push to the Branch (git push origin feature/AmazingFeature)

   5. Open a Pull Request

## Tests
   You can test the API endpoints directly using FastAPI's built-in interactive documentation.
   
   1. Ensure the local server is running.
   
   2. Navigate to http://127.0.0.1:8000/docs in your browser.
   
   3. Use the Swagger UI to execute test queries against the /sync/{disease_name} endpoint to verify database mappings are returning correctly and handling edge cases (like trailing spaces).
