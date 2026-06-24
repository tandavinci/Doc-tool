"""
Enterprise Documentation Review Engine.

Validates content against:
- DITA Information Typing Standards
- Global English Guidelines
- Translation Readiness Requirements
- Standard English Compliance
- UI Language Standards
- Terminology Consistency
- Conciseness / Content Reduction
- Short Description Validation
- Reusability Review

Returns: topic classification, compliance score, violations, suggestions.
"""

import re
from collections import Counter


# =============================================================================
# CONSTANTS
# =============================================================================

VERB_STARTERS = [
    "add", "assign", "build", "cancel", "change", "check", "click",
    "close", "configure", "connect", "copy", "create", "define", "delete",
    "deploy", "disable", "edit", "enable", "enter", "export", "generate",
    "import", "install", "launch", "load", "manage", "modify", "move",
    "open", "perform", "print", "publish", "remove", "rename", "replace",
    "reset", "restore", "run", "save", "search", "select", "send", "set",
    "setup", "specify", "start", "stop", "submit", "test", "transfer",
    "uninstall", "update", "upgrade", "upload", "use", "validate", "verify",
    "view", "write",
]

IMPERATIVE_PATTERNS = [
    r'\bclick\b', r'\bselect\b', r'\btap\b', r'\benter\b', r'\btype\b',
    r'\bnavigate\b', r'\bopen\b', r'\bclose\b', r'\bsave\b', r'\bpress\b',
    r'\bdrag\b', r'\bscroll\b',
]

FIGURATIVE_PHRASES = [
    "at the end of the day", "out of the box", "on the fly", "under the hood",
    "a piece of cake", "boils down to", "in a nutshell", "the bottom line",
    "at your fingertips", "behind the scenes", "cutting edge", "state of the art",
    "best of breed", "low-hanging fruit", "move the needle", "deep dive",
    "take a stab", "circle back", "touch base", "leverage",
]

VAGUE_TERMS = [
    "stuff", "things", "etc", "and so on", "and more", "various",
    "some", "certain", "appropriate", "proper", "suitable", "relevant",
    "necessary", "required", "needed", "desired", "applicable",
]

NON_STANDARD_VERBS = [
    (r'\baction(?:ed|ing)?\b', "action (as verb)", "use a specific verb like 'perform' or 'complete'"),
    (r'\bimpact(?:ed|ing)?\b(?!\s+analysis)', "impact (as verb)", "use 'affect' or 'influence'"),
    (r'\btask(?:ed|ing)\b', "task (as verb)", "use 'assign' or 'delegate'"),
    (r'\bsurface(?:d|ing)?\b(?!\s+area)', "surface (as verb)", "use 'display' or 'show'"),
    (r'\bflag(?:ged|ging)?\b', "flag (as verb)", "use 'mark' or 'identify'"),
]

ADJECTIVE_AS_NOUN = [
    (r'\bthe pop-up\b(?!\s+(?:menu|window|dialog|message))', "the pop-up", "the pop-up menu/window/dialog"),
    (r'\bthe dropdown\b(?!\s+(?:list|menu|field))', "the dropdown", "the dropdown list/menu"),
    (r'\bthe modal\b(?!\s+(?:window|dialog|form))', "the modal", "the modal dialog/window"),
]

TRANSLATION_ISSUES = [
    (r'\bhover\s+over\b', "hover over", "position the mouse pointer over"),
    (r'\bright-click\b', "right-click", "right-click (use platform-neutral: 'access the context menu')"),
    (r'\bdouble-click\b', "double-click", "double-click (clarify: 'select by double-clicking')"),
    (r'\bhit\s+(?:Enter|Return|the\s+button)\b', "hit (key/button)", "press"),
    (r'\bfire\s+(?:up|off)\b', "fire up/off", "start or initiate"),
    (r'\bspin\s+up\b', "spin up", "start or create"),
    (r'\bkill\b(?!\s+switch)', "kill (process)", "stop or terminate"),
]

