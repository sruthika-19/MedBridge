const searchButton = document.getElementById("searchButton");
const diseaseInput = document.getElementById("diseaseInput");
const micButton = document.getElementById("micButton");
const result = document.getElementById("result");
const emrIntegration = document.getElementById("emrIntegration");

diseaseInput.addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault(); 
        searchButton.click();   
    }
});

let lastRawJSON = "";

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-IN'; 

    micButton.addEventListener("click", () => {
        diseaseInput.placeholder = "Listening...";
        micButton.style.background = "#ff4444"; 
        recognition.start();
    });

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        diseaseInput.value = transcript;
        micButton.style.background = "#e0e0e0";
        diseaseInput.placeholder = "Enter diagnosis";
        searchButton.click(); 
    };

    recognition.onerror = () => {
        micButton.style.background = "#e0e0e0";
        diseaseInput.placeholder = "Enter diagnosis";
    };
} 
else {
    micButton.style.display = "none"; 
}

// 🚨 FIX 1: Added 'event' and 'event.preventDefault()' to the Search Button
searchButton.addEventListener("click", async function (event) {
    event.preventDefault(); 
    
    const disease = diseaseInput.value.trim();
    emrIntegration.innerHTML = "";

    if (!disease) {
        result.innerHTML = `<div class="alert-danger text-center mt-4">Error: Please enter a diagnosis.</div>`;
        return;
    }

    result.innerHTML = `
        <div class="d-flex align-items-center text-primary mt-3">
            <div class="spinner-border spinner-border-sm me-2" role="status"></div>
            <strong>Searching and mapping to FHIR standards...</strong>
        </div>
    `;

    try {
        const response = await fetch(
            `http://127.0.0.1:8000/sync/${encodeURIComponent(disease)}`
        );

        const data = await response.json();

        if (data.status === "success") {
            const fhirData = data.data[0];
            lastRawJSON = JSON.stringify(fhirData, null, 2); 

            const confScore = parseFloat(fhirData.confidenceScore);
            const badgeClass = confScore >= 90 ? "bg-success" : "bg-warning text-dark";
            const badgeText = confScore >= 90 ? `High Confidence Match: ${confScore}%` : `Review Suggested: ${confScore}% match`;

            const sysUrl = fhirData.code.coding[0].system;
            const systemName = sysUrl.split(':').pop().toUpperCase();
            const termName = fhirData.code.text;
            const namasteCode = fhirData.code.coding[0].code;
            const tm2Code = fhirData.code.coding[1].code;

            result.innerHTML = `
                <div class="card shadow-sm border-0 position-relative mt-4">
                    <div class="card-body p-4">
                        <button id="copyButton" class="btn btn-outline-primary btn-sm position-absolute top-0 end-0 m-3" onclick="copyJSON()">📋 Copy FHIR Payload</button>
                        
                        <span class="badge rounded-pill ${badgeClass} mb-4 px-3 py-2" style="font-size: 0.85rem;">${badgeText}</span>
                        
                        <div class="row mb-2">
                            <div class="col-sm-4 text-muted fw-bold">System:</div>
                            <div class="col-sm-8 text-dark">${systemName}</div>
                        </div>
                        <div class="row mb-2">
                            <div class="col-sm-4 text-muted fw-bold">Traditional Term:</div>
                            <div class="col-sm-8 text-dark">${termName}</div>
                        </div>
                        <div class="row mb-2">
                            <div class="col-sm-4 text-muted fw-bold">NAMASTE Code:</div>
                            <div class="col-sm-8 text-dark">${namasteCode}</div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-sm-4 text-muted fw-bold">TM2 / ICD-11 Code:</div>
                            <div class="col-sm-8 text-dark">${tm2Code}</div>
                        </div>
                        
                        <details class="mt-3">
                            <summary class="text-primary fw-semibold" style="cursor:pointer; outline: none;">View Raw FHIR Payload</summary>
                            <pre class="bg-dark text-light p-3 mt-3 rounded overflow-x-auto" style="font-size: 13px;">${lastRawJSON}</pre>
                        </details>
                    </div>
                </div>
            `;

            emrIntegration.innerHTML = `
            <div class="glass-panel p-4 mt-4">
                <h4 class="emr-title mb-2">EMR Integration</h4>

                <p class="emr-description mb-3">
                    Send this diagnosis to the MedBridge API as an external EMR would.
                </p>

                <button
                    id="emrButton"
                    class="btn btn-primary search-btn px-4 fw-bold"
                    type="button"
                    data-diagnosis="${disease}">
                    🔗 Send to MedBridge API
                </button>

                <div id="emrResult" class="mt-3"></div>
            </div>
        `;
        
        const emrButton = document.getElementById("emrButton");
        const emrResult = document.getElementById("emrResult");

        // 🚨 FIX 2: Added 'event' and 'event.preventDefault()' to the EMR Send Button
        emrButton.addEventListener("click", async function (event) {
            event.preventDefault();

            emrResult.innerHTML = `
                <div class="emr-status">
                    Sending diagnosis to MedBridge API...
                </div>
            `;

            try {
                const response = await fetch(
                    "http://127.0.0.1:8000/api/v1/map",
                    {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({
                                term: disease
})
                    }
                );

                const apiData = await response.json();
                if (apiData.status === "success") {

                    const apiFHIR = apiData.data[0];
                    const apiNamaste = apiFHIR.code.coding[0].code;

                    const apiTM2 = apiFHIR.code.coding[1].code;

                    emrResult.innerHTML = `
                        <div class="emr-response">
                            <div class="mb-2">
                                <strong>API Status:</strong>
                                <span class="success-text">
                                    Connected
                                </span>
                            </div>
                            <div class="mb-2">
                                <strong>Diagnosis:</strong>
                                ${apiFHIR.code.text}
                            </div>
                            <div class="mb-2">
                                <strong>NAMASTE:</strong>
                                ${apiNamaste}
                            </div>
                            <div class="mb-2">
                                <strong>TM2 / ICD-11:</strong>
                                ${apiTM2}
                            </div>
                            <div>
                                <strong>FHIR:</strong>
                                <span class="success-text">
                                    Valid Response Received
                                </span>
                            </div>
                        </div>
                    `;

                } else {
                    emrResult.innerHTML = `
                        <div class="alert-danger text-center">
                            ${apiData.message}
                        </div>
                    `;
                }

            } catch (error) {
                emrResult.innerHTML = `
                    <div class="alert-danger text-center">
                        Unable to connect to MedBridge API.
                    </div>
                `;

                console.error(error);
            }
        });

        } else {
            emrIntegration.innerHTML = "";

            result.innerHTML = `
                <div class="alert-danger text-center mt-4">
                    ${data.message}
                </div>
            `;
        }

    } catch (error) {
        emrIntegration.innerHTML = "";
        result.innerHTML = `<div class="alert-danger text-center mt-4">Unable to connect to the MedBridge API.</div>`;
        console.error(error);
    }
});

