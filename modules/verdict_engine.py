import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_VERDICT_LABELS = {
    "en": {
        "supported": "Supported by Evidence",
        "misleading": "Misleading or Missing Context",
        "not_factual": "Not a Factual Claim",
        "unverified": "Unverified"
    },
    "hi": {
        "supported": "प्रमाण से समर्थित",
        "misleading": "भ्रामक या संदर्भ अधूरा",
        "not_factual": "तथ्यात्मक दावा नहीं",
        "unverified": "अपुष्ट"
    },
    "hinglish": {
        "supported": "Evidence se Supported",
        "misleading": "Misleading ya Context Adhoora",
        "not_factual": "Factual Claim Nahi",
        "unverified": "Unverified"
    }
}
_EXPLANATIONS = {
    "en": {
        "supported": (
            "Multiple distinct retrieved passages support this wording. "
            "Publisher reliability and source independence were not independently assessed."
        ),
        "misleading": (
            "A retrieved passage gives a clear eligibility or scope qualification "
            "that materially narrows the claim. This is not a complete fact-check."
        ),
        "not_factual": (
            "This is an opinion or instruction, not a checkable factual assertion."
        ),
        "opinion_split": (
            "The evaluative wording is an opinion; its separately extracted factual "
            "assertion is assessed as another claim."
        ),
        "opinion_fact": (
            "This opinion may contain a factual assertion, but it could not be "
            "separated reliably; that assertion remains unverified."
        ),
        "conflict": (
            "Retrieved evidence both supports and contradicts the claim. The "
            "available records do not resolve the conflict."
        ),
        "contradiction": (
            "A retrieved passage is marked as contradictory, but source quality "
            "or claim coverage is not established strongly enough for a false verdict."
        ),
        "context": (
            "Retrieved text adds context, but the available record does not show "
            "a clear material change in scope."
        ),
        "insufficient": (
            "The available evidence is missing, incomplete, irrelevant, conflicting, "
            "or too weak for a verdict. Unverified does not mean false."
        )
    },
    "hi": {
        "supported": (
            "कई अलग-अलग प्राप्त अंश इस शब्दांकन का समर्थन करते हैं। "
            "प्रकाशक की विश्वसनीयता और स्रोतों की स्वतंत्रता की अलग से जाँच नहीं हुई।"
        ),
        "misleading": (
            "प्राप्त अंश में पात्रता या दायरे की स्पष्ट शर्त है, जो दावे को "
            "महत्वपूर्ण रूप से सीमित करती है। यह पूरी तथ्य-जाँच नहीं है।"
        ),
        "not_factual": "यह राय या निर्देश है, जाँचने योग्य तथ्यात्मक दावा नहीं।",
        "opinion_split": (
            "राय वाले हिस्से को मत माना गया है; उससे अलग निकाले गए तथ्यात्मक दावे "
            "का आकलन अलग किया गया है।"
        ),
        "opinion_fact": (
            "इस राय में कोई तथ्यात्मक दावा हो सकता है, लेकिन उसे भरोसे से अलग "
            "नहीं किया जा सका; वह दावा अपुष्ट है।"
        ),
        "conflict": (
            "प्राप्त प्रमाण दावे का समर्थन भी करता है और उसका विरोध भी। "
            "उपलब्ध जानकारी इस मतभेद को सुलझाती नहीं है।"
        ),
        "contradiction": (
            "प्राप्त अंश को विरोधी बताया गया है, लेकिन गलत निष्कर्ष देने के लिए "
            "स्रोत की गुणवत्ता या दावे का पूरा दायरा पर्याप्त रूप से स्थापित नहीं है।"
        ),
        "context": (
            "प्राप्त पाठ संदर्भ जोड़ता है, लेकिन उपलब्ध रिकॉर्ड यह नहीं दिखाता "
            "कि दायरे में स्पष्ट महत्वपूर्ण बदलाव हुआ है।"
        ),
        "insufficient": (
            "प्रमाण अनुपलब्ध, अधूरा, असंबंधित, परस्पर विरोधी या निष्कर्ष के लिए "
            "कमज़ोर है। अपुष्ट का अर्थ गलत नहीं है।"
        )
    },
    "hinglish": {
        "supported": (
            "Kai alag retrieved passages is wording ko support karte hain. "
            "Publisher reliability aur source independence alag se assess nahi hui."
        ),
        "misleading": (
            "Retrieved passage mein eligibility ya scope ki clear condition hai "
            "jo claim ko materially narrow karti hai. Yeh complete fact-check nahi hai."
        ),
        "not_factual": "Yeh opinion ya instruction hai, checkable factual assertion nahi.",
        "opinion_split": (
            "Opinion wale hissa ko opinion maana gaya hai; alag nikale factual "
            "assertion ka assessment alag claim ke roop mein hai."
        ),
        "opinion_fact": (
            "Is opinion mein factual assertion ho sakta hai, lekin use reliably "
            "alag nahi kiya ja saka; woh assertion unverified hai."
        ),
        "conflict": (
            "Retrieved evidence claim ko support bhi karta hai aur contradict bhi. "
            "Available records conflict ko resolve nahi karte."
        ),
        "contradiction": (
            "Ek retrieved passage contradictory mark hua, lekin false verdict ke "
            "liye source quality ya claim coverage kaafi mazbooti se establish nahi hai."
        ),
        "context": (
            "Retrieved text context deta hai, lekin available record clear material "
            "scope change nahi dikhata."
        ),
        "insufficient": (
            "Evidence missing, incomplete, irrelevant, conflicting, ya verdict ke "
            "liye weak hai. Unverified ka matlab false nahi."
        )
    }
}
_SEARCH_LIMITATIONS = {
    "en": {
        "not_enabled": "Source search was disabled for this analysis.",
        "not_configured": "Source search was unavailable because no API key was configured.",
        "no_results": "No search results were returned; absence of results is not evidence against the claim.",
        "search_failed": "Source search failed; no verdict can be based on search snippets.",
        "not_searchable": "No usable claim wording was available for source discovery.",
        "not_searched_limit": "The per-analysis search request limit was reached; this claim was not searched.",
        "not_factual": "This claim was not sent to source search because it was classified as non-factual.",
        "factual_part_unclear": "A possible factual part of this opinion could not be separated reliably, so it was not searched."
    },
    "hi": {
        "not_enabled": "इस विश्लेषण के लिए स्रोत खोज बंद थी।",
        "not_configured": "API key सेट न होने के कारण स्रोत खोज उपलब्ध नहीं थी।",
        "no_results": "खोज में परिणाम नहीं मिले; परिणाम न मिलना दावे के विरुद्ध प्रमाण नहीं है।",
        "search_failed": "स्रोत खोज विफल हुई; खोज के अंशों से निष्कर्ष नहीं निकाला जा सकता।",
        "not_searchable": "स्रोत खोज के लिए दावे का उपयोगी शब्दांकन उपलब्ध नहीं था।",
        "not_searched_limit": "एक विश्लेषण में खोज अनुरोधों की सीमा पूरी हो गई; इस दावे की खोज नहीं हुई।",
        "not_factual": "दावे को गैर-तथ्यात्मक माना गया, इसलिए उसे स्रोत खोज में नहीं भेजा गया।",
        "factual_part_unclear": "इस राय के संभावित तथ्यात्मक हिस्से को भरोसे से अलग नहीं किया जा सका, इसलिए उसकी खोज नहीं हुई।"
    },
    "hinglish": {
        "not_enabled": "Is analysis ke liye source search off thi.",
        "not_configured": "API key set nahi thi, isliye source search available nahi thi.",
        "no_results": "Search results nahi mile; results ka na milna claim ke khilaaf evidence nahi hai.",
        "search_failed": "Source search fail hui; search snippets se verdict nahi diya ja sakta.",
        "not_searchable": "Source discovery ke liye usable claim wording nahi thi.",
        "not_searched_limit": "Ek analysis mein search requests ki limit poori ho gayi; is claim ki search nahi hui.",
        "not_factual": "Claim ko non-factual classify kiya gaya, isliye source search nahi hui.",
        "factual_part_unclear": "Opinion ke possible factual part ko reliably alag nahi kar sake, isliye uski search nahi hui."
    }
}
_LIMITATION_MESSAGES = {
    "en": {
        "malformed_claim": "The claim record is malformed.",
        "opinion_fact": "The factual part of this opinion could not be separated reliably.",
        "missing_claim": "The claim text was missing or malformed.",
        "missing_sources": "Source evidence was missing or malformed.",
        "malformed_source": "A malformed source record was ignored.",
        "invalid_source": "A source without a valid URL and title was not used as evidence.",
        "duplicate_url": "A duplicate source URL was not counted as an independent source.",
        "missing_assessment": "A retrieved source had no valid evidence assessment.",
        "claim_mismatch": "Evidence that did not match this retrieved claim was ignored.",
        "malformed_assessment": "A malformed evidence assessment was ignored.",
        "partial": "Partial page text was not sufficient for a claim verdict.",
        "ungrounded": "An evidence status without a grounded passage was ignored.",
        "low_overlap": "A passage without enough claim-specific wording overlap was ignored.",
        "unusable_passage": "An unusable evidence passage was ignored.",
        "duplicate_passage": "Repeated passages were not counted as separate corroboration.",
        "conflict": "Supporting and contradictory evidence are both present and unresolved.",
        "source_quality": "Source reliability and coverage are not established strongly enough for Mostly False or False.",
        "nonmaterial_context": "The source adds context, but a material qualification was not established.",
        "single_support": "One non-duplicate supporting passage is not enough for this verdict.",
        "no_relevant_evidence": "Available retrieved pages did not contain usable supporting, contradictory, or material contextual evidence.",
        "retrieval_failed": "A failed retrieval is not evidence for or against the claim.",
        "no_assessed_source": "No suitable assessed source evidence was available.",
        "independence": "Different hostnames and passages do not establish independent corroboration; publisher independence was not verified."
    },
    "hi": {
        "malformed_claim": "दावे का रिकॉर्ड सही प्रारूप में नहीं है।",
        "opinion_fact": "इस राय के तथ्यात्मक हिस्से को भरोसे से अलग नहीं किया जा सका।",
        "missing_claim": "दावे का पाठ उपलब्ध नहीं था या उसका प्रारूप गलत था।",
        "missing_sources": "स्रोत प्रमाण उपलब्ध नहीं था या उसका प्रारूप गलत था।",
        "malformed_source": "गलत प्रारूप वाले स्रोत रिकॉर्ड को नज़रअंदाज़ किया गया।",
        "invalid_source": "वैध URL और शीर्षक न होने के कारण स्रोत को प्रमाण नहीं माना गया।",
        "duplicate_url": "डुप्लिकेट स्रोत URL को स्वतंत्र स्रोत नहीं माना गया।",
        "missing_assessment": "प्राप्त स्रोत का मान्य प्रमाण-आकलन उपलब्ध नहीं था।",
        "claim_mismatch": "इस दावे से मेल न खाने वाले प्रमाण को नज़रअंदाज़ किया गया।",
        "malformed_assessment": "गलत प्रारूप वाले प्रमाण-आकलन को नज़रअंदाज़ किया गया।",
        "partial": "पेज का अधूरा पाठ दावे का निष्कर्ष निकालने के लिए पर्याप्त नहीं था।",
        "ungrounded": "मूल पाठ से जुड़ा अंश न होने के कारण प्रमाण-स्थिति नज़रअंदाज़ हुई।",
        "low_overlap": "दावे से पर्याप्त मेल न होने वाले अंश को नज़रअंदाज़ किया गया।",
        "unusable_passage": "उपयोग न किए जा सकने वाले प्रमाण-अंश को नज़रअंदाज़ किया गया।",
        "duplicate_passage": "एक जैसे अंशों को अलग-अलग समर्थन नहीं माना गया।",
        "conflict": "समर्थन और विरोध करने वाले प्रमाण दोनों हैं और मतभेद सुलझा नहीं है।",
        "source_quality": "गलत या अधिकतर गलत निष्कर्ष के लिए स्रोत विश्वसनीयता और दावे का पूरा दायरा पर्याप्त रूप से स्थापित नहीं है।",
        "nonmaterial_context": "स्रोत संदर्भ देता है, लेकिन महत्वपूर्ण शर्त का प्रभाव स्थापित नहीं हुआ।",
        "single_support": "एक अलग समर्थन-अंश इस निष्कर्ष के लिए पर्याप्त नहीं है।",
        "no_relevant_evidence": "प्राप्त पेजों में उपयोगी समर्थन, विरोध या महत्वपूर्ण संदर्भ नहीं मिला।",
        "retrieval_failed": "स्रोत प्राप्त न होना दावे के पक्ष या विरोध का प्रमाण नहीं है।",
        "no_assessed_source": "आकलन के लिए उपयुक्त स्रोत प्रमाण उपलब्ध नहीं था।",
        "independence": "अलग होस्टनाम और अंश स्वतंत्र पुष्टि साबित नहीं करते; प्रकाशकों की स्वतंत्रता जाँची नहीं गई।"
    },
    "hinglish": {
        "malformed_claim": "Claim record ka format valid nahi hai.",
        "opinion_fact": "Opinion ke factual part ko reliably alag nahi kiya ja saka.",
        "missing_claim": "Claim text missing tha ya uska format invalid tha.",
        "missing_sources": "Source evidence missing tha ya uska format invalid tha.",
        "malformed_source": "Invalid format wala source record ignore kiya gaya.",
        "invalid_source": "Valid URL aur title na hone par source ko evidence nahi maana gaya.",
        "duplicate_url": "Duplicate source URL ko independent source nahi maana gaya.",
        "missing_assessment": "Retrieved source ka valid evidence assessment nahi tha.",
        "claim_mismatch": "Is claim se match na hone wala evidence ignore kiya gaya.",
        "malformed_assessment": "Invalid format wala evidence assessment ignore kiya gaya.",
        "partial": "Partial page text claim verdict ke liye sufficient nahi tha.",
        "ungrounded": "Grounded passage ke bina evidence status ignore hua.",
        "low_overlap": "Claim-specific wording se enough match na hone wala passage ignore hua.",
        "unusable_passage": "Use na ho sakne wala evidence passage ignore hua.",
        "duplicate_passage": "Repeated passages ko alag corroboration nahi maana gaya.",
        "conflict": "Supporting aur contradicting evidence dono hain, aur conflict resolve nahi hua.",
        "source_quality": "Mostly False ya False ke liye source reliability aur claim coverage enough establish nahi hai.",
        "nonmaterial_context": "Source context deta hai, par material qualification establish nahi hui.",
        "single_support": "Ek non-duplicate supporting passage is verdict ke liye enough nahi hai.",
        "no_relevant_evidence": "Retrieved pages mein useful supporting, contradicting, ya material context evidence nahi mila.",
        "retrieval_failed": "Source retrieve na hona claim ke support ya contradiction ka evidence nahi hai.",
        "no_assessed_source": "Suitable assessed source evidence available nahi tha.",
        "independence": "Alag hostnames aur passages independent corroboration prove nahi karte; publishers ki independence verify nahi hui."
    }
}

