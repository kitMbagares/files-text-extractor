"""
extractors/web.py — URL fetch + visible text extraction helpers.

Downloads public web pages and extracts readable text content.
Intended for job postings and similar HTML pages.
"""

from html.parser import HTMLParser
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from config import logger


class _VisibleTextParser(HTMLParser):
    """Collect visible text while skipping script/style-like blocks."""

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._text_chunks = []
        self._in_title = False
        self._title_chunks = []

    def handle_starttag(self, tag, attrs):
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "template"}:
            self._skip_depth += 1
        if lowered == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "template"} and self._skip_depth > 0:
            self._skip_depth -= 1
        if lowered == "title":
            self._in_title = False

    def handle_data(self, data):
        if not data:
            return

        normalized = " ".join(data.split())
        if not normalized:
            return

        if self._in_title:
            self._title_chunks.append(normalized)
        if self._skip_depth == 0:
            self._text_chunks.append(normalized)

    @property
    def text(self):
        return "\n".join(self._text_chunks).strip()

    @property
    def title(self):
        return " ".join(self._title_chunks).strip() or None


def _decode_bytes(raw: bytes, content_type: str) -> str:
    """Decode network bytes to text using header charset when present."""
    charset = None
    if "charset=" in content_type.lower():
        charset = content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip()

    for encoding in [charset, "utf-8", "latin-1"]:
        if not encoding:
            continue
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    return raw.decode("utf-8", errors="ignore")


def extract_text_from_url(url: str, timeout_seconds: int = 15, max_bytes: int = 5 * 1024 * 1024):
    """
    Fetch and extract text from a URL.

    Returns:
      {
        "text": "...",
        "title": "...",
        "content_type": "text/html; charset=utf-8"
      }
    """
    request = Request(
        url,
        headers={
            "User-Agent": "Extract-Kit/2.0 (+https://extract-kit.local)",
            "Accept": "text/html,text/plain;q=0.9,*/*;q=0.8",
        },
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not fetch URL. Remote server responded with HTTP {exc.code}.",
        ) from exc
    except URLError as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not fetch URL. The server may be unreachable or blocked.",
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=408,
            detail="URL fetch timed out. Try again or use a different source.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected URL fetch failure")
        raise HTTPException(
            status_code=422,
            detail="Failed to fetch URL content.",
        ) from exc

    if status_code >= 400:
        raise HTTPException(
            status_code=422,
            detail=f"Could not fetch URL. Remote server responded with HTTP {status_code}.",
        )

    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Remote content too large. Maximum supported size is {max_bytes // (1024 * 1024)}MB.",
        )

    decoded = _decode_bytes(raw, content_type)
    lowered_type = content_type.lower()

    if "html" in lowered_type or "<html" in decoded.lower():
        parser = _VisibleTextParser()
        parser.feed(decoded)
        extracted = parser.text
        title = parser.title
    else:
        extracted = re.sub(r"\s+", " ", decoded).strip()
        title = None

    if not extracted:
        raise HTTPException(
            status_code=422,
            detail="The URL was fetched but no readable text could be extracted.",
        )

    return {
        "text": extracted,
        "title": title,
        "content_type": content_type or "unknown",
    }
