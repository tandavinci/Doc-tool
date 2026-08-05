"""
JIRA Summarizer — AI-powered ticket summarization and analysis.

Uses local Ollama (via the OpenAI-compatible API) to:
1. Summarize JIRA tickets for documentation writers
2. Identify documentation impact from ticket content
3. Assess completeness for TECDOC workflows
4. Generate structured summaries ready for first-draft generation

Operates as a stateless module — no conversation history needed.
"""

import json
import logging
import os
import time

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_API_KEY = "ollama"  # Dummy key required by the SDK


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

SUMMARIZE_PROMPT = """You are an AI Documentation Analyst designed to support the Documentation Development Lifecycle (DDLC).

Please provide the output in markdown format.

Your role is to analyze input content from JIRA tickets and related sources to extract and generate a structured functional overview that documentation writers can directly use for planning and authoring.

Analyze the provided content carefully and perform the following:

1. Identify key functional elements of the system:
   - Features
   - Functional workflows
   - User interactions
   - System behavior

2. Detect any:
   - New features
   - Enhancements
   - Changes from previous versions (if mentioned)

3. Determine impacted areas:
   - Modules
   - Roles/users
   - Integrations
   - UI components

4. Extract implicit workflows if not explicitly documented.

5. Identify gaps, ambiguities, or missing details.

IMPORTANT:
- Do NOT fabricate information.
- Only use evidence from the input.
- If something is unclear or missing, explicitly call it out.

OUTPUT FORMAT: Structured Functional Overview

---

### 1. Overview
- High-level purpose of the feature/module
- Business context (if available)

---

### 2. Key Features
- Feature Name
  - Description
  - Key capabilities

---

### 3. Functional Workflows
- Workflow Name
  - Step-by-step description (derived or explicit)
  - Actors involved

---

### 4. Changes / Enhancements
- New features:
- Modified behavior:
- Deprecated elements:

(If not mentioned, state: "No explicit changes identified")

---

### 5. Affected Areas
- Modules:
- User roles:
- Integrations:
- UI components:

---

### 6. Use Cases
- Use Case 1:
- Use Case 2:

---

### 7. Dependencies / Assumptions
- List any dependencies or inferred assumptions

---

### 8. Open Questions / Gaps
- Missing information
- Ambiguities
- Clarifications needed from SMEs

---

### 9. Risks / Edge Cases (Optional)
- Identified risks or unclear behavior

---

### 10. Suggested Documentation Sections
- Topics that should be created in DITA/Docs:
  - Concept topics
  - Task topics
  - Reference topics

ADDITIONAL RULES:
- Pay attention to headings hierarchy in descriptions
- Treat bullet points as potential workflows/features
- Capture embedded notes, warnings, and tables
- Prioritize sections like "Overview", "Scope", "Functional Description"
- Extract structured info from paragraphs and tables
- Handle long-form content carefully (summarize without losing meaning)
- Do not hallucinate features or workflows
- Maintain consistent structure across runs
- Use neutral, professional tone
- Avoid assumptions unless explicitly labeled as "inferred"
- If input is empty, respond: "No content provided for analysis."
- Never generate misleading summaries for invalid input.
"""

DOC_IMPACT_PROMPT = """You are an expert documentation impact assessor for Infor Information Development. Analyze the JIRA ticket content and determine its documentation impact.

Assess and return a structured analysis:

1. **Impact Level**: Critical / High / Medium / Low / None
   - Critical: Major new feature requiring new documentation set or guide
   - High: Significant changes requiring new topics or major revisions
   - Medium: Updates to existing topics (field changes, new options, workflow modifications)
   - Low: Minor corrections or UI text changes
   - None: Internal/technical change with no user-facing documentation impact

2. **Affected Documentation Areas** (list all that apply):
   - User Guide, Admin Guide, Configuration Guide, API Reference, Release Notes
   - Installation Guide, Implementation Guide, Online Help, Field Descriptions

3. **Specific Topics Likely Affected**: Identify specific topic types and likely titles.

4. **New Topics Required**: Yes/No, and suggested topic titles if Yes.

5. **Documentation Type Needed**: Concept, Task, Reference, or combination.

6. **Estimated Effort**: Small (< 2 hours), Medium (2-8 hours), Large (> 8 hours)

7. **Dependencies**: Any prerequisite documentation or information needed.

Rules:
- Base your assessment only on the provided ticket content.
- If the ticket lacks sufficient detail for a confident assessment, flag uncertainty.
- Consider both direct impacts (the changed feature) and indirect impacts (related features).
"""

