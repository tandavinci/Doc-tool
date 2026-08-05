"""
JIRA Ticket Analyst — TECDOC Documentation Readiness Assessment Engine.

Implements a comprehensive analysis pipeline for TECDOC Jira tickets,
assessing their readiness for documentation work per the Infor DDLC.

Sections implemented:
  1. Jira Ticket Access (via jira_handler)
  2. Required Field Validation (P1)
  3. Field Content Validation (P1)
  4. Reference Material Availability (P2)
  5. Cross-Reference with Related Development Ticket (P2)
  6. Input Sufficiency Assessment (P2)
  7. Correction Suggestions (P3)
  8. Output Format (structured report)
  9. Performance Requirements (<10s target)
  10. Definition of Done Checklist

Operates as a stateless module called by protocol.py.
"""

import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import jira_handler
import jira_summarizer

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Fields required for a TECDOC ticket to be documentation-ready
REQUIRED_FIELDS = {
    "components": "Components",
    "fix_versions": "Fix Versions",
    "user_doc_change": "User Doc Change",
    "linked_issues": "Linked Issue",
    "attachments": "Attachments",
    "description": "Description",
}

# Placeholder patterns that indicate a field is not truly filled
PLACEHOLDER_PATTERNS = [
    r"^\[.*\]$",                       # [Fill in Description]
    r"^TODO",                          # TODO: add details
    r"^TBD",                           # TBD
    r"^N/?A$",                         # N/A or NA
    r"^None$",                         # None
    r"^-$",                            # Just a dash
    r"^\.+$",                          # Just dots
    r"^placeholder",                   # placeholder text
    r"^insert\s",                      # insert description here
    r"^add\s+details",                 # add details
    r"^update\s+this",                 # update this field
]

# Reference material file extensions
REFERENCE_EXTENSIONS = {
    "documents": [".docx", ".doc", ".pdf", ".txt", ".rtf", ".odt"],
    "presentations": [".pptx", ".ppt", ".key"],
    "images": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".bmp"],
    "videos": [".mp4", ".mov", ".avi", ".webm"],
    "spreadsheets": [".xlsx", ".xls", ".csv"],
    "design": [".fig", ".sketch", ".xd"],
}

# URL patterns for reference materials
REFERENCE_URL_PATTERNS = [
    (r"confluence|wiki", "Confluence/Wiki page"),
    (r"loom\.com", "Loom recording"),
    (r"drive\.google|docs\.google", "Google Drive document"),
    (r"sharepoint|onedrive", "SharePoint/OneDrive document"),
    (r"figma\.com", "Figma design"),
    (r"miro\.com", "Miro board"),
    (r"youtube\.com|youtu\.be", "YouTube video"),
]


# =============================================================================
# SECTION 2 — REQUIRED FIELD VALIDATION (P1)
# =============================================================================

def _is_placeholder(value: str) -> bool:
    """Check if a string value is a placeholder or template text."""
    if not value or not value.strip():
        return True
    trimmed = value.strip()
    for pattern in PLACEHOLDER_PATTERNS:
        if re.match(pattern, trimmed, re.IGNORECASE):
            return True
    return False


def _is_generic_or_vague(value: str) -> bool:
    """Check if a value appears generic or vague."""
    if not value:
        return True
    trimmed = value.strip().lower()
    # Very short values are likely vague
    if len(trimmed) < 15:
        return True
    # Generic phrases
    generic_phrases = [
        "see attached", "as discussed", "per requirements",
        "update documentation", "fix documentation", "doc update",
        "as per", "refer to", "same as before",
    ]
    return any(phrase in trimmed for phrase in generic_phrases)


def validate_required_fields(issue: Dict, raw_fields: Dict) -> List[Dict]:
    """Validate all required TECDOC fields for presence and basic quality.

    Args:
        issue: Normalized issue dict from jira_handler
        raw_fields: Raw Jira API fields dict for additional field access

    Returns:
        List of field validation results with status (PASS/FAIL/WARNING)
    """
    results = []

    # Components
    components = issue.get("components", [])
    if not components:
        results.append({
            "field": "Components",
            "status": "FAIL",
            "finding": "No component assigned to this ticket.",
        })
    else:
        results.append({
            "field": "Components",
            "status": "PASS",
            "finding": f"Component(s) assigned: {', '.join(components)}",
        })

    # Fix Versions
    fix_versions = issue.get("fix_versions", [])
    if not fix_versions:
        results.append({
            "field": "Fix Versions",
            "status": "FAIL",
            "finding": "No fix version set for this ticket.",
        })
    else:
        results.append({
            "field": "Fix Versions",
            "status": "PASS",
            "finding": f"Fix version(s): {', '.join(fix_versions)}",
        })

    # User Doc Change (custom field — varies by instance)
    user_doc_change = _find_user_doc_change(issue, raw_fields)
    if user_doc_change is None:
        results.append({
            "field": "User Doc Change",
            "status": "FAIL",
            "finding": "User Doc Change field is not set (blank or default).",
        })
    elif user_doc_change.lower() in ("", "none", "n/a"):
        results.append({
            "field": "User Doc Change",
            "status": "WARNING",
            "finding": f"User Doc Change is set to '{user_doc_change}' — verify this is intentional.",
        })
    else:
        results.append({
            "field": "User Doc Change",
            "status": "PASS",
            "finding": f"User Doc Change: {user_doc_change}",
        })

    # Linked Issues
    linked_issues = raw_fields.get("issuelinks", [])
    if not linked_issues:
        results.append({
            "field": "Linked Issue",
            "status": "FAIL",
            "finding": "No linked issues found. A development ticket should be linked.",
        })
    else:
        link_count = len(linked_issues)
        results.append({
            "field": "Linked Issue",
            "status": "PASS",
            "finding": f"{link_count} linked issue(s) found.",
        })

    # Attachments
    attachments = raw_fields.get("attachment", [])
    if not attachments:
        results.append({
            "field": "Attachments",
            "status": "FAIL",
            "finding": "No attachments present. Consider attaching specs, screenshots, or design docs.",
        })
    else:
        results.append({
            "field": "Attachments",
            "status": "PASS",
            "finding": f"{len(attachments)} attachment(s) present.",
        })

    # Description
    description = issue.get("description", "")
    if not description or not description.strip():
        results.append({
            "field": "Description",
            "status": "FAIL",
            "finding": "Description is empty.",
        })
    elif _is_placeholder(description):
        results.append({
            "field": "Description",
            "status": "FAIL",
            "finding": "Description contains only placeholder text.",
        })
    elif _is_generic_or_vague(description):
        results.append({
            "field": "Description",
            "status": "WARNING",
            "finding": "Description appears generic or too brief for documentation work.",
        })
    else:
        word_count = len(description.split())
        results.append({
            "field": "Description",
            "status": "PASS",
            "finding": f"Description is populated ({word_count} words).",
        })

    return results


