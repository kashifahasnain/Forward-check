import ipaddress
import re
from difflib import SequenceMatcher
from urllib.parse import urlsplit


_AUTHORITY_TERMS = {
    "gov", "govt", "government", "bank", "rbi", "uidai", "sbi"
}
_AUTHORITY_EXEMPT_SUFFIXES = (".gov.in", ".gov", ".nic.in")
_KNOWN_SERVICE_NAMES = (
    "amazon", "apple", "facebook", "google", "microsoft",
    "netflix", "paypal", "whatsapp", "youtube", "rbi", "sbi", "uidai"
)
_MESSAGES = {
    "en": {
        "invalid": "The URL has invalid syntax or an unusual hostname. Its destination was not opened.",
        "userinfo": "The URL contains user information before the hostname, which can disguise the actual destination.",
        "ip": "The URL uses a numeric IP address instead of a recognizable domain name.",
        "idn": "The URL contains an encoded internationalized domain label. Check the displayed hostname carefully.",
        "http": "The URL uses HTTP rather than HTTPS. This is a limited caution signal, not proof that the site is harmful.",
        "authority": "The hostname contains an authority or brand-related word, but the domain owner was not verified.",
        "lookalike": "A hostname label is similar to a widely used service name. This resemblance does not prove affiliation or fraud.",
        "not_checked": "Only the URL's visible formatting was analysed. The website and its claims were not opened or independently verified.",
        "no_flags": "No listed URL-format warning was detected. This does not mean the website is safe or verified."
    },
    "hi": {
        "invalid": "URL का syntax या hostname असामान्य है। इसका गंतव्य नहीं खोला गया।",
        "userinfo": "URL में hostname से पहले user information है, जिससे असली गंतव्य छिप सकता है।",
        "ip": "URL में पहचानने योग्य domain के बजाय IP address दिया गया है।",
        "idn": "URL में encoded international domain label है। दिखाए गए hostname को ध्यान से जाँचें।",
        "http": "URL HTTPS के बजाय HTTP इस्तेमाल करता है। यह सीमित चेतावनी है, नुकसान का प्रमाण नहीं।",
        "authority": "Hostname में संस्था या brand जैसा शब्द है, लेकिन domain के मालिक की पुष्टि नहीं हुई है।",
        "lookalike": "Hostname का एक हिस्सा लोकप्रिय सेवा के नाम जैसा है। इससे संबंध या धोखाधड़ी साबित नहीं होती।",
        "not_checked": "केवल URL का दिखने वाला format जाँचा गया। वेबसाइट और उसके दावे खोले या स्वतंत्र रूप से verify नहीं किए गए।",
        "no_flags": "सूची में दिए URL-format चेतावनी संकेत नहीं मिले। इसका मतलब यह नहीं कि वेबसाइट सुरक्षित या प्रमाणित है।"
    },
    "hinglish": {
        "invalid": "URL ka syntax ya hostname unusual hai. Iska destination open nahi kiya gaya.",
        "userinfo": "URL mein hostname se pehle user information hai, jo asli destination chhupa sakti hai.",
        "ip": "URL mein pehchane jaane wale domain ke bajaye IP address hai.",
        "idn": "URL mein encoded international domain label hai. Dikhaye gaye hostname ko dhyan se check karein.",
        "http": "URL HTTPS ke bajaye HTTP use karta hai. Yeh limited warning hai, harm ka proof nahi.",
        "authority": "Hostname mein organisation ya brand jaisa word hai, par domain owner verify nahi hua.",
        "lookalike": "Hostname ka ek hissa popular service ke naam jaisa hai. Isse affiliation ya fraud prove nahi hota.",
        "not_checked": "Sirf URL ka visible format analyse hua. Website aur uske claims open ya independently verify nahi hue.",
        "no_flags": "Listed URL-format warning nahi mili. Iska matlab yeh nahi ki website safe ya verified hai."
    }
}


def _url_parts(url):
    candidate = url if "://" in url else f"https://{url}"
    parsed = urlsplit(candidate)
    if parsed.scheme.casefold() not in {"http", "https"}:
        raise ValueError("Unsupported URL scheme.")
    hostname = parsed.hostname
    if not hostname or any(character.isspace() for character in url):
        raise ValueError("URL has no valid hostname.")
    if "%" in hostname:
        raise ValueError("Encoded hostname.")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Invalid port.")
    ascii_hostname = hostname.encode("idna").decode("ascii").casefold()
    labels = ascii_hostname.rstrip(".").split(".")
    if (
        len(ascii_hostname) > 253
        or any(not label or len(label) > 63 for label in labels)
        or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
            for label in labels
        )
    ):
        raise ValueError("Invalid hostname.")
    return parsed, hostname, ascii_hostname


def analyze_url(url, language="en"):
    """Inspect URL syntax and visible components only; never perform a request."""
    messages = _MESSAGES.get(language, _MESSAGES["en"])
    findings = []
    categories = []

    def add(category, points, explanation, score_category=None):
        categories.append({
            "category": score_category or category,
            "points": points
        })
        findings.append({
            "signal": category,
            "evidence": [url],
            "explanation": explanation
        })

    try:
        parsed, hostname, ascii_hostname = _url_parts(url)
    except (UnicodeError, ValueError):
        add(
            "invalid_url_syntax",
            3,
            messages["invalid"],
            score_category="suspicious_url_structure"
        )
        if url.casefold().startswith("http://"):
            add("unencrypted_http", 1, messages["http"])
        return {
            "url": url,
            "valid_syntax": False,
            "hostname": None,
            "website_content_checked": False,
            "warning_signals": findings,
            "risk_categories": categories
        }

    if parsed.username is not None or parsed.password is not None:
        add(
            "embedded_userinfo",
            3,
            messages["userinfo"],
            score_category="suspicious_url_structure"
        )

    try:
        ipaddress.ip_address(hostname)
        add(
            "ip_address_host",
            3,
            messages["ip"],
            score_category="suspicious_url_structure"
        )
    except ValueError:
        pass

    if any(label.startswith("xn--") for label in ascii_hostname.split(".")):
        add(
            "internationalized_domain",
            2,
            messages["idn"],
            score_category="suspicious_url_structure"
        )

    if parsed.scheme.casefold() == "http":
        add("unencrypted_http", 1, messages["http"])

    host = ascii_hostname.rstrip(".")
    authority_word_found = any(
        re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", host)
        or term in host
        for term in _AUTHORITY_TERMS
    )
    is_known_government_suffix = host.endswith(_AUTHORITY_EXEMPT_SUFFIXES)
    if authority_word_found and not is_known_government_suffix:
        add("authority_word_in_hostname", 1, messages["authority"])

    labels = host.split(".")
    lookalike_found = False
    for label in labels:
        for token in label.split("-"):
            normalized = re.sub(
                r"[0-9]",
                lambda match: {
                    "0": "o", "1": "l", "3": "e", "5": "s"
                }.get(match.group(), match.group()),
                token
            )
            if any(
                (token != service or normalized != token or label != token)
                and len(normalized) >= 5
                and SequenceMatcher(None, normalized, service).ratio() >= 0.86
                for service in _KNOWN_SERVICE_NAMES
            ):
                lookalike_found = True
                break
        if lookalike_found:
            break
    if lookalike_found:
        add(
            "lookalike_brand_term",
            1,
            messages["lookalike"],
            score_category="lookalike_brand_term"
        )

    return {
        "url": url,
        "valid_syntax": True,
        "hostname": hostname,
        "website_content_checked": False,
        "warning_signals": findings,
        "risk_categories": categories
    }