_ALLOWED_EVIDENCE_STATUSES = {
    "Supports",
    "Contradicts",
    "Contextualizes",
    "Does Not Address",
    "Insufficient Information",
    "Retrieval Failed"
}
_TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid"
}
_UNIVERSAL_PATTERN = re.compile(
    r"\b(?:all|every|each|everyone|always|never|guarantee[sd]?)\b|"
    r"सभी|हर|प्रत्येक|हमेशा|गारंटी|"
    r"\b(?:sabhi|har|hamesha|guarantee[sd]?)\b",
    re.IGNORECASE
)
_QUALIFICATION_PATTERN = re.compile(
    r"\b(?:only|some|eligible|limited|subject to|except|may not|not all)\b|"
    r"केवल|सिर्फ|कुछ|पात्र|सीमित|के अलावा|"
    r"\b(?:sirf|kuch|keval|patra|seemit)\b",
    re.IGNORECASE
)
_FACTUAL_CUE_PATTERN = re.compile(
    r"\b(?:because|since|due to|costs?|has|have|was|were|announced|"
    r"said|approved|received|provides?|causes?)\b|₹|\b\d",
    re.IGNORECASE
)
_OPINION_CAUSAL_PATTERN = re.compile(
    r"\b(?:because|since|due to|kyunki)\b|क्योंकि",
    re.IGNORECASE
)
_FACTUAL_CLAUSE_PATTERN = re.compile(
    r"\b(?:costs?|announced|approved|received|provides?|causes?|contains?|"
    r"increased|decreased|occurred|signed|launched|opened|located|"
    r"was signed|were signed|has received)\b|₹|\b\d",
    re.IGNORECASE
)
_TOKEN_PATTERN = re.compile(r"\d+(?:[.,]\d+)*|[^\W_]+", re.UNICODE)
_STOP_WORDS = {
    "all", "and", "are", "because", "but", "each", "every", "for", "from",
    "has", "have", "is", "it", "its", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "will", "with", "सभी", "और", "है", "हैं",
    "का", "की", "के", "को", "में", "से", "था", "थी", "थे", "यह", "इस"
}


