# Documentation AI Tool — Architecture Document

## Executive Summary

The Documentation AI Tool is an offline-first desktop application designed for Infor Information Development teams. It consolidates documentation authoring, compliance review, AI-assisted editing, format conversion, and impact analysis into a single integrated workspace — eliminating context-switching across multiple tools and catching quality issues before review cycles.

**Key differentiator:** Fully offline AI-powered documentation assistant running on local hardware with no cloud dependency, no data leakage, and zero recurring costs.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    Electron Shell (v31.x)                       │  │
│  │  • BrowserWindow (Chromium renderer)                           │  │
│  │  • IPC message routing (main ↔ renderer)                       │  │
│  │  • Ollama process lifecycle management                         │  │
│  │  • Python backend process management                           │  │
│  │  • Window state, close confirmation, title bar                 │  │
│  └──────────────────┬─────────────────────┬───────────────────────┘  │
│                     │                     │                           │
│  ┌──────────────────▼──────────────┐  ┌──▼────────────────────────┐  │
│  │     Frontend (Renderer)         │  │     Preload Bridge         │  │
│  │                                 │  │                            │  │
│  │  • HTML/CSS/JavaScript          │  │  • contextBridge API       │  │
│  │  • 7 Feature Tabs               │  │  • IPC channel exposure    │  │
│  │  • AI Chat Interface            │  │  • Security isolation      │  │
│  │  • Document Editor (WYSIWYG)    │  │                            │  │
│  │  • Results visualization        │  └────────────────────────────┘  │
│  └──────────────────┬──────────────┘                                  │
└─────────────────────│────────────────────────────────────────────────┘
                      │ Electron IPC (invoke/send)
┌─────────────────────│────────────────────────────────────────────────┐
│                     ▼                                                 │
│                   BACKEND LAYER (Python 3.10+)                        │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                 protocol.py (Message Router)                     │ │
│  │         stdin/stdout JSON-line protocol                          │ │
│  │         Request → Action Handler → Response                      │ │
│  └───┬────────┬────────┬────────┬────────┬────────┬───────────────┘ │
│      │        │        │        │        │        │                  │
│  ┌───▼──┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼────────────┐   │
│  │analyz│ │review│ │dita_ │ │markit│ │doc_  │ │ai_assistant.py│   │
│  │er.py │ │_engi │ │conve │ │down_ │ │impac │ │               │   │
│  │      │ │ne.py │ │rter  │ │handl │ │t.py  │ │  OpenAI SDK   │   │
│  │rules │ │first_│ │.py   │ │er.py │ │      │ │  → Ollama API │   │
│  │.py   │ │draft_│ │      │ │      │ │      │ │               │   │
│  │utils │ │engin │ │      │ │      │ │      │ └───────┬───────┘   │
│  │.py   │ │e.py  │ │      │ │      │ │      │         │           │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘         │           │
│                                                         │           │
└─────────────────────────────────────────────────────────│───────────┘
                                                          │
┌─────────────────────────────────────────────────────────│───────────┐
│                    AI INFERENCE LAYER                     │           │
│                                                          ▼           │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                     Ollama Server (Local)                        │ │
│  │                                                                  │ │
│  │  • llama3.2:latest (3B parameters, default)                     │ │
│  │  • OpenAI-compatible REST API (localhost:11434)                  │ │
│  │  • Auto-started by Electron on app launch                       │ │
│  │  • Model cached in memory after first load                      │ │
│  │  • No internet required after initial model pull                │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### Frontend Layer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI Framework | Vanilla HTML/CSS/JS | Lightweight, no build step, instant load |
| Document Editor | contenteditable + execCommand | WYSIWYG with Word-like toolbar |
| File Operations | mammoth.js, docx.js, FileSaver.js | .docx import/export |
| Spreadsheet Parsing | SheetJS (xlsx.js) | JIRA Excel import |
| Archive Handling | JSZip | DITA map ZIP extraction |

### Backend Layer

