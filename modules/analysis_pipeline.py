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
_TRAILING_PUNCTUATION = ".,!?;:)]}\"'"
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
        "text_scope": "The submitted text and visible URL formatting were analysed. No live source search was requested, so no webpages were retrieved. Forward Check did not independently verify claims or assess publisher reliability.",
        "text_scope_search_no_pages": "The submitted text and visible URL formatting were analysed. Live source search was requested, but no source webpages were retrieved. Forward Check did not independently verify claims or assess publisher reliability.",
        "text_scope_search_pages": "The submitted text and visible URL formatting were analysed. Live source search retrieved one or more source webpages for review. Forward Check did not independently verify claims or assess publisher reliability.",
        "image_scope": "Text was extracted from the uploaded image using OCR, then analysed. The image itself was not authenticated and URL destinations were not opened.",
        "image_scope_search_no_pages": "Text was extracted from the uploaded image using OCR, then analysed. Live source search was requested, but no source webpages were retrieved. The image itself was not authenticated and Forward Check did not independently verify claims or assess publisher reliability.",
        "image_scope_search_pages": "Text was extracted from the uploaded image using OCR, then analysed. Live source search retrieved one or more source webpages for review. The image itself was not authenticated and Forward Check did not independently verify claims or assess publisher reliability.",
        "url_scope": "Only visible URL formatting was analysed. The website contents and any claims on the page were not checked."
    },
    "hi": {
        "url_only_claims": "वेबसाइट नहीं खोली गई, इसलिए उसके पेज के दावे नहीं निकाले गए।",
        "url_only_steps": [
            "किसी स्वतंत्र रूप से खोजे गए आधिकारिक स्रोत से domain की जाँच करें।",
            "गंतव्य समझने और स्रोत पर भरोसा होने पर ही वेबसाइट खोलें।",
            "फॉरवर्ड लिंक से पासवर्ड, OTP या भुगतान जानकारी न भरें।"
        ],
        "text_scope": "दिए गए पाठ और URL के दिखने वाले format की जाँच हुई। लाइव source search नहीं माँगी गई, इसलिए कोई webpage retrieve नहीं हुआ। Forward Check ने दावों को स्वतंत्र रूप से verify नहीं किया।",
        "text_scope_search_no_pages": "दिए गए पाठ और URL के दिखने वाले format की जाँच हुई। लाइव source search माँगी गई, लेकिन कोई source webpage retrieve नहीं हुआ। Forward Check ने दावों को स्वतंत्र रूप से verify नहीं किया।",
        "text_scope_search_pages": "दिए गए पाठ और URL के दिखने वाले format की जाँच हुई। लाइव source search से review के लिए एक या अधिक source webpages retrieve हुए। Forward Check ने दावों को स्वतंत्र रूप से verify नहीं किया।",
        "image_scope": "अपलोड की गई image से OCR द्वारा पाठ निकाला और जाँचा गया। image की प्रामाणिकता नहीं जाँची गई और URL नहीं खोले गए।",
        "image_scope_search_no_pages": "अपलोड की गई image से OCR द्वारा पाठ निकाला और जाँचा गया। लाइव source search माँगी गई, लेकिन कोई source webpage retrieve नहीं हुआ। image की प्रामाणिकता नहीं जाँची गई।",
        "image_scope_search_pages": "अपलोड की गई image से OCR द्वारा पाठ निकाला और जाँचा गया। लाइव source search से review के लिए एक या अधिक source webpages retrieve हुए। image की प्रामाणिकता नहीं जाँची गई।",
        "url_scope": "केवल URL का दिखने वाला format जाँचा गया। वेबसाइट की सामग्री और उसके दावों की जाँच नहीं हुई।"
    },
    "hinglish": {
        "url_only_claims": "Website open nahi hui, isliye page ke claims extract nahi kiye gaye.",
        "url_only_steps": [
            "Kisi independently dhoondhe official source se domain check karein.",
            "Destination samajh aaye aur source par bharosa ho tabhi website open karein.",
            "Forwarded link se password, OTP ya payment details na daalein."
        ],
        "text_scope": "Diye gaye text aur URL ke visible format ko analyse kiya. Live source search request nahi hui, isliye koi webpage retrieve nahi hua. Forward Check ne claims ko independently verify nahi kiya.",
        "text_scope_search_no_pages": "Diye gaye text aur URL ke visible format ko analyse kiya. Live source search request hui, lekin koi source webpage retrieve nahi hua. Forward Check ne claims ko independently verify nahi kiya.",
        "text_scope_search_pages": "Diye gaye text aur URL ke visible format ko analyse kiya. Live source search se review ke liye ek ya zyada source webpages retrieve hue. Forward Check ne claims ko independently verify nahi kiya.",
        "image_scope": "Uploaded image se OCR ke zariye text nikala aur analyse kiya. Image authenticate nahi hui aur URL open nahi hue.",
        "image_scope_search_no_pages": "Uploaded image se OCR ke zariye text nikala aur analyse kiya. Live source search request hui, lekin koi source webpage retrieve nahi hua. Image authenticate nahi hui.",
        "image_scope_search_pages": "Uploaded image se OCR ke zariye text nikala aur analyse kiya. Live source search se review ke liye ek ya zyada source webpages retrieve hue. Image authenticate nahi hui.",
        "url_scope": "Sirf URL ka visible format analyse hua. Website content aur page ke claims check nahi hue."
    }
}

