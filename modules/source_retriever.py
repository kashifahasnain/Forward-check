import http.client
import ipaddress
import logging
import queue
import re
import socket
import ssl
import threading
import time
import unicodedata
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


MAX_SOURCE_BYTES = 1_000_000
MAX_SOURCE_TEXT_CHARS = 15_000
MAX_REDIRECTS = 3
TOTAL_TIMEOUT_SECONDS = 15
CONNECT_TIMEOUT_SECONDS = 4
READ_TIMEOUT_SECONDS = 5
MAX_PASSAGE_LENGTH = 600

_BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".test",
    ".invalid"
)
_DISCARD_TAGS = {
    "script", "style", "noscript", "nav", "header", "footer", "aside",
    "form", "button", "svg", "iframe", "template", "canvas"
}
_BLOCK_TAGS = {
    "article", "br", "dd", "div", "dl", "dt", "figcaption", "h1", "h2",
    "h3", "h4", "h5", "h6", "li", "main", "ol", "p", "section", "table",
    "td", "th", "tr", "ul"
}
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "before", "being",
    "but", "by", "can", "could", "did", "do", "does", "for", "from",
    "had", "has", "have", "he", "her", "him", "his", "i", "in", "into",
    "is", "it", "its", "may", "might", "must", "not", "of", "on", "or",
    "our", "she", "should", "than", "that", "the", "their", "them",
    "there", "these", "they", "this", "those", "to", "was", "we", "were",
    "will", "with", "would", "you", "your", "कि", "का", "की", "के", "को",
    "में", "और", "है", "हैं", "था", "थी", "थे", "यह", "इस", "से", "पर"
}
_QUALIFIER_TERMS = {
    "only", "limited", "eligible", "eligibility", "some", "may", "might",
    "reportedly", "allegedly", "except", "unless", "however", "although",
    "केवल", "सिर्फ", "कुछ", "पात्र", "हालांकि"
}
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?।])\s+|\n+")
_TOKEN_PATTERN = re.compile(
    r"\d+(?:[.,]\d+)*|(?:[^\W_]|[\u0900-\u097f])+",
    re.UNICODE
)
_DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TOKEN_NORMALIZATION = {
    "viral": "virus",
    "viruses": "virus"
}
_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3,
    "mar": 3, "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6,
    "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9,
    "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11,
    "nov": 11, "december": 12, "dec": 12, "जनवरी": 1, "फरवरी": 2,
    "मार्च": 3, "अप्रैल": 4, "मई": 5, "जून": 6, "जुलाई": 7,
    "अगस्त": 8, "सितंबर": 9, "सितम्बर": 9, "अक्टूबर": 10,
    "नवंबर": 11, "नवम्बर": 11, "दिसंबर": 12, "दिसम्बर": 12
}
_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90
}
_ORDINAL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17,
    "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
    "twentyfirst": 21, "twentysecond": 22, "twentythird": 23,
    "twentyfourth": 24, "twentyfifth": 25, "twentysixth": 26,
    "twentyseventh": 27, "twentyeighth": 28, "twentyninth": 29,
    "thirtieth": 30, "thirtyfirst": 31
}
_DATE_TOKEN_PATTERN = re.compile(
    r"(?:[^\W_]|[\u0900-\u097f])+(?:-(?:[^\W_]|[\u0900-\u097f])+)*",
    re.UNICODE
)

logger = logging.getLogger(__name__)


class SourceRetrievalError(Exception):
    def __init__(self, status, limitation):
        super().__init__(limitation)
        self.status = status
        self.limitation = limitation


class _PageTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.metadata = {}
        self.title_parts = []
        self.heading_parts = []
        self._discard_depth = 0
        self._discard_stack = []
        self._in_title = False
        self._in_heading = False

    def handle_starttag(self, tag, attrs):
        attributes = {key.casefold(): value or "" for key, value in attrs}
        if self._discard_depth:
            self._discard_depth += 1
            self._discard_stack.append(tag)
            return
        if tag in _DISCARD_TAGS:
            self._discard_depth = 1
            self._discard_stack = [tag]
            return

        if tag == "meta":
            key = (
                attributes.get("property")
                or attributes.get("name")
                or attributes.get("itemprop")
                or ""
            ).casefold()
            content = attributes.get("content", "").strip()
            if key and content and key not in self.metadata:
                self.metadata[key] = content
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_heading = True

        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self._discard_depth:
            for index in range(len(self._discard_stack) - 1, -1, -1):
                if self._discard_stack[index] == tag:
                    del self._discard_stack[index:]
                    break
            self._discard_depth = len(self._discard_stack)
            return
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_heading = False
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._discard_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        self.parts.append(text)
        if self._in_title:
            self.title_parts.append(text)
        if self._in_heading:
            self.heading_parts.append(text)