def _canonical_source_url(value):
    if not isinstance(value, str) or not value:
        return ""
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme.casefold() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            return ""
        port = parsed.port
    except ValueError:
        return ""

    scheme = parsed.scheme.casefold()
    hostname = parsed.hostname.rstrip(".").casefold()
    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port and port != (443 if scheme == "https" else 80):
        netloc = f"{netloc}:{port}"
    query = urlencode(sorted(
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_")
        and key.casefold() not in _TRACKING_PARAMETERS
    ))
    return urlunsplit((scheme, netloc, parsed.path or "/", query, ""))


def _reference(source, index, passage=""):
    hostname = urlsplit(source["url"]).hostname or ""
    return {
        "url": source["url"],
        "title": source["title"],
        "publisher": hostname,
        "publication_date": source.get("retrieved_publication_date", ""),
        "passage": passage,
        "source_index": index
    }


def _passage_signature(passage):
    tokens = _TOKEN_PATTERN.findall(passage.casefold())
    return " ".join(tokens)


def _claim_terms(text):
    return {
        token.casefold()
        for token in _TOKEN_PATTERN.findall(text)
        if (
            len(token) >= 3
            and token.casefold() not in _STOP_WORDS
        )
    }


def _passage_matches_claim(claim_text, passage):
    claim_terms = _claim_terms(claim_text)
    passage_terms = _claim_terms(passage)
    shared = claim_terms & passage_terms
    return (
        len(shared) >= 2
        and len(shared) / max(1, len(claim_terms)) >= 0.3
    )


