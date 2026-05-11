# Phase 2: Business Logic Boundary Map

This document classifies all code in `frontend/app.js` for Phase 3 extraction.

## Classification Legend

| Tag | Meaning | Action in Phase 3 |
|-----|---------|-------------------|
| **[FRONTEND: UI]** | DOM manipulation, rendering, events | Stays in `app.js` |
| **[BACKEND: Logic]** | Business rules, analysis, transformation | Migrates to Python |
| **[SHARED: Utility]** | Small helpers used by both layers | May be duplicated |

---

## Functions to Extract to Python (Phase 3)

### → `backend/rules.py`

| Function/Data | Current Location (line ~) | Description |
|---------------|--------------------------|-------------|
| `CA_RULES` array | ~292 | All content analysis rule definitions (id, category, pattern, message, fix, color) |
| `RW_RULES` array | ~1263 | All rewrite rule definitions (type, pattern, fix, message) |
| `checkSentenceLevel(text)` | ~616 | Sentence length check (>25 words) and number-at-start detection |
| `checkSentenceLength(text)` | ~1403 | Sentence length check for rewrite output (>25 words) |

### → `backend/analyzer.py`

| Function/Data | Current Location (line ~) | Description |
|---------------|--------------------------|-------------|
| `collectViolations(text)` | ~647 | Runs all CA_RULES regex matches, calls checkSentenceLevel, resolves overlaps |
| `computeFixed(text)` | ~1005 | Applies all auto-fix rules to text, cleans up spacing |
| `applyRWRules(text)` | ~1418 | Applies all RW_RULES, post-processes, calls boldUIElements and checkSentenceLength |

### → `backend/utils.py`

| Function/Data | Current Location (line ~) | Description |
|---------------|--------------------------|-------------|
| `xEsc(s)` | ~33 | XML escape (&, <, >) for DITA output |
| `convertConcept()` logic | ~17 | Generate DITA conbody XML from text lines |
| `convertTask()` logic | ~23 | Generate DITA taskbody XML from numbered lines |
| `tokenise(str)` | ~104 | Lowercase word tokenization (length > 2) |
| `jaccardSim(a, b)` | ~110 | Jaccard similarity between two token arrays |
| `boldUIElements(text)` | ~1386 | Bold formatting for UI element names in rewritten text |
| `UI_CONTEXT_WORDS` array | ~1372 | List of UI context words for bold detection |

---

## Functions That Stay in Frontend (`app.js`)

### Tab Switching
- `openTab(id, e)` — tab visibility toggle

### Impact Analyzer — UI
- Excel file upload handler (SheetJS parsing, column detection)
- ZIP file upload handler (JSZip extraction, topic parsing)
- `runImpactAnalysis()` — input validation + calls backend (Phase 5)
- `showImpactError(msg)` — error display
- `renderImpactResults()` — DOM rendering of tables
- `clearImpactAnalysis()` — DOM reset
- `exportImpactCSV(which)` — CSV generation and download
- `csvCell(v)` — CSV escaping

### Content Analysis — UI
- `hEsc(s)`, `aEsc(s)`, `escJs(s)` — HTML/JS escape helpers for rendering
- `getContextHtml(text, v)` — context sentence extraction for display
- `RULE_ALTS` map — suggestion alternatives for UI buttons
- `getAlternatives(v)` — lookup alternatives for a violation
- `buildAnnotated(text, violations)` — render highlighted text
- `buildBadges(violations)` — render category badges
- `buildVTable(violations)` — render violations table
- `applyOneFix(vidx, replacement)` — apply single fix and re-analyze
- `applyCustomFromTable(vidx)` — apply custom replacement from table input
- `ignoreFix(vidx)` — mark violation as ignored
- `toggleDetailRow(vidx)` — expand/collapse table detail row
- `showFixPopup(vidx, el, e)` — position and populate fix popup
- `closeFixPopup()` — hide popup
- `applyFromPopup(value)` — apply fix from popup
- `applyPopupCustom()` — apply custom text from popup input
- `applyPopupDefault()` — apply first suggestion from popup
- `ignoreFromPopup()` — ignore from popup
- `refreshCADisplay()` — re-render all CA UI elements
- `runCA()` — trigger analysis (will call backend in Phase 5)
- `rerunCA()` — re-trigger after fix applied
- `clearCA()` — reset CA state and DOM
- `applyFixes()` — apply all auto-fixes (will call backend in Phase 5)
- `copyFixed()` — clipboard copy
- `downloadFixed()` — .docx export via docx.js
- Tooltip event listeners
- CA file upload handler (mammoth.js)

### Rewrite — UI
- `buildSideBySide(origText, rewrittenHtml)` — diff rendering
- `runRewrite()` — trigger rewrite (will call backend in Phase 5)
- `doRewrite(text)` — render rewrite results
- `clearRewrite()` — reset rewrite state
- `copyRwResult()` — clipboard copy
- `downloadRwWord()` — .docx export
- `toggleRwLog()` — expand/collapse change log
- Rewrite file upload handler (mammoth.js)

### Write Editor — UI (entire section)
- `wrCmd(cmd, val)` — execCommand wrapper
- `wrSetSize(pt)` — font size
- `wrApplyStyle(tag)` — block formatting
- `wrUpdate()` — word/char/para counts
- `wrUpdateToolbarState()` — toolbar active states
- `wrKeyDown(e)` — tab key handling
- `wrNew()` — new document
- `wrOpen()` / `wrFileOpened(inp)` — open file
- `wrSaveDocx()` — save as .docx
- `wrSaveTxt()` — save as .txt
- `wrPrint()` — print
- `wrToggleFindBar()` / `wrCloseFindBar()` — find bar toggle
- `wrFindNext()` / `wrReplaceOne()` / `wrReplaceAll()` — find/replace
- `wrInsertTable()` / `wrCloseTableDialog()` / `wrDoInsertTable()` — table insertion
- `wrInsertHR()` — horizontal rule
- `wrInsertLink()` — link insertion
- Keyboard shortcuts (Ctrl+S, Ctrl+F)
- DOMContentLoaded init

---

## Phase 3 Extraction Plan

1. **Create `backend/rules.py`** — Port `CA_RULES` and `RW_RULES` arrays as Python data structures. Port `checkSentenceLevel` and `checkSentenceLength`.

2. **Create `backend/utils.py`** — Port `xEsc`, `tokenise`, `jaccardSim`, `boldUIElements`, `UI_CONTEXT_WORDS`, and DITA generation logic (`convertConcept`/`convertTask` core logic).

3. **Create `backend/analyzer.py`** — Port `collectViolations`, `computeFixed`, `applyRWRules`, and add `convert_dita` and `impact_analyze` orchestration functions.

4. **Create `backend/protocol.py`** — stdin/stdout JSON message loop routing to analyzer functions.

---

## Notes

- Inline `onclick` handlers in `index.html` are preserved as-is (Phase 1 constraint).
- Dynamically generated UI elements (e.g., `rwInput`, `rw-results`) are created at runtime by JavaScript and are preserved unchanged.
- Frontend libraries (mammoth.js, SheetJS, JSZip, docx.js, FileSaver.js) remain in frontend.
- File parsing (.docx, .xlsx, .zip) stays in frontend — only extracted text/data is sent to backend.
