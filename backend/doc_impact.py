"""
Documentation Impact Assessment Engine.

Parses Chancellor/Cursitor validation session output (JSON files) and
identifies which documentation topics may need updating based on product
changes tracked in Jira tickets.

Input: List of validation JSON objects (from Chancellor sessions)
Output: Impact assessment with categorized topics, severity, and recommendations

No credentials needed — works entirely from imported JSON data.
"""

import re
import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Documentation areas mapped to common keywords in ticket content
DOC_AREA_KEYWORDS = {
    "Configuration & Setup": [
        "config", "configuration", "setup", "setting", "parameter", "property",
        "enable", "disable", "toggle", "flag", "option", "preference",
        "install", "deploy", "initialize", "provision",
    ],
    "User Guide & Procedures": [
        "workflow", "process", "procedure", "step", "task", "action",
        "screen", "page", "form", "dialog", "wizard", "menu",
        "click", "select", "navigate", "button", "field",
    ],
    "API & Integration": [
        "api", "endpoint", "rest", "soap", "webhook", "integration",
        "request", "response", "payload", "json", "xml", "schema",
        "authentication", "token", "oauth", "service",
    ],
    "Administration": [
        "admin", "administrator", "permission", "role", "security",
        "user management", "access", "privilege", "policy",
        "backup", "restore", "maintenance", "monitor",
    ],
    "Release Notes": [
        "new feature", "enhancement", "improvement", "fix", "bug",
        "release", "version", "upgrade", "migration", "deprecat",
        "breaking change", "backward", "compatibility",
    ],
    "Troubleshooting": [
        "error", "issue", "problem", "fail", "exception", "crash",
        "workaround", "resolution", "debug", "log", "trace",
        "timeout", "performance", "slow",
    ],
    "Data & Reports": [
        "report", "query", "data", "export", "import", "csv",
        "dashboard", "analytics", "metric", "kpi", "chart",
        "database", "table", "field", "column", "record",
    ],
    "Concepts & Overview": [
        "overview", "concept", "architecture", "design", "module",
        "component", "feature", "capability", "function",
        "introduction", "about", "what is",
    ],
}

# Impact severity thresholds
SEVERITY_THRESHOLDS = {
    "critical": 0.8,   # Strong match — definitely needs update
    "high": 0.6,       # Likely needs update
    "medium": 0.4,     # May need update
    "low": 0.2,        # Minor or tangential
}

# Infor product identifiers
INFOR_PRODUCTS = [
    "LN", "M3", "Infor OS", "WMS", "IFSM", "DEPM", "CSI", "SyteLine",
    "Factory Track", "Landmark", "SCP", "Birst", "ION", "Ming.le",
    "CloudSuite", "Lawson", "Expense Management", "HCM", "XA",
    "d/EPM", "Infor Nexus", "GT Nexus", "VISUAL",
]


# =============================================================================
# PARSING CHANCELLOR SESSION DATA
# =============================================================================

def parse_validation_json(data):
    """Parse a single Chancellor validation JSON object.

    Handles both the raw Cursitor output format and the Chancellor-assessed format.

    Returns normalized ticket dict with:
    - key, summary, status, priority, fix_version
    - description, overview_of_change, detailed_description
    - relevance_verdict, sufficiency_verdict
    - field_validations (list of {field, status, value})
    - product (detected Infor product)
    """
    if not data or not isinstance(data, dict):
        return None

    # Handle nested structures (Chancellor wraps Cursitor output)
    ticket_data = data.get("ticket", data)
    validation = data.get("validation", data.get("field_validations", {}))

    # Extract core fields
    key = (ticket_data.get("key") or data.get("key") or
           data.get("ticket_key") or "UNKNOWN")
    summary = (ticket_data.get("summary") or
               ticket_data.get("fields", {}).get("summary", "") or
               data.get("summary", ""))
    description = (ticket_data.get("description") or
                   ticket_data.get("fields", {}).get("description", "") or
                   data.get("description", ""))

    # Extract change-related fields (Chancellor custom fields)
    overview = (ticket_data.get("overview_of_change") or
                ticket_data.get("fields", {}).get("overview_of_change", "") or
                data.get("overview_of_change", ""))
    detailed = (ticket_data.get("detailed_description") or
                ticket_data.get("fields", {}).get("detailed_description", "") or
                data.get("detailed_description", ""))

    # Extract metadata
    status = (ticket_data.get("status") or
              ticket_data.get("fields", {}).get("status", {}).get("name", "") or
              data.get("status", ""))
    priority = (ticket_data.get("priority") or
                ticket_data.get("fields", {}).get("priority", {}).get("name", "") or
                data.get("priority", ""))
    fix_version = ""
    fv = ticket_data.get("fix_version") or ticket_data.get("fields", {}).get("fixVersions", [])
    if isinstance(fv, list) and fv:
        fix_version = fv[0].get("name", str(fv[0])) if isinstance(fv[0], dict) else str(fv[0])
    elif isinstance(fv, str):
        fix_version = fv

    # Extract verdicts (Chancellor assessment)
    relevance = data.get("relevance_verdict") or data.get("relevance", "")
    sufficiency = data.get("sufficiency_verdict") or data.get("sufficiency", "")

    # Detect product from content
    all_text = f"{summary} {description} {overview} {detailed}".lower()
    product = _detect_product(all_text)

    # Extract field validations
    field_results = []
    if isinstance(validation, dict):
        for field_name, field_data in validation.items():
            if isinstance(field_data, dict):
                field_results.append({
                    "field": field_name,
                    "status": field_data.get("status", field_data.get("result", "unknown")),
                    "value": field_data.get("value", ""),
                    "message": field_data.get("message", field_data.get("guidance", "")),
                })
    elif isinstance(validation, list):
        for item in validation:
            if isinstance(item, dict):
                field_results.append({
                    "field": item.get("field", item.get("name", "")),
                    "status": item.get("status", item.get("result", "unknown")),
                    "value": item.get("value", ""),
                    "message": item.get("message", item.get("guidance", "")),
                })

    return {
        "key": key,
        "summary": summary,
        "description": description,
        "overview_of_change": overview,
        "detailed_description": detailed,
        "status": status,
        "priority": priority,
        "fix_version": fix_version,
        "relevance_verdict": relevance,
        "sufficiency_verdict": sufficiency,
        "field_validations": field_results,
        "product": product,
    }