_HISTORICAL_TERMS = {
    "constitution", "historical", "history", "treaty", "legislation",
    "parliament", "law", "act", "amendment", "enacted", "ratified",
    "came into effect", "संविधान", "इतिहास", "कानून"
}
_SCHEME_TERMS = {
    "scheme", "yojana", "eligibility", "eligible", "benefit", "scholarship",
    "subsidy", "grant", "fee", "fees", "deadline", "apply", "application",
    "पात्र", "योजना", "लाभ", "शुल्क", "अंतिम तारीख"
}
_GUIDANCE = {
    "en": {
        "historical": [
            "Check authoritative historical records and official government or parliamentary sources.",
            "Confirm the event, date, and legal or constitutional wording against an original record.",
            "Compare more than one independent source before sharing the claim."
        ],
        "scheme": [
            "Check the scheme or benefit name and responsible organisation in an original official source.",
            "Confirm eligibility requirements, fees, application dates, and deadlines from that source.",
            "Do not provide personal details or payment until the official information is independently confirmed."
        ],
        "neutral": [
            "Find the original source and compare the claim with a reliable independent source.",
            "Check the names, dates, numbers, and context against more than one source.",
            "Do not treat search snippets or this analysis as proof that the claim is true or false."
        ]
    },
    "hi": {
        "historical": [
            "प्रामाणिक ऐतिहासिक अभिलेखों और सरकारी या संसदीय आधिकारिक स्रोतों से जाँच करें।",
            "मूल रिकॉर्ड से घटना, तारीख और कानूनी या संवैधानिक शब्दों की पुष्टि करें।",
            "दावा साझा करने से पहले एक से अधिक स्वतंत्र स्रोतों से तुलना करें।"
        ],
        "scheme": [
            "योजना या लाभ का नाम और जिम्मेदार संस्था किसी मूल आधिकारिक स्रोत में जाँचें।",
            "उसी स्रोत से पात्रता, शुल्क, आवेदन की तारीख और अंतिम तारीख की पुष्टि करें।",
            "आधिकारिक जानकारी की स्वतंत्र पुष्टि से पहले निजी जानकारी या भुगतान न दें।"
        ],
        "neutral": [
            "मूल स्रोत खोजें और दावे की किसी विश्वसनीय स्वतंत्र स्रोत से तुलना करें।",
            "नाम, तारीख, संख्या और संदर्भ को एक से अधिक स्रोतों से जाँचें।",
            "Search snippets या इस analysis को दावा सही या गलत होने का प्रमाण न मानें।"
        ]
    },
    "hinglish": {
        "historical": [
            "Authoritative historical records aur official government ya parliamentary sources check karein.",
            "Original record se event, date aur legal ya constitutional wording confirm karein.",
            "Claim share karne se pehle ek se zyada independent sources compare karein."
        ],
        "scheme": [
            "Scheme ya benefit ka naam aur responsible organisation ko original official source mein check karein.",
            "Us source se eligibility, fees, application dates aur deadline confirm karein.",
            "Official information independently confirm hone se pehle personal details ya payment na dein."
        ],
        "neutral": [
            "Original source dhoondhein aur claim ko reliable independent source se compare karein.",
            "Names, dates, numbers aur context ko ek se zyada sources se check karein.",
            "Search snippets ya is analysis ko claim ke true ya false hone ka proof na maanein."
        ]
    }
}


