const uploadForm = document.getElementById("upload-form");
const textForm = document.getElementById("text-form");
const fileInput = document.getElementById("screenshot");
const messageInput = document.getElementById("message-text");
const uploadButton = document.getElementById("analyse-button");
const textButton = document.getElementById("analyse-text-button");
const statusText = document.getElementById("status");
const results = document.getElementById("results");
const shareReportText = document.getElementById("share-report-text");
const copyReportButton = document.getElementById("copy-report-button");
const shareReportButton = document.getElementById("share-report-button");
const shareReportStatus = document.getElementById("share-report-status");
const readReportButton = document.getElementById("read-report-button");
const pauseSpeechButton = document.getElementById("pause-speech-button");
const stopSpeechButton = document.getElementById("stop-speech-button");
const speechStatus = document.getElementById("speech-status");
const mediaChecklistButton = document.getElementById("media-checklist-button");
const mediaChecklist = document.getElementById("media-checklist");
const languageSelect = document.getElementById("language-select");
const sourceSearchCheckbox = document.getElementById("source-search-enabled");
const analysisEndpoint = document.currentScript.dataset.analyseUrl;
const ANALYSIS_TIMEOUT_MS = 60000;
const heroAction = document.querySelector(".hero-action");
const progressPanel = document.getElementById("progress-panel");
const progressDetail = document.getElementById("progress-detail");
const progressSteps = document.querySelectorAll("[data-progress-step]");
const imagePreview = document.getElementById("image-preview");
const dropzone = document.querySelector(".dropzone");
const statClaims = document.getElementById("stat-claims");
const statScreenshots = document.getElementById("stat-screenshots");
const statLanguages = document.getElementById("stat-languages");
const flowExplanation = document.getElementById("flow-explanation");
const flowStages = document.querySelectorAll("[data-flow-target]");

const sessionStats = {
    claims: 0,
    screenshots: 0,
    languages: new Set()
};