def _is_public_ip(value):
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped.is_global
    return (
        address.is_global
        and not address.is_private
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_multicast
        and not address.is_reserved
        and not address.is_unspecified
    )


def _canonical_host(hostname):
    if not isinstance(hostname, str) or not hostname.strip():
        raise SourceRetrievalError("blocked_destination", "The source host is invalid or blocked.")
    if "%" in hostname:
        raise SourceRetrievalError("blocked_destination", "Scoped or encoded hostnames are not allowed.")
    try:
        canonical = hostname.rstrip(".").encode("idna").decode("ascii").casefold()
    except UnicodeError as error:
        raise SourceRetrievalError("blocked_destination", "The source host is invalid or blocked.") from error
    if (
        not canonical
        or len(canonical) > 253
        or any(not label or len(label) > 63 for label in canonical.split("."))
        or canonical == "localhost"
        or canonical.endswith(_BLOCKED_HOST_SUFFIXES)
    ):
        raise SourceRetrievalError("blocked_destination", "The source host is invalid or blocked.")
    return canonical


def _validate_source_url(url):
    if not isinstance(url, str) or not url or len(url) > 2048:
        raise SourceRetrievalError("invalid_url", "The source URL is invalid.")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise SourceRetrievalError("invalid_url", "The source URL is invalid.") from error
    if parsed.scheme.casefold() not in {"http", "https"}:
        raise SourceRetrievalError("unsupported_scheme", "Only HTTP and HTTPS sources can be retrieved.")
    if parsed.username is not None or parsed.password is not None:
        raise SourceRetrievalError("invalid_url", "URLs containing credentials are not allowed.")
    hostname = _canonical_host(parsed.hostname or "")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not _is_public_ip(hostname):
            raise SourceRetrievalError("blocked_destination", "The source destination is not publicly routable.")
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"
    return parsed, hostname, port or (443 if parsed.scheme.casefold() == "https" else 80), path


def _resolve_host(hostname, port, timeout):
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        return [hostname]

    result_queue = queue.Queue(maxsize=1)

    def resolve():
        try:
            result_queue.put(socket.getaddrinfo(
                hostname,
                port,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM
            ))
        except Exception as error:
            result_queue.put(error)

    threading.Thread(target=resolve, daemon=True).start()
    try:
        resolved = result_queue.get(timeout=max(0.01, timeout))
    except queue.Empty as error:
        raise SourceRetrievalError("timeout", "The source host could not be resolved in time.") from error
    if isinstance(resolved, Exception):
        raise SourceRetrievalError("retrieval_failed", "The source host could not be resolved.")

    addresses = []
    for family, _socktype, _protocol, _canonname, sockaddr in resolved:
        if family not in (socket.AF_INET, socket.AF_INET6):
            raise SourceRetrievalError("blocked_destination", "The source host resolved to a blocked destination.")
        address = sockaddr[0].split("%", 1)[0]
        if not _is_public_ip(address):
            raise SourceRetrievalError("blocked_destination", "The source host resolved to a blocked destination.")
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise SourceRetrievalError("retrieval_failed", "The source host did not resolve to a usable address.")
    return addresses


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, port, address, timeout, tls_context=None):
        super().__init__(host=host, port=port, timeout=timeout)
        self._pinned_address = address
        self._tls_context = tls_context

    def connect(self):
        address = ipaddress.ip_address(self._pinned_address)
        family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        target = (
            (self._pinned_address, self.port, 0, 0)
            if family == socket.AF_INET6
            else (self._pinned_address, self.port)
        )
        try:
            sock.connect(target)
            if self._tls_context is not None:
                sock = self._tls_context.wrap_socket(
                    sock,
                    server_hostname=self.host
                )
            self.sock = sock
        except Exception:
            sock.close()
            raise


