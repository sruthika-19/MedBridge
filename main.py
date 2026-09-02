
import os
import csv
import io
import json
import datetime
import pandas as pd
import math
import requests
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ai_scribe import extract_and_bundle_notes

from fastapi import (
    FastAPI,
    BackgroundTasks,
    File,
    UploadFile,
    HTTPException
)

from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, PlainTextResponse, HTMLResponse

from search_engine import search_disease

from typing import Optional

# ============================================================
# PATIENT MODULE IMPORTS
# ============================================================

from patient_module import (
    get_all_patients,
    get_patient,
    add_condition_to_patient
)


app = FastAPI(title="MedBridge API")


# ============================================================
# FRONTEND ROUTES
# ============================================================

@app.get("/", response_class=HTMLResponse, tags=["Frontend Portal"])
async def serve_frontend():
    login_path = os.path.join("src", "login.html")

    if os.path.exists(login_path):
        with open(login_path, "r", encoding="utf-8") as f:
            return f.read()

    return "<h1>login.html not found in src</h1>"


@app.get("/index.html", response_class=HTMLResponse, tags=["Frontend Portal"])
async def serve_dashboard():
    index_path = os.path.join("src", "index.html")

    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()

    return "<h1>index.html not found in src</h1>"


@app.get("/admin.html", response_class=HTMLResponse, tags=["Frontend Portal"])
async def serve_admin():
    admin_path = os.path.join("src", "admin.html")

    if os.path.exists(admin_path):
        with open(admin_path, "r", encoding="utf-8") as f:
            return f.read()

    return "<h1>admin.html not found in src</h1>"


# ============================================================
# PYDANTIC MODELS
# ============================================================

class MappingRequest(BaseModel):
    term: str


class ScribeRequest(BaseModel):
    notes: str


class PatientConditionRequest(BaseModel):
    condition: str
    namaste_code: Optional[str] = None
    icd11_code: Optional[str] = None


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STRUCTURED AUDIT LOG
# ============================================================

def log_audit(event: dict) -> None:
    """
    Write one structured audit event to audit_log.jsonl.

    Security rules:
    - Never store passwords.
    - Never store API keys or access tokens.
    - Never store complete patient clinical records.
    - Store only the minimum information required for auditing.
    """

    safe_event = {
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),

        "user": event.get(
            "user",
            "demo-user"
        ),

        "role": event.get(
            "role",
            "clinician"
        ),

        "action": event.get(
            "action",
            "UNKNOWN"
        ),

        "input": event.get(
            "input"
        ),

        "mapping": event.get(
            "mapping"
        ),

        "source": event.get(
            "source",
            "MedBridge"
        ),

        "status": event.get(
            "status",
            "success"
        )
    }

    with open(
        "audit_log.jsonl",
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(
                safe_event,
                ensure_ascii=False
            ) + "\n"
        )


# ============================================================
# PATIENT MODULE
# ============================================================

@app.get(
    "/api/v1/patients",
    tags=["Patient Module"]
)
def list_patients(
    background_tasks: BackgroundTasks
):

    background_tasks.add_task(
        log_audit,
        {
            "action": "PATIENT_VIEW",
            "input": {
                "view": "all_patients"
            },
            "source": "Patient Module",
            "status": "success"
        }
    )

    return {
        "status": "success",
        "patients": get_all_patients()
    }


@app.get(
    "/api/v1/patients/{patient_id}",
    tags=["Patient Module"]
)
def get_patient_details(
    patient_id: str,
    background_tasks: BackgroundTasks
):

    patient = get_patient(patient_id)

    if patient is None:

        background_tasks.add_task(
            log_audit,
            {
                "action": "ACCESS_DENIED",
                "input": {
                    "patient_id": patient_id
                },
                "source": "Patient Module",
                "status": "failed"
            }
        )

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Only log patient ID, not the complete patient record.
    background_tasks.add_task(
        log_audit,
        {
            "action": "PATIENT_VIEW",
            "input": {
                "patient_id": patient_id
            },
            "source": "Patient Module",
            "status": "success"
        }
    )

    return {
        "status": "success",
        "patient": patient
    }


