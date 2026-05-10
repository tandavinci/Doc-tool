# Requirements Document

## Introduction

This document defines the requirements for migrating the Content Analysis desktop application from a monolithic HTML file (DocAI-updated.html) to a modular Electron + Python architecture. The current application is a fully working prototype containing HTML, CSS, and JavaScript in a single file. The migration must preserve all existing UI behavior, styling, and functionality while separating concerns into a frontend (HTML/CSS/JS), a Python backend (content analysis engine), and an Electron shell for desktop integration and IPC communication.

## Deployment Model

- The application will be distributed as a Windows .exe file to teammates.
- Each user runs their own local copy of the application.
- There is no centralized backend and no shared server.
- The application is offline-capable and single-user.

## Backend Process Architecture

**Process model:** Persistent background process
- Electron main process spawns one persistent Python subprocess on application launch.
- The Python process remains running for the lifetime of the application.
- The Python process terminates cleanly on application close.
- No orphan Python processes are permitted.

**Communication mechanism:** stdin/stdout JSON
- Electron main process sends JSON request payloads to the Python subprocess via stdin.
- Python subprocess returns JSON response payloads via stdout.
- Electron main process forwards results to the frontend renderer via Electron IPC.
- Communication is synchronous per-request (one request, one response).

**Not used:**
- FastAPI, Flask, or any HTTP server framework
- localhost HTTP server
- WebSocket
- Subprocess-per-request execution

