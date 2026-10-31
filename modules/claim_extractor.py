import json
import logging
import os
import re
import time

import requests


logger = logging.getLogger(__name__)
MODEL_NAME = "gemma3:4b"
GEMINI_MODEL_NAME = "gemma-4-26b-a4b-it"
AI_PROVIDER_ENV = "FORWARD_CHECK_AI_PROVIDER"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_CONNECT_TIMEOUT_SECONDS = 3.0
OLLAMA_READ_TIMEOUT_SECONDS = 90.0
_OLLAMA_TIMEOUT_MINIMUM = 0.1
_OLLAMA_TIMEOUT_MAXIMUM = 300.0
_URL_IN_MESSAGE = re.compile(
    r"""(?i)(?:\b(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>'"]+|"""
    r"""(?<![@\w])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"""
    r"""(?:[a-z]{2,})(?::\d+)?(?:/[^\s<>'"]*)?)"""
)
DISCLAIMER = (
    "Forward Check helps you investigate claims. "
    "It does not independently establish whether a message is true or false."
)
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "natural, easy-to-understand Hindi written in Devanagari",
    "hinglish": "natural, simple Hinglish written using the Latin alphabet"
}
LOCALIZED_TEXT = {
    "en": {
        "disclaimer": DISCLAIMER,
        "laptop_claim": "The message says students will receive free laptops.",
        "laptop_reason": "Confirm the offer, organiser and eligibility through an original official announcement.",
        "deadline_claim": "Students must register before {deadline} to qualify.",
        "personal_details_claim": "Students must provide their college ID and personal details to receive the benefit.",
        "specific_claim_reason": "Check this statement and its eligibility requirements with an independent official source.",
        "empty_input": "Paste a message or upload a screenshot to begin the analysis.",
        "scholarship_claim": "The message mentions a scholarship.",
        "scholarship_reason": "Check the scholarship name, application dates and eligibility with the responsible organisation.",
        "fee_claim": "The message makes a claim about a registration fee.",
        "fee_reason": "Confirm any fee directly with the organisation through its official website or published notice.",
        "government_claim": "The message describes a government scheme or benefit.",
        "government_reason": "Search official scheme information and confirm the named organisation and eligibility details.",
        "urgency": "The message uses time pressure, which can discourage careful checking.",
        "forwarding": "The message asks readers to spread it instead of relying on a cited source.",
        "promotional": "This wording may encourage a quick emotional reaction or sharing.",
        "link": "Check the destination and confirm it belongs to the organisation it claims to represent before opening it.",
        "step1": "Identify the organisation or scheme named in the message; do not assume one if none is named.",
        "step2": "Search the claim's key terms on a relevant official website below. A link is a starting point, not proof.",
        "step3": "Compare an original announcement's date and details with the message, including any deadline, eligibility rule or fee.",
        "step4": "Find official contact details independently instead of relying on contact information in the forwarded message.",
        "caution": "Warning signals are reasons to pause and check the message; they do not prove that its claims are true or false."
    },
    "hi": {
        "disclaimer": "Forward Check दावों की जाँच में मदद करता है। यह अपने आप किसी संदेश को सही या गलत साबित नहीं करता।",
        "laptop_claim": "संदेश में दावा है कि छात्रों को मुफ्त लैपटॉप मिलेंगे।",
        "laptop_reason": "ऑफ़र, आयोजक और पात्रता की पुष्टि किसी मूल आधिकारिक घोषणा से करें।",
        "deadline_claim": "पात्र होने के लिए छात्रों को {deadline} से पहले पंजीकरण करना होगा।",
        "personal_details_claim": "लाभ पाने के लिए छात्रों को अपना कॉलेज ID और निजी जानकारी देनी होगी।",
        "specific_claim_reason": "इस दावे और पात्रता की पुष्टि किसी स्वतंत्र आधिकारिक स्रोत से करें।",
        "empty_input": "विश्लेषण शुरू करने के लिए संदेश पेस्ट करें या स्क्रीनशॉट अपलोड करें।",
        "scholarship_claim": "संदेश में छात्रवृत्ति का उल्लेख है।",
        "scholarship_reason": "छात्रवृत्ति का नाम, आवेदन की तारीखें और पात्रता संबंधित संस्था की आधिकारिक जानकारी से जाँचें।",
        "fee_claim": "संदेश में पंजीकरण शुल्क के बारे में दावा किया गया है।",
        "fee_reason": "किसी भी शुल्क की पुष्टि संस्था की आधिकारिक वेबसाइट या प्रकाशित सूचना से करें।",
        "government_claim": "संदेश में सरकारी योजना या लाभ का उल्लेख है।",
        "government_reason": "आधिकारिक योजना की जानकारी खोजें और संस्था तथा पात्रता की पुष्टि करें।",
        "urgency": "संदेश में जल्दी करने का दबाव है, जिससे सावधानी से जाँच करना मुश्किल हो सकता है।",
        "forwarding": "संदेश किसी स्रोत का हवाला देने के बजाय इसे आगे फैलाने के लिए कहता है।",
        "promotional": "यह भाषा जल्दी भावनात्मक प्रतिक्रिया देने या संदेश साझा करने के लिए प्रेरित कर सकती है।",
        "link": "लिंक खोलने से पहले उसका पता जाँचें और पुष्टि करें कि वह उसी संस्था का है जिसका दावा किया गया है।",
        "step1": "संदेश में बताई गई संस्था या योजना पहचानें; नाम न हो तो उसका अनुमान न लगाएँ।",
        "step2": "दावे के मुख्य शब्द किसी संबंधित आधिकारिक वेबसाइट पर खोजें। लिंक केवल शुरुआत है, प्रमाण नहीं।",
        "step3": "मूल घोषणा की तारीख और जानकारी को संदेश से मिलाएँ, जैसे समय-सीमा, पात्रता या शुल्क।",
        "step4": "संदेश में दिए संपर्क पर निर्भर न रहें; आधिकारिक संपर्क जानकारी खुद खोजें।",
        "caution": "चेतावनी संकेत रुककर जाँच करने का कारण हैं; वे दावे को सही या गलत साबित नहीं करते।"
    },
    "hinglish": {
        "disclaimer": "Forward Check claims ki jaanch mein madad karta hai. Yeh apne aap kisi message ko sahi ya galat prove nahi karta.",
        "laptop_claim": "Message mein claim hai ki students ko free laptops milenge.",
        "laptop_reason": "Offer, organiser aur eligibility ko original official announcement se confirm karein.",
        "deadline_claim": "Eligible hone ke liye students ko {deadline} se pehle register karna hoga.",
        "personal_details_claim": "Benefit paane ke liye students ko apna college ID aur personal details deni hongi.",
        "specific_claim_reason": "Is claim aur eligibility ko kisi independent official source se check karein.",
        "empty_input": "Analysis shuru karne ke liye message paste karein ya screenshot upload karein.",
        "scholarship_claim": "Message mein scholarship ka zikr hai.",
        "scholarship_reason": "Scholarship ka naam, application dates aur eligibility zimmedar organisation ki official information se check karein.",
        "fee_claim": "Message registration fee ke baare mein claim karta hai.",
        "fee_reason": "Kisi bhi fee ko organisation ki official website ya notice se confirm karein.",
        "government_claim": "Message mein government scheme ya benefit ka zikr hai.",
        "government_reason": "Official scheme information dekhein aur organisation aur eligibility confirm karein.",
        "urgency": "Message jaldi karne ka pressure banata hai, jis se dhang se check karna mushkil ho sakta hai.",
        "forwarding": "Message kisi source ka hawala dene ke bajaye ise aage share karne ko kehta hai.",
        "promotional": "Yeh wording jaldi emotional reaction ya sharing ke liye uksa sakti hai.",
        "link": "Link kholne se pehle uska address check karein aur confirm karein ki woh daave wali organisation ka hai.",
        "step1": "Message mein batayi organisation ya scheme pehchanein; naam nahi hai to andaza na lagayein.",
        "step2": "Claim ke main words relevant official website par search karein. Link sirf shuruaat hai, proof nahi.",
        "step3": "Original announcement ki date aur details ko message se compare karein, jaise deadline, eligibility ya fee.",
        "step4": "Forwarded message ke contact par bharosa karne ke bajaye official contact khud dhoondhein.",
        "caution": "Warning signals ruk kar check karne ki wajah hain; yeh claim ko sahi ya galat prove nahi karte."
    }

}

_MODEL_UNSAFE_TEXT = re.compile(
    r"\b(?:independently\s+verified|verified\s+as\s+true|proven\s+true|"
    r"proven\s+false|definitely\s+false|definitely\s+true|fraud(?:ulent)?"
    r"|scam)\b",
    re.IGNORECASE
)
_MODEL_URL = re.compile(r"https?://[^\s<>'\"]+|www\.[^\s<>'\"]+", re.IGNORECASE)
_MODEL_NAMED_SOURCE = re.compile(
    r"\b(?:ministry|government of india|press information bureau|"
    r"uidai|rbi|official portal|official website)\b",
    re.IGNORECASE
)


def _configured_timeout(name, default):
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return default
    if not _OLLAMA_TIMEOUT_MINIMUM <= value <= _OLLAMA_TIMEOUT_MAXIMUM:
        return default
    return value


def ollama_timeout():
    return (
        _configured_timeout(
            "OLLAMA_CONNECT_TIMEOUT_SECONDS",
            OLLAMA_CONNECT_TIMEOUT_SECONDS
        ),
        _configured_timeout(
            "OLLAMA_READ_TIMEOUT_SECONDS",
            OLLAMA_READ_TIMEOUT_SECONDS
        )
    )
