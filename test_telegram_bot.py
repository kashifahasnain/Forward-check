import asyncio
import unittest
from unittest.mock import Mock, patch

import telegram_bot


class TelegramBotTests(unittest.TestCase):
    def test_analysis_uses_shared_pipeline_and_disables_source_search(self):
        with patch.object(
            telegram_bot,
            "analyze_message",
            return_value={"analysis": {}}
        ) as analyze:
            telegram_bot.analyze_for_telegram("Students will receive laptops.")

        analyze.assert_called_once()
        self.assertFalse(analyze.call_args.kwargs["source_search_enabled"])
        self.assertEqual(analyze.call_args.kwargs["source_type"], "text")

    def test_report_contains_ai_assessment_provider_and_evidence_status(self):
        result = {
            "analysis": {
                "ai_provider": "gemini",
                "ai_model": "gemma-4-26b-a4b-it",
                "claims": [{
                    "claim": "Eating ice cream causes the common cold.",
                    "ai_assessment": "Likely false",
                    "ai_explanation": "Colds are caused by viruses.",
                    "ai_limitations": "AI assessment, not independent verification.",
                    "verdict": "Unverified",
                    "sources": []
                }],
                "evidence_status": {
                    "status": "not_enabled",
                    "message": "Live source search is off."
                }
            }
        }

        report = telegram_bot.format_analysis_reply(result)

        self.assertIn("gemma-4-26b-a4b-it", report)
        self.assertIn("Likely false", report)
        self.assertIn("Evidence verdict: Unverified", report)
        self.assertIn("Live source search is off.", report)

    def test_report_labels_ollama_fallback_without_calling_it_gemma_4(self):
        result = {
            "analysis": {
                "ai_provider": "ollama",
                "ai_model": "gemma3:4b",
                "claims": [{
                    "claim": "A claim.",
                    "verdict": "Unverified",
                    "sources": []
                }],
                "evidence_status": {"message": "Unverified."}
            }
        }

        report = telegram_bot.format_analysis_reply(result)

        self.assertIn("ollama / gemma3:4b", report)
        self.assertNotIn("gemma-4-26b-a4b-it", report)

    def test_text_length_is_bounded(self):
        with self.assertRaises(ValueError):
            telegram_bot.analyze_for_telegram(
                "x" * (telegram_bot.MAX_TELEGRAM_TEXT + 1)
            )

    def test_application_requires_token_without_logging_it(self):
        with self.assertRaises(ValueError):
            telegram_bot.create_application("")

    def test_reply_chunks_respect_telegram_limit(self):
        chunks = telegram_bot._reply_chunks("x" * (telegram_bot.MAX_REPLY_LENGTH + 1))

        self.assertEqual([len(chunk) for chunk in chunks], [4000, 1])

    def test_main_initializes_and_closes_event_loop(self):
        loop = Mock()
        loop.is_closed.return_value = False
        application = Mock()
        with patch.dict(
            telegram_bot.os.environ,
            {telegram_bot.TELEGRAM_TOKEN_ENV: "test-token"},
            clear=False
        ), patch.object(
            telegram_bot.asyncio,
            "new_event_loop",
            return_value=loop
        ) as new_event_loop, patch.object(
            telegram_bot.asyncio,
            "set_event_loop"
        ) as set_event_loop, patch.object(
            telegram_bot,
            "create_application",
            return_value=application
        ) as create_application:
            telegram_bot.main()

        new_event_loop.assert_called_once_with()
        set_event_loop.assert_any_call(loop)
        set_event_loop.assert_any_call(None)
        loop.close.assert_called_once_with()
        create_application.assert_called_once_with("test-token")
        application.run_polling.assert_called_once_with()

    def test_http_client_logging_is_suppressed(self):
        logger_names = ("httpx", "httpcore")
        previous_levels = {
            name: telegram_bot.logging.getLogger(name).level
            for name in logger_names
        }
        try:
            telegram_bot._configure_logging()
            for name in logger_names:
                self.assertGreater(
                    telegram_bot.logging.getLogger(name).level,
                    telegram_bot.logging.CRITICAL
                )
        finally:
            for name, level in previous_levels.items():
                telegram_bot.logging.getLogger(name).setLevel(level)


if __name__ == "__main__":
    unittest.main()