REDUNDANT_PHRASES = [
    (r'\bin order to\b', "in order to", "to"),
    (r'\bdue to the fact that\b', "due to the fact that", "because"),
    (r'\bat this point in time\b', "at this point in time", "now"),
    (r'\bin the event that\b', "in the event that", "if"),
    (r'\bprior to\b', "prior to", "before"),
    (r'\bsubsequent to\b', "subsequent to", "after"),
    (r'\bfor the purpose of\b', "for the purpose of", "to"),
    (r'\bwith regard to\b', "with regard to", "about"),
    (r'\bin spite of the fact that\b', "in spite of the fact that", "although"),
    (r'\bit is important to note that\b', "it is important to note that", "(remove, state directly)"),
    (r'\bplease note that\b', "please note that", "(remove, state directly)"),
    (r'\bas a matter of fact\b', "as a matter of fact", "(remove)"),
    (r'\bneedless to say\b', "needless to say", "(remove)"),
    (r'\bit should be noted that\b', "it should be noted that", "(remove, state directly)"),
    (r'\bbasically\b', "basically", "(remove)"),
    (r'\bactually\b', "actually", "(remove or clarify)"),
    (r'\bobviously\b', "obviously", "(remove)"),
    (r'\bclearly\b', "clearly", "(remove)"),
    (r'\bsimply\b', "simply", "(remove or rephrase)"),
]

UI_VERB_ISSUES = [
    (r'\bclick\s+(?:on\s+)?the\s+(\w+)\s+button\b', "click the X button", "Select {0}."),
    (r'\bhit\s+the\s+(\w+)\s+button\b', "hit the X button", "Select {0}."),
    (r'\bpress\s+the\s+(\w+)\s+button\b', "press the X button", "Select {0}."),
]

# Scoring weights
SCORE_WEIGHTS = {
    "information_typing": 25,
    "dita_structure": 20,
    "global_english": 15,
    "translation_readiness": 15,
    "writing_quality": 10,
    "terminology": 5,
    "reusability": 5,
    "content_efficiency": 5,
}


# =============================================================================
# TOPIC CLASSIFICATION
# =============================================================================

def classify_topic(text):
    """Determine if the content is concept, task, or reference.

    Returns: dict with 'type', 'confidence', 'reasoning'
    """
    lines = text.strip().split('\n')
    first_line = lines[0].strip() if lines else ""

    signals = {"concept": 0, "task": 0, "reference": 0}
    reasons = []

    # Check title (first line) for verb starter
    first_word = first_line.split()[0].lower() if first_line.split() else ""
    if first_word in VERB_STARTERS:
        signals["task"] += 3
        reasons.append("Title starts with a verb (task indicator)")
    elif first_word in ["about", "overview", "understanding", "introduction"]:
        signals["concept"] += 3
        reasons.append("Title uses concept-oriented language")

    # Check for ordered steps (numbered lists)
    numbered_lines = len(re.findall(r'^\s*\d+[\.\)]\s+', text, re.MULTILINE))
    if numbered_lines >= 3:
        signals["task"] += 4
        reasons.append(f"Contains {numbered_lines} numbered steps")

    # Check for imperative verbs
    imperative_count = 0
    for pat in IMPERATIVE_PATTERNS:
        imperative_count += len(re.findall(pat, text, re.IGNORECASE))
    if imperative_count >= 3:
        signals["task"] += 2
        reasons.append(f"Contains {imperative_count} imperative instructions")

    # Check for explanatory content (what/why patterns)
    explain_patterns = [
        r'\bis\s+(?:a|an|the)\b', r'\bprovides?\b', r'\benables?\b',
        r'\ballows?\b', r'\bdescribes?\b', r'\brepresents?\b',
        r'\bconsists?\s+of\b', r'\bincludes?\b',
    ]
    explain_count = 0
    for pat in explain_patterns:
        explain_count += len(re.findall(pat, text, re.IGNORECASE))
    if explain_count >= 3:
        signals["concept"] += 2
        reasons.append("Contains explanatory/descriptive language")

    # Check for reference patterns (field definitions, tables)
    if re.search(r'\|.*\|.*\|', text):
        signals["reference"] += 3
        reasons.append("Contains tabular/reference data")
    if re.findall(r'^[\w\s]+\n\s{2,}', text, re.MULTILINE):
        signals["reference"] += 1

    # Determine winner
    topic_type = max(signals, key=signals.get)
    total = sum(signals.values()) or 1
    confidence = round(signals[topic_type] / total * 100)

    return {
        "type": topic_type,
        "confidence": confidence,
        "reasoning": reasons,
    }


# =============================================================================
# VIOLATION DETECTION
# =============================================================================