def _is_material_scope_change(claim_text, passage):
    return bool(
        _UNIVERSAL_PATTERN.search(claim_text)
        and _QUALIFICATION_PATTERN.search(passage)
    )


def _contains_factual_opinion_assertion(claim_text):
    return bool(_FACTUAL_CUE_PATTERN.search(claim_text))


def opinion_has_unseparated_factual_assertion(claim):
    return (
        isinstance(claim, dict)
        and claim.get("claim_type") == "opinion"
        and not claim.get("factual_component_extracted")
        and isinstance(claim.get("claim"), str)
        and _contains_factual_opinion_assertion(claim["claim"])
    )


def separate_explicit_opinion_facts(claims):
    """Extract clearly marked causal fact clauses without rewriting their wording."""
    if not isinstance(claims, list):
        return []
    existing = {
        (
            item.get("claim", "").strip().casefold(),
            item.get("claim_type")
        )
        for item in claims
        if isinstance(item, dict) and isinstance(item.get("claim"), str)
    }
    derived = []
    for item in claims:
        if (
            not isinstance(item, dict)
            or item.get("claim_type") != "opinion"
            or not isinstance(item.get("claim"), str)
        ):
            continue
        original = item["claim"]
        marker = _OPINION_CAUSAL_PATTERN.search(original)
        if not marker:
            continue
        factual_clause = original[marker.end():].strip()
        if not factual_clause or not _FACTUAL_CLAUSE_PATTERN.search(factual_clause):
            continue
        key = (factual_clause.casefold(), "factual_assertion")
        if key in existing:
            item["factual_component_extracted"] = True
            continue
        derived.append({
            "claim": factual_clause,
            "normalized_wording": factual_clause,
            "original_wording": original,
            "evidence": factual_clause,
            "context": original,
            "claim_type": "factual_assertion",
            "categories": (
                item.get("categories", [])
                if isinstance(item.get("categories"), list)
                else []
            ),
            "original_language": item.get("original_language", "unknown"),
            "extraction_method": "opinion_clause"
        })
        existing.add(key)
        item["factual_component_extracted"] = True
    return derived


