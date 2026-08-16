const searchButton = document.getElementById("searchButton");
const diseaseInput = document.getElementById("diseaseInput");
const result = document.getElementById("result");

searchButton.addEventListener("click", async function () {
    const disease = diseaseInput.value.trim();

    if (!disease) {
        result.textContent = "Please enter a diagnosis.";
        return;
    }

    result.textContent = "Searching...";

    try {
        const response = await fetch(
            `http://127.0.0.1:8000/sync/${encodeURIComponent(disease)}`
        );

        const data = await response.json();

        if (data.status === "success") {
            const mapping = data.data[0];

            result.innerHTML = `
                <p><strong>System:</strong> ${mapping.system}</p>
                <p><strong>Traditional Term:</strong> ${mapping.traditional_term}</p>
                <p><strong>NAMASTE Code:</strong> ${mapping.namaste_code}</p>
                <p><strong>TM2 Code:</strong> ${mapping.tm2_code}</p>
            `;
        } else {
            result.textContent = data.message;
        }

    } catch (error) {
        result.textContent = "Unable to connect to the MedBridge API.";
        console.error(error);
    }
});