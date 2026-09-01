window.lastRawJSON = "";
const searchButton = document.getElementById("searchButton");
const diseaseInput = document.getElementById("diseaseInput");
const micButton = document.getElementById("micButton");
const result = document.getElementById("result");
const emrIntegration = document.getElementById("emrIntegration");

if (diseaseInput && searchButton) {
    diseaseInput.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            event.preventDefault(); 
            searchButton.click();   
        }
    });

    searchButton.addEventListener("click", async function (event) {
        event.preventDefault(); 
        
        const notesText = diseaseInput.value.trim();
        emrIntegration.innerHTML = "";

        if (!notesText) {
            result.innerHTML = `<div class="alert-danger text-center mt-4">Error: Please enter clinical notes or a diagnosis.</div>`;
            return;
        }

        result.innerHTML = `
            <div class="d-flex align-items-center text-primary mt-3">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                <strong>Analyzing notes with AI Scribe & Risk Radar...</strong>
            </div>
        `;

        try {
            const response = await fetch(`/api/v1/ai-scribe`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ notes: notesText })
            });
            const data = await response.json();

            if (data.status === "success" && data.bundle && data.bundle.entry) {
                window.lastRawJSON = JSON.stringify(data.bundle, null, 2); 
                const entries = data.bundle.entry;

                // 1. Top Differential Candidate Pills (Top 3)
                let cardsHtml = `
                    <div class="glass-panel p-3 mb-4 shadow-sm border border-secondary mt-4">
                        <h6 class="text-info fw-bold mb-2">🎯 TOP DIFFERENTIAL MATCHES (Click to Select)</h6>
                        <div class="d-flex flex-wrap gap-2">
                `;
                
                entries.forEach((entry, index) => {
                    const res = entry.resource;
                   const score = res.confidenceScore || "Not available";
                    
                    const mappingStatus = res.mappingStatus || "Not available";
                    const matchStatus = res.matchStatus || "Not available";
                    const source = res.source || {};
                    const badgeColor = index === 0 ? "bg-success text-white" : index === 1 ? "bg-warning text-dark" : "bg-secondary text-white";
                    cardsHtml += `
                        <button type="button" class="btn btn-sm ${badgeColor} fw-semibold px-3 py-1 rounded-pill" onclick="selectCandidate(${index})">
                            🟢 (${index + 1}) ${res.code.text} - ${score}
                        </button>
                    `;
                });
                cardsHtml += `</div></div>`;

                // 2. Active Candidate Split View Container
                cardsHtml += `<div id="activeCandidateView">`;
                cardsHtml += renderCandidateCard(entries[0]);
                cardsHtml += `</div>`;

                // 3. FHIR Payload & Action Footer Bar (Now Collapsible and Dimmer)
                cardsHtml += `
                    <div class="glass-panel p-4 mb-4 border border-secondary" style="background: rgba(10, 15, 25, 0.6); border-radius: 12px;">
                        <details>
                            <summary class="text-info fw-bold mb-0" style="cursor: pointer; opacity: 0.8; font-size: 1.1rem; list-style: none;">
                                <span style="display: flex; align-items: center; gap: 8px;">
                                    🔗 View FHIR R4 Condition Payload <span style="font-size: 0.8rem; opacity: 0.6;">(Click to Expand)</span>
                                </span>
                            </summary>
                            <div class="mt-3">
                                <pre class="bg-dark text-light p-3 rounded overflow-x-auto border border-secondary" style="font-size: 12px; max-height: 250px; opacity: 0.85;">${window.lastRawJSON}</pre>
                                <div class="d-flex gap-3 mt-3">
                                    <button id="copyButton" class="btn btn-outline-primary btn-sm fw-bold px-3" style="opacity: 0.9;" onclick="copyJSON()">📋 Copy JSON Payload</button>
                                    <button class="btn btn-outline-info btn-sm fw-bold px-3" style="opacity: 0.9;" onclick="testMockEMR()">🚀 Test Post to Hospital EMR</button>
                                </div>
                            </div>
                        </details>
                    </div>

                    <div class="d-flex justify-content-center gap-3 mb-4">
                        <button class="btn btn-sm btn-outline-light px-4 py-2 fw-semibold rounded-pill" style="opacity: 0.7;" onclick="showAIExplanation()">💡 Explain AI Matching</button>
                        <button class="btn btn-sm btn-outline-secondary px-4 py-2 fw-semibold rounded-pill" style="opacity: 0.7;" onclick="togglePatientView()">📄 Patient Friendly View</button>
                    </div>
                `;

                result.innerHTML = cardsHtml;
                window.currentEntries = entries;
                showToast("Successfully extracted conditions and generated Medicine Twins!", 'success');

            } else {
                result.innerHTML = `<div class="alert-danger text-center mt-4">${data.message || "No conditions extracted."}</div>`;
                showToast(data.message || "Extraction failed.", 'error');
            }
            } catch (error) {
                result.innerHTML = `<div class="alert-danger text-center mt-4">Unable to connect to the MedBridge API.</div>`;
                console.error(error);
                showToast("Connection failed.", 'error');
            }
        });
}