def _find_user_doc_change(issue: Dict, raw_fields: Dict) -> Optional[str]:
    """Locate the 'User Doc Change' custom field value.

    This field has different custom field IDs across Jira instances.
    We search by common field names and patterns.
    """
    # Check if already present in normalized issue (custom fields)
    for key, value in issue.items():
        if key.startswith("customfield_") and value:
            # Heuristic: check if the field name hints at doc change
            if isinstance(value, str) and value.lower() in (
                "yes", "no", "not required", "required", "tbd"
            ):
                return value

    # Check raw fields for known patterns
    for key, value in raw_fields.items():
        if not key.startswith("customfield_"):
            continue
        if value is None:
            continue
        if isinstance(value, dict):
            val = value.get("value", "")
            if val and val.lower() in (
                "yes", "no", "not required", "required", "tbd",
                "new topic", "update existing", "no change needed"
            ):
                return val
        elif isinstance(value, str):
            if value.lower() in (
                "yes", "no", "not required", "required", "tbd",
                "new topic", "update existing", "no change needed"
            ):
                return value

    return None


# =============================================================================
# SECTION 3 — FIELD CONTENT VALIDATION (P1)
# =============================================================================

def validate_field_content(issue: Dict, raw_fields: Dict) -> List[Dict]:
    """Validate the quality and accuracy of field content beyond presence.

    Returns:
        List of content validation findings (narrative per field)
    """
    findings = []

    # Components — check for mismatch with description
    components = issue.get("components", [])
    description = issue.get("description", "").lower()
    summary = issue.get("summary", "").lower()

    if components:
        # Flag if component seems mismatched
        component_text = " ".join(c.lower() for c in components)
        if description and len(description) > 50:
            # Simple heuristic: check if any component word appears in desc/summary
            component_words = set(component_text.split())
            desc_words = set(description.split() + summary.split())
            overlap = component_words & desc_words
            if not overlap and len(component_words) > 0:
                findings.append({
                    "field": "Components",
                    "severity": "warning",
                    "finding": (
                        f"Component '{', '.join(components)}' may not match the "
                        f"ticket content. Verify the component is correct."
                    ),
                })
            else:
                findings.append({
                    "field": "Components",
                    "severity": "ok",
                    "finding": f"Component(s) '{', '.join(components)}' appear consistent with ticket content.",
                })

    # Fix Versions — check for outdated or inconsistent versions
    fix_versions = issue.get("fix_versions", [])
    if fix_versions:
        findings.append({
            "field": "Fix Versions",
            "severity": "ok",
            "finding": f"Fix version(s) set: {', '.join(fix_versions)}.",
        })

    # User Doc Change — check for contradiction with description
    user_doc_change = _find_user_doc_change(issue, raw_fields)
    if user_doc_change:
        desc_lower = description.lower()
        # If set to "No" but description mentions user-facing changes
        user_facing_keywords = [
            "user", "screen", "field", "button", "menu", "dialog",
            "workflow", "interface", "ui", "page", "form", "option",
            "setting", "configuration", "navigation",
        ]
        has_user_facing = any(kw in desc_lower for kw in user_facing_keywords)
        if user_doc_change.lower() in ("no", "not required", "no change needed") and has_user_facing:
            findings.append({
                "field": "User Doc Change",
                "severity": "warning",
                "finding": (
                    f"User Doc Change is '{user_doc_change}' but the description "
                    f"mentions user-facing elements. Verify this is correct."
                ),
            })
        else:
            findings.append({
                "field": "User Doc Change",
                "severity": "ok",
                "finding": f"User Doc Change value '{user_doc_change}' appears consistent with ticket content.",
            })

    # Linked Issues — check link types and status
    linked_issues = raw_fields.get("issuelinks", [])
    if linked_issues:
        link_details = []
        for link in linked_issues:
            link_type = link.get("type", {}).get("name", "Unknown")
            # Check outward or inward issue
            linked_issue = link.get("outwardIssue") or link.get("inwardIssue")
            if linked_issue:
                linked_key = linked_issue.get("key", "Unknown")
                linked_status = linked_issue.get("fields", {}).get("status", {}).get("name", "Unknown")
                linked_summary = linked_issue.get("fields", {}).get("summary", "")
                direction = "outward" if link.get("outwardIssue") else "inward"
                link_type_desc = link.get("type", {}).get(f"{direction}", link_type)
                link_details.append({
                    "key": linked_key,
                    "type": link_type_desc,
                    "status": linked_status,
                    "summary": linked_summary[:80],
                })
        if link_details:
            detail_strs = [
                f"{d['key']} ({d['type']}, Status: {d['status']})"
                for d in link_details
            ]
            findings.append({
                "field": "Linked Issue",
                "severity": "ok",
                "finding": f"Linked issues: {'; '.join(detail_strs)}",
                "details": link_details,
            })

    # Attachments — list and classify
    attachments = raw_fields.get("attachment", [])
    if attachments:
        attachment_list = []
        for att in attachments:
            name = att.get("filename", "unknown")
            mime = att.get("mimeType", "")
            size = att.get("size", 0)
            attachment_list.append({
                "name": name,
                "type": mime,
                "size": size,
            })
        findings.append({
            "field": "Attachments",
            "severity": "ok",
            "finding": f"{len(attachments)} attachment(s): {', '.join(a['name'] for a in attachment_list[:5])}",
            "details": attachment_list,
        })

    # Description — validate substance
    if description and len(description) > 20:
        # Check if it's just a copy of the summary
        if description.strip().lower() == summary.strip():
            findings.append({
                "field": "Description",
                "severity": "warning",
                "finding": "Description is identical to the summary. Provide additional detail.",
            })
        else:
            findings.append({
                "field": "Description",
                "severity": "ok",
                "finding": "Description contains substantive content relevant to the ticket.",
            })

    return findings


