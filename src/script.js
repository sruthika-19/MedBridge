const searchButton = document.getElementById("searchButton");
const diseaseInput = document.getElementById("diseaseInput");
const micButton = document.getElementById("micButton");
const result = document.getElementById("result");

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

searchButton.addEventListener("click", async function () {
    const disease = diseaseInput.value.trim();

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
            const badgeText = confScore >= 90 ? `✅ High Confidence Match: ${confScore}%` : `⚠️ Review Suggested: ${confScore}% match`;

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
        } else {
           result.innerHTML = `<div class="alert-danger text-center mt-4">${data.message}</div>`;
        }

    } catch (error) {
        result.innerHTML = `<div class="alert-danger text-center mt-4">Unable to connect to the MedBridge API.</div>`;
        console.error(error);
    }
});

window.copyJSON = function() {
    navigator.clipboard.writeText(lastRawJSON).then(() => {
        const btn = document.getElementById("copyButton");
        btn.textContent = "✅ Copied!";
        setTimeout(() => btn.textContent = "📋 Copy FHIR Payload", 2000);
    });
};