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
import ai_assistant
import doc_impact
import jira_handler
import jira_summarizer
import jira_analyst
import neoscribe_engine


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


def handle_ai_chat(request_id, payload):
    """Handle AI assistant chat request."""
    message = payload.get("message", "")
    context = payload.get("context", "")
    logger.debug(f"[DEBUG] Action 'ai_chat' received: id={request_id}, msg_len={len(message)}")
    if not message:
        error_response(request_id, "INVALID_REQUEST", "Missing 'message' in payload")
        return
    start_time = time.time()
    try:
        result = ai_assistant.chat(message, context)
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=ai_chat, duration={duration}ms")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"AI chat error: id={request_id}, msg={str(e)}")
        error_response(request_id, "AI_CHAT_ERROR", f"AI chat failed: {str(e)}")


def handle_ai_status(request_id, payload):
    """Handle AI assistant status check request."""
    logger.debug(f"[DEBUG] Action 'ai_status' received: id={request_id}")
    try:
        result = ai_assistant.check_status()
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"AI status error: id={request_id}, msg={str(e)}")
        error_response(request_id, "AI_STATUS_ERROR", f"Status check failed: {str(e)}")


def handle_ai_clear(request_id, payload):
    """Handle AI assistant clear history request."""
    logger.debug(f"[DEBUG] Action 'ai_clear' received: id={request_id}")
    try:
        result = ai_assistant.clear_history()
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"AI clear error: id={request_id}, msg={str(e)}")
        error_response(request_id, "AI_CLEAR_ERROR", f"Clear history failed: {str(e)}")


def handle_doc_impact(request_id, payload):
    """Handle documentation impact assessment request."""
    session_data = payload.get("sessionData", [])
    logger.debug(f"[DEBUG] Action 'doc_impact' received: id={request_id}, tickets={len(session_data)}")
    if not session_data:
        error_response(request_id, "INVALID_REQUEST", "Missing 'sessionData' in payload")
        return
    start_time = time.time()
    try:
        result = doc_impact.analyze_session(session_data)
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=doc_impact, duration={duration}ms")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"Doc impact error: id={request_id}, msg={str(e)}")
        error_response(request_id, "DOC_IMPACT_ERROR", f"Impact assessment failed: {str(e)}")


# =============================================================================
# JIRA HANDLERS
# =============================================================================

def handle_jira_configure(request_id, payload):
    """Handle JIRA configuration update."""
    logger.debug(f"[DEBUG] Action 'jira_configure' received: id={request_id}")
    try:
        jira_handler.configure(
            base_url=payload.get("baseUrl"),
            user_email=payload.get("userEmail"),
            api_token=payload.get("apiToken"),
            project_key=payload.get("projectKey"),
        )
        status = jira_handler.get_config_status()
        success_response(request_id, status)
    except Exception as e:
        logger.error(f"JIRA configure error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_CONFIG_ERROR", f"Configuration failed: {str(e)}")


def handle_jira_status(request_id, payload):
    """Handle JIRA connection status check."""
    logger.debug(f"[DEBUG] Action 'jira_status' received: id={request_id}")
    try:
        config_status = jira_handler.get_config_status()
        if config_status["configured"]:
            conn_status = jira_handler.check_connection()
            config_status.update(conn_status)
        success_response(request_id, config_status)
    except Exception as e:
        logger.error(f"JIRA status error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_STATUS_ERROR", f"Status check failed: {str(e)}")


def handle_jira_fetch(request_id, payload):
    """Handle fetching JIRA issues assigned to the user."""
    project_key = payload.get("projectKey", "")
    max_results = payload.get("maxResults", 50)
    status_filter = payload.get("statusFilter", "")
    logger.debug(f"[DEBUG] Action 'jira_fetch' received: id={request_id}, project={project_key}")
    start_time = time.time()
    try:
        result = jira_handler.fetch_assigned_issues(
            project_key=project_key,
            max_results=max_results,
            status_filter=status_filter,
        )
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=jira_fetch, duration={duration}ms, count={len(result.get('issues', []))}")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"JIRA fetch error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_FETCH_ERROR", f"Fetch failed: {str(e)}")


