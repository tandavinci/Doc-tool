"""
Neoscribe Engine — AI Documentation Drafting Agent.

Generates valid, standards-compliant DITA XML drafts from JIRA ticket
content, following the Infor Documentation Development Lifecycle (DDLC).

Supports two modes:
- Mode 1: New Topic Draft — generates a fresh DITA topic from ticket input
- Mode 2: Existing Topic Update — revises an existing DITA topic with new info

All output is labeled as AI-generated draft requiring writer review.

Uses local Ollama (OpenAI-compatible API) for intelligent content generation,
then post-processes the output to ensure DITA compliance.
"""

import logging
import os
import re
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
OLLAMA_API_KEY = "ollama"

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

NEOSCRIBE_CONCEPT_PROMPT = """You are Neoscribe, an AI documentation drafting agent for Infor Information Development. Generate a valid DITA XML concept topic.

RULES:
- Output ONLY valid DITA XML. No markdown, no explanations outside the XML.
- Use second person ("you") throughout.
- Use active voice wherever possible.
- Professional, objective, concise tone.
- Never fabricate information not in the input.
- Insert [TODO: ...] placeholders for missing information.
- Label output with: <!-- AI-GENERATED DRAFT - Requires writer review and approval -->

STRUCTURE:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">
<!-- AI-GENERATED DRAFT - Requires writer review and approval -->
<concept id="concept_{id}">
  <title>{title}</title>
  <shortdesc>{20-60 word description}</shortdesc>
  <conbody>
    <section>
      <title>{section title}</title>
      <p>{content}</p>
    </section>
  </conbody>
</concept>
```

ELEMENT RULES:
- <uicontrol> for UI element names (fields, buttons, tabs, menus, options)
- <wintitle> for screen/window/session names
- <menucascade><uicontrol>A</uicontrol><uicontrol>B</uicontrol></menucascade> for navigation paths
- <note> for important notes (no <p> inside <note>)
- Use <ul>/<ol> for lists, <table> for tabular data
- Use <section> with <title> for logical groupings
- Do NOT use <b>, <i>, or <para> elements

From the JIRA ticket content provided, create a concept topic that explains the feature/change clearly for end users."""

NEOSCRIBE_TASK_PROMPT = """You are Neoscribe, an AI documentation drafting agent for Infor Information Development. Generate a valid DITA XML task topic.

RULES:
- Output ONLY valid DITA XML. No markdown, no explanations outside the XML.
- Use imperative mood for <cmd> elements (e.g., "Select the field", "Click Save").
- Use second person ("you") in non-command elements.
- Never fabricate steps not supported by the input.
- Insert [TODO: ...] placeholders for unclear steps.
- Label output with: <!-- AI-GENERATED DRAFT - Requires writer review and approval -->

STRUCTURE:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE task PUBLIC "-//OASIS//DTD DITA Task//EN" "task.dtd">
<!-- AI-GENERATED DRAFT - Requires writer review and approval -->
<task id="task_{id}">
  <title>{Gerund phrase title}</title>
  <shortdesc>{20-60 word description}</shortdesc>
  <taskbody>
    <prereq><p>{prerequisites}</p></prereq>
    <steps>
      <step><cmd>{imperative instruction}</cmd>
        <info><p>{additional context}</p></info>
      </step>
    </steps>
    <result><p>{expected outcome}</p></result>
  </taskbody>
</task>
```

ELEMENT RULES:
- <uicontrol> for UI element names (fields, buttons, tabs, menus, options)
- <wintitle> for screen/window/session names
- <menucascade><uicontrol>A</uicontrol><uicontrol>B</uicontrol></menucascade> for navigation paths
- <cmd> uses imperative mood: "Click", "Select", "Specify", "Navigate to"
- <info> provides context for a step (optional)
- <stepresult> for what happens after a step
- <note> for cautions/warnings (place BEFORE the step it refers to)
- Use <choices> or <substeps> for branching within a step

From the JIRA ticket content provided, create a task topic with clear step-by-step instructions."""

