import re
from collections.abc import Callable

from modules.claim_extractor import extract_claims
from modules.risk_assessor import calculate_risk
from modules.source_checker import discover_claim_sources
from modules.url_analyzer import analyze_url


_URL_PATTERN = re.compile(
    r"""(?i)(?:\b(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>'"]+|"""
    r"""(?<![@\w])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"""
    r"""(?:[a-z]{2,})(?::\d+)?(?:/[^\s<>'"]*)?)"""
)
_TRAILING_PUNCTUATION = ".,!?;:)]}"
_LANGUAGES = {"en", "hi", "hinglish"}
_CLAIM_DISCLAIMERS = {
    "en": "Forward Check helps you investigate claims. It does not independently establish whether a message is true or false.",
    "hi": "Forward Check दावों की जाँच में मदद करता है। यह अपने आप किसी संदेश को सही या गलत साबित नहीं करता।",
    "hinglish": "Forward Check claims ki jaanch mein madad karta hai. Yeh apne aap kisi message ko sahi ya galat prove nahi karta."
}
_MESSAGES = {
    "en": {
        "url_only_claims": "No page claims were extracted because the website was not opened.",
        "url_only_steps": [
            "Check the domain using an independently found official source.",
            "Open the website only if you trust the source and understand the destination.",
            "Do not enter passwords, OTPs, or payment details from a forwarded link."
        ],
        "text_scope": "The submitted text and visible URL formatting were analysed. No website content was fetched and no independent fact-check was performed.",
        "image_scope": "Text was extracted from the uploaded image using OCR, then analysed. The image itself was not authenticated and URL destinations were not opened.",
        "url_scope": "Only visible URL formatting was analysed. The website contents and any claims on the page were not checked."
    },
    "hi": {
        "url_only_claims": "वेबसाइट नहीं खोली गई, इसलिए उसके पेज के दावे नहीं निकाले गए।",
        "url_only_steps": [
            "किसी स्वतंत्र रूप से खोजे गए आधिकारिक स्रोत से domain की जाँच करें।",
            "गंतव्य समझने और स्रोत पर भरोसा होने पर ही वेबसाइट खोलें।",
            "फॉरवर्ड लिंक से पासवर्ड, OTP या भुगतान जानकारी न भरें।"
        ],
        "text_scope": "दिए गए पाठ और URL के दिखने वाले format की जाँच हुई। वेबसाइट का content नहीं लिया गया और स्वतंत्र fact-check नहीं हुआ।",
        "image_scope": "अपलोड की गई image से OCR द्वारा पाठ निकाला और जाँचा गया। image की प्रामाणिकता नहीं जाँची गई और URL नहीं खोले गए।",
        "url_scope": "केवल URL का दिखने वाला format जाँचा गया। वेबसाइट की सामग्री और उसके दावों की जाँच नहीं हुई।"
    },
    "hinglish": {
        "url_only_claims": "Website open nahi hui, isliye page ke claims extract nahi kiye gaye.",
        "url_only_steps": [
            "Kisi independently dhoondhe official source se domain check karein.",
            "Destination samajh aaye aur source par bharosa ho tabhi website open karein.",
            "Forwarded link se password, OTP ya payment details na daalein."
        ],
        "text_scope": "Diye gaye text aur URL ke visible format ko analyse kiya. Website content fetch nahi hua aur independent fact-check nahi hua.",
        "image_scope": "Uploaded image se OCR ke zariye text nikala aur analyse kiya. Image authenticate nahi hui aur URL open nahi hue.",
        "url_scope": "Sirf URL ka visible format analyse hua. Website content aur page ke claims check nahi hue."
    }
}
_URL_ONLY_DISCLAIMERS = {
    "en": "This score reflects visible warning signs only. It is not a probability of fraud and does not verify claims or website safety.",
    "hi": "यह अंक केवल दिखने वाले चेतावनी संकेत बताता है। यह धोखाधड़ी की संभावना नहीं है और दावों या वेबसाइट की सुरक्षा की पुष्टि नहीं करता।",
    "hinglish": "Yeh score sirf visible warning signals batata hai. Yeh fraud ki probability nahi aur claims ya website safety verify nahi karta."
}


def find_urls(text):
    """Extract unique URL-like strings without opening or normalizing them."""
    urls = []
    seen = set()
    for match in _URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(_TRAILING_PUNCTUATION)
        key = url.casefold()
        if url and key not in seen:
            urls.append(url)
            seen.add(key)
    return urls


