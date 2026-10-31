import logging
import os
import re
import time
from datetime import date as date_type
from typing import Protocol
from urllib.parse import urlsplit

import requests

from modules.source_retriever import (
    SafeSourceRetriever,
    SourceRetrievalError,
    assess_claim_against_source
)
from modules.verdict_engine import (
    assess_claim_verdict,
    opinion_has_unseparated_factual_assertion,
    separate_explicit_opinion_facts
)

BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"
MAX_RESULTS_PER_CLAIM = 3
MAX_SEARCH_REQUESTS_PER_ANALYSIS = 9
MAX_SOURCE_FETCHES_PER_ANALYSIS = 9
SOURCE_REVIEW_TIMEOUT_SECONDS = 30
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:$|T)")
_QUERY_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "before", "by",
    "can", "could", "did", "do", "does", "for", "from", "has", "have",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "will", "with"
}
_CATEGORY_QUERY_HINTS = {
    "government schemes": "official announcement eligibility rules",
    "science": "scientific evidence research",
    "biology": "scientific evidence research",
    "health": "medical research public health systematic review",
    "nutrition": "medical research nutrition systematic review",
    "history": "primary sources historical records",
    "finance": "financial regulator official filings",
    "politics": "transcript interview original statement",
    "education": "official notice eligibility requirements",
    "cybersecurity": "security advisory technical documentation",
    "environment": "scientific evidence environmental research"
}
_URL_IN_QUERY = re.compile(
    r"""(?i)(?:\b(?:https?://|www\.)[^\s<>'"]+|"""
    r"""(?<![@\w])(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s<>'"]*)?)"""
)
_MESSAGES = {
    "en": {
        "no_claims": "No factual claims were available to search.",
        "not_enabled": (
            "Live source search is off. Claims were not sent to an external "
            "search provider and remain unverified."
        ),
        "not_configured": (
            "Source discovery is unavailable. Set TAVILY_API_KEY or "
            "BRAVE_SEARCH_API_KEY in the Flask terminal to discover source leads."
        ),
        "completed": (
            "Search results are leads, not proof. Cautious claim verdicts use "
            "retrieved passages; publisher reliability is not independently assessed."
        ),
        "no_results": (
            "No search results were returned. This does not show that a claim "
            "is true or false."
        ),
        "failed": (
            "Live source search could not be completed. Claims remain "
            "unverified; check the Flask terminal and search-provider access."
        ),
        "unverified": (
            "Search results alone are not evidence of truth or falsity. "
            "Review original and independent sources before reaching a verdict."
        ),
        "source_relation": (
            "Search result lead; evidence assessment is based only on the retrieved text."
        ),
        "search_summary": (
            "Provider(s) used: {providers}. Claim queries attempted: {queries}. "
            "Provider requests: {requests}. Results found: {results}. "
            "Source pages retrieved: {retrieved}/{pages}. Errors: {errors}."
        )
    },
    "hi": {
        "no_claims": "खोजने के लिए कोई तथ्यात्मक दावा नहीं मिला।",
        "not_enabled": (
            "लाइव स्रोत खोज बंद है। दावे किसी बाहरी search provider को नहीं भेजे गए "
            "और अभी अपुष्ट हैं।"
        ),
        "not_configured": (
            "स्रोत खोज उपलब्ध नहीं है। स्रोत खोजने के लिए Flask terminal में "
            "TAVILY_API_KEY या BRAVE_SEARCH_API_KEY सेट करें।"
        ),
        "completed": (
            "खोज परिणाम प्रमाण नहीं, केवल स्रोत-संकेत हैं। सावधानीपूर्ण निष्कर्ष "
            "प्राप्त अंशों पर आधारित हैं; प्रकाशक की विश्वसनीयता की अलग से जाँच नहीं हुई।"
        ),
        "no_results": (
            "खोज में कोई परिणाम नहीं मिला। इससे दावा सही या गलत साबित नहीं होता।"
        ),
        "failed": (
            "लाइव स्रोत खोज पूरी नहीं हो सकी। दावे अपुष्ट हैं; Flask terminal "
            "और search provider की पहुँच जाँचें।"
        ),
        "unverified": (
            "केवल खोज परिणाम किसी दावे को सही या गलत साबित नहीं करते। निष्कर्ष "
            "से पहले मूल और स्वतंत्र स्रोत जाँचें।"
        ),
        "source_relation": (
            "खोज परिणाम का संकेत; प्रमाण-आकलन केवल प्राप्त पाठ पर आधारित है।"
        ),
        "search_summary": (
            "इस्तेमाल provider: {providers}। खोजे गए दावे: {queries}। "
            "Provider requests: {requests}। परिणाम: {results}। "
            "प्राप्त स्रोत पेज: {retrieved}/{pages}। त्रुटियाँ: {errors}।"
        )
    },
    "hinglish": {
        "no_claims": "Search karne ke liye koi factual claim nahi mila.",
        "not_enabled": (
            "Live source search off hai. Claims kisi external search provider ko "
            "nahi bheje gaye aur abhi unverified hain."
        ),
        "not_configured": (
            "Source discovery available nahi hai. Flask terminal mein "
            "TAVILY_API_KEY ya BRAVE_SEARCH_API_KEY set karein."
        ),
        "completed": (
            "Search results leads hain, proof nahi. Cautious claim verdicts "
            "retrieved passages par based hain; publisher reliability alag se assess nahi hui."
        ),
        "no_results": (
            "Search se koi result nahi mila. Isse claim sahi ya galat prove nahi hota."
        ),
        "failed": (
            "Live source search complete nahi hui. Claims unverified hain; "
            "Flask terminal aur provider access check karein."
        ),
        "unverified": (
            "Sirf search results claim ko sahi ya galat prove nahi karte. "
            "Verdict se pehle original aur independent sources review karein."
        ),
        "source_relation": (
            "Search result lead; assessment sirf retrieved text par based hai."
        ),
        "search_summary": (
            "Used provider(s): {providers}. Claim queries attempted: {queries}. "
            "Provider requests: {requests}. Results found: {results}. "
            "Source pages retrieved: {retrieved}/{pages}. Errors: {errors}."
        )
    }
}

