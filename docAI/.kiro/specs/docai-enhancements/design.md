# Design Document: DocAI Enhancements

## Overview

This design covers nine enhancements to the DocAI single-file HTML application (~3121 lines). All changes are embedded directly into `DocAI-updated.html` — no external files. The enhancements span three areas:

1. **Content Analysis tab improvements** (Requirements 1–5): New action buttons (Copy, Download, Move to Doc to DITA) near the Annotated Text heading, category filter buttons above the Issues Table, and a right-side Error Summary Panel with sortable category counts.
2. **Author tab improvements** (Requirements 6–7, 9): Rename "Write" to "Author", enhanced Word-like margin comments with hover cross-highlighting and inline reply, and a proper 4×4 grid highlight palette with "None" option.
3. **Cross-tab formatting preservation** (Requirement 8): Ensure HTML formatting survives the Author → Content Analysis → Author round-trip for copy, download, and push-back operations.

All logic is client-side JavaScript using existing globals (`_text`, `_violations`, `_fixed`, `_caSourceHtml`, `_wrComments`, `WR_PALETTE`) and DOM APIs. The existing `docx` library (already embedded) handles `.docx` generation. The Clipboard API (`navigator.clipboard.write`) handles rich copy.

## Architecture

The application is a single HTML file with three embedded sections: `<style>` (CSS, lines ~5–440), `<body>` (HTML structure, lines ~440–935), and `<script>` (JavaScript, lines ~935–3121).

```
┌─────────────────────────────────────────────────┐
│  Tab bar                                        │
│   ├─ DOC to DITA | Impact Analyzer              │
│   ├─ Content Analysis | Author (renamed)        │
├─────────────────────────────────────────────────┤
│  Tab 3: Content Analysis (#contentAnalysis)     │
│   ├─ Input area + Analyze button                │
│   ├─ #ca-results                                │
│   │   ├─ Badges (#ca-badges)                    │
│   │   ├─ Annotated Text + action btns (NEW R1-3)│
│   │   ├─ Fixed section (#ca-fixed-section)      │
│   │   ├─ Filter bar (NEW R4)                    │
│   │   ├─ Issues Table (#vtable) + Error Summary │
│   │   │   Panel (NEW R5) in flex layout         │
│   │   └─ Fix popup (#ca-fix-popup)              │
├─────────────────────────────────────────────────┤
│  Tab 4: Author (#rewrite, renamed R6)           │
│   ├─ Toolbar (#wr-menubar) + comment badge (R7) │
│   ├─ Editor (#wr-page) + Comments panel (R7)    │
│   └─ Palette popup (#wr-palette, enhanced R9)   │
└─────────────────────────────────────────────────┘
```

### Change Strategy

| Requirement | CSS | HTML | JS |
|---|---|---|---|
| R1: Copy button | Toast style | Button near `#ca-annotated` heading | `caAnnotatedCopy()` |
| R2: Download button | — | Button near heading | `caAnnotatedDownload()` |
| R3: Move to DITA | — | Button near heading | `caMoveToConverter()` |
| R4: Category filter | Filter bar + active styles | `#ca-filter-bar` above `#vtable` | `caFilterByCategory()` |
| R5: Error Summary | Panel layout | `#ca-error-summary` in flex wrapper | `buildErrorSummary()` |
| R6: Rename tab | — | Tab label text | — |
| R7: Comments | Hover, inline reply styles | Restructured panel | Rewrite `wrRenderComments()` |
| R8: Formatting | — | — | Verify existing cross-tab functions |
| R9: Palette | Grid refinement | Palette HTML | `wrShowPalette()` update |

## Components and Interfaces

### Component 1: CA Action Buttons (R1, R2, R3)

Three buttons inserted adjacent to the "Annotated Text" `<h3>` heading inside `#ca-results`.

**HTML (replaces existing Annotated Text heading block):**
```html
<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px;">
  <h3 style="margin:0;">Annotated Text</h3>
  <span style="font-size:12px;color:#888;font-weight:normal;">
    — click a highlight to fix inline
  </span>
  <div style="margin-left:auto;display:flex;gap:6px;position:relative;">
    <button class="btn-sm ca-action-btn" onclick="caAnnotatedCopy(this)">📋 Copy</button>
    <button class="btn-sm ca-action-btn" onclick="caAnnotatedDownload()">⬇ Download</button>
    <button class="btn-sm ca-action-btn" onclick="caMoveToConverter()">➜ Move to Doc to DITA</button>
  </div>
</div>
```