const translations = {
    en: {
        tagline: "Think before you forward.",
        navHome: "Home",
        navHowItWorks: "How It Works",
        navAbout: "About",
        startChecking: "Start Checking",
        howHeading: "A careful way to review a forwarded claim.",
        howCopy: "Paste text or upload a screenshot. Forward Check identifies claims, warning signals, and practical ways to check the message. Optional external search can provide source leads, but snippets are not proof.",
        aboutHeading: "Evidence helps you investigate. It does not decide truth for you.",
        aboutCopy: "Results can be incomplete, sources can disagree, and a cautious score is not a truth or fraud probability. URLs are analysed as text and are not automatically opened.",
        heroTitle: "Think Before You Believe.",
        pageIntro: "Check claims. Explore evidence. Make informed decisions.",
        pageHeading: "Check a Forwarded Message",
        pageIntro: "Upload a screenshot or paste message text to identify claims, possible warning signals, and ways to verify it.",
        languageLabel: "Report language",
        sourceSearchOptIn: "Only if you opt in, send extracted claims, available speaker/context details, and relevant entities to configured external search providers (Tavily, with optional Brave fallback) for source leads. Search snippets are not verification.",
        pasteHeading: "Paste a message or post",
        messageLabel: "Message text (URLs are analysed as text and are not opened)",
        messagePlaceholder: "Paste the forwarded message or post here...",
        analyseMessage: "Analyse Message",
        uploadHeading: "Or upload a screenshot",
        uploadLabel: "Upload screenshot",
        analyseForward: "Analyse Forward",
        extractedHeading: "Extracted Message",
        extractedEditHint: "Extracted text (edit OCR mistakes, then analyse again)",
        analyseCorrected: "Analyse corrected text",
        urlsHeading: "URLs found in the message",
        urlsNotOpened: "These URLs were not opened or checked.",
        urlAnalysisHeading: "URL format observations",
        urlValid: "The URL has a parseable format. The website was not accessed.",
        urlInvalid: "The URL format could not be parsed reliably.",
        urlNoWarnings: "No listed URL-format warning was detected. This does not mean the website is safe or verified.",
        websiteNotChecked: "Website content not checked; URL not opened.",
        scopeHeading: "What this analysis checked",
        riskHeading: "Risk Meter",
        riskUnavailable: "Risk assessment unavailable",
        riskScoreUnavailable: "",
        riskDisclaimer: "This score represents detected warning signs, not a verified assessment of whether the message is true or false.",
        claimsHeading: "Claims to Check",
        verdictUnverified: "Verdict: Unverified",
        verdictSupported: "Supported by Evidence",
        verdictMostlyTrue: "Mostly True",
        verdictMisleading: "Misleading or Missing Context",
        verdictMostlyFalse: "Mostly False",
        verdictFalse: "False",
        verdictNotFactual: "Not a Factual Claim",
        verdictSupportHeading: "Supporting evidence",
        verdictContradictionHeading: "Contradicting evidence",
        verdictContextHeading: "Relevant context",
        verdictOtherHeading: "Other assessed sources",
        verdictFailuresHeading: "Sources not assessed",
        verdictLimitationsHeading: "Limitations and unresolved questions",
        verdictSufficient: "Evidence sufficient for this limited verdict",
        verdictInsufficient: "Evidence is not sufficient for a verdict",
        verdictDisclosure: "Search snippets are not proof. Retrieved text may be incomplete, sources may disagree, and automated assessments can be wrong. Unverified does not mean false. The caution score is not a truth score.",
        sourceSearchNotEnabled: "Live source discovery is off; no claims were sent to external search providers.",
        sourceSearchNotConfigured: "Live source search is not configured.",
        sourceSearchNoResults: "Search completed; no result leads were returned.",
        sourceSearchFailed: "Live source search could not be completed; check each lead's retrieval status.",
        sourceSearchLimited: "Not searched because the per-report search limit was reached.",
        sourceSearchNotSearchable: "No usable claim wording was available to search.",
        sourceSearchRateLimited: "Not searched because the provider rate limit was reached.",
        sourceSearchNotAttempted: "Not searched because a provider request failed.",
        sourceSearchNotFactual: "Not searched because this is not a factual claim.",
        sourceSearchFactualPartUnclear: "A possible factual part of this opinion could not be separated reliably, so it was not searched.",
        sourceSearchFound: "Search-result leads found; each page's retrieval status and assessment are shown where available.",
        extractionMethodLocal: "This claim was extracted with deterministic local rules; it was not fact-checked.",
        extractionFallback: "Ollama was unavailable or its output could not be used, so local fallback extraction ran. Extraction does not verify claims.",
        extractionMethodOllama: "Ollama assisted with claim extraction only; it did not verify these claims.",
        aiAssessmentHeading: "Gemma 4 AI assessment",
        aiAssessmentModel: "AI model: {0}",
        aiAssessmentExplanation: "AI explanation:",
        aiAssessmentLimitations: "AI limitations:",
        gemmaContribution: "Gemma assisted with claim extraction. Deterministic local rules supplemented the result where needed. Search, retrieval, evidence assessment and verdicts are separate processes.",
        originalWording: "Original wording:",
        normalizedWording: "Normalized wording:",
        claimTopics: "Topics:",
        sourceLeadsHeading: "Search result leads (not verified)",
        sourceDate: "Search-result date: {0}",
        sourcePageDate: "Page publication date: {0}",
        sourceDateNotProvided: "The search provider did not supply a publication date.",
        sourceDateUnrecognized: "A publication date was supplied but could not be read.",
        sourceQuery: "Search query:",
        sourceProvider: "Search provider:",
        sourceSummary: "Search-result snippet (not retrieved page text):",
        sourceRelation: "A search result is a lead; only retrieved page text can inform an assessment.",
        sourceDetails: "Source details",
        sourceLimitations: "Page not retrieved or assessed.",
        sourceRetrievalStatus: "Retrieval status:",
        sourceRetrieved: "Retrieved readable text",
        sourceRetrievalFailed: "Retrieval failed",
        sourceRetrievalBlocked: "Blocked destination",
        sourceRetrievalTimeout: "Timed out",
        sourceRetrievalTooLarge: "Response exceeded the size limit",
        sourceRetrievalUnsupported: "Unsupported content type",
        sourceRetrievalNotAttempted: "Not retrieved (analysis limit)",
        sourceRetrievalOther: "Could not retrieve",
        sourcePageTitle: "Retrieved page title:",
        sourceType: "Source type:",
        evidenceAssessmentHeading: "Evidence assessment (not a verdict)",
        evidenceSupports: "Supports",
        evidenceContradicts: "Contradicts",
        evidenceContextualizes: "Contextualizes",
        evidenceDoesNotAddress: "Does Not Address",
        evidenceInsufficient: "Insufficient Information",
        evidenceRetrievalFailed: "Retrieval Failed",
        evidencePassage: "Retrieved passage:",
        partialContent: "Only partial page text was retrieved.",
        noSourceLeads: "No search-result leads are available for this claim.",
        signalsHeading: "Warning Signals",
        verificationHeading: "Verification Steps",
        mediaHeading: "Fake Voice and Video Warning",
        mediaIntro: "AI-generated or manipulated audio and video can sound or look convincing. Unusual visual details or a suspicious-sounding voice alone do not prove that media is fake. Forward Check does not detect or verify deepfakes.",
        mediaButton: "How to Verify Audio or Video",
        mediaStep1: "Find out who first posted the content and check the original source.",
        mediaStep2: "Look for the full video or recording instead of relying on a short clip.",
        mediaStep3: "Check whether trustworthy news organizations or official sources independently confirm the claim.",
        mediaStep4Before: "Take a relevant video frame and reverse-search it with",
        mediaStep4After: ". Avoid uploading private or sensitive images.",
        or: "or",
        mediaStep5: "For a suspicious voice message, contact the person using a phone number you already know or another trusted channel.",
        mediaStep6: "Be cautious about urgent requests for money, passwords, OTPs, or confidential information.",
        mediaStep7: "Do not forward audio or video until you have checked it.",
        speechHeading: "Listen to the Report",
        speechIntro: "Your browser will read a short summary of the analysis. The original message and page code are not read aloud.",
        readReport: "Read Report Aloud",
        pauseSpeech: "Pause Speech",
        resumeSpeech: "Resume Speech",
        stopSpeech: "Stop Speech",
        shareHeading: "Share This Report",
        shareIntro: "Review this summary, then copy it or share it using your browser's share menu. Nothing is sent automatically.",
        reportTextLabel: "Report text",
        copyReport: "Copy Report",
        shareReport: "Share Report",
        disclaimer: "Forward Check helps you investigate claims but does not independently establish whether a message is true or false.",
        noClaims: "No clear factual claims could be extracted. This does not mean the message is accurate or safe; verify it independently.",
        noSignals: "No specific warning signals were identified.",
        evidencePrefix: "Message evidence:",
        noLinks: "No verification websites were provided for this analysis. Find the organisation named in the message independently.",
        riskUnavailableReason: "The server did not provide a risk assessment for this result.",
        riskScore: "Caution score: {0} points",
        scoreUnavailable: "Caution score unavailable",
        noRiskReasons: "No detailed reasons were included in the assessment.",
        noIndicators: "No configured warning signs were detected.",
        riskLow: "Low Caution",
        riskMedium: "Medium Caution",
        riskHigh: "High Caution",
        languageSwitched: "Language changed. The message you entered has been kept.",
        noReportRead: "There is no report available to read yet.",
        speechUnsupported: "Text-to-speech is not supported in this browser. Try a current version of Edge or Chrome.",
        reading: "Reading report aloud.",
        finishedReading: "Finished reading the report.",
        speechError: "Speech playback stopped unexpectedly. You can try reading the report again.",
        speechStarting: "Starting speech...",
        speechStartError: "Speech could not be started. Check that your browser has a speech voice available.",
        startBeforePause: "Start reading the report before pausing.",
        speechResumed: "Speech resumed.",
        speechPaused: "Speech paused.",
        shareNoReport: "There is no report to share yet.",
        copyError: "Could not copy automatically. Select the report text and copy it manually.",
        clipboardCopied: "Report copied to the clipboard.",
        sharingUnavailableCopied: "Sharing is unavailable in this browser. The report was copied instead.",
        reportShared: "Report shared.",
        shareCancelled: "Sharing was cancelled.",
        sharingFailedCopied: "Sharing did not complete. The report was copied instead.",
        speechStopped: "Speech stopped.",
        uploadMissing: "Please select a screenshot to analyse.",
        pasteMissing: "Please paste a message to analyse.",
        analysing: "Analysing your message...",
        extracting: "Extracting text and analysing claims...",
        completed: "Analysis completed.",
        analysisFailed: "Analysis failed.",
        missingResults: "The server response is missing analysis results. Please try again.",
        invalidJsonResponse: "The server returned a response that was not valid JSON.",
        networkError: "Cannot reach Forward Check. Make sure Flask is running, then reload this page and try again.",
        requestTimeout: "The request timed out. Check that Flask and Ollama are responding, then try again.",
        httpError: "The server returned HTTP {0}: {1}",
        serverError: "Forward Check encountered a server error (HTTP {0}). Check the Flask terminal for details.",
        serverErrorDetail: "The server could not complete the request.",
        noSpeechReport: "This analysis helps investigate a message. It does not prove whether the message is true or false.",
        spokenIntro: "Forward Check analysed the submitted message to help investigate its claims.",
        spokenCaution: "Caution level: {0}.",
        spokenReasons: "Reasons: {0}",
        spokenClaims: "Main claims to check: {0}.",
        spokenNoClaims: "No clear factual claims could be extracted. This does not mean the message is accurate or safe; verify it independently.",
        spokenWarnings: "Warning signs: {0}.",
        spokenNoWarnings: "No configured warning signs were detected.",
        spokenSteps: "Ways to verify: {0}.",
        reportTitle: "Forward Check Report",
        reportIntro: "Forward Check analysed a submitted message to help identify possible warning signs and ways to verify claims.",
        reportCaution: "Caution level: {0}{1}",
        reportWarningHeading: "Warning signs:",
        reportNoWarnings: "- No configured warning signs were detected. This does not mean the message is safe or verified.",
        reportStepsHeading: "Ways to verify:",
        reportNoSteps: "- No verification steps were provided in this analysis.",
        reportLinksHeading: "Verification websites:",
        reportNoLinks: "- No verification websites were provided in this analysis.",
        reportEvidence: "Message evidence: ",
        reportWarning: "Warning sign",
        scoreLabel: "score: {0}",
        reportClaimsHeading: "Claims to check:",
        reportEvidenceStatus: "Source search:",
        reportNoClaims: "- No clear factual claims could be extracted. This does not mean the message is accurate or safe; verify it independently.",
        bothInputs: "Submit either pasted message text or a screenshot, not both.",
        tooLong: "Message text is too long. Please keep it under {0} characters.",
        noScreenshotOrMessage: "Please upload a screenshot or paste message text.",
        noOcrText: "No readable text found. Try a clearer screenshot.",
        tesseractMissing: "Tesseract was not found. Check its installation path.",
        ocrFailed: "OCR failed: {0}",
        invalidImage: "The uploaded file is not a valid image.",
        hindiOcrMissing: "Hindi screenshot text needs Tesseract Hindi data (hin.traineddata). Install it or paste the text instead.",
        uploadTooLarge: "The request is too large. Keep the image under 8 MB.",
        unsupportedImage: "Unsupported image type. Upload a PNG, JPG, JPEG, or WEBP image.",
        imageTypeMismatch: "The uploaded file type does not match its filename.",
        imageDimensions: "The image dimensions are too large. Upload a smaller image.",
        ocrFailedGeneric: "OCR failed. Check Tesseract installation and try again."
    },
    hi: {
        tagline: "आगे भेजने से पहले सोचें।",
        navHome: "होम",
        navHowItWorks: "कैसे काम करता है",
        navAbout: "About",
        startChecking: "जाँच शुरू करें",
        howHeading: "फॉरवर्ड किए गए दावे की सावधानी से जाँच करें।",
        howCopy: "पाठ पेस्ट करें या स्क्रीनशॉट अपलोड करें। Forward Check दावों, चेतावनी संकेतों और जाँच के व्यावहारिक तरीकों की पहचान करता है। वैकल्पिक external search source leads दे सकती है, लेकिन snippets प्रमाण नहीं हैं।",
        aboutHeading: "Evidence जाँच में मदद करता है, लेकिन आपके लिए सत्य तय नहीं करता।",
        aboutCopy: "नतीजे अधूरे हो सकते हैं और स्रोतों में मतभेद हो सकता है। सावधानी का score सत्य या धोखाधड़ी की probability नहीं है। URLs को text की तरह analyse किया जाता है और वे अपने आप नहीं खोले जाते।",
        heroTitle: "विश्वास करने से पहले सोचें।",
        pageHeading: "फॉरवर्ड संदेश की जाँच करें",
        pageIntro: "दावों और चेतावनी संकेतों की पहचान करने तथा जाँच के तरीके जानने के लिए स्क्रीनशॉट अपलोड करें या संदेश पेस्ट करें।",
        languageLabel: "रिपोर्ट की भाषा",
        sourceSearchOptIn: "केवल आपकी अनुमति पर निकाले गए दावे, उपलब्ध वक्ता/संदर्भ जानकारी और संबंधित जानकारी configured external search providers (Tavily, optional Brave fallback) को source leads के लिए भेजी जाएगी। खोज के अंश पुष्टि नहीं हैं।",
        pasteHeading: "संदेश या पोस्ट पेस्ट करें",
        messageLabel: "संदेश का पाठ (लिंक केवल पाठ के रूप में जाँचे जाते हैं, खोले नहीं जाते)",
        messagePlaceholder: "फॉरवर्ड संदेश या पोस्ट यहाँ पेस्ट करें...",
        analyseMessage: "संदेश की जाँच करें",
        uploadHeading: "या स्क्रीनशॉट अपलोड करें",
        uploadLabel: "स्क्रीनशॉट अपलोड करें",
        analyseForward: "फॉरवर्ड की जाँच करें",
        extractedHeading: "निकाला गया संदेश",
        extractedEditHint: "निकाला गया पाठ (OCR की गलती सुधारकर फिर जाँचें)",
        analyseCorrected: "सुधारे गए पाठ की जाँच करें",
        urlsHeading: "संदेश में मिले लिंक",
        urlsNotOpened: "ये लिंक खोले या जाँचे नहीं गए।",
        urlAnalysisHeading: "URL format की जाँच",
        urlValid: "URL का format पढ़ा जा सका। वेबसाइट नहीं खोली गई।",
        urlInvalid: "URL का format ठीक से पढ़ा नहीं जा सका।",
        urlNoWarnings: "सूची में दिए URL-format चेतावनी संकेत नहीं मिले। इसका मतलब यह नहीं कि वेबसाइट सुरक्षित या प्रमाणित है।",
        websiteNotChecked: "वेबसाइट का content नहीं जाँचा गया; URL नहीं खोला गया।",
        scopeHeading: "इस विश्लेषण में क्या जाँचा गया",
        riskHeading: "जोखिम संकेतक",
        riskUnavailable: "जोखिम आकलन उपलब्ध नहीं",
        riskScoreUnavailable: "",
        riskDisclaimer: "यह अंक मिले चेतावनी संकेत दिखाता है; यह संदेश के सही या गलत होने की पुष्टि नहीं है।",
        claimsHeading: "जाँचने योग्य दावे",
        verdictUnverified: "निष्कर्ष: अपुष्ट",
        verdictSupported: "प्रमाण से समर्थित",
        verdictMostlyTrue: "अधिकतर सही",
        verdictMisleading: "भ्रामक या संदर्भ अधूरा",
        verdictMostlyFalse: "अधिकतर गलत",
        verdictFalse: "गलत",
        verdictNotFactual: "तथ्यात्मक दावा नहीं",
        verdictSupportHeading: "समर्थन करने वाला प्रमाण",
        verdictContradictionHeading: "विरोध करने वाला प्रमाण",
        verdictContextHeading: "संबंधित संदर्भ",
        verdictOtherHeading: "अन्य जाँचे गए स्रोत",
        verdictFailuresHeading: "जाँचे नहीं जा सके स्रोत",
        verdictLimitationsHeading: "सीमाएँ और अनसुलझे प्रश्न",
        verdictSufficient: "इस सीमित निष्कर्ष के लिए प्रमाण पर्याप्त है",
        verdictInsufficient: "निष्कर्ष के लिए प्रमाण पर्याप्त नहीं है",
        verdictDisclosure: "खोज के अंश स्वयं प्रमाण नहीं हैं। प्राप्त पाठ अधूरा हो सकता है, स्रोत असहमत हो सकते हैं और स्वचालित आकलन गलत हो सकते हैं। अपुष्ट का अर्थ गलत नहीं है। सावधानी अंक सत्यता का अंक नहीं है।",
        sourceSearchNotEnabled: "लाइव स्रोत खोज बंद है; कोई दावा external search providers को नहीं भेजा गया।",
        sourceSearchNotConfigured: "लाइव स्रोत खोज सेट नहीं है।",
        sourceSearchNoResults: "खोज पूरी हुई; कोई परिणाम नहीं मिला।",
        sourceSearchFailed: "लाइव स्रोत खोज पूरी नहीं हो सकी; हर स्रोत की प्राप्ति स्थिति देखें।",
        sourceSearchLimited: "रिपोर्ट की खोज सीमा के कारण यह दावा नहीं खोजा गया।",
        sourceSearchNotSearchable: "खोज के लिए दावा स्पष्ट नहीं था।",
        sourceSearchRateLimited: "Provider की rate limit के कारण खोज नहीं हुई।",
        sourceSearchNotAttempted: "Provider अनुरोध विफल होने के कारण खोज नहीं हुई।",
        sourceSearchNotFactual: "यह तथ्यात्मक दावा नहीं है, इसलिए खोज नहीं हुई।",
        sourceSearchFactualPartUnclear: "इस राय के संभावित तथ्यात्मक हिस्से को भरोसे से अलग नहीं किया जा सका, इसलिए उसकी खोज नहीं हुई।",
        sourceSearchFound: "खोज परिणाम मिले; हर पेज की प्राप्ति स्थिति और आकलन जहाँ उपलब्ध हो दिखाया गया है।",
        extractionMethodLocal: "यह दावा स्थानीय नियमों से निकाला गया; इसकी तथ्य-जाँच नहीं हुई।",
        extractionFallback: "Ollama उपलब्ध नहीं था या उसका उत्तर उपयोग नहीं हो सका, इसलिए स्थानीय fallback extraction चला। दावा निकालना सत्यापन नहीं है।",
        extractionMethodOllama: "Ollama ने केवल दावा निकालने में मदद की; उसने दावों का सत्यापन नहीं किया।",
        aiAssessmentHeading: "Gemma 4 AI आकलन",
        aiAssessmentModel: "AI मॉडल: {0}",
        aiAssessmentExplanation: "AI व्याख्या:",
        aiAssessmentLimitations: "AI सीमाएँ:",
        gemmaContribution: "Gemma ने दावा निकालने में मदद की। जहाँ ज़रूरत थी, स्थानीय deterministic rules ने परिणाम को पूरा किया। Search, retrieval, evidence assessment और verdict अलग प्रक्रियाएँ हैं।",
        originalWording: "मूल शब्द:",
        normalizedWording: "सामान्य रूप:",
        claimTopics: "विषय:",
        sourceLeadsHeading: "खोज परिणाम के संकेत (पुष्ट नहीं)",
        sourceDate: "खोज परिणाम की तारीख: {0}",
        sourcePageDate: "पेज पर दी गई प्रकाशन तारीख: {0}",
        sourceDateNotProvided: "Search provider ने प्रकाशन की तारीख नहीं दी।",
        sourceDateUnrecognized: "तारीख दी गई थी, लेकिन उसे पढ़ा नहीं जा सका।",
        sourceQuery: "खोज का प्रश्न:",
        sourceProvider: "खोज provider:",
        sourceSummary: "खोज परिणाम का अंश (प्राप्त पेज का पाठ नहीं):",
        sourceRelation: "खोज परिणाम केवल स्रोत-संकेत है; आकलन केवल प्राप्त पेज के पाठ से हो सकता है।",
        sourceDetails: "स्रोत की जानकारी",
        sourceLimitations: "पेज प्राप्त या जाँचा नहीं गया।",
        sourceRetrievalStatus: "पेज प्राप्ति की स्थिति:",
        sourceRetrieved: "पढ़ने योग्य पाठ प्राप्त हुआ",
        sourceRetrievalFailed: "पेज प्राप्त नहीं हुआ",
        sourceRetrievalBlocked: "असुरक्षित गंतव्य रोका गया",
        sourceRetrievalTimeout: "समय सीमा समाप्त",
        sourceRetrievalTooLarge: "जवाब आकार सीमा से बड़ा था",
        sourceRetrievalUnsupported: "यह सामग्री प्रकार समर्थित नहीं है",
        sourceRetrievalNotAttempted: "प्राप्त नहीं किया (विश्लेषण सीमा)",
        sourceRetrievalOther: "पेज प्राप्त नहीं हो सका",
        sourcePageTitle: "प्राप्त पेज का शीर्षक:",
        sourceType: "स्रोत का प्रकार:",
        evidenceAssessmentHeading: "प्रमाण का आकलन (अंतिम निष्कर्ष नहीं)",
        evidenceSupports: "समर्थन करता है",
        evidenceContradicts: "खंडन करता है",
        evidenceContextualizes: "संदर्भ देता है",
        evidenceDoesNotAddress: "दावे पर बात नहीं करता",
        evidenceInsufficient: "अपर्याप्त जानकारी",
        evidenceRetrievalFailed: "स्रोत प्राप्त नहीं हुआ",
        evidencePassage: "प्राप्त अंश:",
        partialContent: "पेज का केवल कुछ पाठ प्राप्त हुआ।",
        noSourceLeads: "इस दावे के लिए खोज परिणाम उपलब्ध नहीं हैं।",
        signalsHeading: "चेतावनी संकेत",
        verificationHeading: "जाँच के तरीके",
        mediaHeading: "नकली आवाज़ और वीडियो से सावधान",
        mediaIntro: "AI से बने या बदले गए ऑडियो और वीडियो असली लग सकते हैं। केवल अजीब दृश्य या संदिग्ध आवाज़ से यह साबित नहीं होता कि मीडिया नकली है। Forward Check डीपफेक की पहचान या पुष्टि नहीं करता।",
        mediaButton: "ऑडियो या वीडियो की जाँच कैसे करें",
        mediaStep1: "पता करें कि सामग्री सबसे पहले किसने पोस्ट की और मूल स्रोत जाँचें।",
        mediaStep2: "छोटी क्लिप के बजाय पूरा वीडियो या रिकॉर्डिंग खोजें।",
        mediaStep3: "जाँचें कि भरोसेमंद समाचार संस्थाएँ या आधिकारिक स्रोत स्वतंत्र रूप से दावे की पुष्टि करते हैं या नहीं।",
        mediaStep4Before: "वीडियो का सही फ्रेम लेकर रिवर्स सर्च करें:",
        mediaStep4After: "। निजी या संवेदनशील तस्वीरें अपलोड न करें।",
        or: "या",
        mediaStep5: "संदिग्ध आवाज़ के संदेश पर उस व्यक्ति से पहले से ज्ञात नंबर या भरोसेमंद माध्यम से संपर्क करें।",
        mediaStep6: "पैसे, पासवर्ड, OTP या गोपनीय जानकारी की जल्दी में की गई माँगों से सावधान रहें।",
        mediaStep7: "जाँच करने से पहले ऑडियो या वीडियो आगे न भेजें।",
        speechHeading: "रिपोर्ट सुनें",
        speechIntro: "आपका ब्राउज़र विश्लेषण का छोटा सार पढ़ेगा। मूल संदेश और पेज का कोड नहीं पढ़ा जाएगा।",
        readReport: "रिपोर्ट ज़ोर से पढ़ें",
        pauseSpeech: "पढ़ना रोकें",
        resumeSpeech: "फिर शुरू करें",
        stopSpeech: "पढ़ना बंद करें",
        shareHeading: "यह रिपोर्ट साझा करें",
        shareIntro: "सार की समीक्षा करें, फिर उसे कॉपी करें या ब्राउज़र के शेयर विकल्प से भेजें। कुछ भी अपने आप नहीं भेजा जाता।",
        reportTextLabel: "रिपोर्ट का पाठ",
        copyReport: "रिपोर्ट कॉपी करें",
        shareReport: "रिपोर्ट साझा करें",
        disclaimer: "Forward Check दावों की जाँच में मदद करता है, लेकिन अपने आप यह साबित नहीं करता कि संदेश सही है या गलत।",
        noClaims: "कोई स्पष्ट तथ्यात्मक दावा नहीं निकाला जा सका। इसका मतलब यह नहीं कि संदेश सही या सुरक्षित है; स्वतंत्र रूप से जाँचें।",
        noSignals: "कोई खास चेतावनी संकेत नहीं मिला।",
        evidencePrefix: "संदेश में प्रमाण:",
        noLinks: "इस विश्लेषण में जाँच की वेबसाइट नहीं दी गई। संदेश में बताई संस्था को स्वतंत्र रूप से खोजें।",
        riskUnavailableReason: "इस परिणाम के लिए सर्वर ने जोखिम आकलन नहीं दिया।",
        riskScore: "सावधानी अंक: {0}",
        scoreUnavailable: "सावधानी अंक उपलब्ध नहीं",
        noRiskReasons: "आकलन में कोई विस्तृत कारण नहीं दिया गया।",
        noIndicators: "पहचाने गए चेतावनी संकेत नहीं मिले।",
        riskLow: "कम सावधानी",
        riskMedium: "मध्यम सावधानी",
        riskHigh: "अधिक सावधानी",
        languageSwitched: "भाषा बदल गई है। आपका लिखा संदेश सुरक्षित है।",
        noReportRead: "अभी पढ़ने के लिए कोई रिपोर्ट नहीं है।",
        speechUnsupported: "इस ब्राउज़र में टेक्स्ट-टू-स्पीच उपलब्ध नहीं है। Edge या Chrome का नया संस्करण आज़माएँ।",
        reading: "रिपोर्ट पढ़ी जा रही है।",
        finishedReading: "रिपोर्ट पढ़ना पूरा हुआ।",
        speechError: "आवाज़ अचानक रुक गई। रिपोर्ट फिर से पढ़ने की कोशिश करें।",
        speechStarting: "आवाज़ शुरू हो रही है...",
        speechStartError: "आवाज़ शुरू नहीं हुई। जाँचें कि ब्राउज़र में बोलने वाली आवाज़ उपलब्ध है।",
        startBeforePause: "रोकने से पहले रिपोर्ट पढ़ना शुरू करें।",
        speechResumed: "पढ़ना फिर शुरू हुआ।",
        speechPaused: "पढ़ना रोक दिया गया।",
        shareNoReport: "अभी साझा करने के लिए कोई रिपोर्ट नहीं है।",
        copyError: "अपने आप कॉपी नहीं हुआ। रिपोर्ट का पाठ चुनकर मैन्युअल रूप से कॉपी करें।",
        clipboardCopied: "रिपोर्ट क्लिपबोर्ड पर कॉपी हुई।",
        sharingUnavailableCopied: "इस ब्राउज़र में शेयर विकल्प नहीं है। रिपोर्ट कॉपी कर दी गई।",
        reportShared: "रिपोर्ट साझा की गई।",
        shareCancelled: "साझा करना रद्द हुआ।",
        sharingFailedCopied: "साझा नहीं हो सका। रिपोर्ट कॉपी कर दी गई।",
        speechStopped: "पढ़ना बंद किया गया।",
        uploadMissing: "जाँच के लिए स्क्रीनशॉट चुनें।",
        pasteMissing: "जाँच के लिए संदेश पेस्ट करें।",
        analysing: "संदेश की जाँच हो रही है...",
        extracting: "पाठ निकाला जा रहा है और दावों की जाँच हो रही है...",
        completed: "जाँच पूरी हुई।",
        analysisFailed: "जाँच नहीं हो सकी।",
        missingResults: "सर्वर के जवाब में जाँच के नतीजे नहीं हैं। फिर से कोशिश करें।",
        invalidJsonResponse: "सर्वर का जवाब सही JSON format में नहीं है।",
        networkError: "Forward Check से संपर्क नहीं हो पा रहा। Flask चालू है या नहीं जाँचें, पेज फिर खोलें और कोशिश करें।",
        requestTimeout: "अनुरोध का समय पूरा हो गया। Flask और Ollama के जवाब की जाँचकर फिर कोशिश करें।",
        httpError: "सर्वर ने HTTP {0} जवाब दिया: {1}",
        serverError: "Forward Check में सर्वर त्रुटि हुई (HTTP {0})। जानकारी के लिए Flask terminal देखें।",
        serverErrorDetail: "सर्वर अनुरोध पूरा नहीं कर सका।",
        noSpeechReport: "यह विश्लेषण संदेश की जाँच में मदद करता है। यह संदेश को सही या गलत साबित नहीं करता।",
        spokenIntro: "Forward Check ने संदेश के दावों की जाँच में मदद के लिए उसका विश्लेषण किया।",
        spokenCaution: "सावधानी का स्तर: {0}।",
        spokenReasons: "कारण: {0}",
        spokenClaims: "जाँचने योग्य मुख्य दावे: {0}।",
        spokenNoClaims: "कोई स्पष्ट तथ्यात्मक दावा नहीं निकाला जा सका। इसका मतलब यह नहीं कि संदेश सही या सुरक्षित है; स्वतंत्र रूप से जाँचें।",
        spokenWarnings: "चेतावनी संकेत: {0}।",
        spokenNoWarnings: "पहचाने गए चेतावनी संकेत नहीं मिले।",
        spokenSteps: "जाँच के तरीके: {0}।",
        reportTitle: "Forward Check रिपोर्ट",
        reportIntro: "Forward Check ने चेतावनी संकेत और दावों की जाँच के तरीके पहचानने के लिए संदेश का विश्लेषण किया।",
        reportCaution: "सावधानी का स्तर: {0}{1}",
        reportWarningHeading: "चेतावनी संकेत:",
        reportNoWarnings: "- कोई चेतावनी संकेत नहीं मिला। इसका अर्थ यह नहीं कि संदेश सुरक्षित या प्रमाणित है।",
        reportStepsHeading: "जाँच के तरीके:",
        reportNoSteps: "- इस विश्लेषण में जाँच के तरीके नहीं दिए गए।",
        reportLinksHeading: "जाँच के लिए वेबसाइटें:",
        reportNoLinks: "- इस विश्लेषण में जाँच की वेबसाइटें नहीं दी गईं।",
        reportEvidence: "संदेश में प्रमाण: ",
        reportWarning: "चेतावनी संकेत",
        scoreLabel: "अंक: {0}",
        reportClaimsHeading: "जाँचने योग्य दावे:",
        reportEvidenceStatus: "स्रोत खोज:",
        reportNoClaims: "- कोई स्पष्ट तथ्यात्मक दावा नहीं निकाला जा सका। इसका मतलब यह नहीं कि संदेश सही या सुरक्षित है; स्वतंत्र रूप से जाँचें।",
        bothInputs: "या तो संदेश का पाठ भेजें या स्क्रीनशॉट, दोनों नहीं।",
        tooLong: "संदेश बहुत लंबा है। इसे {0} अक्षरों से कम रखें।",
        noScreenshotOrMessage: "स्क्रीनशॉट अपलोड करें या संदेश पेस्ट करें।",
        noOcrText: "पढ़ने योग्य पाठ नहीं मिला। अधिक साफ़ स्क्रीनशॉट आज़माएँ।",
        tesseractMissing: "Tesseract नहीं मिला। उसका इंस्टॉलेशन पाथ जाँचें।",
        ocrFailed: "OCR विफल हुआ: {0}",
        invalidImage: "अपलोड की गई फ़ाइल सही इमेज नहीं है।",
        hindiOcrMissing: "हिंदी स्क्रीनशॉट पढ़ने के लिए Tesseract का हिंदी डेटा (hin.traineddata) इंस्टॉल करें या पाठ यहाँ पेस्ट करें।",
        uploadTooLarge: "फ़ाइल बहुत बड़ी है। इमेज 8 MB से छोटी रखें।",
        unsupportedImage: "यह इमेज प्रकार समर्थित नहीं है। PNG, JPG, JPEG या WEBP अपलोड करें।",
        imageTypeMismatch: "अपलोड की गई फ़ाइल का प्रकार उसके नाम से मेल नहीं खाता।",
        imageDimensions: "इमेज का आकार बहुत बड़ा है। छोटी इमेज अपलोड करें।",
        ocrFailedGeneric: "OCR विफल हुआ। Tesseract इंस्टॉलेशन जाँचकर फिर कोशिश करें।"
    },
    hinglish: {
        tagline: "Aage bhejne se pehle sochein.",
        navHome: "Home",
        navHowItWorks: "Kaise Kaam Karta Hai",
        navAbout: "About",
        startChecking: "Checking Shuru Karein",
        howHeading: "Forwarded claim ko carefully review karne ka tareeqa.",
        howCopy: "Text paste karein ya screenshot upload karein. Forward Check claims, warning signals aur check karne ke practical tareeqe identify karta hai. Optional external search source leads de sakti hai, lekin snippets proof nahi hain.",
        aboutHeading: "Evidence investigation mein help karta hai; truth aapke liye decide nahi karta.",
        aboutCopy: "Results incomplete ho sakte hain aur sources disagree kar sakte hain. Caution score truth ya fraud probability nahi hai. URLs ko text ki tarah analyse kiya jata hai aur automatically open nahi kiya jata.",
        heroTitle: "Maanne Se Pehle Sochein.",
        pageHeading: "Forwarded Message Check Karein",
        pageIntro: "Claims aur warning signals pehchanne aur verify karne ke tareeqe jaanne ke liye screenshot upload karein ya message paste karein.",
        languageLabel: "Report ki language",
        sourceSearchOptIn: "Sirf aapki permission par extracted claims, available speaker/context details aur relevant entities configured external search providers (Tavily, optional Brave fallback) ko source leads ke liye bheje jayenge. Search snippets verification nahi hain.",
        pasteHeading: "Message ya post paste karein",
        messageLabel: "Message text (URLs ko text ki tarah analyse kiya jata hai, khola nahi jata)",
        messagePlaceholder: "Forwarded message ya post yahan paste karein...",
        analyseMessage: "Message Analyse Karein",
        uploadHeading: "Ya screenshot upload karein",
        uploadLabel: "Screenshot upload karein",
        analyseForward: "Forward Analyse Karein",
        extractedHeading: "Nikala gaya Message",
        extractedEditHint: "Nikala gaya text (OCR ki galti sudhaarkar dobara analyse karein)",
        analyseCorrected: "Corrected text analyse karein",
        urlsHeading: "Message mein mile URLs",
        urlsNotOpened: "Yeh URLs khole ya check nahi kiye gaye.",
        urlAnalysisHeading: "URL format observations",
        urlValid: "URL ka format parse hua. Website access nahi hui.",
        urlInvalid: "URL ka format reliably parse nahi ho saka.",
        urlNoWarnings: "Listed URL-format warning nahi mili. Iska matlab yeh nahi ki website safe ya verified hai.",
        websiteNotChecked: "Website content check nahi hua; URL open nahi hua.",
        scopeHeading: "Is analysis mein kya check hua",
        riskHeading: "Risk Meter",
        riskUnavailable: "Risk assessment available nahi",
        riskScoreUnavailable: "",
        riskDisclaimer: "Yeh score mile warning signals dikhata hai; yeh message ke sahi ya galat hone ki pushti nahi hai.",
        claimsHeading: "Check Karne Wale Claims",
        verdictUnverified: "Verdict: Unverified",
        verdictSupported: "Evidence se Supported",
        verdictMostlyTrue: "Mostly True",
        verdictMisleading: "Misleading ya Context Adhoora",
        verdictMostlyFalse: "Mostly False",
        verdictFalse: "False",
        verdictNotFactual: "Factual Claim Nahi",
        verdictSupportHeading: "Supporting evidence",
        verdictContradictionHeading: "Contradicting evidence",
        verdictContextHeading: "Relevant context",
        verdictOtherHeading: "Other assessed sources",
        verdictFailuresHeading: "Sources assess nahi hue",
        verdictLimitationsHeading: "Limitations aur unresolved questions",
        verdictSufficient: "Is limited verdict ke liye evidence sufficient hai",
        verdictInsufficient: "Verdict ke liye evidence sufficient nahi hai",
        verdictDisclosure: "Search snippets proof nahi hain. Retrieved text incomplete ho sakta hai, sources disagree kar sakte hain, aur automated assessment galat ho sakta hai. Unverified ka matlab false nahi. Caution score truth score nahi hai.",
        sourceSearchNotEnabled: "Live source discovery off hai; koi claim external search providers ko nahi bheja gaya.",
        sourceSearchNotConfigured: "Live source search configure nahi hai.",
        sourceSearchNoResults: "Search complete hui; koi result lead nahi mili.",
        sourceSearchFailed: "Live source search complete nahi hui; har lead ka retrieval status check karein.",
        sourceSearchLimited: "Report ki search limit ke kaaran yeh claim search nahi hua.",
        sourceSearchNotSearchable: "Search karne ke liye claim wording available nahi thi.",
        sourceSearchRateLimited: "Provider rate limit ke kaaran search nahi hui.",
        sourceSearchNotAttempted: "Provider request fail hone ke kaaran search nahi hui.",
        sourceSearchNotFactual: "Yeh factual claim nahi hai, isliye search nahi hui.",
        sourceSearchFactualPartUnclear: "Opinion ke possible factual part ko reliably alag nahi kar sake, isliye search nahi hui.",
        sourceSearchFound: "Search-result leads mili; har page ka retrieval status aur assessment jahan available hai dikhaya gaya hai.",
        extractionMethodLocal: "Yeh claim deterministic local rules se nikala gaya; iski fact-checking nahi hui.",
        extractionFallback: "Ollama available nahi tha ya uska output use nahi ho saka, isliye local fallback extraction chala. Extraction claim verify nahi karta.",
        extractionMethodOllama: "Ollama ne sirf claims extract karne mein madad ki; usne claims verify nahi kiye.",
        aiAssessmentHeading: "Gemma 4 AI assessment",
        aiAssessmentModel: "AI model: {0}",
        aiAssessmentExplanation: "AI explanation:",
        aiAssessmentLimitations: "AI limitations:",
        gemmaContribution: "Gemma ne claims extract karne mein madad ki. Zaroorat par local deterministic rules ne result ko supplement kiya. Search, retrieval, evidence assessment aur verdict alag processes hain.",
        originalWording: "Original wording:",
        normalizedWording: "Normalized wording:",
        claimTopics: "Topics:",
        sourceLeadsHeading: "Search result leads (verified nahi)",
        sourceDate: "Search result date: {0}",
        sourcePageDate: "Page par di gayi publication date: {0}",
        sourceDateNotProvided: "Search provider ne publication date nahi di.",
        sourceDateUnrecognized: "Date di gayi thi, lekin read nahi ho saki.",
        sourceQuery: "Search query:",
        sourceProvider: "Search provider:",
        sourceSummary: "Search-result snippet (retrieved page text nahi):",
        sourceRelation: "Search result ek lead hai; assessment sirf retrieved page text se hota hai.",
        sourceDetails: "Source details",
        sourceLimitations: "Page retrieve ya assess nahi hua.",
        sourceRetrievalStatus: "Page retrieval status:",
        sourceRetrieved: "Readable text retrieve hua",
        sourceRetrievalFailed: "Retrieval fail hui",
        sourceRetrievalBlocked: "Blocked destination",
        sourceRetrievalTimeout: "Timeout",
        sourceRetrievalTooLarge: "Response size limit se bada tha",
        sourceRetrievalUnsupported: "Content type supported nahi hai",
        sourceRetrievalNotAttempted: "Retrieve nahi hua (analysis limit)",
        sourceRetrievalOther: "Retrieve nahi ho saka",
        sourcePageTitle: "Retrieved page title:",
        sourceType: "Source type:",
        evidenceAssessmentHeading: "Evidence assessment (final verdict nahi)",
        evidenceSupports: "Support karta hai",
        evidenceContradicts: "Contradict karta hai",
        evidenceContextualizes: "Context deta hai",
        evidenceDoesNotAddress: "Claim ko address nahi karta",
        evidenceInsufficient: "Insufficient information",
        evidenceRetrievalFailed: "Retrieval failed",
        evidencePassage: "Retrieved passage:",
        partialContent: "Sirf partial page text retrieve hua.",
        noSourceLeads: "Is claim ke liye search-result leads available nahi hain.",
        signalsHeading: "Warning Signals",
        verificationHeading: "Verify Karne ke Steps",
        mediaHeading: "Fake Voice aur Video se Savdhan",
        mediaIntro: "AI se bane ya badle audio aur video asli lag sakte hain. Sirf ajeeb visuals ya suspicious awaaz se media fake prove nahi hota. Forward Check deepfake detect ya verify nahi karta.",
        mediaButton: "Audio ya Video Verify Kaise Karein",
        mediaStep1: "Pata karein content sabse pehle kisne post kiya aur original source check karein.",
        mediaStep2: "Chhoti clip par bharosa karne ke bajaye poora video ya recording dhoondhein.",
        mediaStep3: "Check karein ki bharosemand news organisations ya official sources claim ko independently confirm karte hain ya nahi.",
        mediaStep4Before: "Video ka relevant frame lekar reverse search karein:",
        mediaStep4After: ". Private ya sensitive images upload na karein.",
        or: "ya",
        mediaStep5: "Suspicious voice message ke liye us insaan ko pehle se jaane hue number ya trusted channel se contact karein.",
        mediaStep6: "Paise, password, OTP ya confidential information ke urgent requests se savdhan rahein.",
        mediaStep7: "Check karne se pehle audio ya video forward na karein.",
        speechHeading: "Report Sunein",
        speechIntro: "Aapka browser analysis ka chhota summary padhega. Original message aur page code nahi padha jayega.",
        readReport: "Report Zor se Padhein",
        pauseSpeech: "Pause Karein",
        resumeSpeech: "Phir Shuru Karein",
        stopSpeech: "Padhna Band Karein",
        shareHeading: "Yeh Report Share Karein",
        shareIntro: "Summary review karein, phir copy karein ya browser ke share menu se bhejein. Kuch bhi apne aap nahi bheja jata.",
        reportTextLabel: "Report text",
        copyReport: "Report Copy Karein",
        shareReport: "Report Share Karein",
        disclaimer: "Forward Check claims ki jaanch mein madad karta hai, lekin apne aap yeh prove nahi karta ki message sahi hai ya galat.",
        noClaims: "Koi clear factual claim extract nahi hua. Iska matlab yeh nahi ki message sahi ya safe hai; independently verify karein.",
        noSignals: "Koi khaas warning signal nahi mila.",
        evidencePrefix: "Message evidence:",
        noLinks: "Is analysis mein verification website nahi di gayi. Message mein batayi organisation ko independently dhoondhein.",
        riskUnavailableReason: "Server ne is result ke liye risk assessment nahi diya.",
        riskScore: "Caution score: {0} points",
        scoreUnavailable: "Caution score available nahi",
        noRiskReasons: "Assessment mein detailed reasons nahi diye gaye.",
        noIndicators: "Pehchane gaye warning signals nahi mile.",
        riskLow: "Kam Savdhani",
        riskMedium: "Madhyam Savdhani",
        riskHigh: "Zyada Savdhani",
        languageSwitched: "Language badal gayi hai. Aapka likha message safe hai.",
        noReportRead: "Abhi padhne ke liye report nahi hai.",
        speechUnsupported: "Is browser mein text-to-speech available nahi. Edge ya Chrome ka naya version try karein.",
        reading: "Report padhi ja rahi hai.",
        finishedReading: "Report padhna poora hua.",
        speechError: "Speech achanak ruk gayi. Report dobara padhne ki koshish karein.",
        speechStarting: "Speech shuru ho rahi hai...",
        speechStartError: "Speech shuru nahi ho saki. Check karein ki browser mein speech voice available hai.",
        startBeforePause: "Pause karne se pehle report padhna shuru karein.",
        speechResumed: "Speech phir shuru hui.",
        speechPaused: "Speech pause hui.",
        shareNoReport: "Abhi share karne ke liye report nahi hai.",
        copyError: "Auto copy nahi ho saka. Report text select karke manually copy karein.",
        clipboardCopied: "Report clipboard par copy hui.",
        sharingUnavailableCopied: "Is browser mein sharing available nahi. Report copy kar di gayi.",
        reportShared: "Report share hui.",
        shareCancelled: "Sharing cancel hui.",
        sharingFailedCopied: "Sharing poori nahi hui. Report copy kar di gayi.",
        speechStopped: "Speech band hui.",
        uploadMissing: "Analyse karne ke liye screenshot select karein.",
        pasteMissing: "Analyse karne ke liye message paste karein.",
        analysing: "Aapka message analyse ho raha hai...",
        extracting: "Text nikala ja raha hai aur claims analyse ho rahe hain...",
        completed: "Analysis poora hua.",
        analysisFailed: "Analysis nahi ho saka.",
        missingResults: "Server response mein analysis results nahi hain. Dobara try karein.",
        invalidJsonResponse: "Server ka response valid JSON format mein nahi hai.",
        networkError: "Forward Check se connect nahi ho pa raha. Flask chal raha hai ya nahi check karein, page reload karke dobara try karein.",
        requestTimeout: "Request ka time poora ho gaya. Flask aur Ollama ke response check karke dobara try karein.",
        httpError: "Server ne HTTP {0} response diya: {1}",
        serverError: "Forward Check mein server error hui (HTTP {0}). Details ke liye Flask terminal dekhein.",
        serverErrorDetail: "Server request poori nahi kar saka.",
        noSpeechReport: "Yeh analysis message check karne mein madad karta hai. Yeh message ko sahi ya galat prove nahi karta.",
        spokenIntro: "Forward Check ne message ke claims check karne mein madad ke liye analysis kiya.",
        spokenCaution: "Caution level: {0}.",
        spokenReasons: "Reasons: {0}",
        spokenClaims: "Check karne wale main claims: {0}.",
        spokenNoClaims: "Koi clear factual claim extract nahi hua. Iska matlab yeh nahi ki message sahi ya safe hai; independently verify karein.",
        spokenWarnings: "Warning signals: {0}.",
        spokenNoWarnings: "Koi pehchana gaya warning signal nahi mila.",
        spokenSteps: "Verify karne ke tareeqe: {0}.",
        reportTitle: "Forward Check Report",
        reportIntro: "Forward Check ne warning signals aur claims verify karne ke tareeqe pehchanne ke liye message analyse kiya.",
        reportCaution: "Caution level: {0}{1}",
        reportWarningHeading: "Warning signals:",
        reportNoWarnings: "- Koi warning signal nahi mila. Iska matlab yeh nahi ki message safe ya verified hai.",
        reportStepsHeading: "Verify karne ke tareeqe:",
        reportNoSteps: "- Is analysis mein verification steps nahi diye gaye.",
        reportLinksHeading: "Verification websites:",
        reportNoLinks: "- Is analysis mein verification websites nahi di gayi.",
        reportEvidence: "Message evidence: ",
        reportWarning: "Warning signal",
        scoreLabel: "score: {0}",
        reportClaimsHeading: "Check karne wale claims:",
        reportEvidenceStatus: "Source search:",
        reportNoClaims: "- Koi clear factual claim extract nahi hua. Iska matlab yeh nahi ki message sahi ya safe hai; independently verify karein.",
        bothInputs: "Ya to pasted message text bhejein ya screenshot, dono nahi.",
        tooLong: "Message bahut lamba hai. Ise {0} characters se chhota rakhein.",
        noScreenshotOrMessage: "Screenshot upload karein ya message paste karein.",
        noOcrText: "Padhne layak text nahi mila. Zyada clear screenshot try karein.",
        tesseractMissing: "Tesseract nahi mila. Uska installation path check karein.",
        ocrFailed: "OCR fail hua: {0}",
        invalidImage: "Upload ki gayi file valid image nahi hai.",
        hindiOcrMissing: "Hindi screenshot text padhne ke liye Tesseract ka Hindi data (hin.traineddata) install karein ya text paste karein.",
        uploadTooLarge: "Request bahut badi hai. Image 8 MB se chhoti rakhein.",
        unsupportedImage: "Yeh image type supported nahi hai. PNG, JPG, JPEG ya WEBP upload karein.",
        imageTypeMismatch: "Uploaded file type uske filename se match nahi karta.",
        imageDimensions: "Image dimensions bahut bade hain. Chhoti image upload karein.",
        ocrFailedGeneric: "OCR fail hua. Tesseract installation check karke dobara try karein."
    }
};

