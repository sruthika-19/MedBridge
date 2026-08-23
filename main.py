import os
import csv
import io
import datetime
import pandas as pd
from ai_scribe import extract_and_bundle_notes
from fastapi import FastAPI, BackgroundTasks, File, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from search_engine import search_disease
from fastapi.responses import StreamingResponse, PlainTextResponse, HTMLResponse
from typing import Optional

app = FastAPI(title = "MedBridge API")

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

class MappingRequest(BaseModel):
    term: str

class ScribeRequest(BaseModel):
    notes: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

def log_audit(term: str):
    with open("audit_log.txt", "a") as f:
        f.write(f"[{datetime.datetime.now()}] SEARCH QUERY: '{term}' | STATUS: Logged\n")

#@app.get("/", tags=["Health Check"])
#def home():
#    return {"message": "Welcome to the MedBridge API. Systems operational."}

@app.get("/sync/{disease_name}", summary="Search Traditional Term",tags=["EMR Integration"])
def get_icd_code(disease_name: str, system: Optional[str] = None, background_tasks: BackgroundTasks = None):
    if background_tasks:
        background_tasks.add_task(log_audit, f"{disease_name} (System: {system})")
    
    result = search_disease(disease_name, system_filter=system)
    return result

@app.post("/api/v1/map")
def map_term(request: MappingRequest, system: Optional[str] = None, background_tasks: BackgroundTasks = None):
    if background_tasks:
        background_tasks.add_task(log_audit, f"{request.term} (System: {system})")
        
    result = search_disease(request.term, system_filter=system)
    return result

@app.post("/api/v1/ai-scribe", tags=["Advanced AI Layer"])
def ai_clinical_scribe(request: ScribeRequest, background_tasks: BackgroundTasks = None):
    if background_tasks:
        background_tasks.add_task(log_audit, f"AI Scribe processed notes (Length: {len(request.notes)})")
    return extract_and_bundle_notes(request.notes)

@app.post("/api/v1/bulk-map", tags=["Enterprise Features"])
async def bulk_map_xlsx(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8")
    
    # Create a list to store rows instead of writing directly to CSV
    processed_data = []
    
    reader = csv.reader(io.StringIO(text))
    next(reader, None) # Skip header
    
    for row in reader:
        if not row: continue
        term = row[0].strip()
        result = search_disease(term)
        
        if result["status"] == "success":
            fhir = result["data"][0]
            modern_name = fhir["modernEquivalent"]
            processed_data.append([
                term,
                modern_name, 
                "Mapped", 
                fhir["code"]["coding"][0]["code"], 
                fhir["code"]["coding"][1]["code"], 
                fhir["confidenceScore"], 
                fhir["code"]["coding"][0]["system"].split(":")[-1].upper()
            ])
        else:
            processed_data.append([term, "N/A", "Failed", "N/A", "N/A", "N/A", "N/A"])

    # Create a Professional DataFrame
    df = pd.DataFrame(processed_data, columns=[
        "Original_Diagnosis", "Modern_Clinical_Name", "Status", 
        "NAMASTE_Code", "ICD_11_Code", "Confidence", "System"
    ])
    
    # Save to Excel in memory with auto-fit columns
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Mapped_Data')
        
        # Get the xlsxwriter or openpyxl worksheet object
        worksheet = writer.sheets['Mapped_Data']
        for idx, col in enumerate(df.columns):
            # Calculate column width based on max string length
            series = df[col].astype(str)
            max_len = max(series.map(len).max(), len(col)) + 4
            worksheet.column_dimensions[chr(65 + idx)].width = max_len
            
    output.seek(0)
    
    # Determine filename (swap .csv to .xlsx)
    new_filename = file.filename.replace('.csv', '.xlsx')
    
    return StreamingResponse(
        output, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={new_filename}"}
    )

@app.get("/api/v1/audit-logs", tags=["Enterprise Features"])
def get_audit_logs():
    log_file = "audit_log.txt"
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            logs = f.read()
        return PlainTextResponse(logs)
    return "No audit logs found yet. Perform a search to generate logs."

app.mount("/src", StaticFiles(directory="src"), name="src")

@app.get("/", response_class=HTMLResponse, tags=["Frontend Portal"])
async def serve_login():
    with open(os.path.join("src", "login.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/index.html", response_class=HTMLResponse, tags=["Frontend Portal"])
async def serve_dashboard():
    with open(os.path.join("src", "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin.html", response_class=HTMLResponse, tags=["Frontend Portal"])
async def serve_admin():
    with open(os.path.join("src", "admin.html"), "r", encoding="utf-8") as f:
        return f.read()