def handle_jira_detail(request_id, payload):
    """Handle fetching full detail for a single JIRA issue."""
    issue_key = payload.get("issueKey", "")
    logger.debug(f"[DEBUG] Action 'jira_detail' received: id={request_id}, key={issue_key}")
    if not issue_key:
        error_response(request_id, "INVALID_REQUEST", "Missing 'issueKey' in payload")
        return
    start_time = time.time()
    try:
        result = jira_handler.fetch_issue_detail(issue_key)
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=jira_detail, duration={duration}ms")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"JIRA detail error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_DETAIL_ERROR", f"Detail fetch failed: {str(e)}")


def handle_jira_summarize(request_id, payload):
    """Handle AI summarization of a JIRA ticket."""
    issue = payload.get("issue", {})
    logger.debug(f"[DEBUG] Action 'jira_summarize' received: id={request_id}, key={issue.get('key', '')}")
    if not issue:
        error_response(request_id, "INVALID_REQUEST", "Missing 'issue' in payload")
        return
    start_time = time.time()
    try:
        result = jira_summarizer.summarize_ticket(issue)
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=jira_summarize, duration={duration}ms")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"JIRA summarize error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_SUMMARIZE_ERROR", f"Summarization failed: {str(e)}")


def handle_jira_doc_impact(request_id, payload):
    """Handle AI documentation impact assessment of a JIRA ticket."""
    issue = payload.get("issue", {})
    logger.debug(f"[DEBUG] Action 'jira_doc_impact' received: id={request_id}, key={issue.get('key', '')}")
    if not issue:
        error_response(request_id, "INVALID_REQUEST", "Missing 'issue' in payload")
        return
    start_time = time.time()
    try:
        result = jira_summarizer.assess_doc_impact(issue)
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=jira_doc_impact, duration={duration}ms")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"JIRA doc impact error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_DOC_IMPACT_ERROR", f"Doc impact assessment failed: {str(e)}")


def handle_jira_missing_fields(request_id, payload):
    """Handle missing fields analysis for a JIRA ticket."""
    issue = payload.get("issue", {})
    use_ai = payload.get("useAI", True)
    logger.debug(f"[DEBUG] Action 'jira_missing_fields' received: id={request_id}, key={issue.get('key', '')}")
    if not issue:
        error_response(request_id, "INVALID_REQUEST", "Missing 'issue' in payload")
        return
    start_time = time.time()
    try:
        # Rule-based analysis (always fast)
        rule_result = jira_handler.analyze_missing_fields(issue)

        # AI-powered analysis (optional, slower)
        ai_result = None
        if use_ai:
            try:
                ai_result = jira_summarizer.analyze_missing_fields_ai(issue)
            except Exception as ai_err:
                logger.warning(f"AI missing fields analysis failed (non-fatal): {ai_err}")
                ai_result = {"success": False, "analysis": "", "error": str(ai_err)}

        combined = {
            "rule_based": rule_result,
            "ai_analysis": ai_result,
            "issue_key": issue.get("key", ""),
        }
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=jira_missing_fields, duration={duration}ms")
        success_response(request_id, combined)
    except Exception as e:
        logger.error(f"JIRA missing fields error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_MISSING_FIELDS_ERROR", f"Missing fields analysis failed: {str(e)}")