**JS functions:**

- `caAnnotatedCopy(btnEl)` — If `_fixed` exists, copies rich HTML (via `applyFixesToHtml(_caSourceHtml)` if available, else formatted `_fixed`). Otherwise copies `_text` as plain text. Uses `navigator.clipboard.write()` with both `text/html` and `text/plain` MIME types. Calls `caShowToast('Copied!', btnEl)` on success.
- `caAnnotatedDownload()` — If `_fixed` exists, delegates to existing `downloadFixedRich()` for `.docx` output. Otherwise creates a `Blob` of `_text` as `text/plain` and triggers download as `content-analysis.txt`.
- `caMoveToConverter()` — Sets `document.getElementById('docInput').value` to `_fixed || _text`, then calls `openTab('converter', null)`.
- `caShowToast(msg, anchorEl)` — Creates a temporary `<span class="ca-toast">` appended to `anchorEl.parentElement`, auto-removed after 2000ms via CSS animation.

**CSS additions:**
```css
.ca-action-btn {
  background:#1a2332; color:#fff; border:none; border-radius:4px;
  padding:4px 10px; font-size:12px; cursor:pointer;
}
.ca-action-btn:hover { opacity:.85; }
.ca-toast {
  position:absolute; top:-28px; right:0;
  background:#28a745; color:#fff; padding:3px 10px;
  border-radius:4px; font-size:12px; font-weight:600;
  animation:caToastFade 2s forwards; pointer-events:none;
}
@keyframes caToastFade { 0%,70%{opacity:1} 100%{opacity:0} }
```

### Component 2: Category Filter Bar (R4)

A dynamically rendered row of filter buttons above the Issues Table.

**HTML (inserted before the `#vtable` overflow wrapper):**
```html
<div id="ca-filter-bar"></div>
```

**JS:**

- Global: `var _caActiveFilter = 'All';`
- `buildFilterBar(violations)` — Counts active (non-ignored) violations per category. Returns HTML string with an "All (N)" button plus one button per category with count. Active button gets `.ca-filter-active` class.
- `caFilterByCategory(cat)` — Sets `_caActiveFilter`, re-renders filter bar, shows/hides `#vtbody tr` rows by matching `data-cat` attribute, updates `#vcount` badge to visible count. Also updates the Error Summary Panel active highlight.
- **Modification to `buildVTable()`**: Each `<tr class="vrow">` and `<tr class="vdetail-row">` gets a `data-cat` attribute set to the violation's category string.
- **Modification to `refreshCADisplay()`**: After rendering table, calls `buildFilterBar()` → injects into `#ca-filter-bar`, then applies current `_caActiveFilter`.

**CSS:**
```css
.ca-filter-btn {
  background:#e9ecef; border:1px solid #dee2e6; border-radius:4px;
  padding:4px 10px; font-size:12px; cursor:pointer;
}
.ca-filter-btn:hover { background:#dee2e6; }
.ca-filter-active { background:#1a2332; color:#fff; border-color:#1a2332; }
```

### Component 3: Error Summary Panel (R5)

A fixed-width right-side panel displayed alongside the Issues Table area.

**HTML restructure:** The issues section (filter bar + table) is wrapped in a flex container with the summary panel:
```html
<div style="display:flex;gap:16px;align-items:flex-start;">
  <div style="flex:1;min-width:0;">
    <!-- filter bar + issues table -->
  </div>
  <div id="ca-error-summary"></div>
</div>
```

**JS:**

- Globals: `var _caSummarySortCol = 'category'; var _caSummarySortAsc = true;`
- `buildErrorSummary(violations)` — Counts per category (excluding ignored), sorts by `_caSummarySortCol`/`_caSummarySortAsc`. Returns HTML table with clickable column headers (Category, Count) showing sort arrows, clickable category rows that call `caFilterByCategory(cat)`, and a bold Total row.
- `caSortSummary(col)` — Toggles sort direction if same column, else sets ascending. Re-renders summary.
- **Modification to `refreshCADisplay()`**: Calls `buildErrorSummary()` → injects into `#ca-error-summary`.

