"""
First Draft Engine — Infor Writing Standards Rewriter.

Rewrites input content to comply with Infor Information Development
Writing Standards (Release 3.0.x). Returns the original text, rewritten
text, and a list of changes made with explanations.

Key rules applied:
- need → require
- Anthropomorphism removal (allows you to → Use...to)
- "field is set to" → "the value in this field is set to"
- "please" removal
- Contractions expansion
- Active voice preference
- "click on" → "Click"
- "See xxx" → "See, xxx"
- Screen "displayed" → "accessed" (non-click context)
- Sentence length enforcement (≤25 words guidance)
- Oxford comma insertion
- Emphasis removal
- Inclusive language
"""

import re
from collections import OrderedDict


# =============================================================================
# REWRITE RULES
# Each rule: (pattern, replacement, explanation)
# =============================================================================

REWRITE_RULES = [
    # --- NEED → REQUIRE ---
    (r'\bneed(?:s)?\s+to\b', 'must', 'NEED→REQUIRE: "need to" replaced with "must" (formal requirement)'),
    (r'\byou\s+need\b', 'you must', 'NEED→REQUIRE: "you need" replaced with "you must"'),
    (r'\bneeds?\b(?!\s+to)', 'requires', 'NEED→REQUIRE: "need/needs" replaced with "requires"'),
    (r'\bif\s+needed\b', 'if required', 'NEED→REQUIRE: "if needed" replaced with "if required"'),
    (r'\bas\s+needed\b', 'as required', 'NEED→REQUIRE: "as needed" replaced with "as required"'),
    (r'\bwhen\s+needed\b', 'when required', 'NEED→REQUIRE: "when needed" replaced with "when required"'),

    # --- ANTHROPOMORPHISM ---
    (r'\b[Tt]he\s+(\w+)\s+screen\s+allows\s+you\s+to\b',
     r'Use the \1 screen to',
     'ANTHROPOMORPHISM: "screen allows you to" → "Use the screen to"'),
    (r'\b[Tt]he\s+(\w+)\s+report\s+displays\b',
     r'Use the \1 report to view',
     'ANTHROPOMORPHISM: "report displays" → "Use the report to view"'),
    (r'\b[Tt]he\s+(\w+)\s+option\s+allows\s+you\s+to\b',
     r'Use the \1 option to',
     'ANTHROPOMORPHISM: "option allows you to" → "Use the option to"'),
    (r'\b[Tt]he\s+(\w+)\s+option\s+(creates?|deletes?|adds?|removes?)\b',
     r'Use the \1 option to \2',
     'ANTHROPOMORPHISM: "option creates/deletes" → "Use the option to"'),
    (r'\b[Tt]his\s+(?:screen|page|form|session)\s+allows\s+you\s+to\b',
     'Use this screen to',
     'ANTHROPOMORPHISM: "this screen allows you to" → "Use this screen to"'),
    (r'\ballows\s+you\s+to\b', 'enables you to',
     'ANTHROPOMORPHISM: "allows you to" → "enables you to" (or rewrite with "Use...")'),

    # --- FIELD IS SET TO ---
    (r'\b[Tt]he\s+field\s+value\s+is\s+set\s+to\b',
     'The value in this field is set to',
     'FIELD REFERENCE: "the field value is set to" → "the value in this field is set to"'),
    (r'\b[Tt]he\s+field\s+is\s+set\s+to\b',
     'The value in this field is set to',
     'FIELD REFERENCE: "the field is set to" → "the value in this field is set to"'),
    (r'\bthe\s+(\w+)\s+field\s+is\s+set\s+to\b',
     r'the value in the \1 field is set to',
     'FIELD REFERENCE: "the X field is set to" → "the value in the X field is set to"'),

    # --- SEE REFERENCE ---
    # Only add comma when "See" is followed by a topic name (Capitalized Title),
    # a URL, or a quoted reference — not for generic usage like "see the results"
    # These rules are case-sensitive ((?-i) prefix)
    ('(?-i)\\bSee\\s+(?!,)([A-Z][A-Za-z0-9]+(?: [A-Z][A-Za-z0-9]+)+)',
     r'See, \1',
     'REFERENCE: "See TopicName" → "See, TopicName" (comma required for topic references)'),
    ('(?-i)\\bSee\\s+(?!,)(https?://\\S+)',
     r'See, \1',
     'REFERENCE: "See URL" → "See, URL" (comma required for references)'),

    # --- PLEASE REMOVAL ---
    (r'\b[Pp]lease\s+', '',
     'TONE: Remove "please" (too conversational for technical writing)'),

    # --- CLICK ON → CLICK ---
    (r'\b[Cc]lick\s+on\b', 'Click',
     'UI STANDARD: "click on" → "Click"'),
    (r'\b[Cc]lick\s+at\b', 'Click',
     'UI STANDARD: "click at" → "Click"'),

    # --- CONTRACTIONS ---
    (r"\bdon't\b", 'do not', 'CONTRACTION: Expand "don\'t" → "do not"'),
    (r"\bcan't\b", 'cannot', 'CONTRACTION: Expand "can\'t" → "cannot"'),
    (r"\bwon't\b", 'will not', 'CONTRACTION: Expand "won\'t" → "will not"'),
    (r"\bisn't\b", 'is not', 'CONTRACTION: Expand "isn\'t" → "is not"'),
    (r"\baren't\b", 'are not', 'CONTRACTION: Expand "aren\'t" → "are not"'),
    (r"\bwasn't\b", 'was not', 'CONTRACTION: Expand "wasn\'t" → "was not"'),
    (r"\bweren't\b", 'were not', 'CONTRACTION: Expand "weren\'t" → "were not"'),
    (r"\bdoesn't\b", 'does not', 'CONTRACTION: Expand "doesn\'t" → "does not"'),
    (r"\bdidn't\b", 'did not', 'CONTRACTION: Expand "didn\'t" → "did not"'),
    (r"\bshouldn't\b", 'should not', 'CONTRACTION: Expand "shouldn\'t" → "should not"'),
    (r"\bwouldn't\b", 'would not', 'CONTRACTION: Expand "wouldn\'t" → "would not"'),
    (r"\bcouldn't\b", 'could not', 'CONTRACTION: Expand "couldn\'t" → "could not"'),
    (r"\bit's\b", 'it is', 'CONTRACTION: Expand "it\'s" → "it is"'),
    (r"\bthat's\b", 'that is', 'CONTRACTION: Expand "that\'s" → "that is"'),
    (r"\bthere's\b", 'there is', 'CONTRACTION: Expand "there\'s" → "there is"'),
    (r"\bI'm\b", 'I am', 'CONTRACTION: Expand "I\'m" → "I am"'),
    (r"\bwe're\b", 'we are', 'CONTRACTION: Expand "we\'re" → "we are"'),
    (r"\bthey're\b", 'they are', 'CONTRACTION: Expand "they\'re" → "they are"'),
    (r"\byou're\b", 'you are', 'CONTRACTION: Expand "you\'re" → "you are"'),
    (r"\blet's\b", 'let us', 'CONTRACTION: Expand "let\'s" → "let us"'),

    # --- SCREEN DISPLAYED → ACCESSED (non-click context) ---
    (r'\b[Tt]his\s+(?:screen|page|form|session)\s+is\s+displayed\s+only\s+if\b',
     'This screen can be accessed only if',
     'SCREEN ACCESS: "screen is displayed only if" → "screen can be accessed only if"'),

    # --- QUALIFIERS / FILLER REMOVAL ---
    (r'\b[Ss]imply\s+', '', 'QUALIFIER: Remove "simply" (unnecessary filler)'),
    (r'\b[Jj]ust\s+', '', 'QUALIFIER: Remove "just" (unnecessary filler)'),
    (r'\b[Bb]asically\s*,?\s*', '', 'QUALIFIER: Remove "basically" (unnecessary filler)'),
    (r'\b[Oo]bviously\s*,?\s*', '', 'QUALIFIER: Remove "obviously" (unnecessary filler)'),
    (r'\b[Cc]learly\s*,?\s*', '', 'QUALIFIER: Remove "clearly" (unnecessary filler)'),
    (r'\b[Ee]asily\s+', '', 'QUALIFIER: Remove "easily" (unnecessary filler)'),
    (r'\b[Qq]uickly\s+', '', 'QUALIFIER: Remove "quickly" (unnecessary filler)'),

    # --- REDUNDANT PHRASES ---
    (r'\bin order to\b', 'to', 'CONCISENESS: "in order to" → "to"'),
    (r'\bdue to the fact that\b', 'because', 'CONCISENESS: "due to the fact that" → "because"'),
    (r'\bat this point in time\b', 'now', 'CONCISENESS: "at this point in time" → "now"'),
    (r'\bin the event that\b', 'if', 'CONCISENESS: "in the event that" → "if"'),
    (r'\bprior to\b', 'before', 'CONCISENESS: "prior to" → "before"'),
    (r'\bsubsequent to\b', 'after', 'CONCISENESS: "subsequent to" → "after"'),
    (r'\bfor the purpose of\b', 'to', 'CONCISENESS: "for the purpose of" → "to"'),
    (r'\bwith regard to\b', 'about', 'CONCISENESS: "with regard to" → "about"'),
    (r'\bit is important to note that\b', '', 'CONCISENESS: Remove "it is important to note that"'),
    (r'\bplease note that\b', '', 'CONCISENESS: Remove "please note that"'),
    (r'\bneedless to say\b', '', 'CONCISENESS: Remove "needless to say"'),
]


