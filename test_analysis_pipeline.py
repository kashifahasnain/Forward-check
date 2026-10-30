import io
import unittest
from unittest.mock import patch

from PIL import Image

import app
from modules.analysis_pipeline import analyze_message, find_urls
from modules.url_analyzer import analyze_url


class SharedPipelineTests(unittest.TestCase):
    def setUp(self):
        self.analysis = {
            "claims": [{"claim": "A message claim.", "reason_to_check": "Check a source."}],
            "warning_signals": [],
            "verification_steps": ["Compare with an original announcement."],
            "verification_links": [],
            "disclaimer": "Claims need independent verification.",
            "caution_explanation": "Check this message independently."
        }

    def test_pure_url_skips_claim_model_and_never_fetches_page(self):
        with patch("modules.analysis_pipeline.extract_claims") as model:
            result = analyze_message("https://example.com/path")

        model.assert_not_called()
        self.assertEqual(result["input_type"], "url")
        self.assertEqual(result["content_type"], "url")
        self.assertEqual(result["analysis"]["claims"], [])
        self.assertFalse(result["website_content_checked"])
        self.assertIn("not checked", result["analysis"]["disclaimer"])

    def test_multiple_urls_with_connectors_skip_claim_model(self):
        message = "https://example.com and https://example.in"
        with patch("modules.analysis_pipeline.extract_claims") as model:
            result = analyze_message(message)

        model.assert_not_called()
        self.assertEqual(result["content_type"], "url")
        self.assertEqual(result["detected_urls"], [
            "https://example.com",
            "https://example.in"
        ])
        self.assertEqual(result["analysis"]["claims"], [])

    def test_plain_url_without_scheme_is_detected(self):
        self.assertEqual(find_urls("example.xyz"), ["example.xyz"])
        result = analyze_message("example.xyz")

        self.assertEqual(result["content_type"], "url")
        self.assertEqual(result["detected_urls"], ["example.xyz"])
        self.assertEqual(result["analysis"]["risk_assessment"]["score"], 0)

    def test_multiple_urls_are_unique_and_individually_inspected(self):
        message = "Read https://example.xyz and www.example.in; then https://example.xyz"
        result = analyze_message(message, claim_analyzer=lambda *_args, **_kwargs: self.analysis)

        self.assertEqual(
            result["detected_urls"],
            ["https://example.xyz", "www.example.in"]
        )
        self.assertEqual(len(result["url_analysis"]), 2)
        self.assertTrue(all(not item["website_content_checked"] for item in result["url_analysis"]))
        self.assertEqual(result["extracted_text"], message)

    def test_message_and_url_are_sent_through_separate_analysis_paths(self):
        message = "Students will receive laptops. https://example.com/free-laptop"
        with patch("modules.analysis_pipeline.extract_claims", return_value=self.analysis) as model:
            result = analyze_message(message)

        model.assert_called_once_with(message, language="en")
        self.assertEqual(result["extracted_text"], message)
        self.assertEqual(result["detected_urls"], ["https://example.com/free-laptop"])

    def test_image_ocr_text_is_analyzed_with_image_source_metadata(self):
        result = analyze_message(
            "Notice: https://example.com",
            source_type="image",
            claim_analyzer=lambda *_args, **_kwargs: self.analysis
        )

        self.assertEqual(result["input_type"], "image")
        self.assertEqual(result["source_type"], "image")
        self.assertEqual(result["content_type"], "text")
        self.assertIn("OCR", result["analysis_scope"])

    def test_hindi_and_hinglish_url_reports_are_localized(self):
        hindi = analyze_message("http://example.in", language="hi")
        hinglish = analyze_message("http://example.in", language="hinglish")

        self.assertIn("URL HTTPS", hindi["url_analysis"][0]["warning_signals"][0]["explanation"])
        self.assertIn("URL HTTPS", hinglish["url_analysis"][0]["warning_signals"][0]["explanation"])
        self.assertIn("वेबसाइट", hindi["analysis_scope"])
        self.assertIn("Website", hinglish["analysis_scope"])


