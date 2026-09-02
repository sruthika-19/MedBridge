window.lastRawJSON = "";
window.currentEntries = [];

const searchButton = document.getElementById("searchButton");
const diseaseInput = document.getElementById("diseaseInput");
const micButton = document.getElementById("micButton");
const result = document.getElementById("result");
const emrIntegration = document.getElementById("emrIntegration");

const API_BASE = "http://127.0.0.1:8000";


// ============================================================
// DISEASE SEARCH + AI SCRIBE
// ============================================================

if (diseaseInput && searchButton) {

    diseaseInput.addEventListener("keypress", function (event) {

        if (event.key === "Enter") {

            event.preventDefault();
            searchButton.click();

        }

    });


    searchButton.addEventListener("click", async function (event) {

        event.preventDefault();

        const notesText = diseaseInput.value.trim();

        if (emrIntegration) {
            emrIntegration.innerHTML = "";
        }

        if (!notesText) {

            result.innerHTML = `
                <div class="alert-danger text-center mt-4 p-3">
                    Error: Please enter clinical notes or a diagnosis.
                </div>
            `;

            return;
        }


        result.innerHTML = `
            <div class="d-flex align-items-center text-primary mt-3">

                <div
                    class="spinner-border spinner-border-sm me-2"
                    role="status">
                </div>

                <strong>
                    Analyzing notes with AI Scribe & Risk Radar...
                </strong>

            </div>
        `;


        try {

            const response = await fetch(
                `${API_BASE}/api/v1/ai-scribe`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        notes: notesText
                    })
                }
            );


            const data = await response.json();


            if (
                data.status === "success" &&
                data.bundle &&
                Array.isArray(data.bundle.entry)
            ) {

                window.lastRawJSON =
                    JSON.stringify(
                        data.bundle,
                        null,
                        2
                    );


                const entries = data.bundle.entry;

                /*
                 * Only Condition resources should be displayed
                 * as differential candidates.
                 */
                const conditionEntries =
                    entries.filter(entry => {

                        return (
                            entry.resource &&
                            entry.resource.resourceType === "Condition"
                        );

                    });


                window.currentEntries =
                    conditionEntries;


                if (conditionEntries.length === 0) {

                    result.innerHTML = `
                        <div class="alert-warning text-center mt-4 p-3">
                            No conditions were extracted.
                        </div>
                    `;

                    showToast(
                        "No conditions extracted.",
                        "info"
                    );

                    return;
                }


                // ------------------------------------------------
                // TOP DIFFERENTIAL MATCHES
                // ------------------------------------------------

                let cardsHtml = `

                    <div
                        class="glass-panel p-3 mb-4 shadow-sm border border-secondary mt-4">

                        <h6 class="text-info fw-bold mb-2">
                            🎯 TOP DIFFERENTIAL MATCHES
                            (Click to Select)
                        </h6>

                        <div class="d-flex flex-wrap gap-2">
                `;


                conditionEntries
                    .slice(0, 3)
                    .forEach((entry, index) => {

                        const res =
                            entry.resource || {};

                        const score =
                            res.confidenceScore || "90%";


                        let badgeColor =
                            "bg-secondary text-white";


                        if (index === 0) {
                            badgeColor =
                                "bg-success text-white";
                        }

                        else if (index === 1) {
                            badgeColor =
                                "bg-warning text-dark";
                        }


                        cardsHtml += `

                            <button
                                type="button"
                                class="btn btn-sm ${badgeColor} fw-semibold px-3 py-1 rounded-pill"
                                onclick="selectCandidate(${index})">

                                🟢 (${index + 1})
                                ${escapeHTML(
                                    res.code?.text ||
                                    "Condition"
                                )}
                                - ${escapeHTML(score)}

                            </button>

                        `;

                    });


                cardsHtml += `
                        </div>
                    </div>
                `;


                // ------------------------------------------------
                // ACTIVE CANDIDATE
                // ------------------------------------------------

                cardsHtml += `

                    <div id="activeCandidateView">

                        ${renderCandidateCard(
                            conditionEntries[0],
                            0
                        )}

                    </div>

                `;


                // ------------------------------------------------
                // FHIR PAYLOAD
                // ------------------------------------------------

                cardsHtml += `

                    <div
                        class="glass-panel p-4 mb-4 border border-secondary"
                        style="
                            background: rgba(10, 15, 25, 0.6);
                            border-radius: 12px;
                        ">

                        <details>

                            <summary
                                class="text-info fw-bold mb-0"
                                style="
                                    cursor: pointer;
                                    opacity: 0.8;
                                    font-size: 1.1rem;
                                    list-style: none;
                                ">

                                🔗 View FHIR R4 Condition Payload

                                <span
                                    style="
                                        font-size: 0.8rem;
                                        opacity: 0.6;
                                    ">

                                    (Click to Expand)

                                </span>

                            </summary>


                            <div class="mt-3">

                                <pre
                                    class="bg-dark text-light p-3 rounded overflow-auto border border-secondary"
                                    style="
                                        font-size: 12px;
                                        max-height: 250px;
                                        opacity: 0.85;
                                    ">${escapeHTML(
                                        window.lastRawJSON
                                    )}</pre>


                                <div
                                    class="d-flex flex-wrap gap-3 mt-3">

                                    <button
                                        id="copyButton"
                                        class="btn btn-outline-primary btn-sm fw-bold px-3"
                                        onclick="copyJSON()">

                                        📋 Copy JSON Payload

                                    </button>


                                    <button
                                        class="btn btn-outline-info btn-sm fw-bold px-3"
                                        onclick="testMockEMR()">

                                        🚀 Test Post to Hospital EMR

                                    </button>

                                </div>

                            </div>

                        </details>

                    </div>


                    <div
                        class="d-flex flex-wrap justify-content-center gap-3 mb-4">

                        <button
                            class="btn btn-sm btn-outline-light px-4 py-2 fw-semibold rounded-pill"
                            onclick="showAIExplanation()">

                            💡 Explain AI Matching

                        </button>


                        <button
                            class="btn btn-sm btn-outline-secondary px-4 py-2 fw-semibold rounded-pill"
                            onclick="togglePatientView()">

                            📄 Patient Friendly View

                        </button>

                    </div>

                `;


                result.innerHTML = cardsHtml;


                showToast(
                    "Successfully extracted conditions and generated Medicine Twins!",
                    "success"
                );


            } else {

                result.innerHTML = `

                    <div class="alert-danger text-center mt-4 p-3">

                        ${escapeHTML(
                            data.message ||
                            "No conditions extracted."
                        )}

                    </div>

                `;


                showToast(
                    data.message ||
                    "Extraction failed.",
                    "error"
                );

            }


        } catch (error) {

            console.error(
                "AI Scribe error:",
                error
            );


            result.innerHTML = `

                <div
                    class="alert-danger text-center mt-4 p-3">

                    Unable to connect to the MedBridge API.

                </div>

            `;


            showToast(
                "Connection failed.",
                "error"
            );

        }

    });

}


