from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    # Varshitha's Search Logic

    return {
        "traditional_term": disease_name,
        "icd_11_code": "WAITING FOR VARSHITHA'S LOGIC"
    }