logger = logging.getLogger(__name__)


class SearchProvider(Protocol):
    def search(self, query: str) -> list[dict]:
        """Return source leads for one claim-based query."""


class BraveSearchProvider:
    """Fetch search-result leads from Brave; never retrieves result pages."""

    provider_name = "Brave Search"

    def __init__(self, api_key, session=None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("A Brave Search API key is required.")
        self.api_key = api_key.strip()
        self.session = session or requests

    def search(self, query):
        response = self.session.get(
            BRAVE_SEARCH_ENDPOINT,
            params={"q": query, "count": MAX_RESULTS_PER_CLAIM},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key
            },
            timeout=(3, 10)
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Search provider returned an invalid response.")

        web_results = payload.get("web")
        if not isinstance(web_results, dict):
            raise ValueError("Search provider response is missing web results.")
        results = web_results.get("results")
        if not isinstance(results, list):
            raise ValueError("Search provider response has invalid web results.")
        normalized = [
            source
            for item in results
            if (
                source := _normalize_result(
                    item,
                    query=query,
                    provider_name=self.provider_name
                )
            ) is not None
        ]
        if results and not normalized:
            raise ValueError("Search provider results contained no usable source leads.")
        return normalized[:MAX_RESULTS_PER_CLAIM]


class TavilySearchProvider:
    """Fetch search-result leads from Tavily; never retrieves result pages."""

    provider_name = "Tavily Search"

    def __init__(self, api_key, session=None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("A Tavily API key is required.")
        self.api_key = api_key.strip()
        self.session = session or requests

    def search(self, query):
        response = self.session.post(
            TAVILY_SEARCH_ENDPOINT,
            json={
                "query": query,
                "search_depth": "basic",
                "max_results": MAX_RESULTS_PER_CLAIM,
                "include_published_date": True,
                "include_answer": False,
                "include_raw_content": False
            },
            headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json"
            },
            timeout=(3, 10)
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Search provider returned an invalid response.")

        results = payload.get("results")
        if not isinstance(results, list):
            raise ValueError("Search provider response has invalid results.")
        normalized = [
            source
            for item in results
            if (
                source := _normalize_result(
                    {
                        **item,
                        "summary": item.get("content"),
                        "date": item.get("published_date")
                    } if isinstance(item, dict) else item,
                    query=query,
                    provider_name=self.provider_name
                )
            ) is not None
        ]
        if results and not normalized:
            raise ValueError("Search provider results contained no usable source leads.")
        return normalized[:MAX_RESULTS_PER_CLAIM]


def _normalize_result(item, query="", provider_name="Brave Search"):
    if not isinstance(item, dict):
        return None

    title = item.get("title")
    raw_url = item.get("url")
    description = item.get("description", item.get("summary"))
    if not all(isinstance(value, str) and value.strip() for value in (title, raw_url)):
        return None

    try:
        parsed_url = urlsplit(raw_url.strip())
    except ValueError:
        return None
    if (
        parsed_url.scheme.lower() != "https"
        or not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
    ):
        return None

    date = ""
    date_supplied = False
    for candidate in (item.get("date"), item.get("published"), item.get("page_age")):
        if candidate not in (None, ""):
            date_supplied = True
        if isinstance(candidate, str) and _ISO_DATE.match(candidate):
            try:
                date = date_type.fromisoformat(candidate[:10]).isoformat()
            except ValueError:
                continue
            break

    return {
        "title": title.strip()[:300],
        "publisher": parsed_url.hostname,
        "date": date,
        "url": raw_url.strip()[:2000],
        "summary": (
            description.strip()[:1000]
            if isinstance(description, str)
            else ""
        ),
        "query": query[:500],
        "provider": provider_name,
        "date_status": "provided" if date else (
            "unrecognized" if date_supplied else "not_provided"
        ),
        "retrieval_status": "not_retrieved",
        "limitations": (
            "Search-result metadata only; the destination page was not fetched "
            "or assessed."
        ),
        "source_type": "Search result lead (not independently assessed)",
        "relationship": "Not assessed"
    }


def _clean_query_text(value):
    if not isinstance(value, str):
        return ""
    return " ".join(_URL_IN_QUERY.sub(" ", value).split()).strip()


def _query_for_claim(claim):
    if not isinstance(claim, dict):
        return ""
    wording = claim.get("normalized_wording") or claim.get("claim")
    if not isinstance(wording, str):
        return ""
    query_parts = []

    def add_part(value):
        cleaned = _clean_query_text(value)
        current_query = " ".join(query_parts).casefold()
        if cleaned and cleaned.casefold() not in current_query:
            query_parts.append(cleaned)

    add_part(wording)
    speaker = claim.get("alleged_speaker")
    if isinstance(speaker, str) and speaker.strip():
        add_part(speaker)

    claim_type = claim.get("claim_type")
    if claim_type == "attributed_quote":
        original_wording = claim.get("original_wording")
        if isinstance(original_wording, str):
            quote_text = re.sub(
                r"(?i)^.*?\b(?:said|stated|announced|claimed|declared|"
                r"wrote|posted|told)\b\s*(?:that\s+)?",
                "",
                original_wording
            )
            add_part(quote_text.strip(" \"'“”‘’.,;:"))

    entities = claim.get("entities")
    if isinstance(entities, dict):
        for entity_type in ("people", "organizations", "dates", "locations", "amounts"):
            values = entities.get(entity_type, [])
            if isinstance(values, str):
                values = [values]
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, str) and value.strip():
                    add_part(value)

    if claim_type == "attributed_quote":
        context = claim.get("context")
        if isinstance(context, str):
            context_words = [
                word for word in re.findall(
                    r"[\w₹%.-]+",
                    _clean_query_text(context)
                )
                if len(word) > 2 and word.casefold() not in _QUERY_STOP_WORDS
            ]
            if context_words:
                add_part(" ".join(context_words[:12]))
    elif claim.get("extraction_method") == "opinion_clause":
        context = claim.get("context")
        if isinstance(context, str):
            add_part(context)

    categories = claim.get("categories")
    if isinstance(categories, str):
        categories = [categories]
    if isinstance(categories, list):
        for category in categories:
            if isinstance(category, str):
                if category.casefold() == "politics" and claim_type != "attributed_quote":
                    continue
                hint = _CATEGORY_QUERY_HINTS.get(category.casefold())
                if hint:
                    add_part(hint)

    return " ".join(part for part in query_parts if part)[:300]


def _result_relevance_score(source, claim):
    searchable_text = " ".join(
        str(source.get(field, ""))
        for field in ("title", "publisher", "summary")
    ).casefold()
    claim_text = " ".join(
        str(claim.get(field, ""))
        for field in ("claim", "normalized_wording", "alleged_speaker")
    )
    tokens = {
        token.casefold()
        for token in re.findall(r"[\w₹%.-]+", claim_text)
        if len(token) > 2 and token.casefold() not in _QUERY_STOP_WORDS
    }
    score = sum(1 for token in tokens if token in searchable_text)

    publisher = str(source.get("publisher", "")).casefold()
    categories = claim.get("categories", [])
    if isinstance(categories, str):
        categories = [categories]
    categories = {
        category.casefold()
        for category in categories
        if isinstance(category, str)
    } if isinstance(categories, list) else set()
    domain_hints = {
        "government schemes": (".gov", ".gov.in", ".gov.uk"),
        "science": (".edu", ".edu.in", ".gov", ".gov.in", "nature.com", "science.org"),
        "biology": (".edu", ".edu.in", ".gov", ".gov.in", "nature.com", "science.org"),
        "health": ("who.int", ".gov", ".gov.in", ".edu", ".edu.in", "pubmed.ncbi.nlm.nih.gov", "thelancet.com"),
        "nutrition": ("who.int", ".gov", ".gov.in", ".edu", ".edu.in", "pubmed.ncbi.nlm.nih.gov"),
        "history": (".edu", ".edu.in", "archives.gov", "loc.gov", "nationalarchives.gov.uk"),
        "finance": (".gov", ".gov.in", "sec.gov", "rbi.org.in", "finra.org"),
        "cybersecurity": (".gov", ".gov.in", "cert.org", "cisa.gov"),
        "environment": (".gov", ".gov.in", ".edu", ".edu.in", "nature.com", "science.org")
    }

    def domain_matches(hint):
        if hint.startswith("."):
            return publisher.endswith(hint)
        return publisher == hint or publisher.endswith(f".{hint}")

    for category in categories:
        if any(domain_matches(hint) for hint in domain_hints.get(category, ())):
            score += 2
    return score


def _rank_results(results, claim):
    ranked = sorted(
        results,
        key=lambda source: _result_relevance_score(source, claim),
        reverse=True
    )
    diverse = []
    remaining = []
    seen_urls = set()
    seen_publishers = set()
    for source in ranked:
        url = str(source.get("url", ""))
        if url in seen_urls:
            continue
        seen_urls.add(url)
        publisher = str(source.get("publisher", "")).casefold()
        if publisher and publisher not in seen_publishers:
            diverse.append(source)
            seen_publishers.add(publisher)
        else:
            remaining.append(source)
    return diverse + remaining


def _provider_configuration():
    return {
        "tavily_configured": bool(os.environ.get("TAVILY_API_KEY", "").strip()),
        "brave_configured": bool(os.environ.get("BRAVE_SEARCH_API_KEY", "").strip())
    }


def discover_claim_sources(
    claims,
    language="en",
    provider: SearchProvider | None = None,
    enabled=False,
    retriever=None
):
    """Attach source leads and conservative claim-level verdict assessments."""
    messages = _MESSAGES.get(language, _MESSAGES["en"])
    provider_configuration = _provider_configuration()
    logger.info(
        "Source search configuration: tavily_present=%s brave_present=%s",
        provider_configuration["tavily_configured"],
        provider_configuration["brave_configured"]
    )
    claim_list = claims if isinstance(claims, list) else []
    claim_list.extend(separate_explicit_opinion_facts(claim_list))
    if not claim_list:
        return {
            "status": "not_applicable",
            "message": messages["no_claims"]
        }

    search_providers = [provider] if provider is not None else []
    for claim in claim_list:
        _set_claim_result(
            claim,
            [],
            messages["unverified"],
            "not_enabled",
            language
        )
    if not enabled:
        return {
            "status": "not_enabled",
            "message": messages["not_enabled"]
        }

    if not search_providers:
        tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
        brave_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
        if tavily_key:
            search_providers.append(TavilySearchProvider(tavily_key))
        if brave_key:
            search_providers.append(BraveSearchProvider(brave_key))
        if not search_providers:
            for claim in claim_list:
                _set_claim_result(
                    claim,
                    [],
                    messages["unverified"],
                    "not_configured",
                    language
                )
            return {
                "status": "not_configured",
                "message": messages["not_configured"],
                "provider_used": [],
                "queries_attempted": 0,
                "results_found": 0,
                "errors": [],
                "provider_configuration": provider_configuration
            }

    source_retriever = retriever or getattr(
        search_providers[0],
        "source_retriever",
        None
    ) or SafeSourceRetriever()
    retrieval_cache = {}
    review_deadline = time.monotonic() + SOURCE_REVIEW_TIMEOUT_SECONDS
    retrieval_attempts = 0
    retrieved_pages = 0
    retrieved_urls = set()
    retrieval_failures = 0

    for claim in claim_list:
        _set_claim_result(
            claim,
            [],
            messages["unverified"],
            "not_searched",
            language
        )

    result_count = 0
    source_urls_found = set()
    had_error = False
    searchable_claims = 0
    provider_requests = 0
    providers_used = []
    search_errors = []
    search_limit_reached = False
    for claim_index, claim in enumerate(claim_list):
        if not isinstance(claim, dict):
            continue
        if claim.get("claim_type") in {"opinion", "instruction"}:
            search_status = (
                "factual_part_unclear"
                if opinion_has_unseparated_factual_assertion(claim)
                else "not_factual"
            )
            _set_claim_result(
                claim,
                [],
                messages["unverified"],
                search_status,
                language
            )
            continue
        query = _query_for_claim(claim)
        if not query:
            _set_claim_result(
                claim,
                [],
                messages["unverified"],
                "not_searchable",
                language
            )
            continue
        if (
            searchable_claims >= MAX_SEARCH_REQUESTS_PER_ANALYSIS
            or provider_requests >= MAX_SEARCH_REQUESTS_PER_ANALYSIS
        ):
            search_limit_reached = True
            _set_claim_result(
                claim,
                [],
                messages["unverified"],
                "not_searched_limit",
                language
            )
            continue
        searchable_claims += 1
        claim_had_error = False
        active_provider = None
        results = None
        last_error = None
        provider_limit_reached = False
        for candidate_provider in search_providers:
            if provider_requests >= MAX_SEARCH_REQUESTS_PER_ANALYSIS:
                provider_limit_reached = True
                search_limit_reached = True
                break
            provider_requests += 1
            try:
                results = candidate_provider.search(query)
            except (requests.RequestException, ValueError, TypeError) as error:
                last_error = error
                response_status = getattr(
                    getattr(error, "response", None),
                    "status_code",
                    None
                )
                search_errors.append({
                    "provider": getattr(
                        candidate_provider,
                        "provider_name",
                        type(candidate_provider).__name__
                    ),
                    "type": type(error).__name__,
                    "http_status": response_status
                })
                logger.warning(
                    "Claim-source search failed (%s, HTTP status %s).",
                    type(error).__name__,
                    response_status if response_status is not None else "n/a"
                )
                continue
            if not isinstance(results, list):
                last_error = TypeError(
                    "Search provider returned a non-list result."
                )
                search_errors.append({
                    "provider": getattr(
                        candidate_provider,
                        "provider_name",
                        type(candidate_provider).__name__
                    ),
                    "type": "TypeError",
                    "http_status": None
                })
                continue
            active_provider = candidate_provider
            break

        if active_provider is None:
            had_error = bool(last_error)
            claim_had_error = bool(last_error)
            response_status = getattr(
                getattr(last_error, "response", None),
                "status_code",
                None
            )
            if provider_limit_reached:
                _set_claim_result(
                    claim,
                    [],
                    messages["unverified"],
                    "search_failed" if last_error else "not_searched_limit",
                    language
                )
                for pending_claim in claim_list[claim_index + 1:]:
                    pending_status = (
                        "not_factual"
                        if isinstance(pending_claim, dict)
                        and pending_claim.get("claim_type") in {"opinion", "instruction"}
                        else "not_searched_limit"
                    )
                    _set_claim_result(
                        pending_claim,
                        [],
                        messages["unverified"],
                        pending_status,
                        language
                    )
                if last_error:
                    had_error = True
                    claim_had_error = True
                break
            failed_status = (
                "not_searched_rate_limited"
                if response_status == 429
                else "not_searched_provider_error"
            )
            _set_claim_result(
                claim,
                [],
                messages["unverified"],
                "search_failed",
                language
            )
            for pending_claim in claim_list[claim_index + 1:]:
                pending_status = (
                    "not_factual"
                    if isinstance(pending_claim, dict)
                    and pending_claim.get("claim_type") in {"opinion", "instruction"}
                    else failed_status
                )
                _set_claim_result(
                    pending_claim,
                    [],
                    messages["unverified"],
                    pending_status,
                    language
                )
            break
        provider_name = getattr(
            active_provider,
            "provider_name",
            type(active_provider).__name__
        )
        if provider_name not in providers_used:
            providers_used.append(provider_name)
        normalized = []
        for item in results:
            source = _normalize_result(
                item,
                query=query,
                provider_name=provider_name
            )
            if source is not None:
                normalized.append(source)
        normalized = _rank_results(normalized, claim)[:MAX_RESULTS_PER_CLAIM]
        for source in normalized:
            source["relevance"] = messages["source_relation"]
            source_url = source["url"]
            source_urls_found.add(source_url)
            cache_key = source_url
            retrieval = retrieval_cache.get(cache_key)
            if retrieval is None:
                if (
                    retrieval_attempts >= MAX_SOURCE_FETCHES_PER_ANALYSIS
                    or time.monotonic() >= review_deadline
                ):
                    retrieval = {
                        "retrieval_status": "not_attempted_limit",
                        "retrieved_text": "",
                        "retrieved_title": "",
                        "publication_date": "",
                        "content_type": "",
                        "source_type": "",
                        "partial_content": False,
                        "limitations": (
                            "The per-analysis source review limit was reached; "
                            "this page was not retrieved."
                        )
                    }
                else:
                    retrieval_attempts += 1
                    try:
                        retrieval = source_retriever.fetch(
                            source_url,
                            deadline=review_deadline
                        )
                    except (
                        SourceRetrievalError,
                        requests.RequestException,
                        OSError,
                        TimeoutError,
                        ValueError
                    ) as error:
                        retrieval = {
                            "retrieval_status": getattr(
                                error,
                                "status",
                                "retrieval_failed"
                            ),
                            "retrieved_text": "",
                            "retrieved_title": "",
                            "publication_date": "",
                            "content_type": "",
                            "source_type": "",
                            "partial_content": False,
                            "limitations": (
                                "The source could not be retrieved safely."
                            )
                        }
                    if not isinstance(retrieval, dict):
                        retrieval = {
                            "retrieval_status": "retrieval_failed",
                            "retrieved_text": "",
                            "retrieved_title": "",
                            "publication_date": "",
                            "content_type": "",
                            "source_type": "",
                            "partial_content": False,
                            "limitations": (
                                "The source retriever returned an invalid response."
                            )
                        }
                    retrieval_cache[cache_key] = retrieval

            source["retrieval_status"] = retrieval.get(
                "retrieval_status",
                "retrieval_failed"
            )
            source["retrieved_title"] = retrieval.get("retrieved_title", "")
            source["retrieved_publication_date"] = retrieval.get(
                "publication_date",
                ""
            )
            source["retrieved_source_type"] = retrieval.get("source_type", "")
            source["retrieved_content_type"] = retrieval.get("content_type", "")
            source["partial_content"] = bool(retrieval.get("partial_content"))
            source["limitations"] = retrieval.get(
                "limitations",
                "The source could not be retrieved safely."
            )
            source["evidence_assessment"] = assess_claim_against_source(
                claim,
                retrieval,
                language
            )
            if source["retrieval_status"] == "retrieved":
                retrieved_urls.add(source_url)
            elif source["retrieval_status"] != "not_attempted_limit":
                retrieval_failures += 1
        result_count += len(normalized)
        _set_claim_result(
            claim,
            normalized,
            messages["unverified"],
            "search_failed" if claim_had_error else (
                "search_completed" if normalized else "no_results"
            ),
            language
        )

    if searchable_claims == 0:
        status = "not_applicable"
        message = messages["no_claims"]
    elif had_error:
        status = "search_failed"
        message = messages["failed"]
    elif result_count:
        status = "search_completed"
        message = messages["completed"]
    else:
        status = "no_results"
        message = messages["no_results"]
    retrieved_pages = len(retrieved_urls)
    error_summary = ", ".join(
        f'{error["provider"]}: {error["type"]}'
        + (
            f' (HTTP {error["http_status"]})'
            if error["http_status"] is not None
            else ""
        )
        for error in search_errors
    ) or "none"
    summary = messages["search_summary"].format(
        providers=", ".join(providers_used) if providers_used else "none",
        queries=searchable_claims,
        requests=provider_requests,
        results=result_count,
        retrieved=retrieved_pages,
        pages=len(source_urls_found),
        errors=error_summary
    )
    return {
        "status": status,
        "message": f"{message} {summary}",
        "provider_used": providers_used,
        "queries_attempted": searchable_claims,
        "results_found": result_count,
        "errors": search_errors,
        "provider_configuration": provider_configuration,
        "source_review": {
            "search_requests": searchable_claims,
            "queries_attempted": searchable_claims,
            "provider_requests": provider_requests,
            "results_found": result_count,
            "providers_used": providers_used,
            "errors": search_errors,
            "max_search_requests": MAX_SEARCH_REQUESTS_PER_ANALYSIS,
            "attempted": retrieval_attempts,
            "retrieved": retrieved_pages,
            "failed": retrieval_failures,
            "not_retrieved": max(0, len(source_urls_found) - retrieved_pages),
            "max_sources": MAX_SOURCE_FETCHES_PER_ANALYSIS,
            "time_limit_seconds": SOURCE_REVIEW_TIMEOUT_SECONDS,
            "final_verdict_performed": True,
            "search_limit_reached": search_limit_reached
        }
    }


def _set_claim_result(claim, sources, explanation, search_status, language="en"):
    if not isinstance(claim, dict):
        return
    claim["sources"] = sources
    claim["source_search_status"] = search_status
    verdict = assess_claim_verdict(claim, language)
    claim["verdict"] = verdict["category"]
    claim["verdict_explanation"] = verdict["explanation"] or explanation
    claim["verdict_assessment"] = verdict
