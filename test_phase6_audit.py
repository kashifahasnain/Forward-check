import os
import unittest
from unittest.mock import patch

from modules.analysis_pipeline import analyze_message
from modules.source_checker import discover_claim_sources


class PhaseSixAuditTests(unittest.TestCase):
    def test_synthetic_messages_complete_offline_analysis_flows(self):
        cases = (
            {
                "name": "synthetic fake-quote allegation",
                "text": "Forwarded post: Minister Mira Sen said every student receives 20000 credits by Friday.",
                "language": "en",
                "claims": [{
                    "claim": "Minister Mira Sen said every student receives 20000 credits by Friday.",
                    "claim_type": "attributed_quote",
                    "categories": ["politics"]
                }],
                "search_term": "Mira Sen",
                "sources": [{
                    "title": "Synthetic archive page",
                    "url": "https://quotes.synthetic.example/mira-sen"
                }],
                "retrieved_text": (
                    "This synthetic archive describes a community garden, "
                    "seasonal planting dates, and volunteer activities."
                ),
                "expected": {"unverified"}
            },
            {
                "name": "synthetic scholarship eligibility",
                "text": "Every student is eligible for the fictional Udaan Scholarship.",
                "language": "en",
                "claims": [{
                    "claim": "Every student is eligible for the fictional Udaan Scholarship.",
                    "categories": ["government schemes"]
                }],
                "search_term": "Udaan Scholarship",
                "sources": [{
                    "title": "Synthetic scholarship rules",
                    "url": "https://rules.synthetic.example/udaan"
                }],
                "retrieved_text": (
                    "Only first-year students from low-income households are "
                    "eligible for the fictional Udaan Scholarship."
                ),
                "expected": {"misleading"}
            },
            {
                "name": "synthetic broad health claim",
                "text": "A fictional herb cures every respiratory infection.",
                "language": "en",
                "claims": [{
                    "claim": "A fictional herb cures every respiratory infection.",
                    "categories": ["health"]
                }],
                "search_term": "fictional herb",
                "sources": [],
                "retrieved_text": "",
                "expected": {"unverified"}
            },
            {
                "name": "synthetic historical date",
                "text": "The fictional Rivergate Accord was signed in 1898.",
                "language": "en",
                "claims": [{
                    "claim": "The fictional Rivergate Accord was signed in 1898.",
                    "categories": ["history"]
                }],
                "search_term": "Rivergate Accord",
                "sources": [{
                    "title": "Synthetic primary-source record",
                    "url": "https://archive.synthetic.example/rivergate"
                }],
                "retrieved_text": (
                    "The fictional Rivergate Accord was signed in 1899, "
                    "according to this synthetic primary-source record."
                ),
                "expected": {"unverified"}
            },
            {
                "name": "synthetic guaranteed-return claim",
                "text": "This fictional fund guarantees 4 percent returns every month.",
                "language": "en",
                "claims": [{
                    "claim": "This fictional fund guarantees 4 percent returns every month.",
                    "categories": ["finance"]
                }],
                "search_term": "fictional fund",
                "sources": [],
                "retrieved_text": "",
                "expected": {"unverified"}
            },
            {
                "name": "synthetic opinion with a factual clause",
                "text": (
                    "I think the fictional Bluebird transit plan is wasteful "
                    "because it costs ₹5 billion."
                ),
                "language": "en",
                "claims": [{
                    "claim": (
                        "I think the fictional Bluebird transit plan is wasteful "
                        "because it costs ₹5 billion."
                    ),
                    "claim_type": "opinion",
                    "categories": ["finance"]
                }],
                "search_term": "Bluebird",
                "sources": [{
                    "title": "Synthetic transit budget note",
                    "url": "https://budget.synthetic.example/bluebird"
                }],
                "retrieved_text": (
                    "The fictional Bluebird transit plan costs ₹5 billion, "
                    "according to this synthetic budget note."
                ),
                "expected": {"not_factual", "unverified"}
            },
            {
                "name": "synthetic Hindi viral benefit message",
                "text": "तुरंत रजिस्टर करें! सरकार हर छात्र को मुफ्त लैपटॉप दे रही है।",
                "language": "hi",
                "claims": [{
                    "claim": "सरकार हर छात्र को मुफ्त लैपटॉप दे रही है।",
                    "categories": ["government schemes"],
                    "original_language": "hi"
                }],
                "search_term": "सरकार",
                "sources": [],
                "retrieved_text": "",
                "expected": {"unverified"}
            }
        )

        for case in cases:
            with self.subTest(case=case["name"]):
                source_results = {
                    case["search_term"].casefold(): case["sources"]
                }
                retrieval_results = {
                    source["url"]: {
                        "retrieval_status": "retrieved",
                        "retrieved_text": case["retrieved_text"],
                        "retrieved_title": source["title"],
                        "publication_date": "",
                        "content_type": "text/html",
                        "source_type": "HTML webpage",
                        "partial_content": False,
                        "limitations": "Synthetic test fixture; not real evidence."
                    }
                    for source in case["sources"]
                }
                queries = []

                class SyntheticProvider:
                    provider_name = "Synthetic offline fixture"

                    def __init__(self, api_key):
                        if api_key != "synthetic-test-key":
                            raise AssertionError("Unexpected synthetic test key.")

                    def search(self, query):
                        queries.append(query)
                        for term, results in source_results.items():
                            if term in query.casefold():
                                return results
                        return []

                class SyntheticRetriever:
                    def fetch(self, url, deadline=None):
                        if deadline is None:
                            raise AssertionError("Expected bounded retrieval deadline.")
                        return retrieval_results[url]

                def synthetic_claim_analyzer(text, language="en"):
                    if text != case["text"] or language != case["language"]:
                        raise AssertionError("Unexpected synthetic analysis input.")
                    return {
                        "claims": [dict(claim) for claim in case["claims"]],
                        "warning_signals": [],
                        "verification_steps": [],
                        "verification_links": [],
                        "disclaimer": "Synthetic offline audit fixture.",
                        "caution_explanation": "Synthetic test data only."
                    }

                with (
                    patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "synthetic-test-key"}),
                    patch("modules.source_checker.BraveSearchProvider", SyntheticProvider),
                    patch("modules.source_checker.SafeSourceRetriever", SyntheticRetriever)
                ):
                    result = analyze_message(
                        case["text"],
                        language=case["language"],
                        claim_analyzer=synthetic_claim_analyzer,
                        source_search_enabled=True
                    )

                claims = result["analysis"]["claims"]
                verdict_codes = {
                    claim["verdict_assessment"]["category_code"]
                    for claim in claims
                }
                self.assertEqual(verdict_codes, case["expected"])
                self.assertTrue(result["analysis"]["evidence_status"]["status"])
                self.assertTrue(queries)
                if case["language"] == "hi":
                    self.assertIn("सरकार", queries[0])

                if case["name"] == "synthetic historical date":
                    self.assertEqual(
                        claims[0]["verdict_assessment"]["category_code"],
                        "unverified"
                    )
                    self.assertEqual(
                        len(claims[0]["verdict_assessment"]["contradicting_evidence"]),
                        1
                    )
                    self.assertEqual(
                        claims[0]["sources"][0]["evidence_assessment"]["status"],
                        "Contradicts"
                    )
                if case["name"] == "synthetic opinion with a factual clause":
                    self.assertEqual(len(claims), 2)
                    factual_claim = next(
                        claim for claim in claims
                        if claim.get("claim_type") == "factual_assertion"
                    )
                    self.assertIn("₹5 billion", factual_claim["claim"])
                    self.assertEqual(
                        len(factual_claim["verdict_assessment"]["supporting_evidence"]),
                        1
                    )

    def test_search_request_cap_leaves_later_claims_unverified(self):
        claims = [
            {"claim": f"Synthetic claim number {number} is checkable."}
            for number in range(11)
        ]

        class EmptyProvider:
            def __init__(self):
                self.queries = []

            def search(self, query):
                self.queries.append(query)
                return []

        provider = EmptyProvider()
        result = discover_claim_sources(
            claims,
            provider=provider,
            enabled=True
        )

        self.assertEqual(len(provider.queries), 9)
        self.assertEqual(result["source_review"]["search_requests"], 9)
        self.assertEqual(result["source_review"]["max_search_requests"], 9)
        self.assertTrue(result["source_review"]["search_limit_reached"])
        self.assertEqual(
            [claim["source_search_status"] for claim in claims[-2:]],
            ["not_searched_limit", "not_searched_limit"]
        )
        self.assertTrue(all(
            claim["verdict_assessment"]["category_code"] == "unverified"
            for claim in claims[-2:]
        ))


if __name__ == "__main__":
    unittest.main()