let currentLanguage = languageSelect.value;
let lastAnalyzedText = "";

function t(key, ...values) {
    let text = translations[currentLanguage][key] || translations.en[key] || key;
    values.forEach((value, index) => {
        text = text.replace(`{${index}}`, value);
    });
    return text;
}

function localizeServerError(message) {
    if (message === "Submit either pasted message text or a screenshot, not both.") {
        return t("bothInputs");
    }
    if (message === "Please paste a message to analyse.") {
        return t("pasteMissing");
    }
    if (message === "Please upload a screenshot or paste message text.") {
        return t("noScreenshotOrMessage");
    }
    if (message.startsWith("Message text is too long.")) {
        return t("tooLong", 10000);
    }
    if (message.startsWith("Upload is too large.")) {
        return t("uploadTooLarge");
    }
    if (message.startsWith("Unsupported image type.")) {
        return t("unsupportedImage");
    }
    if (message === "The uploaded file type does not match its filename.") {
        return t("imageTypeMismatch");
    }
    if (message === "The image dimensions are too large. Upload a smaller image.") {
        return t("imageDimensions");
    }
    if (message === "OCR failed. Check Tesseract installation and try again.") {
        return t("ocrFailedGeneric");
    }
    if (message === "No readable text found. Try a clearer screenshot.") {
        return t("noOcrText");
    }
    if (message === "Tesseract was not found. Check its installation path.") {
        return t("tesseractMissing");
    }
    if (message.startsWith("OCR failed: ")) {
        return t("ocrFailed", message.slice("OCR failed: ".length));
    }
    if (message === "The uploaded file is not a valid image.") {
        return t("invalidImage");
    }
    if (message.startsWith("Hindi screenshot text needs Tesseract Hindi data")) {
        return t("hindiOcrMissing");
    }
    return message;
}

