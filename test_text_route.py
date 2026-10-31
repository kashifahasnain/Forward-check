import io
import unittest
from unittest.mock import patch

from PIL import Image
import requests

import app


class AnalyseRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.analysis = {
            "claims": [],
            "warning_signals": [],
            "verification_steps": ["Check an original source."],
            "verification_links": [],
            "disclaimer": (
                "Forward Check helps you investigate claims. "
                "It does not independently establish whether a message is true or false."
            )
        }

    def test_pasted_text_uses_shared_analysis_and_reports_urls_without_opening_them(self):
        message = "A forwarded post says check https://example.com/offer."

        with patch.object(app, "extract_claims", return_value=self.analysis) as analyze:
            response = self.client.post("/analyse", data={"message": message})

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["extracted_text"], message)
        self.assertEqual(body["detected_urls"], ["https://example.com/offer"])
        self.assertEqual(body["analysis"]["claims"], self.analysis["claims"])
        self.assertEqual(
            body["analysis"]["risk_assessment"]["level"],
            "Low Caution"
        )
        analyze.assert_called_once_with(
            message,
            language="en"
        )

    def test_text_with_multiple_urls_returns_json_without_opening_them(self):
        message = (
            "Check these links: https://www.example.com/education and "
            "https://student-benefit.example.com/apply."
        )

        with patch.object(app, "extract_claims", return_value=self.analysis) as analyze:
            response = self.client.post(
                "/analyse",
                data={"message": message, "language": "hinglish"}
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["language"], "hinglish")
        self.assertEqual(body["detected_urls"], [
            "https://www.example.com/education",
            "https://student-benefit.example.com/apply"
        ])
        self.assertFalse(body["website_content_checked"])
        analyze.assert_called_once()
        self.assertIn("https://", analyze.call_args.args[0])
        self.assertIn("student-benefit.example.com", analyze.call_args.args[0])
        self.assertEqual(analyze.call_args.kwargs["language"], "hinglish")

    def test_home_uses_flask_generated_same_origin_analysis_endpoint(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-analyse-url="/analyse"', response.data)
        self.assertIn(b'src="/static/script.js"', response.data)

    def test_search_consent_describes_configured_external_providers(self):
        response = self.client.get("/")

        self.assertIn(b"Tavily", response.data)
        self.assertIn(b"optional Brave fallback", response.data)
        self.assertNotIn(
            b"to Brave Search for source leads",
            response.data
        )

    def test_warning_signal_label_and_url_punctuation_are_localized_in_frontend(self):
        with open("static/script.js", encoding="utf-8") as script:
            source = script.read()

        self.assertIn("Government-looking web address", source)
        self.assertIn("सरकारी जैसा दिखने वाला web address", source)
        self.assertIn("Government jaisa dikhne wala web address", source)

    def test_url_extraction_removes_quotes_and_sentence_punctuation(self):
        message = 'Visit "https://example.com/claim?source=forward".'

        with patch.object(app, "extract_claims", return_value=self.analysis):
            response = self.client.post("/analyse", data={"message": message})

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["detected_urls"], ["https://example.com/claim?source=forward"])
        self.assertEqual(body["url_analysis"][0]["url"], body["detected_urls"][0])

    def test_scope_is_used_by_the_copied_report_builder(self):
        with open("static/script.js", encoding="utf-8") as script:
            source = script.read()

        self.assertIn(
            't("scopeHeading"), metadata.analysis_scope.trim()',
            source
        )
        self.assertIn("analysis.gemma_provenance", source)
        self.assertIn('t("gemmaContribution")', source)
        self.assertIn("renderGemmaContribution", source)

    def test_ollama_timeout_uses_fallback_and_still_returns_json(self):
        with patch(
            "modules.claim_extractor.requests.post",
            side_effect=requests.Timeout("offline test")
        ):
            response = self.client.post(
                "/analyse",
                data={"message": "Students will receive free laptops."}
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["analysis"]["claims"])
        self.assertTrue(body["analysis"]["verification_steps"])

    def test_flask_route_preserves_hinglish_claim_on_ollama_timeout(self):
        message = (
            "Bharat ka Samvidhan 26 January 1950 ko lagu hua tha, "
            "aur Dr. B. R. Ambedkar Drafting Committee ke Chairman the."
        )
        with patch(
            "modules.claim_extractor.requests.post",
            side_effect=requests.Timeout("offline test")
        ):
            response = self.client.post(
                "/analyse",
                data={"message": message, "language": "en"}
            )

        self.assertEqual(response.status_code, 200)
        analysis = response.get_json()["analysis"]
        self.assertEqual(analysis["extraction_method"], "local_rules")
        self.assertEqual(
            analysis["gemma_provenance"]["failure_reason"],
            "timeout"
        )
        self.assertTrue(analysis["claims"])
        self.assertTrue(
            any(
                claim["original_language"] == "hinglish"
                for claim in analysis["claims"]
            )
        )

    def test_empty_claims_render_one_fallback_explanation(self):
        with open("static/script.js", encoding="utf-8") as script:
            source = script.read()

        render_start = source.index("function renderClaims(")
        render_end = source.index("function renderGemmaContribution(")
        render_claims = source[render_start:render_end]
        self.assertNotIn('t("extractionFallback")', render_claims)

    def test_unexpected_analysis_error_returns_json_500(self):
        with patch.object(
            app,
            "analyze_message",
            side_effect=RuntimeError("test failure")
        ):
            response = self.client.post(
                "/analyse",
                data={"message": "A message to analyse."}
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json()["error"],
            "An unexpected server error occurred. Check the Flask terminal logs."
        )

    def test_incomplete_analysis_pipeline_result_returns_json_500(self):
        with patch.object(app, "analyze_message", return_value={"analysis": {}}):
            response = self.client.post(
                "/analyse",
                data={"message": "A message to analyse."}
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json()["error"],
            "An unexpected server error occurred. Check the Flask terminal logs."
        )

    def test_empty_pasted_text_returns_helpful_error(self):
        response = self.client.post("/analyse", data={"message": "  \n "})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"],
            "Please paste a message to analyse."
        )

    def test_request_without_text_or_screenshot_returns_helpful_error(self):
        response = self.client.post("/analyse", data={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"],
            "Please upload a screenshot or paste message text."
        )

    def test_analysis_route_rejects_wrong_method_with_json(self):
        response = self.client.get("/analyse")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(
            response.get_json()["error"],
            "The method is not allowed for the requested URL."
        )

    def test_request_cannot_submit_text_and_screenshot_together(self):
        image_buffer = io.BytesIO()
        Image.new("RGB", (4, 4), "white").save(image_buffer, format="PNG")
        image_buffer.seek(0)

        response = self.client.post(
            "/analyse",
            data={
                "message": "A message",
                "image": (image_buffer, "message.png")
            },
            content_type="multipart/form-data"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("either pasted message text or a screenshot", response.get_json()["error"])

    def test_text_over_limit_is_rejected(self):
        message = "a" * (app.MAX_MESSAGE_LENGTH + 1)

        response = self.client.post("/analyse", data={"message": message})

        self.assertEqual(response.status_code, 413)

    def test_existing_screenshot_upload_still_uses_shared_analysis(self):
        image_buffer = io.BytesIO()
        Image.new("RGB", (4, 4), "white").save(image_buffer, format="PNG")
        image_buffer.seek(0)
        extracted_text = "A screenshot message https://example.com"

        with (
            patch.object(app.pytesseract, "image_to_string", return_value=extracted_text),
            patch.object(app, "extract_claims", return_value=self.analysis) as analyze,
        ):
            response = self.client.post(
                "/analyse",
                data={"image": (image_buffer, "message.png")},
                content_type="multipart/form-data"
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["extracted_text"], extracted_text)
        self.assertEqual(body["detected_urls"], ["https://example.com"])
        self.assertEqual(
            body["analysis"]["risk_assessment"]["level"],
            "Low Caution"
        )
        analyze.assert_called_once_with(
            extracted_text,
            language="en"
        )

    def test_hindi_screenshot_uses_hindi_ocr_data_when_available(self):
        image_buffer = io.BytesIO()
        Image.new("RGB", (4, 4), "white").save(image_buffer, format="PNG")
        image_buffer.seek(0)

        with (
            patch.object(app.pytesseract, "get_languages", return_value=["eng", "hin"]),
            patch.object(app.pytesseract, "image_to_string", return_value="हिंदी संदेश") as ocr,
            patch.object(app, "extract_claims", return_value=self.analysis),
        ):
            response = self.client.post(
                "/analyse",
                data={
                    "language": "hi",
                    "image": (image_buffer, "message.png")
                },
                content_type="multipart/form-data"
            )

        self.assertEqual(response.status_code, 200)
        ocr.assert_called_once()
        self.assertEqual(ocr.call_args.kwargs["lang"], "eng+hin")
        self.assertEqual(response.get_json()["extracted_text"], "हिंदी संदेश")

    def test_hindi_screenshot_without_hindi_ocr_data_gets_helpful_error(self):
        image_buffer = io.BytesIO()
        Image.new("RGB", (4, 4), "white").save(image_buffer, format="PNG")
        image_buffer.seek(0)

        with (
            patch.object(app.pytesseract, "get_languages", return_value=["eng"]),
            patch.object(app.pytesseract, "image_to_string", return_value=""),
        ):
            response = self.client.post(
                "/analyse",
                data={
                    "language": "hi",
                    "image": (image_buffer, "message.png")
                },
                content_type="multipart/form-data"
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("hin.traineddata", response.get_json()["error"])

    def test_invalid_analysis_fields_still_return_a_risk_assessment(self):
        with patch.object(app, "extract_claims", return_value=None):
            response = self.client.post(
                "/analyse",
                data={"message": "A message without warning indicators."}
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["analysis"]["claims"], [])
        self.assertEqual(
            body["analysis"]["risk_assessment"]["level"],
            "Low Caution"
        )

    def test_missing_analysis_disclaimer_uses_selected_language(self):
        with patch.object(app, "extract_claims", return_value=None):
            response = self.client.post(
                "/analyse",
                data={"message": "एक संदेश", "language": "hi"}
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("दावों की जाँच", body["analysis"]["disclaimer"])
        self.assertIn(
            "चेतावनी संकेत",
            body["analysis"]["risk_assessment"]["disclaimer"]
        )


if __name__ == "__main__":
    unittest.main()
