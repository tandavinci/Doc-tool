# Documentation AI Tool

A desktop application for technical writers that provides content analysis, DITA XML conversion, impact analysis, and a lightweight document editor — all in one integrated workspace.

---

## How This Tool Helps Technical Writers

Technical writers spend significant time ensuring their content meets organizational writing standards, converting documents between formats, and tracking which topics need updates when requirements change. This tool consolidates those workflows into a single desktop application:

- **Write with confidence** — The Content Analysis engine checks your text against 60+ writing rules in real time, catching issues like passive voice, vague modifiers, biased terminology, and non-standard word usage before review cycles begin.

- **Convert faster** — Instead of manually structuring DITA XML, paste your content and generate valid Concept or Task topics instantly. This eliminates repetitive markup work and reduces formatting errors.

- **Draft and review in one place** — The Initial Draft editor gives you a lightweight Word-like environment with formatting, comments, and replies. You can compose content, annotate it with review comments, and send it directly to the analysis engine without switching tools.

- **Collaborate through comments** — The Word-style commenting system lets you select text, add annotations, and have threaded reply conversations. Comments persist across sessions so review context is never lost.

The goal is to reduce context-switching, catch quality issues early, and let writers focus on content rather than tooling.

---

## Features

### 1. DOC to DITA Converter
- Convert plain text or pasted document content into DITA XML format
- Supports **Concept** and **Task** topic types
- One-click copy of generated XML to clipboard
- Automatic XML escaping and structure generation

### 2. Content Analysis
- Analyzes text against **Infor Writing Standards** with 60+ built-in rules
- Rule categories include:
  - **Grammar** — double negatives, subjunctive mood, discontinuous phrasal verbs, missing "that"
  - **Word Usage** — controlled vocabulary enforcement (e.g., "utilize" → "use", "login" → "sign in")
  - **Pronouns** — vague pronoun detection, gendered language
  - **Style & Tone** — politeness markers, biased/violent terminology, spatial references
  - **Structure** — passive voice, sentence length, future tense
- Inline fix popup (Grammarly-style) with:
  - Suggested replacements shown as clickable pills
  - Custom replacement text input
  - Accept / Ignore actions per violation
- Color-coded violation highlights with legend (Remove, Replace, Review, Structure)
- Docked issues panel with filtering by category
- "Apply All Auto-fixes" for batch corrections
- Export results as text or copy to clipboard
- Send fixed content directly to the DITA converter
- Upload `.txt` or `.docx` files for analysis

### 3. Initial Draft Editor (Lightweight Word Processor)
- Rich text editing with a familiar toolbar:
  - Font family and size selection
  - Bold, Italic, Underline, Strikethrough
  - Text and highlight color pickers
  - Paragraph alignment (left, center, right, justify)
  - Bullet and numbered lists with indent control
  - Table insertion with configurable rows/columns
  - Horizontal rule and hyperlink insertion
  - Heading styles (H1–H4, Normal, Monospace)
- Find & Replace functionality
- Undo / Redo support
- Word, character, and paragraph count in status bar
- **Comments system** (Microsoft Word-style):
  - Select text and add comments via toolbar button
  - Comments panel with threaded replies
  - Click highlights to navigate to comments
  - Comments persist across sessions (localStorage)
- File operations:
  - New document
  - Open `.txt` or `.docx` files
  - Save as `.docx` (Word) or `.txt`
  - Print support
- Send content directly to Content Analysis tab for review

---

## Prerequisites

### System Requirements
- **Operating System**: Windows 10 or later (64-bit)
- **Node.js**: v18.0.0 or later
- **Python**: 3.8 or later (must be available as `python` on PATH)
- **npm**: Comes bundled with Node.js

### Software Dependencies

| Component | Requirement | Purpose |
|-----------|-------------|---------|
| Node.js | >= 18.x | Electron runtime |
| Python | >= 3.8 | Backend analysis engine |
| npm | >= 9.x | Package management |

### Python Dependencies
The backend uses **Python standard library only** — no additional pip packages are required.

### Frontend Libraries (included in `frontend/lib/`)
These are bundled with the application and do not require separate installation:
- **mammoth.js** — DOCX to HTML conversion
- **docx.js** — DOCX file generation (Save as Word)
- **FileSaver.js** — Client-side file downloads
- **JSZip** — ZIP file reading (for DITA map uploads)
- **SheetJS (xlsx)** — Excel file parsing (for JIRA exports)

---

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/tandavinci/Doc-tool.git
   cd Doc-tool
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

3. **Verify Python is available**
   ```bash
   python --version
   ```
   Ensure it reports Python 3.8 or later.

4. **Run the application**
   ```bash
   npm start
   ```

   For development mode with debug logging:
   ```bash
   npm run dev
   ```

---

## Project Structure

```
├── electron/
│   ├── main.js          # Electron main process, window management, IPC
│   └── preload.js       # Context bridge for secure renderer-to-main communication
├── frontend/
│   ├── index.html       # Application UI layout
│   ├── app.js           # Frontend logic (DOM, events, rendering)
│   ├── styles.css       # Application styles
│   └── lib/             # Bundled third-party libraries
├── backend/
│   ├── protocol.py      # JSON-over-stdin/stdout IPC protocol handler
│   ├── analyzer.py      # Core analysis orchestration
│   ├── rules.py         # Content analysis and rewrite rule definitions
│   └── utils.py         # Shared utilities (tokenization, XML generation)
├── package.json         # Node.js project configuration
└── README.md            # This file
```

---

## Architecture

The application follows a clean separation of concerns:

- **Electron Shell** — Creates the desktop window, spawns the Python backend, and routes IPC messages between frontend and backend
- **Frontend (HTML/CSS/JS)** — Handles all UI rendering, user interaction, and display logic
- **Backend (Python)** — Handles content analysis, rule evaluation, DITA conversion, and impact analysis logic

Communication between frontend and backend uses **Electron IPC** with a JSON-over-stdin/stdout protocol to the Python process.

---

## Usage Tips

- **Content Analysis**: Paste or upload your content, click "Analyze Content", then click any colored highlight to see fix suggestions inline
- **DITA Conversion**: Paste structured text (use numbered lines for task steps) and choose Concept or Task format
- **Impact Analysis**: Export your JIRA backlog as Excel, export your DITA map as a ZIP of HTML files, upload both, and run the analysis
- **Initial Draft**: Use as a lightweight editor to compose content, then send it directly to Content Analysis for review

---

## License

UNLICENSED — Private application.