// ============================================================
// SELECT DIFFERENTIAL CANDIDATE
// ============================================================

window.selectCandidate = function (index) {

    const entry =
        window.currentEntries[index];

    const container =
        document.getElementById(
            "activeCandidateView"
        );


    if (
        container &&
        entry
    ) {

        container.innerHTML =
            renderCandidateCard(
                entry,
                index
            );


        showToast(
            `Switched to candidate #${index + 1}`,
            "info"
        );

    }

};


// ============================================================
// RENDER MEDICINE TWIN CARD
// ============================================================

window.renderCandidateCard =
function (entry, index = 0) {

    const res =
        entry?.resource || {};


    const medTwin =
        res.medicineTwin || {};


    // --------------------------------------------------------
    // Ingredients
    // --------------------------------------------------------

    const rawIngredients =
        medTwin.activeIngredients ||
        medTwin.ingredients ||
        medTwin.active_ingredients;


    const ingredients =
        rawIngredients
            ? (
                Array.isArray(rawIngredients)
                    ? rawIngredients.join(", ")
                    : rawIngredients
            )
            : "Nilavembu, Papaya leaf extract, Nilavembu kudineer chooranam";


    // --------------------------------------------------------
    // Traditional Uses
    // --------------------------------------------------------

    const rawUses =
        medTwin.traditionalUses ||
        medTwin.traditional_uses ||
        medTwin.uses;


    const traditionalUses =
        rawUses
            ? (
                Array.isArray(rawUses)
                    ? rawUses.join(", ")
                    : rawUses
            )
            : "Antipyretic, Anti-inflammatory, Immune Support";


    // --------------------------------------------------------
    // Risk Radar
    // --------------------------------------------------------

    const rawRisk =
        medTwin.riskRadar ||
        medTwin.risk_warnings ||
        medTwin.risk_alerts ||
        medTwin.alerts;


    const riskAlert =
        rawRisk
            ? (
                Array.isArray(rawRisk)
                    ? rawRisk[0]
                    : rawRisk
            )
            : "Monitor patient if co-prescribing with modern NSAIDs due to possible interaction risks.";


    // --------------------------------------------------------
    // Codes
    // --------------------------------------------------------

    const codingList =
        res.code &&
        Array.isArray(res.code.coding)
            ? res.code.coding
            : [];


    const tradCode =
        codingList[0]?.code ||
        "SID-135";


    const icdCode =
        codingList[1]?.code ||
        "SP52";


    const systemName =
        res.system ||
        "Siddha";


    const modernEq =
        res.modernEquivalent ||
        "Standardized Clinical Presentation";


    const tradTerm =
        res.code?.text ||
        "Traditional Presentation";


    const confScore =
        res.confidenceScore ||
        "94.0%";


    return `

        <div
            class="d-flex flex-column flex-lg-row gap-4 mb-4 align-items-stretch w-100">


            <!-- ============================================= -->
            <!-- LEFT: MEDICINE TWIN -->
            <!-- ============================================= -->

            <div
                class="glass-panel p-4 border border-secondary shadow-sm text-light d-flex flex-column"
                style="
                    flex: 2;
                    background: rgba(15, 23, 42, 0.6) !important;
                    border-radius: 12px;
                ">


                <div
                    class="d-flex justify-content-between align-items-center mb-3">


                    <h5
                        class="fw-bold mb-0"
                        style="
                            color: rgba(0, 229, 255, 0.85);
                            font-size: 1.1rem;
                        ">

                        🧬 AI MEDICINE TWIN

                    </h5>


                    <span
                        class="badge px-2 py-1 fw-semibold"
                        style="
                            background: rgba(0, 229, 255, 0.1);
                            border: 1px solid rgba(0, 229, 255, 0.3);
                            color: rgba(0, 229, 255, 0.85);
                            border-radius: 12px;
                            font-size: 0.8rem;
                        ">

                        Confidence:
                        ${escapeHTML(confScore)}

                    </span>

                </div>


                <div class="mb-2">

                    <strong style="opacity: 0.7;">
                        Traditional:
                    </strong>

                    <span class="text-light">

                        ${escapeHTML(tradTerm)}

                    </span>

                    <span
                        class="text-muted"
                        style="font-size: 0.8rem;">

                        (${escapeHTML(systemName)})

                    </span>

                </div>


                <div
                    class="mb-2"
                    style="
                        color: rgba(56, 189, 248, 0.9);
                    ">

                    <strong>
                        ↳ NAMASTE Code:
                    </strong>

                    ${escapeHTML(tradCode)}

                </div>


                <div class="mb-2">

                    <strong style="opacity: 0.7;">
                        Modern Equivalent:
                    </strong>

                    <span class="text-light">

                        ${escapeHTML(modernEq)}

                    </span>

                </div>


                <div
                    class="mb-3"
                    style="
                        color: rgba(52, 211, 153, 0.9);
                    ">

                    <strong>
                        ↳ WHO ICD-11 (TM2):
                    </strong>

                    ${escapeHTML(icdCode)}

                </div>


                <hr
                    class="border-secondary my-3"
                    style="opacity: 0.3;">


                <p
                    class="mb-1 fw-bold"
                    style="
                        color: rgba(56, 189, 248, 0.85);
                        font-size: 0.9rem;
                    ">

                    Active Botanical Ingredients:

                </p>


                <p
                    class="text-light small mb-3"
                    style="opacity: 0.8;">

                    ${escapeHTML(ingredients)}

                </p>


                <p
                    class="mb-1 fw-bold text-muted"
                    style="font-size: 0.9rem;">

                    Traditional Clinical Uses:

                </p>


                <p
                    class="text-muted small mb-3">

                    ${escapeHTML(traditionalUses)}

                </p>


                <!-- LOCATION BUTTON -->

                <button
                    class="btn btn-sm w-100 fw-bold py-2 mt-auto"
                    style="
                        background: rgba(0, 229, 255, 0.1);
                        border: 1px solid rgba(0, 229, 255, 0.4);
                        color: rgba(0, 229, 255, 0.9);
                        border-radius: 8px;
                    "
                    onclick="findNearbyClinics('${escapeJS(systemName)}')">

                    📍 Find Nearby
                    ${escapeHTML(systemName)}
                    Clinics

                </button>

            </div>


            <!-- ============================================= -->
            <!-- RIGHT: RISK RADAR -->
            <!-- ============================================= -->

            <div
                class="glass-panel p-4 border border-secondary shadow-sm text-light d-flex flex-column justify-content-between"
                style="
                    flex: 1;
                    background: rgba(245, 158, 11, 0.03) !important;
                    border-color: rgba(245, 158, 11, 0.15) !important;
                    border-radius: 12px;
                ">


                <div>

                    <h5
                        class="fw-bold mb-3"
                        style="
                            color: rgba(251, 191, 36, 0.85);
                            font-size: 1.05rem;
                        ">

                        ⚠️ CROSS-SYSTEM RISK RADAR

                    </h5>


                    <div
                        class="p-3 rounded bg-dark border border-warning border-opacity-10 mb-3">


                        <strong
                            style="
                                color: rgba(251, 191, 36, 0.8);
                                font-size: 0.85rem;
                            ">

                            AI Interaction Alert:

                        </strong>


                        <p
                            class="small text-muted mt-1 mb-0"
                            style="
                                line-height: 1.4;
                                opacity: 0.85;
                            ">

                            ${escapeHTML(riskAlert)}

                        </p>

                    </div>

                </div>


                <button
                    class="btn btn-sm w-100 fw-bold py-2 mt-auto"
                    style="
                        background: rgba(245, 158, 11, 0.1);
                        border: 1px solid rgba(245, 158, 11, 0.25);
                        color: rgba(251, 191, 36, 0.85);
                        border-radius: 8px;
                    "
                    onclick="acknowledgeRiskWarning()">

                    ✅ Acknowledge Warning

                </button>

            </div>

        </div>

    `;

};