MISSING_FIELDS_PROMPT = """You are a JIRA ticket quality analyst for Infor's TECDOC documentation workflow. Analyze the ticket and identify what information is missing or insufficient for a technical writer to create documentation.

For each missing or insufficient area, provide:
1. **Field/Area**: What information is missing
2. **Why It Matters**: Why a writer needs this for documentation
3. **Suggested Action**: What the reporter/developer should provide
4. **Priority**: Critical (blocks writing) / Important (degrades quality) / Nice-to-have

Check for these documentation-critical elements:
- Clear description of what changed (feature, behavior, UI, API)
- Affected product and version
- User-facing workflow or steps to use the feature
- Screen names, field names, navigation paths
- Prerequisites or configuration requirements
- Expected behavior before and after the change
- Error messages or validation rules
- Integration points with other features
- Migration or upgrade considerations
- Acceptance criteria that implies user-visible changes

Rules:
- Be specific about what is missing — do not use vague terms.
- Prioritize missing items that would block a writer from creating accurate documentation.
- If the ticket is well-documented, say so and note any minor improvements.
"""


# =============================================================================
# OLLAMA CLIENT
# =============================================================================

_client = None


def _get_client():
    """Get or create the OpenAI client for Ollama."""
    global _client
    if _client is None:
        if OpenAI is None:
            raise RuntimeError(
                "openai package not installed. Install with: pip install openai"
            )
        _client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
    return _client


def _call_llm(system_prompt, user_content, max_tokens=2048):
    """Make a single LLM call and return the response text.

    Args:
        system_prompt: System prompt defining the task
        user_content: The user message content
        max_tokens: Maximum tokens in the response

    Returns:
        str: The LLM response text

    Raises:
        RuntimeError: If LLM is unavailable or call fails
    """
    client = _get_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    try:
        start_time = time.time()
        completion = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=messages,
            temperature=0.1,  # Low temp for factual summarization
            max_tokens=max_tokens,
        )
        duration = int((time.time() - start_time) * 1000)
        response = completion.choices[0].message.content or ""
        logger.info(f"LLM call completed: duration={duration}ms, response_len={len(response)}")
        return response
    except Exception as e:
        error_msg = str(e)
        if "Connection refused" in error_msg or "connection error" in error_msg.lower():
            raise RuntimeError(
                "Cannot connect to Ollama. Ensure Ollama is running "
                f"(run 'ollama serve') and model '{OLLAMA_MODEL}' is pulled."
            )
        raise RuntimeError(f"LLM call failed: {error_msg}")


# =============================================================================
# TICKET FORMATTING
# =============================================================================

def _format_ticket_for_llm(issue):
    """Format a normalized JIRA issue dict into readable text for the LLM.

    Args:
        issue: Normalized issue dict from jira_handler

    Returns:
        str: Formatted ticket text
    """
    parts = []
    parts.append(f"JIRA Ticket: {issue.get('key', 'Unknown')}")
    parts.append(f"Summary: {issue.get('summary', 'No summary')}")
    parts.append(f"Type: {issue.get('issue_type', 'Unknown')}")
    parts.append(f"Priority: {issue.get('priority', 'None')}")
    parts.append(f"Status: {issue.get('status', 'Unknown')}")
    parts.append(f"Reporter: {issue.get('reporter', 'Unknown')}")
    parts.append(f"Assignee: {issue.get('assignee', 'Unassigned')}")

    fix_versions = issue.get("fix_versions", [])
    if fix_versions:
        parts.append(f"Fix Version(s): {', '.join(fix_versions)}")

    components = issue.get("components", [])
    if components:
        parts.append(f"Components: {', '.join(components)}")

    labels = issue.get("labels", [])
    if labels:
        parts.append(f"Labels: {', '.join(labels)}")

    parts.append(f"Created: {issue.get('created', 'Unknown')}")
    parts.append(f"Updated: {issue.get('updated', 'Unknown')}")

    parts.append("")  # Blank line before description

    description = issue.get("description", "")
    if description:
        parts.append("--- DESCRIPTION ---")
        parts.append(description)
    else:
        parts.append("--- DESCRIPTION ---")
        parts.append("[No description provided]")

    # Include comments if available
    comments = issue.get("comments", [])
    if comments:
        parts.append("")
        parts.append("--- COMMENTS ---")
        for c in comments[:5]:  # Limit to 5 most recent
            author = c.get("author", "Unknown")
            body = c.get("body", "")
            created = c.get("created", "")
            parts.append(f"[{author} - {created}]")
            parts.append(body)
            parts.append("")

    return "\n".join(parts)


