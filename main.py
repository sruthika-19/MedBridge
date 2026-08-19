import os
import csv
import io
import datetime
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from search_engine import search_disease
from fastapi import File, UploadFile
from fastapi.responses import StreamingResponse, PlainTextResponse

app = FastAPI(title = "MedBridge API")
class MappingRequest(BaseModel):
    term: str

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

@app.get("/", tags=["Health Check"])
def home():
    return {"message": "Welcome to the MedBridge API. Systems operational."}

@app.get(
    "/sync/{disease_name}", 
    summary="Search Traditional Term",
    tags=["EMR Integration"]
)

def get_icd_code(disease_name: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(log_audit, disease_name)
    result = search_disease(disease_name)
    return result

@app.post("/api/v1/map")
def map_term(request: MappingRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        log_audit,
        request.term
    )
    result = search_disease(request.term)
    return result

@app.post("/api/v1/bulk-map", tags=["Enterprise Features"])
async def bulk_map_csv(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8")
    
    output_csv = io.StringIO()
    writer = csv.writer(output_csv)
    
    writer.writerow(["Original_Diagnosis", "Status", "NAMASTE_Code", "ICD_11_Code", "Confidence", "System"])
    
    reader = csv.reader(io.StringIO(text))
    next(reader, None)
    
    success_count = 0
    fail_count = 0

    for row in reader:
        if not row: continue
        term = row[0].strip()
        result = search_disease(term)
        
        if result["status"] == "success":
            fhir = result["data"][0]
            namaste = fhir["code"]["coding"][0]["code"]
            icd = fhir["code"]["coding"][1]["code"]
            conf = fhir["confidenceScore"]
            sys_name = fhir["code"]["coding"][0]["system"].split(":")[-1].upper()
            
            writer.writerow([term, "Mapped", namaste, icd, conf, sys_name])
            success_count += 1
        else:
            writer.writerow([term, "Failed (Needs Manual Review)", "N/A", "N/A", "N/A", "N/A"])
            fail_count += 1

    output_csv.seek(0)
    
    print(f"Bulk Processed: {success_count} mapped, {fail_count} failed.")
    
    return StreamingResponse(
        output_csv, 
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=MedBridge_Standardized_{file.filename}"}
    )

@app.get("/api/v1/audit-logs", tags=["Enterprise Features"])
def get_audit_logs():
    log_file = "audit_log.txt"
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            logs = f.read()
        return PlainTextResponse(logs)
    return "No audit logs found yet. Perform a search to generate logs."