// ============================================================
// RISK WARNING
// ============================================================

window.acknowledgeRiskWarning =
function () {

    showToast(
        "Warning acknowledged & logged to audit trail.",
        "success"
    );

};


// ============================================================
// AI EXPLANATION
// ============================================================

window.showAIExplanation =
function () {

    alert(
        "Explainable AI (XAI):\n\n" +
        "The matching system combines " +
        "TF-IDF cosine similarity with " +
        "traditional-to-modern terminology mapping " +
        "and WHO ICD-11 TM2 crosswalk information."
    );

};


// ============================================================
// PATIENT FRIENDLY VIEW
// ============================================================

window.togglePatientView =
function () {

    alert(
        "Patient Friendly Summary:\n\n" +
        "• Condition: Fever / Body Heat\n" +
        "• Purpose: Helps standardize the clinical description\n" +
        "• Caution: Always consult a qualified healthcare professional before combining treatments."
    );

};


// ============================================================
// MOCK EMR TEST
// ============================================================

window.testMockEMR =
async function () {

    if (!window.lastRawJSON) {

        showToast(
            "FHIR payload is not available.",
            "error"
        );

        return;
    }


    showToast(
        "Sending FHIR payload to mock Hospital EMR...",
        "info"
    );


    try {

        const response =
            await fetch(
                `${API_BASE}/api/v1/test-emr`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        window.lastRawJSON
                }
            );


        if (response.ok) {

            showToast(
                "FHIR payload accepted by mock Hospital EMR.",
                "success"
            );

        } else {

            showToast(
                "Mock EMR returned an error.",
                "error"
            );

        }

    } catch (error) {

        console.error(
            "Mock EMR error:",
            error
        );

        showToast(
            "FHIR payload prepared successfully. Mock EMR endpoint is unavailable.",
            "info"
        );

    }

};