| Module | Responsibility | Lines |
|--------|---------------|-------|
| `protocol.py` | stdin/stdout JSON IPC message loop, action routing | ~320 |
| `analyzer.py` | Content analysis orchestration, violation collection | ~200 |
| `rules.py` | 90+ writing rule definitions (regex patterns) | ~400 |
| `review_engine.py` | Compliance scoring (8 categories), First Draft integration | ~800 |
| `first_draft_engine.py` | Standards-based text rewriting with change tracking | ~250 |
| `ai_assistant.py` | LLM chat via Ollama OpenAI-compatible API | ~330 |
| `dita_converter.py` | DITA XML generation (concept/task) | ~150 |
| `markitdown_handler.py` | Universal file/URL → Markdown conversion | ~100 |
| `doc_impact.py` | Documentation impact assessment from Jira validation data | ~450 |
| `jira_analyst.py` | Jira ticket analysis and documentation readiness | ~300 |
| `jira_handler.py` | Jira data handling and field extraction | ~200 |
| `jira_summarizer.py` | Ticket summarization for documentation planning | ~250 |
| `neoscribe_engine.py` | Advanced documentation generation | ~300 |
| `utils.py` | Shared utilities (tokenization, XML escaping) | ~50 |

### AI Inference Layer

| Property | Value |
|----------|-------|
| Engine | Ollama (local) |
| Default Model | llama3.2:latest (3B parameters) |
| API | OpenAI-compatible (localhost:11434/v1) |
| Connection | Python `openai` SDK pointing to local Ollama |
| Prompt Size | ~1K tokens (optimized for speed) |
| Response Time | 4-5s warm / 60s cold start |
| Memory Usage | ~4GB RAM for model |

---

## Data Flow

### Content Analysis Flow
```
User pastes text → Frontend sends via IPC → protocol.py → analyzer.py
  → rules.py (90+ regex patterns) → collectViolations() → sort/deduplicate
  → JSON response with violations[] → Frontend renders inline highlights
```

### AI Chat Flow
```
User types message → Frontend sends via IPC → protocol.py → ai_assistant.py
  → Build messages (system prompt + history + user message + context)
  → OpenAI SDK → Ollama REST API → LLM inference (local GPU/CPU)
  → Response text → Frontend renders as Markdown bubble
```

### Quick Review Flow
```
User pastes text → Frontend sends via IPC → protocol.py → review_engine.py
  → classify_topic() → _check_* (8 rule sets) → _compute_score()
  → first_draft_engine.generate_first_draft() → rewritten text + changes
  → JSON response → Frontend renders score card + violations + rewrite
```

### Doc Impact Flow
```
User drops JSON files → Frontend parses → sends array via IPC
  → protocol.py → doc_impact.analyze_session()
  → parse_validation_json() for each ticket
  → _identify_impacted_areas() (keyword matching against 8 categories)
  → _compute_ticket_severity() → _generate_recommendations()
  → JSON response → Frontend renders dashboard (stats, areas, timeline)
```

---

## Communication Protocol

The backend uses a **JSON-line protocol over stdin/stdout**:

```
Request:  {"id": "req-0001", "action": "analyze", "payload": {"text": "..."}}
Response: {"id": "req-0001", "success": true, "data": {...}}
Error:    {"id": "req-0001", "success": false, "error": {"code": "...", "message": "..."}}
```

| Action | Handler | Timeout |
|--------|---------|---------|
| `analyze` | Content Analysis | 30s |
| `rewrite` | Rewrite Engine | 30s |
| `convert_dita` | DITA Conversion | 30s |
| `quick_review` | Compliance Review + Rewrite | 30s |
| `markitdown` | File/URL Conversion | 120s |
| `doc_impact` | Documentation Impact Assessment | 30s |
| `ai_chat` | AI Assistant (LLM) | 300s |
| `ai_status` | Ollama Connectivity Check | 30s |
| `ai_clear` | Clear Chat History | 30s |

---

## Security & Privacy