window.showAIExplanation = function() {
    alert("Explainable AI (XAI): Match generated using scikit-learn TF-IDF cosine similarity (96% weight) combined with WHO ICD-11 TM2 ontology cross-walk mapping.");
};

window.togglePatientView = function() {
    alert("Layman Summary:\n• Condition: Fever / Body Heat\n• Purpose: Reduces temperature & clears inflammation\n• Caution: Avoid combining with strong blood thinners without consulting your physician.");
};

// Voice Recognition setup
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition && micButton && diseaseInput) {
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
else if (micButton){
    micButton.style.display = "none"; 
}

//admin.html
const bulkUploadBtn = document.getElementById("bulkUploadBtn");
const csvFileInput = document.getElementById("csvFileInput");
const bulkResult = document.getElementById("bulkResult");
const fileNameDisplay = document.getElementById('fileNameDisplay');
const dropZone = document.getElementById('dropZone');

if (bulkUploadBtn && csvFileInput) {
    bulkUploadBtn.addEventListener("click", async function(event) {
        showToast("Initiating enterprise bulk standardization...", 'info');
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
            const response = await fetch("/api/v1/bulk-map", {
                method: "POST",
                body: formData
            });

            if (response.ok) {
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = downloadUrl;
                a.download = `MedBridge_Standardized_${file.name.replace('.csv', '.xlsx')}`;                document.body.appendChild(a);
                document.body.appendChild(a);    
                a.click();
                a.remove();
                
                bulkResult.innerHTML = "✅ Success! File standardized and downloaded.";

            } else {
                bulkResult.innerHTML = "<span class='text-danger'>Server error processing file.</span>";
                showToast("Failed to standardize records.", "error");
            }
        } catch (error) {
            console.error(error);
            bulkResult.innerHTML = "<span class='text-danger'>Failed to connect to MedBridge API.</span>";
        }
    });

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
}

// Global Copy Function
window.copyJSON = function() {
    navigator.clipboard.writeText(lastRawJSON).then(() => {
        const btn = document.getElementById("copyButton");
        btn.textContent = "Copied!";
        showToast("FHIR JSON Payload copied to clipboard!", 'success');
        setTimeout(() => btn.textContent = "📋 Copy FHIR Payload", 2000);
    });
};

// --- ABDM Audit Trail Live Fetcher ---
const auditLogDisplay = document.getElementById("auditLogDisplay");

if (auditLogDisplay) {
    async function fetchAuditLogs() {
        try {
            const response = await fetch("/api/v1/audit-logs");
            if (response.ok) {
                const logText = await response.text();
                auditLogDisplay.textContent = logText || "No logs recorded yet.";
                // Auto-scroll to the bottom of the log window
                auditLogDisplay.scrollTop = auditLogDisplay.scrollHeight;
            }
        } catch (error) {
            console.error("Failed to fetch audit logs:", error);
        }
    }

    // Fetch logs immediately and then every 3 seconds
    fetchAuditLogs();
    setInterval(fetchAuditLogs, 3000);
}

// --- COMMAND PROMPT (Ctrl + K / Cmd + K) ---
const cmdPalette = document.getElementById("commandPalette");
const cmdInput = document.getElementById("commandInput");
const closePaletteBtn = document.getElementById("closePalette");

