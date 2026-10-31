const API_URL = "http://127.0.0.1:5000/analyse";
const textInput = document.getElementById("claim-text");
const languageInput = document.getElementById("language");
const sourceSearch = document.getElementById("source-search");
const screenshotInput = document.getElementById("screenshot");
const analyzeButton = document.getElementById("analyze");
const progress = document.getElementById("progress");
const progressDetail = document.getElementById("progress-detail");
const errorBox = document.getElementById("error");
const errorMessage = document.getElementById("error-message");
const retryButton = document.getElementById("retry");
const results = document.getElementById("results");
const report = document.getElementById("report");
const copyButton = document.getElementById("copy");
const newCheckButton = document.getElementById("new-check");
const selectionNote = document.getElementById("selection-note");

let lastFormData = null;
let lastReport = "";

function add(parent, tag, text, className = "") {
    const element = document.createElement(tag);
    element.textContent = text;
    if (className) element.className = className;
    parent.appendChild(element);
    return element;
}

function setError(message) {
    errorMessage.textContent = message;
    errorBox.hidden = false;
}

function showProgress(active) {
    progress.hidden = !active;
    analyzeButton.disabled = active;
    progressDetail.textContent = active ? "Reading claim · analyzing with Gemma · preparing report" : "";
}

function makeReport(data) {
    const analysis = data.analysis || {};
    const claims = Array.isArray(analysis.claims) ? analysis.claims : [];
    report.replaceChildren();
    const provider = analysis.ai_provider
        || (analysis.gemma_provenance && analysis.gemma_provenance.provider)
        || "local rules";
    const model = analysis.ai_model
        || (analysis.gemma_provenance && analysis.gemma_provenance.model)
        || "local rules";
    const heading = add(report, "div", `Provider: ${provider} · ${model}`, "meta");
    heading.setAttribute("aria-label", "Actual provider and model");
    claims.filter((item) => item && typeof item.claim === "string").slice(0, 6).forEach((claim) => {
        const claimCard = add(report, "article", "", "report-card");
        add(claimCard, "span", "EXTRACTED CLAIM", "report-label");
        add(claimCard, "h3", claim.claim);
        const ai = add(report, "article", "", "report-card ai");
        add(ai, "span", "AI ASSESSMENT", "report-label");
        add(ai, "h3", typeof claim.ai_assessment === "string" ? claim.ai_assessment : "Not provided");
        if (typeof claim.ai_explanation === "string") add(ai, "p", claim.ai_explanation);
        if (typeof claim.ai_limitations === "string") add(ai, "p", claim.ai_limitations, "meta");
        const evidence = add(report, "article", "", "report-card evidence");
        add(evidence, "span", "INDEPENDENT EVIDENCE", "report-label");
        add(evidence, "h3", typeof claim.verdict === "string" ? claim.verdict : "Unverified");
        add(evidence, "p", "AI assessment is separate from evidence verification.");
        if (Array.isArray(claim.sources)) {
            claim.sources.slice(0, 3).forEach((source) => {
                if (!source || typeof source.url !== "string" || typeof source.title !== "string") return;
                let url;
                try { url = new URL(source.url); } catch (_) { return; }
                if (url.protocol !== "https:") return;
                const link = add(evidence, "a", source.title, "source-link");
                link.href = url.href;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
            });
        }
    });
    const status = analysis.evidence_status && analysis.evidence_status.message;
    if (typeof status === "string") add(report, "p", status, "meta");
    return report.innerText;
}

async function analyze() {
    if (!textInput.value.trim() && !screenshotInput.files[0]) {
        setError("Paste a claim or choose a screenshot first.");
        return;
    }
    errorBox.hidden = true;
    results.hidden = true;
    showProgress(true);
    const formData = new FormData();
    formData.append("language", languageInput.value);
    formData.append("source_search_enabled", sourceSearch.checked ? "true" : "false");
    if (screenshotInput.files[0]) {
        formData.append("image", screenshotInput.files[0]);
        formData.append("source_type", "image");
    } else {
        formData.append("message", textInput.value);
        formData.append("source_type", "text");
    }
    lastFormData = formData;
    try {
        const response = await fetch(API_URL, { method: "POST", body: formData });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Server error (${response.status}).`);
        if (!data.analysis || !Array.isArray(data.analysis.claims)) {
            throw new Error("The backend returned an incomplete analysis.");
        }
        lastReport = makeReport(data);
        results.hidden = false;
    } catch (error) {
        setError(error instanceof Error ? error.message : "Analysis failed. Try again.");
    } finally {
        showProgress(false);
    }
}

analyzeButton.addEventListener("click", analyze);
retryButton.addEventListener("click", () => { if (lastFormData) analyze(); });
copyButton.addEventListener("click", async () => {
    if (!lastReport) return;
    try {
        await navigator.clipboard.writeText(lastReport);
        copyButton.textContent = "Copied";
        window.setTimeout(() => { copyButton.textContent = "Copy"; }, 1500);
    } catch (_) {
        setError("Could not copy the report. Select the report text manually.");
    }
});
newCheckButton.addEventListener("click", () => {
    results.hidden = true;
    textInput.value = "";
    screenshotInput.value = "";
    selectionNote.hidden = true;
    textInput.focus();
});

if (new URLSearchParams(location.search).has("selection")) {
    chrome.storage.session.get("pendingSelection").then((data) => {
        if (typeof data.pendingSelection !== "string") return;
        textInput.value = data.pendingSelection;
        selectionNote.hidden = false;
        chrome.storage.session.remove("pendingSelection");
    });
}