function localizeSignalName(name) {
    const labels = {
        "Urgency": { hi: "जल्दी करने का दबाव", hinglish: "Jaldi karne ka pressure" },
        "Forwarding request": { hi: "आगे भेजने का अनुरोध", hinglish: "Aage forward karne ki request" },
        "Promotional or emotional wording": { hi: "प्रचार या भावनात्मक भाषा", hinglish: "Promotional ya emotional wording" },
        "Link included": { hi: "लिंक शामिल है", hinglish: "Link shamil hai" },
        "credential_request": {
            en: "Sensitive information request",
            hi: "संवेदनशील जानकारी माँगना",
            hinglish: "Sensitive information maangna"
        },
        "urgency": {
            en: "Urgency",
            hi: "जल्दी करने का दबाव",
            hinglish: "Jaldi karne ka pressure"
        },
        "authority_word_in_hostname": {
            en: "Government-looking web address",
            hi: "सरकारी जैसा दिखने वाला web address",
            hinglish: "Government jaisa dikhne wala web address"
        },
        "suspicious_url_structure": {
            en: "Unusual web address structure",
            hi: "असामान्य web address structure",
            hinglish: "Unusual web address structure"
        },
        "unencrypted_http": {
            en: "HTTP web address",
            hi: "HTTP web address",
            hinglish: "HTTP web address"
        },
        "lookalike_brand_term": {
            en: "Lookalike brand wording",
            hi: "मिलते-जुलते brand का wording",
            hinglish: "Lookalike brand wording"
        },
        "mass_forwarding": {
            en: "Broad forwarding request",
            hi: "बहुत लोगों को forward करने का अनुरोध",
            hinglish: "Bahut logon ko forward karne ki request"
        },
        "unattributed_benefit": {
            en: "Unattributed benefit",
            hi: "बिना स्पष्ट स्रोत का लाभ",
            hinglish: "Clear source ke bina benefit"
        }
    };
    return labels[name] && (labels[name][currentLanguage] || labels[name].en)
        ? labels[name][currentLanguage] || labels[name].en
        : name;
}

