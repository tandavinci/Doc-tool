"""
DITA XML Converter — Concept and Task formats.

Converts raw input text into DITA-compliant XML following strict rules:
- Concept: outputs <conbody> content
- Task: outputs <taskbody> content

Accepts both plain text and HTML input (from rich paste / Word documents).
HTML input is preprocessed to extract structure (headings, lists, tables,
bold/italic, notes) before applying DITA conversion rules.

Rules applied:
- <uicontrol> for words before: field, tab, button, menu, widget, check box, option
- <wintitle> for words before: screen, window, session, dialogue box, panel, section
- <userinput> for words after: set to, as
- <note> for note blocks (no <p> inside)
- <ol>, <ul> for lists
- <dl>/<dlentry>/<dt>/<dd> for field definitions in concept
- <section> only when explicitly needed
- <menucascade> for ">" paths in task files
- <fieldlist>/<field>/<fieldname>/<fielddesc> for task field lists
- <shortdesc> for opening sentence in tasks
- Never uses <b>, <para>, or <menucascade> in concept files
"""

import re


# =============================================================================
# HTML INPUT PREPROCESSING
# =============================================================================

def _preprocess_markdown_bold(text):
    """Convert markdown-style **bold** to {{BOLD:...}} markers.

    This handles plain text input where bold is indicated with ** delimiters.
    Strips trailing colons from the bold text (colon stays outside the marker).
    Merges adjacent bold markers like **Word1** **Word2** into one.
    """
    if not text or '**' not in text:
        return text

    # First merge adjacent bold markers: **Word1** **Word2** → **Word1 Word2**
    text = re.sub(r'\*\*(.+?)\*\*\s*\*\*(.+?)\*\*', r'**\1 \2**', text)
    # Repeat for 3+ adjacent
    text = re.sub(r'\*\*(.+?)\*\*\s*\*\*(.+?)\*\*', r'**\1 \2**', text)

    def _md_bold_replacer(m):
        content = m.group(1)
        # If bold text ends with ':', move colon outside the marker
        if content.endswith(':'):
            return '{{BOLD:' + content[:-1] + '}}:'
        return '{{BOLD:' + content + '}}'

    return re.sub(r'\*\*(.+?)\*\*', _md_bold_replacer, text)

def _preprocess_html_input(html_text):
    """Convert HTML input (from rich paste) into structured plain text.

    Preserves:
    - Headings → ALL CAPS lines (detected as headings by the converter)
    - Bold text → preserved as-is (the converter uses capitalization patterns)
    - Lists → bullet/numbered format
    - Tables → pipe-delimited format
    - Notes → "Note:" prefixed lines
    - Paragraphs → newline-separated text

    This allows the existing plain-text converter to work with rich content.
    """
    if not html_text:
        return html_text
    # Check if this is actually HTML (has HTML tags like <p>, <div>, etc.)
    # A lone < in plain text (like "Qty < Safety") should NOT trigger HTML processing
    if not re.search(r'<(?:p|div|ul|ol|li|h[1-6]|strong|em|b|i|table|br|span|a)\b', html_text, re.IGNORECASE):
        # Not HTML — check for markdown-style bold (**text**)
        return _preprocess_markdown_bold(html_text)

    # Use regex-based HTML parsing (no external dependencies)
    text = html_text

    # Remove style, script, and head tags entirely
    text = re.sub(r'<(style|script|head)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Convert headings to uppercase lines (will be detected as sections)
    for level in range(1, 7):
        text = re.sub(
            r'<h' + str(level) + r'[^>]*>(.*?)</h' + str(level) + r'>',
            lambda m: '\n' + _strip_tags(m.group(1)).strip().upper() + '\n',
            text, flags=re.DOTALL | re.IGNORECASE
        )

    # Preserve bold/strong text with markers so the converter can detect them
    # Bold words are potential candidates for <uicontrol> or <wintitle>
    text = re.sub(
        r'<(strong|b)\b[^>]*>(.*?)</\1>',
        lambda m: '{{BOLD:' + _strip_tags(m.group(2)).strip() + '}}',
        text, flags=re.DOTALL | re.IGNORECASE
    )

    # Convert ordered lists — merge adjacent <ol> blocks first
    text = re.sub(r'</ol>\s*<ol[^>]*>', '', text, flags=re.IGNORECASE)

    def _convert_ol(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(0), re.DOTALL | re.IGNORECASE)
        result = '\n'
        for i, item in enumerate(items, 1):
            result += str(i) + '. ' + _strip_tags(item).strip() + '\n'
        return result + '\n'

    text = re.sub(r'<ol[^>]*>.*?</ol>', _convert_ol, text, flags=re.DOTALL | re.IGNORECASE)

    # Convert unordered lists — merge adjacent <ul> blocks first
    # Word often puts each bullet in its own <ul>, merge them
    text = re.sub(r'</ul>\s*<ul[^>]*>', '', text, flags=re.IGNORECASE)

    def _convert_ul(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(0), re.DOTALL | re.IGNORECASE)
        result = '\n'
        for item in items:
            result += '- ' + _strip_tags(item).strip() + '\n'
        return result + '\n'

    text = re.sub(r'<ul[^>]*>.*?</ul>', _convert_ul, text, flags=re.DOTALL | re.IGNORECASE)

    # Convert tables to pipe-delimited format
    def _convert_table(m):
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', m.group(0), re.DOTALL | re.IGNORECASE)
        result = '\n'
        for row in rows:
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL | re.IGNORECASE)
            result += '| ' + ' | '.join(_strip_tags(c).strip() for c in cells) + ' |\n'
        return result + '\n'

    text = re.sub(r'<table[^>]*>.*?</table>', _convert_table, text, flags=re.DOTALL | re.IGNORECASE)

    # Convert <br> to newlines
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)

    # Convert block elements to newline-separated
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<div[^>]*>', '', text, flags=re.IGNORECASE)

    # Strip remaining HTML tags
    text = _strip_tags(text)

    # Convert markdown-style **bold** to {{BOLD:...}} markers
    text = _preprocess_markdown_bold(text)

    # Merge broken lines: fix contenteditable wrapping and split bullet+text
    lines = text.split('\n')
    merged = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            merged.append('')  # preserve blank lines (paragraph breaks)
            continue

        # Check if this is a lone bullet character (Word splits bullet from text)
        # Merge with the NEXT line when we encounter it
        if re.match(r'^[\-\*\+\u2022\u2023\u25E6\u00B7\u2013\u2014\u25AA\u25AB\u27A2o]$', stripped):
            # Lone bullet — merge with whatever comes next
            merged.append(stripped + ' ')
            continue

        # If previous line is a lone bullet waiting for text, append to it
        if merged and merged[-1].strip() and re.match(
                r'^[\-\*\+\u2022\u2023\u25E6\u00B7\u2013\u2014\u25AA\u25AB\u27A2o]\s*$',
                merged[-1].strip()):
            merged[-1] = merged[-1].strip() + ' ' + stripped
            continue

        # Check if this line is a continuation of the previous (starts lowercase)
        if (merged and merged[-1] and stripped
                and not _is_unordered_list_item(stripped)
                and not stripped.startswith('{{BOLD:')
                and not re.match(r'^\d+[\.\)]', stripped)
                and not re.match(r'^(Note|Warning|Caution|Tip|Important)', stripped, re.IGNORECASE)
                and stripped[0].islower()):
            # Continuation line — merge with previous
            merged[-1] = merged[-1].rstrip() + ' ' + stripped
        else:
            merged.append(line)
    text = '\n'.join(merged)

    # Clean up: remove excessive blank lines, trim
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def _strip_tags(html):
    """Remove all HTML tags from a string and decode common HTML entities."""
    text = re.sub(r'<[^>]+>', '', html)
    # Decode common HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&nbsp;', ' ')
    return text


