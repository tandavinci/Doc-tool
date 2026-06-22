"""
Shared utility functions.

Ported from frontend/app.js - preserves output formatting exactly.
"""

import re


# =============================================================================
# XML ESCAPING
# =============================================================================

def xml_escape(s):
    """Escape &, <, > for DITA XML output. Mirrors JS xEsc()."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# =============================================================================
# TOKENIZATION & SIMILARITY
# =============================================================================

def tokenize(text):
    """
    Lowercase word tokenization, keeping only words with length > 2.
    Mirrors JS tokenise().
    """
    if not text:
        return []
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [w for w in cleaned.split() if len(w) > 2]


def jaccard_similarity(tokens_a, tokens_b):
    """
    Jaccard similarity between two token lists.
    Mirrors JS jaccardSim().
    """
    if not tokens_a and not tokens_b:
        return 0.0
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    intersection = len(set_a & set_b)
    union = len(set_a) + len(set_b) - intersection
    return intersection / union if union > 0 else 0.0


# =============================================================================
# DITA XML GENERATION (DEPRECATED - now in dita_converter.py)
# These stubs remain for backward compatibility but delegate to the new module.
# =============================================================================

def generate_concept_xml(text):
    """Deprecated: Use dita_converter.generate_concept_xml instead."""
    from dita_converter import generate_concept_xml as _new
    return _new(text)


def generate_task_xml(text):
    """Deprecated: Use dita_converter.generate_task_xml instead."""
    from dita_converter import generate_task_xml as _new
    return _new(text)


# =============================================================================
# UI ELEMENT BOLDING (for rewrite output)
# =============================================================================

UI_CONTEXT_WORDS = [
    "field", "fields", "tab", "tabs", "button", "buttons",
    "screen", "screens", "window", "windows", "box", "boxes",
    "panel", "panels", "page", "pages", "section", "sections",
    "list", "lists", "menu", "menus", "icon", "icons",
    "link", "links", "option", "options", "column", "columns",
    "dialog box", "check box", "check boxes", "drop-down", "drop-down list",
]


def bold_ui_elements(text):
    """
    Apply bold formatting to UI element names followed by context words.
    Mirrors JS boldUIElements().
    """
    result = text
    for ctx in UI_CONTEXT_WORDS:
        esc = ctx.replace(" ", r"\s+")
        # Match: CapitalizedWord(s) followed by the context word
        # But not if already wrapped in <strong>
        rx = re.compile(
            r"(?<!<strong>)(?:</strong>\s+)?"
            r"([A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*)?)"
            r"(\s+" + esc + r"\b)"
        )

        def replacer(m):
            if "<strong>" in m.group(0):
                return m.group(0)
            return "<strong>" + m.group(1) + "</strong>" + m.group(2)

        result = rx.sub(replacer, result)
    return result