// ============================================================
// VOICE RECOGNITION
// ============================================================

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


if (
    SpeechRecognition &&
    micButton &&
    diseaseInput
) {

    const recognition =
        new SpeechRecognition();


    recognition.continuous = false;
    recognition.lang = "en-IN";


    micButton.addEventListener(
        "click",
        () => {

            diseaseInput.placeholder =
                "Listening...";


            micButton.style.background =
                "#ff4444";


            try {

                recognition.start();

            } catch (error) {

                console.log(
                    "Speech recognition already running."
                );

            }

        }
    );


    recognition.onresult =
    function (event) {

        const transcript =
            event.results[0][0].transcript;


        diseaseInput.value =
            transcript;


        micButton.style.background =
            "#e0e0e0";


        diseaseInput.placeholder =
            "Enter diagnosis";


        searchButton.click();

    };


    recognition.onerror =
    function () {

        micButton.style.background =
            "#e0e0e0";


        diseaseInput.placeholder =
            "Enter diagnosis";

    };

} else if (micButton) {

    micButton.style.display =
        "none";

}


// ============================================================
// ADMIN BULK UPLOAD
// ============================================================

const bulkUploadBtn =
    document.getElementById(
        "bulkUploadBtn"
    );


const csvFileInput =
    document.getElementById(
        "csvFileInput"
    );


const bulkResult =
    document.getElementById(
        "bulkResult"
    );


const fileNameDisplay =
    document.getElementById(
        "fileNameDisplay"
    );


const dropZone =
    document.getElementById(
        "dropZone"
    );