# =============================================================================
# SECTION 4 — REFERENCE MATERIAL AVAILABILITY (P2)
# =============================================================================

def check_reference_materials(issue: Dict, raw_fields: Dict) -> Dict:
    """Check whether reference materials are linked or available.

    Returns:
        Dict with materials_found, gaps, and details
    """
    materials = []
    gaps = []

    # Check attachments for reference materials
    attachments = raw_fields.get("attachment", [])
    for att in attachments:
        filename = att.get("filename", "")
        mime = att.get("mimeType", "")
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        material_type = "Other"
        for category, extensions in REFERENCE_EXTENSIONS.items():
            if ext in extensions:
                material_type = category.capitalize()
                break

        materials.append({
            "name": filename,
            "type": material_type,
            "source": "Attachment",
            "accessible": True,
            "description": f"{material_type} file: {filename}",
        })

    # Check description for URLs that might be reference materials
    description = issue.get("description", "")
    urls_in_desc = re.findall(r'https?://[^\s<>"\']+', description)

    for url in urls_in_desc:
        url_type = "External URL"
        for pattern, label in REFERENCE_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                url_type = label
                break
        materials.append({
            "name": url[:80],
            "type": url_type,
            "source": "Description link",
            "accessible": None,  # Cannot verify without making HTTP requests
            "description": f"{url_type}: {url[:80]}",
        })

    # Check comments for reference materials
    comments = issue.get("comments", [])
    for comment in comments:
        body = comment.get("body", "")
        comment_urls = re.findall(r'https?://[^\s<>"\']+', body)
        for url in comment_urls:
            url_type = "External URL"
            for pattern, label in REFERENCE_URL_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    url_type = label
                    break
            materials.append({
                "name": url[:80],
                "type": url_type,
                "source": "Comment link",
                "accessible": None,
                "description": f"{url_type} found in comment: {url[:60]}",
            })

    # Identify gaps
    if not materials:
        gaps.append(
            "No reference materials found. Documentation input may be insufficient. "
            "Consider requesting design specs, screenshots, or workflow documentation."
        )
    else:
        has_docs = any(m["type"] in ("Documents", "Presentations") for m in materials)
        has_visual = any(m["type"] in ("Images", "Videos") for m in materials)
        if not has_docs:
            gaps.append("No design documents or specs attached. Consider requesting written specifications.")
        if not has_visual:
            gaps.append("No screenshots or recordings attached. Visual aids would help documentation work.")

    return {
        "materials": materials,
        "gaps": gaps,
        "count": len(materials),
    }


# =============================================================================
# SECTION 5 — CROSS-REFERENCE WITH RELATED DEVELOPMENT TICKET (P2)
# =============================================================================

