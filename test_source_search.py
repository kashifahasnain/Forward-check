import unittest
import os
from unittest.mock import Mock, patch

import requests

import app
from modules.claim_extractor import fallback_analysis
from modules.source_checker import (
    BRAVE_SEARCH_ENDPOINT,
    TAVILY_SEARCH_ENDPOINT,
    BraveSearchProvider,
    TavilySearchProvider,
    _query_for_claim,
    discover_claim_sources
)


class FakeProvider:
    def __init__(self, results=None, error=None):
        self.results = results or []
        self.error = error
        self.queries = []
        self.source_retriever = FakeRetriever()

    def search(self, query):
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.results


class FakeRetriever:
    def __init__(self, results=None):
        self.results = results or {}
        self.urls = []

    def fetch(self, url, deadline=None):
        self.urls.append(url)
        if isinstance(self.results, dict) and url in self.results:
            return self.results[url]
        return {
            "retrieval_status": "timeout",
            "retrieved_text": "",
            "retrieved_title": "",
            "publication_date": "",
            "content_type": "",
            "source_type": "",
            "partial_content": False,
            "limitations": "The source did not respond within the time limit."
        }


class SourceSearchTests(unittest.TestCase):
    def test_paired_hindi_hinglish_negation_survives_search_query_generation(self):
        examples = (
            (
                "hi",
                "सभी छात्रों को ₹10,000 की आर्थिक सहायता मिलेगी।",
                "सभी छात्रों को ₹10,000 की आर्थिक सहायता नहीं मिलेगी।",
                "नहीं"
            ),
            (
                "hinglish",
                "Sabhi students ko ₹10,000 ki financial assistance milegi.",
                "Sabhi students ko ₹10,000 ki financial assistance nahi milegi.",
                "nahi"
            )
        )
        for language, positive_message, negative_message, negation in examples:
            with self.subTest(language=language):
                positive_claim = fallback_analysis(
                    positive_message,
                    language
                )["claims"][0]
                negative_claim = fallback_analysis(
                    negative_message,
                    language
                )["claims"][0]
                positive_query = _query_for_claim(positive_claim)
                negative_query = _query_for_claim(negative_claim)

                self.assertIn("10,000", positive_query)
                self.assertIn("10,000", negative_query)
                self.assertNotIn(negation, positive_query.casefold())
                self.assertIn(negation, negative_query.casefold())

    def test_brave_provider_uses_fixed_endpoint_and_server_side_api_header(self):
        response = Mock()
        response.json.return_value = {
            "web": {
                "results": [{
                    "title": "Original announcement",
                    "url": "https://news.example.org/article",
                    "description": "A result summary.",
                    "published": "2026-10-01T10:00:00Z"
                }]
            }
        }
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        provider = BraveSearchProvider("local-test-key", session=session)

        results = provider.search("college scholarship")

        session.get.assert_called_once()
        args, kwargs = session.get.call_args
        self.assertEqual(args[0], BRAVE_SEARCH_ENDPOINT)
        self.assertEqual(kwargs["headers"]["X-Subscription-Token"], "local-test-key")
        self.assertEqual(kwargs["params"], {"q": "college scholarship", "count": 3})
        self.assertEqual(results[0]["publisher"], "news.example.org")
        self.assertEqual(results[0]["date"], "2026-10-01")
        self.assertEqual(results[0]["date_status"], "provided")
        self.assertEqual(results[0]["summary"], "A result summary.")
        self.assertEqual(results[0]["query"], "college scholarship")
        self.assertEqual(results[0]["provider"], "Brave Search")

    def test_tavily_provider_uses_documented_post_and_normalizes_source_leads(self):
        response = Mock()
        response.json.return_value = {
            "results": [{
                "title": "Original announcement",
                "url": "https://news.example.org/article",
                "content": "A result snippet.",
                "published_date": "2026-10-01"
            }]
        }
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        provider = TavilySearchProvider("local-test-key", session=session)

        results = provider.search("college scholarship")

        session.post.assert_called_once()
        args, kwargs = session.post.call_args
        self.assertEqual(args[0], TAVILY_SEARCH_ENDPOINT)
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            "Bearer local-test-key"
        )
        self.assertNotIn("api_key", kwargs["json"])
        self.assertEqual(kwargs["json"]["query"], "college scholarship")
        self.assertEqual(kwargs["json"]["max_results"], 3)
        self.assertTrue(kwargs["json"]["include_published_date"])
        self.assertEqual(kwargs["timeout"], (3, 10))
        self.assertEqual(results[0]["publisher"], "news.example.org")
        self.assertEqual(results[0]["date"], "2026-10-01")
        self.assertEqual(results[0]["summary"], "A result snippet.")
        self.assertEqual(results[0]["query"], "college scholarship")
        self.assertEqual(results[0]["provider"], "Tavily Search")

    def test_tavily_empty_results_are_a_completed_empty_search(self):
        response = Mock()
        response.json.return_value = {"results": []}
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        claims = [{"claim": "A claim with no returned search results."}]

        status = discover_claim_sources(
            claims,
            provider=TavilySearchProvider("local-test-key", session=session),
            enabled=True,
            retriever=FakeRetriever()
        )

        self.assertEqual(status["status"], "no_results")
        self.assertEqual(status["provider_used"], ["Tavily Search"])
        self.assertEqual(status["queries_attempted"], 1)
        self.assertEqual(status["results_found"], 0)
        self.assertEqual(claims[0]["verdict"], "Unverified")
        self.assertIn("does not show", status["message"])

    def test_provider_discards_non_https_and_credentialed_result_links(self):
        response = Mock()
        response.json.return_value = {
            "web": {
                "results": [
                    {"title": "HTTP", "url": "http://example.org/a"},
                    {"title": "Credentials", "url": "https://user@example.org/a"},
                    {"title": "Safe", "url": "https://example.org/a"}
                ]
            }
        }
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        results = BraveSearchProvider("key", session=session).search("a claim")

        self.assertEqual([item["title"] for item in results], ["Safe"])

    def test_discovery_attaches_evidence_and_keeps_retrieval_failures_unverified(self):
        claims = [{
            "claim": "The college opened applications on 15 June.",
            "normalized_wording": "College applications opened on 15 June."
        }]
        provider = FakeProvider([{
            "title": "College notice",
            "url": "https://college.example.edu/notice",
            "description": "The result summary."
        }])

        status = discover_claim_sources(claims, provider=provider, enabled=True)

        self.assertEqual(status["status"], "search_completed")
        self.assertEqual(provider.queries, ["College applications opened on 15 June."])
        self.assertEqual(claims[0]["verdict"], "Unverified")
        self.assertEqual(claims[0]["sources"][0]["publisher"], "college.example.edu")
        self.assertEqual(claims[0]["sources"][0]["summary"], "The result summary.")
        self.assertIn(
            "retrieved text",
            claims[0]["sources"][0]["relevance"].casefold()
        )
        self.assertEqual(
            claims[0]["sources"][0]["evidence_assessment"]["status"],
            "Retrieval Failed"
        )
        self.assertEqual(
            claims[0]["sources"][0]["query"],
            "College applications opened on 15 June."
        )
        self.assertEqual(claims[0]["sources"][0]["provider"], "FakeProvider")
        self.assertEqual(
            claims[0]["sources"][0]["retrieval_status"],
            "timeout"
        )
        self.assertIn(
            "cautious claim verdicts",
            status["message"].casefold()
        )

    def test_discovery_assigns_supported_verdict_only_from_distinct_retrieved_passages(self):
        first_url = "https://college.example/notice"
        second_url = "https://news.example/college"
        claim_text = "The college opened applications on 15 June."
        claims = [{"claim": claim_text}]
        provider = FakeProvider([
            {
                "title": "College applications notice",
                "url": first_url,
                "description": "Applications opened on 15 June."
            },
            {
                "title": "College reports opening date",
                "url": second_url,
                "description": "College applications opened."
            }
        ])
        provider.source_retriever = FakeRetriever({
            first_url: {
                "retrieval_status": "retrieved",
                "retrieved_text": "The college opened applications on 15 June.",
                "retrieved_title": "College applications notice",
                "publication_date": "2026-06-15",
                "source_type": "HTML webpage",
                "partial_content": False,
                "limitations": ""
            },
            second_url: {
                "retrieval_status": "retrieved",
                "retrieved_text": (
                    "The college opened applications on 15 June this year."
                ),
                "retrieved_title": "College reports opening date",
                "publication_date": "",
                "source_type": "HTML webpage",
                "partial_content": False,
                "limitations": ""
            }
        })

        discover_claim_sources(claims, provider=provider, enabled=True)

        self.assertEqual(claims[0]["verdict"], "Unverified")
        self.assertEqual(
            claims[0]["verdict_assessment"]["category_code"],
            "unverified"
        )
        self.assertFalse(claims[0]["verdict_assessment"]["evidence_sufficient"])
        self.assertEqual(
            len(claims[0]["verdict_assessment"]["supporting_evidence"]),
            2
        )
        self.assertTrue(any(
            "independent corroboration" in limitation
            for limitation in claims[0]["verdict_assessment"]["limitations"]
        ))

    def test_duplicate_urls_are_cached_without_collapsing_case_sensitive_paths(self):
        claims = [{"claim": "A factual claim is under review."}]
        provider = FakeProvider([
            {
                "title": "Uppercase path",
                "url": "https://news.example/Article",
                "description": "First lead."
            },
            {
                "title": "Lowercase path",
                "url": "https://news.example/article",
                "description": "Second lead."
            },
            {
                "title": "Duplicate uppercase path",
                "url": "https://news.example/Article",
                "description": "Duplicate lead."
            }
        ])

        discover_claim_sources(claims, provider=provider, enabled=True)

        self.assertEqual(len(claims[0]["sources"]), 2)
        self.assertEqual(
            provider.source_retriever.urls,
            [
                "https://news.example/Article",
                "https://news.example/article"
            ]
        )

    def test_queries_use_subject_specific_claim_context(self):
        examples = (
            (
                {
                    "claim": "Minister X said that all students receive ₹10,000.",
                    "claim_type": "attributed_quote",
                    "alleged_speaker": "Minister X",
                    "original_wording": (
                        "Minister X said that all students receive ₹10,000."
                    ),
                    "context": (
                        "Minister X said that all students receive ₹10,000."
                    ),
                    "categories": ["politics"]
                },
                ("Minister X", "students receive", "transcript interview")
            ),
            (
                {
                    "claim": "Every college student can receive the named scholarship.",
                    "categories": ["government schemes"]
                },
                ("official announcement", "eligibility rules")
            ),
            (
                {
                    "claim": "This plant releases oxygen throughout the night.",
                    "categories": ["biology"]
                },
                ("plant releases oxygen", "scientific evidence")
            ),
            (
                {
                    "claim": "This vitamin prevents every viral infection.",
                    "categories": ["health"]
                },
                ("vitamin prevents every viral infection", "medical research")
            ),
            (
                {
                    "claim": "The Treaty of Versailles was signed in 1918.",
                    "categories": ["history"]
                },
                ("Treaty of Versailles", "primary sources")
            ),
            (
                {
                    "claim": "This investment guarantees a 30% return each month.",
                    "categories": ["finance"]
                },
                ("30% return", "financial regulator")
            )
        )

        for claim, expected_terms in examples:
            with self.subTest(claim=claim["claim"]):
                query = _query_for_claim(claim).casefold()
                for term in expected_terms:
                    self.assertIn(term.casefold(), query)

    def test_queries_do_not_force_political_or_general_claims_to_government_sources(self):
        query = _query_for_claim({
            "claim": "The actor said the movie will be released in June.",
            "claim_type": "attributed_quote",
            "alleged_speaker": "Actor A",
            "categories": ["politics"]
        }).casefold()

        self.assertIn("transcript interview", query)
        self.assertNotIn("government schemes", query)
        self.assertNotIn("official announcement eligibility", query)

    def test_non_quote_political_claim_does_not_get_quote_specific_query_terms(self):
        query = _query_for_claim({
            "claim": "The minister introduced a new transport policy.",
            "categories": ["politics"]
        }).casefold()

        self.assertNotIn("transcript interview", query)
        self.assertNotIn("official announcement", query)

    def test_search_query_includes_grounded_names_dates_and_amounts(self):
        claim = {
            "claim": "Students will receive assistance.",
            "normalized_wording": "Students will receive assistance.",
            "entities": {
                "organizations": ["Ministry of Education"],
                "dates": ["12 October"],
                "amounts": ["₹10,000"]
            }
        }
        provider = FakeProvider()

        discover_claim_sources([claim], provider=provider, enabled=True)

        self.assertIn("Ministry of Education", provider.queries[0])
        self.assertIn("12 October", provider.queries[0])
        self.assertIn("₹10,000", provider.queries[0])

    def test_search_query_never_includes_submitted_url_strings(self):
        submitted_url = "https://private.example/path"
        claim = {
            "claim": f"The message at {submitted_url} promises a benefit."
        }
        provider = FakeProvider()

        discover_claim_sources([claim], provider=provider, enabled=True)

        self.assertNotIn(submitted_url, provider.queries[0])
        self.assertNotIn("private.example", provider.queries[0])

    def test_missing_api_key_is_explicit_and_does_not_make_a_request(self):
        claims = [{"claim": "An unsupported factual assertion."}]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("modules.source_checker.requests.post") as tavily_search,
            patch("modules.source_checker.requests.get") as brave_search
        ):
            status = discover_claim_sources(claims, language="hi", enabled=True)

        self.assertEqual(status["status"], "not_configured")
        self.assertIn("TAVILY_API_KEY", status["message"])
        self.assertIn("BRAVE_SEARCH_API_KEY", status["message"])
        self.assertEqual(status["provider_used"], [])
        tavily_search.assert_not_called()
        brave_search.assert_not_called()
        self.assertEqual(claims[0]["verdict"], "अपुष्ट")
        self.assertEqual(claims[0]["sources"], [])

    def test_tavily_is_preferred_and_source_urls_enter_safe_retrieval(self):
        response = Mock()
        response.json.return_value = {
            "results": [{
                "title": "Original announcement",
                "url": "https://news.example.org/article",
                "content": "Search snippet only."
            }]
        }
        response.raise_for_status.return_value = None
        claims = [{"claim": "An unsupported factual assertion."}]
        retriever = FakeRetriever()

        with (
            patch.dict(
                os.environ,
                {
                    "TAVILY_API_KEY": "tavily-test-key",
                    "BRAVE_SEARCH_API_KEY": "brave-test-key"
                },
                clear=True
            ),
            patch(
                "modules.source_checker.requests.post",
                return_value=response
            ) as tavily_search,
            patch("modules.source_checker.requests.get") as brave_search
        ):
            status = discover_claim_sources(
                claims,
                enabled=True,
                retriever=retriever
            )

        self.assertEqual(status["provider_used"], ["Tavily Search"])
        self.assertEqual(status["queries_attempted"], 1)
        self.assertEqual(status["source_review"]["provider_requests"], 1)
        self.assertEqual(status["results_found"], 1)
        self.assertEqual(claims[0]["sources"][0]["provider"], "Tavily Search")
        self.assertEqual(
            retriever.urls,
            ["https://news.example.org/article"]
        )
        self.assertEqual(claims[0]["sources"][0]["retrieval_status"], "timeout")
        self.assertEqual(claims[0]["verdict"], "Unverified")
        self.assertIn("Source pages retrieved: 0/1", status["message"])
        tavily_search.assert_called_once()
        brave_search.assert_not_called()

    def test_tavily_error_is_reported_when_brave_is_not_configured(self):
        claims = [{"claim": "An unsupported factual assertion."}]

        with (
            patch.dict(
                os.environ,
                {"TAVILY_API_KEY": "tavily-test-key"},
                clear=True
            ),
            patch(
                "modules.source_checker.requests.post",
                side_effect=requests.Timeout("offline test")
            ) as tavily_search
        ):
            status = discover_claim_sources(
                claims,
                enabled=True,
                retriever=FakeRetriever()
            )

        self.assertEqual(status["status"], "search_failed")
        self.assertEqual(status["provider_used"], [])
        self.assertEqual(status["errors"][0]["provider"], "Tavily Search")
        self.assertEqual(status["errors"][0]["type"], "Timeout")
        self.assertEqual(claims[0]["verdict"], "Unverified")
        self.assertEqual(claims[0]["sources"], [])
        tavily_search.assert_called_once()

    def test_brave_is_used_as_fallback_when_tavily_search_fails(self):
        response = Mock()
        response.json.return_value = {
            "web": {
                "results": [{
                    "title": "Fallback source",
                    "url": "https://news.example.org/article",
                    "description": "A result snippet."
                }]
            }
        }
        response.raise_for_status.return_value = None
        claims = [{"claim": "An unsupported factual assertion."}]
        retriever = FakeRetriever()

        with (
            patch.dict(
                os.environ,
                {
                    "TAVILY_API_KEY": "tavily-test-key",
                    "BRAVE_SEARCH_API_KEY": "brave-test-key"
                },
                clear=True
            ),
            patch(
                "modules.source_checker.requests.post",
                side_effect=requests.Timeout("offline test")
            ) as tavily_search,
            patch(
                "modules.source_checker.requests.get",
                return_value=response
            ) as brave_search
        ):
            status = discover_claim_sources(
                claims,
                enabled=True,
                retriever=retriever
            )

        self.assertEqual(status["status"], "search_completed")
        self.assertEqual(status["provider_used"], ["Brave Search"])
        self.assertEqual(status["queries_attempted"], 1)
        self.assertEqual(status["source_review"]["provider_requests"], 2)
        self.assertEqual(status["results_found"], 1)
        self.assertEqual(status["errors"][0]["provider"], "Tavily Search")
        self.assertEqual(claims[0]["sources"][0]["provider"], "Brave Search")
        self.assertEqual(retriever.urls, ["https://news.example.org/article"])
        self.assertEqual(claims[0]["verdict"], "Unverified")
        self.assertIn("Errors: Tavily Search: Timeout", status["message"])
        tavily_search.assert_called_once()
        brave_search.assert_called_once()

    def test_tavily_and_brave_fallback_share_the_existing_request_limit(self):
        tavily_response = Mock()
        tavily_response.json.return_value = {"results": []}
        tavily_response.raise_for_status.return_value = None
        brave_response = Mock()
        brave_response.json.return_value = {"web": {"results": []}}
        brave_response.raise_for_status.return_value = None
        claims = [
            {"claim": f"An unsupported factual assertion number {number}."}
            for number in range(10)
        ]

        with (
            patch.dict(
                os.environ,
                {
                    "TAVILY_API_KEY": "tavily-test-key",
                    "BRAVE_SEARCH_API_KEY": "brave-test-key"
                },
                clear=True
            ),
            patch(
                "modules.source_checker.requests.post",
                side_effect=[
                    requests.Timeout("offline test"),
                    *([tavily_response] * 8)
                ]
            ) as tavily_search,
            patch(
                "modules.source_checker.requests.get",
                return_value=brave_response
            ) as brave_search
        ):
            status = discover_claim_sources(
                claims,
                enabled=True,
                retriever=FakeRetriever()
            )

        self.assertEqual(status["status"], "no_results")
        self.assertEqual(status["source_review"]["provider_requests"], 9)
        self.assertEqual(tavily_search.call_count + brave_search.call_count, 9)
        self.assertTrue(status["source_review"]["search_limit_reached"])
        self.assertTrue(all(
            claim["source_search_status"] == "not_searched_limit"
            for claim in claims[9:]
        ))

    def test_provider_timeout_is_graceful_and_claim_remains_unverified(self):
        claims = [{"claim": "A claim with a deadline."}]
        provider = FakeProvider(error=requests.Timeout("offline test"))

        status = discover_claim_sources(claims, provider=provider, enabled=True)

        self.assertEqual(status["status"], "search_failed")
        self.assertEqual(claims[0]["verdict"], "Unverified")
        self.assertEqual(claims[0]["sources"], [])
        self.assertIn("remain unverified", status["message"])

    def test_empty_results_are_not_interpreted_as_disproof(self):
        claims = [{"claim": "A claim with no returned search results."}]

        status = discover_claim_sources(
            claims,
            provider=FakeProvider(),
            enabled=True
        )

        self.assertEqual(status["status"], "no_results")
        self.assertEqual(claims[0]["verdict"], "Unverified")
        self.assertIn("does not show", status["message"])

    def test_every_suitable_claim_is_searched_and_remains_unverified(self):
        claims = [
            {"claim": f"Factual claim number {number}."}
            for number in range(5)
        ]
        provider = FakeProvider()

        discover_claim_sources(claims, provider=provider, enabled=True)
        self.assertEqual(len(provider.queries), 5)
        self.assertTrue(all(claim["verdict"] == "Unverified" for claim in claims))
        self.assertTrue(all(isinstance(claim["sources"], list) for claim in claims))

    def test_search_is_opt_in_even_if_a_provider_key_is_configured(self):
        claims = [{"claim": "Keep this claim local."}]
        provider = FakeProvider()

        status = discover_claim_sources(
            claims,
            provider=provider,
            enabled=False
        )

        self.assertEqual(status["status"], "not_enabled")
        self.assertEqual(provider.queries, [])
        self.assertEqual(claims[0]["source_search_status"], "not_enabled")

    def test_results_without_publication_date_mark_it_as_not_provided(self):
        claims = [{"claim": "A factual assertion with no date."}]
        provider = FakeProvider([{
            "title": "Related result",
            "url": "https://example.org/article",
            "description": "A short snippet."
        }])

        discover_claim_sources(claims, provider=provider, enabled=True)

        source = claims[0]["sources"][0]
        self.assertEqual(source["date"], "")
        self.assertEqual(source["date_status"], "not_provided")
        self.assertEqual(source["provider"], "FakeProvider")
        self.assertEqual(source["query"], provider.queries[0])

    def test_malformed_provider_results_fail_gracefully(self):
        response = Mock()
        response.json.return_value = {"web": {"results": "not-a-list"}}
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        provider = BraveSearchProvider("test-key", session=session)
        claims = [{"claim": "An assertion that should be searched."}]

        status = discover_claim_sources(
            claims,
            provider=provider,
            enabled=True
        )

        self.assertEqual(status["status"], "search_failed")
        self.assertEqual(claims[0]["sources"], [])
        self.assertEqual(claims[0]["source_search_status"], "search_failed")

    def test_malformed_provider_json_fails_gracefully(self):
        response = Mock()
        response.json.side_effect = ValueError("invalid JSON")
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        claims = [{"claim": "An assertion that should be searched."}]

        status = discover_claim_sources(
            claims,
            provider=BraveSearchProvider("test-key", session=session),
            enabled=True
        )

        self.assertEqual(status["status"], "search_failed")
        self.assertEqual(claims[0]["sources"], [])
        self.assertEqual(claims[0]["verdict"], "Unverified")

    def test_nonempty_but_unusable_provider_results_are_not_reported_as_no_results(self):
        response = Mock()
        response.json.return_value = {
            "web": {
                "results": [{
                    "title": "",
                    "url": "https://example.org/article"
                }]
            }
        }
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        claims = [{"claim": "An assertion that should be searched."}]

        status = discover_claim_sources(
            claims,
            provider=BraveSearchProvider("test-key", session=session),
            enabled=True
        )

        self.assertEqual(status["status"], "search_failed")
        self.assertEqual(claims[0]["source_search_status"], "search_failed")

    def test_brave_rate_limit_is_reported_without_repeating_requests(self):
        response = Mock()
        response.status_code = 429
        response.raise_for_status.side_effect = requests.HTTPError(
            "rate limited",
            response=response
        )
        session = Mock()
        session.get.return_value = response
        provider = BraveSearchProvider("test-key", session=session)
        claims = [
            {"claim": "First factual assertion."},
            {"claim": "Second factual assertion."}
        ]

        status = discover_claim_sources(claims, provider=provider, enabled=True)

        self.assertEqual(status["status"], "search_failed")
        session.get.assert_called_once()
        self.assertEqual(claims[0]["source_search_status"], "search_failed")
        self.assertEqual(
            claims[1]["source_search_status"],
            "not_searched_rate_limited"
        )
        self.assertTrue(all(claim["verdict"] == "Unverified" for claim in claims))

    def test_empty_web_results_are_a_completed_empty_search(self):
        response = Mock()
        response.json.return_value = {"web": {"results": []}}
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        claims = [{"claim": "A claim with no matching leads."}]

        status = discover_claim_sources(
            claims,
            provider=BraveSearchProvider("test-key", session=session),
            enabled=True
        )

        self.assertEqual(status["status"], "no_results")
        self.assertEqual(claims[0]["sources"], [])
        self.assertEqual(claims[0]["source_search_status"], "no_results")

    def test_search_leads_are_ranked_by_claim_relevance_and_topic(self):
        claim = {
            "claim": "The Treaty of Versailles was signed in 1918.",
            "categories": ["history"]
        }
        provider = FakeProvider([
            {
                "title": "General history page",
                "url": "https://example.com/history",
                "description": "Overview."
            },
            {
                "title": "Treaty of Versailles archive document",
                "url": "https://archives.gov/treaty-versailles",
                "description": "Historical record of the treaty."
            }
        ])

        discover_claim_sources([claim], provider=provider, enabled=True)

        self.assertEqual(
            claim["sources"][0]["title"],
            "Treaty of Versailles archive document"
        )
        self.assertTrue(all(
            source["relationship"] == "Not assessed"
            for source in claim["sources"]
        ))

    def test_opinions_and_instructions_are_not_searched(self):
        claims = [
            {"claim": "This is the best policy.", "claim_type": "opinion"},
            {"claim": "Forward this message.", "claim_type": "instruction"}
        ]
        provider = FakeProvider()

        status = discover_claim_sources(claims, provider=provider, enabled=True)

        self.assertEqual(status["status"], "not_applicable")
        self.assertEqual(provider.queries, [])
        self.assertTrue(all(
            claim["source_search_status"] == "not_factual"
            for claim in claims
        ))
        self.assertTrue(all(
            claim["verdict_assessment"]["category_code"] == "not_factual"
            for claim in claims
        ))

    def test_opinion_fact_is_split_and_searched_as_a_separate_claim(self):
        claim = {
            "claim": "I think this policy is terrible because it costs ₹5 billion.",
            "claim_type": "opinion"
        }
        provider = FakeProvider()

        claims = [claim]
        discover_claim_sources(claims, provider=provider, enabled=True)

        self.assertEqual(len(provider.queries), 1)
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0]["source_search_status"], "not_factual")
        self.assertEqual(
            claims[0]["verdict_assessment"]["category_code"],
            "not_factual"
        )
        self.assertEqual(claims[1]["claim"], "it costs ₹5 billion.")
        self.assertEqual(claims[1]["claim_type"], "factual_assertion")
        self.assertEqual(claims[1]["source_search_status"], "no_results")
        self.assertIn("this policy", provider.queries[0].casefold())
        self.assertEqual(claims[1]["verdict"], "Unverified")

    def test_flask_does_not_send_claims_when_search_checkbox_is_off(self):
        analysis = {
            "claims": [{"claim": "Keep this claim local."}],
            "warning_signals": [],
            "verification_steps": [],
            "verification_links": [],
            "disclaimer": "Claims need independent verification.",
            "caution_explanation": "Verify independently."
        }
        with (
            patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-key"}, clear=True),
            patch.object(app, "extract_claims", return_value=analysis),
            patch("modules.source_checker.requests.get") as search
        ):
            result = app.app.test_client().post(
                "/analyse",
                data={"message": "Keep this claim local."}
            )

        self.assertEqual(result.status_code, 200)
        search.assert_not_called()
        body = result.get_json()
        self.assertEqual(
            body["analysis"]["evidence_status"]["status"],
            "not_enabled"
        )
        self.assertEqual(
            body["analysis"]["claims"][0]["source_search_status"],
            "not_enabled"
        )

    def test_flask_analysis_exposes_brave_leads_without_verifying_the_claim(self):
        response = Mock()
        response.json.return_value = {
            "web": {
                "results": [{
                    "title": "Student support notice",
                    "url": "https://education.example.org/notice",
                    "description": "A search-result summary."
                }]
            }
        }
        response.raise_for_status.return_value = None
        message = "Every student will receive ₹10,000 in financial assistance this month."

        with (
            patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-key"}, clear=True),
            patch(
                "modules.claim_extractor.requests.post",
                side_effect=requests.Timeout("offline test")
            ),
            patch("modules.source_checker.requests.get", return_value=response) as search,
            patch(
                "modules.source_checker.SafeSourceRetriever.fetch",
                return_value={
                    "retrieval_status": "retrieved",
                    "retrieved_text": (
                        "Every student will receive ₹10,000 in financial assistance this month."
                    ),
                    "retrieved_title": "Student support",
                    "publication_date": "",
                    "content_type": "text/html",
                    "source_type": "HTML webpage",
                    "partial_content": False,
                    "limitations": "Only readable page text was retrieved."
                }
            )
        ):
            result = app.app.test_client().post(
                "/analyse",
                data={
                    "message": message,
                    "language": "en",
                    "source_search_enabled": "true"
                }
            )

        self.assertEqual(result.status_code, 200)
        body = result.get_json()
        claim = body["analysis"]["claims"][0]
        self.assertEqual(claim["verdict"], "Unverified")
        self.assertEqual(claim["sources"][0]["title"], "Student support notice")
        self.assertEqual(
            claim["sources"][0]["evidence_assessment"]["status"],
            "Supports"
        )
        self.assertFalse(body["independent_verification_performed"])
        self.assertEqual(search.call_args.args[0], BRAVE_SEARCH_ENDPOINT)

    def test_submitted_url_is_never_requested_by_the_server(self):
        response = Mock()
        response.json.return_value = {"web": {"results": []}}
        response.raise_for_status.return_value = None
        analysis = {
            "claims": [{
                "claim": "Students will receive support.",
                "normalized_wording": "Students will receive support."
            }],
            "warning_signals": [],
            "verification_steps": ["Check an original source."],
            "verification_links": [],
            "disclaimer": "Claims need independent verification.",
            "caution_explanation": "Verify this independently."
        }
        submitted_url = "https://user-submitted.example/private-path"

        with (
            patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-key"}, clear=True),
            patch.object(app, "extract_claims", return_value=analysis),
            patch("modules.source_checker.requests.get", return_value=response) as search
        ):
            result = app.app.test_client().post(
                "/analyse",
                data={
                    "message": f"Students will receive support. {submitted_url}",
                    "source_search_enabled": "true"
                }
            )

        self.assertEqual(result.status_code, 200)
        search.assert_called_once()
        self.assertEqual(search.call_args.args[0], BRAVE_SEARCH_ENDPOINT)
        self.assertNotIn(submitted_url, search.call_args.kwargs["params"]["q"])


if __name__ == "__main__":
    unittest.main()