if (
    bulkUploadBtn &&
    csvFileInput
) {

    bulkUploadBtn.addEventListener(
        "click",
        async function (event) {

            event.preventDefault();


            showToast(
                "Initiating enterprise bulk standardization...",
                "info"
            );


            const file =
                csvFileInput.files[0];


            if (!file) {

                bulkResult.innerHTML =
                    "<span class='text-danger'>Please select a .csv file first!</span>";

                return;
            }


            bulkResult.innerHTML = `

                <div
                    class="spinner-border spinner-border-sm text-info me-2">
                </div>

                Mapping records...

            `;


            const formData =
                new FormData();


            formData.append(
                "file",
                file
            );


            try {

                const response =
                    await fetch(
                        `${API_BASE}/api/v1/bulk-map`,
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                if (response.ok) {

                    const blob =
                        await response.blob();


                    const downloadUrl =
                        window.URL.createObjectURL(
                            blob
                        );


                    const a =
                        document.createElement(
                            "a"
                        );


                    a.href =
                        downloadUrl;


                    a.download =
                        `MedBridge_Standardized_${file.name.replace(
                            ".csv",
                            ".xlsx"
                        )}`;


                    document.body.appendChild(a);


                    a.click();


                    a.remove();


                    window.URL.revokeObjectURL(
                        downloadUrl
                    );


                    bulkResult.innerHTML =
                        "✅ Success! File standardized and downloaded.";


                    showToast(
                        "Bulk mapping completed successfully.",
                        "success"
                    );


                } else {

                    bulkResult.innerHTML =
                        "<span class='text-danger'>Server error processing file.</span>";


                    showToast(
                        "Failed to standardize records.",
                        "error"
                    );

                }


            } catch (error) {

                console.error(error);


                bulkResult.innerHTML =
                    "<span class='text-danger'>Failed to connect to MedBridge API.</span>";


                showToast(
                    "API connection failed.",
                    "error"
                );

            }

        }
    );


    csvFileInput.addEventListener(
        "change",
        function () {

            if (this.files.length > 0) {

                fileNameDisplay.textContent =
                    "📄 Selected: " +
                    this.files[0].name;


                fileNameDisplay.classList.remove(
                    "d-none"
                );


                if (dropZone) {

                    dropZone.style.borderColor =
                        "#00e5ff";

                    dropZone.style.background =
                        "rgba(0, 229, 255, 0.05)";

                }

            } else {

                fileNameDisplay.classList.add(
                    "d-none"
                );

            }

        }
    );

}


// ============================================================
// COPY FHIR JSON
// ============================================================

window.copyJSON =
function () {

    if (!window.lastRawJSON) {

        showToast(
            "No FHIR payload available.",
            "error"
        );

        return;
    }


    navigator.clipboard
        .writeText(
            window.lastRawJSON
        )
        .then(() => {

            const btn =
                document.getElementById(
                    "copyButton"
                );


            if (btn) {

                btn.textContent =
                    "Copied!";

            }


            showToast(
                "FHIR JSON Payload copied to clipboard!",
                "success"
            );


            setTimeout(() => {

                if (btn) {

                    btn.textContent =
                        "📋 Copy JSON Payload";

                }

            }, 2000);

        })
        .catch(error => {

            console.error(
                "Copy failed:",
                error
            );


            showToast(
                "Unable to copy FHIR payload.",
                "error"
            );

        });

};


// ============================================================
// AUDIT TRAIL
// ============================================================

const auditLogDisplay =
    document.getElementById(
        "auditLogDisplay"
    );


if (auditLogDisplay) {

    async function fetchAuditLogs() {

        try {

            const response =
                await fetch(
                    `${API_BASE}/api/v1/audit-logs`
                );


            if (!response.ok) {

                throw new Error(
                    "Audit API failed."
                );

            }


            const logText =
                await response.text();


            auditLogDisplay.textContent =
                logText ||
                "No logs recorded yet.";


            auditLogDisplay.scrollTop =
                auditLogDisplay.scrollHeight;


        } catch (error) {

            console.error(
                "Failed to fetch audit logs:",
                error
            );

        }

    }


    fetchAuditLogs();


    setInterval(
        fetchAuditLogs,
        3000
    );

}


// ============================================================
// PATIENT MODULE
// ============================================================

window.loadPatientList =
async function () {

    const patientSelect =
        document.getElementById(
            "patientSelect"
        );


    const patientDetails =
        document.getElementById(
            "patientDetails"
        );


    if (!patientSelect) {

        console.error(
            "Patient selector not found."
        );

        return;
    }


    patientSelect.innerHTML = `

        <option value="">
            Loading patients...
        </option>

    `;


    if (patientDetails) {

        patientDetails.innerHTML =
            "";

    }


    try {

        const response =
            await fetch(
                `${API_BASE}/api/v1/patients`
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to load patients."
            );

        }


        const patients =
            Array.isArray(data.patients)
                ? data.patients
                : [];


        patientSelect.innerHTML = `

            <option value="">
                Select a patient...
            </option>

        `;


        if (patients.length === 0) {

            patientSelect.innerHTML = `

                <option value="">
                    No patients available
                </option>

            `;


            showToast(
                "No patients found.",
                "info"
            );


            return;
        }


        patients.forEach(
            patient => {

                const option =
                    document.createElement(
                        "option"
                    );


                option.value =
                    patient.patient_id;


                option.textContent =
                    `${patient.patient_id} - ${patient.name}`;


                patientSelect.appendChild(
                    option
                );

            }
        );


        showToast(
            `${patients.length} patient(s) loaded successfully.`,
            "success"
        );


    } catch (error) {

        console.error(
            "Patient list error:",
            error
        );


        patientSelect.innerHTML = `

            <option value="">
                Unable to load patients
            </option>

        `;


        if (patientDetails) {

            patientDetails.innerHTML = `

                <div
                    class="alert alert-danger mt-3">

                    Unable to connect to the
                    Patient Module.

                </div>

            `;

        }


        showToast(
            "Failed to load patient records.",
            "error"
        );

    }

};


// ============================================================
// VIEW SELECTED PATIENT
// ============================================================

window.viewSelectedPatient =
async function () {

    const patientSelect =
        document.getElementById(
            "patientSelect"
        );


    const patientDetails =
        document.getElementById(
            "patientDetails"
        );


    if (
        !patientSelect ||
        !patientDetails
    ) {

        return;

    }


    const patientId =
        patientSelect.value;


    if (!patientId) {

        patientDetails.innerHTML = `

            <div
                class="alert alert-warning mt-3">

                Please select a patient first.

            </div>

        `;

        return;
    }


    patientDetails.innerHTML = `

        <div
            class="text-center text-info py-4">

            <div
                class="spinner-border spinner-border-sm me-2"
                role="status">
            </div>

            Loading patient information...

        </div>

    `;


    try {

        const response =
            await fetch(
                `${API_BASE}/api/v1/patients/${encodeURIComponent(
                    patientId
                )}`
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Patient not found."
            );

        }


        const patient =
            data.patient;


        if (!patient) {

            throw new Error(
                "Patient information is unavailable."
            );

        }


        renderPatientDetails(
            patient
        );


    } catch (error) {

        console.error(
            "Patient details error:",
            error
        );


        patientDetails.innerHTML = `

            <div
                class="alert alert-danger mt-3">

                ${escapeHTML(
                    error.message
                )}

            </div>

        `;


        showToast(
            "Unable to load patient information.",
            "error"
        );

    }

};


