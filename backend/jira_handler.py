"""
JIRA Handler — Fetches issues from Atlassian Jira REST API.

Connects to the configured Jira Cloud instance to retrieve issues
assigned to the current user. Supports fetching dashboard data,
individual issue details, and transition info.

Configuration is loaded from environment variables:
- JIRA_BASE_URL: Base URL of the Jira instance (e.g., https://infor.atlassian.net)
- JIRA_USER_EMAIL: User email for authentication
- JIRA_API_TOKEN: API token for authentication
- JIRA_PROJECT_KEY: Optional default project key filter
"""

import json
import logging
import os
import urllib.request
import urllib.error
import urllib.parse
import base64
from typing import Optional

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "https://infor.atlassian.net")
JIRA_USER_EMAIL = os.environ.get("JIRA_USER_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "TECDOC")

# Fields to retrieve for dashboard view
DASHBOARD_FIELDS = [
    "summary", "status", "priority", "assignee", "reporter",
    "issuetype", "created", "updated", "fixVersions", "components",
    "labels", "description", "comment", "resolution",
    "customfield_10014",  # Epic Link (common custom field)
]

# Required TECDOC fields for documentation tickets
TECDOC_REQUIRED_FIELDS = {
    "summary": "Summary",
    "description": "Description",
    "priority": "Priority",
    "fixVersions": "Fix Version",
    "components": "Components",
    "labels": "Labels",
    "issuetype": "Issue Type",
}

# Optional but recommended TECDOC fields
TECDOC_RECOMMENDED_FIELDS = {
    "acceptance_criteria": "Acceptance Criteria",
    "overview_of_change": "Overview of Change",
    "detailed_description": "Detailed Description",
    "steps_to_reproduce": "Steps to Reproduce",
    "expected_behavior": "Expected Behavior",
    "actual_behavior": "Actual Behavior",
    "affected_version": "Affected Version",
    "test_notes": "Test Notes",
}


# =============================================================================
# HTTP HELPERS
# =============================================================================

def _get_auth_header():
    """Build Basic Auth header from email and API token."""
    if not JIRA_USER_EMAIL or not JIRA_API_TOKEN:
        return None
    credentials = f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return f"Basic {encoded}"


def _make_request(endpoint, method="GET", data=None, params=None):
    """Make an HTTP request to the Jira REST API.

    Args:
        endpoint: API endpoint path (e.g., /rest/api/3/search)
        method: HTTP method
        data: Request body (dict, will be JSON-encoded)
        params: Query parameters (dict)

    Returns:
        Parsed JSON response dict

    Raises:
        RuntimeError: On authentication or connection failure
        ValueError: On invalid response
    """
    auth_header = _get_auth_header()
    if not auth_header:
        raise RuntimeError(
            "JIRA credentials not configured. Set JIRA_USER_EMAIL and "
            "JIRA_API_TOKEN environment variables."
        )

    url = f"{JIRA_BASE_URL.rstrip('/')}{endpoint}"
    if params:
        query_string = urllib.parse.urlencode(params)
        url = f"{url}?{query_string}"

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body = None
    if data:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = response.read().decode("utf-8")
            if response_data:
                return json.loads(response_data)
            return {}
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        if e.code == 401:
            raise RuntimeError("JIRA authentication failed. Check your API token.")
        elif e.code == 403:
            raise RuntimeError("JIRA access forbidden. Check your permissions.")
        elif e.code == 404:
            raise RuntimeError(f"JIRA resource not found: {endpoint}")
        else:
            raise RuntimeError(
                f"JIRA API error (HTTP {e.code}): {error_body[:500]}"
            )
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot connect to JIRA: {str(e.reason)}")
    except Exception as e:
        raise RuntimeError(f"JIRA request failed: {str(e)}")


# =============================================================================
# PUBLIC API
# =============================================================================

def configure(base_url=None, user_email=None, api_token=None, project_key=None):
    """Update JIRA configuration at runtime.

    Called from protocol.py when the frontend sends credentials.
    """
    global JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY

    if base_url:
        JIRA_BASE_URL = base_url
    if user_email:
        JIRA_USER_EMAIL = user_email
    if api_token:
        JIRA_API_TOKEN = api_token
    if project_key:
        JIRA_PROJECT_KEY = project_key

    logger.info(f"JIRA configured: url={JIRA_BASE_URL}, user={JIRA_USER_EMAIL}")


def get_config_status():
    """Check if JIRA is configured and return status."""
    configured = bool(JIRA_USER_EMAIL and JIRA_API_TOKEN and JIRA_BASE_URL)
    return {
        "configured": configured,
        "base_url": JIRA_BASE_URL,
        "user_email": JIRA_USER_EMAIL,
        "project_key": JIRA_PROJECT_KEY,
        "has_token": bool(JIRA_API_TOKEN),
    }


def fetch_assigned_issues(project_key=None, max_results=50, status_filter=None):
    """Fetch JIRA issues assigned to the current user.

    Args:
        project_key: Optional project key to filter (e.g., 'TECDOC')
        max_results: Maximum number of issues to return
        status_filter: Optional status category filter (e.g., 'To Do', 'In Progress')

    Returns:
        Dict with issues list, total count, and metadata
    """
    # Build JQL query
    jql_parts = ["assignee = currentUser()"]

    effective_project = project_key or JIRA_PROJECT_KEY
    if effective_project:
        jql_parts.append(f"project = {effective_project}")

    if status_filter:
        if status_filter.lower() == "open":
            jql_parts.append("statusCategory != Done")
        elif status_filter.lower() == "done":
            jql_parts.append("statusCategory = Done")
        elif status_filter.lower() == "in progress":
            jql_parts.append("statusCategory = \"In Progress\"")
        elif status_filter.lower() == "to do":
            jql_parts.append("statusCategory = \"To Do\"")

    jql = " AND ".join(jql_parts) + " ORDER BY updated DESC"

    logger.info(f"Fetching JIRA issues: JQL={jql}")

    # Use the new /rest/api/3/search/jql endpoint (POST with JSON body)
    # The old /rest/api/3/search endpoint was deprecated and returns 410 GONE
    request_body = {
        "jql": jql,
        "maxResults": max_results,
        "fields": DASHBOARD_FIELDS,
    }

    result = _make_request("/rest/api/3/search/jql", method="POST", data=request_body)

    # Normalize issues for frontend consumption
    issues = []
    for raw_issue in result.get("issues", []):
        issues.append(_normalize_issue(raw_issue))

    return {
        "issues": issues,
        "total": result.get("total", 0),
        "max_results": max_results,
        "jql": jql,
    }


def fetch_issue_detail(issue_key):
    """Fetch full details for a single JIRA issue.

    Args:
        issue_key: Issue key (e.g., 'TECDOC-1234')

    Returns:
        Normalized issue dict with all available fields
    """
    logger.info(f"Fetching JIRA issue detail: {issue_key}")

    result = _make_request(f"/rest/api/3/issue/{issue_key}", params={
        "fields": "*all",
        "expand": "renderedFields,names",
    })

    issue = _normalize_issue(result, full_detail=True)

    # Also fetch comments
    comments_result = _make_request(
        f"/rest/api/3/issue/{issue_key}/comment",
        params={"maxResults": 20, "orderBy": "-created"},
    )
    issue["comments"] = [
        {
            "id": c.get("id"),
            "author": _get_display_name(c.get("author")),
            "body": _extract_text_from_adf(c.get("body", {})),
            "created": c.get("created"),
            "updated": c.get("updated"),
        }
        for c in comments_result.get("comments", [])
    ]

    return issue


def check_connection():
    """Test JIRA connectivity and return server info."""
    try:
        result = _make_request("/rest/api/3/myself")
        return {
            "connected": True,
            "user": result.get("displayName", ""),
            "email": result.get("emailAddress", ""),
            "account_id": result.get("accountId", ""),
        }
    except RuntimeError as e:
        return {
            "connected": False,
            "error": str(e),
        }


# =============================================================================
# NORMALIZATION HELPERS
# =============================================================================

def _normalize_issue(raw, full_detail=False):
    """Convert raw Jira API issue to a clean dict for the frontend.

    Args:
        raw: Raw issue dict from Jira API
        full_detail: If True, include all fields; otherwise dashboard subset

    Returns:
        Normalized issue dict
    """
    fields = raw.get("fields", {})

    issue = {
        "key": raw.get("key", ""),
        "id": raw.get("id", ""),
        "self_url": raw.get("self", ""),
        "summary": fields.get("summary", ""),
        "status": _get_nested(fields, "status", "name", default="Unknown"),
        "status_category": _get_nested(
            fields, "status", "statusCategory", "name", default="Unknown"
        ),
        "priority": _get_nested(fields, "priority", "name", default="None"),
        "issue_type": _get_nested(fields, "issuetype", "name", default="Unknown"),
        "assignee": _get_display_name(fields.get("assignee")),
        "reporter": _get_display_name(fields.get("reporter")),
        "created": fields.get("created", ""),
        "updated": fields.get("updated", ""),
        "fix_versions": [
            v.get("name", "") for v in (fields.get("fixVersions") or [])
        ],
        "components": [
            c.get("name", "") for c in (fields.get("components") or [])
        ],
        "labels": fields.get("labels", []),
        "resolution": _get_nested(fields, "resolution", "name", default="Unresolved"),
    }

    # Extract description (Atlassian Document Format → plain text)
    description = fields.get("description")
    if description:
        if isinstance(description, dict):
            issue["description"] = _extract_text_from_adf(description)
        else:
            issue["description"] = str(description)
    else:
        issue["description"] = ""

    if full_detail:
        # Include rendered fields if available
        rendered = raw.get("renderedFields", {})
        if rendered.get("description"):
            issue["description_html"] = rendered["description"]

        # Include any custom fields that might be relevant
        for key, value in fields.items():
            if key.startswith("customfield_") and value:
                if isinstance(value, dict):
                    issue[key] = value.get("value", str(value))
                elif isinstance(value, list):
                    issue[key] = [
                        v.get("value", str(v)) if isinstance(v, dict) else str(v)
                        for v in value
                    ]
                else:
                    issue[key] = str(value)

    return issue


def _get_display_name(user_obj):
    """Extract display name from a Jira user object."""
    if not user_obj:
        return "Unassigned"
    return user_obj.get("displayName", user_obj.get("name", "Unknown"))


def _get_nested(obj, *keys, default=""):
    """Safely traverse nested dicts."""
    current = obj
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        if current is None:
            return default
    return current if current is not None else default


def _extract_text_from_adf(adf_doc):
    """Extract plain text from Atlassian Document Format (ADF).

    ADF is the JSON format used by Jira Cloud for rich text fields.
    This recursively walks the document tree and extracts text content.

    Args:
        adf_doc: ADF document dict (top-level has "type": "doc", "content": [...])

    Returns:
        Plain text string
    """
    if not adf_doc or not isinstance(adf_doc, dict):
        return ""

    parts = []
    _walk_adf_node(adf_doc, parts)
    return "\n".join(parts).strip()


def _walk_adf_node(node, parts, depth=0):
    """Recursively walk ADF nodes and collect text."""
    if not isinstance(node, dict):
        return

    node_type = node.get("type", "")

    # Text node — directly contains text
    if node_type == "text":
        text = node.get("text", "")
        if text:
            parts.append(text)
        return

    # Block-level nodes that should add newlines
    block_types = {
        "paragraph", "heading", "blockquote", "codeBlock",
        "rule", "mediaGroup", "mediaSingle",
    }

    # List item handling
    if node_type == "listItem":
        # Collect child text into a single bullet
        child_parts = []
        for child in node.get("content", []):
            _walk_adf_node(child, child_parts, depth + 1)
        bullet_text = " ".join(child_parts).strip()
        if bullet_text:
            parts.append(f"  {'  ' * depth}- {bullet_text}")
        return

    if node_type == "heading":
        level = node.get("attrs", {}).get("level", 1)
        child_parts = []
        for child in node.get("content", []):
            _walk_adf_node(child, child_parts, depth + 1)
        heading_text = " ".join(child_parts).strip()
        if heading_text:
            parts.append(f"{'#' * level} {heading_text}")
        return

    if node_type == "codeBlock":
        child_parts = []
        for child in node.get("content", []):
            _walk_adf_node(child, child_parts, depth + 1)
        code_text = "\n".join(child_parts)
        if code_text:
            parts.append(f"```\n{code_text}\n```")
        return

    # Table handling
    if node_type == "table":
        for child in node.get("content", []):
            _walk_adf_node(child, parts, depth + 1)
        parts.append("")
        return

    if node_type == "tableRow":
        row_cells = []
        for child in node.get("content", []):
            cell_parts = []
            _walk_adf_node(child, cell_parts, depth + 1)
            row_cells.append(" ".join(cell_parts).strip())
        parts.append(" | ".join(row_cells))
        return

    if node_type in ("tableCell", "tableHeader"):
        for child in node.get("content", []):
            _walk_adf_node(child, parts, depth + 1)
        return

    # Generic content traversal
    content = node.get("content", [])
    if content:
        for child in content:
            _walk_adf_node(child, parts, depth)
        # Add newline after block elements
        if node_type in block_types:
            parts.append("")


# =============================================================================
# MISSING FIELDS ANALYSIS
# =============================================================================

def analyze_missing_fields(issue):
    """Analyze a normalized issue for missing or incomplete TECDOC fields.

    Args:
        issue: Normalized issue dict (from _normalize_issue or fetch_issue_detail)

    Returns:
        Dict with missing_required, missing_recommended, completeness_score, suggestions
    """
    missing_required = []
    missing_recommended = []
    suggestions = []

    # Check required fields
    for field_key, field_label in TECDOC_REQUIRED_FIELDS.items():
        value = issue.get(field_key, "")
        if field_key == "fixVersions":
            value = issue.get("fix_versions", [])
            if not value:
                missing_required.append({
                    "field": field_label,
                    "key": field_key,
                    "severity": "high",
                    "suggestion": "Add a Fix Version to indicate which release this change targets.",
                })
        elif field_key == "components":
            value = issue.get("components", [])
            if not value:
                missing_required.append({
                    "field": field_label,
                    "key": field_key,
                    "severity": "medium",
                    "suggestion": "Add a Component to categorize this issue for documentation routing.",
                })
        elif field_key == "labels":
            value = issue.get("labels", [])
            if not value:
                missing_recommended.append({
                    "field": field_label,
                    "key": field_key,
                    "severity": "low",
                    "suggestion": "Add labels to improve discoverability and classification.",
                })
        elif not value or (isinstance(value, str) and len(value.strip()) < 10):
            severity = "high" if field_key in ("summary", "description") else "medium"
            missing_required.append({
                "field": field_label,
                "key": field_key,
                "severity": severity,
                "suggestion": f"Provide a detailed {field_label} for documentation purposes.",
            })

    # Check description quality
    description = issue.get("description", "")
    if description and len(description) < 50:
        suggestions.append({
            "field": "Description",
            "message": "Description is very brief. Consider adding more detail about the change, its scope, and user impact.",
            "severity": "medium",
        })
    elif description and len(description) > 50:
        # Check for key documentation elements
        desc_lower = description.lower()
        if "step" not in desc_lower and "procedure" not in desc_lower:
            suggestions.append({
                "field": "Description",
                "message": "Consider adding step-by-step instructions or expected workflow if this is a procedural change.",
                "severity": "low",
            })
        if "screen" not in desc_lower and "page" not in desc_lower and "field" not in desc_lower:
            suggestions.append({
                "field": "Description",
                "message": "Consider specifying which screens, pages, or fields are affected by this change.",
                "severity": "low",
            })

    # Check for documentation-specific recommended content
    if not any(kw in description.lower() for kw in ["overview", "summary", "change"]):
        missing_recommended.append({
            "field": "Overview of Change",
            "key": "overview_of_change",
            "severity": "medium",
            "suggestion": "Add an overview describing what changed and why.",
        })

    if not any(kw in description.lower() for kw in ["user", "customer", "impact", "affect"]):
        missing_recommended.append({
            "field": "User Impact",
            "key": "user_impact",
            "severity": "medium",
            "suggestion": "Describe how this change impacts end users.",
        })

    # Compute completeness score
    total_fields = len(TECDOC_REQUIRED_FIELDS) + len(TECDOC_RECOMMENDED_FIELDS)
    missing_count = len(missing_required) + len(missing_recommended)
    completeness = max(0, round((1 - missing_count / total_fields) * 100))

    return {
        "issue_key": issue.get("key", ""),
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "suggestions": suggestions,
        "completeness_score": completeness,
        "total_required": len(TECDOC_REQUIRED_FIELDS),
        "total_recommended": len(TECDOC_RECOMMENDED_FIELDS),
        "filled_required": len(TECDOC_REQUIRED_FIELDS) - len(missing_required),
        "filled_recommended": len(TECDOC_RECOMMENDED_FIELDS) - len(missing_recommended),
    }
