# Feature Guide — Documentation AI Tool

## Tab 1: DOC to DITA Converter

**Purpose:** Convert document content into DITA XML format.

**How to use:**
1. Paste content from Word/Google Docs (or upload .docx/.html/.txt)
2. Click "Convert to Concept" or "Convert to Task"
3. Copy or download the generated XML

**Supports:** Rich text paste (tables, lists, headings preserved), .docx upload, .html upload

---

## Tab 2: Content Analysis

**Purpose:** Check content against 90+ Infor writing rules with inline fix suggestions.

**How to use:**
1. Paste text or upload .txt/.docx
2. Click "Analyze Content"
3. Click any colored highlight for fix popup
4. Accept suggestions or type custom replacements
5. Ctrl+Z to undo, Ctrl+Y to redo

**Rule categories:** Grammar, Word Usage, Pronouns, Style & Tone, Punctuation, Numbers, Translation, UI Conventions

**Features:**
- Grammarly-style inline fix popup
- Docked issues panel with category filtering
- Global undo/redo
- Export results, send to DITA converter

---

## Tab 3: Initial Draft Editor

**Purpose:** Lightweight Word-style editor with comments and direct analysis integration.

**How to use:**
1. Type or paste content
2. Format with toolbar (fonts, headings, bold, lists, tables)
3. Select text → "Comment" to annotate
4. Click "Analyze" to send content to Content Analysis

**Features:**
- Full formatting toolbar (B/I/U, alignment, lists, tables, links)
- Find & Replace (Ctrl+F)
- Word/character/paragraph count
- Comment threads with replies (persist via localStorage)
- Save as .docx or .txt
- Keyboard shortcuts: Ctrl+S, Ctrl+B/I/U, Ctrl+F

---

## Tab 4: MarkItDown

**Purpose:** Convert any file or URL to Markdown format.

**How to use:**
1. Drag-and-drop a file OR enter a URL
2. Click "Convert to Markdown"
3. Toggle raw/rendered view, copy or download

**Supported formats:** PDF, Word, PowerPoint, Excel, HTML, Images (OCR), Audio (transcription), EPUB, Outlook messages, Jupyter notebooks, CSV, JSON, XML

---

## Tab 5: Quick Review

**Purpose:** Instant compliance scoring + automatic standards-compliant rewrite.

**How to use:**
1. Paste content or upload file
2. Click "Run Review"
3. See: compliance score, topic type, violations, suggestions, and rewritten version

**Score breakdown (100 points):**
- Information Typing: 25%
- DITA Structure: 20%
- Global English: 15%
- Translation Readiness: 15%
- Writing Quality: 10%
- Terminology: 5%
- Reusability: 5%
- Content Efficiency: 5%

---

## Tab 6: Doc Impact

**Purpose:** Identify which documentation needs updating based on Jira ticket changes.

**How to use:**
1. Export validation JSON files from your impact assessment sessions
2. Drag-and-drop the JSON files into the import area
3. Click "Run Impact Assessment"
4. Review the dashboard: summary stats, impacted areas, ticket details, timeline

**Output includes:**
- Severity classification (Critical/High/Medium/Low)
- Impacted documentation areas (8 categories)
- Per-ticket recommendations
- Release timeline grouping
- CSV export

---

## Tab 7: AI Assistant

**Purpose:** Chat with a local AI trained on Infor ID writing standards.

**How to use:**
1. Click a suggestion template OR type your question
2. Click 📎 to attach documentation context
3. Press Enter to send

**22 capabilities including:**
- Review content for compliance
- Rewrite for clarity
- Summarize help topics
- Create outlines, FAQs, troubleshooting, release notes
- Explain APIs and configurations
- Suggest topic types and metadata
- Compare documentation across products
- Plan information architecture

**Performance:** 4-5s per response (warm), ~60s first request (model loading)

---

## Keyboard Shortcuts

| Shortcut | Action | Where |
|----------|--------|-------|
| Ctrl+S | Save as .docx | Initial Draft |
| Ctrl+F | Find & Replace | Initial Draft |
| Ctrl+B/I/U | Bold/Italic/Underline | Initial Draft |
| Ctrl+Z | Undo fix | Content Analysis |
| Ctrl+Y | Redo fix | Content Analysis |
| Enter | Send message | AI Assistant |
| Shift+Enter | New line | AI Assistant |
| Ctrl+Scroll | Zoom in/out | All tabs |
