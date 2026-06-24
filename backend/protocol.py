"""
stdin/stdout JSON message loop.

Process entry point. Handles all communication and request routing.
- Reads one JSON line per iteration from stdin
- Routes requests to analyzer.py based on 'action' field
- Writes JSON responses to stdout (flushed after each write)
- Logs to stderr only (stdout reserved for protocol)
- Emits ready signal on startup
- Handles shutdown gracefully
"""

import io
import json
import logging
import os
import signal
import sys
import time
import traceback

# Ensure stdin/stdout use UTF-8 encoding
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Configure logging to stderr only
log_level = logging.DEBUG if os.environ.get("BACKEND_DEBUG") else logging.INFO
logging.basicConfig(
    stream=sys.stderr,
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Import analyzer (same directory)
sys.path.insert(0, ".")
import analyzer
import markitdown_handler
import review_engine


# =============================================================================
# RESPONSE HELPERS
# =============================================================================

def send_response(response):
    """Write JSON response to stdout, terminated by newline, then flush."""
    line = json.dumps(response, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def success_response(request_id, data):
    """Build and send a success response."""
    send_response({
        "id": request_id,
        "success": True,
        "data": data,
    })


def error_response(request_id, code, message, details=""):
    """Build and send an error response."""
    send_response({
        "id": request_id,
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    })


# =============================================================================
# REQUEST HANDLERS
# =============================================================================

def handle_analyze(request_id, payload):
    """Handle content analysis request."""
    logger.debug(f"[DEBUG] Action 'analyze' received: id={request_id}, text_len={len(payload.get('text', ''))}")
    text = payload.get("text", "")
    if not text:
        error_response(request_id, "INVALID_REQUEST", "Missing 'text' in payload")
        return
    start_time = time.time()
    result = analyzer.analyze(text)
    duration = int((time.time() - start_time) * 1000)
    logger.info(f"Handler completed: id={request_id}, action=analyze, duration={duration}ms")
    success_response(request_id, result)


def handle_rewrite(request_id, payload):
    """Handle rewrite request."""
    logger.debug(f"[DEBUG] Action 'rewrite' received: id={request_id}, text_len={len(payload.get('text', ''))}")
    text = payload.get("text", "")
    if not text:
        error_response(request_id, "INVALID_REQUEST", "Missing 'text' in payload")
        return
    start_time = time.time()
    result = analyzer.rewrite(text)
    duration = int((time.time() - start_time) * 1000)
    logger.info(f"Handler completed: id={request_id}, action=rewrite, duration={duration}ms")
    success_response(request_id, result)


def handle_convert_dita(request_id, payload):
    """Handle DITA conversion request."""
    logger.debug(f"[DEBUG] Action 'convert_dita' received: id={request_id}, format={payload.get('format', 'concept')}")
    text = payload.get("text", "")
    fmt = payload.get("format", "concept")
    if not text:
        error_response(request_id, "INVALID_REQUEST", "Missing 'text' in payload")
        return
    start_time = time.time()
    result = analyzer.convert_dita(text, fmt)
    duration = int((time.time() - start_time) * 1000)
    logger.info(f"Handler completed: id={request_id}, action=convert_dita, duration={duration}ms")
    success_response(request_id, result)


def handle_impact_analyze(request_id, payload):
    """Handle impact analysis request."""
    logger.debug(f"[DEBUG] Action 'impact_analyze' received: id={request_id}, jira_count={len(payload.get('jiraItems', []))}, topic_count={len(payload.get('ditaTopics', []))}")
    jira_items = payload.get("jiraItems", [])
    dita_topics = payload.get("ditaTopics", [])
    threshold = payload.get("threshold", 0.18)
    if not jira_items:
        error_response(request_id, "INVALID_REQUEST", "Missing 'jiraItems' in payload")
        return
    if not dita_topics:
        error_response(request_id, "INVALID_REQUEST", "Missing 'ditaTopics' in payload")
        return
    start_time = time.time()
    result = analyzer.impact_analyze(jira_items, dita_topics, threshold)
    duration = int((time.time() - start_time) * 1000)
    logger.info(f"Handler completed: id={request_id}, action=impact_analyze, duration={duration}ms")
    success_response(request_id, result)


def handle_markitdown(request_id, payload):
    """Handle MarkItDown conversion request.

    Supports two modes:
    - File conversion: payload has 'filename' and 'fileData' (base64)
    - URL conversion: payload has 'url'
    """
    mode = payload.get("mode", "file")
    logger.debug(f"[DEBUG] Action 'markitdown' received: id={request_id}, mode={mode}")

    start_time = time.time()
    try:
        if mode == "url":
            url = payload.get("url", "")
            if not url:
                error_response(request_id, "INVALID_REQUEST", "Missing 'url' in payload")
                return
            result = markitdown_handler.convert_url(url)
        else:
            filename = payload.get("filename", "")
            file_data = payload.get("fileData", "")
            if not filename or not file_data:
                error_response(request_id, "INVALID_REQUEST",
                               "Missing 'filename' or 'fileData' in payload")
                return
            result = markitdown_handler.convert_file(filename, file_data)

        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=markitdown, mode={mode}, duration={duration}ms")
        success_response(request_id, result)

    except ValueError as e:
        error_response(request_id, "VALIDATION_ERROR", str(e))
    except RuntimeError as e:
        error_response(request_id, "RUNTIME_ERROR", str(e))
    except Exception as e:
        logger.error(f"MarkItDown error: id={request_id}, msg={str(e)}")
        error_response(request_id, "CONVERSION_ERROR",
                       f"Conversion failed: {str(e)}")


def handle_quick_review(request_id, payload):
    """Handle quick documentation review request."""
    text = payload.get("text", "")
    logger.debug(f"[DEBUG] Action 'quick_review' received: id={request_id}, text_len={len(text)}")
    if not text:
        error_response(request_id, "INVALID_REQUEST", "Missing 'text' in payload")
        return
    start_time = time.time()
    try:
        result = review_engine.run_review(text)
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=quick_review, duration={duration}ms")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"Quick review error: id={request_id}, msg={str(e)}")
        error_response(request_id, "REVIEW_ERROR", f"Review failed: {str(e)}")


# =============================================================================
# ACTION ROUTER
# =============================================================================

ACTION_HANDLERS = {
    "analyze": handle_analyze,
    "rewrite": handle_rewrite,
    "convert_dita": handle_convert_dita,
    "impact_analyze": handle_impact_analyze,
    "markitdown": handle_markitdown,
    "quick_review": handle_quick_review,
}


# =============================================================================
# MAIN MESSAGE LOOP
# =============================================================================

def main():
    """Main stdin/stdout message loop."""
    logger.info("Backend process started, ready for requests")

    # Emit ready signal
    send_response({"status": "ready"})

    # Handle SIGTERM gracefully
    def handle_sigterm(signum, frame):
        logger.info("Shutdown requested (SIGTERM), cleaning up")
        logger.info("Backend process exiting")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Message loop
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            # Parse JSON request
            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                error_response("unknown", "INVALID_REQUEST",
                               "Malformed JSON", str(e))
                continue

            request_id = request.get("id", "unknown")
            action = request.get("action", "")
            payload = request.get("payload", {})

            logger.info(f"Request received: id={request_id}, action={action}")

            # Handle shutdown
            if action == "shutdown":
                logger.info("Shutdown requested, cleaning up")
                logger.info("Backend process exiting")
                break

            # Route to handler
            handler = ACTION_HANDLERS.get(action)
            if not handler:
                error_response(request_id, "UNKNOWN_ACTION",
                               f"Unrecognized action: {action}")
                continue

            # Execute handler with error wrapping
            try:
                handler(request_id, payload)
            except Exception as e:
                logger.error(f"Handler error: id={request_id}, action={action}, "
                             f"msg={str(e)}")
                error_response(request_id, "INTERNAL_ERROR",
                               str(e), traceback.format_exc())

    except EOFError:
        logger.info("Stdin EOF received, treating as shutdown")
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down")

    logger.info("Backend process exiting")


if __name__ == "__main__":
    main()
