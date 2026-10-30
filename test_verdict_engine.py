import unittest

from modules.verdict_engine import assess_claim_verdict


def source_record(
    claim,
    status="Supports",
    passage=None,
    url="https://source-one.example/report",
    title="Source report",
    publisher="source-one.example",
    partial=False
):
    passage = passage or claim
    return {
        "url": url,
        "title": title,
        "publisher": publisher,
        "retrieval_status": "retrieved",
        "partial_content": partial,
        "evidence_assessment": {
            "status": status,
            "claim": claim,
            "retrieval_status": "retrieved",
            "passages": [passage],
            "partial_content": partial,
            "explanation": "Synthetic offline test evidence."
        }
    }


class VerdictEngineTests(unittest.TestCase):
    def test_distinct_hostnames_do_not_establish_independent_corroboration(self):
        claim_text = "The college opened applications on 15 June."
        claim = {
            "claim": claim_text,
            "sources": [
                source_record(
                    claim_text,
                    passage="The college opened applications on 15 June.",
                    url="https://college.example/notice"
                ),
                source_record(
                    claim_text,
                    passage="Applications opened at the college on 15 June.",
                    url="https://news.example/college",
                    publisher="news.example"
                )
            ]
        }

        result = assess_claim_verdict(claim)

        self.assertEqual(result["category_code"], "unverified")
        self.assertEqual(result["category"], "Unverified")
        self.assertFalse(result["evidence_sufficient"])
        self.assertEqual(len(result["supporting_evidence"]), 2)
        self.assertTrue(any(
            "do not establish independent corroboration" in item
            for item in result["limitations"]
        ))

    def test_single_supporting_source_is_unverified(self):
        claim_text = "The college opened applications on 15 June."
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [source_record(claim_text)]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertFalse(result["evidence_sufficient"])
        self.assertTrue(result["supporting_evidence"])

    def test_duplicate_urls_and_copied_passages_do_not_count_as_corroboration(self):
        claim_text = "The scholarship is available to all students."
        passage = "The scholarship is available to all students."
        claim = {
            "claim": claim_text,
            "sources": [
                source_record(
                    claim_text,
                    passage=passage,
                    url="https://a.example/story"
                ),
                source_record(
                    claim_text,
                    passage=passage,
                    url="https://b.example/copied-story",
                    publisher="b.example"
                ),
                source_record(
                    claim_text,
                    passage=passage,
                    url="https://a.example/story?utm_source=copy#section"
                )
            ]
        }

        result = assess_claim_verdict(claim)

        self.assertEqual(result["category_code"], "unverified")
        self.assertEqual(len(result["supporting_evidence"]), 1)
        self.assertTrue(any("Repeated passages" in item for item in result["limitations"]))
        self.assertTrue(any(
            "duplicate source url" in item.casefold()
            for item in result["limitations"]
        ))

    def test_material_eligibility_qualification_is_misleading_context(self):
        claim_text = "Every student is eligible for the scholarship."
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [
                source_record(
                    claim_text,
                    passage="Only low-income students are eligible for the scholarship.",
                    status="Contextualizes"
                )
            ]
        })

        self.assertEqual(result["category_code"], "misleading")
        self.assertEqual(result["category"], "Misleading or Missing Context")
        self.assertTrue(result["evidence_sufficient"])
        self.assertEqual(len(result["contextual_evidence"]), 1)

    def test_non_material_context_does_not_produce_a_misleading_verdict(self):
        claim_text = "The college opened applications."
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [
                source_record(
                    claim_text,
                    passage="The college opened applications according to its annual schedule.",
                    status="Contextualizes"
                )
            ]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertTrue(result["contextual_evidence"])

    def test_contradiction_alone_is_not_a_false_verdict(self):
        claim_text = "The Treaty of Versailles was signed in 1918."
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [
                source_record(
                    claim_text,
                    passage="The Treaty of Versailles was signed in 1919.",
                    status="Contradicts"
                )
            ]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertTrue(result["contradicting_evidence"])
        self.assertIn("source reliability", " ".join(result["limitations"]).casefold())
        self.assertFalse(result["evidence_sufficient"])

    def test_single_keyword_overlap_is_not_accepted_as_claim_evidence(self):
        claim_text = "The minister awarded every student ₹10,000."
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [
                source_record(
                    claim_text,
                    passage="The minister commented on the proposal.",
                    status="Contradicts"
                )
            ]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertEqual(result["contradicting_evidence"], [])
        self.assertTrue(any(
            "claim-specific wording overlap" in limitation
            for limitation in result["limitations"]
        ))

    def test_strong_sounding_contradictions_do_not_trigger_unavailable_false_levels(self):
        claim_text = (
            "The government announced the scholarship yesterday, and every student is eligible."
        )
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [
                source_record(
                    claim_text,
                    passage="The government did not announce the scholarship yesterday.",
                    status="Contradicts",
                    url="https://one.example/scheme"
                ),
                source_record(
                    claim_text,
                    passage="Only eligible applicants may receive the scholarship.",
                    status="Contradicts",
                    url="https://two.example/scheme"
                )
            ]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertNotIn(
            result["category_code"],
            {"mostly_true", "mostly_false", "false"}
        )
        self.assertFalse(result["evidence_sufficient"])

    def test_support_and_contradiction_are_both_preserved_as_unresolved(self):
        claim_text = "The college opened applications on 15 June."
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [
                source_record(
                    claim_text,
                    passage="The college opened applications on 15 June.",
                    url="https://college.example/notice"
                ),
                source_record(
                    claim_text,
                    passage="The college opened applications on 20 June.",
                    status="Contradicts",
                    url="https://news.example/report",
                    publisher="news.example"
                )
            ]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertTrue(result["supporting_evidence"])
        self.assertTrue(result["contradicting_evidence"])
        self.assertIn("both supports and contradicts", result["explanation"])

    def test_retrieval_failure_is_not_contradictory_evidence(self):
        result = assess_claim_verdict({
            "claim": "This investment guarantees a 30% return each month.",
            "source_search_status": "search_completed",
            "sources": [{
                "url": "https://finance.example/report",
                "title": "Finance report",
                "retrieval_status": "timeout",
                "limitations": "The source did not respond."
            }]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertEqual(result["contradicting_evidence"], [])
        self.assertEqual(len(result["retrieval_failures"]), 1)
        self.assertIn("not evidence", " ".join(result["limitations"]).casefold())

    def test_failed_lead_prevents_a_positive_verdict_from_an_incomplete_review(self):
        claim_text = "The college opened applications on 15 June."
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [
                source_record(
                    claim_text,
                    passage="The college opened applications on 15 June.",
                    url="https://college.example/notice"
                ),
                source_record(
                    claim_text,
                    passage="Applications opened at the college on 15 June.",
                    url="https://news.example/college",
                    publisher="news.example"
                ),
                {
                    "url": "https://archive.example/notice",
                    "title": "Archived notice",
                    "retrieval_status": "timeout",
                    "limitations": "Timeout"
                }
            ]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertEqual(len(result["supporting_evidence"]), 2)
        self.assertEqual(len(result["retrieval_failures"]), 1)
        self.assertFalse(result["evidence_sufficient"])

    def test_search_disabled_missing_results_and_missing_key_remain_unverified(self):
        for search_status in ("not_enabled", "not_configured", "no_results"):
            with self.subTest(search_status=search_status):
                result = assess_claim_verdict({
                    "claim": "The plant releases oxygen throughout the night.",
                    "source_search_status": search_status,
                    "sources": []
                })
                self.assertEqual(result["category_code"], "unverified")
                self.assertFalse(result["evidence_sufficient"])
                self.assertTrue(result["limitations"])

    def test_irrelevant_and_partial_pages_are_not_used_for_verdicts(self):
        claim_text = "Drinking lemon water removes all toxins from the body."
        irrelevant = source_record(
            claim_text,
            passage="A separate report discusses the local weather.",
            status="Does Not Address"
        )
        partial = source_record(
            claim_text,
            passage="Drinking lemon water removes all toxins from the body.",
            partial=True,
            url="https://partial.example/article"
        )
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [irrelevant, partial]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertEqual(result["supporting_evidence"], [])
        self.assertEqual(len(result["other_evidence"]), 1)
        self.assertTrue(any("Partial page text" in item for item in result["limitations"]))

    def test_malformed_assessment_and_claim_mismatch_are_ignored(self):
        claim_text = "The minister announced a new scholarship."
        mismatch = source_record(
            "A different claim was announced.",
            passage="The minister announced a new scholarship."
        )
        malformed = {
            "url": "https://malformed.example/report",
            "title": "Malformed report",
            "retrieval_status": "retrieved",
            "evidence_assessment": {"status": "Supports", "passages": "not a list"}
        }
        result = assess_claim_verdict({
            "claim": claim_text,
            "sources": [mismatch, malformed, None]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertEqual(result["supporting_evidence"], [])
        self.assertGreaterEqual(len(result["limitations"]), 2)

    def test_opinions_and_instructions_are_not_factual_claims(self):
        opinion = assess_claim_verdict({
            "claim": "This minister is the best leader.",
            "claim_type": "opinion"
        })
        instruction = assess_claim_verdict({
            "claim": "Forward this message to ten people.",
            "claim_type": "instruction"
        })

        self.assertEqual(opinion["category_code"], "not_factual")
        self.assertEqual(instruction["category_code"], "not_factual")
        self.assertTrue(opinion["evidence_sufficient"])
        self.assertTrue(instruction["evidence_sufficient"])

    def test_opinion_with_possible_fact_is_not_discarded(self):
        result = assess_claim_verdict({
            "claim": "I think this policy is terrible because it costs ₹5 billion.",
            "claim_type": "opinion"
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertIn("factual assertion", result["explanation"])

    def test_question_and_attributed_quote_are_assessed_as_factual_claims(self):
        for claim_type in ("question_containing_claim", "attributed_quote"):
            with self.subTest(claim_type=claim_type):
                result = assess_claim_verdict({
                    "claim": "Minister X said all students receive ₹10,000.",
                    "claim_type": claim_type,
                    "sources": []
                })
                self.assertEqual(result["category_code"], "unverified")

    def test_quote_content_evidence_cannot_be_reused_to_authenticate_attribution(self):
        claim_text = "Minister X said all students receive ₹10,000."
        result = assess_claim_verdict({
            "claim": claim_text,
            "claim_type": "attributed_quote",
            "sources": [
                source_record(
                    "All students receive ₹10,000.",
                    passage="All students receive ₹10,000."
                )
            ]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertEqual(result["supporting_evidence"], [])

    def test_multiple_quote_attribution_passages_support_only_the_attribution_wording(self):
        claim_text = "Minister X said that all students receive ₹10,000."
        result = assess_claim_verdict({
            "claim": claim_text,
            "claim_type": "attributed_quote",
            "sources": [
                source_record(
                    claim_text,
                    passage="A published transcript records: Minister X said that all students receive ₹10,000.",
                    url="https://transcript.example/speech"
                ),
                source_record(
                    claim_text,
                    passage="The interview report quotes Minister X: all students receive ₹10,000.",
                    url="https://interview.example/report",
                    publisher="interview.example"
                )
            ]
        })

        self.assertEqual(result["category_code"], "unverified")
        self.assertTrue(any(
            "independent corroboration" in item
            for item in result["limitations"]
        ))
        self.assertEqual(len(result["supporting_evidence"]), 2)

    def test_evidence_processing_is_topic_neutral_and_risk_score_independent(self):
        examples = (
            ("This vitamin prevents every viral infection.", "health"),
            ("The Treaty of Versailles was signed in 1918.", "history"),
            ("This investment guarantees a 30% return each month.", "finance"),
            ("The government announced a new scholarship.", "government schemes"),
            ("The minister announced a new scholarship.", "politics")
        )
        for claim_text, topic in examples:
            with self.subTest(topic=topic):
                sources = [
                    source_record(
                        claim_text,
                        passage=f"Independent report: {claim_text}",
                        url=f"https://one-{topic.replace(' ', '-')}.example/report"
                    ),
                    source_record(
                        claim_text,
                        passage=f"Another report: {claim_text}",
                        url=f"https://two-{topic.replace(' ', '-')}.example/report",
                        publisher=f"two-{topic.replace(' ', '-')}.example"
                    )
                ]
                with_risk = assess_claim_verdict({
                    "claim": claim_text,
                    "categories": [topic],
                    "risk_score": 100,
                    "sources": sources
                })
                no_risk = assess_claim_verdict({
                    "claim": claim_text,
                    "categories": [topic],
                    "risk_score": 0,
                    "sources": sources
                })
                self.assertEqual(with_risk["category_code"], "unverified")
                self.assertEqual(with_risk["category_code"], no_risk["category_code"])

    def test_verdict_explanations_are_localized(self):
        claim_text = "The college opened applications."
        claim = {
            "claim": claim_text,
            "sources": [source_record(claim_text)]
        }
        hindi = assess_claim_verdict(claim, "hi")
        hinglish = assess_claim_verdict(claim, "hinglish")

        self.assertEqual(hindi["category"], "अपुष्ट")
        self.assertEqual(hinglish["category"], "Unverified")
        self.assertNotEqual(hindi["explanation"], hinglish["explanation"])

    def test_missing_and_invalid_records_never_become_false(self):
        cases = (
            {"claim": "An unsupported factual assertion.", "sources": []},
            {"claim": "An unsupported factual assertion.", "sources": None},
            {"claim": "An unsupported factual assertion.", "sources": [{"url": "file:///x", "title": "X"}]},
            {"claim": "An unsupported factual assertion.", "sources": [{"url": "https://ok.example", "title": "X"}]}
        )
        for claim in cases:
            with self.subTest(claim=claim):
                result = assess_claim_verdict(claim)
                self.assertNotIn(
                    result["category_code"],
                    {"false", "mostly_false"}
                )
                self.assertEqual(result["category_code"], "unverified")


if __name__ == "__main__":
    unittest.main()