_MODEL_UNSUPPORTED_DETAIL = re.compile(
    r"\b(?:eligibility|eligible|deadline|registration fee|application fee|"
    r"scholarship|scheme)\b|₹\s*[\d,]+",
    re.IGNORECASE
)


def _claim_provenance(
    *,
    attempted,
    accepted,
    fallback_used,
    fallback_supplemented,
    model_claim_count=0,
    deterministic_claim_count=0,
    unique_model_claim_count=0,
    failure_reason=None,
    provider="ollama",
    model_name=MODEL_NAME
):
    """Report validated model claims and retained deterministic claims.

    ``accepted_model_claim_count`` is counted after grounding and model-only
    deduplication. ``unique_model_claim_count`` and
    ``deterministic_claim_count`` describe claims retained in the final merge.
    """
    return {
        "model": model_name,
        "provider": provider,
        "model_attempted": attempted,
        "model_response_accepted": accepted,
        "deterministic_fallback_used": fallback_used,
        "deterministic_supplementation_used": fallback_supplemented,
        "accepted_model_claim_count": model_claim_count,
        "deterministic_claim_count": deterministic_claim_count,
        "unique_model_claim_count": unique_model_claim_count,
        "failure_reason": failure_reason
    }


def _safe_model_text(value, message_text, fallback):
    if not isinstance(value, str) or not value.strip():
        return fallback
    text = " ".join(value.split()).strip()
    if _MODEL_UNSAFE_TEXT.search(text):
        return fallback
    message_casefold = message_text.casefold()
    if any(
        phrase.casefold() not in message_casefold
        for phrase in _MODEL_NAMED_SOURCE.findall(text)
    ):
        return fallback
    for detail in _MODEL_UNSUPPORTED_DETAIL.findall(text):
        if detail.casefold() not in message_casefold:
            return fallback
    message_numbers = set(re.findall(r"\d[\d,]*(?:\.\d+)?", message_text))
    if not set(re.findall(r"\d[\d,]*(?:\.\d+)?", text)).issubset(message_numbers):
        return fallback
    message_urls = {
        match.group(0).rstrip(".,!?;:)]}\"'").casefold()
        for match in _MODEL_URL.finditer(message_text)
    }
    for match in _MODEL_URL.finditer(text):
        url = match.group(0).rstrip(".,!?;:)]}\"'").casefold()
        if url not in message_urls:
            return fallback
    return text


def _model_failure_reason(error):
    if isinstance(error, requests.Timeout):
        return "timeout"
    if isinstance(error, requests.HTTPError):
        return "http_error"
    if isinstance(error, requests.RequestException):
        return "connection_error"
    if isinstance(error, json.JSONDecodeError):
        return "invalid_json"
    if isinstance(error, (TypeError, ValueError)):
        return "invalid_response"
    return "unknown_error"


def get_verification_links(message_text):
    """Choose established official sites from the subject visible in the message."""
    text = message_text.casefold()
    links = []

    def add_link(title, url, description):
        if not any(link["url"] == url for link in links):
            links.append({
                "title": title,
                "url": url,
                "description": description
            })

    government_terms = (
        "government", "govt", "scheme", "ministry", "minister",
        "prime minister", "government notification", "सरकार", "योजना",
        "मंत्रालय", "सरकारी योजना", "सरकारी अधिसूचना"
    )
    education_terms = (
        "student", "students", "college", "university", "education",
        "scholarship", "school", "laptop", "छात्र", "विद्यार्थी", "कॉलेज",
        "विश्वविद्यालय", "शिक्षा", "छात्रवृत्ति", "स्कूल", "लैपटॉप",
        "students ko", "student ko"
    )

    education_topic = any(term in text for term in education_terms)
    government_topic = any(term in text for term in government_terms)

    if education_topic:
        add_link(
            "myScheme — Government Schemes Directory",
            "https://www.myscheme.gov.in/",
            "Search for Indian government schemes and review their stated eligibility."
        )
        add_link(
            "Ministry of Education",
            "https://www.education.gov.in/",
            "Check official Indian education announcements and student information."
        )

    if government_topic or education_topic:
        add_link(
            "Press Information Bureau (PIB)",
            "https://www.pib.gov.in/",
            "Search for official Indian government announcements related to the claim."
        )
        add_link(
            "PIB Fact Check",
            "https://factcheck.pib.gov.in/",
            "Check whether India's government fact-checking service has addressed the claim."
        )

    if any(term in text for term in (
        "health", "medicine", "medication", "disease", "cure", "covid",
        "coronavirus", "vaccine", "doctor", "hospital", "symptom", "treatment",
        "स्वास्थ्य", "दवा", "बीमारी", "इलाज", "टीका", "डॉक्टर", "अस्पताल"
    )):
        add_link(
            "Ministry of Health and Family Welfare",
            "https://mohfw.gov.in/",
            "Check official Indian government health information and announcements."
        )

    if any(term in text for term in (
        "bank", "banking", "account", "upi", "payment", "money", "loan",
        "interest rate", "rbi", "reserve bank", "credit card", "debit card",
        "बैंक", "खाता", "भुगतान", "पैसे", "ऋण", "क्रेडिट कार्ड", "डेबिट कार्ड"
    )):
        add_link(
            "Reserve Bank of India",
            "https://www.rbi.org.in/",
            "Check official banking notices, financial information and public alerts."
        )

    if any(term in text for term in (
        "scam", "fraud", "cybercrime", "cyber crime", "suspicious link",
        "phishing", "otp", "password", "online fraud", "hacked", "lottery",
        "prize money"
    )):
        add_link(
            "National Cyber Crime Reporting Portal",
            "https://cybercrime.gov.in/",
            "Find official information about reporting cybercrime in India."
        )

    return links


LOCALIZED_LINK_DESCRIPTIONS = {
    "hi": {
        "https://www.myscheme.gov.in/": "भारत सरकार की योजनाएँ खोजें और पात्रता की जाँच करें।",
        "https://www.education.gov.in/": "शिक्षा और छात्रों से जुड़ी आधिकारिक घोषणाएँ देखें।",
        "https://www.pib.gov.in/": "दावे से जुड़ी भारत सरकार की आधिकारिक घोषणाएँ खोजें।",
        "https://factcheck.pib.gov.in/": "देखें कि सरकारी तथ्य-जाँच सेवा ने इस दावे पर जानकारी दी है या नहीं।",
        "https://mohfw.gov.in/": "भारत सरकार की आधिकारिक स्वास्थ्य जानकारी और घोषणाएँ देखें।",
        "https://www.rbi.org.in/": "बैंकिंग सूचनाएँ, वित्तीय जानकारी और जनहित चेतावनियाँ देखें।",
        "https://cybercrime.gov.in/": "भारत में साइबर अपराध की शिकायत करने की आधिकारिक जानकारी देखें।"
    },
    "hinglish": {
        "https://www.myscheme.gov.in/": "Bharat Sarkar ki schemes dhoondhein aur eligibility check karein.",
        "https://www.education.gov.in/": "Education aur students se judi official announcements dekhein.",
        "https://www.pib.gov.in/": "Claim se judi Bharat Sarkar ki official announcements search karein.",
        "https://factcheck.pib.gov.in/": "Dekhein ki government fact-checking service ne is claim par kuch kaha hai ya nahi.",
        "https://mohfw.gov.in/": "Bharat Sarkar ki official health information aur announcements dekhein.",
        "https://www.rbi.org.in/": "Banking notices, financial information aur public alerts dekhein.",
        "https://cybercrime.gov.in/": "India mein cybercrime report karne ki official information dekhein."
    }
}