def handle_jira_first_draft(request_id, payload):
    """Handle Neoscribe first-draft generation from a JIRA ticket."""
    issue = payload.get("issue", {})
    topic_type = payload.get("topicType", "auto")
    writer_instructions = payload.get("writerInstructions", "")
    existing_xml = payload.get("existingXml", "")
    logger.debug(f"[DEBUG] Action 'jira_first_draft' received: id={request_id}, key={issue.get('key', '')}, type={topic_type}")
    if not issue:
        error_response(request_id, "INVALID_REQUEST", "Missing 'issue' in payload")
        return
    start_time = time.time()
    try:
        if existing_xml:
            # Mode 2: Update existing topic
            result = neoscribe_engine.update_existing_topic(
                issue, existing_xml, writer_instructions
            )
        else:
            # Mode 1: New topic draft
            result = neoscribe_engine.generate_new_draft(
                issue, topic_type, writer_instructions
            )
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=jira_first_draft, duration={duration}ms")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"JIRA first draft error: id={request_id}, msg={str(e)}")
        # Try fallback (no LLM)
        try:
            fallback = neoscribe_engine.generate_fallback_draft(issue, topic_type if topic_type != "auto" else "concept")
            fallback["warning"] = f"LLM unavailable ({str(e)}). Generated skeleton template."
            success_response(request_id, fallback)
        except Exception as fb_err:
            error_response(request_id, "JIRA_DRAFT_ERROR", f"First draft generation failed: {str(e)}")


# =============================================================================
# JIRA TICKET ANALYST HANDLERS
# =============================================================================

def handle_jira_analyze_ticket(request_id, payload):
    """Handle full TECDOC ticket readiness analysis."""
    issue_key = payload.get("issueKey", "")
    logger.debug(f"[DEBUG] Action 'jira_analyze_ticket' received: id={request_id}, key={issue_key}")
    if not issue_key:
        error_response(request_id, "INVALID_REQUEST", "Missing 'issueKey' in payload")
        return
    start_time = time.time()
    try:
        result = jira_analyst.analyze_ticket(issue_key)
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=jira_analyze_ticket, duration={duration}ms")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"JIRA analyze ticket error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_ANALYZE_ERROR", f"Ticket analysis failed: {str(e)}")


def handle_jira_analyze_chat(request_id, payload):
    """Handle chat-based TECDOC ticket analysis (formatted for chat display)."""
    issue_key = payload.get("issueKey", "")
    question = payload.get("question", "")
    logger.debug(f"[DEBUG] Action 'jira_analyze_chat' received: id={request_id}, key={issue_key}, q_len={len(question)}")
    if not issue_key:
        error_response(request_id, "INVALID_REQUEST", "Missing 'issueKey' in payload")
        return
    start_time = time.time()
    try:
        result = jira_analyst.analyze_ticket_chat(issue_key, question)
        duration = int((time.time() - start_time) * 1000)
        logger.info(f"Handler completed: id={request_id}, action=jira_analyze_chat, duration={duration}ms")
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"JIRA analyze chat error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_ANALYZE_CHAT_ERROR", f"Chat analysis failed: {str(e)}")


def handle_jira_quick_summary(request_id, payload):
    """Handle quick summary fetch for JIRA dashboard display."""
    issue_key = payload.get("issueKey", "")
    logger.debug(f"[DEBUG] Action 'jira_quick_summary' received: id={request_id}, key={issue_key}")
    if not issue_key:
        error_response(request_id, "INVALID_REQUEST", "Missing 'issueKey' in payload")
        return
    try:
        result = jira_analyst.get_ticket_quick_summary(issue_key)
        success_response(request_id, result)
    except Exception as e:
        logger.error(f"JIRA quick summary error: id={request_id}, msg={str(e)}")
        error_response(request_id, "JIRA_SUMMARY_ERROR", f"Quick summary failed: {str(e)}")


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
    "doc_impact": handle_doc_impact,
    "ai_chat": handle_ai_chat,
    "ai_status": handle_ai_status,
    "ai_clear": handle_ai_clear,
    "jira_configure": handle_jira_configure,
    "jira_status": handle_jira_status,
    "jira_fetch": handle_jira_fetch,
    "jira_detail": handle_jira_detail,
    "jira_summarize": handle_jira_summarize,
    "jira_doc_impact": handle_jira_doc_impact,
    "jira_missing_fields": handle_jira_missing_fields,
    "jira_first_draft": handle_jira_first_draft,
    "jira_analyze_ticket": handle_jira_analyze_ticket,
    "jira_analyze_chat": handle_jira_analyze_chat,
    "jira_quick_summary": handle_jira_quick_summary,
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