def cross_reference_dev_ticket(issue: Dict, raw_fields: Dict) -> Dict:
    """Cross-reference with linked development tickets.

    Compares fix versions, components, and status consistency.

    Returns:
        Dict with dev_ticket info, discrepancies, and accessibility status
    """
    linked_issues = raw_fields.get("issuelinks", [])
    if not linked_issues:
        return {
            "found": False,
            "message": "No linked development tickets found.",
            "discrepancies": [],
            "dev_tickets": [],
        }

    dev_tickets = []
    discrepancies = []

    for link in linked_issues:
        linked_issue = link.get("outwardIssue") or link.get("inwardIssue")
        if not linked_issue:
            continue

        linked_key = linked_issue.get("key", "")
        linked_fields = linked_issue.get("fields", {})
        linked_status = linked_fields.get("status", {}).get("name", "Unknown")
        linked_status_cat = linked_fields.get("status", {}).get(
            "statusCategory", {}
        ).get("name", "Unknown")
        linked_fix_versions = [
            v.get("name", "") for v in (linked_fields.get("fixVersions") or [])
        ]
        linked_components = [
            c.get("name", "") for c in (linked_fields.get("components") or [])
        ]
        linked_summary = linked_fields.get("summary", "")

        dev_ticket_info = {
            "key": linked_key,
            "summary": linked_summary[:100],
            "status": linked_status,
            "status_category": linked_status_cat,
            "fix_versions": linked_fix_versions,
            "components": linked_components,
            "accessible": True,
        }
        dev_tickets.append(dev_ticket_info)

        # Compare fix versions
        source_versions = set(issue.get("fix_versions", []))
        linked_versions = set(linked_fix_versions)
        if source_versions and linked_versions and source_versions != linked_versions:
            discrepancies.append({
                "type": "fix_version_mismatch",
                "message": (
                    f"Fix version mismatch: TECDOC has {list(source_versions)}, "
                    f"linked {linked_key} has {list(linked_versions)}."
                ),
                "severity": "high",
            })

        # Compare components
        source_components = set(issue.get("components", []))
        linked_comps = set(linked_components)
        if source_components and linked_comps and source_components != linked_comps:
            discrepancies.append({
                "type": "component_mismatch",
                "message": (
                    f"Component mismatch: TECDOC has {list(source_components)}, "
                    f"linked {linked_key} has {list(linked_comps)}."
                ),
                "severity": "medium",
            })

        # Check status consistency
        source_status_cat = issue.get("status_category", "Unknown")
        if linked_status_cat == "Done" and source_status_cat != "Done":
            discrepancies.append({
                "type": "status_inconsistency",
                "message": (
                    f"Development ticket {linked_key} is Done but TECDOC ticket "
                    f"is still '{issue.get('status', 'Unknown')}'. "
                    f"Documentation work may be pending."
                ),
                "severity": "medium",
            })

    return {
        "found": len(dev_tickets) > 0,
        "message": f"Found {len(dev_tickets)} linked development ticket(s).",
        "discrepancies": discrepancies,
        "dev_tickets": dev_tickets,
    }


# =============================================================================
# SECTION 6 — INPUT SUFFICIENCY ASSESSMENT (P2)
# =============================================================================