def _find_sentence_containing(text, phrase):
    """Find the full sentence containing a given phrase. Returns the sentence string."""
    phrase_lower = phrase.lower()

    # Try to find the phrase in the text
    idx = text.lower().find(phrase_lower)
    if idx != -1:
        # Expand to full sentence boundaries
        sent_start = max(0, text.rfind('.', 0, idx) + 1)
        if sent_start <= 1:
            sent_start = max(0, text.rfind('\n', 0, idx) + 1)
        sent_end = text.find('.', idx + len(phrase))
        if sent_end == -1:
            sent_end = text.find('\n', idx + len(phrase))
        if sent_end == -1:
            sent_end = len(text)
        else:
            sent_end += 1
        return text[sent_start:sent_end].strip()

    # Fallback: find line containing the phrase
    for line in text.split('\n'):
        if phrase_lower in line.lower():
            return line.strip()

    return phrase


def _find_sentence_by_pattern(text, pattern):
    """Find the full sentence matching a regex pattern."""
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return ""
    return _find_sentence_containing(text, m.group(0))


def _check_information_typing(text, topic_type):
    """Rule Set 1: Validate content matches its detected topic type."""
    violations = []

    if topic_type == "concept":
        # Check for task content in concept
        numbered = re.findall(r'^\s*(\d+[\.\)]\s+.+)$', text, re.MULTILINE)
        if len(numbered) >= 3:
            violations.append({
                "severity": "critical",
                "rule": "Rule Set 1: Information Typing",
                "message": "Task-oriented content detected in Concept topic. Contains ordered procedures.",
                "category": "information_typing",
                "location": numbered[0].strip(),
            })
        for pat in IMPERATIVE_PATTERNS[:6]:
            matches = list(re.finditer(pat, text, re.IGNORECASE))
            if len(matches) >= 2:
                location = _find_sentence_containing(text, matches[0].group(0))
                violations.append({
                    "severity": "major",
                    "rule": "Rule Set 1: Information Typing",
                    "message": f"Imperative action '{matches[0].group(0)}' found in Concept topic. Concepts should not contain click instructions.",
                    "category": "information_typing",
                    "location": location,
                })
                break

    elif topic_type == "task":
        sentences = re.split(r'[.!?]+', text)
        long_explanations = [s.strip() for s in sentences if len(s.split()) > 35]
        if len(long_explanations) >= 3:
            violations.append({
                "severity": "major",
                "rule": "Rule Set 1: Information Typing",
                "message": "Concept-oriented content detected in Task topic. Contains long explanatory passages.",
                "category": "information_typing",
                "location": long_explanations[0][:120] + "...",
            })

    return violations


def _check_global_english(text):
    """Rule Set 3: Global English compliance."""
    violations = []
    suggestions = []

    # Check for figurative language
    for phrase in FIGURATIVE_PHRASES:
        if phrase.lower() in text.lower():
            location = _find_sentence_containing(text, phrase)
            violations.append({
                "severity": "major",
                "rule": "Rule Set 3: Global English",
                "message": f"Figurative language detected: '{phrase}'. Use literal, precise wording.",
                "category": "global_english",
                "location": location,
            })
            suggestions.append({
                "original": phrase,
                "suggested": "(replace with literal description)",
                "reason": "Figurative language is ambiguous for global audiences and translation.",
                "rule": "Global English",
                "location": location,
            })

    # Check for vague terms
    for term in VAGUE_TERMS:
        pattern = r'\b' + re.escape(term) + r'\b'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if matches:
            location = _find_sentence_containing(text, matches[0].group(0))
            violations.append({
                "severity": "minor",
                "rule": "Rule Set 3: Global English",
                "message": f"Vague terminology: '{term}'. Use precise, specific wording.",
                "category": "global_english",
                "location": location,
            })

    # Check for ambiguous 'this/that/it' without referent
    orphan_pronouns = re.findall(r'(?:^|[.!?]\s+)(This|That|It)\s+(?:is|was|has|will|can|should)\b', text)
    if len(orphan_pronouns) >= 2:
        location = _find_sentence_by_pattern(text, r'(?:^|[.!?]\s+)(?:This|That|It)\s+(?:is|was|has|will|can|should)\b')
        violations.append({
            "severity": "minor",
            "rule": "Rule Set 3: Global English",
            "message": "Ambiguous pronoun references detected. 'This/That/It' without clear noun referent.",
            "category": "global_english",
            "location": location,
        })

    return violations, suggestions