**CSS:**
```css
#ca-error-summary {
  width:220px; flex-shrink:0; background:#f8f9fa;
  border:1px solid #dee2e6; border-radius:6px; padding:12px;
  position:sticky; top:16px;
}
#ca-error-summary table { width:100%; border-collapse:collapse; font-size:13px; }
#ca-error-summary th {
  cursor:pointer; padding:6px 8px; border-bottom:2px solid #dee2e6;
  text-align:left; font-size:12px; user-select:none;
}
#ca-error-summary th:hover { background:#e9ecef; }
#ca-error-summary td { padding:5px 8px; border-bottom:1px solid #eee; cursor:pointer; }
#ca-error-summary tr:hover td { background:#e9ecef; }
#ca-error-summary .summary-total td { font-weight:700; border-top:2px solid #dee2e6; }
```

### Component 4: Tab Rename (R6)

Minimal change — update the tab label text from "Write" to "Author" in the HTML tab bar. The internal ID `rewrite` and all JS function names remain unchanged for backward compatibility.

**HTML change:**
```html
<!-- Before -->
<span class="tab" onclick="openTab('rewrite',event)">Write</span>
<!-- After -->
<span class="tab" onclick="openTab('rewrite',event)">Author</span>
```

Also update the section comment header from "TAB 4: WRITE" to "TAB 4: AUTHOR" for clarity.

### Component 5: Enhanced Comments System (R7)

Major enhancement of `wrRenderComments()` and supporting functions for Word-like margin comments.

**Key behaviors:**
1. Comment cards positioned vertically in the side panel, visually adjacent to their highlighted text
2. Bidirectional hover highlighting: hovering a card highlights the editor mark, hovering a mark highlights the card
3. Click card → scroll editor to highlighted text
4. Each card shows: author label ("You"), timestamp, selected text excerpt, comment body, action buttons (Reply, Resolve, Delete)
5. Inline reply input within the card (no separate dialog)
6. Resolved comments: strikethrough text, reduced opacity on card and dashed border on editor highlight
7. Comment count badge on the "All" toolbar button

**HTML changes:**

The `wrSaveComment()` function is modified so that when adding a new comment, it also attaches `onmouseenter`/`onmouseleave` handlers to the `.wr-comment-mark` span for reverse hover highlighting.

The "All" button gets a badge span:
```html
<button class="wr-tb-btn" id="btn-comments-panel" onclick="wrToggleCommentsPanel()">
  📋 All <span id="wr-comment-count-badge" class="wr-comment-badge"></span>
</button>
```

**Rewritten `wrRenderComments()`:**

Each comment card now includes:
- `data-cid` attribute for JS targeting
- `onmouseenter`/`onmouseleave` calling `wrHighlightMark(id, true/false)`
- Author "You" label and timestamp in header
- Resolved badge when applicable
- Inline reply box (hidden by default, toggled by Reply button)
- `event.stopPropagation()` on action buttons to prevent card click from scrolling

**New JS functions:**

- `wrHighlightMark(commentId, on)` — Finds `.wr-comment-mark[data-comment-id]` in editor, toggles enhanced background/box-shadow.
- `wrHighlightCard(commentId, on)` — Finds `.wr-comment-card[data-cid]` in panel, toggles border-left-color/box-shadow. Called from `onmouseenter`/`onmouseleave` on `.wr-comment-mark` spans.
- `wrStartInlineReply(id)` — Shows the `#wr-reply-box-{id}` div and focuses the textarea.
- `wrCancelInlineReply(id)` — Hides the reply box.
- `wrSubmitInlineReply(id)` — Reads reply text, pushes to `parent.replies[]`, re-renders comments.
- `wrUpdateCommentBadge()` — Counts active (unresolved) comments, updates `#wr-comment-count-badge` text. Called from `wrRenderComments()`.

