# Documentation AI Tool

A desktop application for technical writers that provides AI-powered content analysis, standards-compliant drafting, DITA XML conversion, document compliance review, and a full-featured document editor — all working offline in one integrated workspace.

---

## How This Tool Helps Technical Writers

Technical writers spend significant time ensuring content meets Infor Information Development standards, converting documents between formats, and getting AI-assisted feedback on their writing. This tool consolidates those workflows into a single offline desktop application:

- **AI-powered writing assistant** — Chat with a local AI that knows the full Infor ID standards. Ask it to review, rewrite, plan, or explain any documentation standard. Works completely offline using a bundled local model.

- **Write with confidence** — The Content Analysis engine checks your text against 90+ writing rules in real time, catching issues like passive voice, vague modifiers, biased terminology, controlled vocabulary violations, and structural problems before review cycles begin.

- **Convert any format** — Paste documents, upload Word/PDF/PowerPoint/Excel files, or provide URLs to convert content into Markdown or DITA XML. MarkItDown handles dozens of file formats.

- **Compliance scoring** — Quick Review gives you an instant documentation compliance score with breakdown by category (DITA structure, Global English, translation readiness, writing quality) and actionable suggestions.

- **Draft and review in one place** — The Initial Draft editor gives you a lightweight Word-like environment with formatting, comments, and replies. Compose content, annotate it with review comments, and send it directly to analysis.

- **First Draft rewriter** — Paste rough content and get a standards-compliant rewrite with side-by-side comparison showing every change made and which rule triggered it.

- **Works fully offline** — After initial setup, no internet connection is required. The AI model, analysis engine, and all tools run locally on your machine.

---

## Features

### 1. AI Assistant (New)
- Chat interface with a local AI trained on Infor ID writing standards
- Powered by Ollama running locally — no cloud, no data leaves your machine
- Capabilities:
  - Review content for standards compliance
  - Rewrite text in active voice following Infor guidelines
  - Suggest topic types (concept, task, reference) for your content
  - Plan documentation structure and organization
  - Answer questions about any Infor writing standard
- Conversation history within sessions
- "+ New Chat" button for instant conversation reset
- Status indicator showing AI connectivity
- Markdown-formatted responses with code blocks, lists, and headings

### 2. Content Analysis
- Analyzes text against **Infor Writing Standards** with 90+ built-in rules
- Rule categories:
  - **Grammar** — double negatives, subjunctive mood, discontinuous phrasal verbs, missing "that", noun-as-verb, future tense misuse
  - **Word Usage** — comprehensive controlled vocabulary (70+ substitution rules)
  - **Pronouns** — vague pronoun detection, gendered language
  - **Style & Tone** — politeness markers, biased/violent terminology, spatial references, inclusive language
  - **Punctuation** — semicolons, em dashes, contractions, double spaces, missing commas
  - **Numbers** — spell out small numbers, ordinals, approximations
  - **Translation** — ambiguous modals ("may", "since", "while", "once"), vague antecedents
  - **UI Conventions** — "click on" vs "click", "press" vs "hit", "select" vs "check"
- Inline fix popup (Grammarly-style) with:
  - Multiple suggested replacements as clickable pills
  - Custom replacement text input
  - Accept / Ignore actions per violation
- Global undo/redo (Ctrl+Z / Ctrl+Y) for all fixes
- Color-coded violation highlights with legend (Remove, Replace, Review, Structure)
- Docked issues panel with category filtering
- Export results as text, copy to clipboard, or send to DITA converter
- Upload `.txt` or `.docx` files for analysis

### 3. DOC to DITA Converter
- Convert rich text or plain content into DITA XML format
- Supports **Concept** and **Task** topic types
- Paste from Word/Google Docs with formatting preserved
- Upload `.docx`, `.html`, or `.txt` files directly
- One-click copy or download of generated XML

### 4. Initial Draft Editor (Lightweight Word Processor)
- Rich text editing with a full toolbar:
  - Font family and size selection
  - Bold, Italic, Underline, Strikethrough
  - Text and highlight color pickers
  - Paragraph alignment (left, center, right, justify)
  - Bullet and numbered lists with indent control
  - Table insertion with configurable rows/columns
  - Horizontal rule and hyperlink insertion
  - Heading styles (H1–H4, Normal, Monospace)