def _find_evidence(message_text, phrase):
    """Return the exact OCR wording that matches a phrase, preserving its case."""
    match = re.search(re.escape(phrase), message_text, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def detect_warning_signals(message_text, language="en"):
    """Find specific warning wording and quote that wording from the OCR text."""
    language = language if language in LOCALIZED_TEXT else "en"
    localized = LOCALIZED_TEXT[language]
    rules = [
        (
            "Urgency",
            ("urgent", "immediately", "right now", "act fast", "before midnight",
             "limited time", "last chance", "expires today", "today only", "hurry",
             "तुरंत", "अभी", "आज ही", "सीमित समय", "आखिरी मौका", "आखिरी अवसर",
             "मध्यरात्रि से पहले", "जल्दी करें", "abhi", "turant", "aaj hi",
             "last mauka", "jaldi karo", "midnight se pehle"),
            localized["urgency"]
        ),
        (
            "Forwarding request",
            ("forward this", "share this", "send to", "share with", "send this to",
             "forward to", "at least 10", "atleast 10", "all your friends",
             "इसे आगे भेजें", "आगे भेजें", "शेयर करें", "सबको भेजें",
             "कम से कम 10", "दोस्तों को भेजें", "aage bhejo", "share karo",
             "sabko bhejo", "doston ko bhejo", "kam se kam 10"),
            localized["forwarding"]
        ),
        (
            "Promotional or emotional wording",
            ("you won't believe", "amazing offer", "don't miss", "dont miss",
             "shocking", "incredible", "free gift", "everyone can benefit",
             "good news", "यकीन नहीं होगा", "अद्भुत ऑफर", "मौका न गंवाएं",
             "चौंकाने वाला", "मुफ्त उपहार", "अच्छी खबर", "yaqeen nahi hoga",
             "mauka mat chhodo", "free gift", "acchi khabar"),
            localized["promotional"]
        ),
    ]
    signals = []
    seen = set()

    for label, phrases, explanation in rules:
        for phrase in phrases:
            evidence = _find_evidence(message_text, phrase)
            if evidence:
                key = evidence.casefold()
                if key not in seen:
                    signals.append({
                        "signal": label,
                        "evidence": [evidence],
                        "explanation": explanation
                    })
                    seen.add(key)

    for match in re.finditer(r"https?://[^\s]+|www\.[^\s]+", message_text, re.IGNORECASE):
        evidence = match.group(0).rstrip(".,!?;:)]}\"'")
        if evidence and evidence.casefold() not in seen:
            signals.append({
                "signal": "Link included",
                "evidence": [evidence],
                "explanation": localized["link"]
            })
            seen.add(evidence.casefold())

    return signals


def _claim_key(claim):
    return re.sub(r"[^\w]+", " ", claim.casefold(), flags=re.UNICODE).strip()


def detect_message_language(text):
    """Classify the message language without treating all Latin text as Hinglish."""
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"
    if not re.search(r"[A-Za-z]", text):
        return "unknown"
    hinglish_markers = re.findall(
        r"\b(?:aap|aur|bahut|bhi|hai|hain|hoga|hogi|honge|hua|hui|hue|"
        r"ka|ke|ki|ko|mein|milenge|milega|nahi|nahin|se|tha|thi|the|"
        r"wale|waale)\b",
        text,
        re.IGNORECASE
    )
    return "hinglish" if len(set(marker.casefold() for marker in hinglish_markers)) >= 2 else "en"


def _is_placeholder(value):
    normalized = re.sub(r"[^a-z]+", " ", value.casefold()).strip()
    return normalized in {
        "claim",
        "possible claim",
        "further checking is recommended",
        "review this message",
        "no claim identified",
        "unknown"
    }


def _is_verification_instruction(value):
    return bool(re.match(
        r"^\s*(?:please\s+)?(?:verify|check|review|consult|compare|confirm|"
        r"look up|search|read|visit)\b|"
        r"^\s*(?:कृपया\s*)?(?:जाँचें|जांचें|देखें|पुष्टि करें|सत्यापित करें|"
        r"खोजें|पढ़ें|जाँच करें|जांच करें)|"
        r"^\s*(?:please\s+)?(?:independently\s+)?(?:verify|check)\b",
        value,
        re.IGNORECASE
    ))


def _is_incomplete_claim(value):
    return bool(re.search(
        r"(?:\b(?:and|or|but|aur|lekin|और|लेकिन)\s+"
        r"(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St)\.?|"
        r"\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St)\.)$",
        value.strip(),
        re.IGNORECASE
    ))


def _dedupe_claims(claims):
    unique = []
    keys = set()

    for item in claims:
        if not isinstance(item, dict):
            continue
        claim = item.get("claim")
        reason = item.get("reason_to_check", "")
        if not isinstance(claim, str):
            continue
        claim = " ".join(claim.split()).strip()
        if (
            not claim
            or _is_placeholder(claim)
            or _is_verification_instruction(claim)
            or _is_incomplete_claim(claim)
        ):
            continue

        key = _claim_key(claim)
        if key in keys:
            continue

        normalized_reason = (
            " ".join(reason.split()).strip()
            if isinstance(reason, str) else ""
        )
        if _is_placeholder(normalized_reason):
            normalized_reason = ""

        normalized_item = {
            "claim": claim,
            "reason_to_check": normalized_reason
        }
        for field in (
            "evidence",
            "original_wording",
            "normalized_wording",
            "context",
            "entities",
            "categories",
            "claim_type",
            "alleged_speaker",
            "original_language",
            "extraction_method",
            "uncertainty",
            "ai_assessment",
            "ai_explanation",
            "ai_limitations",
            "ai_provider",
            "ai_model"
        ):
            if field in item:
                normalized_item[field] = item[field]
        unique.append(normalized_item)
        keys.add(key)

    filtered = []
    for item in unique:
        item_key = _claim_key(item["claim"])
        duplicate = False
        for existing in filtered:
            if (
                item.get("claim_type") != existing.get("claim_type")
                and "attributed_quote" in {
                    item.get("claim_type"),
                    existing.get("claim_type")
                }
            ):
                continue
            existing_key = _claim_key(existing["claim"])
            shorter, longer = sorted(
                (item_key.split(), existing_key.split()),
                key=len
            )
            shorter_set = set(shorter)
            longer_set = set(longer)
            if (
                len(shorter) >= 4
                and len(shorter) / max(len(longer), 1) >= 0.6
                and shorter_set.issubset(longer_set)
            ):
                if len(item_key.split()) > len(existing_key.split()):
                    filtered[filtered.index(existing)] = item
                duplicate = True
                break
        if not duplicate:
            filtered.append(item)

    return filtered


def _fallback_claims(message_text, language="en"):
    text = message_text.casefold()
    localized = LOCALIZED_TEXT.get(language, LOCALIZED_TEXT["en"])
    claims = []

    if (
        any(word in text for word in ("laptop", "लैपटॉप"))
        and any(word in text for word in (
            "free", "offer", "giving", "provide", "muft", "free mein",
            "मुफ्त", "मुफ़्त", "निःशुल्क"
        ))
        and re.search(
            r"\b(?:will receive|will get|receive|get|give|giving|offer|offers|"
            r"provides|providing|students? get|milenge|milega|milti hai)\b|"
            r"(?:मिलेंगे|मिलेगा|मिलती है|देगा|देंगे)",
            text,
            re.IGNORECASE
        )
        and not re.search(
            r"\b(?:not|no|never|won't|wouldn't|doesn't|don't|isn't|aren't|nahi|nahin)\b|"
            r"(?:नहीं|मत)",
            text,
            re.IGNORECASE
        )
    ):
        claims.append({
            "claim": localized["laptop_claim"],
            "reason_to_check": localized["laptop_reason"],
            "evidence": _matching_sentence(message_text, ("laptop", "लैपटॉप"))
        })

    if any(word in text for word in ("scholarship", "छात्रवृत्ति", "छात्रवृति")):
        claims.append({
            "claim": localized["scholarship_claim"],
            "reason_to_check": localized["scholarship_reason"],
            "evidence": _matching_sentence(
                message_text,
                ("scholarship", "छात्रवृत्ति", "छात्रवृति")
            )
        })

    if any(word in text for word in (
        "registration fee", "no fee", "पंजीकरण शुल्क", "कोई शुल्क नहीं",
        "कोई फीस नहीं"
    )):
        claims.append({
            "claim": localized["fee_claim"],
            "reason_to_check": localized["fee_reason"],
            "evidence": _matching_sentence(
                message_text,
                ("registration fee", "no fee", "पंजीकरण शुल्क", "फीस", "शुल्क")
            )
        })

    has_specific_claim = bool(claims)
    if (
        not has_specific_claim
        and any(term in text for term in (
            "government", "govt", "scheme", "ministry", "सरकार", "योजना", "मंत्रालय"
        ))
        and any(term in text for term in (
            "benefit", "student", "free", "money", "लाभ", "छात्र", "मुफ्त", "पैसे"
        ))
    ):
        claims.append({
            "claim": localized["government_claim"],
            "reason_to_check": localized["government_reason"],
            "evidence": _matching_sentence(
                message_text,
                ("government", "govt", "scheme", "ministry", "सरकार", "योजना", "मंत्रालय")
            )
        })

    return claims


def _message_sentences(message_text):
    protected = message_text
    protected_period = "\x00"
    protected = re.sub(
        r"\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|No|vs|etc|e\.g|i\.e)\.",
        lambda match: match.group(0).replace(".", protected_period),
        protected,
        flags=re.IGNORECASE
    )
    protected = re.sub(
        r"(?<![A-Za-z])([A-Z])\.",
        lambda match: match.group(0).replace(".", protected_period),
        protected
    )
    return [
        " ".join(sentence.replace(protected_period, ".").split()).strip()
        for sentence in re.split(
            r"(?<=[.!?।])(?:[\"”’']?)(?:\s+)|\n+",
            protected
        )
        if sentence.strip()
    ]


def _message_propositions(sentence):
    parts = re.split(
        r"(?<=[,;])\s+(?:(?:and|or|but|aur|lekin|और|लेकिन)\s+)",
        sentence,
        flags=re.IGNORECASE
    )
    if len(parts) == 1:
        return [sentence]
    candidates = []
    for index, part in enumerate(parts):
        candidate = part.strip(" ,;")
        if index:
            candidate = re.sub(
                r"^(?:and|or|but|aur|lekin|और|लेकिन)\s+",
                "",
                candidate,
                flags=re.IGNORECASE
            )
        claim, _ = _factual_sentence_candidate(candidate)
        if claim:
            candidates.append(candidate)
    return candidates or [sentence]


def _claim_language(text):
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"
    if re.search(
        r"\b(?:sabhi|har|milenge|milega|hai|hain|karo|karna|nahi|nahin|"
        r"mein|ko|ka|ki|ke|hoga|hogi|hua|hui|hue|tha|thi|the)\b",
        text,
        re.IGNORECASE
    ):
        return "hinglish"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def _factual_sentence_candidate(sentence):
    value = sentence.strip()
    value = re.sub(
        r"^(?:people are sharing (?:a message )?claiming that|"
        r"(?:(?:the |a viral )?message claims? that|the post says that)|"
        r"reports? say that|i think(?: that)?|i believe(?: that)?|"
        r"i feel(?: that)?)\s+",
        "",
        value,
        flags=re.IGNORECASE
    )
    value = re.sub(r"^(?:that|कि)\s+", "", value, flags=re.IGNORECASE)
    if not value:
        return None, None

    # Pure requests and forwarding instructions are not assertions.
    if re.match(
        r"^(?:please\s+)?(?:forward|share|send|check|verify|confirm|"
        r"compare|read|visit|click|register|apply|देखें|जाँचें|जांचें|"
        r"भेजें|करें)\b",
        value,
        re.IGNORECASE
    ) or re.match(r"^please\b", value, re.IGNORECASE):
        return None, None

    if re.search(
        r"\b(?:best|worst|terrible|awful|wonderful|greatest|"
        r"सबसे अच्छा|सबसे बुरा)\b",
        value,
        re.IGNORECASE
    ):
        return None, None

    question = bool(
        value.endswith("?")
        or re.match(
            r"^(?:did|does|do|is|are|was|were|has|have|will|can|could|"
            r"would|should)\s+",
            value,
            re.IGNORECASE
        )
        or re.match(r"^क्या\s+", value)
    )
    plain_text = value.rstrip("?!।. ")
    if len(plain_text.split()) < 4:
        return None, None

    has_copula_or_modal = bool(re.search(
        r"\b(?:am|is|are|was|were|be|been|being|has|have|had|will|"
        r"can|could|may|might|must|shall|should|would|do|does|did)\b|"
        r"(?:है|हैं|था|थी|थे|होगा|होगी|होंगे|मिलेगा|मिलेगी|मिलेंगे|"
        r"हुआ|हुई|हुए)\b",
        plain_text,
        re.IGNORECASE
    ))
    has_inflected_verb = bool(re.search(
        r"\b(?:[a-z]{3,}(?:ed|s)|came)\s+"
        r"(?:a|an|the|all|every|each|any|no|not|"
        r"\d|[a-z][a-z-]{2,})\b",
        plain_text,
        re.IGNORECASE
    ))
    has_hindi_predicate = bool(re.search(
        r"(?:\s|^)(?:करता है|करती है|करते हैं|मिलता है|मिलती है|"
        r"देता है|देती है|देते हैं|बनता है|बनती है|होता है|होती है|"
        r"कर सकता है|कर सकती है|कर सकते हैं)",
        plain_text
    ))
    has_hinglish_predicate = bool(re.search(
        r"\b(?:hua|hui|hue|tha|thi|the|hoga|hogi|honge|"
        r"lagu\s+hua|kiya\s+tha|kiye\s+the)\b",
        plain_text,
        re.IGNORECASE
    ))
    if not (
        has_copula_or_modal
        or has_inflected_verb
        or has_hindi_predicate
        or has_hinglish_predicate
    ):
        return None, None

    claim_type = "question_containing_claim" if question else "factual_assertion"
    if plain_text and plain_text[0].islower():
        plain_text = plain_text[0].upper() + plain_text[1:]
    punctuation = "?" if question else ("।" if re.search(r"[\u0900-\u097f]", value) else ".")
    return plain_text + punctuation, claim_type


def _attributed_claims(sentence, localized):
    title = (
        r"(?i:Minister|President|Prime Minister|Chief Minister|Dr\.?|Professor|"
        r"Actor|Actress|Singer|Celebrity|PM|CM)"
    )
    name = r"[A-Z][\w.-]*(?:\s+[A-Z][\w.-]*){0,3}"
    attribution = re.compile(
        rf"(?P<speaker>{title}\s+{name}|{name})\s+"
        r"(?P<verb>(?i:said|stated|announced|claimed|declared|wrote|posted|"
        r"told)|कहा|बताया|घोषणा की)\s*(?:(?:that|कि)\s+|[:,]\s*)?"
        r"(?P<statement>.+)",
    )
    match = next(
        (
            candidate for candidate in attribution.finditer(sentence)
            if not re.search(
                r"\b(?:people|sharing|message|claiming|according|reports?)\b",
                candidate.group("speaker"),
                re.IGNORECASE
            )
        ),
        None
    )
    if not match:
        return []

    speaker = match.group("speaker").strip()
    statement = match.group("statement").strip().strip("\"“”'‘’")
    if not statement:
        return []
    statement_claim, _ = _factual_sentence_candidate(statement)
    if not statement_claim:
        return []

    attribution_claim = (
        f'{speaker} {match.group("verb")} that {statement_claim}'
    )
    return [
        {
            "claim": attribution_claim,
            "reason_to_check": localized["specific_claim_reason"],
            "evidence": sentence,
            "claim_type": "attributed_quote",
            "alleged_speaker": speaker,
            "uncertainty": "The message attributes this statement to the speaker; attribution is not verified."
        },
        {
            "claim": statement_claim,
            "reason_to_check": localized["specific_claim_reason"],
            "evidence": sentence,
            "claim_type": "factual_assertion",
            "alleged_speaker": speaker
        }
    ]


def _general_rule_claims(message_text, localized):
    claims = []
    for sentence in _message_sentences(message_text):
        for proposition in _message_propositions(sentence):
            if not proposition.strip():
                continue
            if re.search(r"\b(?:said|stated|announced|claimed|declared|wrote|posted)\b", proposition, re.IGNORECASE):
                attributed = _attributed_claims(proposition, localized)
                if attributed:
                    claims.extend(attributed)
                    continue

            claim, claim_type = _factual_sentence_candidate(proposition)
            if not claim:
                continue
            claims.append({
                "claim": claim,
                "reason_to_check": localized["specific_claim_reason"],
                "evidence": proposition,
                "claim_type": claim_type,
                "original_language": _claim_language(proposition),
                "extraction_method": "local_rules"
            })
    return claims


def _matching_sentence(message_text, terms):
    for sentence in _message_sentences(message_text):
        if any(term.casefold() in sentence.casefold() for term in terms):
            return sentence
    return ""


def _claim_text_without_urls(message_text):
    return _URL_IN_MESSAGE.sub(" ", message_text)


def _rule_based_claims(message_text, language="en"):
    localized = LOCALIZED_TEXT.get(language, LOCALIZED_TEXT["en"])
    claims = []
    sentences = _message_sentences(message_text)
    student_terms = r"(?:students?|pupils?|छात्र|छात्रों|विद्यार्थी|विद्यार्थियों)"
    money_pattern = re.compile(
        r"(?:₹\s*[\d,]+|(?:INR|Rs\.?)\s*[\d,]+|[\d,]+\s*(?:rupees?|रुपये|रुपए))",
        re.IGNORECASE
    )
    assistance_terms = re.compile(
        r"(?:financial assistance|financial aid|financial support|cash assistance|"
        r"monetary assistance|आर्थिक सहायता|वित्तीय सहायता|पैसों की मदद)",
        re.IGNORECASE
    )
    receive_terms = re.compile(
        r"(?:will receive|get|receive|मिलेगा|मिलेगी|मिलेंगे|प्राप्त होगी|"
        r"\bmilega\b|\bmilegi\b|\bmilenge\b)",
        re.IGNORECASE
    )
    for sentence in sentences:
        benefit_claim_patterns = {
            "en": (
                r"(?:the message claims? that\s+)?"
                r"(?P<claim>(?:all|every|each)\s+(?:college\s+)?students?\s+"
                r"(?:can|may|will be able to|are able to)\s+"
                r"(?:receive|get|access)\s+"
                r"(?:financial assistance|financial aid|financial support|"
                r"student benefit|benefits?))"
            ),
            "hi": (
                r"(?P<claim>(?:सभी|हर)\s+(?:छात्र|छात्रों|विद्यार्थी|विद्यार्थियों)"
                r".{0,55}(?:आर्थिक सहायता|वित्तीय सहायता|छात्र लाभ|लाभ)"
                r".{0,30}(?:मिल सकती है|मिल सकता है|प्राप्त कर सकते हैं|"
                r"पा सकते हैं|पात्र हैं))"
            ),
            "hinglish": (
                r"(?P<claim>(?:sabhi|har|all|every)\s+students?"
                r".{0,55}(?:financial assistance|financial aid|student benefit|benefit)"
                r".{0,30}(?:mil sakti hai|mil sakta hai|receive kar sakte hain|"
                r"le sakte hain|eligible hain))"
            )
        }
        benefit_match = re.search(
            benefit_claim_patterns.get(language, benefit_claim_patterns["en"]),
            sentence,
            re.IGNORECASE
        )
        if benefit_match and not re.search(
            r"\b(?:not|no|never|cannot|can't|unable to)\b|"
            r"(?:नहीं|नही|nahi|nahin|नहीं मिल)",
            benefit_match.group("claim"),
            re.IGNORECASE
        ):
            claim = benefit_match.group("claim").strip()
            claim = claim[0].upper() + claim[1:]
            if claim[-1] not in ".!?।":
                claim += "."
            claims.append({
                "claim": claim,
                "reason_to_check": localized["specific_claim_reason"],
                "evidence": benefit_match.group("claim")
            })

        amount = money_pattern.search(sentence)
        all_students = re.search(
            r"\b(?:every|all|each)\s+(?:college\s+)?students?\b|"
            r"\b(?:sabhi|har)\s+(?:college\s+ke\s+)?students?\b|"
            r"(?:सभी|हर)\s+(?:कॉलेज\s+के\s+)?(?:छात्र|छात्रों|विद्यार्थी|विद्यार्थियों)",
            sentence,
            re.IGNORECASE
        )
        if (
            amount
            and assistance_terms.search(sentence)
            and receive_terms.search(sentence)
            and all_students
        ):
            is_negated = bool(re.search(
                r"\b(?:not|no|never|won't|wouldn't|doesn't|don't|isn't|aren't)\b|"
                r"(?:नहीं|नही|nahi|nahin)",
                sentence,
                re.IGNORECASE
            ))
            period_match = re.search(
                r"(this month|this year|आज|इस महीने|इसी महीने|इस वर्ष|is month|iss mahine)",
                sentence,
                re.IGNORECASE
            )
            period = period_match.group(0) if period_match else ""
            if is_negated:
                claim = sentence
            elif language == "hi":
                claim = (
                    f"हर छात्र को {amount.group(0)} की आर्थिक सहायता"
                    f"{' ' + period if period else ''} मिलेगी।"
                )
            elif language == "hinglish":
                claim = (
                    f"Har student ko {amount.group(0)} ki financial assistance"
                    f"{' ' + period if period else ''} milegi."
                )
            else:
                claim = (
                    f"Every student will receive {amount.group(0)} in financial "
                    f"assistance{' ' + period if period else ''}."
                )
            claims.append({
                "claim": claim,
                "reason_to_check": localized["specific_claim_reason"],
                "evidence": sentence
            })

        deadline = re.search(
            r"(?:before|by|से पहले|तक|pehle)\s+"
            r"(?P<time>[\w:०-९]+(?:\s+[\w:०-९]+){0,3})"
            r"(?:\s+to\s+qualify|\s+to\s+be\s+eligible|\s+पात्रता के लिए|\s+eligible hone ke liye)",
            sentence,
            re.IGNORECASE
        )
        if not deadline:
            deadline = re.search(
                r"(?P<time>(?:(?:आज|कल|aaj|kal)\s+)?"
                r"(?:(?:सुबह|दोपहर|शाम|रात)\s+)?"
                r"[\d०-९]{1,2}(?::[\d०-९]{2})?"
                r"(?:\s*(?:बजे|AM|PM))?(?:\s+(?:आज|कल|aaj|kal))?)\s*"
                r"(?:तक|से पहले)",
                sentence,
                re.IGNORECASE
            )
        has_registration = re.search(
            r"(?:register|registration|apply|application|पंजीकरण|रजिस्टर|आवेदन|register karein)",
            sentence,
            re.IGNORECASE
        )
        qualifies_by_deadline = re.search(
            r"(?:qualify|eligible|पात्र|योग्य|eligible hon|eligible hone|"
            r"karna hoga|करना होगा|करना पड़ेगा)",
            sentence,
            re.IGNORECASE
        )
        has_student_audience = re.search(student_terms, sentence, re.IGNORECASE)
        has_you_with_all_students = (
            re.search(r"\b(?:you|your)\b", sentence, re.IGNORECASE)
            and re.search(
                r"\b(?:every|all|each)\s+(?:college\s+)?students?\b|"
                r"\b(?:sabhi|har)\s+(?:college\s+ke\s+)?students?\b|"
                r"(?:सभी|हर)\s+(?:कॉलेज\s+के\s+)?(?:छात्र|छात्रों|विद्यार्थी|विद्यार्थियों)",
                message_text,
                re.IGNORECASE
            )
        )
        if (
            deadline
            and has_registration
            and qualifies_by_deadline
            and (has_student_audience or has_you_with_all_students)
        ):
            if language == "hi" and re.search(r"[\u0900-\u097f]", sentence):
                claim = sentence
            elif language == "hinglish" and re.search(r"\b(?:karna|hoga|hai|tak)\b", sentence, re.IGNORECASE):
                claim = sentence
            elif language == "hi":
                claim = localized["deadline_claim"].format(
                    deadline=deadline.group("time")
                )
            else:
                claim = localized["deadline_claim"].format(
                    deadline=deadline.group("time")
                )
            claims.append({
                "claim": claim,
                "reason_to_check": localized["specific_claim_reason"],
                "evidence": sentence
            })

        asks_for_personal_details = (
            re.search(r"(?:college\s+ID|कॉलेज\s*(?:ID|आईडी|पहचान पत्र))", sentence, re.IGNORECASE)
            and re.search(
                r"(?:personal details|personal information|व्यक्तिगत जानकारी|निजी जानकारी|personal details)",
                sentence,
                re.IGNORECASE
            )
            and re.search(student_terms, message_text, re.IGNORECASE)
            and re.search(
                r"(?:send|provide|share|submit|भेज|देना|दें|जमा|bhej|share karein)",
                sentence,
                re.IGNORECASE
            )
            and not re.search(
                r"\b(?:do not|don't|never|not)\b|(?:नहीं|मत|nahi|nahin)",
                sentence,
                re.IGNORECASE
            )
        )
        if asks_for_personal_details:
            if language == "hi" and re.search(r"[\u0900-\u097f]", sentence):
                claim = sentence
            elif language == "hinglish" and re.search(r"\b(?:bhej|den|details)\b", sentence, re.IGNORECASE):
                claim = sentence
            else:
                claim = localized["personal_details_claim"]
            claims.append({
                "claim": claim,
                "reason_to_check": localized["specific_claim_reason"],
                "evidence": sentence
            })

    action_or_pressure = re.compile(
        r"\b(?:urgent|immediately|right now|forward|share|send|register|apply|"
        r"must|hurry|today only|limited time)\b|"
        r"(?:तुरंत|अभी|आगे भेज|भेजें|रजिस्टर|पंजीकरण|करें|करना होगा)",
        re.IGNORECASE
    )
    factual_verb = re.compile(
        r"\b(?:will|is|are|has|have|was|were|opens|starts|begins|provides|"
        r"offers|costs|announced|available|received)\b|"
        r"(?:है|हैं|होगा|होगी|होंगे|मिलेगा|मिलेगी|मिलेंगे|शुरू होगा|उपलब्ध है)",
        re.IGNORECASE
    )
    concrete_detail = re.compile(
        r"\d|₹|\b(?:student|students|college|university|application|scholarship|"
        r"benefit|assistance|fee|date|month|scheme)\b|"
        r"(?:छात्र|कॉलेज|विश्वविद्यालय|आवेदन|छात्रवृत्ति|लाभ|सहायता|शुल्क|तारीख)",
        re.IGNORECASE
    )
    for sentence in sentences:
        for proposition in _message_propositions(sentence):
            if re.search(
                r"\b(?:said|stated|announced|claimed|declared|wrote|posted)\b",
                proposition,
                re.IGNORECASE
            ):
                continue
            if (
                len(proposition.split()) >= 5
                and factual_verb.search(proposition)
                and concrete_detail.search(proposition)
                and not action_or_pressure.search(proposition)
            ):
                claim, _ = _factual_sentence_candidate(proposition)
                if not claim:
                    continue
                claims.append({
                    "claim": claim,
                    "reason_to_check": localized["specific_claim_reason"],
                    "evidence": proposition
                })

    claims.extend(_general_rule_claims(message_text, localized))
    return _dedupe_claims(claims)


def _exact_entity_values(value, message_text):
    candidates = value if isinstance(value, list) else [value]
    exact_values = []
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        exact = _find_evidence(message_text, candidate.strip())
        if exact and exact.casefold() not in {
            existing.casefold() for existing in exact_values
        }:
            exact_values.append(exact)
    return exact_values


def _claim_entity_scope(claim, evidence, message_text):
    scope = evidence.strip() if isinstance(evidence, str) else ""
    if not scope:
        scope = claim.strip() if isinstance(claim, str) else ""
    propositions = _message_propositions(scope)
    if len(propositions) <= 1 or not isinstance(claim, str):
        return scope

    claim_tokens = set(re.findall(r"\w+", claim.casefold()))
    return max(
        propositions,
        key=lambda proposition: len(
            claim_tokens & set(re.findall(r"\w+", proposition.casefold()))
        )
    )


def _claim_categories(claim_text):
    text = claim_text.casefold()
    topic_terms = {
        "politics": ("politic", "minister", "election", "सरकार", "मंत्री", "चुनाव"),
        "history": ("histor", "treaty", "versailles", "इतिहास", "ऐतिहासिक"),
        "biology": ("biology", "biolog", "plant", "oxygen", "जीवविज्ञान"),
        "science": ("science", "scientific", "physics", "chemistry", "वैज्ञानिक", "विज्ञान"),
        "health": ("health", "medical", "medicine", "vitamin", "infection", "toxin", "body", "स्वास्थ्य", "दवा", "इलाज"),
        "nutrition": ("nutrition", "diet", "food", "lemon water", "पोषण", "आहार"),
        "fitness": ("fitness", "exercise", "workout", "व्यायाम"),
        "finance": ("finance", "financial", "money", "investment", "वित्त", "पैसा"),
        "education": ("student", "school", "college", "education", "छात्र", "शिक्षा"),
        "employment": ("employment", "job", "career", "नौकरी", "रोजगार"),
        "technology": ("technology", "software", "tech", "तकनीक"),
        "cybersecurity": ("cyber", "security", "password", "otp", "साइबर"),
        "environment": ("climate", "environment", "pollution", "जलवायु", "पर्यावरण"),
        "images and media": ("image", "photo", "video", "picture", "तस्वीर", "वीडियो"),
        "government schemes": ("scheme", "government", "मंत्रालय", "योजना", "सरकारी")
    }
    return [
        category
        for category, terms in topic_terms.items()
        if any(term in text for term in terms)
    ]


def _enrich_claim_metadata(claims, message_text, extraction_method="local_rules"):
    enriched = []
    for item in claims:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        evidence = normalized.get("evidence")
        if isinstance(evidence, list):
            evidence = next(
                (value for value in evidence if isinstance(value, str) and value.strip()),
                ""
            )
        if not isinstance(evidence, str):
            evidence = ""
        entity_scope = _claim_entity_scope(
            normalized.get("claim", ""),
            evidence,
            message_text
        )

        original_wording = ""
        for candidate in (
            normalized.get("original_wording"),
            evidence,
            normalized.get("claim")
        ):
            if isinstance(candidate, str):
                original_wording = _find_evidence(message_text, candidate.strip())
                if original_wording:
                    break

        raw_entities = normalized.get("entities")
        entities = {}
        if isinstance(raw_entities, dict):
            for entity_type, values in raw_entities.items():
                if not isinstance(entity_type, str):
                    continue
                exact_values = _exact_entity_values(values, entity_scope)
                if exact_values:
                    entities[entity_type[:40]] = exact_values[:10]
        for entity_type, pattern in (
            (
                "amounts",
                r"(?:₹\s*[\d,]+(?:\.\d+)?|(?:INR|Rs\.?)\s*[\d,]+(?:\.\d+)?|"
                r"[\d,]+\s*(?:rupees?|रुपये|रुपए))"
            ),
            (
                "dates",
                r"(?:\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|"
                r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|"
                r"August|September|October|November|December)\s+\d{4}\b|"
                r"\b(?:first|second|third|fourth|fifth|sixth|"
                r"seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|"
                r"fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|"
                r"nineteenth|twentieth|twenty-first|twenty-second|"
                r"twenty-third|twenty-fourth|twenty-fifth|twenty-sixth|"
                r"twenty-seventh|twenty-eighth|twenty-ninth|thirtieth|"
                r"thirty-first)\s+of\s+(?:January|February|March|April|May|"
                r"June|July|August|September|October|November|December),\s+"
                r"(?:nineteen|twenty)\s+(?:hundred|one|two|three|four|five|"
                r"six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
                r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
                r"forty|fifty|sixty|seventy|eighty|ninety)"
                r"(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?\b|"
                r"\b(?:today|tomorrow|this month|this year)\b|"
                r"(?:आज|कल|इस महीने|इस वर्ष))"
            )
        ):
            extracted = [
                match.group(0)
                for match in re.finditer(pattern, entity_scope, re.IGNORECASE)
            ]
            if extracted:
                entities[entity_type] = list(dict.fromkeys(extracted))[:10]

        raw_categories = normalized.get("categories")
        categories = (
            [value.strip() for value in raw_categories if isinstance(value, str) and value.strip()]
            if isinstance(raw_categories, list)
            else []
        )
        if not categories:
            categories = _claim_categories(normalized.get("claim", ""))
        context_candidate = normalized.get("context")
        context = (
            _find_evidence(message_text, context_candidate.strip())
            if isinstance(context_candidate, str)
            else ""
        )
        if not context:
            context = original_wording

        normalized_wording = normalized.get("normalized_wording")
        if (
            not isinstance(normalized_wording, str)
            or not normalized_wording.strip()
            or not _claim_is_grounded(
                {
                    "claim": normalized_wording.strip(),
                    "evidence": original_wording
                },
                message_text
            )
        ):
            normalized_wording = normalized.get("claim", "")

        claim_type = normalized.get("claim_type")
        allowed_claim_types = {
            "factual_assertion",
            "attributed_quote",
            "question_containing_claim",
            "opinion",
            "instruction"
        }
        if claim_type not in allowed_claim_types:
            claim_type = (
                "question_containing_claim"
                if normalized.get("claim", "").rstrip().endswith("?")
                else "factual_assertion"
            )
        alleged_speaker = normalized.get("alleged_speaker")
        if isinstance(alleged_speaker, str):
            speaker_match = re.search(
                rf"(?<!\w){re.escape(alleged_speaker.strip())}(?!\w)",
                message_text,
                re.IGNORECASE
            )
            alleged_speaker = speaker_match.group(0) if speaker_match else ""
        else:
            alleged_speaker = ""

        original_language = normalized.get("original_language")
        if not isinstance(original_language, str) or original_language not in {
            "en", "hi", "hinglish", "unknown"
        }:
            original_language = _claim_language(
                original_wording or normalized.get("claim", "")
            )

        normalized.update({
            "original_wording": original_wording,
            "normalized_wording": normalized_wording,
            "entities": entities,
            "context": context,
            "categories": list(dict.fromkeys(categories))[:5],
            "claim_type": claim_type,
            "original_language": original_language,
            "extraction_method": extraction_method
        })
        if alleged_speaker:
            normalized["alleged_speaker"] = alleged_speaker
        else:
            normalized.pop("alleged_speaker", None)
        uncertainty = normalized.get("uncertainty")
        if isinstance(uncertainty, str) and uncertainty.strip():
            normalized["uncertainty"] = uncertainty.strip()
        else:
            normalized.pop("uncertainty", None)
        enriched.append(normalized)
    return enriched


def fallback_analysis(message_text, language="en"):
    """Return a structured, evidence-based analysis when Ollama cannot be used."""
    language = language if language in LOCALIZED_TEXT else "en"
    localized = LOCALIZED_TEXT[language]
    links = get_verification_links(message_text)
    for link in links:
        description = LOCALIZED_LINK_DESCRIPTIONS.get(language, {}).get(link["url"])
        if description:
            link["description"] = description
    verification_steps = [
        localized["step1"],
        localized["step2"],
        localized["step3"],
        localized["step4"]
    ]
    claim_text = _claim_text_without_urls(message_text)

    rule_claims = _rule_based_claims(claim_text, language)
    generic_legacy_claims = {
        localized["scholarship_claim"],
        localized["fee_claim"],
        localized["government_claim"]
    }
    rule_evidence = {
        str(item.get("evidence", "")).casefold()
        for item in rule_claims
    }
    legacy_claims = [
        item for item in _fallback_claims(claim_text, language)
        if not (
            item.get("claim") in generic_legacy_claims
            and str(item.get("evidence", "")).casefold() in rule_evidence
        )
    ]

    return {
        "claims": _enrich_claim_metadata(
            _dedupe_claims(legacy_claims + rule_claims),
            message_text
        ),
        "warning_signals": _merge_signals(
            [], detect_warning_signals(message_text, language)
        ),
        "verification_steps": verification_steps,
        "verification_links": links,
        "disclaimer": localized["disclaimer"],
        "caution_explanation": localized["caution"],
        "extraction_method": "local_rules",
        "gemma_provenance": _claim_provenance(
            attempted=False,
            accepted=False,
            fallback_used=True,
            fallback_supplemented=False,
            deterministic_claim_count=len(legacy_claims + rule_claims),
            failure_reason="not_attempted"
        )
    }


def _normalize_model_claims(model_claims):
    if isinstance(model_claims, dict):
        if any(key in model_claims for key in ("claim", "statement", "text", "description")):
            model_claims = [model_claims]
        elif isinstance(model_claims.get("claims"), (list, dict, str)):
            model_claims = model_claims["claims"]
        else:
            model_claims = [
                {"claim": claim, "reason_to_check": reason}
                for claim, reason in model_claims.items()
            ]
    elif isinstance(model_claims, str):
        model_claims = [model_claims]

    normalized = []
    if not isinstance(model_claims, list):
        return normalized

    for item in model_claims:
        if isinstance(item, str):
            normalized.append({"claim": item, "reason_to_check": ""})
        elif isinstance(item, dict):
            claim = next(
                (
                    item[key]
                    for key in ("claim", "statement", "text", "description")
                    if key in item and item[key] not in (None, "")
                ),
                ""
            )
            reason = next(
                (
                    item[key]
                    for key in ("reason_to_check", "reason", "explanation")
                    if key in item and item[key] not in (None, "")
                ),
                ""
            )
            normalized_item = {
                "claim": str(claim) if isinstance(claim, (str, int, float)) else "",
                "reason_to_check": str(reason) if isinstance(reason, (str, int, float)) else ""
            }
            for field in (
                "evidence",
                "original_wording",
                "normalized_wording",
                "context",
                "entities",
                "categories",
                "claim_type",
                "alleged_speaker",
                "original_language",
                "extraction_method",
                "uncertainty",
                "ai_assessment",
                "ai_explanation",
                "ai_limitations",
                "ai_provider",
                "ai_model"
            ):
                if field in item:
                    normalized_item[field] = item[field]
            normalized.append(normalized_item)
        elif isinstance(item, (int, float)):
            normalized.append({"claim": str(item), "reason_to_check": ""})
    return _dedupe_claims(normalized)


def _normalize_model_signals(model_signals, message_text):
    normalized = []
    if not isinstance(model_signals, list):
        return normalized

    for item in model_signals:
        if isinstance(item, str):
            continue
        if not isinstance(item, dict):
            continue

        signal = item.get("signal")
        evidence = item.get("evidence")
        explanation = item.get("explanation")
        if not isinstance(signal, str) or not isinstance(explanation, str):
            continue
        signal = signal.strip()
        explanation = explanation.strip()
        if not signal or not explanation or _is_placeholder(signal):
            continue

        if isinstance(evidence, str):
            evidence_items = [evidence]
        elif isinstance(evidence, list):
            evidence_items = evidence
        else:
            continue

        verified_evidence = []
        for phrase in evidence_items:
            if not isinstance(phrase, str) or not phrase.strip():
                continue
            exact_evidence = _find_evidence(message_text, phrase.strip())
            if exact_evidence and exact_evidence.casefold() not in {
                existing.casefold() for existing in verified_evidence
            }:
                verified_evidence.append(exact_evidence)
        if not verified_evidence:
            continue

        normalized.append({
            "signal": signal,
            "evidence": verified_evidence,
            "explanation": explanation
        })
    return normalized


def _merge_signals(model_signals, detected_signals):
    merged = []
    for item in model_signals + detected_signals:
        key = item["signal"].strip().casefold()
        existing = next(
            (signal for signal in merged if signal["signal"].strip().casefold() == key),
            None
        )
        if existing is None:
            merged.append({
                "signal": item["signal"],
                "evidence": list(item["evidence"]),
                "explanation": item["explanation"]
            })
            continue

        evidence_seen = {phrase.casefold() for phrase in existing["evidence"]}
        for phrase in item["evidence"]:
            if phrase.casefold() not in evidence_seen:
                existing["evidence"].append(phrase)
                evidence_seen.add(phrase.casefold())

        if item["explanation"] not in existing["explanation"]:
            existing["explanation"] = (
                f'{existing["explanation"]} {item["explanation"]}'
            )
    return merged


def _claim_is_grounded(item, message_text):
    claim = item.get("claim")
    if not isinstance(claim, str) or not claim.strip():
        return False
    source = " ".join(message_text.split()).casefold()
    normalized_claim = " ".join(claim.split()).casefold()
    if normalized_claim in source:
        return True

    evidence = item.get("evidence")
    evidence_items = evidence if isinstance(evidence, list) else [evidence]
    for phrase in evidence_items:
        if isinstance(phrase, str) and phrase.strip():
            normalized_evidence = " ".join(phrase.split()).casefold()
            if normalized_evidence in source:
                claim_numbers = set(re.findall(r"\d[\d,]*(?:\.\d+)?", claim))
                evidence_numbers = set(
                    re.findall(r"\d[\d,]*(?:\.\d+)?", normalized_evidence)
                )
                if not claim_numbers.issubset(evidence_numbers):
                    continue
                claim_tokens = set(re.findall(r"\w+", normalized_claim))
                evidence_tokens = set(re.findall(r"\w+", normalized_evidence))
                stop_words = {
                    "a", "an", "and", "are", "as", "at", "be", "before", "by",
                    "for", "from", "in", "is", "it", "of", "on", "or", "the",
                    "this", "to", "will", "with", "you", "your", "message",
                    "claim", "संदेश", "दावा", "है", "हैं", "को", "का", "की",
                    "के", "से", "में", "और", "यह", "कि"
                }
                shared_tokens = (
                    claim_tokens & evidence_tokens
                ) - stop_words
                claim_negated = bool(
                    claim_tokens & {"not", "no", "never", "नहीं", "नही", "nahi", "nahin"}
                )
                evidence_negated = bool(
                    evidence_tokens & {"not", "no", "never", "नहीं", "नही", "nahi", "nahin"}
                )
                if (
                    len(shared_tokens) >= min(2, len(evidence_tokens - stop_words))
                    and claim_negated == evidence_negated
                ):
                    return True

    return False


def _is_nonfactual_model_claim(item):
    claim = item.get("claim", "")
    claim_type = item.get("claim_type")
    if claim_type in {"opinion", "instruction"}:
        return True
    if not isinstance(claim, str):
        return True
    if re.match(
        r"^\s*(?:please\s+)?(?:forward|share|send|check|verify|confirm|"
        r"compare|read|visit|click|register|apply|देखें|जाँचें|जांचें|"
        r"भेजें|करें)\b",
        claim,
        re.IGNORECASE
    ):
        return True
    if re.search(
        r"\b(?:best|worst|terrible|awful|wonderful|greatest|"
        r"सबसे अच्छा|सबसे बुरा)\b",
        claim,
        re.IGNORECASE
    ):
        normalized, _ = _factual_sentence_candidate(claim)
        return normalized is None
    return False


def _ground_model_claims(model_claims, message_text):
    if isinstance(model_claims, dict):
        if any(key in model_claims for key in ("claim", "statement", "text", "description")):
            candidates = [model_claims]
        elif isinstance(model_claims.get("claims"), (list, dict, str)):
            candidates = _model_claim_items(model_claims["claims"])
        else:
            candidates = [
                {"claim": claim, "reason_to_check": reason}
                for claim, reason in model_claims.items()
            ]
    else:
        candidates = _model_claim_items(model_claims)

    grounded = []
    for item in candidates:
        normalized = _normalize_model_claims([item])
        if normalized and _is_nonfactual_model_claim(normalized[0]):
            continue
        grounding_candidate = normalized[0].copy() if normalized else {}
        if isinstance(item, dict):
            grounding_candidate["evidence"] = item.get(
                "evidence",
                item.get("source_quote", item.get("quote", ""))
            )
        if normalized and _claim_is_grounded(grounding_candidate, message_text):
            grounded.extend(normalized)
    return _dedupe_claims(grounded)


def _model_claim_items(model_claims):
    if isinstance(model_claims, list):
        return model_claims
    if isinstance(model_claims, str):
        return [model_claims]
    if isinstance(model_claims, dict):
        return [model_claims]
    return []


_AI_ASSESSMENTS = {
    "Likely true",
    "Likely false",
    "Misleading",
    "Uncertain"
}


def _ai_provider_setting():
    setting = os.environ.get(AI_PROVIDER_ENV, "auto").strip().casefold()
    return setting if setting in {"auto", "gemini", "ollama"} else "auto"


def _gemini_claim_prompt(message_text, language):
    return f"""
Assess factual claims in this message using your general knowledge. Extract up to
3 claims and return only compact JSON. Do not invent citations, URLs, source
retrieval, or details about the sender. Keep claims grounded in the message.
For each claim return:
{{
  "claim": "claim wording",
  "claim_type": "factual_assertion|question_containing_claim",
  "original_wording": "exact wording from the message",
  "evidence": "exact wording from the message",
  "reason_to_check": "brief reason",
  "ai_assessment": "Likely true|Likely false|Misleading|Uncertain",
  "ai_explanation": "brief explanation of the assessment",
  "ai_limitations": "state that this is an AI assessment, not independent source verification"
}}
Use only text present in the message for claim and evidence. The explanation may
use general factual knowledge, but must not claim that a source was checked.
Write user-facing text in {LANGUAGE_NAMES[language]}.
Message:
{message_text[:3000]}
"""


def _parse_model_analysis(model_text, localized):
    parsed_analysis = json.loads(model_text)
    if isinstance(parsed_analysis, list):
        return {
            "claims": parsed_analysis,
            "warning_signals": [],
            "verification_steps": [],
            "caution_explanation": localized["caution"]
        }
    if isinstance(parsed_analysis, dict):
        if any(
            key in parsed_analysis
            for key in ("claim", "statement", "text", "description")
        ):
            return {
                "claims": [parsed_analysis],
                "warning_signals": [],
                "verification_steps": [],
                "caution_explanation": localized["caution"]
            }
        return parsed_analysis
    raise ValueError("AI analysis was not an object or list.")


def _gemini_analysis(message_text, language, api_key):
    try:
        from google import genai
        from google.genai import types
    except ImportError as error:
        raise RuntimeError("gemini_sdk_missing") from error

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=_gemini_claim_prompt(message_text, language),
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
    )
    model_text = getattr(response, "text", None)
    if not isinstance(model_text, str) or not model_text.strip():
        raise ValueError("Gemini returned an empty response.")
    return _parse_model_analysis(model_text, LOCALIZED_TEXT[language])


