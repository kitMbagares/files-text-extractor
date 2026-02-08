"""
validators.py — Request validation helpers.

Contains FastAPI dependencies and utility functions for validating
authentication tokens, file types, file sizes, and extraction modes.
All validation errors raise HTTPException with descriptive messages.
"""

from fastapi import Header, HTTPException
from config import API_KEY, MAX_FILE_SIZE, EXTENSION_MAP, VALID_MODES_PER_TYPE


# ── Authentication ──────────────────────────────────────────────────
# Used as a FastAPI Depends() dependency on protected endpoints.
# Expects: Authorization: Bearer <token>

def verify_token(authorization: str = Header(None)):
    """Validate Bearer token against the configured API_KEY."""
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "server_misconfigured",
                "message": "Server misconfigured: API_KEY not set.",
            },
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "missing_token",
                "message": "Missing or invalid Authorization header. Expected: Bearer <token>",
            },
        )

    token = authorization.replace("Bearer ", "", 1)
    if token != API_KEY:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "invalid_token",
                "message": "The provided API key is incorrect. Please check your token and try again.",
            },
        )


# ── File type detection ─────────────────────────────────────────────

def detect_file_type(filename: str) -> str:
    """
    Determine file type from the filename extension.

    Returns one of: "pdf", "image", "docx", "xlsx", "csv"
    Raises 400 if extension is missing or unsupported.
    """
    if not filename or "." not in filename:
        raise HTTPException(
            status_code=400,
            detail="Cannot determine file type. Include a file extension.",
        )

    ext = filename.rsplit(".", 1)[-1].lower()
    file_type = EXTENSION_MAP.get(ext)

    if not file_type:
        supported = ", ".join("." + k for k in EXTENSION_MAP)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Supported: {supported}",
        )

    return file_type


# ── File size validation ────────────────────────────────────────────

def validate_file_size(content: bytes, filename: str):
    """
    Reject empty files (400) and files exceeding MAX_FILE_SIZE (413).
    """
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file '{filename}' is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        limit_mb = MAX_FILE_SIZE / (1024 * 1024)
        size_mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB. Maximum allowed: {limit_mb:.0f}MB.",
        )


# ── Mode + file type compatibility ──────────────────────────────────

def validate_mode_for_type(mode: str, file_type: str):
    """
    Ensure the requested extraction mode is valid for the given file type.

    For example, mode="images" only works on PDFs — not on DOCX or XLSX.
    Raises 400 with a list of valid modes if incompatible.
    """
    valid = VALID_MODES_PER_TYPE.get(file_type, {"text"})

    if mode not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Mode '{mode}' is not supported for {file_type} files. Valid modes: {', '.join(sorted(valid))}",
        )