def assess_input_sufficiency(issue: Dict, raw_fields: Dict) -> List[Dict]:
    """Assess whether inputs are sufficient for documentation work.

    Evaluates: Clarity, Completeness, Relevance, Actionability.

    Returns:
        List of dimension assessments with rating, finding, recommendation
    """
    description = issue.get("description", "")
    summary = issue.get("summary", "")
    desc_lower = description.lower()
    assessments = []

    # --- Clarity ---
    clarity_score = 0
    clarity_issues = []
    if description and len(description) > 100:
        clarity_score += 2
    elif description and len(description) > 30:
        clarity_score += 1
        clarity_issues.append("Description is brief — may lack detail for writers.")
    else:
        clarity_issues.append("Description is too short or missing for a writer to understand the change.")

    # Check for clear explanation of what/why
    what_keywords = ["change", "add", "remove", "update", "modify", "new", "create", "enable", "disable"]
    why_keywords = ["because", "so that", "in order to", "to allow", "to support", "requirement"]
    has_what = any(kw in desc_lower for kw in what_keywords)
    has_why = any(kw in desc_lower for kw in why_keywords)
    if has_what:
        clarity_score += 1
    else:
        clarity_issues.append("Description does not clearly state what changed.")
    if has_why:
        clarity_score += 1

    if clarity_score >= 3:
        clarity_rating = "Sufficient"
    elif clarity_score >= 2:
        clarity_rating = "Partially Sufficient"
    else:
        clarity_rating = "Insufficient"

    assessments.append({
        "dimension": "Clarity",
        "rating": clarity_rating,
        "finding": (
            "The feature/change is described clearly enough for documentation."
            if clarity_rating == "Sufficient"
            else "; ".join(clarity_issues) if clarity_issues
            else "Clarity could be improved."
        ),
        "recommendation": (
            "" if clarity_rating == "Sufficient"
            else "Provide a clear explanation of what changed and why in the description."
        ),
    })

    # --- Completeness ---
    completeness_score = 0
    completeness_issues = []
    completeness_aspects = {
        "UI changes": ["screen", "field", "button", "menu", "dialog", "page", "form", "ui", "interface"],
        "Workflow changes": ["workflow", "process", "step", "procedure", "flow", "sequence"],
        "New fields": ["field", "column", "parameter", "option", "setting", "attribute"],
        "Removed features": ["remove", "deprecat", "retire", "eliminat", "drop", "sunset"],
    }
    covered_aspects = []
    for aspect, keywords in completeness_aspects.items():
        if any(kw in desc_lower for kw in keywords):
            covered_aspects.append(aspect)
            completeness_score += 1

    if completeness_score >= 3:
        completeness_rating = "Sufficient"
    elif completeness_score >= 2:
        completeness_rating = "Partially Sufficient"
    else:
        completeness_rating = "Insufficient"
        completeness_issues.append(
            "The description does not cover enough aspects of the change "
            "(UI changes, workflow changes, new fields, removed features)."
        )

    assessments.append({
        "dimension": "Completeness",
        "rating": completeness_rating,
        "finding": (
            f"Covered aspects: {', '.join(covered_aspects)}."
            if covered_aspects
            else "No specific change aspects (UI, workflow, fields, removals) are described."
        ),
        "recommendation": (
            "" if completeness_rating == "Sufficient"
            else "Describe all affected areas: UI changes, workflow changes, new/modified fields, and any removed features."
        ),
    })

    # --- Relevance ---
    relevance_rating = "Sufficient"
    relevance_finding = "Content appears relevant to the ticket summary."
    relevance_recommendation = ""

    if description and summary:
        # Check if description is related to summary
        summary_words = set(summary.lower().split())
        desc_words = set(desc_lower.split())
        # Remove stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or"}
        summary_words -= stop_words
        desc_words -= stop_words
        overlap = summary_words & desc_words
        if summary_words and len(overlap) / len(summary_words) < 0.2:
            relevance_rating = "Partially Sufficient"
            relevance_finding = "Description content has low overlap with the ticket summary — may describe something unrelated."
            relevance_recommendation = "Ensure the description directly relates to the ticket summary and describes the same change."
    elif not description:
        relevance_rating = "Insufficient"
        relevance_finding = "No description to assess relevance."
        relevance_recommendation = "Add a description that explains the change described in the summary."

    assessments.append({
        "dimension": "Relevance",
        "rating": relevance_rating,
        "finding": relevance_finding,
        "recommendation": relevance_recommendation,
    })

    # --- Actionability ---
    actionability_score = 0
    actionability_issues = []

    # Can a writer begin drafting?
    if description and len(description) > 100:
        actionability_score += 1
    if issue.get("fix_versions"):
        actionability_score += 1
    if issue.get("components"):
        actionability_score += 1
    attachments = raw_fields.get("attachment", [])
    if attachments:
        actionability_score += 1

    # Check for specific actionable details
    actionable_keywords = ["navigate to", "click", "select", "enter", "go to", "open", "access"]
    if any(kw in desc_lower for kw in actionable_keywords):
        actionability_score += 1

    if actionability_score >= 4:
        actionability_rating = "Sufficient"
    elif actionability_score >= 2:
        actionability_rating = "Partially Sufficient"
        actionability_issues.append("Some supporting details (attachments, navigation paths) are missing.")
    else:
        actionability_rating = "Insufficient"
        actionability_issues.append("Critical details are missing — a writer cannot begin drafting documentation.")

    assessments.append({
        "dimension": "Actionability",
        "rating": actionability_rating,
        "finding": (
            "Sufficient information available for a writer to begin documentation."
            if actionability_rating == "Sufficient"
            else "; ".join(actionability_issues) if actionability_issues
            else "Some supporting details are missing."
        ),
        "recommendation": (
            "" if actionability_rating == "Sufficient"
            else "Provide navigation paths, field descriptions, screenshots, and step-by-step workflow to enable documentation drafting."
        ),
    })

    return assessments


# =============================================================================
# SECTION 7 — CORRECTION SUGGESTIONS (P3)
# =============================================================================

def generate_corrections(
    issue: Dict,
    raw_fields: Dict,
    field_validation: List[Dict],
    content_validation: List[Dict],
    reference_materials: Dict,
) -> List[Dict]:
    """Generate correction suggestions for flagged fields.

    Returns:
        List of suggestion dicts with field, suggestion, and priority
    """
    corrections = []
    description = issue.get("description", "")
    summary = issue.get("summary", "")

    for result in field_validation:
        if result["status"] in ("FAIL", "WARNING"):
            field = result["field"]

            if field == "Components":
                # Suggest component based on summary keywords
                suggestion = _suggest_component(summary, description)
                corrections.append({
                    "field": "Components",
                    "suggestion": suggestion,
                    "priority": "High",
                })

            elif field == "Fix Versions":
                corrections.append({
                    "field": "Fix Versions",
                    "suggestion": (
                        "Set the Fix Version to the target release for this change. "
                        "Check related development tickets for the correct version."
                    ),
                    "priority": "High",
                })

            elif field == "User Doc Change":
                # Suggest based on description content
                user_facing_keywords = [
                    "user", "screen", "field", "button", "menu",
                    "workflow", "interface", "ui", "page",
                ]
                has_user_facing = any(
                    kw in description.lower() for kw in user_facing_keywords
                )
                suggested_value = "Yes" if has_user_facing else "Review needed"
                corrections.append({
                    "field": "User Doc Change",
                    "suggestion": (
                        f"Suggested value: '{suggested_value}'. "
                        f"The description {'mentions' if has_user_facing else 'does not mention'} "
                        f"user-facing changes."
                    ),
                    "priority": "High",
                })

            elif field == "Linked Issue":
                corrections.append({
                    "field": "Linked Issue",
                    "suggestion": (
                        "Link the related development ticket (use 'is documented by' or "
                        "'relates to' link type). This enables cross-reference validation."
                    ),
                    "priority": "Medium",
                })

            elif field == "Attachments":
                corrections.append({
                    "field": "Attachments",
                    "suggestion": (
                        "Attach supporting materials: screenshots of affected screens, "
                        "design specifications, or workflow diagrams."
                    ),
                    "priority": "Medium",
                })

            elif field == "Description":
                corrections.append({
                    "field": "Description",
                    "suggestion": (
                        "The description should include: what changed, why it changed, "
                        "which screens/fields are affected, the user workflow, and any "
                        "prerequisites or configuration needed."
                    ),
                    "priority": "High",
                })

    # Reference material suggestions
    if reference_materials.get("gaps"):
        for gap in reference_materials["gaps"]:
            corrections.append({
                "field": "Reference Materials",
                "suggestion": gap,
                "priority": "Medium",
            })

    return corrections


