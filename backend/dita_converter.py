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
- <uicontrol> for CamelCase UI identifiers (e.g. FTSFMachineRunning); paths/filenames are left untouched
- <note> whenever "Note:" (or Warning/Caution/etc.) appears, even mid-paragraph
- Original letter casing is preserved (headings are NOT forced to upper case)
- Sentences and continuous words are never split for tagging
- <wintitle> for words before: screen, window, session, dialogue box, panel, section
- <userinput> for words after: set to, as
- <note> for note blocks (no <p> inside)
- <ol>, <ul> for lists
- <dl>/<dlentry>/<dt>/<dd> for field definitions in concept
- <codeph> for inline code spans; <codeblock> for multi-line code
- <section> only when explicitly needed
- <menucascade> for ">" paths in task files
- <fieldlist>/<field>/<fieldname>/<fielddesc> for task field lists
- <shortdesc> for opening sentence in tasks
- Never uses <b>, <para>, or <menucascade> in concept files
"""

import re


def _process_table_cell(cell_html):
    """Process HTML content inside a table cell into DITA-compatible content.

    Handles:
    - Plain text paragraphs → wrapped in <p>
    - Bullet lists → <ul><li>
    - Numbered lists → <ol><li>
    - Notes → <note>
    - Bold text → <uicontrol>
    - Line breaks → separate <p> elements
    """
    if not cell_html or not cell_html.strip():
        return ''

    # Convert lists inside the cell
    cell = cell_html

    # Convert <ul><li> — preserve bold inside list items
    cell = re.sub(r'</ul>\s*<ul[^>]*>', '', cell, flags=re.IGNORECASE)
    def _cell_ul(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(0), re.DOTALL | re.IGNORECASE)
        parts = []
        for item in items:
            # Convert bold to uicontrol, then strip remaining tags
            item_text = re.sub(r'<(strong|b)\b[^>]*>(.*?)</\1>', r'<uicontrol>\2</uicontrol>', item, flags=re.DOTALL | re.IGNORECASE)
            item_text = re.sub(r'<(?!/?uicontrol)[^>]+>', '', item_text)
            item_text = item_text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
            # Re-escape for XML safety
            item_text = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', item_text)
            item_text = re.sub(r'<([A-Z][A-Z0-9/,\s]*[A-Z0-9/])>', r'&lt;\1&gt;', item_text)
            parts.append('<li>' + item_text.strip() + '</li>')
        return '<ul>' + ''.join(parts) + '</ul>'
    cell = re.sub(r'<ul[^>]*>.*?</ul>', _cell_ul, cell, flags=re.DOTALL | re.IGNORECASE)

    # Convert <ol><li> — preserve bold inside list items
    cell = re.sub(r'</ol>\s*<ol[^>]*>', '', cell, flags=re.IGNORECASE)
    def _cell_ol(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(0), re.DOTALL | re.IGNORECASE)
        parts = []
        for item in items:
            item_text = re.sub(r'<(strong|b)\b[^>]*>(.*?)</\1>', r'<uicontrol>\2</uicontrol>', item, flags=re.DOTALL | re.IGNORECASE)
            item_text = re.sub(r'<(?!/?uicontrol)[^>]+>', '', item_text)
            item_text = item_text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
            item_text = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', item_text)
            item_text = re.sub(r'<([A-Z][A-Z0-9/,\s]*[A-Z0-9/])>', r'&lt;\1&gt;', item_text)
            parts.append('<li>' + item_text.strip() + '</li>')
        return '<ol>' + ''.join(parts) + '</ol>'
    cell = re.sub(r'<ol[^>]*>.*?</ol>', _cell_ol, cell, flags=re.DOTALL | re.IGNORECASE)

    # Convert bold/strong to <uicontrol> markers BEFORE stripping other tags
    cell = re.sub(r'<(strong|b)\b[^>]*>(.*?)</\1>', r'<uicontrol>\2</uicontrol>', cell, flags=re.DOTALL | re.IGNORECASE)

    # Convert <br> to newlines for processing
    cell = re.sub(r'<br\s*/?\s*>', '\n', cell, flags=re.IGNORECASE)
    # Convert block elements
    cell = re.sub(r'</p>', '\n', cell, flags=re.IGNORECASE)
    cell = re.sub(r'<p[^>]*>', '', cell, flags=re.IGNORECASE)

    # Preserve <ul>, <ol>, <uicontrol>, <note> tags — strip all other HTML
    cell = re.sub(r'<(?!/?(?:ul|ol|li|note|uicontrol))[^>]+>', '', cell)

    # Normalize line endings and decode entities
    cell = cell.replace('\r\n', '\n').replace('\r', '\n')
    cell = cell.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')

    # Escape angle-bracket codes that look like abbreviations (e.g., <CR>, <MO>, <DO/RO>)
    # These are NOT HTML tags — they're content codes that must be preserved as text.
    # Match < followed by uppercase letters/slashes/commas/spaces (not valid HTML tag patterns)
    cell = re.sub(r'<([A-Z][A-Z0-9/,\s]*[A-Z0-9/])>', r'&lt;\1&gt;', cell)
    # Also catch unclosed angle brackets like "<DO " or "<MO," that lack closing >
    cell = re.sub(r'<([A-Z]{2,}(?:[/,][A-Z]{2,})*)(?=[\s,;.\)]|$)', r'&lt;\1', cell)

    # Escape bare & that are not already part of an entity reference
    # This must happen AFTER the angle-bracket escaping (which introduces &lt; and &gt;)
    cell = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', cell)

    # Handle Note: prefix
    lines_list = cell.split('\n')
    processed_lines = []
    for l in lines_list:
        note_match = re.match(r'^(Note|Warning|Caution|Tip|Important)\s*[:.]?\s*(.*)', l.strip(), re.IGNORECASE)
        if note_match:
            note_type = note_match.group(1).lower()
            note_content = note_match.group(2)
            if note_type == 'note':
                processed_lines.append('<note>' + note_content + '</note>')
            else:
                processed_lines.append('<note type="' + note_type + '">' + note_content + '</note>')
        else:
            processed_lines.append(l)
    cell = '\n'.join(processed_lines)

    # Clean up whitespace
    cell = re.sub(r'\n{3,}', '\n\n', cell).strip()

    # Wrap cell content lines in <p> tags (each line = separate paragraph)
    lines = cell.split('\n')
    # Filter empty lines
    non_empty = [l.strip() for l in lines if l.strip()]
    if not non_empty:
        return ''
    if len(non_empty) == 1:
        content = non_empty[0]
        # Don't wrap in <p> if it's already a list or note
        if content.startswith('<ul>') or content.startswith('<ol>') or content.startswith('<note'):
            return content
        # Check for bullet marker in single line
        bullet_match = re.match(r'^[\-\*\+\u2022\u2023\u25E6\u00B7\u2013\u2014]\s+(.+)', content)
        if bullet_match:
            return '<ul><li>' + bullet_match.group(1) + '</li></ul>'
        # Single text — wrap in <p>
        return '<p>' + content + '</p>'
    else:
        # Multiple lines — wrap each in <p>, keep lists/notes/bullets as-is
        result = ''
        bullet_buffer = []  # Collect consecutive bullets into one <ul>
        for line in non_empty:
            # Check if it's a bullet line
            bullet_match = re.match(r'^[\-\*\+\u2022\u2023\u25E6\u00B7\u2013\u2014]\s+(.+)', line)

            if line.startswith('<ul>') or line.startswith('<ol>') or line.startswith('<note'):
                # Flush bullet buffer first
                if bullet_buffer:
                    result += '<ul>' + ''.join('<li>' + b + '</li>' for b in bullet_buffer) + '</ul>'
                    bullet_buffer = []
                result += line
            elif bullet_match:
                bullet_buffer.append(bullet_match.group(1))
            else:
                # Flush bullet buffer
                if bullet_buffer:
                    result += '<ul>' + ''.join('<li>' + b + '</li>' for b in bullet_buffer) + '</ul>'
                    bullet_buffer = []
                result += '<p>' + line + '</p>'
        # Flush remaining bullets
        if bullet_buffer:
            result += '<ul>' + ''.join('<li>' + b + '</li>' for b in bullet_buffer) + '</ul>'
        return result


# =============================================================================
# HTML INPUT PREPROCESSING
# =============================================================================

def _preprocess_markdown_bold(text):
    """Convert markdown-style **bold** to {{BOLD:...}} markers.

    This handles plain text input where bold is indicated with ** delimiters.
    Strips trailing colons from the bold text (colon stays outside the marker).
    Merges adjacent bold markers like **Word1** **Word2** into one.
    Handles bold text that spans line breaks (joins them with space).
    """
    if not text or '**' not in text:
        return text

    # First merge adjacent bold markers: **Word1** **Word2** → **Word1 Word2**
    text = re.sub(r'\*\*(.+?)\*\*\s*\*\*(.+?)\*\*', r'**\1 \2**', text)
    text = re.sub(r'\*\*(.+?)\*\*\s*\*\*(.+?)\*\*', r'**\1 \2**', text)

    # Handle bold spanning line breaks: **text\nmore text** → **text more text**
    # Match ** ... ** allowing newlines inside, then collapse whitespace
    def _md_bold_replacer(m):
        content = m.group(1)
        # Collapse any newlines/extra whitespace inside the bold text
        content = re.sub(r'\s+', ' ', content).strip()
        if not content:
            return ''
        # If bold text ends with ':', move colon outside the marker
        if content.endswith(':'):
            return '{{BOLD:' + content[:-1] + '}}:'
        return '{{BOLD:' + content + '}}'

    # Use re.DOTALL so .+? matches across newlines
    result = re.sub(r'\*\*(.+?)\*\*', _md_bold_replacer, text, flags=re.DOTALL)
    # Remove empty bold markers (from stray ****)
    result = re.sub(r'\{\{BOLD:\s*\}\}', '', result)
    return result


def _preprocess_code_markers(text):
    """Convert markdown-style code into {{CODEPH:...}} / {{CODEBLOCK:...}} markers.

    - Fenced code blocks (```...```) become {{CODEBLOCK:...}} on their own line.
    - Inline `code` spans become {{CODEPH:...}} markers.

    The marker content is stored raw (not yet XML-escaped); escaping happens
    when the marker is resolved into a <codeph>/<codeblock> tag. Markers are
    placed on their own lines for codeblocks so the block-level parser can
    detect them.
    """
    if not text:
        return text

    # Fenced code blocks first: ```lang\n ... \n``` (multiline). Store raw content.
    def _fence_replacer(m):
        body = m.group(1)
        # Drop an optional language token on the opening fence line
        if '\n' in body:
            first, rest = body.split('\n', 1)
            if first.strip() and ' ' not in first.strip() and len(first.strip()) < 20:
                body = rest
        body = body.strip('\n')
        # Encode internal newlines so the marker stays on one logical line
        body = body.replace('\n', '{{NL}}')
        return '\n{{CODEBLOCK:' + body + '}}\n'

    text = re.sub(r'```(.*?)```', _fence_replacer, text, flags=re.DOTALL)

    # Inline code spans: `code` → {{CODEPH:code}} (single backticks, no newline inside)
    text = re.sub(r'`([^`\n]+?)`', lambda m: '{{CODEPH:' + m.group(1) + '}}', text)

    return text


def _looks_like_code_line(line):
    """Heuristic: a line that is essentially a standalone markup/code element.

    Matches things like:
        <ConfigurationSettings>
        <ftusername>sa</ftusername>
        <!-- a comment -->
        </machine>
    Ordinary prose containing a stray '<' (e.g. "Qty < 5") is NOT matched
    because it must START with '<' plus a tag-name/slash/bang/question char.
    """
    s = line.strip()
    if not s:
        return False
    return bool(re.match(r'^</?[A-Za-z!?][^\n]*>$', s)) or bool(re.match(r'^<!--.*-->$', s))


def _protect_literal_code_blocks(text):
    """Wrap contiguous runs of markup/code lines in {{CODEBLOCK:...}} markers.

    A run of 2+ consecutive code-looking lines (blank lines allowed between
    them) is treated as a code sample. This runs before HTML detection so a
    pasted XML block is preserved verbatim rather than parsed as HTML.
    """
    if '<' not in text:
        return text

    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    out = []
    i = 0
    n = len(lines)
    while i < n:
        if _looks_like_code_line(lines[i]):
            # Gather the run, allowing single blank lines between code lines
            block = []
            j = i
            while j < n:
                if _looks_like_code_line(lines[j]):
                    block.append(lines[j].rstrip())
                    j += 1
                elif lines[j].strip() == '':
                    # Allow one or more blank lines between code lines, as long
                    # as another code line follows before any non-code content.
                    k = j
                    while k < n and lines[k].strip() == '':
                        k += 1
                    if k < n and _looks_like_code_line(lines[k]):
                        block.append('')  # collapse internal blanks to one
                        j = k
                    else:
                        break
                else:
                    break
            # Only treat as a code block if it has at least 2 real code lines
            real = [b for b in block if b.strip()]
            if len(real) >= 2:
                body = '\n'.join(block).strip('\n')
                out.append('{{CODEBLOCK:' + body.replace('\n', '{{NL}}') + '}}')
                i = j
                continue
            # Otherwise fall through and emit the single line as-is
        out.append(lines[i])
        i += 1
    return '\n'.join(out)


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

    # Strip base64 embedded images FIRST (can be megabytes of data that choke regex)
    html_text = re.sub(r'src="data:image/[^"]*"', 'src=""', html_text)
    html_text = re.sub(r'src=\'data:image/[^\']*\'', "src=''", html_text)
    # Also strip any standalone base64 data blocks
    html_text = re.sub(r'data:image/[a-z+]+;base64,[A-Za-z0-9+/=\s]{100,}', '', html_text)

    # Check if this is actually HTML (has HTML tags like <p>, <div>, etc.)
    # A lone < in plain text (like "Qty < Safety") should NOT trigger HTML processing
    if not re.search(r'<(?:p|div|ul|ol|li|h[1-6]|strong|em|b|i|table|br|span|a)\b', html_text, re.IGNORECASE):
        # Not HTML — protect literal code blocks, then handle markdown code
        # fences/inline code, then bold.
        plain = _protect_literal_code_blocks(html_text)
        plain = _preprocess_code_markers(plain)
        return _preprocess_markdown_bold(plain)

    # Use regex-based HTML parsing (no external dependencies)
    text = html_text

    # Remove style, script, and head tags entirely
    text = re.sub(r'<(style|script|head)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Preserve code content BEFORE other tags are stripped.
    # <pre> (optionally wrapping <code>) → multi-line code block.
    def _pre_replacer(m):
        inner = m.group(1)
        # Unwrap a nested <code> element if present
        inner = re.sub(r'</?code[^>]*>', '', inner, flags=re.IGNORECASE)
        body = _strip_tags(inner)
        body = body.replace('\r\n', '\n').replace('\r', '\n').strip('\n')
        body = body.replace('\n', '{{NL}}')
        return '\n{{CODEBLOCK:' + body + '}}\n'

    text = re.sub(r'<pre[^>]*>(.*?)</pre>', _pre_replacer, text, flags=re.DOTALL | re.IGNORECASE)

    # Inline code elements → {{CODEPH:...}} markers.
    def _codeph_replacer(m):
        body = re.sub(r'\s+', ' ', _strip_tags(m.group(1))).strip()
        if not body:
            return ''
        return '{{CODEPH:' + body + '}}'

    text = re.sub(r'<(?:code|tt|kbd|samp)\b[^>]*>(.*?)</(?:code|tt|kbd|samp)>',
                  _codeph_replacer, text, flags=re.DOTALL | re.IGNORECASE)

    # Convert headings to marked lines (detected as section titles later).
    # Preserve the ORIGINAL casing — do not force upper case.
    for level in range(1, 7):
        text = re.sub(
            r'<h' + str(level) + r'[^>]*>(.*?)</h' + str(level) + r'>',
            lambda m: '\n{{HEADING:' + re.sub(r'\s+', ' ', _strip_tags(m.group(1))).strip() + '}}\n',
            text, flags=re.DOTALL | re.IGNORECASE
        )

    # Preserve bold/strong text with markers so the converter can detect them
    # Bold words are potential candidates for <uicontrol> or <wintitle>
    # Use re.DOTALL to handle bold spanning multiple elements
    text = re.sub(
        r'<(strong|b)\b[^>]*>(.*?)</\1>',
        lambda m: '{{BOLD:' + re.sub(r'\s+', ' ', _strip_tags(m.group(2))).strip() + '}}',
        text, flags=re.DOTALL | re.IGNORECASE
    )

    # Convert <br> to newlines BEFORE list processing so that a field name and
    # its description separated by <br> inside an <li> land on separate lines.
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)

    def _split_li_lines(item_html):
        """Return the text lines of an <li>, splitting on internal newlines."""
        item_text = _strip_tags(item_html)
        return [ln.strip() for ln in item_text.split('\n') if ln.strip()]

    def _convert_ol(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), re.DOTALL | re.IGNORECASE)
        result = '\n'
        for i, item in enumerate(items, 1):
            lines_ = _split_li_lines(item)
            if not lines_:
                continue
            result += str(i) + '. ' + lines_[0] + '\n'
            for extra in lines_[1:]:
                result += extra + '\n'
        return result + '\n'

    def _convert_ul(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), re.DOTALL | re.IGNORECASE)
        result = '\n'
        for item in items:
            lines_ = _split_li_lines(item)
            if not lines_:
                continue
            result += '- ' + lines_[0] + '\n'
            for extra in lines_[1:]:
                result += extra + '\n'
        return result + '\n'

    # Convert lists INNERMOST-FIRST: repeatedly convert any <ul>/<ol> that has
    # no nested list inside it. This correctly handles nested value lists
    # (e.g. Running/Down/Idle under a Status field) without the outer regex
    # stopping at the first inner </ul>.
    for _ in range(10):
        before = text
        # Merge adjacent same-type lists first (Word emits one <ul> per bullet)
        text = re.sub(r'</ol>\s*<ol[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</ul>\s*<ul[^>]*>', '', text, flags=re.IGNORECASE)
        # Innermost = a list whose body contains no further <ul>/<ol>
        text = re.sub(r'<ol[^>]*>((?:(?!<(?:ul|ol)\b).)*?)</ol>',
                      _convert_ol, text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<ul[^>]*>((?:(?!<(?:ul|ol)\b).)*?)</ul>',
                      _convert_ul, text, flags=re.DOTALL | re.IGNORECASE)
        if text == before:
            break

    # Fallback: convert any lists that still remain (e.g. malformed nesting)
    text = re.sub(r'<ol[^>]*>(.*?)</ol>', _convert_ol, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<ul[^>]*>(.*?)</ul>', _convert_ul, text, flags=re.DOTALL | re.IGNORECASE)

    # Convert tables directly to DITA table XML format
    # This preserves complex cell content (notes, lists, multi-line text)
    def _convert_table_to_dita(m):
        table_html = m.group(0)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)
        if not rows:
            return ''

        # Determine number of columns from first row
        first_row_cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', rows[0], re.DOTALL | re.IGNORECASE)
        num_cols = len(first_row_cells)
        if num_cols == 0:
            return ''

        # Drop layout/spacer tables that carry no textual content (common in
        # Word/Docs paste). If every cell is empty after stripping tags, the
        # table is noise and would otherwise leak raw table XML into steps.
        all_cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', table_html, re.DOTALL | re.IGNORECASE)
        if not any(_strip_tags(c).strip() for c in all_cells):
            return ''

        xml = '\n{{DITA_TABLE_START}}\n'
        xml += '<table>\n'
        xml += '<tgroup cols="' + str(num_cols) + '">\n'
        for i in range(1, num_cols + 1):
            xml += '<colspec colname="col' + str(i) + '" colwidth="1*"/>\n'

        # Check if first row is header (contains <th> tags)
        is_header_row = bool(re.search(r'<th\b', rows[0], re.IGNORECASE))

        if is_header_row:
            xml += '<thead>\n<row>\n'
            for i, cell in enumerate(first_row_cells):
                cell_text = xml_escape(_strip_tags(cell).strip())
                xml += '<entry nameend="col' + str(i+1) + '" namest="col' + str(i+1) + '">' + cell_text + '</entry>\n'
            xml += '</row>\n</thead>\n'
            data_rows = rows[1:]
        else:
            # Treat first row as header if all cells are short AND look like column labels
            # (not numeric, not containing = signs which indicate values)
            all_short = all(len(_strip_tags(c).strip()) < 40 for c in first_row_cells)
            first_row_texts = [_strip_tags(c).strip() for c in first_row_cells]
            looks_like_data = any('=' in t or t.replace('.','').isdigit() or '\n' in _strip_tags(c) for t, c in zip(first_row_texts, first_row_cells))

            if all_short and len(rows) > 1 and not looks_like_data:
                xml += '<thead>\n<row>\n'
                for i, cell in enumerate(first_row_cells):
                    cell_text = xml_escape(_strip_tags(cell).strip())
                    xml += '<entry nameend="col' + str(i+1) + '" namest="col' + str(i+1) + '">' + cell_text + '</entry>\n'
                xml += '</row>\n</thead>\n'
                data_rows = rows[1:]
            elif num_cols == 4:
                # Default 4-column header for parameter tables
                xml += '<thead>\n<row>\n'
                xml += '<entry nameend="col1" namest="col1">Parameter Name</entry>\n'
                xml += '<entry nameend="col2" namest="col2">Values</entry>\n'
                xml += '<entry nameend="col3" namest="col3">Example</entry>\n'
                xml += '<entry nameend="col4" namest="col4">Default Value</entry>\n'
                xml += '</row>\n</thead>\n'
                data_rows = rows
            else:
                data_rows = rows

        xml += '<tbody>\n'
        for row in data_rows:
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL | re.IGNORECASE)
            xml += '<row>\n'
            for cell in cells:
                # Process cell content: preserve lists, notes, paragraphs
                cell_content = _process_table_cell(cell)
                # Final cleanup: ensure no raw newlines remain — wrap any unstructured lines in <p>
                if '\n' in cell_content:
                    parts = cell_content.split('\n')
                    cleaned = ''
                    for part in parts:
                        part = part.strip()
                        if not part:
                            continue
                        # Already structured content — keep as-is
                        if part.startswith('<p>') or part.startswith('<ul>') or part.startswith('<ol>') or part.startswith('<note') or part.startswith('</'):
                            cleaned += part
                        else:
                            cleaned += '<p>' + part + '</p>'
                    cell_content = cleaned
                xml += '<entry>' + cell_content + '</entry>\n'
            xml += '</row>\n'
        xml += '</tbody>\n</tgroup>\n</table>\n'
        xml += '{{DITA_TABLE_END}}\n'
        return xml

    text = re.sub(r'<table[^>]*>.*?</table>', _convert_table_to_dita, text, flags=re.DOTALL | re.IGNORECASE)

    # Convert <br> to newlines
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)

    # Convert block elements to newline-separated
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<div[^>]*>', '', text, flags=re.IGNORECASE)

    # Strip remaining HTML tags — but preserve content inside {{DITA_TABLE_START}}...{{DITA_TABLE_END}}
    # Split on table markers, only strip tags in non-table sections
    parts = re.split(r'(\{\{DITA_TABLE_START\}\}.*?\{\{DITA_TABLE_END\}\})', text, flags=re.DOTALL)
    processed_parts = []
    for part in parts:
        if part.startswith('{{DITA_TABLE_START}}'):
            processed_parts.append(part)  # preserve table XML as-is
        else:
            stripped = _strip_tags(part)
            # After entity decoding, a pasted XML/code block reappears as
            # literal <tag> lines — protect those as a code block now.
            stripped = _protect_literal_code_blocks(stripped)
            stripped = _preprocess_code_markers(stripped)
            stripped = _preprocess_markdown_bold(stripped)
            processed_parts.append(stripped)
    text = ''.join(processed_parts)

    # Normalize list markers at the start of a line into real ordered-list
    # markers ("1. text") so they are recognized as steps. This handles the
    # many ways Word/Docs paste renders list numbers/letters:
    #   "{{BOLD:1}}<tab>Create..."   bold number + separator
    #   "{{BOLD:1}}Create..."        bold number glued to the text
    #   "1<tab>Create..." / "1 Create..."  plain number + separator
    #   "a) Download..." handled elsewhere by _is_ordered_list_item
    def _norm_bold_marker(m):
        marker = m.group(1).strip()
        sep = m.group(2)
        rest = m.group(3)
        if not (re.fullmatch(r'\d+', marker) or re.fullmatch(r'[A-Za-z]', marker)):
            return m.group(0)
        # If glued (no separator), require the text to start with a capital
        # letter so we don't split a word like "{{BOLD:S}}ave".
        if not sep and not (rest[:1].isupper()):
            return m.group(0)
        return marker + '. ' + rest.lstrip()

    # Bold-number/letter marker, optional punctuation, optional separator, text
    text = re.sub(
        r'^[ \t]*\{\{BOLD:([^}]+)\}\}[\.\):]?([ \t]*)(\S.*)$',
        _norm_bold_marker, text, flags=re.MULTILINE)

    # Plain number/letter followed by a TAB (or 2+ spaces) then text — a list
    # marker even without a trailing period (common Word tabbed lists).
    text = re.sub(
        r'^[ \t]*(\d+|[A-Za-z])(?:\t+|[ ]{2,})(\S.*)$',
        lambda m: m.group(1) + '. ' + m.group(2), text, flags=re.MULTILINE)

    # Merge broken lines: fix contenteditable wrapping and split bullet+text
    # Skip lines inside DITA table blocks
    lines = text.split('\n')
    merged = []
    in_table_block = False
    for line in lines:
        stripped = line.strip()

        # Track table marker blocks — don't merge inside them
        if stripped == '{{DITA_TABLE_START}}':
            in_table_block = True
            merged.append(line)
            continue
        if stripped == '{{DITA_TABLE_END}}':
            in_table_block = False
            merged.append(line)
            continue
        if in_table_block:
            merged.append(line)
            continue

        if not stripped:
            merged.append('')
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

        # Check if this line is a continuation of the previous
        # Merge if: starts lowercase OR previous line doesn't end with sentence punctuation
        # (indicating the line was broken mid-sentence by word wrap)
        prev_is_list_item = bool(merged) and (
            _is_unordered_list_item(merged[-1].strip())
            or _is_ordered_list_item(merged[-1].strip()))
        if (merged and merged[-1] and stripped
                and not _is_unordered_list_item(stripped)
                and not stripped.startswith('{{BOLD:')
                and not stripped.startswith('{{CODEBLOCK:')
                and not merged[-1].strip().startswith('{{CODEBLOCK:')
                # Never merge a description line back into a bullet/numbered
                # list item — the split is intentional (field name vs. desc).
                and not prev_is_list_item
                and not re.match(r'^\d+[\.\)]', stripped)
                and not re.match(r'^(Note|Warning|Caution|Tip|Important)', stripped, re.IGNORECASE)):
            prev = merged[-1].rstrip()
            # Merge if starts lowercase
            if stripped[0].islower():
                merged[-1] = prev + ' ' + stripped
                continue
            # Merge if previous line ends mid-sentence (no period, colon, or closing paren)
            # and this line doesn't look like a new heading/title
            if (prev and not prev.endswith(('.', '!', '?', ':', ')'))
                    and not re.match(r'^\s*\{\{BOLD:', prev)
                    and not _is_heading_line(prev)):
                merged[-1] = prev + ' ' + stripped
                continue
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
            # Strip action verbs from the beginning (Click, Select, Press, etc.)
            action_verbs = ['Click', 'Select', 'Press', 'Tap', 'Choose', 'Open', 'Close']
            for verb in action_verbs:
                if name.startswith(verb + ' '):
                    prefix = verb + ' '
                    name = name[len(prefix):]
                    if name:
                        return prefix + "<uicontrol>" + name + "</uicontrol>" + suffix
                    return m.group(0)
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
    # Tag CamelCase UI-element identifiers (e.g. FTSFMachineRunning)
    result = _apply_ui_tokens(result)
    # Resolve inline code markers into <codeph> (content already XML-escaped above)
    result = re.sub(r'\{\{CODEPH:(.*?)\}\}', r'<codeph>\1</codeph>', result)
    return result


# Matches a CamelCase / mixed-case technical identifier used as a UI element
# name, e.g. FTSFMachineRunning, FTSFMachineInterruption, KepwareData.
# Requires at least one lower->upper or upper-run->upper transition so ordinary
# Title Case words ("Machine", "Server") are NOT matched.
_UI_TOKEN_RE = re.compile(
    r'(?<![>\w])'                      # not already inside a tag/word
    r'([A-Za-z]*[a-z][A-Z][A-Za-z]*'   # lower then Upper (camelCase / MixedCase)
    r'|[A-Z]{2,}[a-z][A-Za-z]*)'       # ACRONYM followed by Word (e.g. FTSFMachine)
    r'(?![\w>])'
)


def _apply_ui_tokens(text):
    """Wrap CamelCase UI-element identifiers in <uicontrol>.

    Skips content already inside a tag (e.g. <uicontrol>..</uicontrol>,
    <codeph>..</codeph>) and code markers so nothing is double-tagged or
    tags are injected into code.
    """
    # Split on existing tags and code markers; only tag the plain-text segments.
    segments = re.split(r'(<[^>]+>|\{\{CODEPH:.*?\}\}|\{\{CODEBLOCK:.*?\}\})', text)
    out = []
    inside_tag_depth = 0
    for seg in segments:
        if not seg:
            continue
        # Existing tag or code marker — pass through untouched
        if seg.startswith('<') or seg.startswith('{{'):
            out.append(seg)
            # Track whether we're between an opening and closing inline tag
            if re.match(r'<[a-zA-Z]', seg):
                inside_tag_depth += 1
            elif seg.startswith('</'):
                inside_tag_depth = max(0, inside_tag_depth - 1)
            continue
        if inside_tag_depth > 0:
            # Text already wrapped by another inline tag — leave it alone
            out.append(seg)
            continue

        def _tok(m):
            token = m.group(1)
            start, end = m.start(1), m.end(1)
            before = seg[start - 1] if start > 0 else ''
            after = seg[end] if end < len(seg) else ''
            # Skip tokens that are part of a file path or a filename:
            #  - preceded by a path separator (\ or /) or a dot
            #  - followed by a path separator or a file extension (.exe, .dll)
            if before in ('\\', '/', '.'):
                return token
            if after == '.' or after in ('\\', '/'):
                return token
            return '<uicontrol>' + token + '</uicontrol>'

        out.append(_UI_TOKEN_RE.sub(_tok, seg))
    return ''.join(out)


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
    Navigation verbs (Navigate to, Select, Go to) are kept outside the tag.

    Only used in task files.
    """
    # Match: optional nav verb + word(s) &gt; word(s) [&gt; word(s)]...
    pattern = re.compile(
        r'((?:Navigate\s+to|Select|Go\s+to|Access)\s+)?'  # optional nav verb prefix
        r'((?:[A-Za-z][\w]*(?:\s+[A-Za-z][\w]*)*)'  # first segment
        r'(?:\s*&gt;\s*(?:[A-Za-z][\w]*(?:\s+[A-Za-z][\w]*)*))+)'  # subsequent segments
    )

    def _menucascade_replacer(m):
        prefix = m.group(1) or ''
        full = m.group(2).strip()
        parts = re.split(r'\s*&gt;\s*', full)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 2:
            return m.group(0)
        inner = "".join(
            "<uicontrol>" + p + "</uicontrol>" for p in parts
        )
        return prefix + "<menucascade>" + inner + "</menucascade>"

    return pattern.sub(_menucascade_replacer, text)