def _check_standard_english(text):
    """Rule Set 4: Standard English compliance."""
    violations = []
    suggestions = []

    # Non-standard verbs
    for pattern, term, replacement in NON_STANDARD_VERBS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = _find_sentence_containing(text, match.group(0))
            violations.append({
                "severity": "major",
                "rule": "Rule Set 4: Standard English",
                "message": f"Non-standard word formation: '{term}'. Use standard dictionary words.",
                "category": "writing_quality",
                "location": location,
            })
            suggestions.append({
                "original": match.group(0),
                "suggested": replacement,
                "reason": "Non-standard verb/word usage.",
                "rule": "Standard English",
                "location": location,
            })

    # Adjectives used as nouns
    for pattern, term, replacement in ADJECTIVE_AS_NOUN:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = _find_sentence_containing(text, match.group(0))
            violations.append({
                "severity": "minor",
                "rule": "Rule Set 4: Standard English",
                "message": f"Adjective used as noun: '{term}'. Add the appropriate noun.",
                "category": "writing_quality",
                "location": location,
            })
            suggestions.append({
                "original": term,
                "suggested": replacement,
                "reason": "Adjectives require a noun for clarity in translation.",
                "rule": "Standard English",
                "location": location,
            })

    return violations, suggestions


def _check_translation_readiness(text):
    """Rule Set 5: Translation readiness."""
    violations = []
    suggestions = []

    for pattern, term, replacement in TRANSLATION_ISSUES:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = _find_sentence_containing(text, match.group(0))
            violations.append({
                "severity": "minor",
                "rule": "Rule Set 5: Translation Readiness",
                "message": f"Translation ambiguity: '{term}'. May not translate clearly.",
                "category": "translation_readiness",
                "location": location,
            })
            suggestions.append({
                "original": match.group(0),
                "suggested": replacement,
                "reason": "Translation ambiguity detected. Use explicit wording.",
                "rule": "Translation Readiness",
                "location": location,
            })

    return violations, suggestions


def _check_syntactic_cues(text):
    """Rule Set 6: Syntactic cue validation."""
    violations = []

    # Check for missing 'that' after reporting verbs
    missing_that = re.findall(
        r'\b(ensure|verify|confirm|note|specify|indicate|assume)\s+(?!that\b)([a-z])',
        text, re.IGNORECASE
    )
    if len(missing_that) >= 2:
        location = _find_sentence_by_pattern(text, r'\b(?:ensure|verify|confirm|note|specify|indicate|assume)\s+(?!that\b)[a-z]')
        violations.append({
            "severity": "minor",
            "rule": "Rule Set 6: Syntactic Cues",
            "message": "Possible missing syntactic cue 'that' after reporting verbs. Aids translation clarity.",
            "category": "translation_readiness",
            "location": location,
        })

    return violations


def _check_terminology(text):
    """Rule Set 7: Terminology consistency."""
    violations = []

    # Detect synonym groups used interchangeably
    synonym_groups = [
        (["customer", "client", "account holder", "user"], "customer/user terminology"),
        (["delete", "remove", "erase", "clear"], "delete/remove terminology"),
        (["display", "show", "present", "render"], "display/show terminology"),
        (["choose", "select", "pick"], "choose/select terminology"),
    ]

    for group, label in synonym_groups:
        found = []
        for term in group:
            if re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE):
                found.append(term)
        if len(found) >= 2:
            location = _find_sentence_containing(text, found[0])
            violations.append({
                "severity": "minor",
                "rule": "Rule Set 7: Terminology",
                "message": f"Terminology inconsistency ({label}): using '{found[0]}' and '{found[1]}' interchangeably. Use one term consistently.",
                "category": "terminology",
                "location": location,
            })

    return violations


def _check_ui_language(text):
    """Rule Set 8: UI language standards."""
    violations = []
    suggestions = []

    for pattern, desc, fix_template in UI_VERB_ISSUES:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            btn_name = m.group(1) if m.groups() else ""
            location = _find_sentence_containing(text, m.group(0))
            violations.append({
                "severity": "minor",
                "rule": "Rule Set 8: UI Language",
                "message": f"UI language: '{m.group(0)}'. Use exact UI label format.",
                "category": "writing_quality",
                "location": location,
            })
            suggestions.append({
                "original": m.group(0),
                "suggested": fix_template.format(btn_name) if btn_name else fix_template,
                "reason": "Use exact UI labels. Correct format: 'Select [Label].'",
                "rule": "UI Language",
                "location": location,
            })

    return violations, suggestions


