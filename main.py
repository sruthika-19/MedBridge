from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from search_engine import search_disease

# Initialize FastAPI app
app = FastAPI(title = "MedBridge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

@app.get("/")
def home():
    return {"message": "Welcome to the MedBridge API!"}

@app.get("/sync/{disease_name}")
def get_icd_code(disease_name: str):
    result = search_disease(disease_name)
    return result