def _detect_product(text):
    """Detect Infor product name from text content."""
    text_lower = text.lower()
    for product in INFOR_PRODUCTS:
        if product.lower() in text_lower:
            return product
    return "Unknown"


# =============================================================================
# IMPACT ASSESSMENT
# =============================================================================

def assess_impact(tickets):
    """Assess documentation impact from a list of parsed ticket dicts.

    Args:
        tickets: List of normalized ticket dicts (from parse_validation_json)

    Returns:
        dict with:
        - summary: overall impact summary stats
        - impacted_areas: list of {area, severity, tickets, recommendations}
        - ticket_impacts: per-ticket impact details
        - timeline: grouped by fix_version
    """
    if not tickets:
        return {
            "summary": {"total_tickets": 0, "relevant": 0, "impacted_areas": 0},
            "impacted_areas": [],
            "ticket_impacts": [],
            "timeline": {},
        }

    # Analyze each ticket
    ticket_impacts = []
    area_hits = defaultdict(list)  # area -> list of ticket impacts

    for ticket in tickets:
        if not ticket:
            continue

        # Combine all text for analysis
        change_text = " ".join(filter(None, [
            ticket.get("summary", ""),
            ticket.get("overview_of_change", ""),
            ticket.get("detailed_description", ""),
            ticket.get("description", ""),
        ]))

        if not change_text.strip():
            continue

        # Identify impacted documentation areas
        areas = _identify_impacted_areas(change_text)

        # Determine overall impact severity for this ticket
        severity = _compute_ticket_severity(ticket, areas)

        # Generate recommendations
        recommendations = _generate_recommendations(ticket, areas)

        impact = {
            "key": ticket["key"],
            "summary": ticket["summary"],
            "product": ticket["product"],
            "fix_version": ticket["fix_version"],
            "severity": severity,
            "impacted_areas": [a["area"] for a in areas],
            "area_details": areas,
            "recommendations": recommendations,
            "relevance": ticket.get("relevance_verdict", ""),
            "sufficiency": ticket.get("sufficiency_verdict", ""),
        }
        ticket_impacts.append(impact)

        # Accumulate area hits
        for area_info in areas:
            area_hits[area_info["area"]].append({
                "key": ticket["key"],
                "summary": ticket["summary"],
                "score": area_info["score"],
                "severity": area_info["severity"],
            })

    # Build impacted areas summary
    impacted_areas = []
    for area, hits in sorted(area_hits.items(), key=lambda x: -len(x[1])):
        max_severity = max(hits, key=lambda h: h["score"])["severity"]
        impacted_areas.append({
            "area": area,
            "severity": max_severity,
            "ticket_count": len(hits),
            "tickets": hits,
            "recommendation": _area_recommendation(area, len(hits)),
        })

    # Group by fix_version for timeline
    timeline = defaultdict(list)
    for ti in ticket_impacts:
        version = ti["fix_version"] or "Unscheduled"
        timeline[version].append({
            "key": ti["key"],
            "summary": ti["summary"],
            "severity": ti["severity"],
        })

    # Count relevant tickets
    relevant_count = sum(
        1 for t in tickets
        if t and t.get("relevance_verdict", "").lower() not in ["not relevant", "irrelevant", "no"]
    )

    return {
        "summary": {
            "total_tickets": len(tickets),
            "relevant": relevant_count,
            "impacted_areas": len(impacted_areas),
            "critical": sum(1 for ti in ticket_impacts if ti["severity"] == "critical"),
            "high": sum(1 for ti in ticket_impacts if ti["severity"] == "high"),
            "medium": sum(1 for ti in ticket_impacts if ti["severity"] == "medium"),
            "low": sum(1 for ti in ticket_impacts if ti["severity"] == "low"),
        },
        "impacted_areas": impacted_areas,
        "ticket_impacts": ticket_impacts,
        "timeline": dict(timeline),
    }