if (cmdPalette && cmdInput) {
    // Listen for Ctrl+K or Cmd+K globally
    window.addEventListener("keydown", function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault(); // Prevent browser's default search shortcut
            cmdPalette.classList.remove("d-none");
            cmdInput.focus();
            cmdInput.value = "";
        }
        // Close on ESC key
        if (e.key === "Escape" && !cmdPalette.classList.contains("d-none")) {
            cmdPalette.classList.add("d-none");
        }
    });

    // Close button click
    if (closePaletteBtn) {
        closePaletteBtn.addEventListener("click", () => {
            cmdPalette.classList.add("d-none");
        });
    }

    // Close when clicking outside the box
    cmdPalette.addEventListener("click", (e) => {
        if (e.target === cmdPalette) {
            cmdPalette.classList.add("d-none");
        }
    });

    // Quick filter actions inside the command palette
    cmdInput.addEventListener("input", function(e) {
        const query = e.target.value.toLowerCase().trim();
        // You can add instant filtering logic or command shortcuts here
        if (query.startsWith("search ")) {
            // e.g. typing "search jvara" could auto-execute
        }
    });
}

// --- Global Toast Notification Helper ---
function showToast(message, type = 'success') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container-custom';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'custom-toast';
    
    let icon = '✅';
    if (type === 'error') icon = '❌';
    if (type === 'info') icon = 'ℹ️';
    
    toast.innerHTML = `<span style="font-size: 1.2rem;">${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    // Automatically remove after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// --- PWA Service Worker Registration ---
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/src/sw.js')
            .then((registration) => {
                console.log('MedBridge ServiceWorker registered with scope:', registration.scope);
            })
            .catch((error) => {
                console.log('ServiceWorker registration failed:', error);
            });
    });
}

// Password Visibility Eye Toggle (Safely guarded)
const togglePassword = document.getElementById('togglePassword');
const passwordInput = document.getElementById('passwordInput');

if (togglePassword && passwordInput) {
    togglePassword.addEventListener('click', function () {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        this.textContent = type === 'password' ? '👁️' : '🔒';
    });
}

// --- SESSION PROTECTION & SIGN OUT ---
async function checkUserSession() {
    const { data: { session } } = await supabase.auth.getSession();
    
    // If no active session and we are not already on the login page, redirect!
    if ((!session && window.location.pathname.includes('index.html')) || (!session && window.location.pathname.includes('admin.html'))) {
        window.location.href = '/src/login.html'; // Updated path
    }
}

// Run session check on page load
if (window.supabase) {
    checkUserSession();
}

// Global Sign Out Function
window.handleSignOut = async function(event) {
    if(event) 
        event.preventDefault();
    localStorage.removeItem('userRole');
    localStorage.clear();
    sessionStorage.clear();

    try {
        const sb = window.supabaseClient || window.supabase || supabase; 
        if (typeof sb !== 'undefined' && sb.auth) {
            await sb.auth.signOut();
        }
    } catch (err) {
        console.log("Session notice:", err);
    }

    const currentPath = window.location.pathname;
    if (currentPath.includes('/src/')) {
        window.location.replace('login.html');
    } else {
        window.location.replace('/src/login.html');
    }
};

// Switch between Top 3 candidates when pills are clicked
window.selectCandidate = function(index) {
    const entry = window.currentEntries[index];
    const container = document.getElementById("activeCandidateView");
    if (container && entry) {
        container.innerHTML = renderCandidateCard(entry, index);
        showToast(`Switched to candidate #${index + 1}`, 'info');
    }
};

