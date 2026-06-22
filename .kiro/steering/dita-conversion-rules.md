---
inclusion: fileMatch
fileMatchPattern: "**/dita_converter*,**/analyzer*,**/converter*,**/dita*"
---

# DOCX TO DITA CONVERSION RULE SPECIFICATION

These rules govern how the DOC to DITA converter transforms input text into DITA XML.

## 1. DOCUMENT TYPE DETECTION

- RULE-001: IF document contains ordered procedural steps THEN output topic type = task
- RULE-002: IF document primarily contains descriptive information THEN output topic type = concept
- RULE-003: IF document answers questions or provides reference data THEN output topic type = reference
- RULE-004: IF document contains mixed content THEN split into multiple topics and generate ditamap

## 2. TITLE MAPPING

- RULE-010: Word Heading 1 → `<title>`
- RULE-011: Only one Heading 1 allowed per topic
- RULE-012: Additional Heading 1 instances create new DITA topics
- RULE-013: Heading 2+ → `<section>/<title>`
- RULE-014: Empty headings are prohibited

## 3. BODY CONTENT

- RULE-020: Normal paragraph → `<p>`
- RULE-021: Consecutive related paragraphs remain within same section
- RULE-022: Blank paragraphs are removed
- RULE-023: Paragraphs containing only whitespace are discarded

## 4. TASK ELEMENTS

- RULE-030: Numbered list following an imperative heading becomes `<steps>`
- RULE-031: Each numbered item becomes `<step><cmd>...</cmd></step>`
- RULE-032: Sub-numbered items become `<substeps><substep><cmd>...</cmd></substep></substeps>`
- RULE-033: Text preceding steps becomes `<context>`
- RULE-034: Text after steps becomes `<result>`
- RULE-035: Warnings become `<stepsection>` when step specific
- RULE-036: Prerequisites become `<prereq>`

## 5. LIST HANDLING

- RULE-040: Bulleted list → `<ul>`
- RULE-041: Bullet item → `<li>`
- RULE-042: Numbered list → `<ol>`
- RULE-043: Nested list preserves hierarchy
- RULE-044: List depth greater than 5 generates warning

## 6. NOTES

- RULE-050: Note label = Note → `<note>`
- RULE-051: Warning label = Warning → `<note type="warning">`
- RULE-052: Caution label = Caution → `<note type="caution">`
- RULE-053: Danger label = Danger → `<note type="danger">`
- RULE-054: Tip label = Tip → `<note type="tip">`
- RULE-055: Important label = Important → `<note type="important">`
- No `<p>` inside `<note>`

## 7. TABLES

- RULE-060: Word table → `<table><tgroup>...</tgroup></table>`
- RULE-061: First row styled as header → `<thead><row><entry>...</entry></row></thead>`
- RULE-062: Remaining rows → `<tbody><row><entry>...</entry></row></tbody>`
- RULE-063: Merged cells generate appropriate rowspan/colspan
- RULE-064: Nested tables prohibited
- RULE-065: Table title → `<title>`
- RULE-066: Table description → `<desc>`

## 8. IMAGES

- RULE-070: Image → `<image href="...">`
- RULE-071: Image caption → `<fig><title>...</title><image .../></fig>`
- RULE-072: Caption becomes `<title>` inside `<fig>`
- RULE-073: Alternative text required via `<alt>`
- RULE-074: Missing alt text generates validation error
- RULE-075: Image width and height stored as attributes

## 9. CODE BLOCKS

- RULE-080: Monospace paragraph → `<codeblock>`
- RULE-081: Inline monospace text → `<codeph>`
- RULE-082: Programming language detected → output language attribute
- RULE-083: Preserve indentation

## 10. INLINE FORMATTING

- RULE-090: Bold → `<b>`
- RULE-091: Italic → `<i>`
- RULE-092: Underline → `<u>`
- RULE-093: Superscript → `<sup>`
- RULE-094: Subscript → `<sub>`
- RULE-095: Keyboard input → `<userinput>`
- RULE-096: File names → `<filepath>`
- RULE-097: System names → `<systemoutput>`
- RULE-098: Commands → `<cmdname>`
- RULE-099: Variables → `<varname>`

