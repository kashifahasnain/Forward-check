import unittest

from modules.risk_assessor import calculate_risk


class RiskAssessorTests(unittest.TestCase):
    def test_ordinary_message_has_low_caution(self):
        result = calculate_risk("The library will close at 5 PM today.")

        self.assertEqual(result["level"], "Low Caution")
        self.assertEqual(result["score"], 0)
        self.assertTrue(result["reasons"])

    def test_urgent_forward_is_medium_caution(self):
        message = "URGENT! Share this with at least 10 friends before midnight."

        result = calculate_risk(message)

        self.assertEqual(result["level"], "Medium Caution")
        self.assertEqual(result["score"], 4)
        self.assertEqual(
            {reason["category"] for reason in result["reasons"]},
            {"urgency", "mass_forwarding"}
        )

    def test_suspicious_url_structure_adds_caution(self):
        result = calculate_risk(
            "Please view this notice.",
            detected_urls=["https://user@192.0.2.10/login"]
        )

        self.assertEqual(result["level"], "Medium Caution")
        self.assertEqual(result["score"], 3)
        self.assertIn(
            "suspicious_url_structure",
            {reason["category"] for reason in result["reasons"]}
        )

    def test_password_or_otp_request_is_high_caution(self):
        result = calculate_risk("Reply with your OTP to verify your account.")

        self.assertEqual(result["level"], "High Caution")
        self.assertEqual(result["score"], 5)

    def test_http_alone_is_not_high_caution(self):
        result = calculate_risk(
            "Read the notice.",
            detected_urls=["http://example.org/notice"]
        )

        self.assertEqual(result["level"], "Low Caution")
        self.assertEqual(result["score"], 1)

    def test_unknown_domain_extension_or_https_url_alone_is_not_flagged(self):
        result = calculate_risk(
            "This is a neutral note.",
            detected_urls=["https://example.unfamiliar-tld/"]
        )

        self.assertEqual(result["level"], "Low Caution")
        self.assertEqual(result["score"], 0)

    def test_unattributed_benefit_is_medium_caution(self):
        result = calculate_risk("Claim your free money benefit today.")

        self.assertEqual(result["level"], "Medium Caution")
        self.assertEqual(result["score"], 2)

    def test_duplicate_signal_sections_only_score_category_once(self):
        message = "URGENT! Share this with 10 friends."
        signals = [
            {"signal": "Urgency"},
            {"signal": "Urgency", "evidence": ["URGENT"]},
            {"signal": "Forwarding request"},
            {"signal": "Forwarding request", "evidence": ["Share this"]}
        ]

        result = calculate_risk(message, signals, [])

        self.assertEqual(result["score"], 4)
        self.assertEqual(
            [reason["category"] for reason in result["reasons"]],
            ["urgency", "mass_forwarding"]
        )

    def test_empty_fields_and_malformed_urls_do_not_crash(self):
        result = calculate_risk(
            None,
            warning_signals=None,
            detected_urls=["http://[malformed"]
        )

        self.assertEqual(result["level"], "Medium Caution")
        self.assertEqual(result["score"], 4)

    def test_negated_credential_advice_is_not_scored_as_a_request(self):
        result = calculate_risk("Never share your OTP or password with anyone.")

        self.assertEqual(result["level"], "Low Caution")
        self.assertEqual(result["score"], 0)

    def test_deadline_cancellation_threat_adds_urgency(self):
        result = calculate_risk(
            "Enter your details within 24 hours or your payment will be cancelled."
        )

        self.assertIn(
            "urgency",
            {reason["category"] for reason in result["reasons"]}
        )

    def test_aadhaar_and_bank_detail_request_is_sensitive_information_warning(self):
        result = calculate_risk(
            "Claim your payment and enter your Aadhaar number and bank details."
        )

        self.assertIn(
            "credential_request",
            {reason["category"] for reason in result["reasons"]}
        )

    def test_harmless_aadhaar_or_bank_mention_is_not_a_request(self):
        result = calculate_risk(
            "This educational article explains Aadhaar and bank details."
        )

        self.assertNotIn(
            "credential_request",
            {reason["category"] for reason in result["reasons"]}
        )


if __name__ == "__main__":
    unittest.main()