NEOSCRIBE_UPDATE_PROMPT = """You are Neoscribe, an AI documentation drafting agent for Infor Information Development. You are updating an EXISTING DITA XML topic with new information from a JIRA ticket.

RULES:
- Output ONLY valid DITA XML. No markdown, no explanations outside the XML.
- PRESERVE all existing content that is NOT affected by the update.
- RETAIN all existing metadata and attributes.
- Annotate changes with XML comments:
  <!-- CHANGED: brief description -->
  <!-- ADDED: brief description -->
  <!-- REMOVED: brief description -->
- Insert [TODO: ...] placeholders where new input is insufficient.
- Label output with: <!-- AI-GENERATED DRAFT - Requires writer review and approval -->
- Use second person, active voice, imperative mood for task steps.
- Do NOT fabricate information.

Given the existing topic XML and the JIRA ticket describing the change, produce the updated topic."""


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


def _call_llm(system_prompt, user_content, max_tokens=3000):
    """Make a single LLM call and return the response text."""
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
            temperature=0.15,
            max_tokens=max_tokens,
        )
        duration = int((time.time() - start_time) * 1000)
        response = completion.choices[0].message.content or ""
        logger.info(f"Neoscribe LLM call: duration={duration}ms, len={len(response)}")
        return response
    except Exception as e:
        error_msg = str(e)
        if "Connection refused" in error_msg or "connection error" in error_msg.lower():
            raise RuntimeError(
                "Cannot connect to Ollama. Ensure Ollama is running "
                f"and model '{OLLAMA_MODEL}' is pulled."
            )
        raise RuntimeError(f"LLM call failed: {error_msg}")

# =============================================================================
# POST-PROCESSING
# =============================================================================

def _extract_xml_from_response(response):
    """Extract DITA XML from LLM response, stripping any surrounding text.

    The LLM sometimes wraps XML in markdown code blocks or adds explanations.
    This extracts just the XML content.
    """
    # Try to find XML within code blocks first
    code_block_match = re.search(
        r'```(?:xml|dita)?\s*\n(.*?)```',
        response, re.DOTALL
    )
    if code_block_match:
        return code_block_match.group(1).strip()

    # Try to find content starting with <?xml or <!DOCTYPE or <concept or <task
    xml_match = re.search(
        r'(<\?xml.*?</(?:concept|task|topic)>)',
        response, re.DOTALL
    )
    if xml_match:
        return xml_match.group(1).strip()

    # Try without XML declaration
    xml_match = re.search(
        r'(<!DOCTYPE.*?</(?:concept|task|topic)>)',
        response, re.DOTALL
    )
    if xml_match:
        return xml_match.group(1).strip()

    # Try just the root element
    xml_match = re.search(
        r'(<(?:concept|task|topic)\b.*?</(?:concept|task|topic)>)',
        response, re.DOTALL
    )
    if xml_match:
        return xml_match.group(1).strip()

    # If nothing matched, return as-is (may need manual cleanup)
    return response.strip()


def _ensure_xml_declaration(xml_text):
    """Ensure the XML has a proper declaration and DOCTYPE."""
    if not xml_text.startswith('<?xml'):
        # Detect topic type from root element
        if '<task' in xml_text[:200]:
            doctype = '<!DOCTYPE task PUBLIC "-//OASIS//DTD DITA Task//EN" "task.dtd">'
        else:
            doctype = '<!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">'

        header = '<?xml version="1.0" encoding="UTF-8"?>\n'
        if '<!DOCTYPE' not in xml_text[:200]:
            header += doctype + '\n'
        header += '<!-- AI-GENERATED DRAFT - Requires writer review and approval -->\n'
        xml_text = header + xml_text
    elif '<!-- AI-GENERATED DRAFT' not in xml_text:
        # Add the draft label after XML declaration
        xml_text = xml_text.replace(
            '?>\n', '?>\n<!-- AI-GENERATED DRAFT - Requires writer review and approval -->\n',
            1
        )
    return xml_text

