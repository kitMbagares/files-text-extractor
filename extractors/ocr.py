"""
extractors/ocr.py — Optical Character Recognition (OCR).

Provides OCR for:
  - Standalone image files (PNG, JPG, etc.)
  - Scanned PDFs (renders each page to image, then OCR)

Requires:
  - pytesseract Python package
  - Tesseract binary installed on the system
    macOS:  brew install tesseract
    Linux:  apt-get install tesseract-ocr

OCR can be disabled via OCR_PROVIDER=none in .env (used on Vercel
where the Tesseract binary is not available).
"""

import io
from fastapi import HTTPException
import fitz
from PIL import Image

from config import OCR_PROVIDER, TESSERACT_AVAILABLE, logger

# pytesseract is optional — only needed if OCR is enabled
try:
    import pytesseract
except ImportError:
    pytesseract = None


def _check_ocr_available():
    """
    Pre-flight check before any OCR operation.

    Raises 501 (Not Implemented) if OCR is disabled or Tesseract is missing.
    This gives callers a clear, actionable error message.
    """
    if OCR_PROVIDER == "none":
        raise HTTPException(
            status_code=501,
            detail="OCR is disabled in this deployment. Set OCR_PROVIDER=local and install Tesseract.",
        )
    if pytesseract is None:
        raise HTTPException(
            status_code=501,
            detail="pytesseract package is not installed.",
        )
    if not TESSERACT_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Tesseract binary not found. Install: brew install tesseract (macOS) or apt-get install tesseract-ocr (Linux).",
        )


def ocr_image(file_bytes: bytes) -> str:
    """
    Run OCR on a standalone image file (PNG, JPG, TIFF, etc.).

    Returns extracted text, or empty string if no text was found.
    Raises 501 if OCR is unavailable, 422 if the image is unreadable.
    """
    _check_ocr_available()
    try:
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        if not text or not text.strip():
            return ""
        return text
    except Exception as e:
        logger.exception("Error performing OCR on image")
        raise HTTPException(status_code=422, detail=f"OCR failed on image: {e}")


def ocr_pdf(file_bytes: bytes) -> str:
    """
    Run OCR on a scanned PDF by rendering each page to a 300 DPI image.

    This is slower than text extraction but works on PDFs where the
    content is embedded as images rather than selectable text.

    Returns concatenated text from all pages.
    Raises 501 if OCR is unavailable, 422 if the PDF is unreadable.
    """
    _check_ocr_available()
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            # Render page to a high-resolution image for better OCR accuracy
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += pytesseract.image_to_string(img) + "\n"
        doc.close()
        return text.strip()
    except Exception as e:
        logger.exception("Error performing OCR on PDF")
        raise HTTPException(status_code=422, detail=f"OCR failed on PDF: {e}")