function applyUiLanguage() {
    document.documentElement.lang = currentLanguage === "hi" ? "hi" : "en";
    document.querySelectorAll("[data-i18n]").forEach((element) => {
        const key = element.dataset.i18n;
        if (translations[currentLanguage][key] !== undefined) {
            element.textContent = t(key);
        }
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
        const key = element.dataset.i18nPlaceholder;
        if (translations[currentLanguage][key] !== undefined) {
            element.placeholder = t(key);
        }
    });
}

const MAX_REPORT_LENGTH = 6000;
const MAX_SPOKEN_REPORT_LENGTH = 3000;
let currentSpeechText = "";
let currentUtterance = null;
let languageChangePending = false;
let lastSourceType = "text";
const correctedTextButton = document.getElementById("analyse-corrected-button");
const correctedTextButtonLabel = correctedTextButton.querySelector("span");

function updateSessionStats(claimCount, sourceType, language) {
    sessionStats.claims += claimCount;
    if (sourceType === "image") {
        sessionStats.screenshots += 1;
    }
    sessionStats.languages.add(language);
    statClaims.textContent = sessionStats.claims;
    statScreenshots.textContent = sessionStats.screenshots;
    statLanguages.textContent = sessionStats.languages.size;
}

function setProgressStage(stage, sourceType) {
    const stages = sourceType === "image"
        ? ["reading", "extracting", "analysing", "sources", "report"]
        : ["reading", "analysing", "sources", "report"];
    progressSteps.forEach((step) => {
        const key = step.dataset.progressStep;
        step.classList.toggle("active", key === stage);
        step.classList.remove("done");
        step.hidden = sourceType !== "image" && key === "extracting";
    });
    const active = document.querySelector(`[data-progress-step="${stage}"]`);
    progressDetail.textContent = active
        ? active.textContent.replace(/^\d+\s*/, "").trim()
        : stage;
}

function startProgress(sourceType, searchEnabled) {
    progressPanel.hidden = false;
    progressPanel.setAttribute("aria-busy", "true");
    setProgressStage("reading", sourceType);
    const stages = sourceType === "image"
        ? ["reading", "extracting", "analysing", ...(searchEnabled ? ["sources"] : []), "report"]
        : ["reading", "analysing", ...(searchEnabled ? ["sources"] : []), "report"];
    const waitingStages = stages.slice(0, -1);
    let index = 0;
    const timer = window.setInterval(() => {
        index += 1;
        if (index >= waitingStages.length) {
            window.clearInterval(timer);
            index = waitingStages.length - 1;
        }
        if (waitingStages[index]) {
            setProgressStage(waitingStages[index], sourceType);
        }
    }, 850);
    return () => {
        window.clearInterval(timer);
        setProgressStage("report", sourceType);
        progressPanel.setAttribute("aria-busy", "false");
        window.setTimeout(() => {
            progressPanel.hidden = true;
        }, 500);
    };
}

function showImagePreview(file) {
    if (!file || !file.type.startsWith("image/")) {
        imagePreview.hidden = true;
        imagePreview.replaceChildren();
        return;
    }
    const image = document.createElement("img");
    image.alt = "Selected screenshot preview";
    image.src = URL.createObjectURL(file);
    imagePreview.replaceChildren(image);
    imagePreview.hidden = false;
}

const flowDescriptions = {
    "flow-claim": "We preserve the message's wording so you can see exactly what was analysed.",
    "flow-ai": "Gemma provides a separate, clearly labelled AI assessment based on the claim.",
    "flow-evidence": "Optional source search looks for leads; retrieved evidence is assessed separately.",
    "flow-report": "The report combines findings and limitations without claiming more than the evidence supports."
};

flowStages.forEach((stage) => {
    stage.addEventListener("click", () => {
        flowStages.forEach((item) => item.classList.toggle("active", item === stage));
        const target = stage.dataset.flowTarget;
        const title = stage.querySelector("strong");
        flowExplanation.innerHTML = "";
        addTextElement(flowExplanation, "strong", title ? title.textContent : "Stage");
        addTextElement(flowExplanation, "span", flowDescriptions[target] || "");
    });
});

document.querySelectorAll("[data-sample-claim]").forEach((sample) => {
    sample.addEventListener("click", () => {
        messageInput.value = sample.dataset.sampleClaim || "";
        messageInput.focus();
    });
});

fileInput.addEventListener("change", () => showImagePreview(fileInput.files[0]));
["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.add("is-dragging");
    });
});
["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.remove("is-dragging");
    });
});
dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
    showImagePreview(file);
});

if (heroAction) {
    heroAction.addEventListener("click", () => {
        window.setTimeout(() => messageInput.focus(), 0);
    });
}

function addTextElement(parent, tag, text, className = "") {
    const element = document.createElement(tag);
    element.textContent = text;

    if (className) {
        element.className = className;
    }

    parent.appendChild(element);
    return element;
}

function uniqueItems(items, keyFor) {
    const seen = new Set();
    return items.filter((item) => {
        const key = keyFor(item);
        if (!key || seen.has(key)) {
            return false;
        }
        seen.add(key);
        return true;
    });
}

function localizeSourceRetrievalStatus(status) {
    const keys = {
        retrieved: "sourceRetrieved",
        blocked_destination: "sourceRetrievalBlocked",
        invalid_url: "sourceRetrievalBlocked",
        unsupported_scheme: "sourceRetrievalBlocked",
        tls_error: "sourceRetrievalFailed",
        timeout: "sourceRetrievalTimeout",
        too_large: "sourceRetrievalTooLarge",
        unsupported_content_type: "sourceRetrievalUnsupported",
        unsupported_content_encoding: "sourceRetrievalUnsupported",
        not_attempted_limit: "sourceRetrievalNotAttempted"
    };
    return t(keys[status] || "sourceRetrievalOther");
}

function localizeEvidenceStatus(status) {
    const keys = {
        Supports: "evidenceSupports",
        Contradicts: "evidenceContradicts",
        Contextualizes: "evidenceContextualizes",
        "Does Not Address": "evidenceDoesNotAddress",
        "Insufficient Information": "evidenceInsufficient",
        "Retrieval Failed": "evidenceRetrievalFailed"
    };
    return t(keys[status] || "evidenceInsufficient");
}

function localizeVerdictCategory(categoryCode) {
    const keys = {
        supported: "verdictSupported",
        mostly_true: "verdictMostlyTrue",
        misleading: "verdictMisleading",
        mostly_false: "verdictMostlyFalse",
        false: "verdictFalse",
        not_factual: "verdictNotFactual",
        unverified: "verdictUnverified"
    };
    return keys[categoryCode] ? t(keys[categoryCode]) : t("verdictUnverified");
}

function addVerdictEvidenceGroup(container, headingKey, evidence) {
    if (!Array.isArray(evidence) || evidence.length === 0) {
        return;
    }
    addTextElement(container, "h5", t(headingKey));
    evidence.forEach((item) => {
        if (!item || typeof item !== "object") {
            return;
        }
        let safeUrl;
        try {
            safeUrl = new URL(item.url);
        } catch (_error) {
            return;
        }
        if (
            !["http:", "https:"].includes(safeUrl.protocol)
            || safeUrl.username
            || safeUrl.password
            || typeof item.title !== "string"
        ) {
            return;
        }
        const link = document.createElement("a");
        link.className = "verdict-source-link";
        link.href = safeUrl.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = item.title;
        container.appendChild(link);
        if (typeof item.passage === "string" && item.passage.trim()) {
            addTextElement(
                container,
                "blockquote",
                `“${item.passage.trim()}”`
            );
        }
        if (typeof item.limitation === "string" && item.limitation.trim()) {
            addTextElement(container, "p", item.limitation);
        }
    });
}

function renderVerdictAssessment(container, item) {
    const assessment = item.verdict_assessment;
    if (!assessment || typeof assessment !== "object") {
        addTextElement(container, "p", t("verdictUnverified"), "claim-verdict");
        return;
    }
    const section = document.createElement("section");
    section.className = "verdict-assessment";
    addTextElement(
        section,
        "p",
        typeof assessment.category === "string" && assessment.category.trim()
            ? assessment.category
            : localizeVerdictCategory(assessment.category_code),
        "claim-verdict"
    );
    if (typeof assessment.explanation === "string" && assessment.explanation.trim()) {
        addTextElement(section, "p", assessment.explanation);
    }
    addTextElement(
        section,
        "p",
        t(assessment.evidence_sufficient ? "verdictSufficient" : "verdictInsufficient")
    );
    addVerdictEvidenceGroup(
        section,
        "verdictSupportHeading",
        assessment.supporting_evidence
    );
    addVerdictEvidenceGroup(
        section,
        "verdictContradictionHeading",
        assessment.contradicting_evidence
    );
    addVerdictEvidenceGroup(
        section,
        "verdictContextHeading",
        assessment.contextual_evidence
    );
    addVerdictEvidenceGroup(
        section,
        "verdictOtherHeading",
        assessment.other_evidence
    );
    addVerdictEvidenceGroup(
        section,
        "verdictFailuresHeading",
        assessment.retrieval_failures
    );
    if (Array.isArray(assessment.limitations) && assessment.limitations.length) {
        addTextElement(section, "h5", t("verdictLimitationsHeading"));
        assessment.limitations
            .filter((limitation) => typeof limitation === "string" && limitation.trim())
            .forEach((limitation) => addTextElement(section, "p", limitation));
    }
    addTextElement(section, "p", t("verdictDisclosure"));
    container.appendChild(section);
}