- Find & Replace functionality
- Word, character, and paragraph count in status bar
- **Comments system** (Microsoft Word-style):
  - Select text and add inline comments via toolbar
  - Comments panel with threaded replies
  - Bidirectional navigation (click highlight → scroll to card, and vice versa)
  - Hover interaction between highlights and cards
  - Comments persist across sessions (localStorage)
  - Orphaned comment detection when text changes
- File operations:
  - New, Open (.txt/.docx), Save as .docx, Save as .txt, Print
  - Filename auto-derived from document heading
- Document title shown in window title bar
- Send content directly to Content Analysis tab
- Keyboard shortcuts: Ctrl+S (save), Ctrl+F (find), Ctrl+B/I/U (format)

### 5. MarkItDown — Universal File Converter
- Convert files or URLs to Markdown format
- Supported input formats:
  - Documents: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx)
  - Web: HTML pages, URLs, RSS feeds, YouTube
  - Media: Images (with OCR), Audio (with transcription)
  - Other: EPUB, Outlook messages, Jupyter notebooks, CSV, JSON, XML
- Drag-and-drop file upload
- Raw Markdown and rendered preview toggle
- Copy or download converted Markdown

### 6. Quick Review — Documentation Compliance
- Instant compliance scoring (0–100) with verdict
- Score breakdown by category:
  - Information typing (25%)
  - DITA structure (20%)
  - Global English (15%)
  - Translation readiness (15%)
  - Writing quality (10%)
  - Terminology (5%)
  - Reusability (5%)
  - Content efficiency (5%)
- Auto-detects topic type (concept, task, reference) with confidence score
- Violation list with severity levels (critical, major, minor)
- Inline highlights in the input text linked to violation cards
- Suggested changes panel with Accept/Dismiss per suggestion
- Translation risks and reuse opportunities identification

### 7. First Draft — Standards Rewriter
- Paste rough content and generate a standards-compliant rewrite
- Side-by-side comparison with highlighted changes (deletions in red, insertions in green)
- Detailed change log showing each rule that was applied
- Upload .docx or .txt files as input
- Copy or download the rewritten output

### 8. Impact Analyzer (JIRA + DITA Map)
- Upload JIRA export (Excel) and DITA map output (ZIP of HTML topics)
- Auto-detects column mappings in JIRA exports
- Classifies topics into "Create" and "Update" categories
- Configurable match sensitivity (Strict, Normal, Loose)
- Export results as CSV

---

## Quick Start (3 Steps)