# =============================================================================
# SHARED UTILITIES
# =============================================================================

def xml_escape(s):
    """Escape &, <, > for XML output."""
    if not s:
        return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Context words that trigger <uicontrol> on the preceding word(s)
UICONTROL_TRIGGERS = [
    "field", "fields", "tab", "tabs", "button", "buttons",
    "menu", "menus", "widget", "widgets", "check box",
    "check boxes", "option", "options", "module", "modules",
    "form", "forms", "column", "columns",
]

# Context words that trigger <wintitle> on the preceding word(s)
WINTITLE_TRIGGERS = [
    "screen", "screens", "window", "windows", "session", "sessions",
    "dialogue box", "dialogue boxes", "dialog box", "dialog boxes",
    "panel", "panels", "section", "sections",
]

# Words after which <userinput> is applied to the following value
USERINPUT_TRIGGERS = [r"set\s+to", r"as"]


def _apply_uicontrol(text):
    """Apply <uicontrol> tags to words preceding UI context words.

    Skips text already inside XML tags to prevent double-tagging.
    """
    result = text
    for trigger in UICONTROL_TRIGGERS:
        pattern = re.compile(
            r'\b((?:[A-Z][A-Za-z0-9]*)'
            r'(?:(?:\s+(?:from|for|of|to|in|on|by|with|By))?'
            r'\s+(?:[A-Z0-9][A-Za-z0-9]*))*'
            r'(?:\s*\([^)]*\))?)'
            r'(\s+' + re.escape(trigger) + r')\b'
        )

        def _uicontrol_replacer(m):
            name = m.group(1).strip()
            suffix = m.group(2)
            if not name or len(name) < 2:
                return m.group(0)
            # Skip if already tagged
            if '<uicontrol>' in name or '<wintitle>' in name:
                return m.group(0)
            skip_words = {'The', 'This', 'That', 'These', 'Those', 'Each',
                          'Every', 'Some', 'Any', 'All', 'No', 'One', 'Its'}
            for sw in skip_words:
                if name.startswith(sw + ' '):
                    prefix = sw + ' '
                    name = name[len(prefix):]
                    if name:
                        return prefix + "<uicontrol>" + name + "</uicontrol>" + suffix
                    return m.group(0)
            if name in skip_words:
                return m.group(0)
            return "<uicontrol>" + name + "</uicontrol>" + suffix

        result = pattern.sub(_uicontrol_replacer, result)
    return result