function renderClaims(claimsBox, claims, extractionMethod) {
    const uniqueClaims = uniqueItems(
        claims.filter((item) => item && typeof item.claim === "string"),
        (item) => item.claim.trim().toLocaleLowerCase().replace(/\s+/g, " ")
    );

    if (uniqueClaims.length === 0) {
        if (extractionMethod === "ollama_assisted") {
            addTextElement(claimsBox, "p", t("extractionMethodOllama"));
        }

        addTextElement(claimsBox, "p", t("noClaims"));
        return;
    }

    uniqueClaims.forEach((item) => {
        const card = document.createElement("article");
        card.className = "result-card";
        addTextElement(card, "h3", item.claim);
        if (item.extraction_method === "local_rules") {
            addTextElement(card, "p", t("extractionMethodLocal"));
        } else if (item.extraction_method === "ollama") {
            addTextElement(card, "p", t("extractionMethodOllama"));
        }
        if (
            typeof item.ai_assessment === "string"
            && typeof item.ai_explanation === "string"
            && item.ai_assessment.trim()
            && item.ai_explanation.trim()
        ) {
            const aiSection = document.createElement("section");
            aiSection.className = "ai-assessment";
            addTextElement(aiSection, "h4", t("aiAssessmentHeading"));
            addTextElement(aiSection, "p", item.ai_assessment.trim());
            if (typeof item.ai_provider === "string" && item.ai_provider.trim()) {
                const modelLabel = item.ai_model || (
                    item.ai_provider === "gemini" ? "gemma-4-26b-a4b-it" : "Ollama"
                );
                addTextElement(
                    aiSection,
                    "p",
                    t("aiAssessmentModel", modelLabel)
                );
            }
            addTextElement(
                aiSection,
                "p",
                `${t("aiAssessmentExplanation")} ${item.ai_explanation.trim()}`
            );
            if (typeof item.ai_limitations === "string" && item.ai_limitations.trim()) {
                addTextElement(
                    aiSection,
                    "p",
                    `${t("aiAssessmentLimitations")} ${item.ai_limitations.trim()}`
                );
            }
            const why = document.createElement("details");
            why.className = "why-assessment";
            addTextElement(why, "summary", "Why this assessment?");
            addTextElement(
                why,
                "p",
                item.ai_explanation.trim()
            );
            aiSection.appendChild(why);
            card.appendChild(aiSection);
        }
        renderVerdictAssessment(card, item);
        const searchStatusKeys = {
            not_enabled: "sourceSearchNotEnabled",
            not_configured: "sourceSearchNotConfigured",
            no_results: "sourceSearchNoResults",
            search_failed: "sourceSearchFailed",
            not_searched_limit: "sourceSearchLimited",
            not_searched_rate_limited: "sourceSearchRateLimited",
            not_searched_provider_error: "sourceSearchNotAttempted",
            not_searchable: "sourceSearchNotSearchable",
            not_factual: "sourceSearchNotFactual",
            factual_part_unclear: "sourceSearchFactualPartUnclear",
            search_completed: "sourceSearchFound"
        };
        if (searchStatusKeys[item.source_search_status]) {
            addTextElement(
                card,
                "p",
                t(searchStatusKeys[item.source_search_status])
            );
        }

        if (typeof item.original_wording === "string" && item.original_wording.trim()) {
            addTextElement(
                card,
                "p",
                `${t("originalWording")} “${item.original_wording.trim()}”`
            );
        }
        if (
            typeof item.normalized_wording === "string"
            && item.normalized_wording.trim()
            && item.normalized_wording.trim() !== item.claim.trim()
        ) {
            addTextElement(
                card,
                "p",
                `${t("normalizedWording")} ${item.normalized_wording.trim()}`
            );
        }
        if (Array.isArray(item.categories) && item.categories.length) {
            addTextElement(
                card,
                "p",
                `${t("claimTopics")} ${item.categories
                    .filter((category) => typeof category === "string")
                    .join(", ")}`
            );
        }

        if (typeof item.reason_to_check === "string" && item.reason_to_check.trim()) {
            addTextElement(card, "p", item.reason_to_check);
        }

        const sources = Array.isArray(item.sources) ? item.sources : [];
        if (sources.length) {
            addTextElement(card, "h4", t("sourceLeadsHeading"));
            sources.forEach((source) => {
                if (!source || typeof source !== "object") {
                    return;
                }
                let safeUrl;
                try {
                    safeUrl = new URL(source.url);
                } catch (_error) {
                    return;
                }
                if (
                    safeUrl.protocol !== "https:"
                    || safeUrl.username
                    || safeUrl.password
                    || typeof source.title !== "string"
                ) {
                    return;
                }
                const sourceCard = document.createElement("div");
                sourceCard.className = "source-lead";
                addTextElement(
                    sourceCard,
                    "p",
                    `${t("sourceRetrievalStatus")} ${localizeSourceRetrievalStatus(source.retrieval_status)}`
                );
                if (typeof source.provider === "string" && source.provider.trim()) {
                    addTextElement(
                        sourceCard,
                        "p",
                        `${t("sourceProvider")} ${source.provider}`
                    );
                }
                const sourceLink = document.createElement("a");
                sourceLink.href = safeUrl.href;
                sourceLink.target = "_blank";
                sourceLink.rel = "noopener noreferrer";
                sourceLink.textContent = source.title;
                sourceCard.appendChild(sourceLink);
                const sourceDetails = document.createElement("details");
                sourceDetails.className = "source-details";
                const sourceDetailsSummary = document.createElement("summary");
                sourceDetailsSummary.textContent = t("sourceDetails");
                sourceDetails.appendChild(sourceDetailsSummary);
                if (
                    typeof source.retrieved_title === "string"
                    && source.retrieved_title.trim()
                    && source.retrieved_title.trim() !== source.title.trim()
                ) {
                    addTextElement(
                        sourceDetails,
                        "p",
                        `${t("sourcePageTitle")} ${source.retrieved_title}`
                    );
                }
                if (typeof source.publisher === "string" && source.publisher.trim()) {
                    addTextElement(sourceDetails, "p", source.publisher);
                }
                if (typeof source.date === "string" && source.date.trim()) {
                    addTextElement(sourceDetails, "p", t("sourceDate", source.date));
                } else if (source.date_status === "not_provided") {
                    addTextElement(sourceDetails, "p", t("sourceDateNotProvided"));
                } else if (source.date_status === "unrecognized") {
                    addTextElement(sourceDetails, "p", t("sourceDateUnrecognized"));
                }
                if (
                    typeof source.retrieved_publication_date === "string"
                    && source.retrieved_publication_date.trim()
                ) {
                    addTextElement(
                        sourceDetails,
                        "p",
                        t("sourcePageDate", source.retrieved_publication_date)
                    );
                }
                if (
                    typeof source.retrieved_source_type === "string"
                    && source.retrieved_source_type.trim()
                ) {
                    addTextElement(
                        sourceDetails,
                        "p",
                        `${t("sourceType")} ${source.retrieved_source_type}`
                    );
                }
                if (typeof source.query === "string" && source.query.trim()) {
                    addTextElement(
                        sourceDetails,
                        "p",
                        `${t("sourceQuery")} ${source.query}`
                    );
                }
                if (typeof source.summary === "string" && source.summary.trim()) {
                    addTextElement(
                        sourceDetails,
                        "p",
                        `${t("sourceSummary")} ${source.summary}`
                    );
                }
                if (sourceDetails.childElementCount > 1) {
                    sourceCard.appendChild(sourceDetails);
                }
                addTextElement(sourceCard, "p", t("sourceRelation"));
                if (
                    typeof source.limitations === "string"
                    && source.limitations.trim()
                ) {
                    addTextElement(sourceCard, "p", source.limitations);
                } else if (source.retrieval_status === "not_retrieved") {
                    addTextElement(sourceCard, "p", t("sourceLimitations"));
                }
                const evidence = source.evidence_assessment;
                if (evidence && typeof evidence === "object") {
                    const evidenceBox = document.createElement("section");
                    evidenceBox.className = "source-evidence";
                    addTextElement(
                        evidenceBox,
                        "h5",
                        `${t("evidenceAssessmentHeading")}: ${localizeEvidenceStatus(evidence.status)}`
                    );
                    if (
                        typeof evidence.explanation === "string"
                        && evidence.explanation.trim()
                    ) {
                        addTextElement(evidenceBox, "p", evidence.explanation);
                    }
                    if (Array.isArray(evidence.passages)) {
                        evidence.passages.forEach((passage) => {
                            if (typeof passage === "string" && passage.trim()) {
                                addTextElement(
                                    evidenceBox,
                                    "blockquote",
                                    `${t("evidencePassage")} “${passage}”`
                                );
                            }
                        });
                    }
                    if (evidence.partial_content) {
                        addTextElement(evidenceBox, "p", t("partialContent"));
                    }
                    sourceCard.appendChild(evidenceBox);
                }
                card.appendChild(sourceCard);
            });
        } else {
            addTextElement(card, "p", t("noSourceLeads"));
        }

        claimsBox.appendChild(card);
    });
}

function renderGemmaContribution(claimsBox, provenance) {
    if (!provenance || typeof provenance !== "object") {
        return;
    }
    if (provenance.model_response_accepted) {
        addTextElement(claimsBox, "p", t("gemmaContribution"));
    } else if (provenance.deterministic_fallback_used) {
        addTextElement(claimsBox, "p", t("extractionFallback"));
    }
}

function renderSignals(signalsBox, signals) {
    const validSignals = signals.filter((item) =>
        item
        && typeof item.signal === "string"
        && (typeof item.evidence === "string" || Array.isArray(item.evidence))
        && typeof item.explanation === "string"
        && item.signal.trim()
        && item.explanation.trim()
    );
    const groupedSignals = new Map();
    validSignals.forEach((item) => {
        const key = item.signal.trim().toLocaleLowerCase();
        let group = groupedSignals.get(key);
        if (!group) {
            group = {
                signal: item.signal.trim(),
                evidence: [],
                explanation: item.explanation.trim()
            };
            groupedSignals.set(key, group);
        }

        const evidenceItems = Array.isArray(item.evidence)
            ? item.evidence
            : [item.evidence];
        evidenceItems.forEach((evidence) => {
            if (typeof evidence !== "string" || !evidence.trim()) {
                return;
            }
            const phrase = evidence.trim();
            if (!group.evidence.some((existing) =>
                existing.toLocaleLowerCase() === phrase.toLocaleLowerCase()
            )) {
                group.evidence.push(phrase);
            }
        });
    });
    const uniqueSignals = [...groupedSignals.values()].filter((item) => item.evidence.length > 0);

    if (uniqueSignals.length === 0) {
        addTextElement(signalsBox, "p", t("noSignals"));
        return;
    }

    uniqueSignals.forEach((item) => {
        const card = document.createElement("article");
        card.className = "result-card";
        addTextElement(card, "h3", localizeSignalName(item.signal));
        item.evidence.forEach((evidence) => {
            addTextElement(card, "p", `${t("evidencePrefix")} “${evidence}”`);
        });
        addTextElement(card, "p", item.explanation);
        signalsBox.appendChild(card);
    });
}

function renderVerificationLinks(linksBox, links) {
    const validLinks = links.filter((item) =>
        item
        && typeof item.title === "string"
        && typeof item.url === "string"
        && typeof item.description === "string"
    );
    const safeLinks = [];
    validLinks.forEach((item) => {
        try {
            const url = new URL(item.url);
            if (
                url.protocol === "https:"
                && !url.username
                && !url.password
                && !safeLinks.some((existing) => existing.url.href === url.href)
            ) {
                safeLinks.push({ item, url });
            }
        } catch (_error) {
            // Invalid URLs are ignored; they are never inserted into the page.
        }
    });

    if (safeLinks.length === 0) {
        addTextElement(
            linksBox,
            "p",
            t("noLinks")
        );
        return;
    }

    safeLinks.forEach(({ item, url }) => {
        const card = document.createElement("article");
        card.className = "verification-link";
        addTextElement(card, "h3", item.title);

        const link = document.createElement("a");
        link.href = url.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = url.href;
        card.appendChild(link);
        addTextElement(card, "p", item.description);
        linksBox.appendChild(card);
    });
}

function renderDetectedUrls(urls, urlAnalyses) {
    const container = document.getElementById("detected-urls-container");
    const list = document.getElementById("detected-urls");
    const analysisBox = document.getElementById("url-analysis");
    list.replaceChildren();
    analysisBox.replaceChildren();

    const uniqueUrls = uniqueItems(
        urls.filter((url) => typeof url === "string"),
        (url) => url.trim().toLocaleLowerCase()
    );
    uniqueUrls.forEach((url) => addTextElement(list, "li", url));
    addTextElement(analysisBox, "h3", t("urlAnalysisHeading"));
    const resultByUrl = new Map(
        (Array.isArray(urlAnalyses) ? urlAnalyses : [])
            .filter((item) => item && typeof item.url === "string")
            .map((item) => [item.url.toLocaleLowerCase(), item])
    );
    uniqueUrls.forEach((url) => {
        const urlResult = resultByUrl.get(url.toLocaleLowerCase());
        const card = document.createElement("article");
        card.className = "result-card";
        addTextElement(card, "h3", url);
        addTextElement(
            card,
            "p",
            urlResult && urlResult.valid_syntax ? t("urlValid") : t("urlInvalid")
        );
        const warnings = urlResult && Array.isArray(urlResult.warning_signals)
            ? urlResult.warning_signals
            : [];
        if (warnings.length) {
            warnings.forEach((warning) => {
                if (warning && typeof warning.explanation === "string") {
                    addTextElement(card, "p", warning.explanation);
                }
            });
        } else {
            addTextElement(card, "p", t("urlNoWarnings"));
        }
        addTextElement(card, "p", t("websiteNotChecked"));
        analysisBox.appendChild(card);
    });
    container.hidden = uniqueUrls.length === 0;
}

function renderRiskAssessment(riskAssessment) {
    const levelElement = document.getElementById("risk-level");
    const scoreElement = document.getElementById("risk-score");
    const disclaimerElement = document.getElementById("risk-disclaimer");
    const reasonsList = document.getElementById("risk-reasons");
    reasonsList.replaceChildren();

    const levels = {
        "Low Caution": { className: "risk-low", label: t("riskLow") },
        "Medium Caution": { className: "risk-medium", label: t("riskMedium") },
        "High Caution": { className: "risk-high", label: t("riskHigh") }
    };

    if (!riskAssessment || typeof riskAssessment !== "object") {
        levelElement.textContent = t("riskUnavailable");
        levelElement.className = "";
        scoreElement.textContent = "";
        addTextElement(
            reasonsList,
            "li",
            t("riskUnavailableReason")
        );
        return;
    }

    const level = levels[riskAssessment.level] || null;
    levelElement.textContent = level ? level.label : t("riskUnavailable");
    levelElement.className = level ? level.className : "";
    scoreElement.textContent =
        Number.isFinite(riskAssessment.score) && riskAssessment.score >= 0
            ? t("riskScore", riskAssessment.score)
            : t("scoreUnavailable");

    if (typeof riskAssessment.disclaimer === "string" && riskAssessment.disclaimer.trim()) {
        disclaimerElement.textContent = riskAssessment.disclaimer;
    }

    const reasons = Array.isArray(riskAssessment.reasons)
        ? riskAssessment.reasons
        : [];
    const seen = new Set();
    reasons.forEach((reason) => {
        if (!reason || typeof reason.explanation !== "string" || !reason.explanation.trim()) {
            return;
        }
        const key = reason.explanation.trim().toLocaleLowerCase();
        if (seen.has(key)) {
            return;
        }
        seen.add(key);

        const points = Number.isFinite(reason.points) && reason.points > 0
            ? ` (+${reason.points} ${currentLanguage === "hi" ? "अंक" : "points"})`
            : "";
        addTextElement(reasonsList, "li", `${reason.explanation.trim()}${points}`);
    });

    if (reasonsList.childElementCount === 0) {
        addTextElement(
            reasonsList,
            "li",
            t("noRiskReasons")
        );
    }
}

function addUniqueSpokenLine(lines, seen, text) {
    const normalized = reportText(text, 280);
    const key = normalized.toLocaleLowerCase();
    if (normalized && !seen.has(key)) {
        lines.push(normalized);
        seen.add(key);
    }
}

function buildSpokenReport(analysis) {
    const sections = [];
    const spokenLines = [t("spokenIntro")];
    const seen = new Set();
    const riskAssessment = analysis.risk_assessment;

    if (
        riskAssessment
        && typeof riskAssessment === "object"
        && ["Low Caution", "Medium Caution", "High Caution"].includes(riskAssessment.level)
    ) {
        spokenLines.push(t("spokenCaution", localizeRiskLevel(riskAssessment.level)));
        const reasons = Array.isArray(riskAssessment.reasons)
            ? riskAssessment.reasons
            : [];
        reasons.slice(0, 2).forEach((reason) => {
            if (reason && typeof reason.explanation === "string") {
                addUniqueSpokenLine(sections, seen, reason.explanation);
            }
        });
        if (sections.length) {
            spokenLines.push(t("spokenReasons", sections.join(" ")));
        }
    }
    if (typeof analysis.caution_explanation === "string" && analysis.caution_explanation.trim()) {
        spokenLines.push(analysis.caution_explanation.trim());
    }

    const claimLines = [];
    const seenClaims = new Set();
    const claims = Array.isArray(analysis.claims) ? analysis.claims : [];
    claims.forEach((claim) => {
        const text = typeof claim === "string"
            ? claim
            : claim && typeof claim.claim === "string"
                ? claim.claim
                : "";
        addUniqueSpokenLine(claimLines, seenClaims, text);
    });
    spokenLines.push(
        claimLines.length
            ? t("spokenClaims", claimLines.slice(0, 3).join(". "))
            : t("spokenNoClaims")
    );

    const warningLines = [];
    const seenWarnings = new Set();
    const groupedWarnings = new Map();
    const warnings = Array.isArray(analysis.warning_signals)
        ? analysis.warning_signals
        : [];
    warnings.forEach((warning) => {
        if (typeof warning === "string") {
            addUniqueSpokenLine(warningLines, seenWarnings, warning);
            return;
        }
        if (!warning || typeof warning !== "object") {
            return;
        }

        const signal = reportText(warning.signal, 120);
        const explanation = reportText(warning.explanation, 260);
        const key = (signal || explanation).toLocaleLowerCase();
        if (!key) {
            return;
        }
        let group = groupedWarnings.get(key);
        if (!group) {
            group = { signal, explanations: [] };
            groupedWarnings.set(key, group);
        }
        if (
            explanation
            && !group.explanations.some(
                (existing) => existing.toLocaleLowerCase() === explanation.toLocaleLowerCase()
            )
        ) {
            group.explanations.push(explanation);
        }
    });
    groupedWarnings.forEach((group) => {
        const line = [
            group.signal,
            group.explanations.join(" ")
        ].filter(Boolean).join(": ");
        addUniqueSpokenLine(warningLines, seenWarnings, line);
    });
    spokenLines.push(
        warningLines.length
            ? t("spokenWarnings", warningLines.slice(0, 3).join(". "))
            : t("spokenNoWarnings")
    );

    const stepLines = [];
    const seenSteps = new Set();
    const steps = Array.isArray(analysis.verification_steps)
        ? analysis.verification_steps
        : [];
    steps.forEach((step) => addUniqueSpokenLine(stepLines, seenSteps, step));
    if (stepLines.length) {
        spokenLines.push(t("spokenSteps", stepLines.slice(0, 4).join(". ")));
    }

    spokenLines.push(
        t("noSpeechReport")
    );
    const spokenReport = spokenLines.join(" ");
    return spokenReport.length <= MAX_SPOKEN_REPORT_LENGTH
        ? spokenReport
        : `${spokenReport.slice(0, MAX_SPOKEN_REPORT_LENGTH - 3).trimEnd()}...`;
}