class SafeSourceRetriever:
    """Fetch bounded text from public search-result hosts with validated redirects."""

    provider_name = "constrained HTTP(S) retrieval"

    def __init__(
        self,
        resolver=_resolve_host,
        total_timeout=TOTAL_TIMEOUT_SECONDS,
        max_bytes=MAX_SOURCE_BYTES,
        max_text_chars=MAX_SOURCE_TEXT_CHARS,
        max_redirects=MAX_REDIRECTS,
        connection_factory=_PinnedHTTPConnection
    ):
        self.resolver = resolver
        self.total_timeout = total_timeout
        self.max_bytes = max_bytes
        self.max_text_chars = max_text_chars
        self.max_redirects = max_redirects
        self.connection_factory = connection_factory
        self.tls_context = ssl.create_default_context()

    def fetch(self, url, deadline=None):
        own_deadline = time.monotonic() + self.total_timeout
        deadline = min(own_deadline, deadline) if deadline is not None else own_deadline
        current_url = url
        visited = set()
        try:
            for redirect_count in range(self.max_redirects + 1):
                parsed, hostname, port, path = _validate_source_url(current_url)
                normalized_url = parsed._replace(fragment="").geturl()
                if normalized_url in visited:
                    raise SourceRetrievalError("redirect_loop", "The source redirected repeatedly.")
                visited.add(normalized_url)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SourceRetrievalError("timeout", "The source retrieval time limit was reached.")
                addresses = self.resolver(hostname, port, remaining)
                if (
                    not isinstance(addresses, list)
                    or not addresses
                    or any(
                        not isinstance(address, str) or not _is_public_ip(address)
                        for address in addresses
                    )
                ):
                    raise SourceRetrievalError(
                        "blocked_destination",
                        "The source host resolved to a blocked destination."
                    )
                if time.monotonic() >= deadline:
                    raise SourceRetrievalError("timeout", "The source retrieval time limit was reached.")
                address = addresses[0]
                result = self._request_once(
                    parsed,
                    hostname,
                    port,
                    path,
                    address,
                    deadline
                )
                if result["status_code"] in {301, 302, 303, 307, 308}:
                    location = result["location"]
                    if not location or redirect_count >= self.max_redirects:
                        raise SourceRetrievalError(
                            "too_many_redirects",
                            "The source exceeded the allowed redirect limit."
                        )
                    current_url = urljoin(normalized_url, location)
                    continue
                return self._parse_response(
                    result["headers"],
                    result["body"],
                    parsed.scheme,
                    result.get("partial_content", False)
                )
        except SourceRetrievalError as error:
            return self._failure(error.status, error.limitation)
        except (ssl.SSLError, ssl.CertificateError):
            return self._failure("tls_error", "A secure connection to the source could not be established.")
        except (socket.timeout, TimeoutError):
            return self._failure("timeout", "The source did not respond within the time limit.")
        except (OSError, http.client.HTTPException, UnicodeError, ValueError):
            logger.warning("Constrained source retrieval failed.")
            return self._failure("retrieval_failed", "The source response could not be retrieved safely.")
        return self._failure("too_many_redirects", "The source exceeded the allowed redirect limit.")

    def _request_once(self, parsed, hostname, port, path, address, deadline):
        remaining = max(0.01, min(CONNECT_TIMEOUT_SECONDS, deadline - time.monotonic()))
        connection_class = self.connection_factory
        tls_context = None
        if parsed.scheme.casefold() == "https":
            tls_context = self.tls_context
        host_header = f"[{hostname}]" if ":" in hostname else hostname
        if port != (443 if parsed.scheme.casefold() == "https" else 80):
            host_header = f"{host_header}:{port}"
        connection = connection_class(
            hostname,
            port,
            address,
            remaining,
            tls_context=tls_context
        )
        try:
            connection.request(
                "GET",
                path,
                headers={
                    "Host": host_header,
                    "User-Agent": "ForwardCheck-SourceReview/1.0",
                    "Accept": "text/html, application/xhtml+xml, text/plain;q=0.9",
                    "Accept-Encoding": "identity",
                    "Connection": "close"
                }
            )
            response = connection.getresponse()
            content_encoding = str(
                response.getheader("Content-Encoding", "identity") or "identity"
            ).casefold()
            if content_encoding not in {"", "identity"}:
                raise SourceRetrievalError(
                    "unsupported_content_encoding",
                    "Compressed or encoded source responses are not supported."
                )
            content_length = response.getheader("Content-Length")
            if content_length:
                try:
                    if int(content_length) > self.max_bytes:
                        raise SourceRetrievalError(
                            "too_large",
                            "The source response exceeds the allowed size."
                        )
                except ValueError:
                    raise SourceRetrievalError(
                        "invalid_response",
                        "The source response has invalid size metadata."
                    )

            if response.status in {301, 302, 303, 307, 308}:
                return {
                    "status_code": response.status,
                    "location": response.getheader("Location", ""),
                    "headers": dict(response.getheaders()),
                    "body": b""
                }
            if response.status < 200 or response.status >= 300:
                raise SourceRetrievalError(
                    "http_error",
                    "The source returned an unsuccessful HTTP response."
                )

            body = bytearray()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SourceRetrievalError(
                        "timeout",
                        "The source retrieval time limit was reached."
                    )
                if connection.sock:
                    connection.sock.settimeout(
                        max(0.01, min(READ_TIMEOUT_SECONDS, remaining))
                    )
                chunk = response.read(min(64 * 1024, self.max_bytes + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > self.max_bytes:
                    raise SourceRetrievalError(
                        "too_large",
                        "The source response exceeds the allowed size."
                    )
            return {
                "status_code": response.status,
                "headers": dict(response.getheaders()),
                "body": bytes(body),
                "partial_content": response.status == 206
            }
        finally:
            connection.close()

    def _parse_response(self, headers, body, scheme, response_partial=False):
        content_type = _header_value(headers, "Content-Type").split(";", 1)[0].strip().casefold()
        if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
            raise SourceRetrievalError(
                "unsupported_content_type",
                "Only HTML and plain-text source pages are supported."
            )
        charset = "utf-8"
        content_type_header = _header_value(headers, "Content-Type")
        charset_match = re.search(r"charset\s*=\s*[\"']?([\w.-]+)", content_type_header, re.IGNORECASE)
        if charset_match:
            charset = charset_match.group(1)
        try:
            decoded = body.decode(charset, errors="replace")
        except LookupError:
            decoded = body.decode("utf-8", errors="replace")

        title = ""
        publication_date = ""
        source_type = "Plain-text webpage" if content_type == "text/plain" else "HTML webpage"
        if content_type in {"text/html", "application/xhtml+xml"}:
            parser = _PageTextParser()
            try:
                parser.feed(decoded)
                parser.close()
            except Exception:
                logger.debug("Source HTML parser rejected malformed markup.")
            title = " ".join(parser.title_parts).strip()
            if not title:
                title = " ".join(parser.heading_parts).strip()
            decoded = "\n".join(parser.parts)
            for key in (
                "article:published_time",
                "datepublished",
                "date",
                "pubdate",
                "dc.date",
                "dcterms.date",
                "datecreated"
            ):
                if key in parser.metadata:
                    publication_date = _parse_publication_date(parser.metadata[key])
                    if publication_date:
                        break

        text = _normalize_page_text(decoded)
        if not text:
            raise SourceRetrievalError(
                "empty_content",
                "The source page did not contain readable text."
            )
        partial = response_partial or len(text) > self.max_text_chars
        text = text[:self.max_text_chars]
        return {
            "retrieval_status": "retrieved",
            "retrieved_text": text,
            "retrieved_title": title[:300],
            "publication_date": publication_date,
            "content_type": content_type,
            "source_type": source_type,
            "partial_content": partial,
            "limitations": (
                (
                    "Only partial source text was retrieved due to the configured "
                    "content limit or a partial HTTP response."
                )
                if partial
                else (
                    "The source was retrieved over unencrypted HTTP; its content may have been modified in transit."
                    if scheme.casefold() == "http"
                    else "Only readable page text was retrieved; embedded files and linked pages were not fetched."
                )
            )
        }

    @staticmethod
    def _failure(status, limitation):
        return {
            "retrieval_status": status,
            "retrieved_text": "",
            "retrieved_title": "",
            "publication_date": "",
            "content_type": "",
            "source_type": "",
            "partial_content": False,
            "limitations": limitation
        }


def _header_value(headers, name):
    for key, value in headers.items():
        if str(key).casefold() == name.casefold():
            return str(value)
    return ""


def _parse_publication_date(value):
    candidate = value.strip()
    if not candidate:
        return ""
    try:
        return date.fromisoformat(candidate[:10]).isoformat()
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(candidate)
        return parsed.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return ""


def _normalize_page_text(text):
    lines = []
    for line in text.splitlines():
        normalized = " ".join(line.split()).strip()
        if normalized:
            lines.append(normalized)
    return "\n".join(lines)


def _claim_terms(text):
    terms = set()
    for token in _TOKEN_PATTERN.findall(text):
        normalized = _ascii_digits(token.casefold())
        if (
            len(normalized) >= 3
            and normalized not in _STOP_WORDS
            and not normalized.startswith("http")
        ):
            terms.add(_TOKEN_NORMALIZATION.get(normalized, normalized))
    return terms


def _ascii_digits(text):
    return "".join(
        str(unicodedata.digit(character))
        if character.isdigit() and unicodedata.digit(character, None) is not None
        else character
        for character in text
    )


def _number_words_value(words):
    total = 0
    current = 0
    found_number = False
    for word in words:
        if word == "and":
            continue
        value = _NUMBER_WORDS.get(word)
        if value is not None:
            current += value
            found_number = True
        elif word == "hundred":
            current = max(1, current) * 100
            found_number = True
        elif word == "thousand":
            total += max(1, current) * 1000
            current = 0
            found_number = True
        else:
            return None
    return total + current if found_number else None


def _has_year_context(text, position):
    prefix = text[max(0, position - 50):position]
    return bool(re.search(
        r"\b(?:year|date|dates|in|during|from|since|dated|on)\b[^.!?]{0,45}$|"
        r"(?:वर्ष|साल|दिनांक|तारीख|में|को)[^।.!?]{0,45}$",
        prefix,
        re.IGNORECASE
    ))


def _date_components(text):
    normalized_text = _ascii_digits(text.casefold())
    tokens = [
        token.casefold()
        for token in _DATE_TOKEN_PATTERN.findall(normalized_text)
    ]
    month_days = set()

    def day_value(token):
        token = token.casefold()
        if token in _ORDINAL_WORDS:
            return _ORDINAL_WORDS[token]
        numeric = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", token)
        if numeric:
            value = int(numeric.group(1))
            return value if 1 <= value <= 31 else None
        return None

    month_positions = [
        (index, _MONTHS[token])
        for index, token in enumerate(tokens)
        if token in _MONTHS
    ]
    for index, month in month_positions:
        nearby_tokens = tokens[max(0, index - 4):index] + tokens[index + 1:index + 3]
        for token in nearby_tokens:
            day = day_value(token)
            if day is not None:
                month_days.add(f"{month:02d}-{day:02d}")
                break

    years = set()
    for match in re.finditer(r"(?<!\d)(1\d{3}|2\d{3})(?!\d)", normalized_text):
        if month_positions or _has_year_context(normalized_text, match.start()):
            years.add(int(match.group(1)))

    word_tokens = []
    for match in _DATE_TOKEN_PATTERN.finditer(normalized_text):
        for token in match.group(0).casefold().split("-"):
            word_tokens.append((token, match.start()))
    number_words = set(_NUMBER_WORDS) | {"and", "hundred", "thousand"}
    for start, (word, position) in enumerate(word_tokens):
        if word not in _NUMBER_WORDS:
            continue
        sequence = []
        for token, _token_position in word_tokens[start:start + 9]:
            if token not in number_words:
                break
            sequence.append(token)
        value = _number_words_value(sequence)
        if (
            value is not None
            and 1000 <= value <= 2999
            and (month_positions or _has_year_context(normalized_text, position))
        ):
            years.add(value)

        first = _NUMBER_WORDS[word]
        if first is not None and 10 <= first <= 19:
            second_words = []
            for token, _token_position in word_tokens[start + 1:start + 4]:
                if token not in _NUMBER_WORDS:
                    break
                second_words.append(token)
            second = _number_words_value(second_words)
            if (
                second is not None
                and 0 <= second <= 99
                and (month_positions or _has_year_context(normalized_text, position))
            ):
                year = first * 100 + second
                if 1000 <= year <= 2999:
                    years.add(year)

    for match in _DATE_PATTERN.finditer(normalized_text):
        try:
            parsed = date.fromisoformat(match.group(0))
        except ValueError:
            continue
        years.add(parsed.year)
        month_days.add(f"{parsed.month:02d}-{parsed.day:02d}")

    return {"years": years, "month_days": month_days}


def _dates_conflict(claim_text, passage):
    claim_dates = _date_components(claim_text)
    passage_dates = _date_components(passage)
    for key in ("years", "month_days"):
        claim_values = claim_dates[key]
        passage_values = passage_dates[key]
        if (
            len(claim_values) == 1
            and len(passage_values) == 1
            and claim_values.isdisjoint(passage_values)
        ):
            return True
    return False


def _date_coverage_incomplete(claim_text, passage):
    claim_dates = _date_components(claim_text)
    passage_dates = _date_components(passage)
    for key in ("years", "month_days"):
        claim_values = claim_dates[key]
        if len(claim_values) > 1:
            return True
        if claim_values and (
            len(passage_dates[key]) != 1
            or claim_values != passage_dates[key]
        ):
            return True
    return False


def _is_negated(text):
    return bool(
        re.search(
            r"\b(?:not|no|never|neither|without|does not|do not|did not|"
            r"is not|are not|was not|were not|has not|have not|cannot|"
            r"can't|won't|nahi|nahin)\b|नहीं|नही|मत",
            text,
            re.IGNORECASE
        )
    )


def _assessment(status, explanation, passages, retrieval, claim, language):
    return {
        "status": status,
        "explanation": explanation,
        "passages": passages,
        "claim": claim,
        "publication_date": retrieval.get("publication_date", ""),
        "source_type": retrieval.get("source_type", ""),
        "retrieval_status": retrieval.get("retrieval_status", ""),
        "partial_content": bool(retrieval.get("partial_content")),
        "limitations": retrieval.get("limitations", "")
    }


_ASSESSMENT_MESSAGES = {
    "en": {
        "retrieval_failed": "The source could not be retrieved; this is not evidence for or against the claim.",
        "insufficient": "The retrieved content does not provide enough relevant information to assess this claim.",
        "not_address": "The retrieved content does not address this claim.",
        "supports": "This passage contains wording consistent with the claim; it is not a final verification.",
        "contradicts": "This passage contains wording that conflicts with the claim; it is not a final verification.",
        "context": "This passage is related to the claim but adds context or qualifications rather than resolving it."
    },
    "hi": {
        "retrieval_failed": "स्रोत प्राप्त नहीं हो सका; यह दावा सही या गलत होने का प्रमाण नहीं है।",
        "insufficient": "प्राप्त सामग्री में इस दावे का आकलन करने के लिए पर्याप्त संबंधित जानकारी नहीं है।",
        "not_address": "प्राप्त सामग्री इस दावे पर बात नहीं करती।",
        "supports": "इस अंश की भाषा दावे से मेल खाती है; यह अंतिम पुष्टि नहीं है।",
        "contradicts": "इस अंश की भाषा दावे से टकराती है; यह अंतिम पुष्टि नहीं है।",
        "context": "यह अंश दावे से संबंधित है, लेकिन उसे तय करने के बजाय संदर्भ या शर्तें जोड़ता है।"
    },
    "hinglish": {
        "retrieval_failed": "Source retrieve nahi ho saka; yeh claim ke support ya contradiction ka evidence nahi hai.",
        "insufficient": "Retrieved content mein claim assess karne ke liye kaafi relevant information nahi hai.",
        "not_address": "Retrieved content is claim ko address nahi karta.",
        "supports": "Yeh passage claim se milti-julti baat kehta hai; yeh final verification nahi hai.",
        "contradicts": "Yeh passage claim se takrati baat kehta hai; yeh final verification nahi hai.",
        "context": "Yeh passage claim se related context ya qualification deta hai, lekin claim ko resolve nahi karta."
    }
}


def assess_claim_against_source(claim, retrieval, language="en"):
    """Compare a claim with retrieved text using traceable lexical rules only."""
    messages = _ASSESSMENT_MESSAGES.get(language, _ASSESSMENT_MESSAGES["en"])
    claim_text = claim.get("claim", "") if isinstance(claim, dict) else ""
    if not isinstance(claim_text, str):
        claim_text = ""
    retrieval_status = retrieval.get("retrieval_status", "retrieval_failed")
    text = retrieval.get("retrieved_text", "")

    if retrieval_status == "not_attempted_limit":
        return _assessment(
            "Insufficient Information",
            messages["insufficient"],
            [],
            retrieval,
            claim_text,
            language
        )
    if retrieval_status != "retrieved":
        return _assessment(
            "Retrieval Failed",
            messages["retrieval_failed"],
            [],
            retrieval,
            claim_text,
            language
        )
    if not isinstance(text, str) or len(text.strip()) < 20:
        return _assessment(
            "Insufficient Information",
            messages["insufficient"],
            [],
            retrieval,
            claim_text,
            language
        )

    claim_terms = _claim_terms(claim_text)
    if not claim_terms:
        return _assessment(
            "Insufficient Information",
            messages["insufficient"],
            [],
            retrieval,
            claim_text,
            language
        )

    candidates = []
    for passage in _SENTENCE_BOUNDARY.split(text):
        passage = " ".join(passage.split()).strip()
        if not passage:
            continue
        passage_terms = _claim_terms(passage)
        shared = claim_terms & passage_terms
        number_terms = {term for term in claim_terms if term.isdigit()}
        text_shared = shared - number_terms
        score = len(shared) / max(1, len(claim_terms))
        if (
            len(text_shared) >= 2
            or (len(text_shared) >= 1 and bool(shared & number_terms))
            or score >= 0.55
        ):
            candidates.append((score, len(shared), passage, shared))

    if not candidates:
        status = "Does Not Address" if len(text.split()) >= 20 else "Insufficient Information"
        explanation = messages["not_address"] if status == "Does Not Address" else messages["insufficient"]
        return _assessment(status, explanation, [], retrieval, claim_text, language)

    _score, _overlap, passage, shared_terms = max(
        candidates,
        key=lambda item: (item[0], item[1], -len(item[2]))
    )
    passage_numbers = {
        value for value in re.findall(
            r"\d+(?:[.,]\d+)*",
            _ascii_digits(passage)
        )
    }
    claim_numbers = {
        value for value in re.findall(
            r"\d+(?:[.,]\d+)*",
            _ascii_digits(claim_text)
        )
    }
    numerical_conflict = bool(
        claim_numbers
        and passage_numbers
        and claim_numbers.isdisjoint(passage_numbers)
        and len(shared_terms - claim_numbers) >= 2
    )
    date_conflict = (
        len(shared_terms - claim_numbers) >= 2
        and _dates_conflict(claim_text, passage)
    )
    date_incomplete = _date_coverage_incomplete(claim_text, passage)
    polarity_conflict = (
        _is_negated(claim_text) != _is_negated(passage)
        and len(shared_terms) >= 3
    )
    if numerical_conflict or date_conflict or polarity_conflict:
        status = "Contradicts"
        key = "contradicts"
    elif date_incomplete:
        status = "Contextualizes"
        key = "context"
    elif _claim_terms(passage) & _QUALIFIER_TERMS:
        status = "Contextualizes"
        key = "context"
    elif len(shared_terms) >= max(2, int(len(claim_terms) * 0.4)):
        status = "Supports"
        key = "supports"
    else:
        status = "Contextualizes"
        key = "context"

    grounded_passage = passage[:MAX_PASSAGE_LENGTH]
    return _assessment(
        status,
        messages[key],
        [grounded_passage],
        retrieval,
        claim_text,
        language
    )