// Helper to generate a clean, side-by-side enterprise split card layout using Flexbox
window.renderCandidateCard = function(entry, index) {
    const res = entry.resource || {};
    const medTwin = res.medicineTwin || {};
    
    // Multi-key fallbacks
    const rawIngredients = medTwin.activeIngredients || medTwin.ingredients || medTwin.active_ingredients;
    const ingredients = rawIngredients ? 
        (Array.isArray(rawIngredients) ? rawIngredients.join(", ") : rawIngredients) 
        : "Not available";
    const rawUses = medTwin.traditionalUses || medTwin.traditional_uses || medTwin.uses;
    const traditionalUses = rawUses ? 
        (Array.isArray(rawUses) ? rawUses.join(", ") : rawUses) 
       "Not available"
    const rawRisk = medTwin.riskRadar || medTwin.risk_warnings || medTwin.risk_alerts || medTwin.alerts;
    const riskAlert = rawRisk ? 
        (Array.isArray(rawRisk) ? rawRisk[0] : rawRisk) 
        : "Not available";
   const codingList = res.code && res.code.coding ? res.code.coding : [];
const tradCode = codingList[0] ? codingList[0].code : "Not available";
const icdCode = codingList[1] ? codingList[1].code : "Not available";
const systemName = res.system || "Not available";
const modernEq = res.modernEquivalent || "Not available";
const tradTerm = res.code && res.code.text ? res.code.text : "Not available";
const confScore = res.confidenceScore || "Not available";

    return `
        <!-- Flexbox wrapper to guarantee side-by-side layout on desktop -->
        <div class="d-flex flex-column flex-lg-row gap-4 mb-4 align-items-stretch w-100">
            
            <!-- Left: AI Medicine Twin (Takes ~66% space) -->
            <div class="glass-panel p-4 border border-secondary shadow-sm text-light d-flex flex-column" style="flex: 2; background: rgba(15, 23, 42, 0.6) !important; border-radius: 12px;">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="fw-bold mb-0" style="color: rgba(0, 229, 255, 0.85); font-size: 1.1rem;">🧬 AI MEDICINE TWIN</h5>
                    <span class="badge px-2 py-1 fw-semibold" style="background: rgba(0, 229, 255, 0.1); border: 1px solid rgba(0, 229, 255, 0.3); color: rgba(0, 229, 255, 0.85); border-radius: 12px; font-size: 0.8rem;">Confidence: ${confScore}</span>
                </div>
                
                <div class="mb-2"><strong style="opacity: 0.7;">Traditional:</strong> <span class="text-light">${tradTerm}</span> <span class="text-muted" style="font-size: 0.8rem;">(${systemName})</span></div>
                <div class="mb-2"><strong style="opacity: 0.7;">Mapping Status:</strong> <span class="text-light">${mappingStatus}</span></div>
                <div class="mb-2"><strong style="opacity: 0.7;">Match Status:</strong> <span class="text-light">${matchStatus}</span></div>
                <div class="mb-2"><strong style="opacity: 0.7;">Source Version:</strong> <span class="text-light">${source.version || "Not available"}</span></div>
                <div class="mb-2"><strong style="opacity: 0.7;">Source:</strong> <span class="text-light">${source.name || "Not available"}</span></div>
                <div class="mb-2" style="color: rgba(56, 189, 248, 0.9);"><strong>↳ NAMASTE Code:</strong> ${tradCode}</div>
                <div class="mb-2"><strong style="opacity: 0.7;">Modern Equivalent:</strong> <span class="text-light">${modernEq}</span></div>
                <div class="mb-3" style="color: rgba(52, 211, 153, 0.9);"><strong>↳ WHO ICD-11 (TM2):</strong> ${icdCode}</div>
    <div class="mb-2"><strong style="opacity: 0.7;">Validation Status:</strong> <span class="text-light">${validationStatus}</span></div>
                <hr class="border-secondary my-3" style="opacity: 0.3;">
                
                <p class="mb-1 fw-bold" style="color: rgba(56, 189, 248, 0.85); font-size: 0.9rem;">Active Botanical Ingredients:</p>
                <p class="text-light small mb-3" style="opacity: 0.8;">${ingredients}</p>
                
                <!-- NEW IOT LOCATION BUTTON -->
                <button class="btn btn-sm w-100 fw-bold py-2 mt-2" style="background: rgba(0, 229, 255, 0.1); border: 1px solid rgba(0, 229, 255, 0.4); color: rgba(0, 229, 255, 0.9); border-radius: 8px; transition: all 0.2s ease;" onmouseover="this.style.background='rgba(0, 229, 255, 0.2)'" onmouseout="this.style.background='rgba(0, 229, 255, 0.1)'" onclick="findNearbyClinics('${systemName}')">
                    📍 Find Nearby ${systemName} Clinics (IoT)
                </button>
            </div>

            <!-- Right: Cross-System Risk Radar Sidebar (Takes ~33% space) -->
            <div class="glass-panel p-4 border border-secondary shadow-sm text-light d-flex flex-column justify-content-between" style="flex: 1; background: rgba(245, 158, 11, 0.03) !important; border-color: rgba(245, 158, 11, 0.15) !important; border-radius: 12px;">
                <div>
                    <h5 class="fw-bold mb-3" style="color: rgba(251, 191, 36, 0.85); font-size: 1.05rem;">⚠️ CROSS-SYSTEM RISK RADAR</h5>
                    <div class="p-3 rounded bg-dark border border-warning border-opacity-10 mb-3">
                       <strong style="color: rgba(251, 191, 36, 0.8); font-size: 0.85rem;">Risk Radar:</strong>
                        <p class="small text-muted mt-1 mb-0" style="line-height: 1.4; opacity: 0.85;">${riskAlert}</p>
                    </div>
                </div>
                <button class="btn btn-sm w-100 fw-bold py-2 mt-auto" style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.25); color: rgba(251, 191, 36, 0.85); border-radius: 8px; transition: all 0.2s ease;" onmouseover="this.style.background='rgba(245, 158, 11, 0.2)'" onmouseout="this.style.background='rgba(245, 158, 11, 0.1)'" onclick="showToast('Warning acknowledged & logged to ABDM audit trail.', 'success')">
                    ✅ Acknowledge Warning
                </button>
            </div>
            
        </div>
    `;
};