# =============================================================================
# BLOCK-LEVEL PARSING HELPERS
# =============================================================================

def _split_note_from_text(text, is_task=False):
    """Split any inline 'Note:' (or Warning/Caution/etc.) out of a text block.

    Returns (main_text, note_xml_or_empty). Everything from the note keyword
    onward becomes a <note> element; the text before it is returned separately.
    This enforces the rule: a <note> is emitted whenever 'Note:' appears.
    """
    m = re.search(
        r'\b(Note|Warning|Caution|Danger|Tip|Important)\s*:\s*',
        text)
    if not m:
        return text, ""
    main = text[:m.start()].strip()
    note_body = text[m.end():].strip()
    kw = m.group(1).lower()
    type_map = {
        'warning': ' type="warning"', 'caution': ' type="caution"',
        'danger': ' type="danger"', 'tip': ' type="tip"',
        'important': ' type="important"',
    }
    attr = type_map.get(kw, '')
    note_xml = ""
    if note_body:
        note_xml = "<note" + attr + ">" + _apply_inline_tags(note_body, is_task=is_task) + "</note>\n"
    return main, note_xml


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


# Ordered-list markers:
#   "1. ", "1) ", "1 <tab>"  — numbered
#   "a. ", "a) ", "a <tab>"  — lettered sub-steps (single letter)
_ORDERED_NUM_RE = re.compile(r'^\d+[\.\)]\s+|^\d+\t+\s*')
_ORDERED_ALPHA_RE = re.compile(r'^[a-zA-Z][\.\)]\s+|^[a-zA-Z]\t+\s*')