function localizeRiskLevel(level) {
    const keys = {
        "Low Caution": "riskLow",
        "Medium Caution": "riskMedium",
        "High Caution": "riskHigh"
    };
    return keys[level] ? t(keys[level]) : t("riskUnavailable");
}

function speechIsSupported() {
    return (
        typeof window.speechSynthesis !== "undefined"
        && typeof window.SpeechSynthesisUtterance === "function"
    );
}

function resetSpeechControls(statusMessage = "") {
    currentUtterance = null;
    pauseSpeechButton.textContent = t("pauseSpeech");
    pauseSpeechButton.setAttribute("aria-pressed", "false");
    pauseSpeechButton.disabled = true;
    stopSpeechButton.disabled = true;
    speechStatus.textContent = statusMessage;
}

function stopCurrentSpeech(statusMessage = "") {
    if (speechIsSupported()) {
        window.speechSynthesis.cancel();
    }
    resetSpeechControls(statusMessage);
}

function startReportSpeech() {
    if (!currentSpeechText) {
        speechStatus.textContent = t("noReportRead");
        return;
    }
    if (!speechIsSupported()) {
        speechStatus.textContent =
            t("speechUnsupported");
        return;
    }

    stopCurrentSpeech();
    try {
        const utterance = new window.SpeechSynthesisUtterance(currentSpeechText);
        utterance.lang = currentLanguage === "hi" ? "hi-IN" : "en-IN";
        currentUtterance = utterance;
        pauseSpeechButton.disabled = false;
        stopSpeechButton.disabled = false;
        pauseSpeechButton.textContent = t("pauseSpeech");
        pauseSpeechButton.setAttribute("aria-pressed", "false");

        utterance.onstart = () => {
            if (currentUtterance === utterance) {
                speechStatus.textContent = t("reading");
            }
        };
        utterance.onend = () => {
            if (currentUtterance === utterance) {
                resetSpeechControls(t("finishedReading"));
            }
        };
        utterance.onerror = () => {
            if (currentUtterance === utterance) {
                resetSpeechControls(
                    t("speechError")
                );
            }
        };

        speechStatus.textContent = t("speechStarting");
        window.speechSynthesis.speak(utterance);
    } catch (_error) {
        stopCurrentSpeech(
            t("speechStartError")
        );
    }
}

function toggleReportSpeech() {
    if (!speechIsSupported() || !currentUtterance) {
        speechStatus.textContent = speechIsSupported()
            ? t("startBeforePause")
            : t("speechUnsupported");
        return;
    }

    if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
        pauseSpeechButton.textContent = t("pauseSpeech");
        pauseSpeechButton.setAttribute("aria-pressed", "false");
        speechStatus.textContent = t("speechResumed");
    } else if (window.speechSynthesis.speaking) {
        window.speechSynthesis.pause();
        pauseSpeechButton.textContent = t("resumeSpeech");
        pauseSpeechButton.setAttribute("aria-pressed", "true");
        speechStatus.textContent = t("speechPaused");
    }
}

function reportText(value, maxLength) {
    if (typeof value !== "string") {
        return "";
    }

    const normalized = value.replace(/\s+/g, " ").trim();
    if (normalized.length <= maxLength) {
        return normalized;
    }
    return `${normalized.slice(0, maxLength - 3).trimEnd()}...`;
}

function createShareReport(analysis, metadata = {}) {
    const lines = [
        t("reportTitle"),
        t("reportIntro")
    ];
    if (typeof metadata.analysis_scope === "string" && metadata.analysis_scope.trim()) {
        lines.push("", t("scopeHeading"), metadata.analysis_scope.trim());
    }
    const provenance = analysis.gemma_provenance;
    if (provenance && typeof provenance === "object") {
        lines.push(
            "",
            provenance.model_response_accepted
                ? t("gemmaContribution")
                : provenance.deterministic_fallback_used
                    ? t("extractionFallback")
                    : ""
        );
    }

    const urlAnalyses = Array.isArray(metadata.url_analysis)
        ? metadata.url_analysis
        : [];
    if (urlAnalyses.length) {
        lines.push("", t("urlAnalysisHeading"));
        urlAnalyses.forEach((item) => {
            if (!item || typeof item.url !== "string") {
                return;
            }
            lines.push(`- ${item.url}`);
            const warnings = Array.isArray(item.warning_signals)
                ? item.warning_signals
                : [];
            if (warnings.length) {
                warnings.forEach((warning) => {
                    if (warning && typeof warning.explanation === "string") {
                        lines.push(`  ${warning.explanation}`);
                    }
                });
            } else {
                lines.push(`  ${t("urlNoWarnings")}`);
            }
            lines.push(`  ${t("websiteNotChecked")}`);
        });
    }

    const riskAssessment = analysis.risk_assessment;
    if (
        riskAssessment
        && typeof riskAssessment === "object"
        && ["Low Caution", "Medium Caution", "High Caution"].includes(riskAssessment.level)
    ) {
        const score = Number.isFinite(riskAssessment.score) && riskAssessment.score >= 0
            ? ` (${t("scoreLabel", riskAssessment.score)})`
            : "";
        lines.push(t("reportCaution", localizeRiskLevel(riskAssessment.level), score));
    }
    if (typeof analysis.caution_explanation === "string" && analysis.caution_explanation.trim()) {
        lines.push("", analysis.caution_explanation.trim());
    }
    if (
        analysis.evidence_status
        && typeof analysis.evidence_status.message === "string"
        && analysis.evidence_status.message.trim()
    ) {
        lines.push("", t("reportEvidenceStatus"), analysis.evidence_status.message.trim());
    }

    const claims = uniqueItems(
        (Array.isArray(analysis.claims) ? analysis.claims : [])
            .map((item) => {
                if (typeof item === "string") {
                    return {
                        claim: reportText(item, 320),
                        reason: "",
                        original: "",
                        normalized: "",
                        categories: [],
                        extractionMethodMessage: "",
                        sources: [],
                        verdictAssessment: null
                    };
                }
                if (!item || typeof item.claim !== "string") {
                    return null;
                }
                return {
                    claim: reportText(item.claim, 320),
                    reason: reportText(item.reason_to_check, 320),
                    original: reportText(item.original_wording, 320),
                    normalized: reportText(item.normalized_wording, 320),
                    categories: Array.isArray(item.categories)
                        ? item.categories.filter((value) => typeof value === "string").slice(0, 5)
                        : [],
                    extractionMethodMessage: item.extraction_method === "local_rules"
                        ? "extractionMethodLocal"
                        : item.extraction_method === "ollama"
                            ? "extractionMethodOllama"
                            : "",
                    aiAssessment: reportText(item.ai_assessment, 80),
                    aiExplanation: reportText(item.ai_explanation, 500),
                    aiLimitations: reportText(item.ai_limitations, 300),
                    aiProvider: reportText(item.ai_provider, 80),
                    aiModel: reportText(item.ai_model, 120),
                    sources: Array.isArray(item.sources) ? item.sources.slice(0, 3) : [],
                    verdictAssessment: (
                        item.verdict_assessment
                        && typeof item.verdict_assessment === "object"
                    )
                        ? item.verdict_assessment
                        : null
                };
            })
            .filter((item) => item && item.claim),
        (item) => item.claim.toLocaleLowerCase()
    ).slice(0, 6);
    lines.push("", t("reportClaimsHeading"), t("verdictDisclosure"));
    if (claims.length) {
        claims.forEach((item) => {
            lines.push(`- ${item.claim}`);
            if (item.original) {
                lines.push(`  ${t("originalWording")} “${item.original}”`);
            }
            if (item.normalized && item.normalized !== item.claim) {
                lines.push(`  ${t("normalizedWording")} ${item.normalized}`);
            }
            if (item.categories.length) {
                lines.push(`  ${t("claimTopics")} ${item.categories.join(", ")}`);
            }
            if (item.extractionMethodMessage) {
                lines.push(`  ${t(item.extractionMethodMessage)}`);
            }
            if (item.aiAssessment && item.aiExplanation) {
                lines.push(`  ${t("aiAssessmentHeading")}: ${item.aiAssessment}`);
                if (item.aiModel || item.aiProvider) {
                    lines.push(
                        `  ${t("aiAssessmentModel", item.aiModel || item.aiProvider)}`
                    );
                }
                lines.push(`  ${t("aiAssessmentExplanation")} ${item.aiExplanation}`);
                if (item.aiLimitations) {
                    lines.push(`  ${t("aiAssessmentLimitations")} ${item.aiLimitations}`);
                }
            }
            const verdict = item.verdictAssessment;
            lines.push(
                `  ${verdict && typeof verdict.category === "string"
                    ? verdict.category
                    : localizeVerdictCategory("unverified")}`
            );
            if (verdict && typeof verdict.explanation === "string") {
                lines.push(`  ${reportText(verdict.explanation, 500)}`);
                lines.push(
                    `  ${t(verdict.evidence_sufficient ? "verdictSufficient" : "verdictInsufficient")}`
                );
                const evidenceGroups = [
                    ["verdictSupportHeading", verdict.supporting_evidence],
                    ["verdictContradictionHeading", verdict.contradicting_evidence],
                    ["verdictContextHeading", verdict.contextual_evidence],
                    ["verdictOtherHeading", verdict.other_evidence],
                    ["verdictFailuresHeading", verdict.retrieval_failures]
                ];
                evidenceGroups.forEach(([headingKey, references]) => {
                    if (!Array.isArray(references) || references.length === 0) {
                        return;
                    }
                    lines.push(`  ${t(headingKey)}:`);
                    references.forEach((reference) => {
                        if (!reference || typeof reference !== "object") {
                            return;
                        }
                        const title = reportText(reference.title, 160);
                        const url = reportText(reference.url, 300);
                        if (title && url) {
                            lines.push(`    - ${title} (${url})`);
                        }
                        if (typeof reference.passage === "string" && reference.passage.trim()) {
                            lines.push(
                                `      ${t("evidencePassage")} “${reportText(reference.passage, 500)}”`
                            );
                        }
                        if (typeof reference.limitation === "string" && reference.limitation.trim()) {
                            lines.push(`      ${reportText(reference.limitation, 300)}`);
                        }
                    });
                });
                if (Array.isArray(verdict.limitations)) {
                    verdict.limitations
                        .filter((limitation) => typeof limitation === "string" && limitation.trim())
                        .forEach((limitation) => {
                            lines.push(
                                `  ${t("verdictLimitationsHeading")}: ${reportText(limitation, 300)}`
                            );
                        });
                }
            }
            if (item.reason) {
                lines.push(`  ${item.reason}`);
            }
            item.sources.forEach((source) => {
                if (!source || typeof source !== "object") {
                    return;
                }
                const url = typeof source.url === "string"
                    ? reportText(source.url, 300)
                    : "";
                const title = typeof source.title === "string"
                    ? reportText(source.title, 160)
                    : "";
                if (!url || !title) {
                    return;
                }
                lines.push(`  - ${t("sourceLeadsHeading")}: ${title} (${url})`);
                lines.push(
                    `    ${t("sourceRetrievalStatus")} ${localizeSourceRetrievalStatus(source.retrieval_status)}`
                );
                if (typeof source.summary === "string" && source.summary.trim()) {
                    lines.push(`    ${t("sourceSummary")} ${reportText(source.summary, 300)}`);
                }
                if (typeof source.publisher === "string" && source.publisher.trim()) {
                    lines.push(`    ${reportText(source.publisher, 180)}`);
                }
                if (typeof source.provider === "string" && source.provider.trim()) {
                    lines.push(`    ${t("sourceProvider")} ${reportText(source.provider, 100)}`);
                }
                if (typeof source.date === "string" && source.date.trim()) {
                    lines.push(`    ${t("sourceDate", source.date)}`);
                } else if (source.date_status === "not_provided") {
                    lines.push(`    ${t("sourceDateNotProvided")}`);
                } else if (source.date_status === "unrecognized") {
                    lines.push(`    ${t("sourceDateUnrecognized")}`);
                }
                if (
                    typeof source.retrieved_title === "string"
                    && source.retrieved_title.trim()
                    && source.retrieved_title.trim() !== title
                ) {
                    lines.push(
                        `    ${t("sourcePageTitle")} ${reportText(source.retrieved_title, 160)}`
                    );
                }
                if (
                    typeof source.retrieved_publication_date === "string"
                    && source.retrieved_publication_date.trim()
                ) {
                    lines.push(
                        `    ${t("sourcePageDate", reportText(source.retrieved_publication_date, 40))}`
                    );
                }
                if (
                    typeof source.retrieved_source_type === "string"
                    && source.retrieved_source_type.trim()
                ) {
                    lines.push(
                        `    ${t("sourceType")} ${reportText(source.retrieved_source_type, 100)}`
                    );
                }
                if (typeof source.query === "string" && source.query.trim()) {
                    lines.push(`    ${t("sourceQuery")} ${reportText(source.query, 300)}`);
                }
                lines.push(`    ${t("sourceRelation")}`);
                if (
                    typeof source.limitations === "string"
                    && source.limitations.trim()
                ) {
                    lines.push(`    ${reportText(source.limitations, 300)}`);
                }
                const evidence = source.evidence_assessment;
                if (evidence && typeof evidence === "object") {
                    lines.push(
                        `    ${t("evidenceAssessmentHeading")}: ${localizeEvidenceStatus(evidence.status)}`
                    );
                    if (typeof evidence.explanation === "string" && evidence.explanation.trim()) {
                        lines.push(`    ${reportText(evidence.explanation, 300)}`);
                    }
                    if (Array.isArray(evidence.passages)) {
                        evidence.passages.forEach((passage) => {
                            if (typeof passage === "string" && passage.trim()) {
                                lines.push(
                                    `    ${t("evidencePassage")} “${reportText(passage, 500)}”`
                                );
                            }
                        });
                    }
                    if (evidence.partial_content) {
                        lines.push(`    ${t("partialContent")}`);
                    }
                }
            });
        });
    } else {
        if (analysis.extraction_method === "local_rules") {
            lines.push(t("extractionFallback"));
        } else if (analysis.extraction_method === "ollama_assisted") {
            lines.push(t("extractionMethodOllama"));
        }
        lines.push(t("reportNoClaims"));
    }

    const warningItems = Array.isArray(analysis.warning_signals)
        ? analysis.warning_signals
        : [];
    const warningLines = [];
    const seenWarnings = new Set();
    warningItems.forEach((item) => {
        if (typeof item === "string") {
            const signal = reportText(item, 160);
            if (signal && !seenWarnings.has(signal.toLocaleLowerCase())) {
                warningLines.push(`- ${signal}`);
                seenWarnings.add(signal.toLocaleLowerCase());
            }
            return;
        }
        if (!item || typeof item !== "object") {
            return;
        }

        const signal = reportText(item.signal, 160);
        const explanation = reportText(item.explanation, 320);
        const evidenceItems = Array.isArray(item.evidence)
            ? item.evidence
            : [item.evidence];
        const evidence = uniqueItems(
            evidenceItems
                .filter((entry) => typeof entry === "string")
                .map((entry) => reportText(entry, 120)),
            (entry) => entry.toLocaleLowerCase()
        ).slice(0, 3);

        if (!signal && !explanation) {
            return;
        }
        const key = `${signal.toLocaleLowerCase()}|${explanation.toLocaleLowerCase()}`;
        if (seenWarnings.has(key)) {
            return;
        }
        seenWarnings.add(key);

        let line = `- ${localizeSignalName(signal) || t("reportWarning")}`;
        if (explanation) {
            line += `: ${explanation}`;
        }
        if (evidence.length) {
            line += ` (${t("reportEvidence")}${evidence.map((entry) => `“${entry}”`).join("; ")})`;
        }
        warningLines.push(line);
    });

    lines.push("", t("reportWarningHeading"));
    if (warningLines.length) {
        lines.push(...warningLines.slice(0, 6));
    } else {
        lines.push(
            t("reportNoWarnings")
        );
    }

    const steps = uniqueItems(
        (Array.isArray(analysis.verification_steps) ? analysis.verification_steps : [])
            .filter((step) => typeof step === "string")
            .map((step) => reportText(step, 320)),
        (step) => step.toLocaleLowerCase()
    ).slice(0, 6);
    lines.push("", t("reportStepsHeading"));
    if (steps.length) {
        steps.forEach((step) => lines.push(`- ${step}`));
    } else {
        lines.push(t("reportNoSteps"));
    }

    const links = uniqueItems(
        (Array.isArray(analysis.verification_links) ? analysis.verification_links : [])
            .filter((link) =>
                link
                && typeof link.title === "string"
                && typeof link.url === "string"
            )
            .map((link) => ({
                title: reportText(link.title, 120),
                url: reportText(link.url, 300)
            }))
            .filter((link) => link.title && link.url),
        (link) => `${link.title.toLocaleLowerCase()}|${link.url.toLocaleLowerCase()}`
    ).slice(0, 6);
    lines.push("", t("reportLinksHeading"));
    if (links.length) {
        links.forEach((link) => lines.push(`- ${link.title}: ${link.url}`));
    } else {
        lines.push(t("reportNoLinks"));
    }

    lines.push("", t("disclaimer"));
    const report = lines.join("\n");
    if (report.length <= MAX_REPORT_LENGTH) {
        return report;
    }
    const reportDisclaimer = t("disclaimer");
    return `${report.slice(0, MAX_REPORT_LENGTH - reportDisclaimer.length - 2).trimEnd()}\n\n${reportDisclaimer}`;
}

