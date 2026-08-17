from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from search_engine import search_disease
import datetime

app = FastAPI(title = "MedBridge API")

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