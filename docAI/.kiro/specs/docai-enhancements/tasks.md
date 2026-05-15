# Tasks

## Task 1: Add CA Action Buttons (Copy, Download, Move to DITA)
- [x] 1.1 Add CSS styles for `.ca-action-btn`, `.ca-toast`, and `@keyframes caToastFade` to the `<style>` section of `DocAI-updated.html`
- [x] 1.2 Replace the existing "Annotated Text" heading block in the Content Analysis results section with the new flex layout containing the heading, subtitle, and three action buttons (Copy, Download, Move to Doc to DITA)
- [x] 1.3 Implement `caShowToast(msg, anchorEl)` function that creates a temporary toast element, appends it near the button, and auto-removes after 2000ms
- [x] 1.4 Implement `caAnnotatedCopy(btnEl)` function that copies rich HTML (from `_fixed` with formatting) or plain text (from `_text`) to clipboard using `navigator.clipboard.write()` with fallback to `execCommand('copy')`
- [x] 1.5 Implement `caAnnotatedDownload()` function that downloads fixed content as `.docx` (delegating to existing `downloadFixedRich()`) or annotated text as `.txt` file
- [x] 1.6 Implement `caMoveToConverter()` function that sets the DOC to DITA input textarea value to `_fixed || _text` and switches to the converter tab

## Task 2: Add Category Filter Bar to Issues Table
Depends on: Task 1
- [x] 2.1 Add CSS styles for `.ca-filter-btn` and `.ca-filter-active` classes to the `<style>` section
- [x] 2.2 Add `<div id="ca-filter-bar"></div>` HTML element above the Issues Table (`#vtable`) in the Content Analysis results section
- [x] 2.3 Add global variable `var _caActiveFilter = 'All';` to the script section
- [x] 2.4 Implement `buildFilterBar(violations)` function that counts active (non-ignored) violations per category and returns HTML string with "All" button plus one button per category with count badges
- [x] 2.5 Implement `caFilterByCategory(cat)` function that sets `_caActiveFilter`, re-renders filter bar, shows/hides table rows by `data-cat` attribute, and updates `#vcount` badge
- [x] 2.6 Modify `buildVTable()` to add `data-cat` attribute to each `<tr class="vrow">` and `<tr class="vdetail-row">` with the violation's category
- [x] 2.7 Modify `refreshCADisplay()` (or equivalent display refresh function) to call `buildFilterBar()` and inject into `#ca-filter-bar`, then apply current `_caActiveFilter`

## Task 3: Add Error Summary Panel
Depends on: Task 2
- [x] 3.1 Add CSS styles for `#ca-error-summary`, its table, headers, rows, hover states, and `.summary-total` class
- [x] 3.2 Restructure the Issues Table section HTML to wrap filter bar + table in a flex container with the new `<div id="ca-error-summary"></div>` panel alongside
- [x] 3.3 Add global variables `var _caSummarySortCol = 'category'; var _caSummarySortAsc = true;`
- [x] 3.4 Implement `buildErrorSummary(violations)` function that counts per category (excluding ignored), sorts by current sort column/direction, and returns HTML table with clickable headers and category rows
- [x] 3.5 Implement `caSortSummary(col)` function that toggles sort direction and re-renders the summary panel
- [x] 3.6 Modify `refreshCADisplay()` to also call `buildErrorSummary()` and inject into `#ca-error-summary`
- [x] 3.7 Wire Error Summary Panel category row clicks to call `caFilterByCategory(cat)` for cross-filtering with the Issues Table

## Task 4: Rename Write Tab to Author
- [x] 4.1 Change the tab label text from "Write" to "Author" in the HTML tab bar (keeping `onclick="openTab('rewrite',event)"` unchanged)
- [x] 4.2 Update any section comment headers from "TAB 4: WRITE" to "TAB 4: AUTHOR" for code clarity

## Task 5: Enhanced Word-like Comments System
Depends on: Task 4
- [x] 5.1 Add CSS styles for `.wr-comment-badge`, `.wr-cc-header`, `.wr-cc-author`, `.wr-cc-time`, `.wr-cc-resolved-badge`, `.wr-cc-actions`, `.wr-inline-reply`, `.wr-reply-input`, `.wr-reply`, `.wr-reply-author`, `.wr-reply-text`, and `.wr-comment-mark.wr-mark-hover`
- [x] 5.2 Add comment count badge HTML (`<span id="wr-comment-count-badge" class="wr-comment-badge"></span>`) to the "All" toolbar button
- [x] 5.3 Rewrite `wrRenderComments()` to render enhanced comment cards with author label "You", timestamp, selected text excerpt, comment body, action buttons (Reply, Resolve, Delete), resolved styling, and `data-cid` attributes
- [x] 5.4 Implement `wrHighlightMark(commentId, on)` function for hover-highlighting editor marks when hovering comment cards
- [x] 5.5 Implement `wrHighlightCard(commentId, on)` function for hover-highlighting comment cards when hovering editor marks
- [x] 5.6 Modify `wrSaveComment()` to attach `onmouseenter`/`onmouseleave` handlers on `.wr-comment-mark` spans that call `wrHighlightCard()`
- [x] 5.7 Implement `wrStartInlineReply(id)`, `wrCancelInlineReply(id)`, and `wrSubmitInlineReply(id)` functions for inline reply within comment cards
- [x] 5.8 Implement `wrUpdateCommentBadge()` function that counts active (unresolved) comments and updates `#wr-comment-count-badge`
- [x] 5.9 Add click handler on comment cards to scroll editor to the corresponding highlighted text

## Task 6: Cross-Tab Formatting Preservation Verification
Depends on: Task 1
- [x] 6.1 Verify that `wrSendToCA()` stores `page.innerHTML` in `_caSourceHtml` before sending to CA, and fix if not working correctly
- [x] 6.2 Verify that `caAnnotatedCopy()` (from Task 1.4) uses `applyFixesToHtml(_caSourceHtml)` when available to produce rich clipboard content preserving formatting
- [x] 6.3 Verify that `caAnnotatedDownload()` (from Task 1.5) uses `applyFixesToHtml(_caSourceHtml)` for `.docx` generation preserving formatting
- [x] 6.4 Verify that `wrPushBackFromCA()` applies fixes to `_caSourceHtml` and restores formatted content into the Author tab editor
- [x] 6.5 Ensure `applyFixesToHtml()` correctly handles bold, italic, underline, font-family, font-size, headings, and lists by walking text nodes only without stripping element structure

## Task 7: Highlight Palette Enhancement
Depends on: Task 4
- [x] 7.1 Verify the existing `wrShowPalette()` renders all 16 `WR_PALETTE` colors as a grid of clickable swatches with a "None" option
- [x] 7.2 Ensure the "None" button removes highlight color using `document.execCommand('hiliteColor', false, 'transparent')` and resets the toolbar indicator
- [x] 7.3 Modify `wrPickColor()` to update `#wr-hi-label` background to the selected color (or default `#ffff00` if "None") when in highlight mode