def _validated_ai_fields(item):
    assessment = item.get("ai_assessment")
    if assessment not in _AI_ASSESSMENTS:
        return {}
    explanation = item.get("ai_explanation")
    limitations = item.get("ai_limitations")
    if not isinstance(explanation, str) or not explanation.strip():
        return {}
    if not isinstance(limitations, str) or not limitations.strip():
        return {}
    return {
        "ai_assessment": assessment,
        "ai_explanation": " ".join(explanation.split()).strip()[:1000],
        "ai_limitations": " ".join(limitations.split()).strip()[:500]
    }


def _merge_model_analysis(
    analysis,
    fallback,
    message_text,
    localized,
    provider,
    model_name,
    extraction_method
):
    analysis.setdefault("warning_signals", [])
    analysis.setdefault("verification_steps", [])
    analysis.setdefault("caution_explanation", localized["caution"])
    model_claims = analysis.get("claims", [])
    if (
        not isinstance(model_claims, (list, dict, str))
        or not isinstance(analysis.get("warning_signals"), list)
        or not isinstance(analysis.get("verification_steps"), list)
        or not isinstance(analysis["caution_explanation"], str)
        or not analysis["caution_explanation"].strip()
    ):
        raise ValueError("AI analysis is missing required fields.")

    claims = _ground_model_claims(model_claims, message_text)
    accepted_model_claim_count = len(claims)
    if provider == "gemini":
        for claim in claims:
            ai_fields = _validated_ai_fields(claim)
            if not ai_fields:
                continue
            claim.update(ai_fields)
            claim["ai_provider"] = provider
            claim["ai_model"] = model_name
    claims = _enrich_claim_metadata(
        claims,
        message_text,
        extraction_method=extraction_method
    )
    merged_claims = _dedupe_claims(claims + fallback["claims"])
    retained_model_claims = [
        item for item in merged_claims
        if item.get("extraction_method") == extraction_method
    ]
    retained_deterministic_claims = [
        item for item in merged_claims
        if item.get("extraction_method") == "local_rules"
    ]
    model_steps = [
        " ".join(step.split()).strip()
        for step in analysis["verification_steps"]
        if isinstance(step, str) and step.strip()
    ][:5]
    verification_steps = model_steps or fallback["verification_steps"]
    verification_steps = [
        _safe_model_text(
            step,
            message_text,
            fallback["verification_steps"][index]
            if index < len(fallback["verification_steps"])
            else localized["step1"]
        )
        for index, step in enumerate(verification_steps)
    ]
    verification_steps = [step for step in verification_steps if step] or fallback["verification_steps"]
    return {
        "claims": merged_claims,
        "warning_signals": _merge_signals(
            _normalize_model_signals(analysis["warning_signals"], message_text),
            fallback["warning_signals"]
        ),
        "verification_steps": verification_steps,
        "caution_explanation": _safe_model_text(
            analysis["caution_explanation"],
            message_text,
            fallback["caution_explanation"]
        ),
        "accepted_model_claim_count": accepted_model_claim_count,
        "unique_model_claim_count": len(retained_model_claims),
        "deterministic_claim_count": len(retained_deterministic_claims),
        "deterministic_supplementation_used": bool(retained_deterministic_claims)
    }


