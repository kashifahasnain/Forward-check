import ipaddress
import re
from urllib.parse import urlsplit

from modules.url_analyzer import analyze_url


RISK_DISCLAIMER = (
    "This score reflects detected warning signs only. It does not verify whether "
    "a message or URL is true, false, safe, or fraudulent."
)
_RISK_DISCLAIMERS = {
    "hi": "यह अंक केवल मिले चेतावनी संकेत दिखाता है। यह धोखाधड़ी की संभावना या सत्यापन का प्रमाण नहीं है।",
    "hinglish": "Yeh score sirf warning signals dikhata hai. Yeh fraud ki probability ya verification ka proof nahi hai."
}

_CREDENTIAL_WORDS = re.compile(
    r"\b(?:passwords?|passcodes?|otps?|one[- ]time passwords?|pins?|"
    r"cvv|cvc|bank(?:ing)? credentials|account credentials|card details|"
    r"बैंक विवरण|कार्ड विवरण)\b|(?:पासवर्ड|ओटीपी|पिन)",
    re.IGNORECASE
)
_CREDENTIAL_ACTIONS = re.compile(
    r"\b(?:send|share|enter|provide|submit|reply|give|type|text|email|"
    r"confirm|verify|update|bhejo)\b|"
    r"(?:भेजें|भेजो|साझा करें|दर्ज करें|बताएँ|दीजिए|भरे|करें|करो)",
    re.IGNORECASE
)
_NEGATED_REQUEST = re.compile(
    r"\b(?:do not|don't|dont|never|avoid|should not|shouldn't)\b"
    r".{0,40}\b(?:send|share|enter|provide|submit|reply|give|type|"
    r"text|email|confirm|verify|update)\b|"
    r"(?:मत|नहीं|कभी न|na|mat|nahi)\s*"
    r".{0,30}\b(?:भेजें|भेजो|साझा करें|दर्ज करें|बताएँ|दीजिए|share|send|enter|provide)\b|"
    r"(?:कभी\s*)?(?:भेजें|भेजो|साझा|दर्ज|बताएँ).{0,20}(?:न करें|मत करें|ना करें)",
    re.IGNORECASE
)
_BENEFIT_TERMS = re.compile(
    r"\b(?:free money|cash prize|prize money|prize|lottery|reward|"
    r"grant|benefit|financial aid|free laptop|scholarship)\b|"
    r"(?:मुफ्त पैसा|मुफ़्त पैसा|इनाम|लॉटरी|पुरस्कार|लाभ|छात्रवृत्ति|"
    r"मुफ्त लैपटॉप|मुफ़्त लैपटॉप)",
    re.IGNORECASE
)
_SOURCE_TERMS = re.compile(
    r"\b(?:according to|official source|official website|ministry of|"
    r"department of|press information bureau|government notification|"
    r"notification no\.?|issued by|published by|source:)\b|"
    r"(?:सरकारी वेबसाइट|सरकारी अधिसूचना|मंत्रालय|विभाग द्वारा|आधिकारिक स्रोत)",
    re.IGNORECASE
)
_RISK_TRANSLATIONS = {
    "hi": {
        "credential_request": "संदेश पासवर्ड, OTP, PIN या बैंक जानकारी माँगता हुआ लगता है। ऐसे विवरण साझा न करें।",
        "suspicious_url_structure": "URL की बनावट से उसका असली गंतव्य पहचानना कठिन हो सकता है। यह चेतावनी है, नुकसान का प्रमाण नहीं।",
        "unencrypted_http": "URL HTTPS के बजाय HTTP इस्तेमाल करता है। यह सीमित चेतावनी है, नुकसान का प्रमाण नहीं।",
        "authority_word_in_hostname": "Hostname में संस्था या brand जैसा शब्द है, लेकिन domain के मालिक की पुष्टि नहीं हुई है।",
        "lookalike_brand_term": "Hostname का एक हिस्सा लोकप्रिय सेवा के नाम जैसा है। इससे संबंध या धोखाधड़ी साबित नहीं होती।",
        "urgency": "संदेश जल्दी करने का दबाव डालता है, जिससे सावधानी से जाँच करना मुश्किल हो सकता है।",
        "mass_forwarding": "संदेश इसे बहुत से लोगों को आगे भेजने या साझा करने के लिए कहता है।",
        "unattributed_benefit": "संदेश में लाभ या इनाम का उल्लेख है, लेकिन स्पष्ट स्रोत नहीं बताया गया।",
        "no_listed_indicators": "सूची में दिए चेतावनी संकेत नहीं मिले। इसका मतलब यह नहीं कि संदेश या लिंक सुरक्षित या प्रमाणित है。"
    },
    "hinglish": {
        "credential_request": "Message password, OTP, PIN ya bank details maangta hua lagta hai. Yeh details share na karein.",
        "suspicious_url_structure": "URL ki structure se asli destination pehchanna mushkil ho sakta hai. Yeh warning hai, harm ka proof nahi.",
        "unencrypted_http": "URL HTTPS ke bajaye HTTP use karta hai. Yeh limited warning hai, harm ka proof nahi.",
        "authority_word_in_hostname": "Hostname mein organisation ya brand jaisa word hai, par domain owner verify nahi hua.",
        "lookalike_brand_term": "Hostname ka ek hissa popular service ke naam jaisa hai. Isse affiliation ya fraud prove nahi hota.",
        "urgency": "Message jaldi karne ka pressure banata hai, jis se dhang se check karna mushkil ho sakta hai.",
        "mass_forwarding": "Message ise bahut logon ko forward ya share karne ko kehta hai.",
        "unattributed_benefit": "Message benefit ya prize ka zikr karta hai, lekin clear source nahi batata.",
        "no_listed_indicators": "List mein warning signals nahi mile. Iska matlab yeh nahi ki message ya URL safe ya verified hai."
    }
}