def _apply_wintitle(text):
    """Apply <wintitle> tags to words preceding window/screen context words.

    The context word itself (screen, window, etc.) is NOT tagged.
    Handles names with parenthetical codes like 'Rental Agreement (tssoc2610m300)'.
    """
    result = text
    for trigger in WINTITLE_TRIGGERS:
        pattern = re.compile(
            r'\b((?:[A-Z][a-z]+|[A-Z]{2,})'
            r'(?:(?:\s+(?:from|for|of|to|and|or|in|on|by|with))?'
            r'\s+(?:[A-Z][a-z]+|[A-Z]{2,}))*'
            r'(?:\s*\([^)]*\))?)'
            r'(\s+' + re.escape(trigger) + r')\b'
        )

        def _wintitle_replacer(m):
            name = m.group(1).strip()
            suffix = m.group(2)
            if not name or name.startswith("<") or len(name) < 2:
                return m.group(0)
            skip_words = {'The', 'This', 'That', 'These', 'Those', 'Each',
                          'Every', 'Some', 'Any', 'All', 'No', 'One', 'Its'}
            # If name starts with a skip word, strip it and keep it outside the tag
            for sw in skip_words:
                if name.startswith(sw + ' '):
                    prefix = sw + ' '
                    name = name[len(prefix):]
                    if name:
                        return prefix + "<wintitle>" + name + "</wintitle>" + suffix
                    return m.group(0)
            if name in skip_words:
                return m.group(0)
            return "<wintitle>" + name + "</wintitle>" + suffix

        result = pattern.sub(_wintitle_replacer, result)
    return result


def _apply_userinput(text):
    """Apply <userinput> tags to values following 'set to' or 'as'.

    Only tags words that look like actual values: capitalized words,
    numbers, or known setting values. Does NOT tag articles (a, an, the)
    or common lowercase words.

    Example: 'set to True' -> 'set to <userinput>True</userinput>'
    Example: 'defined as Manual' -> 'defined as <userinput>Manual</userinput>'
    """
    result = text
    # "set to <Value>" — value must be capitalized or numeric
    result = re.sub(
        r'(set\s+to)\s+([A-Z][A-Za-z0-9_\-]*)',
        r'\1 <userinput>\2</userinput>',
        result,
        flags=re.IGNORECASE
    )
    # "defined as <Value>" / "configured as <Value>" — value must be capitalized
    result = re.sub(
        r'((?:defined|configured|specified|marked|flagged)\s+as)\s+([A-Z][A-Za-z0-9_\-]*)',
        r'\1 <userinput>\2</userinput>',
        result
    )
    return result


def _apply_inline_tags(text, is_task=False):
    """Apply all inline DITA tags to a line of text.

    Order: escape XML first, then apply semantic tags.
    For task files, menucascade is applied FIRST (before other tags)
    since it operates on the ">" separator.
    For concept files, menucascade is never used.
    Bold markers from HTML paste are resolved into appropriate DITA tags.
    """
    escaped = xml_escape(text)
    if is_task:
        escaped = _apply_menucascade(escaped)
    # Process bold markers from HTML paste into DITA tags
    escaped = _apply_bold_markers(escaped, is_task=is_task)
    result = _apply_uicontrol(escaped)
    result = _apply_wintitle(result)
    result = _apply_userinput(result)
    return result


def _apply_bold_markers(text, is_task=False):
    """Convert {{BOLD:word}} markers into appropriate DITA inline tags.

    Logic:
    - If the bold word appears before a UI trigger word → <uicontrol>
    - If the bold word appears before a window trigger word → <wintitle>
    - If the bold word is a note prefix (Note, Warning, etc.) → leave as text (note handled at block level)
    - Otherwise → <uicontrol> (bold in technical docs usually indicates UI elements)
    """
    # First pass: resolve bold markers that are immediately before a trigger word
    # The trigger words will be handled by _apply_uicontrol/_apply_wintitle after this
    def _bold_replacer(m):
        word = m.group(1)
        # Skip note prefixes — they're handled at block level
        if re.match(r'^(Note|Warning|Caution|Tip|Important|Danger)$', word, re.IGNORECASE):
            return word
        # Return the word as-is — the uicontrol/wintitle patterns will pick it up
        # if it's followed by a trigger word. If not, tag it as <uicontrol>
        # since bold in technical docs typically indicates a UI element name.
        return word

    # Check each bold marker: if followed by a trigger word, just unwrap it
    # (the downstream _apply_uicontrol will handle it). Otherwise, tag it.
    result = text

    def _contextual_bold(m):
        word = m.group(1)

        # Skip note-type prefixes
        if re.match(r'^(Note|Warning|Caution|Tip|Important|Danger)$', word, re.IGNORECASE):
            return word

        # If bold text is the entire line content, it was already handled as section title
        # by the main loop — just return the word plain (shouldn't reach here for titles)
        line_start = text.rfind('\n', 0, m.start()) + 1
        line_end = text.find('\n', m.end())
        if line_end == -1:
            line_end = len(text)
        line_content = text[line_start:line_end].strip()
        if line_content == '{{BOLD:' + word + '}}':
            return word  # standalone bold = title, handled elsewhere

        # Check if followed by a UI trigger word → tag directly as <uicontrol>
        pos = m.end()
        remaining = text[pos:pos + 30] if pos < len(text) else ''
        for trigger in WINTITLE_TRIGGERS:
            if remaining.lstrip().lower().startswith(trigger):
                return '<wintitle>' + word + '</wintitle>'
        for trigger in UICONTROL_TRIGGERS:
            if remaining.lstrip().lower().startswith(trigger):
                return '<uicontrol>' + word + '</uicontrol>'

        # No trigger word follows — this bold word is a standalone UI element
        return '<uicontrol>' + word + '</uicontrol>'

    result = re.sub(r'\{\{BOLD:(.*?)\}\}', _contextual_bold, result)
    return result