def _check_conciseness(text):
    """Rule Set 9: Conciseness validation."""
    violations = []
    suggestions = []

    for pattern, phrase, replacement in REDUNDANT_PHRASES:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for m in matches:
            location = _find_sentence_containing(text, m.group(0))
            violations.append({
                "severity": "minor",
                "rule": "Rule Set 9: Conciseness",
                "message": f"Redundant phrase: '{phrase}'. Simplify.",
                "category": "content_efficiency",
                "location": location,
            })
            suggestions.append({
                "original": m.group(0),
                "suggested": replacement,
                "reason": "Content reduction opportunity. Remove wordiness.",
                "rule": "Conciseness",
                "location": location,
            })

    # Check for repeated sentences
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip() and len(s.strip()) > 20]
    seen = Counter()
    for s in sentences:
        normalized = ' '.join(s.lower().split())
        seen[normalized] += 1
    for sent, count in seen.items():
        if count > 1:
            violations.append({
                "severity": "minor",
                "rule": "Rule Set 9: Conciseness",
                "message": f"Repeated content detected ({count} occurrences). Consider consolidation.",
                "category": "content_efficiency",
                "location": sent[:120],
            })
            break

    return violations, suggestions


def _check_short_description(text, topic_type):
    """Rule Set 11: Short description validation."""
    violations = []

    lines = text.strip().split('\n')
    # Skip the title (first line), check if second substantial line is a short desc
    content_lines = [l for l in lines[1:] if l.strip()]
    if content_lines:
        first_para = content_lines[0].strip()
        word_count = len(first_para.split())
        if word_count > 60:
            violations.append({
                "severity": "minor",
                "rule": "Rule Set 11: Short Description",
                "message": f"Opening paragraph is {word_count} words. Short description should be 20-60 words.",
                "category": "dita_structure",
                "location": first_para[:120] + ("..." if len(first_para) > 120 else ""),
            })
        elif word_count < 10:
            violations.append({
                "severity": "minor",
                "rule": "Rule Set 11: Short Description",
                "message": "Opening paragraph may be too brief for a short description (less than 10 words).",
                "category": "dita_structure",
                "location": first_para,
            })
    else:
        violations.append({
            "severity": "major",
            "rule": "Rule Set 11: Short Description",
            "message": "Missing short description. Every topic requires a shortdesc element.",
            "category": "dita_structure",
            "location": lines[0].strip() if lines else "",
        })

    return violations


def _check_reusability(text):
    """Rule Set 10: Reusability review."""
    violations = []

    # Detect repeated warnings/notes
    notes = re.findall(r'(?:Note|Warning|Caution|Important|Tip)\s*[:.]?\s*(.{20,80})', text, re.IGNORECASE)
    if len(notes) != len(set(n.lower().strip() for n in notes)) and len(notes) > 1:
        violations.append({
            "severity": "minor",
            "rule": "Rule Set 10: Reusability",
            "message": "Duplicate note/warning content detected. Consider using conref for shared content.",
            "category": "reusability",
        })

    # General duplicate detection
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 40]
    if len(paragraphs) != len(set(p.lower() for p in paragraphs)):
        violations.append({
            "severity": "minor",
            "rule": "Rule Set 10: Reusability",
            "message": "Reusable content opportunity detected. Duplicate paragraphs found.",
            "category": "reusability",
        })

    return violations


# =============================================================================
# SCORING
# =============================================================================

def _compute_score(violations):
    """Compute compliance score based on violations and category weights."""
    # Start with perfect scores per category
    category_scores = {cat: 100 for cat in SCORE_WEIGHTS}

    # Deduct points based on violations
    deductions = {
        "critical": 25,
        "major": 12,
        "minor": 5,
    }

    for v in violations:
        cat = v.get("category", "writing_quality")
        severity = v.get("severity", "minor")
        deduct = deductions.get(severity, 5)
        if cat in category_scores:
            category_scores[cat] = max(0, category_scores[cat] - deduct)

    # Compute weighted total
    total = 0
    breakdown = {}
    for cat, weight in SCORE_WEIGHTS.items():
        score = category_scores[cat]
        weighted = round(score * weight / 100)
        total += weighted
        breakdown[cat] = score

    # Determine verdict
    if total >= 95:
        verdict = "Enterprise Ready"
    elif total >= 90:
        verdict = "Compliant"
    elif total >= 80:
        verdict = "Minor Issues"
    elif total >= 70:
        verdict = "Major Revision Required"
    else:
        verdict = "Non-Compliant"

    return {
        "total": total,
        "verdict": verdict,
        "breakdown": breakdown,
    }


# =============================================================================
# MAIN REVIEW FUNCTION
# =============================================================================