class UrlAnalyzerTests(unittest.TestCase):
    def test_ordinary_https_and_unfamiliar_top_level_domains_are_not_flagged(self):
        for url in (
            "https://example.com",
            "https://example.in",
            "https://example.xyz"
        ):
            with self.subTest(url=url):
                result = analyze_url(url)
                self.assertTrue(result["valid_syntax"])
                self.assertEqual(result["risk_categories"], [])

    def test_http_is_a_limited_warning(self):
        result = analyze_url("http://example.com")

        self.assertEqual(
            result["risk_categories"],
            [{"category": "unencrypted_http", "points": 1}]
        )
        self.assertIn("not proof", result["warning_signals"][0]["explanation"])

    def test_invalid_missing_host_and_user_information_are_detected(self):
        invalid = analyze_url("https://[broken")
        missing_host = analyze_url("https:///path")
        userinfo = analyze_url("https://trusted.example@evil.example/path")

        self.assertFalse(invalid["valid_syntax"])
        self.assertFalse(missing_host["valid_syntax"])
        self.assertEqual(userinfo["hostname"], "evil.example")
        self.assertIn("suspicious_url_structure", {
            item["category"] for item in userinfo["risk_categories"]
        })

    def test_ip_address_and_encoded_domain_are_detected(self):
        ip_result = analyze_url("https://192.0.2.1/login")
        idn_result = analyze_url("https://xn--e1afmkfd.example")

        self.assertIn(
            "ip_address_host",
            {item["signal"] for item in ip_result["warning_signals"]}
        )
        self.assertIn(
            "internationalized_domain",
            {item["signal"] for item in idn_result["warning_signals"]}
        )

    def test_lookalike_and_government_style_domains_only_get_caution(self):
        lookalike = analyze_url("https://gooogle-login.example")
        government_style = analyze_url("https://gov-benefit.example")

        self.assertIn(
            "lookalike_brand_term",
            {item["category"] for item in lookalike["risk_categories"]}
        )
        self.assertIn(
            "authority_word_in_hostname",
            {item["category"] for item in government_style["risk_categories"]}
        )
        self.assertIn(
            "not verified",
            government_style["warning_signals"][0]["explanation"]
        )

    def test_unusual_port_and_url_characters_fail_safely(self):
        result = analyze_url("https://example.com:99999")

        self.assertFalse(result["valid_syntax"])
        self.assertTrue(result["risk_categories"])


class UploadValidationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.analysis = {
            "claims": [],
            "warning_signals": [],
            "verification_steps": [],
            "verification_links": [],
            "disclaimer": "Claims need independent verification."
        }

    def _png(self):
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def test_valid_screenshot_runs_ocr_and_reports_urls_from_ocr(self):
        with (
            patch.object(app.pytesseract, "image_to_string", return_value="Check https://example.com"),
            patch.object(app, "extract_claims", return_value=self.analysis) as model
        ):
            response = self.client.post(
                "/analyse",
                data={"image": (self._png(), "notice.png", "image/png")},
                content_type="multipart/form-data"
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["source_type"], "image")
        self.assertEqual(body["detected_urls"], ["https://example.com"])
        model.assert_called_once_with("Check https://example.com", language="en")

    def test_unreadable_screenshot_returns_a_clear_error(self):
        with patch.object(app.pytesseract, "image_to_string", return_value=" \n"):
            response = self.client.post(
                "/analyse",
                data={"image": (self._png(), "notice.png", "image/png")},
                content_type="multipart/form-data"
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("clearer screenshot", response.get_json()["error"])

    def test_corrupted_and_unsupported_uploads_are_rejected(self):
        corrupted = self.client.post(
            "/analyse",
            data={"image": (io.BytesIO(b"not an image"), "bad.png", "image/png")},
            content_type="multipart/form-data"
        )
        unsupported = self.client.post(
            "/analyse",
            data={"image": (io.BytesIO(b"anything"), "notes.txt", "text/plain")},
            content_type="multipart/form-data"
        )

        self.assertEqual(corrupted.status_code, 400)
        self.assertEqual(unsupported.status_code, 400)
        self.assertIn("not a valid image", corrupted.get_json()["error"])
        self.assertIn("Unsupported image type", unsupported.get_json()["error"])

    def test_mismatched_mime_type_is_rejected(self):
        response = self.client.post(
            "/analyse",
            data={"image": (self._png(), "notice.png", "image/jpeg")},
            content_type="multipart/form-data"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("does not match", response.get_json()["error"])

    def test_extracted_text_is_editable_in_the_interface(self):
        response = self.client.get("/")

        self.assertIn(b'<textarea id="extracted-text"', response.data)
        self.assertIn(b'id="analyse-corrected-button"', response.data)
        self.assertNotIn(b'id="extracted-text"></textarea>', response.data)


if __name__ == "__main__":
    unittest.main()
