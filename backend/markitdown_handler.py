"""
MarkItDown conversion handler for the backend protocol.

Converts files (from base64-encoded content) and URLs to Markdown
using the MarkItDown library.
"""

import base64
import logging
import os
import re
import secrets
import tempfile
import time

logger = logging.getLogger(__name__)

# Lazy-load MarkItDown to avoid import errors if not installed
_md_instance = None


def _get_markitdown():
    """Lazy-initialize the MarkItDown instance."""
    global _md_instance
    if _md_instance is None:
        try:
            from markitdown import MarkItDown
            _md_instance = MarkItDown(enable_plugins=False)
            logger.info("MarkItDown initialized successfully")
        except ImportError:
            raise RuntimeError(
                "MarkItDown library is not installed. "
                "Run: pip install 'markitdown[all]'"
            )
    return _md_instance


SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
    ".html", ".htm",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff",
    ".mp3", ".wav",
    ".epub", ".msg", ".ipynb", ".zip",
    ".csv", ".json", ".xml",
    ".txt", ".md", ".rst",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def convert_file(filename, file_data_b64):
    """Convert a file (provided as base64) to Markdown.

    Args:
        filename: Original filename (used for extension detection).
        file_data_b64: Base64-encoded file content.

    Returns:
        dict with keys: markdown, filename (output .md name)
    """
    md = _get_markitdown()

    # Validate extension
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    if ext_lower not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # Decode file content
    try:
        file_bytes = base64.b64decode(file_data_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 file data: {e}")

    # Validate size
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError("File size exceeds the 50 MB limit")

    if len(file_bytes) == 0:
        raise ValueError("File is empty")

    # Write to a temp file for conversion, preserving original extension
    temp_dir = tempfile.gettempdir()
    safe_name = secrets.token_hex(16) + ext_lower
    temp_path = os.path.join(temp_dir, safe_name)

    try:
        with open(temp_path, "wb") as f:
            f.write(file_bytes)

        start = time.time()
        result = md.convert(temp_path)
        duration = time.time() - start
        logger.info(f"File conversion completed in {duration:.2f}s: {filename} ({len(file_bytes)} bytes)")

        markdown = _extract_markdown(result)

        # Generate output filename
        base = os.path.splitext(filename)[0]
        output_name = _sanitize_filename(base) + ".md"

        return {
            "markdown": markdown,
            "filename": output_name,
        }
    finally:
        # Clean up temp file
        try:
            os.remove(temp_path)
        except OSError:
            pass


def convert_url(url):
    """Convert a URL to Markdown.

    Args:
        url: The URL to convert.

    Returns:
        dict with keys: markdown, filename (output .md name)
    """
    md = _get_markitdown()

    # Basic URL validation
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS URLs are supported")
    if not parsed.hostname:
        raise ValueError("URL must contain a valid hostname")

    start = time.time()
    result = md.convert(url)
    duration = time.time() - start
    logger.info(f"URL conversion completed in {duration:.2f}s: {url}")

    markdown = _extract_markdown(result)

    # Generate output filename from URL
    base = parsed.netloc + parsed.path.rstrip("/")
    base = base.replace("/", "_")
    output_name = _sanitize_filename(base) + ".md"

    return {
        "markdown": markdown,
        "filename": output_name,
    }


def _extract_markdown(result):
    """Safely extract markdown text from a MarkItDown conversion result.

    The library returns a DocumentConverterResult with a text_content attribute.
    """
    if result is None:
        return ""
    if hasattr(result, "text_content") and result.text_content:
        return result.text_content
    # Fallback: some older versions might use different attributes
    if hasattr(result, "markdown") and result.markdown:
        return result.markdown
    return ""


def _sanitize_filename(name, max_length=200):
    """Replace non-safe characters with underscore, truncate."""
    sanitized = re.sub(r"[^a-zA-Z0-9._\-]", "_", name)
    return sanitized[:max_length]