def _apply_menucascade(text):
    """Apply <menucascade> tags when '>' (escaped as &gt;) is used to define a path.

    Example: 'Navigate to Settings &gt; Label Configuration &gt; Printers'
    The path 'Settings > Label Configuration > Printers' is wrapped in menucascade.

    Only used in task files.
    """
    # Match: word(s) &gt; word(s) [&gt; word(s)]...
    # Stop each segment at the next &gt; or at punctuation/end
    pattern = re.compile(
        r'((?:[A-Za-z][\w]*(?:\s+[A-Za-z][\w]*)*)'  # first segment
        r'(?:\s*&gt;\s*(?:[A-Za-z][\w]*(?:\s+[A-Za-z][\w]*)*))+)'  # subsequent segments
    )

    def _menucascade_replacer(m):
        full = m.group(0).strip()
        parts = re.split(r'\s*&gt;\s*', full)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 2:
            return m.group(0)
        inner = "".join(
            "<uicontrol>" + p + "</uicontrol>" for p in parts
        )
        return "<menucascade>" + inner + "</menucascade>"

    return pattern.sub(_menucascade_replacer, text)


# =============================================================================
# BLOCK-LEVEL PARSING HELPERS
# =============================================================================

def _is_note_line(line):
    """Check if a line starts a note block. Supports typed notes."""
    return bool(re.match(
        r'^(Note|NOTE|note|Warning|WARNING|warning|Caution|CAUTION|caution'
        r'|Danger|DANGER|danger|Tip|TIP|tip|Important|IMPORTANT|important)\s*[:.]?\s*',
        line
    ))


def _get_note_type(line):
    """Get the note type attribute from a note line prefix.

    Returns: tuple (type_attr_string, stripped_content)
    type_attr_string is '' for regular notes, ' type="warning"' etc for typed notes.
    """
    patterns = [
        (r'^(Warning|WARNING|warning)\s*[:.]?\s*', ' type="warning"'),
        (r'^(Caution|CAUTION|caution)\s*[:.]?\s*', ' type="caution"'),
        (r'^(Danger|DANGER|danger)\s*[:.]?\s*', ' type="danger"'),
        (r'^(Tip|TIP|tip)\s*[:.]?\s*', ' type="tip"'),
        (r'^(Important|IMPORTANT|important)\s*[:.]?\s*', ' type="important"'),
        (r'^(Note|NOTE|note)\s*[:.]?\s*', ''),
    ]
    for pat, type_attr in patterns:
        m = re.match(pat, line)
        if m:
            return type_attr, line[m.end():]
    return '', line


def _strip_note_prefix(line):
    """Remove the note type prefix from a note line."""
    _, content = _get_note_type(line)
    return content


def _is_ordered_list_item(line):
    """Check if a line is a numbered list item."""
    return bool(re.match(r'^\d+[\.\)]\s+', line))


def _strip_ordered_prefix(line):
    """Remove the number prefix from an ordered list item."""
    return re.sub(r'^\d+[\.\)]\s+', '', line)


def _is_unordered_list_item(line):
    """Check if a line is a bullet list item.

    Recognizes common bullet characters from Word, Google Docs, and plain text:
    - Hyphen (-), asterisk (*), plus (+)
    - Bullet (•), triangular bullet (‣), white bullet (◦)
    - Middle dot (·), en-dash (–), em-dash (—)
    - Small circle (o) followed by space (Word-style)
    Handles multiple spaces/tabs between bullet and text.
    """
    return bool(re.match(
        r'^[\-\*\+\u2022\u2023\u25E6\u00B7\u2013\u2014\u25AA\u25AB\u27A2]\s+', line
    )) or bool(re.match(r'^o\s+\S', line))


def _strip_unordered_prefix(line):
    """Remove the bullet prefix from an unordered list item."""
    result = re.sub(r'^[\-\*\+\u2022\u2023\u25E6\u00B7\u2013\u2014\u25AA\u25AB\u27A2]\s+', '', line)
    if result == line:
        result = re.sub(r'^o\s+', '', line)
    return result


