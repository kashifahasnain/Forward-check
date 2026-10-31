"""Telegram long-polling adapter for Forward Check analysis."""

import asyncio
import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from app import extract_image_text
from modules.analysis_pipeline import analyze_message
from modules.claim_extractor import detect_message_language, extract_claims

logger = logging.getLogger(__name__)
TELEGRAM_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
MAX_TELEGRAM_TEXT = 10000
MAX_REPLY_LENGTH = 4000
SUPPORTED_LANGUAGES = {"en", "hi", "hinglish"}


def _configure_logging():
    """Keep HTTP client request URLs, including Telegram tokens, out of logs."""
    for logger_name in ("httpx", "httpcore"):
        logging.getLogger(logger_name).setLevel(logging.CRITICAL + 1)


def _language_for_text(text):
    language = detect_message_language(text)
    return language if language in SUPPORTED_LANGUAGES else "en"


def analyze_for_telegram(text):
    """Run the shared analysis pipeline without enabling external search."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Please send some text to analyse.")
    if len(text) > MAX_TELEGRAM_TEXT:
        raise ValueError(
            f"Message is too long. Keep it under {MAX_TELEGRAM_TEXT} characters."
        )
    language = _language_for_text(text)
    return analyze_message(
        text,
        language=language,
        source_type="text",
        claim_analyzer=extract_claims,
        source_search_enabled=False
    )


def _provider_model(analysis):
    provider = analysis.get("ai_provider")
    model = analysis.get("ai_model")
    provenance = analysis.get("gemma_provenance")
    if isinstance(provenance, dict):
        provider = provider or provenance.get("provider")
        model = model or provenance.get("model")
    return str(provider or "local rules"), str(model or "local rules")


def format_analysis_reply(result):
    """Create a bounded, citation-safe Telegram response from API data."""
    analysis = result.get("analysis", {}) if isinstance(result, dict) else {}
    claims = analysis.get("claims", []) if isinstance(analysis, dict) else []
    provider, model = _provider_model(analysis)
    lines = [
        "Forward Check",
        f"AI provider/model: {provider} / {model}",
        ""
    ]
    valid_claims = [item for item in claims if isinstance(item, dict)]
    if not valid_claims:
        lines.append("No factual claim was extracted.")
    for index, claim in enumerate(valid_claims[:3], start=1):
        wording = claim.get("claim")
        if not isinstance(wording, str) or not wording.strip():
            continue
        lines.extend([f"Claim {index}: {wording.strip()}"])
        assessment = claim.get("ai_assessment")
        explanation = claim.get("ai_explanation")
        limitations = claim.get("ai_limitations")
        if isinstance(assessment, str) and assessment.strip():
            lines.append(f"Gemma 4 AI assessment: {assessment.strip()}")
        if isinstance(explanation, str) and explanation.strip():
            lines.append(f"Explanation: {explanation.strip()}")
        if isinstance(limitations, str) and limitations.strip():
            lines.append(f"AI limitations: {limitations.strip()}")
        verdict = claim.get("verdict")
        if isinstance(verdict, str) and verdict.strip():
            lines.append(f"Evidence verdict: {verdict.strip()}")
        sources = claim.get("sources")
        if isinstance(sources, list):
            for source in sources[:3]:
                if not isinstance(source, dict):
                    continue
                title = source.get("title")
                url = source.get("url")
                if isinstance(title, str) and isinstance(url, str):
                    lines.append(f"Source lead (not proof): {title} - {url}")
        lines.append("")

    evidence = analysis.get("evidence_status", {})
    if isinstance(evidence, dict):
        message = evidence.get("message")
        if isinstance(message, str) and message.strip():
            lines.extend(["Evidence status:", message.strip()])
    return "\n".join(lines).strip()


def _reply_chunks(text):
    text = text.strip()
    return [
        text[index:index + MAX_REPLY_LENGTH]
        for index in range(0, len(text), MAX_REPLY_LENGTH)
    ] or ["No analysis result was available."]


async def _send_reply(update, text):
    if not update.message:
        return
    for chunk in _reply_chunks(text):
        await update.message.reply_text(chunk)


async def start_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await _send_reply(
        update,
        "Forward Check is ready. Send a claim or screenshot to analyse it."
    )


async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await _send_reply(
        update,
        "Send a text claim or screenshot. The bot returns the AI assessment, "
        "provider/model, and separate evidence-verification status. "
        "Evidence remains Unverified when live source search is unavailable."
    )


async def text_message(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    try:
        result = await asyncio.to_thread(analyze_for_telegram, update.message.text)
        await _send_reply(update, format_analysis_reply(result))
    except ValueError as error:
        await _send_reply(update, str(error))
    except Exception:
        logger.exception("Telegram text analysis failed.")
        await _send_reply(update, "Analysis failed. Please try again later.")


async def photo_message(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return
    try:
        photo = update.message.photo[-1]
        telegram_file = await photo.get_file()
        image_bytes = bytes(await telegram_file.download_as_bytearray())
        text = await asyncio.to_thread(extract_image_text, image_bytes, "auto")
        result = await asyncio.to_thread(analyze_for_telegram, text)
        await _send_reply(update, format_analysis_reply(result))
    except ValueError as error:
        await _send_reply(update, str(error))
    except Exception:
        logger.exception("Telegram photo analysis failed.")
        await _send_reply(update, "Screenshot analysis failed. Please try again.")


def create_application(token):
    if not isinstance(token, str) or not token.strip():
        raise ValueError(f"{TELEGRAM_TOKEN_ENV} is not configured.")
    application = Application.builder().token(token.strip()).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, photo_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    return application


def main():
    token = os.environ.get(TELEGRAM_TOKEN_ENV, "").strip()
    if not token:
        raise SystemExit(
            f"Set {TELEGRAM_TOKEN_ENV} in the terminal before starting the bot."
        )
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")
    _configure_logging()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        create_application(token).run_polling()
    finally:
        if not loop.is_closed():
            loop.close()
        asyncio.set_event_loop(None)


if __name__ == "__main__":
    main()
