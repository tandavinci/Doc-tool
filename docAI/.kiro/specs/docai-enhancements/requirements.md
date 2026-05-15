# Requirements Document

## Introduction

This document specifies enhancements to the Documentation AI Tool (DocAI), a single-file HTML application with four tabs: DOC to DITA, Impact Analyzer, Content Analysis, and Author (renamed from Write). All enhancements operate entirely client-side within the existing HTML file. The changes span the Content Analysis tab (new action buttons, error filtering, sortable error summary panel), the Author tab (rename, enhanced Word-like comments), cross-tab formatting preservation, and highlight palette improvements.

## Glossary

- **DocAI_App**: The single-file HTML Documentation AI Tool application containing all tabs, styles, and scripts.
- **Content_Analysis_Tab**: The tab (id `contentAnalysis`) that checks content against Infor Writing Standards, highlights violations inline, and provides fix suggestions.
- **Author_Tab**: The tab (id `rewrite`, formerly labeled "Write") providing a lightweight Word-like editor with formatting toolbar, comments, and save/export features.
- **Annotated_Text_Section**: The `#ca-annotated` container in the Content Analysis tab that displays analyzed content with inline violation highlights.
- **Issues_Table**: The `#vtable` HTML table in the Content Analysis tab listing all detected violations with category, word/phrase, role, rule, and actions columns.
- **Error_Summary_Panel**: A new right-side panel in the Content Analysis tab that displays violation counts grouped and sortable by category (Grammar, Translation, Style & Tone, Word Usage, Punctuation, and Total).
- **Comments_System**: The existing JavaScript-based commenting feature in the Author tab that supports add, reply, resolve, and delete operations on selected text ranges.
- **CA_RULES**: The JavaScript array of rule objects defining violation patterns, categories, messages, and optional auto-fix values.
- **Violation_Category**: One of the six classification labels assigned to each rule in CA_RULES: Grammar, Word Usage, Style & Tone, Punctuation, Translation, or Structure.
- **WR_PALETTE**: The existing 16-color array used for text color and highlight color selection in the Author tab toolbar.

## Requirements

### Requirement 1: Content Analysis Annotated Text Copy Button

**User Story:** As a technical writer, I want to copy the annotated or fixed content from the Content Analysis tab, so that I can paste it into other applications while preserving formatting.

#### Acceptance Criteria

1. WHEN the Content Analysis results are displayed, THE Content_Analysis_Tab SHALL display a "Copy" button adjacent to the Annotated_Text_Section heading.
2. WHEN the user clicks the Copy button and fixed text is available, THE Content_Analysis_Tab SHALL copy the fixed rich-formatted content to the system clipboard.
3. WHEN the user clicks the Copy button and no fixed text is available, THE Content_Analysis_Tab SHALL copy the annotated text content to the system clipboard.
4. WHEN the copy operation completes successfully, THE Content_Analysis_Tab SHALL display a brief visual confirmation message near the button for 2 seconds.

### Requirement 2: Content Analysis Download Button

**User Story:** As a technical writer, I want to download the analyzed content from the Content Analysis tab, so that I can save the results as a file for offline review.

#### Acceptance Criteria

1. WHEN the Content Analysis results are displayed, THE Content_Analysis_Tab SHALL display a "Download" button adjacent to the Copy button near the Annotated_Text_Section heading.
2. WHEN the user clicks the Download button and fixed text is available, THE Content_Analysis_Tab SHALL trigger a download of the fixed content as a `.docx` file preserving formatting.
3. WHEN the user clicks the Download button and no fixed text is available, THE Content_Analysis_Tab SHALL trigger a download of the annotated text content as a `.txt` file.

### Requirement 3: Move to Doc to DITA Button

**User Story:** As a technical writer, I want to send analyzed content from the Content Analysis tab directly to the DOC to DITA tab, so that I can convert the cleaned content to DITA format without manual copy-paste.

#### Acceptance Criteria

1. WHEN the Content Analysis results are displayed, THE Content_Analysis_Tab SHALL display a "Move to Doc to DITA" button adjacent to the Copy and Download buttons near the Annotated_Text_Section heading.
2. WHEN the user clicks the "Move to Doc to DITA" button, THE DocAI_App SHALL populate the DOC to DITA input textarea with the fixed text content (or annotated plain text if no fixes have been applied).
3. WHEN the user clicks the "Move to Doc to DITA" button, THE DocAI_App SHALL switch the active tab to the DOC to DITA tab.

### Requirement 4: Issues Table Category Filter

**User Story:** As a technical writer, I want to filter the issues list by violation category, so that I can focus on one type of violation at a time during review.

#### Acceptance Criteria

1. WHEN the Content Analysis results are displayed, THE Content_Analysis_Tab SHALL display a row of filter buttons above the Issues_Table, one for each Violation_Category present in the results plus an "All" option.
2. WHEN the user clicks a specific category filter button, THE Issues_Table SHALL display only rows matching the selected Violation_Category.
3. WHEN the user clicks the "All" filter button, THE Issues_Table SHALL display all violation rows regardless of category.
4. THE Content_Analysis_Tab SHALL visually indicate the currently active filter button using a distinct background color or border style.
5. WHEN the filter selection changes, THE Content_Analysis_Tab SHALL update the issue count badge to reflect the number of currently visible issues.