def _is_heading_line(line):
    """Check if a line appears to be a heading.

    Only treats lines as headings if they came from HTML heading tags
    (preprocessed to ALL CAPS by _preprocess_html_input).
    Plain text that happens to be short or title-case is NOT treated as a heading
    to avoid creating unnecessary sections.
    """
    stripped = line.strip()
    if not stripped:
        return False
    # Only detect as heading if ALL CAPS (from HTML preprocessing of <h1>-<h6>)
    if (stripped == stripped.upper()
            and len(stripped) > 2
            and stripped != stripped.lower()
            and len(stripped.split()) <= 10
            and not stripped.endswith(('.', ',', ';', ':'))):
        return True
    return False


def _is_table_line(line):
    """Check if a line appears to be part of a table (pipe-delimited)."""
    return '|' in line and line.count('|') >= 2


def _is_dl_block_start(line):
    """Check if a line starts a definition list pattern (field name on its own line)."""
    # A short line (< 60 chars) followed by a longer description line
    return len(line.strip()) < 60 and line.strip() and not line.strip().endswith('.')


def _parse_table_block(lines, start_idx):
    """Parse a table block starting from start_idx. Returns (xml_string, end_idx)."""
    table_lines = []
    idx = start_idx
    while idx < len(lines) and _is_table_line(lines[idx]):
        table_lines.append(lines[idx])
        idx += 1

    if not table_lines:
        return "", start_idx

    # Parse header and rows
    xml = "<table>\n<tgroup>\n"

    # First row is header
    header_cells = [c.strip() for c in table_lines[0].split('|') if c.strip()]
    num_cols = len(header_cells)
    xml += f'<colspec colnum="1" colname="col1"/>\n' * 0  # skip colspec for simplicity

    xml += "<thead>\n<row>\n"
    for cell in header_cells:
        xml += "  <entry>" + xml_escape(cell) + "</entry>\n"
    xml += "</row>\n</thead>\n"

    # Remaining rows (skip separator lines like |---|---|)
    xml += "<tbody>\n"
    for row_line in table_lines[1:]:
        cells = [c.strip() for c in row_line.split('|') if c.strip()]
        # Skip separator rows
        if all(re.match(r'^[\-=:]+$', c) for c in cells):
            continue
        xml += "<row>\n"
        for cell in cells:
            xml += "  <entry>" + xml_escape(cell) + "</entry>\n"
        xml += "</row>\n"
    xml += "</tbody>\n</tgroup>\n</table>\n"

    return xml, idx


# =============================================================================
# CONCEPT CONVERSION
# =============================================================================

def generate_concept_xml(text):
    """Generate DITA <conbody> XML from input text.

    Rules:
    - Only outputs <conbody> content
    - Never uses <b>, <para>, or <menucascade>
    - Applies <uicontrol>, <wintitle>, <userinput> inline tags
    - Handles notes, ordered/unordered lists, tables, definition lists
    - Creates <section> only when headings are detected
    - Never divides paragraphs into <section>
    - Does not modify the input language or structure
    """
    # Preprocess HTML input if detected
    text = _preprocess_html_input(text)

    lines = text.split('\n')
    xml_parts = []
    idx = 0
    in_section = False

    while idx < len(lines):
        line = lines[idx].rstrip()

        # Skip empty lines
        if not line.strip():
            idx += 1
            continue

        # Check for table block
        if _is_table_line(line):
            table_xml, idx = _parse_table_block(lines, idx)
            xml_parts.append(table_xml)
            continue

        # Check for note
        if _is_note_line(line):
            note_type_attr, note_content = _get_note_type(line)
            idx += 1
            # Collect continuation lines for the note
            while idx < len(lines) and lines[idx].strip() and not _is_note_line(lines[idx]):
                if _is_ordered_list_item(lines[idx]) or _is_unordered_list_item(lines[idx]):
                    break
                note_content += " " + lines[idx].strip()
                idx += 1
            # Check if note has list items following
            note_xml = "<note" + note_type_attr + ">" + _apply_inline_tags(note_content, is_task=False)
            # Collect list items inside the note
            if idx < len(lines) and (_is_ordered_list_item(lines[idx]) or _is_unordered_list_item(lines[idx])):
                list_xml, idx = _parse_list_in_note(lines, idx)
                note_xml += "\n" + list_xml
            note_xml += "</note>\n"
            xml_parts.append(note_xml)
            continue

        # Check for ordered list
        if _is_ordered_list_item(line):
            list_xml, idx = _parse_ordered_list(lines, idx, is_task=False)
            xml_parts.append(list_xml)
            continue

        # Check for unordered list
        if _is_unordered_list_item(line):
            list_xml, idx = _parse_unordered_list(lines, idx, is_task=False)
            xml_parts.append(list_xml)
            continue

        # Check for section title (bold standalone line from pasted content)
        # Only create a section if bold line is followed by 2+ paragraphs of content
        # (not just a single description line, which indicates a field definition)
        bold_title_match = re.match(r'^\s*\{\{BOLD:(.*?)\}\}\s*$', line)
        if bold_title_match:
            title_text = bold_title_match.group(1)
            # Look ahead: count content lines before next bold line or end
            content_lines_ahead = 0
            peek = idx + 1
            while peek < len(lines):
                peek_line = lines[peek].strip()
                if not peek_line:
                    peek += 1
                    continue
                if re.match(r'^\s*\{\{BOLD:.*\}\}\s*$', peek_line) or _is_heading_line(peek_line):
                    break
                content_lines_ahead += 1
                peek += 1
            # Section title: 2+ content lines ahead (substantial content)
            if content_lines_ahead >= 2:
                if in_section:
                    xml_parts.append("</section>\n")
                xml_parts.append('<section>\n<title>' + xml_escape(title_text) + '</title>\n')
                in_section = True
                idx += 1
                continue
            else:
                # Field definition: bold name + single description = just paragraphs
                xml_parts.append("<p><uicontrol>" + xml_escape(title_text) + "</uicontrol></p>\n")
                idx += 1
                continue

        # Check for section title (from ALL CAPS heading preprocessing)
        if _is_heading_line(line):
            if in_section:
                xml_parts.append("</section>\n")
            xml_parts.append('<section>\n<title>' + xml_escape(line.strip()) + '</title>\n')
            in_section = True
            idx += 1
            continue

        # Default: paragraph
        xml_parts.append("<p>" + _apply_inline_tags(line.strip(), is_task=False) + "</p>\n")
        idx += 1

    if in_section:
        xml_parts.append("</section>\n")

    result = "<conbody>\n" + "".join(xml_parts) + "</conbody>"
    # Clean up any unresolved bold markers that leaked through
    result = re.sub(r'\{\{BOLD:(.*?)\}\}', r'<uicontrol>\1</uicontrol>', result)
    return result