function resetShareReport() {
    shareReportText.value = "";
    shareReportStatus.textContent = "";
    copyReportButton.disabled = true;
    shareReportButton.disabled = true;
}

async function copyReportToClipboard() {
    const report = shareReportText.value;
    if (!report) {
        shareReportStatus.textContent = t("shareNoReport");
        return false;
    }

    try {
        if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
            await navigator.clipboard.writeText(report);
        } else {
            const temporaryField = document.createElement("textarea");
            temporaryField.value = report;
            temporaryField.setAttribute("readonly", "");
            temporaryField.style.position = "fixed";
            temporaryField.style.opacity = "0";
            document.body.appendChild(temporaryField);
            temporaryField.select();
            const copied = document.execCommand("copy");
            temporaryField.remove();
            if (!copied) {
                throw new Error("Clipboard access is unavailable.");
            }
        }
        return true;
    } catch (_error) {
        shareReportStatus.textContent =
            t("copyError");
        return false;
    }
}

async function submitAnalysis(formData, progressMessage) {
    formData.set("language", currentLanguage);
    formData.set(
        "source_search_enabled",
        sourceSearchCheckbox.checked ? "true" : "false"
    );
    uploadButton.disabled = true;
    textButton.disabled = true;
    statusText.textContent = progressMessage;
    statusText.classList.add("loading");
    statusText.setAttribute("aria-busy", "true");
    const finishProgress = startProgress(
        formData.get("source_type") === "image" ? "image" : "text",
        sourceSearchCheckbox.checked
    );
    stopCurrentSpeech();
    currentSpeechText = "";
    readReportButton.disabled = true;
    correctedTextButton.disabled = true;
    resetShareReport();
    results.hidden = true;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(
        () => controller.abort(),
        ANALYSIS_TIMEOUT_MS
    );

    try {
        let response;
        try {
            response = await fetch(analysisEndpoint, {
                method: "POST",
                body: formData,
                signal: controller.signal
            });
        } catch (error) {
            if (error && error.name === "AbortError") {
                throw error;
            }
            throw new Error(t("networkError"));
        }

        let data;
        try {
            data = await response.json();
        } catch (_error) {
            if (response.status >= 500) {
                throw new Error(t("serverError", response.status));
            }
            throw new Error(t("invalidJsonResponse"));
        }

        if (!response.ok) {
            if (response.status >= 500) {
                throw new Error(t("serverError", response.status));
            }
            const detail = data && typeof data.error === "string"
                ? localizeServerError(data.error)
                : t("serverErrorDetail");
            throw new Error(t("httpError", response.status, detail));
        }

        const analysis = data && data.analysis;
        if (
            !data
            || typeof data !== "object"
            || Array.isArray(data)
            || typeof data.extracted_text !== "string"
            || typeof data.analysis_scope !== "string"
            || !["text", "image"].includes(data.source_type)
            || !analysis
            || !Array.isArray(analysis.claims)
            || !Array.isArray(analysis.warning_signals)
            || !Array.isArray(analysis.verification_steps)
            || !Array.isArray(analysis.verification_links)
            || typeof analysis.caution_explanation !== "string"
            || !analysis.risk_assessment
            || typeof analysis.risk_assessment !== "object"
            || !["Low Caution", "Medium Caution", "High Caution"].includes(
                analysis.risk_assessment.level
            )
            || !Number.isFinite(analysis.risk_assessment.score)
            || !Array.isArray(analysis.risk_assessment.reasons)
            || !Array.isArray(data.detected_urls)
            || !Array.isArray(data.url_analysis)
        ) {
            throw new Error(t("missingResults"));
        }

        document.getElementById("extracted-text").value =
            typeof data.extracted_text === "string" ? data.extracted_text : "";
        lastAnalyzedText = typeof data.extracted_text === "string" ? data.extracted_text : "";
        lastSourceType = data.source_type === "image" ? "image" : "text";
        renderDetectedUrls(data.detected_urls, data.url_analysis);
        document.getElementById("analysis-scope").textContent =
            typeof data.analysis_scope === "string" ? data.analysis_scope : "";

        const claimsBox = document.getElementById("claims");
        const signalsBox = document.getElementById("signals");
        const stepsBox = document.getElementById("verification-steps");
        const linksBox = document.getElementById("verification-links");
        const evidenceStatusElement = document.getElementById("evidence-status");
        claimsBox.replaceChildren();
        signalsBox.replaceChildren();
        stepsBox.replaceChildren();
        linksBox.replaceChildren();

        renderClaims(claimsBox, analysis.claims, analysis.extraction_method);
        updateSessionStats(
            analysis.claims.filter((item) => item && typeof item.claim === "string").length,
            lastSourceType,
            data.language || currentLanguage
        );
        renderGemmaContribution(claimsBox, analysis.gemma_provenance);
        evidenceStatusElement.textContent =
            analysis.evidence_status && typeof analysis.evidence_status.message === "string"
                ? analysis.evidence_status.message
                : "";
        renderSignals(signalsBox, analysis.warning_signals);
        renderRiskAssessment(analysis.risk_assessment);
        document.getElementById("caution-explanation").textContent =
            typeof analysis.caution_explanation === "string"
                ? analysis.caution_explanation
                : "";
        uniqueItems(
            analysis.verification_steps.filter((step) => typeof step === "string"),
            (step) => step.trim().toLocaleLowerCase()
        ).forEach((step) => addTextElement(stepsBox, "li", step));
        renderVerificationLinks(linksBox, analysis.verification_links);

        document.getElementById("disclaimer").textContent =
            typeof analysis.disclaimer === "string" && analysis.disclaimer.trim()
                ? analysis.disclaimer
                : t("disclaimer");

        shareReportText.value = createShareReport(analysis, data);
        currentSpeechText = buildSpokenReport(analysis);
        readReportButton.disabled = false;
        correctedTextButton.disabled = false;
        copyReportButton.disabled = false;
        shareReportButton.disabled = false;
        results.hidden = false;
        statusText.textContent = t("completed");
    } catch (error) {
        lastAnalyzedText = "";
        lastSourceType = "text";
        if (error && error.name === "AbortError") {
            statusText.textContent = t("requestTimeout");
        } else {
            statusText.textContent =
                error instanceof Error ? error.message : t("analysisFailed");
        }
    } finally {
        finishProgress();
        window.clearTimeout(timeoutId);
        statusText.classList.remove("loading");
        statusText.removeAttribute("aria-busy");
        uploadButton.disabled = false;
        textButton.disabled = false;
        if (languageChangePending) {
            languageChangePending = false;
            if (!results.hidden && lastAnalyzedText) {
                const formData = new FormData();
                formData.append("message", document.getElementById("extracted-text").value);
                formData.append("source_type", lastSourceType);
                submitAnalysis(formData, t("analysing"));
            }
        }
    }
}

copyReportButton.addEventListener("click", async () => {
    if (await copyReportToClipboard()) {
        shareReportStatus.textContent = t("clipboardCopied");
    }
});

shareReportButton.addEventListener("click", async () => {
    const report = shareReportText.value;
    if (!report) {
        shareReportStatus.textContent = t("shareNoReport");
        return;
    }

    if (typeof navigator.share !== "function") {
        if (await copyReportToClipboard()) {
            shareReportStatus.textContent =
                t("sharingUnavailableCopied");
        }
        return;
    }

    try {
        await navigator.share({
            title: t("reportTitle"),
            text: report
        });
        shareReportStatus.textContent = t("reportShared");
    } catch (error) {
        if (error && error.name === "AbortError") {
            shareReportStatus.textContent = t("shareCancelled");
            return;
        }
        if (await copyReportToClipboard()) {
            shareReportStatus.textContent =
                t("sharingFailedCopied");
        }
    }
});

readReportButton.addEventListener("click", startReportSpeech);
pauseSpeechButton.addEventListener("click", toggleReportSpeech);
stopSpeechButton.addEventListener("click", () => {
    stopCurrentSpeech(t("speechStopped"));
});

mediaChecklistButton.addEventListener("click", () => {
    const isExpanded = mediaChecklistButton.getAttribute("aria-expanded") === "true";
    mediaChecklistButton.setAttribute("aria-expanded", String(!isExpanded));
    mediaChecklist.hidden = isExpanded;
});

textForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (!message) {
        statusText.textContent = t("pasteMissing");
        messageInput.focus();
        return;
    }

    const formData = new FormData();
    formData.append("message", message);
    submitAnalysis(formData, t("analysing"));
});

uploadForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
        statusText.textContent = t("uploadMissing");
        fileInput.focus();
        return;
    }

    const formData = new FormData();
    formData.append("image", file);
    submitAnalysis(formData, t("extracting"));
});

languageSelect.addEventListener("change", () => {
    currentLanguage = languageSelect.value;
    applyUiLanguage();
    stopCurrentSpeech();

    if (uploadButton.disabled || textButton.disabled) {
        languageChangePending = true;
        return;
    }

    if (!results.hidden && lastAnalyzedText) {
        const formData = new FormData();
        formData.append("message", document.getElementById("extracted-text").value);
        formData.append("source_type", lastSourceType);
        submitAnalysis(formData, t("analysing"));
        return;
    }

    statusText.textContent = t("languageSwitched");
});

correctedTextButton.addEventListener("click", () => {
    const correctedText = document.getElementById("extracted-text").value;
    if (!correctedText.trim()) {
        statusText.textContent = t("pasteMissing");
        return;
    }
    const formData = new FormData();
    formData.append("message", correctedText);
    formData.append("source_type", lastSourceType);
    submitAnalysis(formData, t("analysing"));
});

applyUiLanguage();