def _is_ordered_list_item(line):
    """Check if a line is a numbered or lettered list item.

    Recognizes '1.', '1)', '1<tab>' and single-letter markers 'a.', 'a)',
    'a<tab>' (common for sub-steps pasted from Word).
    """
    return bool(_ORDERED_NUM_RE.match(line)) or bool(_ORDERED_ALPHA_RE.match(line))


def _strip_ordered_prefix(line):
    """Remove the number/letter marker prefix from an ordered list item."""
    result = _ORDERED_NUM_RE.sub('', line, count=1)
    if result == line:
        result = _ORDERED_ALPHA_RE.sub('', line, count=1)
    return result


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


def _heading_marker_text(line):
    """If the line is a {{HEADING:...}} marker, return its text; else None."""
    m = re.match(r'^\s*\{\{HEADING:(.*?)\}\}\s*$', line, re.DOTALL)
    return m.group(1).strip() if m else None


def _is_heading_line(line):
    """Check if a line appears to be a heading/section title.

    Detects:
    - ALL CAPS lines (from HTML heading preprocessing)
    - Title Case short lines that look like section headings
      (short, no ending punctuation, mostly capitalized words)
    """
    stripped = line.strip()
    if not stripped:
        return False
    # Explicit heading marker from HTML <h1>-<h6> preprocessing
    if _heading_marker_text(stripped) is not None:
        return True
    # ALL CAPS (from HTML preprocessing of <h1>-<h6>)
    if (stripped == stripped.upper()
            and len(stripped) > 2
            and stripped != stripped.lower()
            and len(stripped.split()) <= 10
            and not stripped.endswith(('.', ',', ';', ':'))):
        return True
    # Title Case: short line, starts with uppercase, no ending sentence punctuation,
    # most words capitalized, and no more than ~8 words (looks like a heading)
    words = stripped.split()
    if (len(words) <= 8
            and len(stripped) < 80
            and stripped[0].isupper()
            and not stripped.endswith(('.', ',', ';', ':', '!', '?'))
            and not _is_unordered_list_item(stripped)
            and not re.match(r'^\d+[\.\)]', stripped)
            and not stripped.startswith('{{BOLD:')
            and not re.match(r'^(Note|Warning|Caution|Tip|Important|The|This|A|An|If|When|You|It|In|For|Use)\b', stripped)):
        # Count capitalized words (skip short prepositions)
        cap_words = sum(1 for w in words if w[0].isupper() or len(w) <= 3)
        if cap_words >= len(words) * 0.6:
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
    """Parse a table block starting from start_idx. Returns (xml_string, end_idx).

    Generates proper DITA CALS table with:
    - <colspec> elements with colname and colwidth
    - <thead> from first row (header)
    - <tbody> with data rows
    - Inline DITA tags applied to cell content
    """
    table_lines = []
    idx = start_idx
    while idx < len(lines) and _is_table_line(lines[idx]):
        table_lines.append(lines[idx])
        idx += 1

    if not table_lines:
        return "", start_idx

    # Parse header and rows
    header_cells = [c.strip() for c in table_lines[0].split('|') if c.strip()]
    num_cols = len(header_cells)

    xml = "<table>\n"
    xml += '<tgroup cols="' + str(num_cols) + '">\n'

    # Add colspec for each column
    for i in range(1, num_cols + 1):
        xml += '<colspec colname="col' + str(i) + '" colwidth="1*"/>\n'

    # First row is header
    xml += "<thead>\n<row>\n"
    for i, cell in enumerate(header_cells):
        xml += '<entry nameend="col' + str(i+1) + '" namest="col' + str(i+1) + '">' + xml_escape(cell) + "</entry>\n"
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
            # Apply inline DITA tags to cell content, wrap in <p>
            escaped_cell = _apply_inline_tags(cell, is_task=False)
            xml += "<entry><p>" + escaped_cell + "</p></entry>\n"
        xml += "</row>\n"
    xml += "</tbody>\n</tgroup>\n</table>\n"

    return xml, idx