def _parse_ordered_list(lines, start_idx, is_task=False):
    """Parse consecutive ordered list items into <ol> XML.
    Skips blank lines between items (common in Word paste).
    """
    xml = "<ol>\n"
    idx = start_idx
    while idx < len(lines):
        if _is_ordered_list_item(lines[idx]):
            content = _strip_ordered_prefix(lines[idx]).strip()
            xml += "<li>" + _apply_inline_tags(content, is_task=is_task) + "</li>\n"
            idx += 1
        elif not lines[idx].strip():
            peek = idx + 1
            while peek < len(lines) and not lines[peek].strip():
                peek += 1
            if peek < len(lines) and _is_ordered_list_item(lines[peek]):
                idx = peek
            else:
                break
        else:
            break
    xml += "</ol>\n"
    return xml, idx


def _parse_unordered_list(lines, start_idx, is_task=False):
    """Parse consecutive unordered list items into <ul> XML.
    Skips blank lines between items (common in Word paste).
    """
    xml = "<ul>\n"
    idx = start_idx
    while idx < len(lines):
        if _is_unordered_list_item(lines[idx]):
            content = _strip_unordered_prefix(lines[idx]).strip()
            xml += "<li>" + _apply_inline_tags(content, is_task=is_task) + "</li>\n"
            idx += 1
        elif not lines[idx].strip():
            # Blank line — check if next non-blank line is still a list item
            peek = idx + 1
            while peek < len(lines) and not lines[peek].strip():
                peek += 1
            if peek < len(lines) and _is_unordered_list_item(lines[peek]):
                idx = peek  # Skip blank lines, continue collecting
            else:
                break  # End of list
        else:
            break
    xml += "</ul>\n"
    return xml, idx


def _parse_list_in_note(lines, start_idx):
    """Parse list items that appear inside a note block."""
    idx = start_idx
    if _is_ordered_list_item(lines[idx]):
        xml = "<ol>\n"
        while idx < len(lines) and _is_ordered_list_item(lines[idx]):
            content = _strip_ordered_prefix(lines[idx]).strip()
            xml += "<li>" + xml_escape(content) + "</li>\n"
            idx += 1
        xml += "</ol>\n"
    elif _is_unordered_list_item(lines[idx]):
        xml = "<ul>\n"
        while idx < len(lines) and _is_unordered_list_item(lines[idx]):
            content = _strip_unordered_prefix(lines[idx]).strip()
            xml += "<li>" + xml_escape(content) + "</li>\n"
            idx += 1
        xml += "</ul>\n"
    else:
        xml = ""
    return xml, idx


def _is_dl_candidate(lines, idx):
    """Check if current position looks like a definition list.

    Pattern: a short line (field name) followed by an indented or longer
    description line, repeating.
    """
    if idx + 1 >= len(lines):
        return False
    current = lines[idx].strip()
    next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
    # Short label (< 60 chars, no period at end) followed by a description
    if (current and len(current) < 60 and not current.endswith('.')
            and not _is_ordered_list_item(current)
            and not _is_unordered_list_item(current)
            and not _is_note_line(current)
            and next_line and len(next_line) > len(current)
            and not _is_heading_line(current)):
        # Check if the next line looks like a description (starts lowercase or is longer)
        if next_line[0].islower() or len(next_line) > 60:
            return True
    return False