# =============================================================================
# PUBLIC API
# =============================================================================

def summarize_ticket(issue):
    """Generate a structured summary of a JIRA ticket.

    Args:
        issue: Normalized issue dict from jira_handler

    Returns:
        dict with:
        - success: bool
        - summary: str (the formatted summary)
        - issue_key: str
        - error: str (if success is False)
    """
    try:
        ticket_text = _format_ticket_for_llm(issue)
        response = _call_llm(SUMMARIZE_PROMPT, ticket_text, max_tokens=3000)

        return {
            "success": True,
            "summary": response,
            "issue_key": issue.get("key", ""),
            "error": "",
        }
    except RuntimeError as e:
        return {
            "success": False,
            "summary": "",
            "issue_key": issue.get("key", ""),
            "error": str(e),
        }


def assess_doc_impact(issue):
    """Assess the documentation impact of a JIRA ticket.

    Args:
        issue: Normalized issue dict from jira_handler

    Returns:
        dict with:
        - success: bool
        - assessment: str (the impact assessment)
        - issue_key: str
        - error: str (if success is False)
    """
    try:
        ticket_text = _format_ticket_for_llm(issue)
        response = _call_llm(DOC_IMPACT_PROMPT, ticket_text, max_tokens=1500)

        return {
            "success": True,
            "assessment": response,
            "issue_key": issue.get("key", ""),
            "error": "",
        }
    except RuntimeError as e:
        return {
            "success": False,
            "assessment": "",
            "issue_key": issue.get("key", ""),
            "error": str(e),
        }


def analyze_missing_fields_ai(issue):
    """Use AI to analyze a JIRA ticket for missing documentation-critical fields.

    This complements the rule-based analyze_missing_fields() in jira_handler.py
    by using LLM understanding to identify semantic gaps.

    Args:
        issue: Normalized issue dict from jira_handler

    Returns:
        dict with:
        - success: bool
        - analysis: str (the missing fields analysis)
        - issue_key: str
        - error: str (if success is False)
    """
    try:
        ticket_text = _format_ticket_for_llm(issue)
        response = _call_llm(MISSING_FIELDS_PROMPT, ticket_text, max_tokens=1500)

        return {
            "success": True,
            "analysis": response,
            "issue_key": issue.get("key", ""),
            "error": "",
        }
    except RuntimeError as e:
        return {
            "success": False,
            "analysis": "",
            "issue_key": issue.get("key", ""),
            "error": str(e),
        }


def summarize_batch(issues):
    """Summarize multiple tickets at once (brief mode).

    Generates a one-line summary for each ticket without full LLM calls
    (uses the ticket's own summary + basic heuristics for speed).

    Args:
        issues: List of normalized issue dicts

    Returns:
        list of dicts with: key, summary, issue_type, priority, doc_relevance
    """
    results = []
    for issue in issues:
        # Quick heuristic assessment without LLM
        description = issue.get("description", "")
        summary = issue.get("summary", "")
        issue_type = issue.get("issue_type", "")
        labels = issue.get("labels", [])

        # Assess doc relevance heuristically
        doc_keywords = [
            "documentation", "doc", "help", "guide", "user guide",
            "release note", "field", "screen", "page", "workflow",
            "new feature", "enhancement", "ui", "configuration",
        ]
        text_lower = f"{summary} {description}".lower()
        keyword_hits = sum(1 for kw in doc_keywords if kw in text_lower)

        # Issue type relevance
        type_relevance = {
            "Story": "high",
            "New Feature": "high",
            "Enhancement": "high",
            "Bug": "medium",
            "Task": "medium",
            "Sub-task": "low",
            "Epic": "high",
        }
        base_relevance = type_relevance.get(issue_type, "medium")

        # Boost if doc-related labels
        if any("doc" in l.lower() or "tecdoc" in l.lower() for l in labels):
            base_relevance = "high"

        # Boost based on keyword hits
        if keyword_hits >= 3:
            base_relevance = "high"
        elif keyword_hits == 0 and base_relevance != "high":
            base_relevance = "low"

        results.append({
            "key": issue.get("key", ""),
            "summary": summary,
            "issue_type": issue_type,
            "priority": issue.get("priority", "None"),
            "status": issue.get("status", "Unknown"),
            "doc_relevance": base_relevance,
            "has_description": bool(description and len(description) > 20),
            "has_fix_version": bool(issue.get("fix_versions")),
        })

    return results
