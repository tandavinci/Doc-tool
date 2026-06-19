"""
Business logic orchestration.

Contains the core analysis, rewrite, DITA conversion, and impact analysis
functions. Accepts plain Python data and returns plain Python data.
No I/O, no protocol handling, no JSON serialization.

Ported from frontend/app.js - preserves behavior exactly.
"""

import re

from rules import CA_RULES, RW_RULES, check_sentence_level, check_sentence_length
from utils import (
    xml_escape,
    tokenize,
    jaccard_similarity,
    bold_ui_elements,
)
from dita_converter import (
    generate_concept_xml,
    generate_task_xml,
)


# =============================================================================
# CONTENT ANALYSIS
# =============================================================================

def collect_violations(text):
    """
    Run all CA_RULES regex matches against text, add sentence-level checks,
    sort by start position, and resolve overlaps (keep first, skip overlapping).
    Mirrors JS collectViolations().
    """
    all_violations = []

    for rule in CA_RULES:
        rx = rule["pattern"]
        for m in rx.finditer(text):
            violation = {
                "start": m.start(),
                "end": m.end(),
                "ruleId": rule["id"],
                "cat": rule["cat"],
                "msg": rule["msg"],
                "color": rule["color"],
                "matchText": m.group(0),
            }
            if "fix" in rule:
                violation["fix"] = rule["fix"]
            all_violations.append(violation)

    # Add sentence-level checks
    all_violations.extend(check_sentence_level(text))

    # Sort by start position
    all_violations.sort(key=lambda v: v["start"])

    # Resolve overlaps: keep first match, skip subsequent overlapping matches
    clean = []
    cursor = 0
    for v in all_violations:
        if v["start"] >= cursor:
            clean.append(v)
            cursor = v["end"]

    return clean


def compute_fixed(text):
    """
    Apply all auto-fix rules to text and clean up spacing.
    Mirrors JS computeFixed().
    """
    out = text
    for rule in CA_RULES:
        if "fix" not in rule:
            continue
        out = rule["pattern"].sub(rule["fix"], out)
    # Clean up double spaces and space before punctuation
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r" ([,.:!?])", r"\1", out)
    return out.strip()


def analyze(text):
    """
    Main analysis orchestration function.
    Returns violations list and summary.
    """
    violations = collect_violations(text)

    # Build summary
    by_category = {}
    for v in violations:
        cat = v["cat"]
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "violations": violations,
        "summary": {
            "total": len(violations),
            "byCategory": by_category,
        },
    }


# =============================================================================
# REWRITE
# =============================================================================

def apply_rw_rules(text):
    """
    Apply all RW_RULES to text, post-process, bold UI elements,
    and check sentence length.
    Mirrors JS applyRWRules().
    """
    out = text
    changes = []

    for rule in RW_RULES:
        rx = rule["pattern"]

        def make_replacer(r):
            def replacer(m):
                matched = m.group(0)
                if r["type"] == "remove":
                    changes.append({
                        "from": matched.strip(),
                        "to": "(removed)",
                        "msg": r["msg"],
                    })
                    return ""
                else:
                    # Handle backreferences like $1
                    rep = r.get("fix", "")
                    # Replace $1, $2, etc. with captured groups
                    for i in range(1, 10):
                        placeholder = f"${i}"
                        if placeholder in rep:
                            group_val = m.group(i) if i <= len(m.groups()) and m.group(i) is not None else ""
                            rep = rep.replace(placeholder, group_val)
                    if matched.strip().lower() != rep.strip().lower():
                        changes.append({
                            "from": matched.strip(),
                            "to": rep.strip(),
                            "msg": r["msg"],
                        })
                    return rep
            return replacer

        out = rx.sub(make_replacer(rule), out)

    # Post-processing: clean up double spaces and space before punctuation
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([,.!?])", r"\1", out)
    out = out.strip()

    # Bold UI elements
    out = bold_ui_elements(out)

    # Check sentence length on plain text (strip HTML tags)
    plain = re.sub(r"<[^>]+>", "", out)
    sent_warnings = check_sentence_length(plain)

    return {
        "rewritten": out,
        "changes": changes,
        "sentenceWarnings": sent_warnings,
    }


def rewrite(text):
    """Main rewrite orchestration function."""
    return apply_rw_rules(text)


# =============================================================================
# DITA CONVERSION
# =============================================================================

def convert_dita(text, fmt):
    """
    Convert text to DITA XML.
    fmt: "concept" or "task"
    """
    if fmt == "task":
        xml = generate_task_xml(text)
    else:
        xml = generate_concept_xml(text)
    return {"xml": xml}


# =============================================================================
# IMPACT ANALYSIS
# =============================================================================

def impact_analyze(jira_items, dita_topics, threshold):
    """
    Compare JIRA items against DITA topics using Jaccard similarity.
    Mirrors the comparison logic from JS runImpactAnalysis().

    Args:
        jira_items: list of dicts with keys: key, summary, description, issueType
        dita_topics: list of dicts with keys: title, body
        threshold: float similarity threshold (e.g., 0.18)

    Returns:
        dict with topicsToCreate and topicsToUpdate lists
    """
    # Pre-tokenize topics
    topic_tokens = [tokenize(t["title"] + " " + t.get("body", "")) for t in dita_topics]

    topics_to_create = []
    topics_to_update = []

    for item in jira_items:
        summary = item.get("summary", "")
        description = item.get("description", "")
        issue_type = item.get("issueType", "")
        jira_key = item.get("key", "")

        jira_tokens = tokenize(summary + " " + description)

        # Find best matching topic
        best_score = 0.0
        best_topic = None
        for i, topic in enumerate(dita_topics):
            score = jaccard_similarity(jira_tokens, topic_tokens[i])
            if score > best_score:
                best_score = score
                best_topic = topic

        if best_score >= threshold:
            topics_to_update.append({
                "jiraKey": jira_key,
                "summary": summary,
                "issueType": issue_type,
                "matchedTopic": best_topic["title"] if best_topic else "",
                "confidence": round(best_score, 4),
            })
        else:
            topics_to_create.append({
                "jiraKey": jira_key,
                "summary": summary,
                "issueType": issue_type,
                "bestMatchScore": round(best_score, 4),
            })

    return {
        "topicsToCreate": topics_to_create,
        "topicsToUpdate": topics_to_update,
    }