**Modification to `wrSaveComment()`:** After creating the `.wr-comment-mark` span, attach hover handlers:
```javascript
span.onmouseenter = function(){ wrHighlightCard(id, true); };
span.onmouseleave = function(){ wrHighlightCard(id, false); };
```

**CSS additions:**
```css
.wr-comment-badge {
  background:#e74c3c; color:#fff; font-size:10px; font-weight:700;
  padding:1px 5px; border-radius:8px; margin-left:4px;
}
.wr-comment-badge:empty { display:none; }
.wr-cc-header { display:flex; justify-content:space-between; margin-bottom:3px; }
.wr-cc-author { font-size:11px; font-weight:700; color:#1a2332; }
.wr-cc-time { font-size:10px; color:#999; }
.wr-cc-resolved-badge {
  font-size:10px; color:#28a745; font-weight:600; margin-bottom:3px; display:block;
}
.wr-cc-actions { margin-top:5px; display:flex; gap:8px; flex-wrap:wrap; }
.wr-inline-reply { margin-top:6px; border-top:1px solid #eee; padding-top:6px; }
.wr-reply-input {
  width:100%; box-sizing:border-box; padding:4px 6px;
  border:1px solid #ccc; border-radius:4px; font-size:12px; resize:vertical;
}
.wr-reply { border-top:1px solid #e0e0e0; margin-top:5px; padding-top:5px; }
.wr-reply-author { font-size:10px; color:#999; }
.wr-reply-text { font-size:11px; color:#333; line-height:1.4; }
.wr-comment-mark.wr-mark-hover {
  background:rgba(74,134,232,.45) !important;
  box-shadow:0 0 0 2px rgba(74,134,232,.3);
}
```

### Component 6: Cross-Tab Formatting Preservation (R8)

The existing implementation already handles most of R8. The key functions are:

1. `wrSendToCA()` — Stores `page.innerHTML` in `_caSourceHtml` before sending plain text to CA. ✅ Already implemented.
2. `copyFixedRich()` — Uses `applyFixesToHtml(_caSourceHtml)` when available to produce rich clipboard content. ✅ Already implemented.
3. `downloadFixedRich()` — Uses `applyFixesToHtml(_caSourceHtml)` to build `.docx` preserving formatting. ✅ Already implemented.
4. `wrPushBackFromCA()` — Applies fixes to `_caSourceHtml` and sets `wr-page.innerHTML`. ✅ Already implemented.

**Verification needed:** Ensure `applyFixesToHtml()` correctly handles bold, italic, underline, font-family, font-size, headings (`<h1>`–`<h6>`), and lists (`<ul>`, `<ol>`) by walking text nodes only and not stripping element structure. The current implementation uses a DOM walker on text nodes, which preserves element structure. No code changes required — only testing verification.

**Design decision:** No new code needed. The existing `_caSourceHtml` round-trip mechanism already preserves formatting. The new `caAnnotatedCopy()` and `caAnnotatedDownload()` functions (R1, R2) reuse this same mechanism.

### Component 7: Highlight Palette Enhancement (R9)

Update the existing palette to display a proper 4×4 grid with a "None" option and toolbar indicator update.

**Current state:** `wrShowPalette()` already renders `WR_PALETTE` (16 colors) as a grid of swatches with a "None" button. The grid uses `grid-template-columns: repeat(8, 20px)` — an 8×2 layout.

**Changes:**