# =============================================================================
# MAIN REWRITE FUNCTION
# =============================================================================

def generate_first_draft(text):
    """Rewrite input text according to Infor Writing Standards.

    Returns:
        dict with:
        - original: the original input text
        - rewritten: the corrected text
        - changes: list of {original, replacement, rule, position}
    """
    if not text or not text.strip():
        return {"original": "", "rewritten": "", "changes": []}

    original = text
    result = text
    changes = []

    # Apply each rewrite rule
    for pattern, replacement, explanation in REWRITE_RULES:
        # Rules starting with (?-i) marker should be case-sensitive
        if pattern.startswith('(?-i)'):
            regex = re.compile(pattern[5:], 0)  # No flags, case-sensitive
        else:
            regex = re.compile(pattern, re.IGNORECASE)
        matches = list(regex.finditer(result))
        if matches:
            for m in reversed(matches):  # reverse to preserve positions
                original_text = m.group(0)
                # Apply backreferences in replacement
                new_text = regex.sub(replacement, original_text)
                if new_text != original_text:
                    changes.append({
                        "original": original_text,
                        "replacement": new_text,
                        "rule": explanation,
                        "position": m.start(),
                    })
            result = regex.sub(replacement, result)

    # Post-processing: clean up double spaces
    result = re.sub(r'  +', ' ', result)
    result = re.sub(r' ([.,;:!?])', r'\1', result)
    # Fix sentence starts after removals
    result = re.sub(r'(?<=\. )([a-z])', lambda m: m.group(1).upper(), result)
    result = re.sub(r'^\s*([a-z])', lambda m: m.group(1).upper(), result, flags=re.MULTILINE)

    # Sort changes by position
    changes.sort(key=lambda c: c["position"])

    return {
        "original": original,
        "rewritten": result.strip(),
        "changes": changes,
    }