def _signal_names(warning_signals):
    if isinstance(warning_signals, dict):
        warning_signals = [warning_signals]
    if not isinstance(warning_signals, list):
        return []

    names = []
    for signal in warning_signals:
        if isinstance(signal, str):
            names.append(signal.casefold())
        elif isinstance(signal, dict):
            name = signal.get("signal")
            if isinstance(name, str):
                names.append(name.casefold())
    return names


def _has_credential_request(message_text):
    for clause in re.split(r"[.!?;।\n]+", message_text):
        if not _CREDENTIAL_WORDS.search(clause):
            continue
        if _NEGATED_REQUEST.search(clause):
            continue
        if _CREDENTIAL_ACTIONS.search(clause):
            return True
    return False


def _url_has_suspicious_structure(url):
    candidate = url if "://" in url else f"//{url}"
    try:
        parsed = urlsplit(candidate)
        hostname = parsed.hostname
        if not hostname or parsed.username or parsed.password:
            return True

        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            pass

        return any(label.startswith("xn--") for label in hostname.casefold().split("."))
    except ValueError:
        return True


def _uses_http(url):
    if "://" not in url:
        return False
    try:
        return urlsplit(url).scheme.casefold() == "http"
    except ValueError:
        return url.casefold().startswith("http://")


def _add_reason(reasons, category, points, explanation):
    if not any(reason["category"] == category for reason in reasons):
        reasons.append({
            "category": category,
            "points": points,
            "explanation": explanation
        })