1. Keep the 8×2 grid layout (it's compact and usable; changing to 4×4 would make it taller without benefit). The requirement says "grid of clickable color swatches" which the current 8×2 satisfies.
2. Ensure the "None" button explicitly removes highlight (`document.execCommand('hiliteColor', false, 'transparent')`) and resets the toolbar indicator.
3. After picking a highlight color, update `#wr-hi-label` background to the selected color (or reset to default yellow if "None").

**Modification to `wrPickColor()`:**
```javascript
// After applying color, update toolbar indicator
if (_wrPaletteMode === 'hi') {
  document.getElementById('wr-hi-label').style.background = hex || '#ffff00';
}
```

**Modification to `wrShowPalette()`:** Ensure the "None" button text reads "No highlight" for highlight mode and "No color" for text mode (already implemented). Verify the `onclick` calls `wrPickColor(null)` which should pass `transparent` to `hiliteColor`.

## Data Models

All data is held in JavaScript globals within the single HTML file. No persistent storage or external APIs are involved.

### Existing Globals (unchanged)

| Variable | Type | Description |
|---|---|---|
| `_text` | `string` | Raw plain text from CA input |
| `_violations` | `Array<{start, end, cat, msg, color, fix, pattern}>` | Detected violations with positions |
| `_fixed` | `string` | Text after auto-fixes applied |
| `_ignoredSet` | `Set<number>` | Indices of ignored violations |
| `_caSourceHtml` | `string` | Original HTML from Author tab for rich round-trip |
| `_wrComments` | `Array<CommentObj>` | Comments in Author tab |
| `_wrCommentCounter` | `number` | Auto-increment comment ID counter |
| `WR_PALETTE` | `Array<string>` | 16 hex color strings |
| `CA_RULES` | `Array<RuleObj>` | Violation detection rules |

### Existing CommentObj Shape (enhanced for R7)

```javascript
{
  id: 'wrc-1',           // unique ID
  sel: 'selected text',  // excerpt of highlighted text (max 60 chars)
  text: 'comment body',  // user's comment
  resolved: false,       // boolean
  replies: [             // array of reply objects
    { text: 'reply text', time: '10:30 AM' }
  ],
  time: '10:25 AM'       // creation timestamp
}
```

No shape changes needed — the existing structure supports all R7 features. The `author` field is not stored since it always defaults to "You" (single-user app).

### New Globals

| Variable | Type | Description |
|---|---|---|
| `_caActiveFilter` | `string` | Currently active category filter, default `'All'` |
| `_caSummarySortCol` | `string` | Error summary sort column: `'category'` or `'count'` |
| `_caSummarySortAsc` | `boolean` | Error summary sort direction |

### Violation Object Shape (existing, for reference)

```javascript
{
  start: 42,              // character offset in _text
  end: 48,                // character offset end
  cat: 'Grammar',         // category string
  msg: 'Use active voice',// rule message
  color: 'ca-replace',    // CSS class for highlight color
  fix: 'corrected text',  // auto-fix value (undefined if no auto-fix)
  pattern: /regex/        // original pattern
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Move to DITA content selection

*For any* combination of `_text` (non-empty string) and `_fixed` (string or empty), calling `caMoveToConverter()` SHALL set `docInput.value` to `_fixed` when `_fixed` is non-empty, otherwise to `_text`.

**Validates: Requirements 3.2**

### Property 2: Filter bar category completeness

*For any* array of violations with various categories, `buildFilterBar(violations)` SHALL produce buttons for exactly the set of unique categories present in active (non-ignored) violations, plus an "All" button.

**Validates: Requirements 4.1**

### Property 3: Category filter correctness

*For any* array of violations and any selected category filter (including "All"), after calling `caFilterByCategory(cat)`, only table rows whose `data-cat` attribute matches `cat` SHALL be visible (or all rows if `cat` is "All").

**Validates: Requirements 4.2, 4.3, 5.4**

### Property 4: Filter count consistency

*For any* array of violations and any selected category filter, the displayed `#vcount` badge value SHALL equal the number of active (non-ignored) violations matching the selected category (or all active violations if filter is "All").

**Validates: Requirements 4.5**

### Property 5: Error summary count accuracy

*For any* array of violations, `buildErrorSummary(violations)` SHALL list each category with a count equal to the number of active (non-ignored) violations in that category, and the Total row SHALL equal the sum of all category counts.

**Validates: Requirements 5.2**

### Property 6: Error summary sort correctness

*For any* set of category-count pairs and any sort column (category name or count) and direction (ascending/descending), the Error Summary Panel rows SHALL be ordered according to the selected sort criteria.

**Validates: Requirements 5.3**

### Property 7: Hover mark highlights corresponding card

*For any* comment in `_wrComments` that has a corresponding `.wr-comment-mark` in the editor, triggering `mouseenter` on the mark SHALL cause the corresponding `.wr-comment-card[data-cid]` to receive visual emphasis (border/shadow change).

**Validates: Requirements 7.2**

### Property 8: Hover card highlights corresponding mark

*For any* comment in `_wrComments` that has a corresponding `.wr-comment-mark` in the editor, triggering `mouseenter` on the `.wr-comment-card` SHALL cause the corresponding `.wr-comment-mark` to receive visual emphasis (enhanced background/box-shadow).

**Validates: Requirements 7.3**

### Property 9: Comment card rendering completeness

*For any* comment object (with arbitrary text, selection excerpt, timestamp, resolved state, and replies), the rendered comment card HTML SHALL contain: the author label "You", the timestamp string, the selection excerpt, the comment body text (with strikethrough if resolved), Reply/Resolve/Delete action elements, and reduced opacity if resolved.

**Validates: Requirements 7.5, 7.7**

### Property 10: Comment badge active count

*For any* array of comment objects with various `resolved` states, `wrUpdateCommentBadge()` SHALL set the badge text to the count of comments where `resolved === false`. If the count is zero, the badge SHALL be empty.

**Validates: Requirements 7.8**

### Property 11: HTML formatting preservation through fix application

*For any* HTML string containing formatting elements (bold, italic, underline, headings, lists), `applyFixesToHtml(html)` SHALL preserve the element structure (tag names and attributes) while only modifying text node content according to CA_RULES fix patterns.

**Validates: Requirements 8.1, 8.2, 8.4**

### Property 12: Toolbar indicator reflects palette selection

*For any* hex color string from `WR_PALETTE` (or null for "None"), after calling `wrPickColor(hex)` in highlight mode, the `#wr-hi-label` element's background style SHALL equal the selected hex color (or the default `#ffff00` if null).

**Validates: Requirements 9.4**

## Error Handling

### Clipboard API Failures (R1)

The `navigator.clipboard.write()` API may fail due to:
- Browser not supporting Clipboard API (older browsers)
- Page not served over HTTPS (required for clipboard access)
- User denying clipboard permission

**Strategy:** Wrap clipboard call in try/catch. On failure, fall back to `document.execCommand('copy')` with a temporary textarea. Show toast "Copy failed — try Ctrl+C" if both methods fail.

```javascript
function caAnnotatedCopy(btnEl) {
  // ... build html/plain ...
  try {
    navigator.clipboard.write([new ClipboardItem({
      'text/html': new Blob([html], {type:'text/html'}),
      'text/plain': new Blob([plain], {type:'text/plain'})
    })]).then(function(){ caShowToast('Copied!', btnEl); })
      .catch(function(){ caFallbackCopy(plain, btnEl); });
  } catch(e) {
    caFallbackCopy(plain, btnEl);
  }
}
function caFallbackCopy(text, btnEl) {
  var ta = document.createElement('textarea');
  ta.value = text; document.body.appendChild(ta);
  ta.select(); document.execCommand('copy');
  document.body.removeChild(ta);
  caShowToast('Copied (plain text)', btnEl);
}
```

### Download Failures (R2)

Blob URL creation and anchor click download are well-supported. The `.docx` generation via the `docx` library may throw if HTML parsing fails.

**Strategy:** Wrap `downloadFixedRich()` call in try/catch. On failure, fall back to `.txt` download.

### Empty Content (R1, R2, R3)

If both `_text` and `_fixed` are empty when action buttons are clicked:

**Strategy:** Show `alert('No content to copy/download. Run analysis first.')` and return early.

### Filter with No Matching Violations (R4)

If a category filter is applied but all violations in that category have been ignored:

**Strategy:** Show "No issues in this category" message in the table area. The filter bar re-renders on each `refreshCADisplay()` call, so ignored violations are excluded from category counts.

### Comment Mark Not Found (R7)

If a `.wr-comment-mark` span is removed from the editor (e.g., user deletes the text), hover/click handlers should gracefully handle the missing element.

**Strategy:** All `wrHighlightMark()`, `wrHighlightCard()`, and `wrScrollToComment()` functions check for element existence before operating:
```javascript
function wrHighlightMark(commentId, on) {
  var mark = document.querySelector('.wr-comment-mark[data-comment-id="'+commentId+'"]');
  if (!mark) return; // mark was deleted from editor
  // ... apply styles
}
```

### Cross-Node Selection for Comments (R7)

The existing `surroundContents()` call throws when the selection spans multiple DOM nodes.

**Strategy:** Already handled with try/catch in existing `wrSaveComment()`. The comment is still saved to `_wrComments` even if the highlight span can't be created. The card will render without a clickable excerpt link.

## Testing Strategy

### Unit Tests (Example-Based)

Unit tests cover specific scenarios, DOM presence checks, and edge cases. Use a lightweight test runner (e.g., inline test functions or a simple assertion helper embedded in the HTML for development).

Key unit test scenarios:
- **R1:** Copy button exists after `runCA()`. Toast appears and disappears.
- **R2:** Download triggers `.docx` when `_fixed` set, `.txt` when not.
- **R3:** Move to DITA button exists. Tab switches to converter.
- **R4:** Active filter button has `.ca-filter-active` class.
- **R5:** Error Summary Panel visible after `runCA()`. Fixed width CSS applied.
- **R6:** Tab label reads "Author". Tab ID is still "rewrite".
- **R7:** Comment card appears after `wrSaveComment()`. Inline reply box toggles. Click card calls `scrollIntoView`.
- **R8:** `_caSourceHtml` populated after `wrSendToCA()`.
- **R9:** 16 swatches rendered. "None" button exists.

### Property-Based Tests

Property-based tests validate universal properties across generated inputs. Use **fast-check** (JavaScript PBT library) with minimum 100 iterations per property.

Each property test references its design document property with a tag comment:
```javascript
// Feature: docai-enhancements, Property 1: Move to DITA content selection
```

**Property test implementations:**

1. **Property 1 (Move to DITA):** Generate arbitrary `_text` (non-empty string) and `_fixed` (string, possibly empty). Set globals, call `caMoveToConverter()`, assert `docInput.value === (_fixed || _text)`.

2. **Property 2 (Filter bar completeness):** Generate array of violation objects with random categories from a known set. Call `buildFilterBar()`, parse output HTML, assert button labels match unique categories + "All".

3. **Property 3 (Filter correctness):** Generate violations, render table with `buildVTable()`, apply `caFilterByCategory(cat)` for a random category, assert only rows with matching `data-cat` are visible.

4. **Property 4 (Filter count):** Same setup as Property 3, assert `#vcount` text equals count of matching violations.

5. **Property 5 (Summary counts):** Generate violations, call `buildErrorSummary()`, parse output, assert each category count matches `violations.filter(v => v.cat === cat).length` and total is sum.

6. **Property 6 (Summary sort):** Generate category-count pairs, set sort column/direction, call `buildErrorSummary()`, assert rows are in correct order.

7. **Property 7 (Hover mark → card):** Create comments with marks in a mock editor, trigger mouseenter on mark, assert card element has emphasis styles.

8. **Property 8 (Hover card → mark):** Reverse of Property 7.

9. **Property 9 (Card rendering):** Generate comment objects with random text/sel/time/resolved/replies, render via `wrRenderComments()`, assert each card contains author "You", timestamp, excerpt, body, action buttons, and correct resolved styling.

10. **Property 10 (Badge count):** Generate array of comments with random resolved states, call `wrUpdateCommentBadge()`, assert badge text equals count of `!resolved`.

11. **Property 11 (HTML preservation):** Generate HTML strings with random combinations of `<b>`, `<i>`, `<u>`, `<h1>`–`<h3>`, `<ul>/<li>` wrapping random text. Call `applyFixesToHtml(html)`, parse result, assert all original element tags and attributes are preserved (only text content may change).

12. **Property 12 (Toolbar indicator):** For each color in `WR_PALETTE` plus null, call `wrPickColor()` in highlight mode, assert `#wr-hi-label` background matches.

### Integration Tests

- **R2:** Full `.docx` download flow with formatted content from Author tab.
- **R6:** All existing Author tab operations (bold, italic, save, export, send to CA) work after rename.
- **R8:** Full round-trip: Author → CA → apply fixes → push back → verify formatting preserved.

### Test Configuration

- Property tests: minimum 100 iterations each
- Tag format: `Feature: docai-enhancements, Property {N}: {title}`
- Library: fast-check (can be loaded via CDN `<script>` tag for testing, or run in Node.js with jsdom)