def _base_assessment(
    category,
    explanation,
    sufficient=False,
    category_code="unverified"
):
    return {
        "category_code": category_code,
        "category": category,
        "explanation": explanation,
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "contextual_evidence": [],
        "other_evidence": [],
        "retrieval_failures": [],
        "limitations": [],
        "evidence_sufficient": sufficient
    }


def _add_limitation(result, locale, key):
    result["limitations"].append(_LIMITATION_MESSAGES[locale][key])


def assess_claim_verdict(claim, language="en"):
    """Return a cautious verdict from the retrieved evidence records only.

    The current source schema has no validated source-quality, independence, or
    compound-component metadata. Consequently, it does not issue Supported by
    Evidence, Mostly True, Mostly False, or False verdicts automatically.
    """
    locale = language if language in _VERDICT_LABELS else "en"
    labels = _VERDICT_LABELS[locale]
    messages = _EXPLANATIONS[locale]
    if not isinstance(claim, dict):
        result = _base_assessment(labels["unverified"], messages["insufficient"])
        _add_limitation(result, locale, "malformed_claim")
        return result

    claim_text = claim.get("claim", "")
    claim_text = claim_text if isinstance(claim_text, str) else ""
    claim_type = claim.get("claim_type")
    if claim_type in {"opinion", "instruction"}:
        if claim.get("factual_component_extracted"):
            return _base_assessment(
                labels["not_factual"],
                messages["opinion_split"],
                sufficient=True,
                category_code="not_factual"
            )
        if claim_type == "instruction" or not _contains_factual_opinion_assertion(claim_text):
            return _base_assessment(
                labels["not_factual"],
                messages["not_factual"],
                sufficient=True,
                category_code="not_factual"
            )
        result = _base_assessment(labels["unverified"], messages["opinion_fact"])
        _add_limitation(result, locale, "opinion_fact")
        return result

    result = _base_assessment(labels["unverified"], messages["insufficient"])
    if not claim_text.strip():
        _add_limitation(result, locale, "missing_claim")
        return result
    search_status = claim.get("source_search_status")
    if search_status in _SEARCH_LIMITATIONS[locale]:
        result["limitations"].append(_SEARCH_LIMITATIONS[locale][search_status])
    raw_sources = claim.get("sources")
    if not isinstance(raw_sources, list):
        _add_limitation(result, locale, "missing_sources")
        return result

    seen_urls = set()
    seen_passages = {}
    incomplete_review = False
    for index, source in enumerate(raw_sources):
        if not isinstance(source, dict):
            _add_limitation(result, locale, "malformed_source")
            incomplete_review = True
            continue
        url = _canonical_source_url(source.get("url"))
        title = source.get("title")
        if not url or not isinstance(title, str) or not title.strip():
            _add_limitation(result, locale, "invalid_source")
            incomplete_review = True
            continue
        if url in seen_urls:
            _add_limitation(result, locale, "duplicate_url")
        else:
            seen_urls.add(url)

        retrieval_status = source.get("retrieval_status")
        assessment = source.get("evidence_assessment")
        if retrieval_status != "retrieved":
            result["retrieval_failures"].append({
                "url": source["url"],
                "title": title.strip(),
                "status": retrieval_status or "unknown",
                "limitation": source.get("limitations", "")
            })
            continue
        if not isinstance(assessment, dict):
            _add_limitation(result, locale, "missing_assessment")
            incomplete_review = True
            continue
        if (
            assessment.get("retrieval_status") != "retrieved"
            or assessment.get("claim") != claim_text
        ):
            _add_limitation(result, locale, "claim_mismatch")
            incomplete_review = True
            continue
        status = assessment.get("status")
        passages = assessment.get("passages")
        if (
            status not in _ALLOWED_EVIDENCE_STATUSES
            or not isinstance(passages, list)
            or any(not isinstance(passage, str) for passage in passages)
        ):
            _add_limitation(result, locale, "malformed_assessment")
            incomplete_review = True
            continue
        if status == "Retrieval Failed":
            result["retrieval_failures"].append({
                "url": source["url"],
                "title": title.strip(),
                "status": "retrieval_failed",
                "limitation": assessment.get("explanation", "")
            })
            continue
        if status in {"Supports", "Contradicts", "Contextualizes"}:
            if assessment.get("partial_content") or source.get("partial_content"):
                _add_limitation(result, locale, "partial")
                incomplete_review = True
                continue
            passage = next(
                (value.strip() for value in passages if value.strip()),
                ""
            )
            if not passage:
                _add_limitation(result, locale, "ungrounded")
                continue
            if not _passage_matches_claim(claim_text, passage):
                _add_limitation(result, locale, "low_overlap")
                continue
            signature = _passage_signature(passage)
            if not signature:
                _add_limitation(result, locale, "unusable_passage")
                continue
            if signature in seen_passages and seen_passages[signature] == status:
                _add_limitation(result, locale, "duplicate_passage")
                continue
            seen_passages[signature] = status
            evidence = _reference(source, index, passage[:600])
        else:
            evidence = _reference(source, index)

        if status == "Supports":
            result["supporting_evidence"].append(evidence)
        elif status == "Contradicts":
            result["contradicting_evidence"].append(evidence)
        elif status == "Contextualizes":
            result["contextual_evidence"].append(evidence)
        else:
            result["other_evidence"].append({
                **evidence,
                "status": status
            })

    has_support = bool(result["supporting_evidence"])
    has_contradiction = bool(result["contradicting_evidence"])
    has_context = bool(result["contextual_evidence"])
    if has_support and has_contradiction:
        result["explanation"] = messages["conflict"]
        _add_limitation(result, locale, "conflict")
    elif result["retrieval_failures"] or incomplete_review:
        result["explanation"] = messages["insufficient"]
    elif has_contradiction:
        result["explanation"] = messages["contradiction"]
        _add_limitation(result, locale, "source_quality")
    elif has_context:
        if any(
            _is_material_scope_change(claim_text, evidence["passage"])
            for evidence in result["contextual_evidence"]
        ):
            result["category"] = labels["misleading"]
            result["category_code"] = "misleading"
            result["explanation"] = messages["misleading"]
            result["evidence_sufficient"] = True
        else:
            result["explanation"] = messages["context"]
            _add_limitation(result, locale, "nonmaterial_context")
    elif has_support:
        if len(result["supporting_evidence"]) >= 2:
            _add_limitation(result, locale, "independence")
        else:
            _add_limitation(result, locale, "single_support")
    elif result["other_evidence"]:
        _add_limitation(result, locale, "no_relevant_evidence")

    if result["retrieval_failures"]:
        _add_limitation(result, locale, "retrieval_failed")
    if result["category"] == labels["unverified"] and not result["limitations"]:
        _add_limitation(result, locale, "no_assessed_source")
    return result