@app.post(
    "/api/v1/patients/{patient_id}/conditions",
    tags=["Patient Module"]
)
def add_patient_condition(
    patient_id: str,
    request: PatientConditionRequest,
    background_tasks: BackgroundTasks
):

    patient = add_condition_to_patient(
        patient_id=patient_id,
        condition=request.condition,
        namaste_code=request.namaste_code,
        icd11_code=request.icd11_code
    )

    if patient is None:

        background_tasks.add_task(
            log_audit,
            {
                "action": "ACCESS_DENIED",
                "input": {
                    "patient_id": patient_id
                },
                "source": "Patient Module",
                "status": "failed"
            }
        )

        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Log only the mapping information.
    background_tasks.add_task(
        log_audit,
        {
            "action": "MAPPING_UPDATED",
            "input": {
                "patient_id": patient_id,
                "condition": request.condition
            },
            "mapping": {
                "namaste_code": request.namaste_code,
                "icd11_code": request.icd11_code
            },
            "source": "Patient Module",
            "status": "success"
        }
    )

    return {
        "status": "success",
        "message": "Condition added successfully",
        "patient": patient
    }


# ============================================================
# EXISTING MAPPING / SEARCH API
# ============================================================

@app.get(
    "/sync/{disease_name}",
    summary="Search Traditional Term",
    tags=["EMR Integration"]
)
def get_icd_code(
    disease_name: str,
    system: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):

    if background_tasks:

        background_tasks.add_task(
            log_audit,
            {
                "action": "TERM_SEARCH",
                "input": {
                    "term": disease_name,
                    "system": system
                },
                "source": "Search Engine",
                "status": "success"
            }
        )

    result = search_disease(
        disease_name,
        system_filter=system
    )

    return result


@app.post(
    "/api/v1/map",
    tags=["Terminology Mapping"]
)
def map_term(
    request: MappingRequest,
    system: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):

    if background_tasks:

        background_tasks.add_task(
            log_audit,
            {
                "action": "TERM_SEARCH",
                "input": {
                    "term": request.term,
                    "system": system
                },
                "source": "Search Engine",
                "status": "success"
            }
        )

    result = search_disease(
        request.term,
        system_filter=system
    )

    return result


# ============================================================
# AI SCRIBE
# ============================================================

@app.post(
    "/api/v1/ai-scribe",
    tags=["Advanced AI Layer"]
)
def ai_clinical_scribe(
    request: ScribeRequest,
    background_tasks: BackgroundTasks = None
):

    result = extract_and_bundle_notes(
        request.notes
    )

    if background_tasks:

        background_tasks.add_task(
            log_audit,
            {
                "action": "FHIR_GENERATED",
                "input": {
                    "note_length": len(request.notes)
                },
                "mapping": {
                    "extracted_terms":
                        result.get(
                            "extractedTerms",
                            []
                        ),
                    "mapped_conditions":
                        len(
                            result.get(
                                "mappedConditions",
                                []
                            )
                        )
                },
                "source": "AI Scribe + FHIR",
                "status": result.get(
                    "status",
                    "unknown"
                )
            }
        )

    return result


# ============================================================
# BULK MAPPING
# ============================================================

@app.post(
    "/api/v1/bulk-map",
    tags=["Enterprise Features"]
)
async def bulk_map_xlsx(
    file: UploadFile = File(...)
):

    content = await file.read()
    text = content.decode("utf-8")

    processed_data = []

    reader = csv.reader(
        io.StringIO(text)
    )

    next(
        reader,
        None
    )

    for row in reader:

        if not row:
            continue

        term = row[0].strip()

        result = search_disease(term)

        if result["status"] == "success":

            fhir = result["data"][0]

            modern_name = fhir[
                "modernEquivalent"
            ]

            processed_data.append([
                term,
                modern_name,
                "Mapped",
                fhir["code"]["coding"][0]["code"],
                fhir["code"]["coding"][1]["code"],
                fhir["confidenceScore"],
                fhir["code"]["coding"][0]["system"]
                    .split(":")[-1]
                    .upper()
            ])

        else:

            processed_data.append([
                term,
                "N/A",
                "Failed",
                "N/A",
                "N/A",
                "N/A",
                "N/A"
            ])

    df = pd.DataFrame(
        processed_data,
        columns=[
            "Original_Diagnosis",
            "Modern_Clinical_Name",
            "Status",
            "NAMASTE_Code",
            "ICD_11_Code",
            "Confidence",
            "System"
        ]
    )

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Mapped_Data"
        )

        worksheet = writer.sheets[
            "Mapped_Data"
        ]

        for idx, col in enumerate(
            df.columns
        ):

            series = df[col].astype(str)

            max_len = max(
                series.map(len).max(),
                len(col)
            ) + 4

            worksheet.column_dimensions[
                chr(65 + idx)
            ].width = max_len

    output.seek(0)

    new_filename = file.filename.replace(
        ".csv",
        ".xlsx"
    )

    return StreamingResponse(
        output,
        media_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
            f"attachment; filename={new_filename}"
        }
    )