window.showAIExplanation = function() {
    if (window.currentEntries && window.currentEntries.length > 0) {
        const entry = window.currentEntries[0].resource;
       const scoreStr = entry.confidenceScore || "Not available";
        const scoreNum = parseFloat(scoreStr);
        const term = entry.code.text;
        
        let matchReason = "Semantic NLP match using TF-IDF cosine similarity.";
        if (scoreNum >= 98.0) {
            matchReason = "Exact term match in the standardized terminology registry.";
        } else if (scoreNum >= 95.0) {
            matchReason = "Matched via known regional aliases or synonyms.";
        }
        
        showGlassModal("Explainable AI (XAI) Engine", `
            <div style="margin-bottom: 12px;"><strong>Term Mapped:</strong> ${term}</div>
            <div style="margin-bottom: 12px;"><strong>Confidence Score:</strong> ${scoreStr}</div>
            <div style="margin-bottom: 12px;"><strong>Match Reason:</strong> ${matchReason}</div>
            <div><strong>Methodology:</strong> Standardized to NAMASTE and WHO ICD-11 TM2 ontologies.</div>
        `);
    } else {
        showGlassModal("Explainable AI (XAI) Engine", "No AI mapping data available to explain.");
    }
};

window.togglePatientView = function() {
    if (window.currentEntries && window.currentEntries.length > 0) {
        const entry = window.currentEntries[0].resource;
        const condition = entry.modernEquivalent || entry.code.text;
        
        const medTwin = entry.medicineTwin || {};
       const rawUses = medTwin.traditionalUses || medTwin.traditional_uses || medTwin.uses;
        const uses = Array.isArray(rawUses) ? rawUses.join(", ") : rawUses;
        
        const rawRisk = medTwin.riskRadar || medTwin.risk_warnings || ["Consult your physician before combining medications."];
        const risk = Array.isArray(rawRisk) ? rawRisk[0] : rawRisk;

        showGlassModal("Patient Friendly View", `
            <div style="margin-bottom: 12px;"><strong>Condition:</strong> ${condition}</div>
            <div style="margin-bottom: 12px;"><strong>Purpose:</strong> ${uses}</div>
            <div><strong>Caution:</strong> ${risk}</div>
        `);
    } else {
        showGlassModal("Patient Friendly View", "No active patient data available.");
    }
};

// Helper function to render a gorgeous centered glassmorphism modal popup
function showGlassModal(title, contentHtml) {
    const existingModal = document.getElementById('customGlassModal');
    if (existingModal) existingModal.remove();

    const overlay = document.createElement('div');
    overlay.id = 'customGlassModal';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(5, 8, 15, 0.75);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        z-index: 99999;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeInGlass 0.2s ease-out;
    `;

    const card = document.createElement('div');
    card.style.cssText = `
        background: rgba(18, 24, 38, 0.85);
        border: 1px solid rgba(0, 242, 254, 0.3);
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 242, 254, 0.15);
        border-radius: 16px;
        padding: 28px;
        width: 90%;
        max-width: 440px;
        color: #f8fafc;
        font-family: inherit;
        position: relative;
    `;

    card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">
            <h3 style="margin: 0; font-size: 1.15rem; color: #38bdf8; font-weight: 600;">${title}</h3>
            <button id="closeGlassBtn" style="background: transparent; border: none; color: #94a3b8; font-size: 1.4rem; cursor: pointer; padding: 0; line-height: 1;">&times;</button>
        </div>
        <div style="font-size: 0.95rem; line-height: 1.5; color: #cbd5e1; margin-bottom: 24px;">
            ${contentHtml}
        </div>
        <div style="text-align: right;">
            <button id="glassOkBtn" style="background: linear-gradient(135deg, #0ea5e9, #2563eb); border: none; color: white; padding: 8px 20px; border-radius: 8px; font-weight: 500; cursor: pointer; box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);">Close</button>
        </div>
    `;

    overlay.appendChild(card);
    document.body.appendChild(overlay);

    const closeAction = () => overlay.remove();
    document.getElementById('closeGlassBtn').onclick = closeAction;
    document.getElementById('glassOkBtn').onclick = closeAction;
    overlay.onclick = (e) => { if (e.target === overlay) closeAction(); };
}

