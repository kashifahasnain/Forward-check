import json
import unittest
from unittest.mock import Mock, patch

import app
from modules import claim_extractor
from modules.risk_assessor import calculate_risk


TEST_A_MESSAGE = (
    "URGENT NOTICE FOR ALL COLLEGE STUDENTS!\n\n"
    "Every student will receive ₹10,000 in financial assistance this month. "
    "You must register before 8 PM today to qualify. Send your college ID and "
    "personal details immediately. Forward this message to at least 10 students "
    "so nobody misses this opportunity."
)
TEST_B_MESSAGE = (
    "Please check these websites before applying for the student benefit.\n\n"
    "Official information example: https://www.example.com/education\n\n"
    "Application information: https://student-benefit.example.com/apply\n\n"
    "Another reference: https://www.example.org/student-support\n\n"
    "The message claims that all students can receive financial assistance. "
    "Please verify the eligibility rules before sharing it."
)


class LanguageRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.analysis = {
            "claims": [],
            "warning_signals": [],
            "verification_steps": ["Check an original source."],
            "verification_links": [],
            "disclaimer": "Claims need independent verification.",
            "caution_explanation": "Pause and check independently."
        }

    def test_language_options_are_available_on_homepage(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="language-select"', response.data)
        self.assertIn(b'id="source-search-enabled"', response.data)
        self.assertIn('value="hi"'.encode(), response.data)
        self.assertIn('value="hinglish"'.encode(), response.data)

    def test_each_language_is_passed_to_analysis_without_changing_message(self):
        messages = {
            "en": "Students will receive free laptops.",
            "hi": "सभी छात्रों को मुफ्त लैपटॉप मिलेंगे।",
            "hinglish": "Sabhi students ko free laptop milenge.",
            "hi-mixed": "सभी students को free laptop मिलेंगे।"
        }

        for language, message in messages.items():
            with self.subTest(language=language):
                selected_language = "hi" if language == "hi-mixed" else language
                with patch.object(app, "extract_claims", return_value=self.analysis) as analyze:
                    response = self.client.post(
                        "/analyse",
                        data={"message": message, "language": selected_language}
                    )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["extracted_text"], message)
                self.assertEqual(response.get_json()["language"], selected_language)
                analyze.assert_called_once_with(message, language=selected_language)

    def test_unsupported_language_is_rejected(self):
        response = self.client.post(
            "/analyse",
            data={"message": "A message", "language": "fr"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported language", response.get_json()["error"])

    def test_switching_report_language_reuses_identical_message_text(self):
        message = "Students will receive free laptops."
        with patch.object(app, "extract_claims", return_value=self.analysis) as analyze:
            english = self.client.post(
                "/analyse",
                data={"message": message, "language": "en"}
            )
            hindi = self.client.post(
                "/analyse",
                data={"message": message, "language": "hi"}
            )

        self.assertEqual(english.get_json()["extracted_text"], message)
        self.assertEqual(hindi.get_json()["extracted_text"], message)
        self.assertEqual(english.get_json()["language"], "en")
        self.assertEqual(hindi.get_json()["language"], "hi")
        self.assertEqual(
            analyze.call_args_list[0].args[0],
            analyze.call_args_list[1].args[0]
        )
        self.assertEqual(
            [call.kwargs["language"] for call in analyze.call_args_list],
            ["en", "hi"]
        )


class OfflineClaimAnalysisTests(unittest.TestCase):
    def _mock_ollama(self, response_text):
        response = Mock()
        response.json.return_value = {"response": response_text}
        response.raise_for_status.return_value = None
        return response

    def test_topic_independent_fallback_extracts_requested_science_health_and_finance_claims(self):
        examples = (
            (
                "Drinking lemon water every morning removes all toxins from the body.",
                "removes all toxins"
            ),
            ("This vitamin prevents every viral infection.", "prevents every viral"),
            ("Eating a particular food doubles memory in seven days.", "doubles memory"),
            (
                "This investment guarantees a 30% return every month.",
                "guarantees a 30%"
            ),
            ("The Treaty of Versailles was signed in 1918.", "was signed in 1918"),
            ("This plant releases oxygen throughout the night.", "releases oxygen"),
            (
                "The government announced a new scholarship for every college student.",
                "announced a new scholarship"
            )
        )

        for message, expected_phrase in examples:
            with self.subTest(message=message):
                result = claim_extractor.fallback_analysis(message, "en")
                claims = [item["claim"] for item in result["claims"]]
                self.assertTrue(claims)
                self.assertEqual(result["extraction_method"], "local_rules")
                self.assertTrue(
                    any(expected_phrase.casefold() in claim.casefold() for claim in claims)
                )
                self.assertEqual(
                    result["claims"][0]["extraction_method"],
                    "local_rules"
                )

    def test_attributed_statement_preserves_speaker_and_extracts_underlying_claim(self):
        message = (
            "People are sharing a message claiming that Minister X said that "
            "all students will receive ₹10,000."
        )
        result = claim_extractor.fallback_analysis(message, "en")
        claims = result["claims"]

        attributed = next(
            item for item in claims
            if item["claim_type"] == "attributed_quote"
        )
        underlying = next(
            item for item in claims
            if item["claim_type"] == "factual_assertion"
        )
        self.assertIn("Minister X", attributed["claim"])
        self.assertEqual(attributed["alleged_speaker"], "Minister X")
        self.assertIn("₹10,000", underlying["claim"])
        self.assertEqual(underlying["alleged_speaker"], "Minister X")
        self.assertIn("Minister X said", attributed["evidence"])

    def test_quote_and_multiple_assertions_are_retained_separately(self):
        message = (
            'Celebrity A said, "This vitamin prevents every viral infection." '
            "The investment guarantees a 30% return every month."
        )
        result = claim_extractor.fallback_analysis(message, "en")
        claims = result["claims"]

        self.assertTrue(any(item["claim_type"] == "attributed_quote" for item in claims))
        self.assertTrue(any("vitamin prevents" in item["claim"].casefold() for item in claims))
        self.assertTrue(any("30%" in item["claim"] for item in claims))
        self.assertGreaterEqual(len(claims), 3)

    def test_question_and_opinion_with_factual_content_are_distinguished(self):
        question = claim_extractor.fallback_analysis(
            "Did this minister announce a new scholarship yesterday?",
            "en"
        )["claims"]
        opinion = claim_extractor.fallback_analysis(
            "I think the minister announced a new scholarship yesterday.",
            "en"
        )["claims"]
        pure_opinion = claim_extractor.fallback_analysis(
            "This minister is the best leader.",
            "en"
        )["claims"]
        instruction = claim_extractor.fallback_analysis(
            "Forward this message to ten people.",
            "en"
        )["claims"]

        self.assertTrue(question)
        self.assertEqual(question[0]["claim_type"], "question_containing_claim")
        self.assertTrue(any("scholarship" in item["claim"].casefold() for item in opinion))
        self.assertEqual(pure_opinion, [])
        self.assertEqual(instruction, [])

    def test_local_fallback_preserves_hindi_hinglish_and_claim_spans(self):
        examples = (
            (
                "सभी छात्रों को मुफ्त लैपटॉप मिलेंगे।",
                "hi"
            ),
            (
                "Sabhi students ko free laptop milenge.",
                "hinglish"
            ),
            (
                "सभी students को free laptop मिलेंगे।",
                "hi"
            )
        )
        for message, language in examples:
            with self.subTest(message=message):
                result = claim_extractor.fallback_analysis(message, language)
                self.assertTrue(result["claims"])
                self.assertIn(message.rstrip(".।"), result["claims"][0]["evidence"])
                self.assertIn(
                    result["claims"][0]["original_language"],
                    {"hi", "hinglish"}
                )

    def test_local_fallback_handles_urls_without_inventing_claims(self):
        message = (
            "Please review these websites before applying:\n"
            "https://www.example.com/education\n"
            "https://student-benefit.example.com/apply"
        )
        self.assertEqual(
            claim_extractor.fallback_analysis(message, "en")["claims"],
            []
        )

    def test_local_fallback_extracts_claim_after_multiple_urls(self):
        message = (
            "Check these references:\n"
            "https://www.example.com/education\n"
            "https://www.example.org/support\n"
            "Every college student can receive financial assistance."
        )
        result = claim_extractor.fallback_analysis(message, "en")
        self.assertTrue(
            any(
                "Every college student can receive financial assistance"
                in item["claim"]
                for item in result["claims"]
            )
        )

    def test_local_fallback_ignores_ordinary_nonfactual_text_and_empty_input(self):
        self.assertEqual(
            claim_extractor.fallback_analysis(
                "Happy birthday! Have a wonderful day.",
                "en"
            )["claims"],
            []
        )
        self.assertEqual(
            claim_extractor.extract_claims("  ", "en")["claims"],
            []
        )

    def test_local_fallback_extracts_an_ordinary_announcement(self):
        result = claim_extractor.fallback_analysis(
            "The school will be closed tomorrow.",
            "en"
        )
        self.assertIn(
            "The school will be closed tomorrow.",
            [item["claim"] for item in result["claims"]]
        )

    def test_spelled_out_historical_date_is_extracted_without_rewriting_claim(self):
        message = (
            "The Constitution of India came into effect on the twenty-sixth "
            "of January, nineteen fifty."
        )
        result = claim_extractor.fallback_analysis(message, "en")

        self.assertEqual(result["extraction_method"], "local_rules")
        self.assertTrue(result["verification_steps"])
        claim = next(
            item for item in result["claims"]
            if item["claim"] == message
        )
        self.assertEqual(claim["original_wording"], message)
        self.assertEqual(claim["evidence"], message)
        self.assertIn(
            "twenty-sixth of January, nineteen fifty",
            claim["entities"]["dates"]
        )
        self.assertNotIn("verdict", claim)

    def test_similar_claims_with_different_factual_details_are_not_merged(self):
        result = claim_extractor.fallback_analysis(
            "The Treaty was signed in 1918. The Treaty was signed in 1919.",
            "en"
        )
        claims = [item["claim"] for item in result["claims"]]
        self.assertTrue(any("1918" in claim for claim in claims))
        self.assertTrue(any("1919" in claim for claim in claims))

    def test_partial_model_claims_are_merged_with_local_fallback(self):
        message = (
            "The vitamin prevents every viral infection. "
            "This plant releases oxygen throughout the night."
        )
        response = self._mock_ollama(json.dumps({
            "claims": [{
                "claim": "The vitamin prevents every viral infection.",
                "evidence": "The vitamin prevents every viral infection."
            }],
            "warning_signals": [],
            "verification_steps": ["Check an independent source."],
            "caution_explanation": "Verify independently."
        }))
        with patch.object(claim_extractor.requests, "post", return_value=response):
            result = claim_extractor.extract_claims(message, "en")

        self.assertEqual(result["extraction_method"], "ollama_assisted")
        claims = [item["claim"] for item in result["claims"]]
        self.assertTrue(any("vitamin prevents" in claim.casefold() for claim in claims))
        self.assertTrue(any("plant releases" in claim.casefold() for claim in claims))
        self.assertIn(
            "ollama",
            {item["extraction_method"] for item in result["claims"]}
        )
        self.assertIn(
            "local_rules",
            {item["extraction_method"] for item in result["claims"]}
        )

    def test_model_opinions_and_instructions_are_not_shown_as_factual_claims(self):
        message = (
            "This minister is the best leader. "
            "Forward this message to ten people."
        )
        response = self._mock_ollama(json.dumps({
            "claims": [
                {
                    "claim": "This minister is the best leader.",
                    "claim_type": "opinion",
                    "evidence": "This minister is the best leader."
                },
                {
                    "claim": "Forward this message to ten people.",
                    "claim_type": "instruction",
                    "evidence": "Forward this message to ten people."
                }
            ],
            "warning_signals": [],
            "verification_steps": ["Look for an original statement."],
            "caution_explanation": "Pause and check independently."
        }))
        with patch.object(claim_extractor.requests, "post", return_value=response):
            result = claim_extractor.extract_claims(message, "en")

        self.assertEqual(result["claims"], [])

    def test_all_three_languages_and_mixed_text_have_fallback_claims(self):
        examples = (
            (
                "en",
                "Students will receive free laptops.",
                "The message says students will receive free laptops."
            ),
            (
                "hi",
                "सभी छात्रों को मुफ्त लैपटॉप मिलेंगे।",
                "संदेश में दावा है कि छात्रों को मुफ्त लैपटॉप मिलेंगे।"
            ),
            (
                "hinglish",
                "Sabhi students ko free laptop milenge.",
                "Message mein claim hai ki students ko free laptops milenge."
            ),
            (
                "hi",
                "सभी students को free laptop मिलेंगे।",
                "संदेश में दावा है कि छात्रों को मुफ्त लैपटॉप मिलेंगे।"
            )
        )

        for language, message, expected_claim in examples:
            with self.subTest(language=language, message=message):
                with patch.object(
                    claim_extractor.requests,
                    "post",
                    side_effect=claim_extractor.requests.Timeout("offline test")
                ):
                    result = claim_extractor.extract_claims(message, language)

                self.assertEqual(result["claims"][0]["claim"], expected_claim)
                self.assertTrue(result["verification_steps"])
                self.assertTrue(result["caution_explanation"])

    def test_exact_test_a_message_returns_all_three_requested_claims(self):
        with patch.object(
            claim_extractor.requests,
            "post",
            side_effect=claim_extractor.requests.Timeout("offline test")
        ):
            response = app.app.test_client().post(
                "/analyse",
                data={"message": TEST_A_MESSAGE, "language": "en"}
            )

        self.assertEqual(response.status_code, 200)
        claims = [
            item["claim"]
            for item in response.get_json()["analysis"]["claims"]
        ]
        self.assertIn(
            "Every student will receive ₹10,000 in financial assistance this month.",
            claims
        )
        self.assertIn("Students must register before 8 PM today to qualify.", claims)
        self.assertIn(
            "Students must provide their college ID and personal details to receive the benefit.",
            claims
        )
        self.assertFalse(any("Forward this message" in claim for claim in claims))

    def test_exact_test_b_extracts_the_embedded_assistance_claim_and_link_signal(self):
        with patch.object(
            claim_extractor.requests,
            "post",
            side_effect=claim_extractor.requests.Timeout("offline test")
        ):
            result = app.app.test_client().post(
                "/analyse",
                data={"message": TEST_B_MESSAGE, "language": "en"}
            )

        self.assertEqual(result.status_code, 200)
        body = result.get_json()
        claims = [
            item["claim"]
            for item in body["analysis"]["claims"]
        ]
        self.assertIn(
            "All students can receive financial assistance.",
            claims
        )
        self.assertEqual(body["detected_urls"], [
            "https://www.example.com/education",
            "https://student-benefit.example.com/apply",
            "https://www.example.org/student-support"
        ])
        signals = body["analysis"]["warning_signals"]
        self.assertTrue(any(item["signal"] == "Link included" for item in signals))
        self.assertFalse(any(
            item["signal"] in {"Urgency", "Forwarding request"}
            for item in signals
        ))
        self.assertFalse(any(
            "verify the eligibility rules" in claim.casefold()
            for claim in claims
        ))
        self.assertEqual(body["analysis"]["risk_assessment"]["score"], 2)

    def test_test_b_claim_keeps_exact_original_wording_and_search_metadata(self):
        with patch.object(
            claim_extractor.requests,
            "post",
            side_effect=claim_extractor.requests.Timeout("offline test")
        ):
            result = claim_extractor.extract_claims(TEST_B_MESSAGE, "en")

        benefit_claim = next(
            item for item in result["claims"]
            if item["claim"] == "All students can receive financial assistance."
        )
        self.assertEqual(
            benefit_claim["original_wording"],
            "all students can receive financial assistance"
        )
        self.assertEqual(
            benefit_claim["normalized_wording"],
            benefit_claim["claim"]
        )
        self.assertTrue(benefit_claim["categories"])
        self.assertIsInstance(benefit_claim["entities"], dict)
        self.assertIn("The message claims that", TEST_B_MESSAGE)

    def test_benefit_claim_without_urls_is_extracted(self):
        message = "All students can receive financial assistance."
        with patch.object(
            claim_extractor.requests,
            "post",
            side_effect=claim_extractor.requests.Timeout("offline test")
        ):
            result = claim_extractor.extract_claims(message, "en")

        self.assertIn(
            message,
            [item["claim"] for item in result["claims"]]
        )

    def test_explicit_hindi_and_hinglish_benefit_claims_are_extracted(self):
        examples = (
            ("hi", "सभी छात्रों को आर्थिक सहायता मिल सकती है।"),
            ("hinglish", "Sabhi students ko financial assistance mil sakti hai.")
        )
        for language, message in examples:
            with self.subTest(language=language):
                with patch.object(
                    claim_extractor.requests,
                    "post",
                    side_effect=claim_extractor.requests.Timeout("offline test")
                ):
                    result = claim_extractor.extract_claims(message, language)
                self.assertIn(
                    message.rstrip(".।"),
                    [
                        claim["claim"].rstrip(".।")
                        for claim in result["claims"]
                    ]
                )

    def test_urls_without_factual_claims_do_not_create_claims_or_urgency(self):
        message = (
            "Please review these websites before applying:\n"
            "https://www.example.com/education\n"
            "https://student-benefit.example.com/apply"
        )
        with patch.object(
            claim_extractor.requests,
            "post",
            side_effect=claim_extractor.requests.Timeout("offline test")
        ):
            result = claim_extractor.extract_claims(message, "en")

        self.assertEqual(result["claims"], [])
        labels = {item["signal"] for item in result["warning_signals"]}
        self.assertEqual(labels, {"Link included"})
        self.assertNotIn("Urgency", labels)
        self.assertNotIn("Forwarding request", labels)

    def test_empty_or_malformed_ollama_output_uses_test_a_fallback_claims(self):
        empty_response = self._mock_ollama("")
        malformed_response = self._mock_ollama("{not valid JSON")
        for response in (empty_response, malformed_response):
            with self.subTest(response=response.json.return_value):
                with patch.object(
                    claim_extractor.requests,
                    "post",
                    return_value=response
                ):
                    result = claim_extractor.extract_claims(TEST_A_MESSAGE, "en")

                claims = [item["claim"] for item in result["claims"]]
                self.assertIn(
                    "Every student will receive ₹10,000 in financial assistance this month.",
                    claims
                )
                self.assertIn("Students must register before 8 PM today to qualify.", claims)

    def test_assistance_claims_are_extracted_from_hindi_and_hinglish(self):
        examples = (
            (
                "hi",
                "सभी छात्रों को ₹10,000 की आर्थिक सहायता इस महीने मिलेगी।"
            ),
            (
                "hinglish",
                "Sabhi students ko ₹10,000 ki financial assistance is month milegi."
            )
        )

        for language, message in examples:
            with self.subTest(language=language):
                with patch.object(
                    claim_extractor.requests,
                    "post",
                    side_effect=claim_extractor.requests.Timeout("offline test")
                ):
                    result = claim_extractor.extract_claims(message, language)

                self.assertTrue(result["claims"])
                self.assertIn("₹10,000", result["claims"][0]["claim"])

    def test_paired_hindi_hinglish_negation_keeps_original_evidence(self):
        examples = (
            (
                "hi",
                "सभी छात्रों को ₹10,000 की आर्थिक सहायता मिलेगी।"
            ),
            (
                "hi",
                "सभी छात्रों को ₹10,000 की आर्थिक सहायता नहीं मिलेगी।"
            ),
            (
                "hinglish",
                "Sabhi students ko ₹10,000 ki financial assistance milegi."
            ),
            (
                "hinglish",
                "Sabhi students ko ₹10,000 ki financial assistance nahi milegi."
            )
        )
        for language, message in examples:
            with self.subTest(message=message):
                result = claim_extractor.fallback_analysis(message, language)
                self.assertTrue(result["claims"])
                self.assertTrue(any(
                    claim.get("original_wording") == message
                    and message in claim.get("evidence", "")
                    for claim in result["claims"]
                ))

    def test_multiple_hindi_claims_are_not_deduplicated_as_empty_ascii_keys(self):
        message = (
            "सभी छात्रों को ₹10,000 की आर्थिक सहायता इस महीने मिलेगी। "
            "सभी छात्रों को 8 बजे तक पंजीकरण करना होगा।"
        )
        with patch.object(
            claim_extractor.requests,
            "post",
            side_effect=claim_extractor.requests.Timeout("offline test")
        ):
            result = claim_extractor.extract_claims(message, "hi")

        claims = [item["claim"] for item in result["claims"]]
        self.assertTrue(any("₹10,000" in claim for claim in claims))
        self.assertTrue(any("पंजीकरण करना होगा" in claim for claim in claims))
        self.assertGreaterEqual(len(claims), 2)

    def test_url_containing_text_keeps_supported_claim_and_not_url_as_claim(self):
        message = (
            "Every student will receive ₹10,000 in financial assistance this month. "
            "Check https://example.com/education."
        )
        with patch.object(
            claim_extractor.requests,
            "post",
            side_effect=claim_extractor.requests.Timeout("offline test")
        ):
            result = claim_extractor.extract_claims(message, "en")

        claims = [item["claim"] for item in result["claims"]]
        self.assertIn(
            "Every student will receive ₹10,000 in financial assistance this month.",
            claims
        )
        self.assertFalse(any("https://example.com" in claim for claim in claims))

    def test_ordinary_announcement_is_preserved_as_a_checkable_claim(self):
        message = "The college will open applications on 15 June."
        with patch.object(
            claim_extractor.requests,
            "post",
            side_effect=claim_extractor.requests.Timeout("offline test")
        ):
            result = claim_extractor.extract_claims(message, "en")

        self.assertIn(
            message,
            [item["claim"] for item in result["claims"]]
        )

    def test_model_claims_accept_object_and_list_formats_without_dropping_items(self):
        claims = [
            "Students will receive ₹10,000 in financial assistance this month.",
            {"statement": "Applications close today."},
            {"claim": "Students must register.", "reason": "Check the deadline."}
        ]
        result = claim_extractor._normalize_model_claims(claims)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[1]["claim"], "Applications close today.")
        self.assertEqual(result[1]["reason_to_check"], "")
        self.assertEqual(result[2]["reason_to_check"], "Check the deadline.")

        single_dict = claim_extractor._normalize_model_claims({
            "claim": "Students may apply.",
            "reason_to_check": "Check the published notice."
        })
        self.assertEqual(len(single_dict), 1)

        mapped = claim_extractor._normalize_model_claims({
            "Students may receive assistance.": "Verify eligibility."
        })
        self.assertEqual(mapped[0]["claim"], "Students may receive assistance.")

    def test_warning_only_message_does_not_get_an_invented_factual_claim(self):
        message = "URGENT! Forward this offer to everyone immediately."
        with patch.object(
            claim_extractor.requests,
            "post",
            side_effect=claim_extractor.requests.Timeout("offline test")
        ):
            result = claim_extractor.extract_claims(message, "en")

        self.assertEqual(result["claims"], [])
        self.assertTrue(result["warning_signals"])

    def test_top_level_list_ai_response_is_normalized_and_merged_with_fallback(self):
        response = self._mock_ollama(json.dumps([
            "Every student will receive ₹10,000 in financial assistance this month.",
            {
                "statement": "Students must register before 8 PM today to qualify.",
                "evidence": "You must register before 8 PM today to qualify."
            }
        ]))
        with patch.object(claim_extractor.requests, "post", return_value=response):
            result = claim_extractor.extract_claims(TEST_A_MESSAGE, "en")

        claims = [item["claim"] for item in result["claims"]]
        self.assertIn(
            "Every student will receive ₹10,000 in financial assistance this month.",
            claims
        )
        self.assertIn("Students must register before 8 PM today to qualify.", claims)
        self.assertTrue(result["verification_steps"])

    def test_top_level_claim_dictionary_is_normalized(self):
        response = self._mock_ollama(json.dumps({
            "claim": "The college will open applications on 15 June.",
            "reason_to_check": "Check the college's published notice."
        }))
        with patch.object(claim_extractor.requests, "post", return_value=response):
            result = claim_extractor.extract_claims(
                "The college will open applications on 15 June.",
                "en"
            )

        self.assertEqual(
            result["claims"][0]["claim"],
            "The college will open applications on 15 June."
        )
        self.assertEqual(
            result["claims"][0]["reason_to_check"],
            "Check the college's published notice."
        )

    def test_model_verification_instruction_is_not_returned_as_a_claim(self):
        response = self._mock_ollama(json.dumps({
            "claims": [{
                "claim": "Please verify the eligibility rules before sharing it.",
                "evidence": "Please verify the eligibility rules before sharing it."
            }],
            "warning_signals": [],
            "verification_steps": ["Compare the claim with an official source."],
            "caution_explanation": "Verify this independently."
        }))
        with patch.object(claim_extractor.requests, "post", return_value=response):
            result = claim_extractor.extract_claims(TEST_B_MESSAGE, "en")

        claims = [item["claim"] for item in result["claims"]]
        self.assertNotIn(
            "Please verify the eligibility rules before sharing it.",
            claims
        )
        self.assertIn("All students can receive financial assistance.", claims)

    def test_unanchored_model_claim_is_replaced_by_source_supported_fallback(self):
        response = self._mock_ollama(json.dumps({
            "claims": [{
                "claim": "The government has approved this scheme.",
                "evidence": "Forward this message to at least 10 students."
            }],
            "warning_signals": [],
            "verification_steps": ["Check an official announcement."],
            "caution_explanation": "Verify this independently."
        }))
        with patch.object(claim_extractor.requests, "post", return_value=response):
            result = claim_extractor.extract_claims(TEST_A_MESSAGE, "en")

        claims = [item["claim"] for item in result["claims"]]
        self.assertNotIn("The government has approved this scheme.", claims)
        self.assertIn(
            "Every student will receive ₹10,000 in financial assistance this month.",
            claims
        )

    def test_suspicious_messages_are_detected_in_each_language(self):
        examples = (
            ("en", "URGENT! Share this with all your friends today."),
            ("hi", "तुरंत! इसे सबको भेजें।"),
            ("hinglish", "Abhi share karo, sabko bhejo!"),
            ("hi", "तुरंत share karo, इसे सबको भेजें।")
        )

        for language, message in examples:
            with self.subTest(language=language, message=message):
                with patch.object(
                    claim_extractor.requests,
                    "post",
                    side_effect=claim_extractor.requests.Timeout("offline test")
                ):
                    result = claim_extractor.extract_claims(message, language)

                labels = {
                    item["signal"]
                    for item in result["warning_signals"]
                }
                self.assertIn("Urgency", labels)
                self.assertIn("Forwarding request", labels)

    def test_hindi_scheme_messages_get_official_verification_links(self):
        result = claim_extractor.fallback_analysis(
            "सरकार की मुफ्त लैपटॉप योजना सभी छात्रों के लिए है।",
            "hi"
        )

        link_by_url = {
            item["url"]: item
            for item in result["verification_links"]
        }
        self.assertIn("https://www.myscheme.gov.in/", link_by_url)
        self.assertIn("https://www.pib.gov.in/", link_by_url)
        self.assertIn("आधिकारिक", link_by_url["https://www.pib.gov.in/"]["description"])

    def test_timeout_and_malformed_json_return_localized_fallback(self):
        message = "Aaj hi share karo: students ko free laptop milenge."
        cases = (
            claim_extractor.requests.Timeout("offline test"),
            self._mock_ollama("{not valid JSON")
        )

        for failure in cases:
            with self.subTest(failure=type(failure).__name__):
                with patch.object(claim_extractor.requests, "post", side_effect=failure):
                    result = claim_extractor.extract_claims(message, "hinglish")

                self.assertEqual(result["extraction_method"], "local_rules")
                self.assertTrue(result["claims"])
                self.assertTrue(result["verification_steps"])
                self.assertTrue(result["disclaimer"].startswith("Forward Check claims"))
                self.assertTrue(result["warning_signals"])

    def test_incomplete_json_uses_fallback_instead_of_an_empty_report(self):
        message = "Students will receive free laptops."
        incomplete = self._mock_ollama(json.dumps({"claims": [], "warning_signals": []}))

        with patch.object(claim_extractor.requests, "post", return_value=incomplete):
            result = claim_extractor.extract_claims(message, "en")

        self.assertTrue(result["claims"])
        self.assertTrue(result["verification_steps"])
        self.assertTrue(result["caution_explanation"])

    def test_empty_input_does_not_call_ollama(self):
        with patch.object(claim_extractor.requests, "post") as ollama:
            result = claim_extractor.extract_claims("  ", "hi")

        ollama.assert_not_called()
        self.assertEqual(result["claims"], [])
        self.assertIn("Forward Check", result["disclaimer"])

    def test_prompt_requests_selected_language_and_exact_evidence(self):
        model_result = {
            "claims": [],
            "warning_signals": [],
            "verification_steps": ["आधिकारिक वेबसाइट पर मूल घोषणा खोजें।"],
            "caution_explanation": "दावे की स्वतंत्र रूप से जाँच करें।"
        }
        response = self._mock_ollama(json.dumps(model_result, ensure_ascii=False))

        with patch.object(claim_extractor.requests, "post", return_value=response) as post:
            result = claim_extractor.extract_claims(
                "सभी छात्रों को मुफ्त लैपटॉप मिलेंगे।", "hi"
            )

        prompt = post.call_args.kwargs["json"]["prompt"]
        self.assertIn("natural, easy-to-understand Hindi written in Devanagari", prompt)
        self.assertIn("Copy evidence exactly", prompt)
        self.assertEqual(result["verification_steps"], model_result["verification_steps"])


class MultilingualRiskTests(unittest.TestCase):
    def test_urgent_forward_in_hindi_is_scored(self):
        result = calculate_risk("तुरंत! इसे सबको भेजें।")

        self.assertEqual(result["level"], "Medium Caution")
        self.assertEqual(
            {reason["category"] for reason in result["reasons"]},
            {"urgency", "mass_forwarding"}
        )

    def test_hinglish_urgent_forward_and_credential_request_are_scored(self):
        result = calculate_risk(
            "Abhi share karo aur apna OTP bhejo.",
            [{"signal": "Urgency"}, {"signal": "Forwarding request"}]
        )

        self.assertEqual(result["level"], "High Caution")
        self.assertIn(
            "credential_request",
            {reason["category"] for reason in result["reasons"]}
        )

    def test_hindi_advice_not_to_share_otp_is_not_scored_as_a_request(self):
        result = calculate_risk("अपना OTP कभी साझा न करें।")

        self.assertEqual(result["score"], 0)


if __name__ == "__main__":
    unittest.main()