def _sanitize_id(text):
    """Create a valid DITA XML ID from text."""
    # Lowercase, replace non-alphanumeric with underscore, collapse multiples
    result = re.sub(r'[^a-z0-9]+', '_', text.lower())
    result = result.strip('_')
    return result[:60] if result else "untitled"


def _format_ticket_for_draft(issue, writer_instructions=""):
    """Format a JIRA issue into input text for the Neoscribe LLM."""
    parts = []
    parts.append(f"JIRA Ticket: {issue.get('key', 'Unknown')}")
    parts.append(f"Summary: {issue.get('summary', 'No summary')}")
    parts.append(f"Type: {issue.get('issue_type', 'Unknown')}")
    parts.append(f"Priority: {issue.get('priority', 'None')}")
    parts.append(f"Product/Components: {', '.join(issue.get('components', ['Unknown']))}")

    fix_versions = issue.get("fix_versions", [])
    if fix_versions:
        parts.append(f"Fix Version: {', '.join(fix_versions)}")

    parts.append("")
    description = issue.get("description", "")
    if description:
        parts.append("DESCRIPTION:")
        parts.append(description)
    else:
        parts.append("DESCRIPTION: [No description provided]")

    comments = issue.get("comments", [])
    if comments:
        parts.append("")
        parts.append("RELEVANT COMMENTS:")
        for c in comments[:3]:
            parts.append(f"- {c.get('author', 'Unknown')}: {c.get('body', '')}")

    if writer_instructions:
        parts.append("")
        parts.append("WRITER INSTRUCTIONS:")
        parts.append(writer_instructions)

    return "\n".join(parts)


# =============================================================================
# PUBLIC API
# =============================================================================

def generate_new_draft(issue, topic_type="auto", writer_instructions=""):
    """Generate a new DITA topic draft from a JIRA ticket (Mode 1).

    Args:
        issue: Normalized issue dict from jira_handler
        topic_type: "concept", "task", or "auto" (auto-detect from content)
        writer_instructions: Optional writer constraints/focus areas

    Returns:
        dict with:
        - success: bool
        - xml: str (the generated DITA XML)
        - topic_type: str ("concept" or "task")
        - issue_key: str
        - metadata: dict (suggested metadata)
        - error: str (if success is False)
    """
    try:
        # Auto-detect topic type if needed
        if topic_type == "auto":
            topic_type = _detect_topic_type(issue)

        # Select the appropriate prompt
        if topic_type == "task":
            system_prompt = NEOSCRIBE_TASK_PROMPT
        else:
            system_prompt = NEOSCRIBE_CONCEPT_PROMPT

        # Format input
        user_content = _format_ticket_for_draft(issue, writer_instructions)

        # Generate via LLM
        response = _call_llm(system_prompt, user_content, max_tokens=3000)

        # Post-process
        xml = _extract_xml_from_response(response)
        xml = _ensure_xml_declaration(xml)

        # Suggest metadata
        metadata = _suggest_metadata(issue, topic_type)

        return {
            "success": True,
            "xml": xml,
            "topic_type": topic_type,
            "issue_key": issue.get("key", ""),
            "metadata": metadata,
            "error": "",
        }
    except RuntimeError as e:
        return {
            "success": False,
            "xml": "",
            "topic_type": topic_type,
            "issue_key": issue.get("key", ""),
            "metadata": {},
            "error": str(e),
        }