def _guidance_topic(claims, message_text):
    values = message_text.casefold()
    categories = set()
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        values += " " + " ".join(
            str(claim.get(field, "")) for field in
            ("claim", "normalized_wording", "original_wording", "context")
        ).casefold()
        categories.update(
            str(category).casefold()
            for category in claim.get("categories", [])
            if isinstance(category, str)
        )
    if categories.intersection({"history", "historical", "law", "legislation"}):
        return "historical"
    if categories.intersection({"government schemes", "government scheme", "benefits"}):
        return "scheme"
    if any(term in values for term in _HISTORICAL_TERMS):
        return "historical"
    if any(term in values for term in _SCHEME_TERMS):
        return "scheme"
    return "neutral"


def _select_verification_guidance(analysis, message_text, language):
    return list(_GUIDANCE[language][_guidance_topic(
        analysis.get("claims", []), message_text
    )])


def _claim_verification_guidance(claim, message_text, language):
    guidance = _GUIDANCE[language][_guidance_topic([claim], message_text)]
    return " ".join(guidance[:2])


def _build_analysis_scope(language, source_type, evidence_status, content_type):
    localized = _MESSAGES[language]
    if content_type == "url" and source_type != "image":
        return localized["url_scope"]
    base = "image_scope" if source_type == "image" else "text_scope"
    review = evidence_status.get("source_review", {})
    retrieved = isinstance(review, dict) and review.get("retrieved", 0) > 0
    requested = evidence_status.get("status") not in {"not_enabled", "not_applicable"}
    if requested:
        base = f"{base}_search_pages" if retrieved else f"{base}_search_no_pages"
    scope = localized[base]
    if content_type == "url" and source_type == "image":
        scope = f'{scope} {localized["url_scope"]}'
    return scope


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
        for claim in analysis["claims"]:
            if isinstance(claim, dict):
                claim["reason_to_check"] = _claim_verification_guidance(
                    claim,
                    text,
                    language
                )
        analysis["verification_steps"] = _select_verification_guidance(
            analysis,
            text,
            language
        )

    analysis["warning_signals"] = _merge_url_warnings(analysis, url_analyses)
    analysis["risk_assessment"] = calculate_risk(
        message_without_urls,
        analysis["warning_signals"],
        urls,
        language=language,
        url_analyses=url_analyses
    )
    existing_warning_keys = {
        str(signal.get("signal", "")).casefold()
        for signal in analysis["warning_signals"]
        if isinstance(signal, dict)
    }
    for reason in analysis["risk_assessment"].get("reasons", []):
        if not isinstance(reason, dict):
            continue
        category = reason.get("category")
        if not isinstance(category, str) or category.casefold() in existing_warning_keys:
            continue
        evidence = reason.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            continue
        analysis["warning_signals"].append({
            "signal": category,
            "evidence": evidence,
            "explanation": reason.get("explanation", "")
        })
        existing_warning_keys.add(category.casefold())
    if content_type == "url":
        analysis["disclaimer"] = _MESSAGES[language]["url_scope"]
    analysis["risk_assessment"]["disclaimer"] = _URL_ONLY_DISCLAIMERS[language]
    analysis_scope = _build_analysis_scope(
        language,
        source_type,
        analysis["evidence_status"],
        content_type
    )

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