def _suggest_component(summary: str, description: str) -> str:
    """Suggest a component based on ticket content keywords."""
    text = f"{summary} {description}".lower()

    component_hints = {
        "Financials": ["finance", "gl", "general ledger", "ap", "ar", "billing", "invoice", "payment"],
        "Supply Chain": ["supply chain", "inventory", "warehouse", "procurement", "purchasing", "shipment"],
        "HCM": ["hr", "human resource", "payroll", "employee", "workforce", "talent", "recruit"],
        "CRM": ["crm", "customer", "sales", "opportunity", "lead", "campaign", "marketing"],
        "EAM": ["asset", "maintenance", "work order", "equipment", "facility"],
        "PLM": ["product lifecycle", "engineering", "bom", "bill of material", "revision"],
        "WMS": ["warehouse management", "wms", "picking", "putaway", "receiving"],
        "CloudSuite": ["cloudsuite", "cloud suite", "saas", "multi-tenant"],
    }

    for component, keywords in component_hints.items():
        if any(kw in text for kw in keywords):
            return f"Suggested component: '{component}' (based on ticket content mentioning related keywords)."

    return "Unable to suggest a specific component. Review the ticket content and assign the appropriate product/module component."


# =============================================================================
# SECTION 8 — OUTPUT FORMAT & MAIN ANALYSIS FUNCTION
# =============================================================================

def _determine_readiness(
    field_validation: List[Dict],
    sufficiency: List[Dict],
    discrepancies: List[Dict],
) -> Dict:
    """Determine overall documentation readiness.

    Returns:
        Dict with verdict, summary text
    """
    fail_count = sum(1 for r in field_validation if r["status"] == "FAIL")
    warning_count = sum(1 for r in field_validation if r["status"] == "WARNING")
    insufficient_count = sum(1 for a in sufficiency if a["rating"] == "Insufficient")
    partial_count = sum(1 for a in sufficiency if a["rating"] == "Partially Sufficient")
    high_discrepancies = sum(1 for d in discrepancies if d.get("severity") == "high")

    if fail_count == 0 and insufficient_count == 0 and high_discrepancies == 0:
        if warning_count == 0 and partial_count == 0:
            verdict = "Yes"
            summary = "All required fields are populated and content is sufficient for documentation work."
        else:
            verdict = "Conditional"
            summary = (
                f"The ticket is mostly ready but has {warning_count} warning(s) and "
                f"{partial_count} partially sufficient area(s). "
                "A writer can begin work but may need to follow up on flagged items."
            )
    elif fail_count <= 2 and insufficient_count <= 1:
        verdict = "Conditional"
        issues = []
        if fail_count:
            issues.append(f"{fail_count} missing required field(s)")
        if insufficient_count:
            issues.append(f"{insufficient_count} insufficient input area(s)")
        if high_discrepancies:
            issues.append(f"{high_discrepancies} critical discrepancy/discrepancies")
        summary = (
            f"The ticket has {', '.join(issues)}. "
            "Address the flagged items before documentation work begins, "
            "or proceed with caveats."
        )
    else:
        verdict = "No"
        summary = (
            f"The ticket is not ready for documentation: {fail_count} required field(s) missing, "
            f"{insufficient_count} input area(s) insufficient. "
            "The reporter/developer must provide the missing information before a writer can proceed."
        )

    return {"verdict": verdict, "summary": summary}


# =============================================================================
# MAIN PUBLIC API
# =============================================================================

