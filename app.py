"""
app.py — FastAPI application entry point.

This is the main router. All business logic lives in separate modules:
  - config.py           : Settings, env vars, constants
  - validators.py       : Auth, file type, size, mode validation
  - extractors/pdf.py   : PDF text, tables, images
  - extractors/ocr.py   : OCR for images and scanned PDFs
  - extractors/docx_ext.py : Word document extraction
  - extractors/spreadsheet.py : Excel and CSV extraction
  - text_utils.py       : Grammar correction and table flattening

API Endpoints:
  GET  /         — Health check (status, version, capabilities)
  POST /upload/  — Upload a file and extract content
"""

import time
from fastapi import FastAPI, File, UploadFile, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
import uvicorn

# ── Configuration ───────────────────────────────────────────────────
from config import (
    HOST,
    PORT,
    ALLOWED_ORIGINS,
    OCR_PROVIDER,
    TESSERACT_AVAILABLE,
    EXTENSION_MAP,
    logger,
)

# ── Validation ──────────────────────────────────────────────────────
from validators import (
    verify_token,
    detect_file_type,
    validate_file_size,
    validate_mode_for_type,
)

# ── Extractors ──────────────────────────────────────────────────────
from extractors.pdf import (
    extract_text_from_pdf,
    extract_tables_from_pdf,
    extract_images_from_pdf,
    get_pdf_page_count,
    smart_extract_pdf_text,
)
from extractors.ocr import ocr_image, ocr_pdf
from extractors.docx_ext import extract_text_from_docx
from extractors.spreadsheet import extract_data_from_xlsx, extract_data_from_csv

# ── Text processing ─────────────────────────────────────────────────
from text_utils import flatten_table_to_text, correct_text


# ═══════════════════════════════════════════════════════════════════
#  App setup
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(title="Extract-Kit", version="2.0.0")

# Allow cross-origin requests from configured frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
#  Global error handler
# ═══════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch any unhandled exception and return a clean JSON 500 response."""
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "An unexpected error occurred. Please try again.",
        },
    )


# ═══════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def health_check():
    """
    Health check endpoint.

    Returns server status, version, OCR availability,
    and the list of supported file types.
    """
    return {
        "status": "ok",
        "version": "2.0.0",
        "ocr_available": TESSERACT_AVAILABLE and OCR_PROVIDER != "none",
        "supported_types": list(set(EXTENSION_MAP.values())),
    }


@app.post("/upload")
@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    mode: str = Query("text", regex="^(text|tables|images|ocr|full)$"),
    correct: bool = Query(True),
    _auth: None = Depends(verify_token),
):
    """
    Upload a file and extract content from it.

    Query params:
      - mode:    "text" | "tables" | "images" | "ocr" | "full" (PDF only)
      - correct: true/false — apply grammar/spelling correction

    Supported file types: PDF, PNG, JPG, DOCX, XLSX, CSV

    Response includes: filename, file_type, mode, extracted_text,
    corrected_text, tables, images, and metadata.
    """
    start_time = time.time()
    content = await file.read()

    # ── Step 1: Validate the upload ─────────────────────────────────
    validate_file_size(content, file.filename)
    file_type = detect_file_type(file.filename)
    validate_mode_for_type(mode, file_type)

    # ── Step 2: Build the response envelope ─────────────────────────
    result = {
        "filename": file.filename,
        "file_type": file_type,
        "mode": mode,
        "extracted_text": None,
        "corrected_text": None,
        "tables": None,
        "images": None,
        "metadata": {},
    }

    # ── Step 3: Route to the correct extractor ──────────────────────

    if file_type == "pdf":
        result["metadata"]["pages"] = get_pdf_page_count(content)

        # Text extraction (with auto-OCR fallback for scanned PDFs)
        if mode in ("text", "full"):
            text, used_ocr = smart_extract_pdf_text(content)
            result["extracted_text"] = text
            result["metadata"]["used_ocr"] = used_ocr
            if correct and text and text.strip():
                result["corrected_text"] = correct_text(text)

        # Table extraction
        if mode in ("tables", "full"):
            result["tables"] = extract_tables_from_pdf(content)

        # Image extraction
        if mode in ("images", "full"):
            result["images"] = extract_images_from_pdf(content)

        # Forced OCR mode (ignores selectable text, always uses Tesseract)
        if mode == "ocr":
            text = ocr_pdf(content)
            result["extracted_text"] = text
            if correct and text and text.strip():
                result["corrected_text"] = correct_text(text)

    elif file_type == "image":
        # Image files are always processed via OCR
        text = ocr_image(content)
        result["extracted_text"] = text
        if correct and text and text.strip():
            result["corrected_text"] = correct_text(text)

    elif file_type == "docx":
        # Word documents — extract paragraph text
        text = extract_text_from_docx(content)
        result["extracted_text"] = text
        if correct and text and text.strip():
            result["corrected_text"] = correct_text(text)

    elif file_type in ("xlsx", "csv"):
        # Spreadsheets — extract as structured table data
        if file_type == "xlsx":
            data = extract_data_from_xlsx(content)
        else:
            data = extract_data_from_csv(content)
        result["tables"] = data
        result["extracted_text"] = flatten_table_to_text(data)

    # ── Step 4: Add timing metadata ─────────────────────────────────
    elapsed = round(time.time() - start_time, 3)
    result["metadata"]["processing_seconds"] = elapsed

    return result


# ═══════════════════════════════════════════════════════════════════
#  Local development server
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="error", access_log=False)