def update_existing_topic(issue, existing_xml, writer_instructions=""):
    """Update an existing DITA topic with new info from a JIRA ticket (Mode 2).

    Args:
        issue: Normalized issue dict from jira_handler
        existing_xml: The current DITA XML topic content
        writer_instructions: Optional writer constraints

    Returns:
        dict with:
        - success: bool
        - xml: str (the updated DITA XML)
        - issue_key: str
        - changes: list of change annotations found
        - error: str (if success is False)
    """
    try:
        # Build the user content with both existing topic and new info
        ticket_info = _format_ticket_for_draft(issue, writer_instructions)

        user_content = (
            "EXISTING TOPIC XML:\n"
            "```xml\n"
            f"{existing_xml}\n"
            "```\n\n"
            "NEW INFORMATION FROM JIRA TICKET:\n"
            f"{ticket_info}\n\n"
            "Update the existing topic to incorporate the new information. "
            "Preserve all content not affected by the update. "
            "Annotate all changes with XML comments."
        )

        response = _call_llm(NEOSCRIBE_UPDATE_PROMPT, user_content, max_tokens=4000)

        # Post-process
        xml = _extract_xml_from_response(response)
        xml = _ensure_xml_declaration(xml)

        # Extract change annotations
        changes = re.findall(
            r'<!--\s*(CHANGED|ADDED|REMOVED):\s*(.*?)\s*-->',
            xml
        )
        change_list = [
            {"type": c[0].lower(), "description": c[1]}
            for c in changes
        ]

        return {
            "success": True,
            "xml": xml,
            "issue_key": issue.get("key", ""),
            "changes": change_list,
            "error": "",
        }
    except RuntimeError as e:
        return {
            "success": False,
            "xml": "",
            "issue_key": issue.get("key", ""),
            "changes": [],
            "error": str(e),
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _detect_topic_type(issue):
    """Auto-detect whether content should be a concept or task topic.

    Heuristics:
    - Task indicators: steps, procedures, actions, imperative verbs
    - Concept indicators: explanation, overview, description, what-is
    """
    text = f"{issue.get('summary', '')} {issue.get('description', '')}".lower()

    task_signals = [
        "step", "procedure", "workflow", "how to", "configure",
        "set up", "setup", "create", "navigate", "click", "select",
        "specify", "enable", "disable", "process", "perform",
        "instruction", "1.", "2.", "3.",
    ]

    concept_signals = [
        "overview", "about", "what is", "introduction", "concept",
        "description", "explain", "understand", "purpose", "background",
        "architecture", "design", "behavior", "feature",
    ]

    task_score = sum(1 for s in task_signals if s in text)
    concept_score = sum(1 for s in concept_signals if s in text)

    # Issue type hints
    issue_type = issue.get("issue_type", "").lower()
    if issue_type in ("bug", "defect"):
        task_score += 1  # Bugs often result in procedure updates
    elif issue_type in ("epic", "story"):
        concept_score += 1  # Epics/stories often need overview topics

    return "task" if task_score > concept_score else "concept"

def _suggest_metadata(issue, topic_type):
    """Suggest DITA metadata for the generated topic.

    Returns dict with suggested attributes and values.
    """
    summary = issue.get("summary", "Untitled")
    components = issue.get("components", [])
    fix_versions = issue.get("fix_versions", [])
    labels = issue.get("labels", [])

    # Generate topic ID
    topic_id = f"{topic_type}_{_sanitize_id(summary)}"

    # Suggest product attribute
    product = ""
    if components:
        product = components[0]
    elif labels:
        # Check for product-like labels
        for label in labels:
            if any(p.lower() in label.lower() for p in [
                "ln", "m3", "wms", "csb", "csi", "os", "hcm"
            ]):
                product = label
                break

    # Suggest rev attribute from fix version
    rev = ""
    if fix_versions:
        rev = fix_versions[0]

    return {
        "topic_id": topic_id,
        "suggested_title": summary,
        "topic_type": topic_type,
        "product": product,
        "rev": rev,
        "audience": "user",
        "source_ticket": issue.get("key", ""),
        "labels": labels,
        "components": components,
    }


def generate_fallback_draft(issue, topic_type="concept"):
    """Generate a basic DITA template without LLM (offline fallback).

    Used when Ollama is unavailable. Produces a skeleton topic
    with placeholders filled from the ticket data.

    Args:
        issue: Normalized issue dict
        topic_type: "concept" or "task"

    Returns:
        dict matching generate_new_draft() return format
    """
    summary = issue.get("summary", "Untitled Topic")
    description = issue.get("description", "")
    issue_key = issue.get("key", "")
    topic_id = _sanitize_id(summary)

    if topic_type == "task":
        xml = _build_task_skeleton(topic_id, summary, description, issue_key)
    else:
        xml = _build_concept_skeleton(topic_id, summary, description, issue_key)

    metadata = _suggest_metadata(issue, topic_type)

    return {
        "success": True,
        "xml": xml,
        "topic_type": topic_type,
        "issue_key": issue_key,
        "metadata": metadata,
        "error": "",
        "fallback": True,
    }

def _build_concept_skeleton(topic_id, title, description, issue_key):
    """Build a basic concept DITA skeleton from ticket data."""
    # Extract a short description (first sentence or first 60 words)
    shortdesc = _extract_shortdesc(description)

    # Build body content from description
    body_content = _description_to_sections(description)

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">
<!-- AI-GENERATED DRAFT - Requires writer review and approval -->
<!-- Source: {issue_key} -->
<concept id="concept_{topic_id}">
  <title>{_xml_escape(title)}</title>
  <shortdesc>{_xml_escape(shortdesc)}</shortdesc>
  <conbody>
{body_content}
  </conbody>
</concept>'''
    return xml


def _build_task_skeleton(topic_id, title, description, issue_key):
    """Build a basic task DITA skeleton from ticket data."""
    # Make title a gerund if it isn't already
    task_title = _ensure_gerund_title(title)
    shortdesc = _extract_shortdesc(description)

    # Try to extract steps from description
    steps_xml = _extract_steps(description)

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE task PUBLIC "-//OASIS//DTD DITA Task//EN" "task.dtd">
<!-- AI-GENERATED DRAFT - Requires writer review and approval -->
<!-- Source: {issue_key} -->
<task id="task_{topic_id}">
  <title>{_xml_escape(task_title)}</title>
  <shortdesc>{_xml_escape(shortdesc)}</shortdesc>
  <taskbody>
    <prereq>
      <p>[TODO: Confirm prerequisites with SME]</p>
    </prereq>
    <steps>
{steps_xml}
    </steps>
    <result>
      <p>[TODO: Describe the expected result]</p>
    </result>
  </taskbody>
</task>'''
    return xml


def _xml_escape(text):
    """Escape text for XML content."""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _extract_shortdesc(description):
    """Extract a suitable short description from the ticket description."""
    if not description:
        return "[TODO: Add short description (20-60 words)]"

    # Take first sentence
    sentences = re.split(r'(?<=[.!?])\s+', description.strip())
    if sentences:
        first = sentences[0].strip()
        words = first.split()
        if 10 <= len(words) <= 60:
            return first
        elif len(words) > 60:
            return " ".join(words[:50]) + "..."
        elif len(words) < 10 and len(sentences) > 1:
            # First sentence too short, combine with second
            combined = first + " " + sentences[1].strip()
            words = combined.split()
            return " ".join(words[:50])

    return description[:200] if len(description) > 200 else description

def _ensure_gerund_title(title):
    """Convert a title to gerund form if it isn't already.

    'Configure warehouse rules' -> 'Configuring warehouse rules'
    'Add new field' -> 'Adding a new field'
    """
    if not title:
        return "Performing the task"

    words = title.strip().split()
    if not words:
        return title

    first_word = words[0]

    # Already a gerund
    if first_word.endswith("ing"):
        return title

    # Common verb -> gerund mappings
    gerund_map = {
        "configure": "Configuring",
        "create": "Creating",
        "add": "Adding",
        "delete": "Deleting",
        "remove": "Removing",
        "update": "Updating",
        "edit": "Editing",
        "set": "Setting",
        "enable": "Enabling",
        "disable": "Disabling",
        "manage": "Managing",
        "define": "Defining",
        "assign": "Assigning",
        "run": "Running",
        "export": "Exporting",
        "import": "Importing",
        "install": "Installing",
        "deploy": "Deploying",
        "view": "Viewing",
        "search": "Searching",
        "filter": "Filtering",
    }

    lower_first = first_word.lower()
    if lower_first in gerund_map:
        words[0] = gerund_map[lower_first]
        return " ".join(words)

    # Generic gerund conversion
    if lower_first.endswith("e"):
        words[0] = first_word[:-1] + "ing"
    else:
        words[0] = first_word + "ing"

    return " ".join(words)


def _description_to_sections(description):
    """Convert ticket description text into DITA <section> elements."""
    if not description:
        return '    <section>\n      <p>[TODO: Add content based on feature details]</p>\n    </section>'

    lines = description.strip().split("\n")
    sections = []
    current_section_title = "Overview"
    current_content = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Detect headings (# markdown or ALL CAPS short lines)
        if stripped.startswith("#"):
            if current_content:
                sections.append((current_section_title, current_content))
                current_content = []
            current_section_title = stripped.lstrip("#").strip()
        elif (stripped == stripped.upper() and len(stripped.split()) <= 6
              and len(stripped) > 3 and not stripped.endswith((".", ",", ":"))):
            if current_content:
                sections.append((current_section_title, current_content))
                current_content = []
            current_section_title = stripped.title()
        else:
            current_content.append(stripped)

    if current_content:
        sections.append((current_section_title, current_content))

    # Build XML
    xml_parts = []
    for title, content in sections:
        xml_parts.append(f'    <section>')
        xml_parts.append(f'      <title>{_xml_escape(title)}</title>')
        for para in content:
            xml_parts.append(f'      <p>{_xml_escape(para)}</p>')
        xml_parts.append(f'    </section>')

    return "\n".join(xml_parts) if xml_parts else '    <section>\n      <p>[TODO: Add content]</p>\n    </section>'

def _extract_steps(description):
    """Try to extract procedural steps from the description.

    Looks for numbered lists, bullet lists, or imperative sentences.
    Falls back to placeholder steps if nothing is found.
    """
    if not description:
        return '      <step>\n        <cmd>[TODO: Add step instructions]</cmd>\n      </step>'

    steps = []

    # Look for numbered items (1. Step text, 2. Step text, etc.)
    numbered = re.findall(r'^\s*\d+[\.\)]\s*(.+)', description, re.MULTILINE)
    if numbered:
        for step_text in numbered:
            escaped = _xml_escape(step_text.strip())
            steps.append(f'      <step>\n        <cmd>{escaped}</cmd>\n      </step>')
        return "\n".join(steps)

    # Look for bullet items that sound procedural (start with imperative verbs)
    bullets = re.findall(r'^\s*[\-\*\u2022]\s*(.+)', description, re.MULTILINE)
    imperative_verbs = [
        "click", "select", "navigate", "open", "enter", "specify",
        "configure", "set", "choose", "verify", "ensure", "check",
        "save", "submit", "run", "create", "add", "remove", "delete",
    ]
    procedural_bullets = [
        b for b in bullets
        if any(b.strip().lower().startswith(v) for v in imperative_verbs)
    ]

    if procedural_bullets:
        for step_text in procedural_bullets:
            escaped = _xml_escape(step_text.strip())
            steps.append(f'      <step>\n        <cmd>{escaped}</cmd>\n      </step>')
        return "\n".join(steps)

    # Fallback: generate placeholder steps
    return (
        '      <step>\n'
        '        <cmd>[TODO: Describe the first action the user must perform]</cmd>\n'
        '      </step>\n'
        '      <step>\n'
        '        <cmd>[TODO: Describe the next action]</cmd>\n'
        '      </step>\n'
        '      <step>\n'
        '        <cmd>[TODO: Describe the final action]</cmd>\n'
        '      </step>'
    )