def analyze_ticket(issue_key: str) -> Dict:
    """Perform full TECDOC ticket analysis.

    This is the main entry point. Fetches the ticket from Jira,
    runs all validation sections, and returns a structured report.

    Args:
        issue_key: Jira issue key (e.g., 'TECDOC-1234')

    Returns:
        Structured analysis report dict

    Raises:
        RuntimeError: If Jira is unreachable or ticket not found
    """
    start_time = time.time()
    logger.info(f"Starting TECDOC ticket analysis: {issue_key}")

    # --- SECTION 1: Access ticket ---
    try:
        # Fetch full issue details (raw) for field-level access
        raw_result = jira_handler._make_request(
            f"/rest/api/3/issue/{issue_key}",
            params={"fields": "*all", "expand": "renderedFields,names"},
        )
    except RuntimeError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            return {
                "success": False,
                "error": f"Ticket {issue_key} not found. Check the ticket key and try again.",
                "error_code": "TICKET_NOT_FOUND",
            }
        elif "authentication" in error_msg.lower():
            return {
                "success": False,
                "error": "Jira authentication failed. Check your credentials in Settings.",
                "error_code": "AUTH_FAILED",
            }
        elif "connect" in error_msg.lower():
            return {
                "success": False,
                "error": f"Cannot connect to Jira. Check your network and try again. ({error_msg})",
                "error_code": "CONNECTION_ERROR",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to access ticket: {error_msg}",
                "error_code": "JIRA_ERROR",
            }

    # Normalize for our internal use
    raw_fields = raw_result.get("fields", {})
    issue = jira_handler._normalize_issue(raw_result, full_detail=True)

    # Fetch comments separately
    try:
        comments_result = jira_handler._make_request(
            f"/rest/api/3/issue/{issue_key}/comment",
            params={"maxResults": 20, "orderBy": "-created"},
        )
        issue["comments"] = [
            {
                "id": c.get("id"),
                "author": jira_handler._get_display_name(c.get("author")),
                "body": jira_handler._extract_text_from_adf(c.get("body", {})),
                "created": c.get("created"),
            }
            for c in comments_result.get("comments", [])
        ]
    except Exception:
        issue["comments"] = []

    # --- SECTION 2: Required Field Validation ---
    field_validation = validate_required_fields(issue, raw_fields)

    # --- SECTION 3: Field Content Validation ---
    content_validation = validate_field_content(issue, raw_fields)

    # --- SECTION 4: Reference Material Availability ---
    reference_materials = check_reference_materials(issue, raw_fields)

    # --- SECTION 5: Cross-Reference with Development Ticket ---
    cross_reference = cross_reference_dev_ticket(issue, raw_fields)

    # --- SECTION 6: Input Sufficiency Assessment ---
    sufficiency = assess_input_sufficiency(issue, raw_fields)

    # --- SECTION 7: Correction Suggestions ---
    corrections = generate_corrections(
        issue, raw_fields, field_validation, content_validation, reference_materials
    )

    # --- Determine Overall Readiness ---
    readiness = _determine_readiness(
        field_validation, sufficiency, cross_reference.get("discrepancies", [])
    )

    # --- Performance tracking ---
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(f"TECDOC analysis completed: {issue_key}, duration={duration_ms}ms")

    # --- SECTION 8: Build structured output ---
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    report = {
        "success": True,
        "ticket_key": issue_key,
        "ticket_summary": issue.get("summary", ""),
        "analysis_timestamp": timestamp,
        "duration_ms": duration_ms,

        # Section 2 — Required Field Validation
        "field_validation": field_validation,

        # Section 3 — Field Content Validation
        "content_validation": content_validation,

        # Section 4 — Reference Materials
        "reference_materials": reference_materials,

        # Section 5 — Development Ticket Cross-Reference
        "cross_reference": cross_reference,

        # Section 6 — Input Sufficiency
        "input_sufficiency": sufficiency,

        # Section 7 — Correction Suggestions
        "corrections": corrections,

        # Overall Readiness
        "readiness": readiness,

        # Summary counts for UI
        "summary_counts": {
            "pass": sum(1 for r in field_validation if r["status"] == "PASS"),
            "fail": sum(1 for r in field_validation if r["status"] == "FAIL"),
            "warning": sum(1 for r in field_validation if r["status"] == "WARNING"),
            "sufficient": sum(1 for a in sufficiency if a["rating"] == "Sufficient"),
            "partial": sum(1 for a in sufficiency if a["rating"] == "Partially Sufficient"),
            "insufficient": sum(1 for a in sufficiency if a["rating"] == "Insufficient"),
            "discrepancies": len(cross_reference.get("discrepancies", [])),
            "materials": reference_materials.get("count", 0),
            "corrections": len(corrections),
        },
    }

    return report


def analyze_ticket_chat(issue_key: str, question: str = "") -> Dict:
    """Chat-based ticket analysis — returns formatted analysis or answers questions.

    When no question is provided, returns the full structured analysis.
    When a question is provided, uses AI to answer about the ticket.

    Args:
        issue_key: Jira issue key
        question: Optional user question about the ticket

    Returns:
        Dict with success status and response text
    """
    # If just asking for analysis, run the full pipeline
    if not question or question.strip().lower() in (
        "analyze", "analyze this ticket", "run analysis", "check readiness",
        "validate", "assess", "review",
    ):
        report = analyze_ticket(issue_key)
        if not report.get("success"):
            return report
        # Format as chat-friendly text
        return {
            "success": True,
            "response": _format_report_as_text(report),
            "report": report,
        }

    # For specific questions, fetch ticket and use AI
    try:
        issue = jira_handler.fetch_issue_detail(issue_key)
    except RuntimeError as e:
        return {
            "success": False,
            "error": str(e),
        }

    # Build context for AI
    ticket_context = jira_summarizer._format_ticket_for_llm(issue)
    prompt = (
        f"The user is asking about TECDOC ticket {issue_key}. "
        f"Answer their question based on the ticket data below.\n\n"
        f"User question: {question}\n\n"
        f"Ticket data:\n{ticket_context}"
    )

    try:
        response = jira_summarizer._call_llm(
            "You are a documentation analyst helping writers understand JIRA tickets. "
            "Answer concisely and factually based on the ticket data provided.",
            prompt,
            max_tokens=1000,
        )
        return {
            "success": True,
            "response": response,
        }
    except RuntimeError as e:
        # Fallback: return basic ticket info
        return {
            "success": True,
            "response": (
                f"AI is unavailable ({str(e)}). Here's the ticket summary:\n\n"
                f"**{issue_key}**: {issue.get('summary', 'N/A')}\n"
                f"**Status**: {issue.get('status', 'N/A')}\n"
                f"**Priority**: {issue.get('priority', 'N/A')}\n"
                f"**Description**: {issue.get('description', 'N/A')[:300]}"
            ),
        }