def _parse_definition_list(lines, idx, is_task=False):
    """Parse a definition list (field name + description pairs) into <dl> XML."""
    xml = "<dl>\n"
    while idx < len(lines):
        term_line = lines[idx].strip()
        if not term_line:
            idx += 1
            continue

        # Check if this still looks like a DL entry
        if idx + 1 >= len(lines):
            break
        next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
        if not (term_line and len(term_line) < 60 and not term_line.endswith('.')
                and next_line and (next_line[0].islower() or len(next_line) > 60)):
            break

        # Term
        xml += "<dlentry>\n"
        xml += "<dt>" + _apply_inline_tags(term_line, is_task=is_task) + "</dt>\n"
        idx += 1

        # Description (collect continuation lines)
        desc_parts = []
        while idx < len(lines) and lines[idx].strip():
            desc_line = lines[idx].strip()
            # Stop if we hit another short label (next DL entry)
            if (len(desc_line) < 60 and not desc_line.endswith('.')
                    and idx + 1 < len(lines) and lines[idx + 1].strip()
                    and (lines[idx + 1].strip()[0].islower() or len(lines[idx + 1].strip()) > 60)):
                break
            # Check for note inside description
            if _is_note_line(desc_line):
                note_text = _strip_note_prefix(desc_line)
                desc_parts.append("<note>" + xml_escape(note_text) + "</note>")
                idx += 1
                continue
            # Check for list inside description
            if _is_unordered_list_item(desc_line):
                list_xml, idx = _parse_unordered_list(lines, idx, is_task=is_task)
                desc_parts.append(list_xml)
                continue
            if _is_ordered_list_item(desc_line):
                list_xml, idx = _parse_ordered_list(lines, idx, is_task=is_task)
                desc_parts.append(list_xml)
                continue
            desc_parts.append(_apply_inline_tags(desc_line, is_task=is_task))
            idx += 1

        xml += "<dd>" + " ".join(desc_parts) + "</dd>\n"
        xml += "</dlentry>\n"

        # Skip blank lines between entries
        while idx < len(lines) and not lines[idx].strip():
            idx += 1

    xml += "</dl>\n"
    return xml, idx


# =============================================================================
# TASK CONVERSION
# =============================================================================

def generate_task_xml(text):
    """Generate DITA <taskbody> XML from input text.

    Rules:
    - Only outputs <taskbody> content
    - Uses <shortdesc> for the opening sentence before steps
    - Uses <steps>/<step>/<cmd> for numbered instructions
    - Uses <menucascade> for ">" paths
    - Uses <fieldlist>/<field>/<fieldname>/<fielddesc> for field definitions
    - Uses <info> for additional content within a step
    - Applies <uicontrol>, <wintitle>, <userinput> inline tags
    - Handles notes (no <p> inside), lists inside <info>
    - Never nests <step> inside <step>
    - Does not modify the input language or structure
    """
    # Preprocess HTML input if detected
    text = _preprocess_html_input(text)

    lines = text.split('\n')
    xml_parts = []
    idx = 0
    has_steps = False
    in_steps = False

    # Look for the first numbered step to determine where shortdesc ends
    first_step_idx = None
    for i, line in enumerate(lines):
        if _is_ordered_list_item(line.strip()):
            first_step_idx = i
            break

    # Extract shortdesc (opening content before steps)
    if first_step_idx is not None and first_step_idx > 0:
        shortdesc_lines = []
        for i in range(first_step_idx):
            if lines[i].strip():
                shortdesc_lines.append(lines[i].strip())
        if shortdesc_lines:
            shortdesc_text = " ".join(shortdesc_lines)
            xml_parts.append("<shortdesc>" + _apply_inline_tags(shortdesc_text, is_task=True) + "</shortdesc>\n")
        idx = first_step_idx
    elif first_step_idx is None:
        # No numbered steps found — treat all content as steps-unordered or context
        # Try to find the first meaningful paragraph as shortdesc
        for i, line in enumerate(lines):
            if line.strip():
                xml_parts.append("<shortdesc>" + _apply_inline_tags(line.strip(), is_task=True) + "</shortdesc>\n")
                idx = i + 1
                break

    # Parse steps and content
    xml_parts.append("<steps>\n")
    in_steps = True

    while idx < len(lines):
        line = lines[idx].rstrip()

        # Skip empty lines
        if not line.strip():
            idx += 1
            continue

        # Numbered step
        if _is_ordered_list_item(line.strip()):
            cmd_text = _strip_ordered_prefix(line.strip()).strip()
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>" + _apply_inline_tags(cmd_text, is_task=True) + "</cmd>\n")
            idx += 1

            # Check for sub-content within this step (info, fieldlist, notes, lists)
            step_info = _parse_step_info(lines, idx)
            if step_info["xml"]:
                xml_parts.append(step_info["xml"])
            idx = step_info["end_idx"]

            xml_parts.append("</step>\n")
            has_steps = True
            continue

        # Non-step content after steps started — wrap in a step with info
        if in_steps:
            # This might be additional context; create a step for it
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>" + _apply_inline_tags(line.strip(), is_task=True) + "</cmd>\n")
            idx += 1
            xml_parts.append("</step>\n")
            continue

        idx += 1

    if in_steps:
        xml_parts.append("</steps>\n")

    return "<taskbody>\n" + "".join(xml_parts) + "</taskbody>"