def _wrap_entry_lines_in_p(table_xml):
    """Post-process table XML to wrap raw text lines inside <entry> with <p> tags.

    Finds all <entry>...</entry> blocks and ensures every text line is wrapped in <p>,
    while preserving existing structured content (<ul>, <ol>, <note>, <uicontrol>).
    """
    def _fix_entry(m):
        content = m.group(1)
        # If content is already properly structured (all in <p>/<ul>/<note>), skip
        stripped = content.strip()
        if not stripped:
            return '<entry></entry>'
        # If already wrapped in <p> and no raw newlines outside, keep as-is
        if stripped.startswith('<p>') and '\n' not in stripped.replace('</p>\n<p>', ''):
            return '<entry>' + stripped + '</entry>'

        # Split into lines and wrap each non-structured line in <p>
        lines = content.split('\n')
        result_parts = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Already structured — keep as-is
            if (line.startswith('<p>') or line.startswith('<ul>') or line.startswith('<ol>')
                    or line.startswith('<note') or line.startswith('</ul>') or line.startswith('</ol>')):
                result_parts.append(line)
            # Partial tag content (like closing tags or mid-list) — keep
            elif line.startswith('</') or line.startswith('<li>') or line.startswith('<entry') or line.startswith('<row'):
                result_parts.append(line)
            # Raw text — wrap in <p>
            else:
                result_parts.append('<p>' + line + '</p>')
        return '<entry>' + ''.join(result_parts) + '</entry>'

    # Only process <entry> blocks that are in <tbody> (not <thead>)
    # Find tbody section and process entries within it
    tbody_match = re.search(r'(<tbody>)(.*?)(</tbody>)', table_xml, re.DOTALL)
    if tbody_match:
        tbody_content = tbody_match.group(2)
        fixed_tbody = re.sub(r'<entry>(.*?)</entry>', _fix_entry, tbody_content, flags=re.DOTALL)
        table_xml = table_xml[:tbody_match.start(2)] + fixed_tbody + table_xml[tbody_match.end(2):]

    return table_xml


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
    # Safety: truncate extremely large inputs to prevent regex catastrophic backtracking
    if len(text) > 500000:
        text = text[:500000]

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

        # Check for standalone code block marker
        if _is_codeblock_marker(line):
            xml_parts.append(_render_codeblock_marker(line))
            idx += 1
            continue

        # Check for DITA table (pre-converted from HTML table in preprocessor)
        if line.strip() == '{{DITA_TABLE_START}}':
            # Collect all lines until {{DITA_TABLE_END}} and output as-is
            idx += 1
            table_xml = ''
            while idx < len(lines) and lines[idx].strip() != '{{DITA_TABLE_END}}':
                table_xml += lines[idx] + '\n'
                idx += 1
            if idx < len(lines):
                idx += 1  # skip the END marker
            # Post-process: wrap raw lines inside <entry> with <p> tags
            table_xml = _wrap_entry_lines_in_p(table_xml)
            xml_parts.append(table_xml)
            continue

        # Check for table block (pipe-delimited plain text tables)
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

        # Check for bulleted definition list (bullet label + description pairs).
        # Must be tested BEFORE the plain unordered-list check so field lists
        # written as bullets become <dl>/<dlentry>/<dt>/<dd> instead of <ul>.
        if _is_bulleted_dl_candidate(lines, idx):
            dl_xml, idx = _parse_bulleted_definition_list(lines, idx, is_task=False)
            xml_parts.append(dl_xml)
            continue

        # Check for unordered list
        if _is_unordered_list_item(line):
            list_xml, idx = _parse_unordered_list(lines, idx, is_task=False)
            xml_parts.append(list_xml)
            continue

        # Check for section title (bold standalone line from pasted content)
        # Explicit heading marker (from HTML <h1>-<h6>) — preserves casing.
        heading_text = _heading_marker_text(line)
        if heading_text is not None:
            if in_section:
                xml_parts.append("</section>\n")
            xml_parts.append('<section>\n<title>' + xml_escape(heading_text) + '</title>\n')
            in_section = True
            idx += 1
            continue

        # Every bold standalone line becomes a section title
        bold_title_match = re.match(r'^\s*\{\{BOLD:(.*?)\}\}\s*$', line)
        if bold_title_match:
            title_text = bold_title_match.group(1)
            if in_section:
                xml_parts.append("</section>\n")
            xml_parts.append('<section>\n<title>' + xml_escape(title_text) + '</title>\n')
            in_section = True
            idx += 1
            continue

        # Check for definition list (field name + description pairs).
        # This must be tested BEFORE the Title Case heading check, because a
        # short field-name label followed immediately by a description line
        # otherwise gets misclassified as a section heading.
        if _is_dl_candidate(lines, idx):
            dl_xml, idx = _parse_definition_list(lines, idx, is_task=False)
            xml_parts.append(dl_xml)
            continue

        # Check for section title (from ALL CAPS heading preprocessing)
        if _is_heading_line(line):
            if in_section:
                xml_parts.append("</section>\n")
            xml_parts.append('<section>\n<title>' + xml_escape(line.strip()) + '</title>\n')
            in_section = True
            idx += 1
            continue

        # Default: paragraph. If it contains an inline "Note:", split the note
        # out into its own <note> block (rule: always tag Note:).
        main_text, note_xml = _split_note_from_text(line.strip())
        if main_text:
            xml_parts.append("<p>" + _apply_inline_tags(main_text, is_task=False) + "</p>\n")
        if note_xml:
            xml_parts.append(note_xml)
        idx += 1

    if in_section:
        xml_parts.append("</section>\n")

    result = "<conbody>\n" + "".join(xml_parts) + "</conbody>"
    # Clean up any unresolved heading markers (emit their text as a paragraph)
    result = re.sub(r'\{\{HEADING:(.*?)\}\}', r'\1', result)
    # Clean up any unresolved bold markers that leaked through
    result = re.sub(r'\{\{BOLD:(.*?)\}\}', r'<uicontrol>\1</uicontrol>', result)
    # Safety: escape any remaining bare & that aren't valid XML entity references
    result = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', result)
    # Safety: escape any remaining unmatched < that aren't valid XML tags
    result = re.sub(r'<(?!/?\w)', '&lt;', result)
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


