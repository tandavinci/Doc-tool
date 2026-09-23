# Documentation AI Tool
# Documentation AI Tool

A desktop application for technical writers that provides AI-powered content analysis, standards-compliant drafting, DITA XML conversion, document compliance review, JIRA analysis, and a full-featured document editor — all working offline in one integrated workspace.

> **Branch `Sept26`** — this build includes the latest DOC to DITA converter improvements (field lists, definition lists, code blocks, note handling, casing preservation) and ships as a ready-to-run packaged Windows app that needs no Python, Node.js, Ollama install, or internet.

---

## Download & Run the Packaged App (No Install Needed)

The easiest way to use the tool is the packaged Windows build. It bundles the app, the Python backend, Ollama, and the AI model — nothing else to install.

1. Get the distributable: **`dist/Documentation-AI-Tool-Sept26-Windows-x64.zip`** (~3.8 GB).
2. Right-click the zip → **Extract All** to a folder (for example `C:\DocAITool`).
3. Open the extracted folder and double-click **`Content Analysis.exe`**.
4. On first launch the app starts the bundled Ollama server automatically. The DITA converter, analysis, review, and editor features work immediately; the AI Assistant is ready once Ollama finishes loading the model (a few seconds).

That's it — no Python, Node.js, separate Ollama install, or internet connection required.

> Windows SmartScreen may warn about an unsigned app the first time. Choose **More info → Run anyway**. The build is unsigned by design (internal tool).

---

## How This Tool Helps Technical Writers

Technical writers spend significant time ensuring content meets Infor Information Development standards, converting documents between formats, and getting AI-assisted feedback on their writing. This tool consolidates those workflows into a single offline desktop application:

- **AI-powered writing assistant** — Chat with a local AI that knows the full Infor ID standards. Ask it to review, rewrite, plan, or explain any documentation standard. Works completely offline using a bundled local model.

- **Write with confidence** — The Content Analysis engine checks your text against 90+ writing rules in real time, catching issues like passive voice, vague modifiers, biased terminology, controlled vocabulary violations, and structural problems before review cycles begin.

- **Convert any format** — Paste documents, upload Word/PDF/PowerPoint/Excel files, or provide URLs to convert content into Markdown or DITA XML. MarkItDown handles dozens of file formats.

- **Compliance scoring** — Quick Review gives you an instant documentation compliance score with breakdown by category (DITA structure, Global English, translation readiness, writing quality) and actionable suggestions.

- **Draft and review in one place** — The Initial Draft editor gives you a lightweight Word-like environment with formatting, comments, and replies. Compose content, annotate it with review comments, and send it directly to analysis.

- **Standards rewriter** — Inside Quick Review, paste rough content and get a standards-compliant rewrite with side-by-side comparison showing every change made and which rule triggered it.

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
- Paste from Word/Google Docs with formatting preserved, or upload `.docx`, `.html`, or `.txt`
- Structure detection built for real-world Word/Docs paste:
  - **Field lists / definition lists** — bulleted and numbered field/description pairs become `<dl>/<dlentry>/<dt>/<dd>` (concept) or `<fieldlist>/<field>/<fieldname>/<fielddesc>` (task), with nested value bullets rendered as `<ul>`
  - **Steps** — numbered, lettered, tab-separated, and bold list markers are all recognized as `<step>`s (the marker is never mistaken for a UI control)
  - **Code** — pasted XML/code blocks become `<codeblock>`; inline code becomes `<codeph>`, with angle brackets and ampersands safely escaped
  - **Notes** — any inline `Note:` (or Warning/Caution/etc.) is emitted as a `<note>`
  - **UI elements** — CamelCase identifiers (for example `FTSFMachineRunning`) are tagged as `<uicontrol>`; file paths and filenames are left untouched
  - **Faithful text** — original casing is preserved (headings are not force-uppercased) and sentences are never split mid-phrase for tagging
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

### 7. Doc Impact
- Import validation-session JSON files (no credentials required)
- Dashboard view of documentation impact across imported items
- Export results as CSV

### 8. JIRA Dashboard
- Fetch and review JIRA issues, with AI-assisted summaries and documentation-impact analysis
- **Quick Mode** toggle uses fast rule-based analysis (no LLM) for instant results
- AI mode (when Ollama is available) provides richer summaries and missing-field detection
- Requires JIRA credentials for live fetch; Quick Mode works on imported issue data

> A standards-based **rewriter** (paste rough content, get a compliant rewrite with tracked changes) is available inside **Quick Review**.

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

The build bundles everything — app, Python backend, Ollama, and the ~2 GB AI model — into a fully offline package. Because that payload is ~5 GB, the recommended shareable form is a **packaged folder zipped for distribution** (a single NSIS installer can't memory-map a payload that large).

**Prerequisites (build machine only):** Python 3.10+, Node.js 18+, Ollama with the `llama3.2:latest` model pulled.

Steps performed for the `Sept26` build:

```powershell
# 1. Rebuild the Python backend into backend.exe
py -m PyInstaller --distpath ./backend-dist --workpath ./build-backend --clean --noconfirm backend.spec

# 2. Bundle Ollama + model into ollama-bundle/
#    (ollama.exe, lib/, and %USERPROFILE%\.ollama\models  ->  ollama-bundle\)

# 3. Package the app into an unpacked folder (no size limit)
npx electron-builder --dir            # produces dist\win-unpacked\

# 4. Zip the folder for sharing
Compress-Archive -Path dist\win-unpacked\* `
  -DestinationPath dist\Documentation-AI-Tool-Sept26-Windows-x64.zip
```

Output in `dist/`:
- `win-unpacked/` — the runnable app folder (double-click `Content Analysis.exe`)
- `Documentation-AI-Tool-Sept26-Windows-x64.zip` — the shareable single-file distributable (~3.8 GB)

**Lighter build (no bundled AI model, ~150 MB):** delete or empty `ollama-bundle/` before step 3. Every feature still works offline except the AI Assistant / JIRA-AI, which then need Ollama installed separately (`ollama pull llama3.2:latest`). With a small payload, the standard installer works too:

```batch
npm run dist          :: NSIS installer + portable exe in dist\
```

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
│   ├── review_engine.py   # Quick Review compliance scoring + rewriter
│   ├── first_draft_engine.py  # Standards-based rewriting engine
│   ├── dita_converter.py  # DITA XML generation (concept + task)
│   ├── doc_impact.py      # Doc Impact dashboard (imported JSON)
│   ├── jira_handler.py    # JIRA fetch/detail
│   ├── jira_summarizer.py # JIRA AI summaries + doc-impact
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
| Doc Impact | Yes | Works on imported JSON files |
| JIRA Dashboard | Partly | Quick Mode is local; live fetch needs JIRA access |

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