def classify_input(text, source_type="text"):
    if source_type == "image":
        return "image"
    urls = find_urls(text)
    if not urls:
        return "text"

    remaining_text = _URL_PATTERN.sub(" ", text)
    remaining_text = re.sub(
        r"(?i)\b(?:and|or|aur)\b|और|[\s,;|&]+",
        "",
        remaining_text
    )
    return "url" if not remaining_text else "text"


def _merge_url_warnings(analysis, url_analyses):
    merged = []
    seen = set()
    for signal in analysis.get("warning_signals", []):
        if not isinstance(signal, dict):
            continue
        key = (
            str(signal.get("signal", "")).casefold(),
            tuple(str(item).casefold() for item in signal.get("evidence", []))
            if isinstance(signal.get("evidence"), list)
            else str(signal.get("evidence", "")).casefold()
        )
        if key not in seen:
            merged.append(signal)
            seen.add(key)

    for url_result in url_analyses:
        for signal in url_result["warning_signals"]:
            key = (
                signal["signal"].casefold(),
                tuple(item.casefold() for item in signal["evidence"])
            )
            if key not in seen:
                merged.append(signal)
                seen.add(key)
    return merged


def analyze_message(
    message_text,
    language="en",
    source_type="text",
    claim_analyzer: Callable | None = None,
    source_search_enabled=False
):
    """Analyse text/OCR and discover claim sources without opening submitted URLs."""
    if language not in _LANGUAGES:
        raise ValueError("Unsupported language selection.")
    if source_type not in {"text", "image"}:
        raise ValueError("Unsupported input type.")
    if not isinstance(message_text, str) or not message_text.strip():
        raise ValueError("Message text is empty.")
    if claim_analyzer is None:
        claim_analyzer = extract_claims

    text = message_text
    urls = find_urls(text)
    content_type = classify_input(text)
    input_type = source_type if source_type == "image" else content_type
    url_analyses = [analyze_url(url, language) for url in urls]
    message_without_urls = re.sub(
        r"\s+",
        " ",
        _URL_PATTERN.sub(" ", text)
    ).strip()

    if content_type == "url":
        localized = _MESSAGES[language]
        analysis = {
            "claims": [],
            "warning_signals": [],
            "verification_steps": list(localized["url_only_steps"]),
            "verification_links": [],
            "disclaimer": localized["url_scope"],
            "caution_explanation": localized["url_only_claims"]
        }
        analysis["evidence_status"] = discover_claim_sources([], language=language)
    else:
        analysis = claim_analyzer(text, language=language)
        if not isinstance(analysis, dict):
            analysis = {}
        for field in ("claims", "warning_signals", "verification_steps", "verification_links"):
            if not isinstance(analysis.get(field), list):
                analysis[field] = []
        analysis.setdefault(
            "caution_explanation",
            _MESSAGES[language]["text_scope"]
        )
        if not isinstance(analysis.get("disclaimer"), str) or not analysis["disclaimer"].strip():
            analysis["disclaimer"] = _CLAIM_DISCLAIMERS[language]
        analysis["evidence_status"] = discover_claim_sources(
            analysis["claims"],
            language=language,
            enabled=source_search_enabled
        )

    analysis["warning_signals"] = _merge_url_warnings(analysis, url_analyses)
    analysis["risk_assessment"] = calculate_risk(
        message_without_urls,
        analysis["warning_signals"],
        urls,
        language=language,
        url_analyses=url_analyses
    )
    if content_type == "url":
        analysis["disclaimer"] = _MESSAGES[language]["url_scope"]
    analysis["risk_assessment"]["disclaimer"] = _URL_ONLY_DISCLAIMERS[language]
    analysis_scope = _MESSAGES[language][
        "image_scope" if source_type == "image" else "text_scope"
    ]
    if content_type == "url" and source_type == "image":
        analysis_scope = f'{analysis_scope} {_MESSAGES[language]["url_scope"]}'

    return {
        "extracted_text": text,
        "detected_urls": urls,
        "url_analysis": url_analyses,
        "input_type": input_type,
        "content_type": content_type,
        "source_type": source_type,
        "website_content_checked": False,
        "independent_verification_performed": False,
        "analysis_scope": analysis_scope,
        "analysis": analysis
    }
