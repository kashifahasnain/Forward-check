from flask import Flask, render_template, request, jsonify
from PIL import Image, UnidentifiedImageError
import pytesseract
import os
from io import BytesIO
from werkzeug.exceptions import HTTPException
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(name)s: %(message)s"
)
from modules.analysis_pipeline import analyze_message, find_urls
from modules.claim_extractor import detect_message_language, extract_claims

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
MAX_MESSAGE_LENGTH = 10000
MAX_UPLOAD_SIZE = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}
SUPPORTED_LANGUAGES = {"en", "hi", "hinglish"}
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
HINDI_OCR_MISSING = {
    "en": "Hindi screenshot text needs Tesseract Hindi data (hin.traineddata). Install it or paste the text instead.",
    "hi": "हिंदी स्क्रीनशॉट पढ़ने के लिए Tesseract का हिंदी डेटा (hin.traineddata) इंस्टॉल करें या पाठ यहाँ पेस्ट करें।",
    "hinglish": "Hindi screenshot text padhne ke liye Tesseract ka Hindi data (hin.traineddata) install karein ya text paste karein."
}


@app.after_request
def allow_chrome_extension_requests(response):
    """Allow the unpacked extension to call Flask without opening the API broadly."""
    origin = request.headers.get("Origin", "")
    if origin.startswith("chrome-extension://"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


@app.route("/")
def home():
    return render_template("index.html")


def find_message_urls(message_text):
    """Compatibility wrapper for URL extraction; URLs are never opened."""
    return find_urls(message_text)


def build_analysis_response(
    message_text,
    language="en",
    source_type="text",
    source_search_enabled=False
):
    if language == "en":
        detected_language = detect_message_language(message_text)
        if detected_language == "hinglish":
            language = detected_language
    result = analyze_message(
        message_text,
        language=language,
        source_type=source_type,
        claim_analyzer=extract_claims,
        source_search_enabled=source_search_enabled
    )
    if not isinstance(result, dict):
        raise RuntimeError("Analysis pipeline returned an invalid response.")

    analysis = result.get("analysis")
    if (
        not isinstance(result.get("extracted_text"), str)
        or not isinstance(result.get("analysis_scope"), str)
        or result.get("source_type") not in {"text", "image"}
        or not isinstance(result.get("detected_urls"), list)
        or not isinstance(result.get("url_analysis"), list)
        or not isinstance(analysis, dict)
        or any(
            not isinstance(analysis.get(field), list)
            for field in (
                "claims",
                "warning_signals",
                "verification_steps",
                "verification_links"
            )
        )
        or not isinstance(analysis.get("caution_explanation"), str)
        or not isinstance(analysis.get("risk_assessment"), dict)
        or not isinstance(analysis.get("evidence_status"), dict)
        or not isinstance(analysis["evidence_status"].get("status"), str)
        or not isinstance(analysis["evidence_status"].get("message"), str)
    ):
        raise RuntimeError("Analysis pipeline returned an incomplete response.")

    return jsonify({"language": language, **result})


def extract_image_text(image_bytes, language="en"):
    """Decode a Telegram or web image and run the existing OCR pipeline."""
    if not isinstance(image_bytes, (bytes, bytearray)):
        raise ValueError("Image data is invalid.")
    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise ValueError(
            f"Upload is too large. Keep the image under "
            f"{MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
        )

    image = Image.open(BytesIO(image_bytes))
    if image.format not in ALLOWED_IMAGE_FORMATS:
        raise ValueError("Unsupported image type.")
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise ValueError("The image dimensions are too large.")
    image.load()

    ocr_language = "eng"
    has_hindi_ocr = True
    if language in {"hi", "auto"}:
        has_hindi_ocr = "hin" in pytesseract.get_languages(config="")
        if has_hindi_ocr:
            ocr_language = "eng+hin"
    extracted_text = pytesseract.image_to_string(image, lang=ocr_language)
    if not extracted_text.strip():
        if language == "hi" and not has_hindi_ocr:
            raise ValueError(HINDI_OCR_MISSING[language])
        raise ValueError("No readable text found. Try a clearer screenshot.")
    return extracted_text


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({
        "error": f"Upload is too large. Keep the image under {MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
    }), 413


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        if request.path == "/analyse":
            return jsonify({"error": error.description}), error.code
        return error

    app.logger.exception("Unhandled error while processing the request")
    return jsonify({
        "error": "An unexpected server error occurred. Check the Flask terminal logs."
    }), 500


@app.route("/analyse", methods=["POST"])
def analyse():
    uploaded_file = request.files.get("image")
    message_text = request.form.get("message")
    language = request.form.get("language", "en")
    source_type = request.form.get("source_type", "text")
    source_search_enabled = request.form.get("source_search_enabled") == "true"

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": "Unsupported language selection."}), 400
    if source_type not in {"text", "image"}:
        return jsonify({"error": "Unsupported input type."}), 400

    if message_text is not None:
        if uploaded_file and uploaded_file.filename:
            return jsonify({
                "error": "Submit either pasted message text or a screenshot, not both."
            }), 400

        if not message_text.strip():
            return jsonify({"error": "Please paste a message to analyse."}), 400

        if len(message_text) > MAX_MESSAGE_LENGTH:
            return jsonify({
                "error": (
                    f"Message text is too long. Please keep it under "
                    f"{MAX_MESSAGE_LENGTH} characters."
                )
            }), 413

        return build_analysis_response(
            message_text,
            language,
            source_type,
            source_search_enabled
        )

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            "error": "Please upload a screenshot or paste message text."
        }), 400

    try:
        extension = os.path.splitext(uploaded_file.filename)[1].casefold()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            return jsonify({
                "error": "Unsupported image type. Upload a PNG, JPG, JPEG, or WEBP image."
            }), 400
        expected_mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp"
        }
        if uploaded_file.mimetype != expected_mime_types[extension]:
            return jsonify({
                "error": "The uploaded file type does not match its filename."
            }), 400

        extracted_text = extract_image_text(
            uploaded_file.stream.read(),
            language=language
        )

        return build_analysis_response(
            extracted_text,
            language,
            "image",
            source_search_enabled
        )

    except pytesseract.TesseractNotFoundError:
        return jsonify({
            "error": "Tesseract was not found. Check its installation path."
        }), 500

    except pytesseract.TesseractError:
        return jsonify({
            "error": "OCR failed. Check Tesseract installation and try again."
        }), 500

    except ValueError as error:
        status_code = 413 if "too large" in str(error).casefold() else 400
        return jsonify({"error": str(error)}), status_code

    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        return jsonify({
            "error": "The uploaded file is not a valid image."
        }), 400


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")