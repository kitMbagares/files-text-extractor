"""
extractors/pdf.py — PDF extraction functions.

Handles three types of data extraction from PDFs:
  1. Text   — selectable text via pdfplumber
  2. Tables — structured tabular data via pdfplumber
  3. Images — embedded images via PyMuPDF (fitz), returned as base64

Also provides page count and a "smart" extractor that auto-falls back to OCR.
"""

import io
import base64
from fastapi import HTTPException
import pdfplumber
import fitz

from config import logger


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract selectable text from all pages of a PDF.

    Uses pdfplumber which works well for PDFs with embedded text.
    Returns empty string for PDFs with no selectable text (scanned docs).
    Raises 422 if the file is not a valid PDF.
    """
    try:
        with io.BytesIO(file_bytes) as pdf_file:
            with pdfplumber.open(pdf_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
        return text
    except Exception as e:
        logger.exception("Error extracting text from PDF")
        raise HTTPException(status_code=422, detail=f"Failed to read PDF: {e}")


def extract_tables_from_pdf(file_bytes: bytes) -> list:
    """
    Extract all tables from a PDF, organized by page.

    Returns a list of table objects:
    [
        {"page": 1, "table_index": 0, "rows": [["cell", "cell"], ...]},
        ...
    ]

    Empty cells are normalized to empty strings.
    Raises 422 if the file is not a valid PDF.
    """
    try:
        tables = []
        with io.BytesIO(file_bytes) as pdf_file:
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    for table_idx, table in enumerate(page_tables):
                        # Replace None cells with empty strings for clean output
                        cleaned = []
                        for row in table:
                            cleaned.append([cell if cell else "" for cell in row])
                        tables.append({
                            "page": page_num,
                            "table_index": table_idx,
                            "rows": cleaned,
                        })
        return tables
    except Exception as e:
        logger.exception("Error extracting tables from PDF")
        raise HTTPException(status_code=422, detail=f"Failed to extract tables from PDF: {e}")


def extract_images_from_pdf(file_bytes: bytes, max_images: int = 20) -> list:
    """
    Extract embedded images from a PDF using PyMuPDF.

    Each image is returned as a dict with base64-encoded data:
    {
        "page": 1,
        "index": 0,
        "format": "png",
        "width": 800,
        "height": 600,
        "data_base64": "iVBORw0KGgo..."
    }

    Capped at max_images (default 20) to prevent huge responses.
    Raises 422 if the file is not a valid PDF.
    """
    try:
        images = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page_num in range(len(doc)):
            if len(images) >= max_images:
                break

            page = doc[page_num]
            image_list = page.get_images(full=True)

            for img_idx, img_info in enumerate(image_list):
                if len(images) >= max_images:
                    break

                # xref is the PDF internal reference ID for the image
                xref = img_info[0]
                base_image = doc.extract_image(xref)

                if base_image:
                    img_b64 = base64.b64encode(base_image["image"]).decode("utf-8")
                    images.append({
                        "page": page_num + 1,
                        "index": img_idx,
                        "format": base_image["ext"],
                        "width": base_image.get("width", 0),
                        "height": base_image.get("height", 0),
                        "data_base64": img_b64,
                    })

        doc.close()
        return images
    except Exception as e:
        logger.exception("Error extracting images from PDF")
        raise HTTPException(status_code=422, detail=f"Failed to extract images from PDF: {e}")


def get_pdf_page_count(file_bytes: bytes) -> int:
    """Return the number of pages in a PDF. Returns 0 if the file is invalid."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def smart_extract_pdf_text(file_bytes: bytes) -> tuple:
    """
    Smart text extraction: tries pdfplumber first, falls back to OCR.

    This handles the common case where a PDF looks like it has text
    but is actually a scanned image (< 10 chars of selectable text).

    Returns: (text: str, used_ocr: bool)

    If OCR is unavailable, returns whatever pdfplumber found.
    """
    # Import here to avoid circular dependency (ocr imports fitz too)
    from extractors.ocr import ocr_pdf

    text = extract_text_from_pdf(file_bytes)
    used_ocr = False

    # If pdfplumber got very little text, try OCR as fallback
    if not text or len(text.strip()) < 10:
        try:
            ocr_text = ocr_pdf(file_bytes)
            # Only use OCR result if it's better than what we had
            if ocr_text and len(ocr_text.strip()) > len((text or "").strip()):
                text = ocr_text
                used_ocr = True
        except HTTPException:
            pass  # OCR unavailable — return whatever pdfplumber got

    return text, used_ocr