def _format_report_as_text(report: Dict) -> str:
    """Format a structured analysis report as readable text for chat display."""
    lines = []
    lines.append(f"**Ticket:** {report['ticket_key']} — {report['ticket_summary']}")
    lines.append(f"**Analysis completed:** {report['analysis_timestamp']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Required Field Validation
    lines.append("### 1. Required Field Validation")
    lines.append("")
    lines.append("| Field | Status | Finding |")
    lines.append("|---|---|---|")
    for fv in report["field_validation"]:
        status_icon = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️"}.get(fv["status"], "")
        lines.append(f"| {fv['field']} | {status_icon} {fv['status']} | {fv['finding']} |")
    lines.append("")

    # 2. Field Content Validation
    lines.append("### 2. Field Content Validation")
    lines.append("")
    for cv in report["content_validation"]:
        severity_icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}.get(cv["severity"], "")
        lines.append(f"- {severity_icon} **{cv['field']}**: {cv['finding']}")
    if not report["content_validation"]:
        lines.append("- No additional content issues found.")
    lines.append("")

    # 3. Reference Materials
    lines.append("### 3. Reference Materials")
    lines.append("")
    ref = report["reference_materials"]
    if ref["materials"]:
        for mat in ref["materials"]:
            accessible = "✅" if mat.get("accessible") else "❓"
            lines.append(f"- {accessible} [{mat['type']}] {mat['name']} (Source: {mat['source']})")
    else:
        lines.append("- No reference materials found.")
    if ref["gaps"]:
        lines.append("")
        lines.append("**Gaps:**")
        for gap in ref["gaps"]:
            lines.append(f"- ⚠️ {gap}")
    lines.append("")

    # 4. Development Ticket Cross-Reference
    lines.append("### 4. Development Ticket Cross-Reference")
    lines.append("")
    xref = report["cross_reference"]
    lines.append(f"- {xref['message']}")
    if xref["dev_tickets"]:
        for dt in xref["dev_tickets"]:
            lines.append(f"  - **{dt['key']}**: {dt['summary']} (Status: {dt['status']})")
    if xref["discrepancies"]:
        lines.append("")
        lines.append("**Discrepancies:**")
        for disc in xref["discrepancies"]:
            lines.append(f"- ⚠️ {disc['message']}")
    lines.append("")

    # 5. Input Sufficiency Assessment
    lines.append("### 5. Input Sufficiency Assessment")
    lines.append("")
    lines.append("| Dimension | Rating | Finding | Recommendation |")
    lines.append("|---|---|---|---|")
    for sa in report["input_sufficiency"]:
        rating_icon = {"Sufficient": "✅", "Partially Sufficient": "⚠️", "Insufficient": "❌"}.get(sa["rating"], "")
        rec = sa["recommendation"] or "—"
        lines.append(f"| {sa['dimension']} | {rating_icon} {sa['rating']} | {sa['finding']} | {rec} |")
    lines.append("")

    # 6. Correction Suggestions
    if report["corrections"]:
        lines.append("### 6. Correction Suggestions")
        lines.append("")
        for corr in report["corrections"]:
            lines.append(f"- **{corr['field']}** ({corr['priority']}): {corr['suggestion']}")
        lines.append("")

    # 7. Overall Readiness
    lines.append("### 7. Overall Readiness")
    lines.append("")
    readiness = report["readiness"]
    verdict_icon = {"Yes": "✅", "No": "❌", "Conditional": "⚠️"}.get(readiness["verdict"], "")
    lines.append(f"- **Ready for documentation:** {verdict_icon} {readiness['verdict']}")
    lines.append(f"- **Summary:** {readiness['summary']}")
    lines.append("")

    # Performance
    lines.append(f"*Analysis completed in {report['duration_ms']}ms*")

    return "\n".join(lines)


# =============================================================================
# QUICK SUMMARY FOR DASHBOARD
# =============================================================================

def get_ticket_quick_summary(issue_key: str) -> Dict:
    """Get a quick summary of a ticket for dashboard display.

    Lighter-weight than full analysis — just fetches and summarizes.

    Returns:
        Dict with key fields for display
    """
    try:
        issue = jira_handler.fetch_issue_detail(issue_key)
        return {
            "success": True,
            "key": issue.get("key"),
            "summary": issue.get("summary"),
            "status": issue.get("status"),
            "priority": issue.get("priority"),
            "issue_type": issue.get("issue_type"),
            "assignee": issue.get("assignee"),
            "fix_versions": issue.get("fix_versions", []),
            "components": issue.get("components", []),
            "description_preview": issue.get("description", "")[:200],
        }
    except RuntimeError as e:
        return {
            "success": False,
            "error": str(e),
        }