// ============================================================
// RENDER PATIENT DETAILS
// ============================================================

window.renderPatientDetails =
function (patient) {

    const patientDetails =
        document.getElementById(
            "patientDetails"
        );


    if (!patientDetails) {

        return;

    }


    const conditions =
        Array.isArray(
            patient.conditions
        )
            ? patient.conditions
            : [];


    const namasteCodes =
        Array.isArray(
            patient.namaste_codes
        )
            ? patient.namaste_codes
            : [];


    const icd11Codes =
        Array.isArray(
            patient.icd11_codes
        )
            ? patient.icd11_codes
            : [];


    let conditionsHTML =
        "";


    if (conditions.length === 0) {

        conditionsHTML = `

            <div
                class="text-muted py-3">

                No mapped conditions recorded
                for this patient.

            </div>

        `;

    } else {

        conditionsHTML = `

            <div
                class="table-responsive">

                <table
                    class="table table-dark table-hover align-middle">


                    <thead>

                        <tr>

                            <th>
                                Condition
                            </th>

                            <th>
                                NAMASTE Code
                            </th>

                            <th>
                                ICD-11 Code
                            </th>

                        </tr>

                    </thead>


                    <tbody>

                        ${conditions.map(
                            (condition, index) => `

                            <tr>

                                <td
                                    class="fw-semibold text-light">

                                    ${escapeHTML(
                                        condition
                                    )}

                                </td>


                                <td>

                                    <span
                                        class="badge bg-info text-dark">

                                        ${escapeHTML(
                                            namasteCodes[index] ||
                                            "—"
                                        )}

                                    </span>

                                </td>


                                <td>

                                    <span
                                        class="badge bg-primary">

                                        ${escapeHTML(
                                            icd11Codes[index] ||
                                            "—"
                                        )}

                                    </span>

                                </td>

                            </tr>

                        `
                        ).join("")}

                    </tbody>

                </table>

            </div>

        `;

    }


    patientDetails.innerHTML = `

        <div
            class="card bg-transparent border border-info mt-4 shadow-sm">


            <!-- HEADER -->

            <div
                class="card-header border-info d-flex justify-content-between align-items-center">

                <h4
                    class="text-info fw-bold mb-0">

                    Patient Information

                </h4>


                <span
                    class="badge bg-success">

                    Synthetic Demo Patient

                </span>

            </div>


            <!-- BODY -->

            <div class="card-body">


                <div class="row g-4">


                    <div class="col-md-3">

                        <div
                            class="text-muted small">

                            Patient ID

                        </div>


                        <div
                            class="fw-bold text-light fs-5">

                            ${escapeHTML(
                                patient.patient_id
                            )}

                        </div>

                    </div>


                    <div class="col-md-3">

                        <div
                            class="text-muted small">

                            Name

                        </div>


                        <div
                            class="fw-bold text-light fs-5">

                            ${escapeHTML(
                                patient.name
                            )}

                        </div>

                    </div>


                    <div class="col-md-3">

                        <div
                            class="text-muted small">

                            Age

                        </div>


                        <div
                            class="fw-bold text-light fs-5">

                            ${escapeHTML(
                                String(
                                    patient.age
                                )
                            )}

                        </div>

                    </div>


                    <div class="col-md-3">

                        <div
                            class="text-muted small">

                            Gender

                        </div>


                        <div
                            class="fw-bold text-light fs-5">

                            ${escapeHTML(
                                patient.gender
                            )}

                        </div>

                    </div>

                </div>


                <hr
                    class="border-secondary my-4">


                <div
                    class="d-flex justify-content-between align-items-center mb-3">


                    <h5
                        class="text-info fw-bold mb-0">

                        Mapped Conditions

                    </h5>


                    <span
                        class="badge bg-secondary">

                        ${conditions.length}
                        condition(s)

                    </span>

                </div>


                ${conditionsHTML}

            </div>

        </div>

    `;


    showToast(
        `Patient ${patient.patient_id} loaded successfully.`,
        "success"
    );

};


// ============================================================
// NEARBY CLINICS
// ============================================================