**Prerequisites:** Windows 10/11, [Python 3.10+](https://python.org), [Node.js 18+](https://nodejs.org)

```batch
1. Double-click  setup.bat
2. Wait for it to finish (downloads ~2GB AI model on first run)
3. Run:  npm start
```

That's it. The app launches with full offline AI capability.

See [SETUP.md](SETUP.md) for detailed instructions, building distributables, and troubleshooting.

---

## Installation (Manual)

1. **Clone the repository**
   ```bash
   git clone https://github.com/tandavinci/Doc-tool.git
   cd Doc-tool
   git checkout DOC2DITA
   ```

2. **Install Ollama** (for AI Assistant)
   - Download from [ollama.com](https://ollama.com/download)
   - Pull the model: `ollama pull llama3.2:latest`

3. **Install dependencies**
   ```bash
   pip install "markitdown[all]" openai
   npm install
   ```

4. **Run the application**
   ```bash
   npm start
   ```

---

## Building a Standalone Distributable

To create an installer that works on any Windows PC without Python, Node.js, or internet:

```batch
build-all.bat
```

Output in `dist/`:
- `Content Analysis Setup *.exe` — Standard installer
- `Content Analysis-Portable-*.exe` — Portable (no install needed)

The package bundles everything: app, Python backend, Ollama, and the AI model.

---

## Project Structure

```
Doc-AI-Analyst/
├── electron/
│   ├── main.js            # Electron main process, Ollama management, IPC routing
│   └── preload.js         # Context bridge (secure renderer-to-main API)
├── frontend/
│   ├── index.html         # Application UI (7 tabs + AI Assistant)
│   ├── app.js             # Frontend logic (DOM, events, rendering, AI chat)
│   ├── styles.css         # Application styles
│   └── lib/               # Bundled libraries (mammoth, docx, FileSaver, xlsx, jszip)
├── backend/
│   ├── protocol.py        # JSON-over-stdin/stdout IPC message loop
│   ├── analyzer.py        # Content analysis orchestration
│   ├── rules.py           # Writing rules and violations
│   ├── utils.py           # Shared utilities (tokenization, XML generation)
│   ├── ai_assistant.py    # AI chat engine (Ollama/OpenAI-compatible API)
│   ├── review_engine.py   # Quick Review compliance scoring
│   ├── first_draft_engine.py  # Standards-based rewriting engine
│   ├── dita_converter.py  # DITA XML generation
│   └── markitdown_handler.py  # File/URL to Markdown conversion
├── setup.bat              # One-click setup (installs Ollama, model, deps)
├── build-all.bat          # Build standalone offline distributable
├── backend.spec           # PyInstaller config for backend bundling
├── package.json           # Node.js + electron-builder config
├── SETUP.md              # Detailed setup and troubleshooting guide
└── README.md             # This file
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Electron Shell                   │
│  (Window management, IPC routing, Ollama mgmt)   │
├─────────────────────┬───────────────────────────┤
│   Frontend (UI)     │      Backend (Python)      │
│                     │                            │
│  • HTML/CSS/JS      │  • Content Analysis        │
│  • 8 feature tabs   │  • DITA Conversion         │
│  • AI Chat UI       │  • Quick Review            │
│  • Editor + Comments│  • First Draft Engine      │
│  • Results display  │  • MarkItDown              │
│                     │  • AI Assistant (Ollama)    │
└─────────────────────┴───────────────────────────┘
         ↕ Electron IPC (JSON protocol)
```

- **Electron Shell** — Creates the desktop window, spawns Python backend, auto-starts Ollama, routes IPC
- **Frontend** — Handles all UI rendering, user interaction, and display (no business logic)
- **Backend** — All analysis logic, rule evaluation, AI chat, file conversion, compliance scoring
- **Ollama** — Local LLM server bundled with the app for offline AI Assistant

---

## Offline Capability

After running `setup.bat` once (requires internet for initial download):

| Feature | Offline? | Notes |
|---------|----------|-------|
| Content Analysis | Yes | All rules run locally in Python |
| AI Assistant | Yes | Uses bundled Ollama + local model |
| DOC to DITA | Yes | Conversion logic is local |
| Initial Draft Editor | Yes | Fully client-side |
| MarkItDown (files) | Yes | File conversion is local |
| MarkItDown (URLs) | No | Requires internet to fetch the URL |
| Quick Review | Yes | Scoring engine runs locally |
| First Draft | Yes | Rewrite rules are local |
| Impact Analyzer | Yes | Local similarity matching |

---

## Configuration

The AI model can be changed via environment variable:

```batch
set OLLAMA_MODEL=llama3.2:latest
npm start
```

For better quality (requires more RAM):
```batch
ollama pull llama3.1:8b
set OLLAMA_MODEL=llama3.1:8b
npm start
```

---

## Usage Tips

- **AI Assistant**: Ask it to review a paragraph, suggest a topic type, or rewrite content. It knows all Infor ID standards.
- **Content Analysis**: Paste content and click highlights for inline fixes. Use Ctrl+Z to undo any fix.
- **Quick Review**: Get an instant compliance score before submitting content for formal review.
- **First Draft**: Paste rough notes and get a standards-compliant version with tracked changes.
- **Initial Draft**: Compose content with comments, then click "Analyze" to send it to Content Analysis.
- **MarkItDown**: Drop any file (PDF, Word, PowerPoint, etc.) to convert it to editable Markdown.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Desktop shell | Electron 31.x |
| Frontend | HTML/CSS/JavaScript (vanilla) |
| Backend | Python 3.10+ |
| AI Engine | Ollama (local LLM) |
| AI Model | llama3.2:latest (3B parameters) |
| File conversion | MarkItDown |
| Build/Package | electron-builder, PyInstaller |

---

## License

UNLICENSED — Private application.