def extract_claims(message_text, language="en"):
    """Analyse OCR text with the configured AI provider and local fallback."""
    language = language if language in LANGUAGE_NAMES else "en"
    localized = LOCALIZED_TEXT[language]
    if not isinstance(message_text, str) or not message_text.strip():
        return {
            "claims": [],
            "warning_signals": [],
            "verification_steps": [localized["empty_input"]],
            "verification_links": [],
            "disclaimer": localized["disclaimer"],
            "caution_explanation": localized["caution"],
            "extraction_method": "not_run",
            "gemma_provenance": _claim_provenance(
                attempted=False,
                accepted=False,
                fallback_used=False,
                fallback_supplemented=False,
                failure_reason="empty_input"
            )
        }

    fallback = fallback_analysis(message_text, language)
    provider_setting = _ai_provider_setting()
    gemini_key = os.environ.get(GEMINI_API_KEY_ENV, "").strip()
    if provider_setting in {"auto", "gemini"} and gemini_key:
        try:
            gemini_analysis = _gemini_analysis(message_text, language, gemini_key)
            merged = _merge_model_analysis(
                gemini_analysis,
                fallback,
                message_text,
                localized,
                "gemini",
                GEMINI_MODEL_NAME,
                "gemini"
            )
            return {
                "claims": merged["claims"],
                "warning_signals": merged["warning_signals"],
                "verification_steps": merged["verification_steps"],
                "verification_links": fallback["verification_links"],
                "disclaimer": localized["disclaimer"],
                "caution_explanation": merged["caution_explanation"],
                "extraction_method": "gemini_assisted",
                "ai_provider": "gemini",
                "ai_model": GEMINI_MODEL_NAME,
                "gemma_provenance": _claim_provenance(
                    attempted=True,
                    accepted=True,
                    fallback_used=False,
                    fallback_supplemented=merged["deterministic_supplementation_used"],
                    model_claim_count=merged["accepted_model_claim_count"],
                    deterministic_claim_count=merged["deterministic_claim_count"],
                    unique_model_claim_count=merged["unique_model_claim_count"],
                    provider="gemini",
                    model_name=GEMINI_MODEL_NAME
                )
            }
        except Exception as error:
            logger.warning(
                "Gemini extraction failed: category=%s",
                type(error).__name__
            )

    requested_language = LANGUAGE_NAMES[language]
    prompt = f"""
Extract up to 3 factual claims from this message. Preserve meaning, language,
transliteration, qualifiers, names, recipients, amounts, dates and locations.
Use only text present in the message. Never decide truth, invent facts, sources,
URLs or evidence, or treat URLs as page evidence. Ignore pure opinions and
instructions without a factual proposition. Copy evidence exactly; keep quotes
and names unchanged. Write the reason in {requested_language}. Return only compact JSON:
{{
  "claims": [{{"claim":"factual claim","claim_type":"factual_assertion|attributed_quote|question_containing_claim","original_wording":"exact quote","evidence":"exact text","reason_to_check":"brief reason"}}
  ]
}}
Use [] when there are no factual claims. Message:
{message_text[:3000]}
"""

    effective_timeout = ollama_timeout()
    request_started = time.perf_counter()
    logger.warning(
        "Gemma extraction request started: connect_timeout=%.1fs read_timeout=%.1fs",
        effective_timeout[0],
        effective_timeout[1]
    )
    response_status = None
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 256,
                    "num_ctx": 1536
                },
                "keep_alive": "10m"
            },
            timeout=effective_timeout
        )
        response_status = response.status_code
        response.raise_for_status()
        response_data = response.json()
        if not isinstance(response_data, dict):
            raise ValueError("Ollama response was not a JSON object.")

        model_text = response_data.get("response")
        if not isinstance(model_text, str) or not model_text.strip():
            raise ValueError("Ollama returned an empty response.")

        parsed_analysis = json.loads(model_text)
        if isinstance(parsed_analysis, list):
            analysis = {
                "claims": parsed_analysis,
                "warning_signals": [],
                "verification_steps": [],
                "caution_explanation": localized["caution"]
            }
        elif isinstance(parsed_analysis, dict):
            if any(
                key in parsed_analysis
                for key in ("claim", "statement", "text", "description")
            ):
                analysis = {
                    "claims": [parsed_analysis],
                    "warning_signals": [],
                    "verification_steps": [],
                    "caution_explanation": localized["caution"]
                }
            else:
                analysis = parsed_analysis
        else:
            raise ValueError("Ollama analysis was not an object or list.")

        analysis.setdefault("warning_signals", [])
        analysis.setdefault("verification_steps", [])
        analysis.setdefault("caution_explanation", localized["caution"])
        model_claims = analysis.get("claims", [])
        if (
            not isinstance(model_claims, (list, dict, str))
            or not isinstance(analysis.get("warning_signals"), list)
            or not isinstance(analysis.get("verification_steps"), list)
            or not isinstance(analysis["caution_explanation"], str)
            or not analysis["caution_explanation"].strip()
        ):
            raise ValueError("Ollama analysis is missing required fields.")

        claims = _ground_model_claims(model_claims, message_text)
        accepted_model_claim_count = len(claims)
        if claims:
            claims = _enrich_claim_metadata(
                claims,
                message_text,
                extraction_method="ollama"
            )
        merged_claims = _dedupe_claims(claims + fallback["claims"])
        retained_model_claims = [
            item for item in merged_claims
            if item.get("extraction_method") == "ollama"
        ]
        retained_deterministic_claims = [
            item for item in merged_claims
            if item.get("extraction_method") == "local_rules"
        ]
        unique_model_claim_count = len(retained_model_claims)

        detected_signals = fallback["warning_signals"]
        model_signals = _normalize_model_signals(
            analysis.get("warning_signals"), message_text
        )

        model_steps = [
            " ".join(step.split()).strip()
            for step in analysis["verification_steps"]
            if isinstance(step, str) and step.strip()
        ][:5]
        verification_steps = (
            model_steps
            if model_steps
            else fallback["verification_steps"]
        )
        verification_steps = [
            _safe_model_text(
                step,
                message_text,
                fallback["verification_steps"][index]
                if index < len(fallback["verification_steps"])
                else localized["step1"]
            )
            for index, step in enumerate(verification_steps)
        ]
        verification_steps = [
            step for step in verification_steps if step
        ] or fallback["verification_steps"]
        caution_explanation = _safe_model_text(
            analysis["caution_explanation"],
            message_text,
            fallback["caution_explanation"]
        )

        logger.warning(
            "Gemma extraction request completed: status=%s elapsed_seconds=%.2f",
            response_status,
            time.perf_counter() - request_started
        )
        return {
            "claims": merged_claims,
            "warning_signals": _merge_signals(model_signals, detected_signals),
            "verification_steps": verification_steps,
            "verification_links": fallback["verification_links"],
            "disclaimer": localized["disclaimer"],
            "caution_explanation": caution_explanation,
            "extraction_method": "ollama_assisted",
            "ai_provider": "ollama",
            "ai_model": MODEL_NAME,
            "gemma_provenance": _claim_provenance(
                attempted=True,
                accepted=True,
                fallback_used=False,
                fallback_supplemented=bool(retained_deterministic_claims),
                model_claim_count=accepted_model_claim_count,
                deterministic_claim_count=len(retained_deterministic_claims),
                unique_model_claim_count=unique_model_claim_count,
                provider="ollama",
                model_name=MODEL_NAME
            )
        }

    except (requests.RequestException, ValueError, TypeError) as error:
        failure_reason = _model_failure_reason(error)
        logger.warning(
            "Gemma extraction request failed: category=%s status=%s elapsed_seconds=%.2f",
            failure_reason,
            response_status,
            time.perf_counter() - request_started
        )
        fallback["gemma_provenance"] = _claim_provenance(
            attempted=True,
            accepted=False,
            fallback_used=True,
            fallback_supplemented=False,
            deterministic_claim_count=len(fallback["claims"]),
            failure_reason=failure_reason
        )
        return fallback