# ============================================================
# STRUCTURED AUDIT LOG API
# ============================================================

@app.get(
    "/api/v1/audit-logs",
    tags=["Enterprise Features"]
)
def get_audit_logs():

    log_file = "audit_log.jsonl"

    if not os.path.exists(log_file):

        return PlainTextResponse(
            "No audit logs found yet. "
            "Perform an operation to generate logs."
        )

    with open(
        log_file,
        "r",
        encoding="utf-8"
    ) as f:

        logs = f.read()

    return PlainTextResponse(
        logs,
        media_type="application/x-ndjson"
    )


# ============================================================
# LOCATION / CLINIC MODULE
# ============================================================

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    condition_system: str = "Siddha"


def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):

    R = 6371.0

    dlat = math.radians(
        lat2 - lat1
    )

    dlon = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(
            math.radians(lat1)
        )
        *
        math.cos(
            math.radians(lat2)
        )
        *
        math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return round(
        R * c,
        2
    )


@app.post(
    "/api/v1/nearby-clinics",
    tags=["IoT Referral System"]
)
async def get_nearby_clinics(
    req: LocationRequest,
    background_tasks: BackgroundTasks = None
):

    try:

        if background_tasks:

            background_tasks.add_task(
                log_audit,
                {
                    "action": "PATIENT_VIEW",
                    "input": {
                        "operation":
                            "nearby_clinics"
                    },
                    "source": "Geo Routing",
                    "status": "success"
                }
            )

        radius = 5000

        overpass_url = (
            "http://overpass-api.de/api/interpreter"
        )

        overpass_query = f"""
        [out:json][timeout:5];
        (
          node["amenity"~"hospital|clinic"](
              around:{radius},
              {req.latitude},
              {req.longitude}
          );

          node["healthcare"](
              around:{radius},
              {req.latitude},
              {req.longitude}
          );
        );
        out body;
        """

        headers = {
            "User-Agent":
                "MedBridge-EMR/1.0"
        }

        response = requests.get(
            overpass_url,
            params={
                "data": overpass_query
            },
            headers=headers,
            timeout=6
        )

        if response.status_code == 200:

            data = response.json()

            results = []

            for element in data.get(
                "elements",
                []
            ):

                lat = element.get(
                    "lat"
                )

                lon = element.get(
                    "lon"
                )

                if lat is None or lon is None:
                    continue

                tags = element.get(
                    "tags",
                    {}
                )

                name = (
                    tags.get("name")
                    or tags.get("operator")
                    or "Verified Health Center"
                )

                dist = calculate_distance(
                    req.latitude,
                    req.longitude,
                    lat,
                    lon
                )

                results.append({
                    "id":
                        element.get("id"),

                    "name":
                        name,

                    "doctor":
                        tags.get(
                            "doctor",
                            "Dr. Ayush Specialist"
                        ),

                    "specialties": [
                        req.condition_system,
                        tags.get(
                            "healthcare:speciality",
                            "Traditional Care"
                        )
                    ],

                    "distance_km":
                        dist,

                    "lat":
                        lat,

                    "lng":
                        lon
                })

            if results:

                results.sort(
                    key=lambda x:
                        x["distance_km"]
                )

                return {
                    "status":
                        "success",

                    "clinics":
                        results[:3]
                }

        raise Exception(
            "Overpass returned no nodes."
        )

    except Exception as e:

        if background_tasks:

            background_tasks.add_task(
                log_audit,
                {
                    "action": "API_ERROR",
                    "input": {
                        "operation":
                            "nearby_clinics"
                    },
                    "source": "Geo Routing",
                    "status": "failed"
                }
            )

        fallback_clinics = [

            {
                "id": 201,

                "name":
                    "Kokila Siddha Hospital & Research Centre",

                "doctor":
                    "Dr. J. Jeyavenkatesh (BSMS)",

                "specialties": [
                    req.condition_system,
                    "Siddha Clinical Research"
                ],

                "distance_km":
                    3.4,

                "lat":
                    9.9050,

                "lng":
                    78.1060
            },

            {
                "id": 202,

                "name":
                    "Pathanjali Siddha Vaidya Nilayam",

                "doctor":
                    "Dr. R. Karthik (BSMS)",

                "specialties": [
                    req.condition_system,
                    "Traditional Therapeutics"
                ],

                "distance_km":
                    5.8,

                "lat":
                    9.9270,

                "lng":
                    78.1450
            },

            {
                "id": 203,

                "name":
                    "Dhanvanthri Nilayam Ayurveda Vaidhyasalai",

                "doctor":
                    "Dr. S. Dhanvanthri Premvel",

                "specialties": [
                    req.condition_system,
                    "Ayurvedic Care"
                ],

                "distance_km":
                    7.2,

                "lat":
                    9.8960,

                "lng":
                    78.1040
            }
        ]

        return {
            "status":
                "success",

            "clinics":
                fallback_clinics
        }