def run_review(text):
    """Execute full documentation review.

    Args:
        text: The content to review (plain text or pre-processed from HTML).

    Returns:
        dict with: classification, score, violations, suggestions,
        translation_risks, reuse_opportunities, pass_fail
    """
    if not text or not text.strip():
        return {
            "classification": {"type": "unknown", "confidence": 0, "reasoning": []},
            "score": {"total": 0, "verdict": "Non-Compliant", "breakdown": {}},
            "violations": [],
            "suggestions": [],
            "translation_risks": [],
            "reuse_opportunities": [],
            "pass_fail": "Fail",
        }

    # Step 1: Classify topic
    classification = classify_topic(text)
    topic_type = classification["type"]

    # Step 2: Run all rule checks
    all_violations = []
    all_suggestions = []

    # Rule Set 1: Information Typing
    all_violations.extend(_check_information_typing(text, topic_type))

    # Rule Set 3: Global English
    v, s = _check_global_english(text)
    all_violations.extend(v)
    all_suggestions.extend(s)

    # Rule Set 4: Standard English
    v, s = _check_standard_english(text)
    all_violations.extend(v)
    all_suggestions.extend(s)

    # Rule Set 5: Translation Readiness
    v, s = _check_translation_readiness(text)
    all_violations.extend(v)
    all_suggestions.extend(s)
    translation_risks = [item["message"] for item in v]

    # Rule Set 6: Syntactic Cues
    all_violations.extend(_check_syntactic_cues(text))

    # Rule Set 7: Terminology
    all_violations.extend(_check_terminology(text))

    # Rule Set 8: UI Language
    v, s = _check_ui_language(text)
    all_violations.extend(v)
    all_suggestions.extend(s)

    # Rule Set 9: Conciseness
    v, s = _check_conciseness(text)
    all_violations.extend(v)
    all_suggestions.extend(s)

    # Rule Set 10: Reusability
    reuse_violations = _check_reusability(text)
    all_violations.extend(reuse_violations)
    reuse_opportunities = [item["message"] for item in reuse_violations]

    # Rule Set 11: Short Description
    all_violations.extend(_check_short_description(text, topic_type))

    # Step 3: Compute score
    score = _compute_score(all_violations)

    # Step 4: Determine pass/fail
    pass_fail = "Pass" if score["total"] >= 80 else "Fail"

    # Sort violations: critical first, then major, then minor
    severity_order = {"critical": 0, "major": 1, "minor": 2}
    all_violations.sort(key=lambda v: severity_order.get(v.get("severity", "minor"), 3))

    # Step 5: Resolve character positions (start/end) for each violation and suggestion
    # This enables the frontend to render inline highlights like the Content Analysis tab
    _resolve_positions(text, all_violations, all_suggestions)

    return {
        "classification": classification,
        "score": score,
        "violations": all_violations,
        "suggestions": all_suggestions,
        "translation_risks": translation_risks,
        "reuse_opportunities": reuse_opportunities,
        "pass_fail": pass_fail,
    }


def _resolve_positions(text, violations, suggestions):
    """Add start/end character positions to violations and suggestions.

    Searches the input text for the phrase that triggered each violation.
    Positions enable the frontend to render inline highlights.
    """
    text_lower = text.lower()

    for v in violations:
        if "start" in v and "end" in v:
            continue  # Already has positions
        # Try to find the location text in the original input
        loc = v.get("location", "")
        if loc:
            idx = text_lower.find(loc.lower())
            if idx != -1:
                v["start"] = idx
                v["end"] = idx + len(loc)
                continue
            # Try first 60 chars of location
            short = loc[:60].lower()
            idx = text_lower.find(short)
            if idx != -1:
                # Find end of that sentence
                end = text.find('.', idx + len(short))
                if end == -1:
                    end = text.find('\n', idx + len(short))
                if end == -1:
                    end = min(idx + len(loc), len(text))
                else:
                    end += 1
                v["start"] = idx
                v["end"] = end
                continue
        # No position found
        v["start"] = 0
        v["end"] = 0

    for s in suggestions:
        if "start" in s and "end" in s:
            continue
        original = s.get("original", "")
        if original:
            idx = text_lower.find(original.lower())
            if idx != -1:
                s["start"] = idx
                s["end"] = idx + len(original)
                continue
        loc = s.get("location", "")
        if loc:
            idx = text_lower.find(loc.lower()[:60])
            if idx != -1:
                s["start"] = idx
                s["end"] = idx + len(loc)
                continue
        s["start"] = 0
        s["end"] = 0