## 11. LINKS

- RULE-110: Internal bookmark → `<xref href="...">`
- RULE-111: External URL → `<xref href="..." scope="external">`
- RULE-112: Email → `<xref href="mailto:..." scope="external">`
- RULE-113: Broken links generate validation warning

## 12. UI DOMAIN

- RULE-120: Button names → `<uicontrol>`
- RULE-121: Menu paths → `<menucascade><uicontrol>...</uicontrol></menucascade>`
- RULE-122: Dialog names → `<wintitle>`
- RULE-123: Screen names → `<wintitle>`
- RULE-124: Window titles → `<wintitle>`

### UI Tagging Rules (from project requirements):
- Give `<uicontrol>` to words BEFORE: field, tab, button, menu, widget, check box, option
- Do NOT tag the trigger words themselves
- Give `<wintitle>` to words BEFORE: screen, window, session, dialogue box, panel, section
- Do NOT tag the trigger words themselves
- Never use `<menucascade>` in concept files
- Use `<menucascade>` in task files when ">" defines a navigation path

## 13. SOFTWARE DOMAIN

- RULE-130: Command syntax → `<cmdname>`
- RULE-131: API names → `<apiname>`
- RULE-132: Parameters → `<parmname>`
- RULE-133: Options → `<option>`
- RULE-134: User-entered values → `<userinput>`
- RULE-135: System output → `<systemoutput>`

### Userinput Rules:
- Apply `<userinput>` to words that come AFTER "set to" or "as"

## 14. REFERENCE TOPICS

- RULE-140: Properties table → `<properties>`
- RULE-141: Parameter definitions → `<plentry>`
- RULE-142: Definition term → `<dt>`
- RULE-143: Definition description → `<dd>`

## 15. GLOSSARY

- RULE-150: Glossary entry → `<glossentry>`
- RULE-151: Term → `<glossterm>`
- RULE-152: Definition → `<glossdef>`
- RULE-153: Acronym → `<glossAcronym>`

## 16. METADATA

- RULE-160: Document title → `<title>`
- RULE-161: Author → `<author>`
- RULE-162: Revision date → `<revised>`
- RULE-163: Keywords → `<keyword>`
- RULE-164: Product names → `<prodname>`
- RULE-165: Audience metadata → `<audience>`

## 17. CONDITIONAL PROCESSING

- RULE-170: Tagged content → audience attribute
- RULE-171: Platform-specific content → platform attribute
- RULE-172: Product-specific content → product attribute
- RULE-173: Version-specific content → rev attribute

## 18. DITAMAP GENERATION

- RULE-180: Each Heading 1 creates topic
- RULE-181: Parent-child hierarchy creates topicref structure
- RULE-182: Cross-references become map relationships
- RULE-183: Generate unique topic IDs
- RULE-184: Generate unique map IDs

## 19. VALIDATION

- RULE-190: Every topic must contain title
- RULE-191: Every image requires alt text
- RULE-192: No duplicate IDs allowed
- RULE-193: All xrefs must resolve
- RULE-194: All topicrefs must resolve
- RULE-195: XML must be schema valid
- RULE-196: No orphan topics
- RULE-197: No empty sections
- RULE-198: No empty tables
- RULE-199: No invalid nesting

## 20. OUTPUT

- RULE-200: Output UTF-8 XML
- RULE-201: Output valid DITA 1.3
- RULE-202: Generate topic files
- RULE-203: Generate ditamap
- RULE-204: Generate relationship tables
- RULE-205: Generate validation report
- RULE-206: Generate conversion log

## Key Constraints (from project-specific rules)

- Never use `<b>` tag in any format
- Never use `<para>` tag — use `<p>` instead
- Don't create unnecessary sections; only when required
- Never divide paragraphs into `<section>`
- Always provide a closing tag for every opened tag
- Never use `<menucascade>` in concept files
- Do not use `<p>` inside a `<note>`
- Do not modify the input language or structure
- Only display `<conbody>` elements for concept output
- Only display `<taskbody>` elements for task output