# ============================================================
# REFERRAL SYSTEM
# ============================================================

class ReferralRequest(BaseModel):
    clinic_name: str
    doctor_name: str
    condition: str
    distance: str


def send_email_background(
    req: ReferralRequest
):

    sender_email = os.getenv(
        "GMAIL_SENDER_EMAIL"
    )

    sender_password = os.getenv(
        "GMAIL_APP_PASSWORD"
    )

    receiver_email = os.getenv(
        "GMAIL_SENDER_EMAIL"
    )

    msg = MIMEMultipart()

    msg["From"] = sender_email
    msg["To"] = receiver_email

    msg["Subject"] = (
        f"URGENT: ABDM Patient Referral "
        f"to {req.clinic_name}"
    )

    body = f"""
    🏥 MEDBRIDGE EMR - AUTOMATED REFERRAL REQUEST
    ======================================================

    You have received a new secure patient transfer generated
    via the MedBridge Interoperability Gateway.

    TARGET FACILITY DETAILS:
    - Clinic Name: {req.clinic_name}
    - Attending Physician: {req.doctor_name}
    - Distance from originating facility: {req.distance} km

    CLINICAL DATA:
    - Patient Condition / System Match: {req.condition}

    ACTION REQUIRED:
    Please log in to the MedBridge Admin Portal to review
    the attached FHIR R4 Condition Payload and accept
    this transfer.

    ======================================================
    Powered by MedBridge - Smart India Hackathon Prototype
    """

    msg.attach(
        MIMEText(
            body,
            "plain"
        )
    )

    try:

        server = smtplib.SMTP(
            "smtp.gmail.com",
            587
        )

        server.starttls()

        server.login(
            sender_email,
            sender_password
        )

        text = msg.as_string()

        server.sendmail(
            sender_email,
            receiver_email,
            text
        )

        server.quit()

        log_audit(
            {
                "action": "FHIR_EXPORTED",
                "input": {
                    "operation":
                        "referral",
                    "clinic":
                        req.clinic_name,
                    "condition":
                        req.condition
                },
                "source":
                    "Referral System",
                "status":
                    "success"
            }
        )

    except Exception as e:

        print(
            f"Failed to send email: {e}"
        )

        log_audit(
            {
                "action": "API_ERROR",
                "input": {
                    "operation":
                        "referral",
                    "clinic":
                        req.clinic_name
                },
                "source":
                    "Referral System",
                "status":
                    "failed"
            }
        )


@app.post(
    "/api/v1/send-referral",
    tags=["IoT Referral System"]
)
async def trigger_referral(
    req: ReferralRequest,
    background_tasks: BackgroundTasks
):

    background_tasks.add_task(
        send_email_background,
        req
    )

    return {
        "status":
            "success",

        "message":
            "Secure email dispatched"
    }


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/src",
    StaticFiles(
        directory="src"
    ),
    name="src"
)