### Requirement 5: Error Summary Panel

**User Story:** As a technical writer, I want a side panel showing violation counts grouped by category, so that I can quickly assess the distribution and severity of issues in my content.

#### Acceptance Criteria

1. WHEN the Content Analysis results are displayed, THE Content_Analysis_Tab SHALL display the Error_Summary_Panel on the right side of the results area.
2. THE Error_Summary_Panel SHALL list each Violation_Category (Grammar, Translation, Style & Tone, Word Usage, Punctuation) with its corresponding violation count, plus a Total row.
3. WHEN the user clicks a category row header in the Error_Summary_Panel, THE Error_Summary_Panel SHALL sort the category list by the clicked column (ascending on first click, descending on second click).
4. WHEN the user clicks a specific category row in the Error_Summary_Panel, THE Issues_Table SHALL filter to show only violations of that category.
5. THE Error_Summary_Panel SHALL use a fixed width and remain visible alongside the main results content without overlapping.

### Requirement 6: Rename Write Tab to Author

**User Story:** As a product owner, I want the "Write" tab to be labeled "Author", so that the tab name better reflects the authoring workflow.

#### Acceptance Criteria

1. THE DocAI_App SHALL display the fourth tab label as "Author" instead of "Write".
2. THE DocAI_App SHALL preserve all existing Author_Tab functionality (toolbar, editor, comments, save, export, send to CA) after the rename.
3. THE DocAI_App SHALL maintain the same internal tab identifier (`rewrite`) to preserve backward compatibility with existing JavaScript functions.

### Requirement 7: Enhanced Word-like Comments System

**User Story:** As a technical writer, I want a Word-like commenting experience in the Author tab, so that I can review and collaborate on content with familiar comment interactions.

#### Acceptance Criteria

1. WHEN the user adds a comment, THE Comments_System SHALL display the comment card in the side panel positioned vertically adjacent to the highlighted text in the editor, similar to Microsoft Word margin comments.
2. WHEN the user hovers over a comment highlight in the editor, THE Comments_System SHALL visually emphasize the corresponding comment card in the side panel using a highlight or border change.
3. WHEN the user hovers over a comment card in the side panel, THE Comments_System SHALL visually emphasize the corresponding highlighted text span in the editor.
4. WHEN the user clicks a comment card in the side panel, THE Comments_System SHALL scroll the editor to bring the highlighted text into view.
5. THE Comments_System SHALL display each comment card with an author label defaulting to "You", a timestamp, the selected text excerpt, the comment body, and action buttons (Reply, Resolve, Delete).
6. WHEN the user clicks Reply on a comment card, THE Comments_System SHALL display a reply input field inline within the comment card rather than opening a separate dialog.
7. WHEN the user resolves a comment, THE Comments_System SHALL apply a strikethrough style to the comment text and reduce the opacity of the comment card and the editor highlight.
8. THE Comments_System SHALL display a comment count indicator on the "All" toolbar button showing the total number of active (unresolved) comments.

### Requirement 8: Cross-Tab Formatting Preservation

**User Story:** As a technical writer, I want content formatted in the Author tab to retain its formatting when analyzed in Content Analysis and copied back, so that I do not lose my Word-like formatting during the review cycle.

#### Acceptance Criteria

1. WHEN the user sends formatted content from the Author_Tab to the Content_Analysis_Tab using the "Analyze" button, THE DocAI_App SHALL preserve the HTML formatting structure in a stored variable for later retrieval.
2. WHEN the user copies the fixed content from the Content_Analysis_Tab after analysis of Author_Tab content, THE Content_Analysis_Tab SHALL produce clipboard content that preserves the original Word-like formatting (bold, italic, underline, font family, font size, headings, lists).
3. WHEN the user downloads the fixed content from the Content_Analysis_Tab after analysis of Author_Tab content, THE Content_Analysis_Tab SHALL produce a `.docx` file that preserves the original Word-like formatting.
4. WHEN the user clicks "Push Back to Write" in the Content_Analysis_Tab, THE DocAI_App SHALL restore the fixed content into the Author_Tab editor preserving the original formatting structure.

### Requirement 9: Highlight Palette Enhancement

**User Story:** As a technical writer, I want the highlight color picker to display a basic 16-color palette grid, so that I can quickly select from a standard set of colors.

#### Acceptance Criteria

1. THE Author_Tab highlight color picker SHALL display the 16 colors defined in WR_PALETTE as a grid of clickable color swatches.
2. WHEN the user clicks a color swatch in the palette, THE Author_Tab SHALL apply that color as the highlight (background) color to the selected text.
3. THE Author_Tab SHALL provide a "None" option in the palette to remove highlight color from selected text.
4. WHEN the user selects a highlight color, THE Author_Tab SHALL update the toolbar highlight button indicator to reflect the currently selected color.