| Aspect | Implementation |
|--------|---------------|
| Data residency | All data stays on local machine — never transmitted externally |
| AI model | Runs locally via Ollama — no cloud API calls |
| Context isolation | Electron contextBridge — no direct Node.js access from renderer |
| Network access | Only localhost:11434 (Ollama). No external connections after setup. |
| Credential storage | No credentials stored. Doc Impact works from imported files. |
| Process isolation | Python backend sandboxed via stdin/stdout — no filesystem access from renderer |

---

## Deployment Architecture

### Development Mode
```
npm start → Electron → spawns Python (protocol.py) → connects to system Ollama
```

### Production (Standalone Package)
```
build-all.bat → PyInstaller (backend.exe) + electron-builder (installer)
  + bundled Ollama + bundled AI model
  = Single .exe installer, no dependencies needed on target machine
```

### Distribution
```
Installer:  dist/Content Analysis Setup *.exe  (~2.5GB with model)
Portable:   dist/Content Analysis-Portable-*.exe
```

Target machine requirements: Windows 10/11 64-bit, 8GB RAM. No Python, Node.js, or internet needed.

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| App startup | ~3s (Electron + Python backend) |
| Content Analysis (500 words) | <100ms |
| Quick Review (500 words) | <200ms |
| DITA Conversion | <50ms |
| MarkItDown (10MB PDF) | 5-15s |
| AI Chat (warm) | 4-5s |
| AI Chat (cold start) | ~60s (model loading) |
| Doc Impact (50 tickets) | <500ms |

---

## Technology Stack

| Layer | Technology | Version | License |
|-------|-----------|---------|---------|
| Desktop Shell | Electron | 31.x | MIT |
| Frontend | HTML/CSS/JavaScript | ES6 | — |
| Backend | Python | 3.10+ | PSF |
| AI Engine | Ollama | Latest | MIT |
| AI Model | Llama 3.2 | 3B | Meta Llama 3 Community |
| File Conversion | MarkItDown | Latest | MIT |
| DOCX I/O | mammoth.js / docx.js | Latest | MIT/BSD |
| Build (Python) | PyInstaller | Latest | GPL (build tool only) |
| Build (Electron) | electron-builder | 25.x | MIT |
| Vector DB (future) | ChromaDB | — | Apache 2.0 |

---

## Feature Matrix

| Feature | Status | Backend Module | Offline |
|---------|--------|---------------|---------|
| Content Analysis (90+ rules) | ✅ Live | analyzer.py, rules.py | Yes |
| DOC to DITA Conversion | ✅ Live | dita_converter.py | Yes |
| Initial Draft Editor | ✅ Live | (frontend only) | Yes |
| Word-style Comments | ✅ Live | (frontend only) | Yes |
| MarkItDown (file conversion) | ✅ Live | markitdown_handler.py | Yes* |
| Quick Review + Rewrite | ✅ Live | review_engine.py, first_draft_engine.py | Yes |
| AI Assistant (22 capabilities) | ✅ Live | ai_assistant.py | Yes |
| Doc Impact Assessment | ✅ Live | doc_impact.py | Yes |
| Jira Analysis & Summarization | ✅ Live | jira_analyst.py, jira_summarizer.py | Yes |
| NeoScribe Engine | ✅ Live | neoscribe_engine.py | Yes |
| RAG (vector search) | 🔮 Planned | — | Yes |
| Streaming AI responses | 🔮 Planned | — | Yes |
| Dark mode | 🔮 Planned | — | Yes |

*MarkItDown URL mode requires internet to fetch the URL content.

---

## Scaling Considerations

| Dimension | Current | Growth Path |
|-----------|---------|-------------|
| Users | Single user (desktop app) | Multi-user via shared server deployment |
| AI Model | 3B (CPU/RAM) | 8B-70B with GPU acceleration |
| Document Store | Local files | RAG with ChromaDB vector indexing |
| Rules | 90+ hardcoded | Config-driven, hot-reloadable |
| Products | All Infor products | Pluggable product-specific rule packs |