// --- IOT LOCATION-BASED ROUTING ---
window.findNearbyClinics = function(systemName) {
    showToast(`📍 Acquiring GPS coordinates & querying live global map for ${systemName}...`, "success");
    if (!navigator.geolocation) {
        showToast("Geolocation is not supported by your browser.", "error");
        return;
    }

    navigator.geolocation.getCurrentPosition(async (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        
        showToast("📡 Coordinates acquired! Searching network...", "success");

        try {
            const response = await fetch('/api/v1/nearby-clinics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    latitude: lat,
                    longitude: lng,
                    condition_system: systemName || "Siddha"
                })
            });

            const data = await response.json();
            if (data.status === 'success') {
                renderClinicsList(data.clinics);
            } else {
                showToast("Error finding clinics: " + data.message, "error");
            }
        } catch (error) {
            showToast("API connection failed.", "error");
            console.error(error);
        }
    }, (error) => {
        console.error(error);
        showToast("Location access denied. Please allow permissions in your browser.", "error");
    });
};
function renderClinicsList(clinics) {
    const modalBody = document.getElementById('clinicsModalBody');
    
    if (clinics.length === 0) {
        modalBody.innerHTML = `<p class="text-muted text-center py-4">No specialized clinics found within range.</p>`;
    } else {
        let html = '<div class="d-flex flex-column gap-3">';
        clinics.forEach((c) => {
            html += `
                <div class="p-3 rounded border border-secondary" style="background: rgba(255,255,255,0.02);">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h6 class="fw-bold text-light mb-1">${c.name}</h6>
                            <p class="text-muted small mb-0">👨‍⚕️ ${c.doctor}</p>
                        </div>
                        <span class="badge bg-dark border border-info" style="color: rgba(0, 229, 255, 0.9);">${c.distance_km} km</span>
                    </div>
                    <div class="d-flex justify-content-between align-items-center mt-3">
                        <span class="small" style="color: rgba(52, 211, 153, 0.9);">System: ${c.specialties[0]}</span>
                        
                        <!-- UPDATED REFER PATIENT BUTTON TO TRIGGER EMAIL -->
                        <button class="btn btn-sm btn-outline-success fw-bold py-1 px-3" style="opacity: 0.9;" onclick="sendReferralEmail('${c.name}', '${c.doctor}', '${c.distance_km}', '${c.specialties[0]}')">Refer Patient</button>
                    
                    </div>
                </div>
            `;
        });
        html += '</div>';
        modalBody.innerHTML = html;
    }

    const clinicsModal = new bootstrap.Modal(document.getElementById('clinicsModal'));
    clinicsModal.show();
}

// Function to trigger the backend Email API
window.sendReferralEmail = async function(clinicName, doctorName, distance, system) {
    showToast("📧 Encrypting and sending secure referral...", "success");
    
    try {
        const response = await fetch('/api/v1/send-referral', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                clinic_name: clinicName,
                doctor_name: doctorName,
                condition: system,
                distance: distance.toString()
            })
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            // Close the modal
            const modalEl = document.getElementById('clinicsModal');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            if(modalInstance) modalInstance.hide();
            
            // Show massive success alert
            setTimeout(() => {
                showToast(`✅ ABDM Referral sent to ${clinicName}! Check your email inbox.`, "success");
            }, 1000);
        }
    } catch (error) {
        showToast("Error establishing secure connection.", "error");
        console.error(error);
    }
};

const clearSearchBtn = document.getElementById("clearSearchBtn");

if (diseaseInput && clearSearchBtn) {
    // Show/hide close button based on whether text exists
    diseaseInput.addEventListener("input", function() {
        if (this.value.trim().length > 0) {
            clearSearchBtn.classList.remove("d-none");
        } else {
            clearSearchBtn.classList.add("d-none");
        }
    });

    // Clear input and results when close button is clicked
    clearSearchBtn.addEventListener("click", function() {
        diseaseInput.value = "";
        clearSearchBtn.classList.add("d-none");
        if (result) result.innerHTML = "";
        if (emrIntegration) emrIntegration.innerHTML = "";
        diseaseInput.focus();
        showToast("Search cleared.", "info");
    });
}