def _parse_step_info(lines, start_idx):
    """Parse additional content following a step's <cmd>.

    Returns dict with 'xml' (string) and 'end_idx' (int).
    Handles: field lists, notes, sub-lists, additional paragraphs.
    """
    idx = start_idx
    info_parts = []
    has_fieldlist = False

    while idx < len(lines):
        line = lines[idx].rstrip()

        # Stop at next numbered step or empty line followed by numbered step
        if _is_ordered_list_item(line.strip()):
            break
        if not line.strip():
            # Check if next non-empty line is a step
            peek = idx + 1
            while peek < len(lines) and not lines[peek].strip():
                peek += 1
            if peek >= len(lines) or _is_ordered_list_item(lines[peek].strip()):
                break
            idx += 1
            continue

        # Note inside step
        if _is_note_line(line.strip()):
            note_type_attr, note_content = _get_note_type(line.strip())
            idx += 1
            while idx < len(lines) and lines[idx].strip() and not _is_note_line(lines[idx].strip()):
                if _is_ordered_list_item(lines[idx].strip()) or _is_unordered_list_item(lines[idx].strip()):
                    break
                note_content += " " + lines[idx].strip()
                idx += 1
            note_xml = "<note" + note_type_attr + ">" + _apply_inline_tags(note_content, is_task=True)
            if idx < len(lines) and (_is_ordered_list_item(lines[idx].strip()) or _is_unordered_list_item(lines[idx].strip())):
                list_xml, idx = _parse_list_in_note(lines, idx)
                note_xml += "\n" + list_xml
            note_xml += "</note>\n"
            info_parts.append(note_xml)
            continue

        # Unordered list inside step
        if _is_unordered_list_item(line.strip()):
            list_xml, idx = _parse_unordered_list(lines, idx, is_task=True)
            info_parts.append(list_xml)
            continue

        # Field list detection (pattern: short label then description)
        if _is_fieldlist_candidate(lines, idx):
            fl_xml, idx = _parse_fieldlist(lines, idx)
            info_parts.append(fl_xml)
            has_fieldlist = True
            continue

        # Regular info paragraph
        info_parts.append("<p>" + _apply_inline_tags(line.strip(), is_task=True) + "</p>\n")
        idx += 1

    xml = ""
    if info_parts:
        xml = "<info>\n" + "".join(info_parts) + "</info>\n"

    return {"xml": xml, "end_idx": idx}


def _is_fieldlist_candidate(lines, idx):
    """Check if current position starts a field list in task context.

    Field lists are identified by a short label line followed by a
    description line, typically after 'specify this information' or similar.
    """
    if idx + 1 >= len(lines):
        return False
    current = lines[idx].strip()
    next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
    # Short label (< 50 chars, no period, typically a field name)
    if (current and len(current) < 50 and not current.endswith('.')
            and not _is_ordered_list_item(current)
            and not _is_unordered_list_item(current)
            and not _is_note_line(current)
            and next_line and len(next_line) > len(current)):
        return True
    return False


def _parse_fieldlist(lines, idx):
    """Parse a field list into <fieldlist> XML for task files.

    Structure:
    <fieldlist>
      <field>
        <fieldname><uicontrol>Name</uicontrol></fieldname>
        <fielddesc>Description text</fielddesc>
      </field>
    </fieldlist>
    """
    xml = "<fieldlist>\n"
    while idx < len(lines):
        term_line = lines[idx].strip()
        if not term_line:
            idx += 1
            continue

        # Check if this still looks like a field entry
        if idx + 1 >= len(lines):
            break
        next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
        if not (term_line and len(term_line) < 50 and not term_line.endswith('.')
                and next_line and len(next_line) > len(term_line)):
            break

        # Field name
        xml += "<field>\n"
        xml += "<fieldname><uicontrol>" + xml_escape(term_line) + "</uicontrol></fieldname>\n"
        idx += 1

        # Field description (collect continuation lines)
        desc_parts = []
        while idx < len(lines) and lines[idx].strip():
            desc_line = lines[idx].strip()
            # Stop if we hit another short label (next field entry)
            if (len(desc_line) < 50 and not desc_line.endswith('.')
                    and idx + 1 < len(lines) and lines[idx + 1].strip()
                    and len(lines[idx + 1].strip()) > len(desc_line)):
                break
            # Stop if we hit a numbered step
            if _is_ordered_list_item(desc_line):
                break
            # Handle note inside field description
            if _is_note_line(desc_line):
                note_text = _strip_note_prefix(desc_line)
                desc_parts.append("<note>" + xml_escape(note_text) + "</note>")
                idx += 1
                continue
            desc_parts.append(_apply_inline_tags(desc_line, is_task=True))
            idx += 1

        xml += "<fielddesc>" + " ".join(desc_parts) + "</fielddesc>\n"
        xml += "</field>\n"

        # Skip blank lines between entries
        while idx < len(lines) and not lines[idx].strip():
            idx += 1

    xml += "</fieldlist>\n"
    return xml, idx