window.copyJSON = function() {
    navigator.clipboard.writeText(lastRawJSON).then(() => {
        const btn = document.getElementById("copyButton");
        btn.textContent = "Copied!";
        setTimeout(() => btn.textContent = "📋 Copy FHIR Payload", 2000);
    });
};

const bulkUploadBtn = document.getElementById("bulkUploadBtn");
const csvFileInput = document.getElementById("csvFileInput");
const bulkResult = document.getElementById("bulkResult");

// 🚨 FIX 3: Added 'event' and 'event.preventDefault()' to the Bulk Upload Button
bulkUploadBtn.addEventListener("click", async function(event) {
    event.preventDefault();

    const file = csvFileInput.files[0];
    
    if (!file) {
        bulkResult.innerHTML = "<span class='text-danger'>Please select a .csv file first!</span>";
        return;
    }

    bulkResult.innerHTML = `<div class="spinner-border spinner-border-sm text-info me-2"></div> Mapping thousands of records...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("http://127.0.0.1:8000/api/v1/bulk-map", {
            method: "POST",
            body: formData
        });

        if (response.ok) {
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = `MedBridge_Standardized_${file.name}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            
            bulkResult.innerHTML = "✅ Success! File standardized and downloaded.";
        } else {
            bulkResult.innerHTML = "<span class='text-danger'>Server error processing file.</span>";
        }
    } catch (error) {
        console.error(error);
        bulkResult.innerHTML = "<span class='text-danger'>Failed to connect to MedBridge API.</span>";
    }
});

const fileNameDisplay = document.getElementById('fileNameDisplay');
const dropZone = document.getElementById('dropZone');

csvFileInput.addEventListener('change', function(e) {
    if(this.files.length > 0) {
        fileNameDisplay.textContent = '📄 Selected: ' + this.files[0].name;
        fileNameDisplay.classList.remove('d-none');
        
        dropZone.style.borderColor = '#00e5ff';
        dropZone.style.background = 'rgba(0, 229, 255, 0.05)';
    } else {
        fileNameDisplay.classList.add('d-none');
        dropZone.style.borderColor = 'rgba(0, 229, 255, 0.4)';
    }
});