def _is_codeblock_marker(line):
    """Check if a line is a standalone {{CODEBLOCK:...}} marker."""
    return line.strip().startswith('{{CODEBLOCK:') and line.strip().endswith('}}')


def _render_codeblock_marker(line):
    """Render a {{CODEBLOCK:...}} marker into a <codeblock> element.

    The stored body has newlines encoded as {{NL}}; they are restored and the
    content is XML-escaped so code containing <, >, & stays valid.
    """
    m = re.match(r'^\s*\{\{CODEBLOCK:(.*)\}\}\s*$', line, re.DOTALL)
    body = m.group(1) if m else ''
    body = body.replace('{{NL}}', '\n')
    # Collapse runs of blank lines (from block-element paste) to a single break
    body = re.sub(r'\n[ \t]*\n+', '\n', body).strip('\n')
    return '<codeblock>' + xml_escape(body) + '</codeblock>\n'


def _next_nonblank_idx(lines, idx):
    """Return the index of the next non-blank line at or after idx, or len(lines)."""
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    return idx


def _is_single_dl_pair(lines, idx):
    """Check whether a single term/description pair starts at idx.

    A term is a short label (no trailing sentence punctuation) that is
    followed (after any blank lines) by a longer description line. Blank
    lines between the term and description are tolerated because Word/HTML
    paste commonly inserts them.
    Returns (is_pair, description_idx).
    """
    if idx >= len(lines):
        return False, idx
    term = lines[idx].strip()
    if not term or len(term) >= 60 or term.endswith(('.', ',', ';', ':', '!', '?')):
        return False, idx
    if (_is_ordered_list_item(term) or _is_unordered_list_item(term)
            or _is_note_line(term) or term.startswith('{{')):
        return False, idx
    desc_idx = _next_nonblank_idx(lines, idx + 1)
    if desc_idx >= len(lines):
        return False, idx
    next_line = lines[desc_idx].strip()
    if not next_line:
        return False, idx
    # A multi-word Title Case heading followed by a full sentence (ending in a
    # period) is a section title + intro paragraph, not a field/description
    # pair. Field labels are typically one or two words.
    if (len(term.split()) >= 3 and _is_heading_line(term)
            and next_line.endswith('.')):
        return False, idx
    # Description must look like prose: starts lowercase, or is a longer sentence.
    if next_line[0].islower() or len(next_line) > 60:
        return True, desc_idx
    return False, idx