def calculate_risk(
    message_text,
    warning_signals=None,
    detected_urls=None,
    language="en",
    url_analyses=None
):
    """Score explicit warning indicators; this is not a truth or safety verdict."""
    text = message_text if isinstance(message_text, str) else ""
    signals = _signal_names(warning_signals)
    urls = detected_urls if isinstance(detected_urls, list) else []
    urls = [url.strip() for url in urls if isinstance(url, str) and url.strip()]
    if not isinstance(url_analyses, list):
        url_analyses = [analyze_url(url, language) for url in urls]
    reasons = []
    translations = _RISK_TRANSLATIONS.get(language, {})

    def explanation(category, english):
        return translations.get(category, english)

    scored_url_categories = {}
    for url_result in url_analyses:
        if not isinstance(url_result, dict):
            continue
        for item in url_result.get("risk_categories", []):
            if not isinstance(item, dict):
                continue
            category = item.get("category")
            points = item.get("points")
            if isinstance(category, str) and isinstance(points, int):
                scored_url_categories[category] = max(
                    scored_url_categories.get(category, 0), points
                )

    url_explanations = {
        "suspicious_url_structure": (
            "A URL has an invalid or hard-to-recognize structure. This is a warning sign, not proof of harm."
        ),
        "unencrypted_http": (
            "At least one URL uses HTTP rather than HTTPS. This alone does not establish that the site is harmful."
        ),
        "authority_word_in_hostname": (
            "A hostname contains authority- or brand-related wording, but its owner has not been verified."
        ),
        "lookalike_brand_term": (
            "A hostname label resembles a widely used service name. This resemblance does not prove affiliation or fraud."
        )
    }
    for category, points in scored_url_categories.items():
        if category in url_explanations:
            _add_reason(
                reasons,
                category,
                points,
                explanation(category, url_explanations[category])
            )

    if _has_credential_request(text):
        _add_reason(
            reasons,
            "credential_request",
            5,
            explanation(
                "credential_request",
                "The message appears to ask for a password, OTP, PIN, or banking credential. "
                "Do not share these details in response to a forwarded message."
            )
        )

    if (
        any("urgency" in signal or "urgent" in signal for signal in signals)
        or re.search(
            r"\b(?:urgent|immediately|right now|act fast|before midnight|"
            r"limited time|last chance|expires today|today only|hurry|"
            r"abhi|turant|jaldi karo|aaj hi|last mauka)\b|"
            r"(?:अभी|तुरंत|जल्दी करें|आज ही|सीमित समय|आखिरी मौका)",
            text,
            re.IGNORECASE
        )
    ):
        _add_reason(
            reasons,
            "urgency",
            2,
            explanation(
                "urgency",
                "The message applies time pressure, which can discourage careful checking."
            )
        )

    if (
        any("forward" in signal or "sharing request" in signal for signal in signals)
        or re.search(
            r"\b(?:forward this|share this|send this to|share with|"
            r"at least\s+\d+|atleast\s+\d+|all your friends|"
            r"aage bhejo|doston ko bhejo|sabko bhejo)\b",
            text,
            re.IGNORECASE
        )
        or re.search(
            r"(?:आगे भेजें|इसे शेयर करें|दोस्तों को भेजें|सबको भेजें)",
            text,
            re.IGNORECASE
        )
    ):
        _add_reason(
            reasons,
            "mass_forwarding",
            2,
            explanation(
                "mass_forwarding",
                "The message asks readers to forward or share it broadly."
            )
        )

    if _BENEFIT_TERMS.search(text) and not _SOURCE_TERMS.search(text):
        _add_reason(
            reasons,
            "unattributed_benefit",
            2,
            explanation(
                "unattributed_benefit",
                "The message mentions money, a prize, or a benefit without a clear source "
                "being named in the text."
            )
        )

    score = sum(reason["points"] for reason in reasons)
    if score >= 5:
        level = "High Caution"
    elif score >= 2:
        level = "Medium Caution"
    else:
        level = "Low Caution"

    if not reasons:
        reasons.append({
            "category": "no_listed_indicators",
            "points": 0,
            "explanation": (
                explanation(
                    "no_listed_indicators",
                    "No listed warning indicators were detected. This does not mean "
                    "the message or URL is verified or safe."
                )
            )
        })

    return {
        "level": level,
        "score": score,
        "reasons": reasons,
        "disclaimer": RISK_DISCLAIMER
        if language not in _RISK_DISCLAIMERS
        else _RISK_DISCLAIMERS[language]
    }