def _identify_impacted_areas(text):
    """Identify which documentation areas are impacted by the change text.

    Returns list of {area, score, severity, matched_keywords}.
    """
    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))
    areas = []

    for area, keywords in DOC_AREA_KEYWORDS.items():
        matched = []
        for kw in keywords:
            if ' ' in kw:
                # Multi-word keyword — check substring
                if kw.lower() in text_lower:
                    matched.append(kw)
            else:
                if kw.lower() in words:
                    matched.append(kw)

        if matched:
            score = min(len(matched) / max(len(keywords) * 0.3, 1), 1.0)
            severity = _score_to_severity(score)
            areas.append({
                "area": area,
                "score": round(score, 2),
                "severity": severity,
                "matched_keywords": matched[:5],
            })

    # Sort by score descending
    areas.sort(key=lambda a: -a["score"])
    return areas


def _score_to_severity(score):
    """Convert a numeric score to a severity label."""
    if score >= SEVERITY_THRESHOLDS["critical"]:
        return "critical"
    elif score >= SEVERITY_THRESHOLDS["high"]:
        return "high"
    elif score >= SEVERITY_THRESHOLDS["medium"]:
        return "medium"
    else:
        return "low"


def _compute_ticket_severity(ticket, areas):
    """Compute the overall severity for a ticket based on its impact areas."""
    if not areas:
        return "low"

    # Use the highest area severity
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    max_sev = max(areas, key=lambda a: severity_rank.get(a["severity"], 0))

    # Boost if ticket priority is high/critical
    priority = (ticket.get("priority") or "").lower()
    if priority in ["highest", "critical", "blocker"]:
        rank = severity_rank.get(max_sev["severity"], 1)
        rank = min(rank + 1, 4)
        return {4: "critical", 3: "high", 2: "medium", 1: "low"}[rank]

    return max_sev["severity"]


def _generate_recommendations(ticket, areas):
    """Generate documentation update recommendations for a ticket."""
    recs = []
    area_names = [a["area"] for a in areas]

    if "User Guide & Procedures" in area_names:
        recs.append("Review and update task topics for changed workflows or UI")
    if "Configuration & Setup" in area_names:
        recs.append("Update configuration reference with new/changed parameters")
    if "API & Integration" in area_names:
        recs.append("Update API reference documentation (endpoints, parameters, responses)")
    if "Administration" in area_names:
        recs.append("Review admin guide for permission or security changes")
    if "Release Notes" in area_names:
        recs.append("Add release note entry for this change")
    if "Troubleshooting" in area_names:
        recs.append("Add or update troubleshooting topic for this scenario")
    if "Data & Reports" in area_names:
        recs.append("Update report/data reference documentation")
    if "Concepts & Overview" in area_names:
        recs.append("Review and update conceptual overview topics")

    # Add generic recommendation if nothing specific matched
    if not recs:
        recs.append("Review related documentation for accuracy after this change")

    return recs


def _area_recommendation(area, ticket_count):
    """Generate a recommendation for an impacted documentation area."""
    if ticket_count >= 5:
        return f"Major documentation effort required — {ticket_count} changes affect this area"
    elif ticket_count >= 3:
        return f"Significant review needed — {ticket_count} changes in this area"
    elif ticket_count >= 2:
        return f"Review recommended — multiple changes in this area"
    else:
        return f"Check for accuracy — 1 change in this area"


# =============================================================================
# PUBLIC API
# =============================================================================

def analyze_session(session_data):
    """Main entry point: analyze a Chancellor session.

    Args:
        session_data: list of raw validation JSON objects (as parsed from files)

    Returns:
        Full impact assessment dict
    """
    # Parse each validation JSON
    tickets = []
    for item in session_data:
        parsed = parse_validation_json(item)
        if parsed:
            tickets.append(parsed)

    if not tickets:
        return {
            "summary": {"total_tickets": 0, "relevant": 0, "impacted_areas": 0},
            "impacted_areas": [],
            "ticket_impacts": [],
            "timeline": {},
            "error": "No valid ticket data found in the imported session.",
        }

    # Run impact assessment
    result = assess_impact(tickets)
    return result