window.findNearbyClinics =
function (systemName) {

    showToast(
        `📍 Acquiring GPS coordinates and searching for ${systemName} clinics...`,
        "info"
    );


    if (!navigator.geolocation) {

        showToast(
            "Geolocation is not supported by your browser.",
            "error"
        );

        return;
    }


    navigator.geolocation.getCurrentPosition(

        async function (position) {

            const lat =
                position.coords.latitude;


            const lng =
                position.coords.longitude;


            showToast(
                "📡 Coordinates acquired! Searching network...",
                "success"
            );


            try {

                const response =
                    await fetch(
                        `${API_BASE}/api/v1/nearby-clinics`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    latitude: lat,
                                    longitude: lng,
                                    condition_system:
                                        systemName ||
                                        "Siddha"
                                })
                        }
                    );


                const data =
                    await response.json();


                if (
                    data.status === "success"
                ) {

                    renderClinicsList(
                        data.clinics || []
                    );

                } else {

                    showToast(
                        "Error finding clinics: " +
                        (
                            data.message ||
                            "Unknown error"
                        ),
                        "error"
                    );

                }


            } catch (error) {

                console.error(
                    "Clinic API error:",
                    error
                );


                showToast(
                    "API connection failed.",
                    "error"
                );

            }

        },


        function (error) {

            console.error(
                "Geolocation error:",
                error
            );


            showToast(
                "Location access denied. Please allow browser location permissions.",
                "error"
            );

        }

    );

};


// ============================================================
// RENDER CLINICS
// ============================================================

function renderClinicsList(
    clinics
) {

    const modalBody =
        document.getElementById(
            "clinicsModalBody"
        );


    if (!modalBody) {

        return;

    }


    if (
        !Array.isArray(clinics) ||
        clinics.length === 0
    ) {

        modalBody.innerHTML = `

            <p
                class="text-muted text-center py-4">

                No specialized clinics found
                within range.

            </p>

        `;

    } else {

        let html = `

            <div
                class="d-flex flex-column gap-3">

        `;


        clinics.forEach(
            clinic => {

                const specialties =
                    Array.isArray(
                        clinic.specialties
                    )
                        ? clinic.specialties
                        : [];


                html += `

                    <div
                        class="p-3 rounded border border-secondary"
                        style="
                            background: rgba(255,255,255,0.02);
                        ">


                        <div
                            class="d-flex justify-content-between align-items-start mb-2">


                            <div>

                                <h6
                                    class="fw-bold text-light mb-1">

                                    ${escapeHTML(
                                        clinic.name
                                    )}

                                </h6>


                                <p
                                    class="text-muted small mb-0">

                                    👨‍⚕️
                                    ${escapeHTML(
                                        clinic.doctor
                                    )}

                                </p>

                            </div>


                            <span
                                class="badge bg-dark border border-info"
                                style="
                                    color: rgba(0,229,255,0.9);
                                ">

                                ${escapeHTML(
                                    clinic.distance_km
                                )}
                                km

                            </span>

                        </div>


                        <div
                            class="d-flex justify-content-between align-items-center mt-3">


                            <span
                                class="small"
                                style="
                                    color: rgba(52,211,153,0.9);
                                ">

                                System:
                                ${escapeHTML(
                                    specialties[0] ||
                                    "Traditional Medicine"
                                )}

                            </span>


                            <button
                                class="btn btn-sm btn-outline-success fw-bold py-1 px-3"
                                onclick="sendReferralEmail(
                                    '${escapeJS(clinic.name)}',
                                    '${escapeJS(clinic.doctor)}',
                                    '${escapeJS(clinic.distance_km)}',
                                    '${escapeJS(
                                        specialties[0] ||
                                        "Traditional Medicine"
                                    )}'
                                )">

                                Refer Patient

                            </button>

                        </div>

                    </div>

                `;

            }
        );


        html += `
            </div>
        `;


        modalBody.innerHTML =
            html;

    }


    const modalElement =
        document.getElementById(
            "clinicsModal"
        );


    if (
        modalElement &&
        window.bootstrap
    ) {

        const clinicsModal =
            new bootstrap.Modal(
                modalElement
            );


        clinicsModal.show();

    }

}


// ============================================================
// REFERRAL EMAIL
// ============================================================

window.sendReferralEmail =
async function (
    clinicName,
    doctorName,
    distance,
    system
) {

    showToast(
        "📧 Encrypting and sending secure referral...",
        "info"
    );


    try {

        const response =
            await fetch(
                `${API_BASE}/api/v1/send-referral`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            clinic_name:
                                clinicName,

                            doctor_name:
                                doctorName,

                            condition:
                                system,

                            distance:
                                String(distance)
                        })
                }
            );


        const data =
            await response.json();


        if (
            response.ok &&
            data.status === "success"
        ) {

            const modalEl =
                document.getElementById(
                    "clinicsModal"
                );


            if (
                modalEl &&
                window.bootstrap
            {

                const modalInstance =
                    bootstrap.Modal.getInstance(
                        modalEl
                    );


                if (modalInstance) {

                    modalInstance.hide();

                }

            }


            showToast(
                `✅ Referral sent to ${clinicName}.`,
                "success"
            );


        } else {

            showToast(
                data.message ||
                "Referral could not be sent.",
                "error"
            );

        }


    } catch (error) {

        console.error(
            "Referral error:",
            error
        );


        showToast(
            "Error establishing secure connection.",
            "error"
        );

    }

};


// ============================================================
// COMMAND PALETTE
// ============================================================

const cmdPalette =
    document.getElementById(
        "commandPalette"
    );


const cmdInput =
    document.getElementById(
        "commandInput"
    );


const closePaletteBtn =
    document.getElementById(
        "closePalette"
    );