**Error handling:** Structured JSON error responses
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error",
    "details": "Technical details"
  }
}
```

**Progress reporting:** Deferred unless performance requires it later. Current operations (analysis, rewrite, DITA conversion) are expected to complete quickly for typical document sizes.

## Migration Boundary Principles

The following principles govern what migrates to Python and what remains in frontend JavaScript:

**Migrates to Python backend (business logic only):**
- Content analysis rule definitions and evaluation
- Scoring logic
- Content transformation logic (rewrite rules)
- XML generation for DITA conversion
- Similarity comparison for impact analysis

**Remains in frontend JavaScript (UI behavior):**
- Tab switching
- DOM updates and rendering
- Editor interactions (formatting, find/replace, cursor management)
- Loading states and progress indicators
- Rendering analysis results (highlights, badges, tables, popups)
- File upload UI handling and user feedback
- Event listeners and user interaction handlers
- Editor file I/O (open/save in Write Editor)
- Frontend library integrations (SheetJS, JSZip, Mammoth, docx.js, FileSaver)

**Library preservation principle:**
- Working frontend libraries (mammoth.js, XLSX/SheetJS, JSZip, docx.js, FileSaver.js) SHALL be preserved as npm dependencies unless migrating a specific library to Python provides a clear, documented functional benefit.
- Do not over-migrate working frontend behavior into backend Python.

**Goal:** Keep the application lightweight, local, maintainable, and preserve existing functionality while improving modularity.

## Glossary

- **Application**: The Content Analysis desktop application for technical writers
- **Monolith**: The current single-file implementation (DocAI-updated.html) containing all HTML, CSS, JavaScript, and embedded libraries
- **Frontend**: The HTML/CSS/JavaScript layer responsible for UI rendering and user interaction (index.html, styles.css, app.js)
- **Backend**: The Python layer responsible for content analysis logic, rule evaluation, and scoring (protocol.py, analyzer.py, rules.py, utils.py)
- **Electron_Shell**: The Electron framework layer providing the desktop window, process management, and IPC bridge (main.js, preload.js)
- **IPC_Bridge**: The Electron Inter-Process Communication mechanism connecting the Frontend to the Backend
- **Content_Analysis_Engine**: The Backend module that evaluates text against writing rules and produces violation reports
- **Rule**: A single writing standard check defined by a pattern, category, message, and optional fix suggestion
- **Violation**: An instance where content matches a Rule pattern, indicating a writing standards issue
- **DITA_Converter**: The application module that converts plain text into DITA XML (concept or task format)
- **Impact_Analyzer**: The application module that compares JIRA items against DITA topic files to determine content creation or update needs
- **Rewrite_Engine**: The application module that automatically applies writing rule fixes to content
- **Write_Editor**: The built-in lightweight word processor with formatting, find/replace, and export capabilities

## Requirements

### Requirement 1: Separation of HTML Structure

**User Story:** As a developer, I want the HTML markup separated into its own file, so that the UI structure is maintainable independently of styles and logic.

#### Acceptance Criteria

1. WHEN the migration is complete, THE Frontend SHALL contain an index.html file with all UI markup currently embedded in the Monolith
2. THE Frontend SHALL preserve the tab-based navigation structure with tabs for DITA Converter, Impact Analyzer, Content Analysis, and Rewrite/Write
3. THE Frontend SHALL preserve all form elements, input fields, file upload controls, and output containers from the Monolith
4. THE Frontend SHALL not contain any inline JavaScript or embedded script libraries

### Requirement 2: Separation of CSS Styles

**User Story:** As a developer, I want all CSS extracted into a dedicated stylesheet, so that visual styling is decoupled from structure and behavior.

#### Acceptance Criteria

1. WHEN the migration is complete, THE Frontend SHALL contain a styles.css file with all CSS rules currently embedded in the Monolith
2. THE Frontend SHALL preserve the visual appearance of all UI components including violation highlights, badges, tabs, buttons, and layout
3. THE Frontend SHALL preserve responsive behavior and interactive states such as hover effects, active tab indicators, and tooltip positioning
4. THE Frontend SHALL not contain any inline style attributes that duplicate stylesheet rules

### Requirement 3: Separation of Frontend JavaScript

**User Story:** As a developer, I want all UI interaction logic extracted into a dedicated JavaScript file, so that frontend behavior is modular and testable.

#### Acceptance Criteria

1. WHEN the migration is complete, THE Frontend SHALL contain an app.js file with all UI interaction logic
2. THE Frontend app.js SHALL handle tab switching, DOM manipulation, event listeners, and display rendering
3. THE Frontend app.js SHALL use event listeners instead of inline onclick handlers
4. THE Frontend app.js SHALL not contain content analysis rules, scoring logic, or rule evaluation algorithms

### Requirement 4: Content Analysis Rule Evaluation in Python

**User Story:** As a developer, I want the content analysis rules and evaluation logic moved to Python, so that the analysis engine is testable, extensible, and separated from the UI.

#### Acceptance Criteria

1. THE Backend rules.py SHALL contain all writing rule definitions currently in the CA_RULES array, preserving rule IDs, categories, patterns, messages, fix suggestions, and color classifications
2. THE Backend analyzer.py SHALL orchestrate content analysis by accepting text input and returning a structured list of Violations with start position, end position, rule ID, category, message, fix suggestion, and matched text
3. WHEN text is submitted for analysis, THE Backend SHALL detect all rule violations in the same order as the current Monolith implementation
4. THE Backend SHALL perform sentence-level checks including sentence length validation (maximum 25 words) and number-at-sentence-start detection
5. THE Backend SHALL resolve overlapping violations by keeping the first match and skipping subsequent overlapping matches

### Requirement 5: File Parsing Stays in Frontend

**User Story:** As a developer, I want .docx and .txt file parsing to remain in the frontend using existing libraries, so that working functionality is not unnecessarily duplicated in the backend.

#### Acceptance Criteria

1. THE Frontend SHALL continue using mammoth.js (as npm dependency) to extract plain text from .docx files for content analysis and rewrite input
2. THE Frontend SHALL read .txt file content directly using the File API
3. THE Backend SHALL NOT implement file parsing or a parse_file action — there is no documented backend-only requirement for this
4. THE Frontend SHALL pass extracted plain text (as a string) to the Backend for analysis or rewriting via the IPC_Bridge

### Requirement 6: Rewrite Engine in Python

**User Story:** As a developer, I want the automatic rewrite logic moved to Python, so that text transformation rules are maintainable alongside analysis rules.

#### Acceptance Criteria

1. THE Backend SHALL contain all rewrite rules currently in the RW_RULES array, preserving pattern matching, replacement values, and change descriptions
2. WHEN text is submitted for rewriting, THE Backend SHALL apply all rewrite rules and return the transformed text along with a list of changes made
3. THE Backend SHALL perform post-processing including double-space removal and space-before-punctuation cleanup
4. THE Backend SHALL detect sentences exceeding 25 words in the rewritten output and return warnings for manual review

### Requirement 7: Electron Shell Integration

**User Story:** As a developer, I want the application wrapped in an Electron shell, so that it runs as a native desktop application with access to system resources.

#### Acceptance Criteria

1. THE Electron_Shell main.js SHALL create and manage the application window with appropriate dimensions and settings
2. THE Electron_Shell main.js SHALL spawn and manage the Python Backend process
3. THE Electron_Shell preload.js SHALL expose a secure IPC_Bridge API to the Frontend using contextBridge
4. WHEN the application window is closed, THE Electron_Shell SHALL terminate the Python Backend process

### Requirement 8: IPC Communication Between Frontend and Backend

**User Story:** As a developer, I want a well-defined IPC communication layer, so that the Frontend and Backend exchange data reliably without direct coupling.

#### Acceptance Criteria

1. THE IPC_Bridge SHALL support sending content analysis requests from the Frontend to the Backend and receiving violation results
2. THE IPC_Bridge SHALL support sending rewrite requests from the Frontend to the Backend and receiving transformed text with change logs
3. THE IPC_Bridge SHALL support sending DITA conversion requests from the Frontend to the Backend and receiving generated XML
4. THE IPC_Bridge SHALL support sending impact analysis requests from the Frontend to the Backend and receiving create/update topic lists
5. IF the Backend process becomes unresponsive, THEN THE Electron_Shell SHALL report an error state to the Frontend

### Requirement 9: Preserve Content Analysis UI Behavior

**User Story:** As a technical writer, I want the content analysis interface to work identically after migration, so that my workflow is not disrupted.

#### Acceptance Criteria

1. WHEN content is analyzed, THE Frontend SHALL display annotated text with color-coded violation highlights matching the current categories (Grammar, Word Usage, Pronouns, Style & Tone, Punctuation, Numbers, Translation, UI Conventions)
2. THE Frontend SHALL display summary badges showing violation counts per category
3. THE Frontend SHALL display a violations table with expandable detail rows showing rule explanation, context sentence, and replacement suggestions
4. WHEN a user clicks a violation highlight, THE Frontend SHALL display a fix popup with alternative suggestions and a custom replacement input
5. WHEN a user applies a fix, THE Frontend SHALL update the text and re-run analysis to reflect the change
6. THE Frontend SHALL support ignoring individual violations
7. THE Frontend SHALL support applying all automatic fixes at once

### Requirement 10: Preserve Impact Analyzer Functionality

**User Story:** As a technical writer, I want the impact analyzer to work identically after migration, so that I can continue matching JIRA items to DITA topics.

#### Acceptance Criteria

1. WHEN a JIRA Excel file is uploaded, THE Application SHALL parse the spreadsheet and auto-detect column mappings for Summary, Description, and Issue Type
2. WHEN a DITA map ZIP file is uploaded, THE Application SHALL extract HTML topic files and parse their titles and body content
3. WHEN impact analysis is run, THE Application SHALL compare JIRA items against DITA topics using Jaccard similarity with configurable sensitivity thresholds (strict: 0.30, normal: 0.18, loose: 0.10)
4. THE Frontend SHALL display results in summary strips, a "Topics to Create" table, and a "Topics to Update" table with match confidence percentages
5. THE Frontend SHALL support exporting results as CSV files

### Requirement 11: Preserve DITA Converter Functionality

**User Story:** As a technical writer, I want the DITA converter to work identically after migration, so that I can continue converting text to DITA XML.

#### Acceptance Criteria

1. WHEN text is submitted for concept conversion, THE Application SHALL generate valid DITA conbody XML with paragraph elements
2. WHEN text is submitted for task conversion, THE Application SHALL generate valid DITA taskbody XML with step elements derived from numbered lines
3. THE Application SHALL properly escape XML special characters in generated output

### Requirement 12: Preserve Rewrite and Write Editor Functionality

**User Story:** As a technical writer, I want the rewrite tool and built-in editor to work identically after migration, so that I can continue editing and exporting documents.

#### Acceptance Criteria

1. WHEN text is submitted for rewriting, THE Frontend SHALL display the rewritten result with bold UI element names, a side-by-side diff view, and a change log
2. THE Frontend SHALL support copying rewritten results to clipboard and downloading as .docx
3. THE Write_Editor SHALL provide text formatting (bold, italic, underline, strikethrough, alignment), paragraph styles (headings, preformatted), font size control, and list insertion
4. THE Write_Editor SHALL support opening .docx and .txt files, saving as .docx and .txt, and printing
5. THE Write_Editor SHALL provide find and replace functionality and table insertion
6. THE Write_Editor SHALL display live word count, character count, and paragraph count

### Requirement 13: File Upload Handling

**User Story:** As a technical writer, I want to upload .docx and .txt files in any tab, so that I can analyze or rewrite content from existing documents.

#### Acceptance Criteria

1. WHEN a .docx file is uploaded in the Content Analysis tab, THE Frontend SHALL extract raw text using mammoth.js and populate the input textarea
2. WHEN a .txt file is uploaded in the Content Analysis tab, THE Frontend SHALL read the file content using the File API and populate the input textarea
3. WHEN a .docx file is uploaded in the Rewrite tab, THE Frontend SHALL extract raw text using mammoth.js and populate the rewrite input textarea
4. WHEN an Excel file is uploaded in the Impact Analyzer tab, THE Frontend SHALL parse the spreadsheet using SheetJS and display column selection options
5. All file parsing for upload handling SHALL remain in the Frontend — no backend parse_file action is required

### Requirement 14: Migration Phase Validation

**User Story:** As a developer, I want each migration phase validated independently, so that regressions are caught before proceeding to the next phase.

#### Acceptance Criteria

1. WHEN Phase 1 (HTML/CSS/JS separation) is complete, THE Application SHALL render identically to the Monolith when opened in a browser
2. WHEN Phase 2 (business logic identification) is complete, THE Application SHALL have documented boundaries between UI logic and analysis logic
3. WHEN Phase 3 (Python backend migration) is complete, THE Backend SHALL produce identical violation results for any given input text compared to the JavaScript implementation
4. WHEN Phase 4 (Electron shell integration) is complete, THE Application SHALL launch as a desktop window and load the Frontend
5. WHEN Phase 5 (frontend-backend connection) is complete, THE Application SHALL perform end-to-end content analysis through the IPC_Bridge with results matching the original Monolith output

### Requirement 15: Folder Structure Compliance

**User Story:** As a developer, I want the final project to follow the prescribed folder structure, so that the codebase is organized and maintainable.

#### Acceptance Criteria

1. THE Application SHALL organize files into four directories: frontend/ (index.html, styles.css, app.js), backend/ (protocol.py, analyzer.py, rules.py, utils.py), electron/ (main.js, preload.js), and assets/ (icons/, templates/)
2. THE Frontend directory SHALL not contain any Python files or Electron process management code
3. THE Backend directory SHALL not contain any HTML, CSS, or JavaScript files
4. THE Electron directory SHALL contain only the main process and preload scripts
5. THE Backend SHALL separate protocol concerns (protocol.py) from business logic (analyzer.py, rules.py, utils.py)

### Requirement 16: Third-Party Library Management

**User Story:** As a developer, I want embedded libraries replaced with proper package dependencies, so that they are versioned and updatable.

#### Acceptance Criteria

1. THE Application SHALL replace the embedded mammoth.js library with a proper npm dependency or equivalent Python library for .docx parsing
2. THE Application SHALL replace the embedded XLSX (SheetJS) library with a proper npm or Python dependency for Excel parsing
3. THE Application SHALL replace the embedded JSZip library with a proper npm or Python dependency for ZIP file handling
4. THE Application SHALL replace the embedded docx.js library with a proper npm dependency for .docx generation
5. THE Application SHALL replace the embedded FileSaver.js (saveAs) with a proper npm dependency or Electron native file dialog