def _is_dl_candidate(lines, idx):
    """Check if current position starts a definition list (field list).

    Pattern: a short line (field name) followed by a longer description
    line, repeating. To avoid misclassifying a heading + paragraph as a
    definition list, at least TWO consecutive term/description pairs must
    be present before the block is treated as a <dl>.
    """
    is_pair, desc_idx = _is_single_dl_pair(lines, idx)
    if not is_pair:
        return False
    # Advance past this pair's description (and its continuation lines)
    scan = desc_idx + 1
    while scan < len(lines) and lines[scan].strip():
        # Stop the description if the next line itself starts a new pair
        if _is_single_dl_pair(lines, scan)[0]:
            break
        scan += 1
    scan = _next_nonblank_idx(lines, scan)
    # Require a second pair to confirm this is a field list, not a heading.
    return _is_single_dl_pair(lines, scan)[0]


def _is_bulleted_dl_pair(lines, idx):
    """Check whether a bulleted term + description pair starts at idx.

    Pattern (common in Word/Google Docs field lists):
        * Field Name
        The description of that field.

    The term is a bullet item with a short label; the description is the
    next non-blank line that is NOT itself a bullet. Returns
    (is_pair, term_text, description_idx).
    """
    if idx >= len(lines) or not _is_unordered_list_item(lines[idx].strip()):
        return False, "", idx
    term = _strip_unordered_prefix(lines[idx].strip()).strip()
    # Term should be a short label (field name), not a full sentence
    if not term or len(term) >= 60 or term.endswith(('.', '!', '?')):
        return False, "", idx
    desc_idx = _next_nonblank_idx(lines, idx + 1)
    if desc_idx >= len(lines):
        return False, "", idx
    desc = lines[desc_idx].strip()
    # Description must be a non-bullet line with real prose content
    if not desc or _is_unordered_list_item(desc) or _is_ordered_list_item(desc):
        return False, "", idx
    return True, term, desc_idx


def _is_bulleted_dl_candidate(lines, idx):
    """Detect a bulleted definition-list block.

    A bullet immediately followed by a non-bullet description line is a field
    definition (unlike a normal bullet list, whose items are consecutive
    bullets with no prose paragraph between them). A single such pair is
    enough to treat the block as a <dl>.
    """
    return _is_bulleted_dl_pair(lines, idx)[0]


def _parse_bulleted_definition_list(lines, idx, is_task=False):
    """Parse a bulleted field list into <dl>/<dlentry>/<dt>/<dd> XML.

    Each bullet label becomes a <dt>; the following non-bullet lines
    (until the next bullet) become the <dd>.
    """
    xml = "<dl>\n"
    while idx < len(lines):
        idx = _next_nonblank_idx(lines, idx)
        if idx >= len(lines):
            break
        is_pair, term, desc_idx = _is_bulleted_dl_pair(lines, idx)
        if not is_pair:
            break

        xml += "<dlentry>\n"
        xml += "<dt>" + _apply_inline_tags(term, is_task=is_task) + "</dt>\n"

        idx = desc_idx
        desc_parts = []
        while idx < len(lines) and lines[idx].strip():
            # Stop when the next bullet term begins
            if _is_unordered_list_item(lines[idx].strip()):
                break
            desc_line = lines[idx].strip()
            if _is_note_line(desc_line):
                note_text = _strip_note_prefix(desc_line)
                desc_parts.append("<note>" + xml_escape(note_text) + "</note>")
                idx += 1
                continue
            desc_parts.append(_apply_inline_tags(desc_line, is_task=is_task))
            idx += 1

        xml += "<dd>" + " ".join(desc_parts) + "</dd>\n"
        xml += "</dlentry>\n"

    xml += "</dl>\n"
    return xml, idx