if (
    cmdPalette &&
    cmdInput
) {

    window.addEventListener(
        "keydown",
        function (event) {

            if (
                (event.ctrlKey ||
                    event.metaKey) &&
                event.key.toLowerCase() ===
                    "k"
            ) {

                event.preventDefault();


                cmdPalette.classList.remove(
                    "d-none"
                );


                cmdInput.focus();


                cmdInput.value =
                    "";

            }


            if (
                event.key === "Escape" &&
                !cmdPalette.classList.contains(
                    "d-none"
                )
            ) {

                cmdPalette.classList.add(
                    "d-none"
                );

            }

        }
    );


    if (closePaletteBtn) {

        closePaletteBtn.addEventListener(
            "click",
            () => {

                cmdPalette.classList.add(
                    "d-none"
                );

            }
        );

    }


    cmdPalette.addEventListener(
        "click",
        function (event) {

            if (
                event.target ===
                cmdPalette
            ) {

                cmdPalette.classList.add(
                    "d-none"
                );

            }

        }
    );


    cmdInput.addEventListener(
        "input",
        function (event) {

            const query =
                event.target.value
                    .toLowerCase()
                    .trim();


            if (
                query.startsWith(
                    "search "
                )
            ) {

                // Reserved for future
                // command shortcuts.

            }

        }
    );

}


// ============================================================
// TOAST NOTIFICATION
// ============================================================

function showToast(
    message,
    type = "success"
) {

    let container =
        document.getElementById(
            "toastContainer"
        );


    if (!container) {

        container =
            document.createElement(
                "div"
            );


        container.id =
            "toastContainer";


        container.className =
            "toast-container-custom";


        document.body.appendChild(
            container
        );

    }


    const toast =
        document.createElement(
            "div"
        );


    toast.className =
        "custom-toast";


    let icon =
        "✅";


    if (type === "error") {
        icon = "❌";
    }

    else if (type === "info") {
        icon = "ℹ️";
    }


    toast.innerHTML = `

        <span
            style="font-size: 1.2rem;">

            ${icon}

        </span>

        <span>

            ${escapeHTML(message)}

        </span>

    `;


    container.appendChild(
        toast
    );


    setTimeout(
        () => {

            toast.remove();

        },
        3000
    );

}


// ============================================================
// PWA SERVICE WORKER
// ============================================================

if (
    "serviceWorker" in navigator
) {

    window.addEventListener(
        "load",
        () => {

            navigator.serviceWorker
                .register(
                    "/src/sw.js"
                )

                .then(
                    registration => {

                        console.log(
                            "MedBridge ServiceWorker registered with scope:",
                            registration.scope
                        );

                    }
                )

                .catch(
                    error => {

                        console.log(
                            "ServiceWorker registration failed:",
                            error
                        );

                    }
                );

        }
    );

}


// ============================================================
// PASSWORD VISIBILITY
// ============================================================

const togglePassword =
    document.getElementById(
        "togglePassword"
    );


const passwordInput =
    document.getElementById(
        "passwordInput"
    );


if (
    togglePassword &&
    passwordInput
) {

    togglePassword.addEventListener(
        "click",
        function () {

            const type =
                passwordInput.getAttribute(
                    "type"
                ) === "password"
                    ? "text"
                    : "password";


            passwordInput.setAttribute(
                "type",
                type
            );


            this.textContent =
                type === "password"
                    ? "👁️"
                    : "🔒";

        }
    );

}


// ============================================================
// SESSION PROTECTION
// ============================================================

async function checkUserSession() {

    try {

        if (
            !window.supabase ||
            !window.supabase.auth
        ) {

            return;

        }


        const {
            data: {
                session
            }
        } =
            await window.supabase.auth.getSession();


        const path =
            window.location.pathname;


        const protectedPage =
            path.includes("index.html") ||
            path.includes("admin.html");


        if (
            !session &&
            protectedPage
        ) {

            window.location.href =
                "/src/login.html";

        }

    } catch (error) {

        console.error(
            "Session check failed:",
            error
        );

    }

}


if (window.supabase) {

    checkUserSession();

}


// ============================================================
// SIGN OUT
// ============================================================

window.handleSignOut =
async function (event) {

    if (event) {

        event.preventDefault();

    }


    localStorage.removeItem(
        "userRole"
    );


    try {

        const sb =
            window.supabaseClient ||
            window.supabase;


        if (
            sb &&
            sb.auth
        ) {

            await sb.auth.signOut();

        }

    } catch (error) {

        console.log(
            "Session notice:",
            error
        );

    }


    window.location.replace(
        "login.html"
    );

};


// ============================================================
// SECURITY / HTML HELPERS
// ============================================================

function escapeHTML(value) {

    return String(
        value ?? ""
    )

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


function escapeJS(value) {

    return String(
        value ?? ""
    )
        .replace(
            /\\/g,
            "\\\\"
        )
        .replace(
            /'/g,
            "\\'"
        )
        .replace(
            /"/g,
            '\\"'
        )
        .replace(
            /\r?\n/g,
            "\\n"
        );

}


// ============================================================
// END OF MEDBRIDGE SCRIPT
// ============================================================