def _parse_definition_list(lines, idx, is_task=False):
    """Parse a definition list (field name + description pairs) into <dl> XML.

    Tolerates blank lines between the term and its description, and between
    consecutive entries (common with Word/HTML paste).
    """
    xml = "<dl>\n"
    while idx < len(lines):
        # Skip blank lines before a term
        idx = _next_nonblank_idx(lines, idx)
        if idx >= len(lines):
            break

        is_pair, desc_idx = _is_single_dl_pair(lines, idx)
        if not is_pair:
            break

        term_line = lines[idx].strip()
        # Term
        xml += "<dlentry>\n"
        xml += "<dt>" + _apply_inline_tags(term_line, is_task=is_task) + "</dt>\n"

        # Move to the description
        idx = desc_idx

        # Description (collect continuation lines until the next term/pair)
        desc_parts = []
        while idx < len(lines) and lines[idx].strip():
            # Stop if the current line begins a new term/description pair
            if desc_parts and _is_single_dl_pair(lines, idx)[0]:
                break
            desc_line = lines[idx].strip()
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
      (detects bulleted "* Field / description" and numbered
      "N Field: description" formats, each grouped into one step's <info>)
    - Uses <info> for additional content within a step
    - Applies <uicontrol>, <wintitle>, <userinput> inline tags
    - Handles notes (no <p> inside), lists inside <info>
    - Never nests <step> inside <step>
    - Does not modify the input language or structure
    """
    # Safety: truncate extremely large inputs to prevent regex catastrophic backtracking
    if len(text) > 500000:
        text = text[:500000]
    # Preprocess HTML input if detected
    text = _preprocess_html_input(text)

    lines = text.split('\n')
    xml_parts = []
    idx = 0
    has_steps = False
    in_steps = False

    # Look for the first content that starts the step body. This can be a
    # numbered step, a bulleted/numbered field list, or a lead-in line ending
    # with ':'. A numbered *field* line (e.g. "1 Machine Server: desc") is NOT
    # a procedural step, so it is treated as field-list content, not a step.
    first_step_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if i == 0 and _is_heading_line(stripped):
            continue  # title line
        if (_is_bulleted_fieldlist_candidate(lines, i)
                or _is_numbered_fieldlist_candidate(lines, i)):
            first_step_idx = i
            break
        # A ':' lead-in only starts the body if it introduces bullet/code/field
        # content; otherwise it is context (goes into shortdesc).
        if stripped.endswith(':') and i > 0:
            nb = _next_nonblank_idx(lines, i + 1)
            if nb < len(lines) and (
                    _is_bulleted_fieldlist_candidate(lines, nb)
                    or _is_codeblock_marker(lines[nb])):
                first_step_idx = i
                break
        if _is_ordered_list_item(stripped) and not _is_numbered_field_line(stripped):
            first_step_idx = i
            break

    # Extract shortdesc (opening content before steps)
    if first_step_idx is not None and first_step_idx > 0:
        shortdesc_lines = []
        for i in range(first_step_idx):
            stripped = lines[i].strip()
            if not stripped:
                continue
            # Skip the title line (first non-empty line that looks like a heading/gerund title)
            if i == 0 and _is_heading_line(stripped):
                continue
            # Skip gerund-style title lines (e.g., "Configuring warehouse zones")
            if i == 0 and re.match(r'^[A-Z][a-z]+ing\s+', stripped) and not stripped.endswith('.'):
                continue
            shortdesc_lines.append(stripped)
        if shortdesc_lines:
            shortdesc_text = " ".join(shortdesc_lines)
            xml_parts.append("<shortdesc>" + _apply_inline_tags(shortdesc_text, is_task=True) + "</shortdesc>\n")
        idx = first_step_idx
    elif first_step_idx is None:
        # No numbered steps found. Collect leading prose (title + intro
        # sentences) as the shortdesc, stopping at the first field list, a
        # lead-in line ending with ':', or a note.
        shortdesc_lines = []
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped:
                i += 1
                continue
            # Stop at the start of field-list content or a lead-in line
            if (_is_bulleted_fieldlist_candidate(lines, i)
                    or _is_numbered_fieldlist_candidate(lines, i)
                    or _is_note_line(stripped)
                    or stripped.endswith(':')):
                break
            # Skip the gerund-style title line (e.g., "Linking machine ...")
            if not (len(shortdesc_lines) == 0 and _is_heading_line(stripped)):
                shortdesc_lines.append(stripped)
            i += 1
        if shortdesc_lines:
            shortdesc_text = " ".join(shortdesc_lines)
            xml_parts.append("<shortdesc>" + _apply_inline_tags(shortdesc_text, is_task=True) + "</shortdesc>\n")
        idx = i

    # Parse steps and content
    xml_parts.append("<steps>\n")
    in_steps = True

    while idx < len(lines):
        line = lines[idx].rstrip()

        # Skip empty lines
        if not line.strip():
            idx += 1
            continue

        # DITA table block (pre-converted from an HTML table) — wrap in a step's <info>.
        if line.strip() == '{{DITA_TABLE_START}}':
            idx += 1
            table_xml = ''
            while idx < len(lines) and lines[idx].strip() != '{{DITA_TABLE_END}}':
                table_xml += lines[idx] + '\n'
                idx += 1
            if idx < len(lines):
                idx += 1  # skip END marker
            table_xml = _wrap_entry_lines_in_p(table_xml)
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>Refer to the following table:</cmd>\n")
            xml_parts.append("<info>\n" + table_xml + "</info>\n")
            xml_parts.append("</step>\n")
            has_steps = True
            continue

        # Standalone code block — emit as a step containing <info><codeblock>
        if _is_codeblock_marker(line):
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>Code sample:</cmd>\n")
            xml_parts.append("<info>" + _render_codeblock_marker(line) + "</info>\n")
            xml_parts.append("</step>\n")
            idx += 1
            continue

        # Numbered inline field list (e.g. "1\tMachine Server: description").
        # These are field definitions, not procedural steps, so wrap the whole
        # block in a single step's <info><fieldlist>.
        if _is_numbered_fieldlist_candidate(lines, idx):
            fl_xml, idx = _parse_numbered_fieldlist(lines, idx)
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>Specify this information:</cmd>\n")
            xml_parts.append("<info>\n" + fl_xml + "</info>\n")
            xml_parts.append("</step>\n")
            has_steps = True
            continue

        # A lead-in line ending with ':' followed by a code block. Emit as a
        # step whose <cmd> is the lead-in and <info> holds the <codeblock>.
        stripped_line = line.strip()
        _cb_nb = _next_nonblank_idx(lines, idx + 1)
        if (stripped_line.endswith(':')
                and _cb_nb < len(lines) and _is_codeblock_marker(lines[_cb_nb])):
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>" + _apply_inline_tags(stripped_line, is_task=True) + "</cmd>\n")
            xml_parts.append("<info>\n" + _render_codeblock_marker(lines[_cb_nb]) + "</info>\n")
            xml_parts.append("</step>\n")
            idx = _cb_nb + 1
            has_steps = True
            continue

        # A lead-in line ending with ':' followed by a bulleted field list.
        # Emit the lead-in as the step command and the field list as its <info>.
        if (stripped_line.endswith(':')
                and _is_bulleted_fieldlist_candidate(lines, _next_nonblank_idx(lines, idx + 1))):
            fl_start = _next_nonblank_idx(lines, idx + 1)
            fl_xml, idx = _parse_bulleted_fieldlist(lines, fl_start)
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>" + _apply_inline_tags(stripped_line, is_task=True) + "</cmd>\n")
            xml_parts.append("<info>\n" + fl_xml + "</info>\n")
            xml_parts.append("</step>\n")
            has_steps = True
            continue

        # Bulleted field list with no explicit lead-in — still emit as a step.
        if _is_bulleted_fieldlist_candidate(lines, idx):
            fl_xml, idx = _parse_bulleted_fieldlist(lines, idx)
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>Specify this information:</cmd>\n")
            xml_parts.append("<info>\n" + fl_xml + "</info>\n")
            xml_parts.append("</step>\n")
            has_steps = True
            continue

        # Numbered step
        if _is_ordered_list_item(line.strip()):
            cmd_text = _strip_ordered_prefix(line.strip()).strip()
            # Split any inline "Note:" out of the command into a step <note>.
            cmd_main, cmd_note = _split_note_from_text(cmd_text, is_task=True)
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>" + _apply_inline_tags(cmd_main or cmd_text, is_task=True) + "</cmd>\n")
            idx += 1

            # Check for sub-content within this step (info, fieldlist, notes, lists)
            step_info = _parse_step_info(lines, idx)
            info_body = step_info["xml"]
            if cmd_note:
                if info_body.startswith("<info>\n"):
                    # Insert the note right after the opening <info>
                    info_body = "<info>\n" + cmd_note + info_body[len("<info>\n"):]
                else:
                    info_body = "<info>\n" + cmd_note + "</info>\n" + info_body
            if info_body:
                xml_parts.append(info_body)
            idx = step_info["end_idx"]

            xml_parts.append("</step>\n")
            has_steps = True
            continue

        # Non-step content after steps started — wrap in a step with info
        if in_steps:
            cmd_main, cmd_note = _split_note_from_text(line.strip(), is_task=True)
            xml_parts.append("<step>\n")
            xml_parts.append("<cmd>" + _apply_inline_tags(cmd_main or line.strip(), is_task=True) + "</cmd>\n")
            if cmd_note:
                xml_parts.append("<info>\n" + cmd_note + "</info>\n")
            idx += 1
            xml_parts.append("</step>\n")
            continue

        idx += 1

    if in_steps:
        xml_parts.append("</steps>\n")

    result = "<taskbody>\n" + "".join(xml_parts) + "</taskbody>"
    # Clean up any unresolved heading/bold markers that leaked through
    result = re.sub(r'\{\{HEADING:(.*?)\}\}', r'\1', result)
    # Safety: escape any remaining bare & that aren't valid XML entity references
    result = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', result)
    # Safety: escape any remaining unmatched < that aren't valid XML tags
    result = re.sub(r'<(?!/?\w)', '&lt;', result)
    return result


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

        # DITA table block inside a step
        if line.strip() == '{{DITA_TABLE_START}}':
            idx += 1
            table_xml = ''
            while idx < len(lines) and lines[idx].strip() != '{{DITA_TABLE_END}}':
                table_xml += lines[idx] + '\n'
                idx += 1
            if idx < len(lines):
                idx += 1
            info_parts.append(_wrap_entry_lines_in_p(table_xml))
            continue

        # Code block inside step
        if _is_codeblock_marker(line):
            info_parts.append(_render_codeblock_marker(line))
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

        # Lead-in line followed by a code block (e.g. "... in this format:"
        # then a pasted XML sample). Emit the lead-in as a paragraph and the
        # code as a <codeblock>, never as a field list.
        nb = _next_nonblank_idx(lines, idx + 1)
        if nb < len(lines) and _is_codeblock_marker(lines[nb]):
            info_parts.append("<p>" + _apply_inline_tags(line.strip(), is_task=True) + "</p>\n")
            info_parts.append(_render_codeblock_marker(lines[nb]))
            idx = nb + 1
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


# Matches a numbered field line where the number and label are on the same
# line as the description, e.g. "1\tMachine Server: The internal FT name..."
# or "1. Polling Interval: The default interval..."
_NUMBERED_FIELD_RE = re.compile(r'^\s*\d+[\.\)]?[\t ]+(.+?):\s+(.+)$')


def _is_numbered_field_line(line):
    """Check if a line is a 'N<sep>FieldName: description' field entry."""
    m = _NUMBERED_FIELD_RE.match(line)
    if not m:
        return False
    name = m.group(1).strip()
    if not name or len(name) >= 60:
        return False
    # A field label is a short noun phrase — it must NOT contain sentence
    # punctuation or a note keyword (those indicate prose, not a field name).
    if re.search(r'[.!?]', name):
        return False
    if re.search(r'\b(Note|Warning|Caution|Danger|Tip|Important)\b', name):
        return False
    return True


def _is_numbered_fieldlist_candidate(lines, idx):
    """Detect a block of 'N FieldName: description' numbered field entries."""
    return _is_numbered_field_line(lines[idx].strip()) if idx < len(lines) else False


def _parse_numbered_fieldlist(lines, idx):
    """Parse 'N FieldName: description' lines into <fieldlist> XML.

    Each numbered line yields one <field> with the label as <fieldname> and
    the text after the colon as <fielddesc>. Continuation lines (until the
    next numbered field) are appended to the current description.
    """
    xml = "<fieldlist>\n"
    while idx < len(lines):
        idx = _next_nonblank_idx(lines, idx)
        if idx >= len(lines):
            break
        m = _NUMBERED_FIELD_RE.match(lines[idx].strip())
        if not m:
            break
        name = m.group(1).strip()
        desc = m.group(2).strip()
        idx += 1

        # Collect continuation lines that belong to this description
        while idx < len(lines) and lines[idx].strip():
            nxt = lines[idx].strip()
            if _is_numbered_field_line(nxt) or _is_ordered_list_item(nxt) or _is_unordered_list_item(nxt):
                break
            desc += " " + nxt
            idx += 1

        xml += "<field>\n"
        xml += "<fieldname><uicontrol>" + xml_escape(name) + "</uicontrol></fieldname>\n"
        # Split off a trailing "Note:" into a <note> element
        note_split = re.split(r'\bNote:\s*', desc, maxsplit=1)
        if len(note_split) == 2:
            main_desc = note_split[0].strip()
            note_text = note_split[1].strip()
            fd = "<fielddesc>" + _apply_inline_tags(main_desc, is_task=True)
            if note_text:
                fd += "<note>" + xml_escape(note_text) + "</note>"
            fd += "</fielddesc>\n"
            xml += fd
        else:
            xml += "<fielddesc>" + _apply_inline_tags(desc, is_task=True) + "</fielddesc>\n"
        xml += "</field>\n"

    xml += "</fieldlist>\n"
    return xml, idx


def _is_bulleted_fieldlist_candidate(lines, idx):
    """Detect a bulleted field list (bullet label + description) in task context."""
    return _is_bulleted_dl_pair(lines, idx)[0]


def _parse_bulleted_fieldlist(lines, idx):
    """Parse a bulleted field list into <fieldlist> XML for task files.

    Each bullet label becomes a <fieldname>; the following non-bullet lines
    (until the next bullet) become the <fielddesc>. Deeper sub-bullets (e.g.
    a set of possible values) are rendered as a <ul> inside the <fielddesc>.
    Inline "Note:" text becomes a <note>.
    """
    xml = "<fieldlist>\n"
    while idx < len(lines):
        idx = _next_nonblank_idx(lines, idx)
        if idx >= len(lines):
            break
        is_pair, term, desc_idx = _is_bulleted_dl_pair(lines, idx)
        if not is_pair:
            break

        xml += "<field>\n"
        xml += "<fieldname><uicontrol>" + xml_escape(term) + "</uicontrol></fieldname>\n"

        idx = desc_idx
        desc_parts = []
        while idx < len(lines) and lines[idx].strip():
            raw = lines[idx]
            cur = raw.strip()
            # Stop at a code block marker (handled as its own block)
            if _is_codeblock_marker(cur):
                break
            # A bullet that begins a new field pair (bullet + description)
            # ends this description. But a run of "value bullets" (bullets
            # with no following description, e.g. Running/Down/Idle) belongs
            # to THIS field and is absorbed as a <ul>.
            if _is_unordered_list_item(cur):
                if _is_bulleted_dl_pair(lines, idx)[0]:
                    break  # next field
                values = []
                while idx < len(lines) and _is_unordered_list_item(lines[idx].strip()):
                    if _is_bulleted_dl_pair(lines, idx)[0]:
                        break
                    values.append(_strip_unordered_prefix(lines[idx].strip()).strip())
                    idx += 1
                if values:
                    desc_parts.append(
                        "<ul>\n" + "".join(
                            "<li>" + _apply_inline_tags(v, is_task=True) + "</li>\n"
                            for v in values
                        ) + "</ul>\n"
                    )
                continue
            # Stop when a numbered inline field list begins (new step)
            if _is_numbered_field_line(cur):
                break
            # A sub-list of values (indented items) becomes a <ul>
            if _is_ordered_list_item(cur):
                list_xml, idx = _parse_ordered_list(lines, idx, is_task=True)
                desc_parts.append(list_xml)
                continue
            # Indented short value lines (e.g. tab-indented Running/Down/Idle)
            # form a <ul> of possible values.
            if raw[:1] in ('\t', ' ') and len(cur) < 40 and not cur.endswith(('.', ':')):
                values = []
                while idx < len(lines) and lines[idx].strip():
                    vraw = lines[idx]
                    vcur = vraw.strip()
                    if vraw[:1] in ('\t', ' ') and len(vcur) < 40 and not vcur.endswith(('.', ':')) \
                            and not _is_unordered_list_item(vcur):
                        values.append(vcur)
                        idx += 1
                    else:
                        break
                if values:
                    ul = "<ul>\n" + "".join(
                        "<li>" + _apply_inline_tags(v, is_task=True) + "</li>\n" for v in values
                    ) + "</ul>\n"
                    desc_parts.append(ul)
                continue
            # Inline note within the description
            if _is_note_line(cur):
                note_text = _strip_note_prefix(cur)
                desc_parts.append("<note>" + xml_escape(note_text) + "</note>")
                idx += 1
                continue
            # Split a trailing "Note:" out of the same line
            note_split = re.split(r'\bNote:\s*', cur, maxsplit=1)
            if len(note_split) == 2 and note_split[0].strip():
                desc_parts.append(_apply_inline_tags(note_split[0].strip(), is_task=True))
                if note_split[1].strip():
                    desc_parts.append("<note>" + xml_escape(note_split[1].strip()) + "</note>")
                idx += 1
                continue
            desc_parts.append(_apply_inline_tags(cur, is_task=True))
            idx += 1

        xml += "<fielddesc>" + " ".join(desc_parts) + "</fielddesc>\n"
        xml += "</field>\n"

    xml += "</fieldlist>\n"
    return xml, idx


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
            # Stop at a code block marker (handled as its own block)
            if _is_codeblock_marker(desc_line):
                break
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
