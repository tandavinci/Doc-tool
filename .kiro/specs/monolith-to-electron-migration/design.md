# Technical Design Document

## 1. Final Folder Structure

```
content-analysis-app/
├── electron/
│   ├── main.js              # Electron main process, window management, Python lifecycle
│   └── preload.js           # Secure IPC bridge via contextBridge
├── frontend/
│   ├── index.html           # UI markup (tabs, forms, containers)
│   ├── styles.css           # All CSS rules extracted from monolith
│   └── app.js              # UI interaction logic, event handlers, rendering
├── backend/
│   ├── protocol.py          # stdin/stdout message loop, JSON parsing, routing, shutdown
│   ├── analyzer.py          # Business logic orchestration (analysis, rewrite, convert, impact)
│   ├── rules.py             # CA_RULES and RW_RULES definitions
│   └── utils.py             # Shared helpers (XML escaping, tokenization, Jaccard)
├── assets/
│   ├── icons/               # Application icons (taskbar, window, installer)
│   └── templates/           # Static resources and templates
├── package.json             # Electron + npm dependencies
├── requirements.txt         # Python dependencies
└── README.md
```

## 2. File Responsibilities

### electron/main.js

**Role:** Application entry point. Manages window lifecycle and Python subprocess.

**Responsibilities:**
- Create BrowserWindow loading `frontend/index.html`
- Spawn persistent Python subprocess (`backend/protocol.py`) on app launch
- Maintain a request queue for stdin/stdout communication with Python
- Register IPC handlers for each approved channel
- Forward frontend IPC requests to Python via stdin
- Parse Python stdout JSON responses and forward to renderer via IPC
- Terminate Python subprocess on window close (SIGTERM, then SIGKILL after timeout)
- Handle Python process crash detection and notify frontend
- Prevent orphan processes on all exit paths (close, crash, force-quit)

### electron/preload.js

**Role:** Secure bridge between renderer and main process.

**Responsibilities:**
- Expose `window.api` object via `contextBridge.exposeInMainWorld`
- Expose only approved async methods:
  - `window.api.analyze(text)` → content analysis
  - `window.api.rewrite(text)` → rewrite transformation
  - `window.api.convertDita(text, format)` → DITA XML generation
  - `window.api.impactAnalyze(jiraItems, ditaTopics, threshold)` → similarity comparison
- No direct Node.js or Electron API exposure to renderer

### frontend/index.html

**Role:** UI structure only.

**Responsibilities:**
- Tab navigation markup (DITA Converter, Impact Analyzer, Content Analysis, Rewrite/Write)
- Form elements, textareas, file inputs, buttons
- Output containers for results display
- Script/stylesheet references
- No inline JavaScript, no embedded libraries

### frontend/styles.css

**Role:** All visual styling.

**Responsibilities:**
- Tab styling and active states
- Violation highlight colors per category
- Badge styling for violation counts
- Editor toolbar and formatting styles
- Responsive layout rules
- Diff view styling (added/removed highlights)
- Loading states and animations
- All hover, focus, and interactive states

### frontend/app.js

**Role:** UI interaction and rendering logic.

**Responsibilities:**
- Tab switching
- Event listener registration (buttons, file inputs, keyboard shortcuts)
- Loading state management (show/hide spinners)
- Call `window.api.*` methods for backend operations
- Render analysis results (annotated text, badges, violations table)
- Render fix popups and handle fix application
- Render rewrite results (diff view, change log)
- Render DITA conversion output
- Render impact analysis results (tables, CSV export)
- Write Editor: formatting commands, find/replace, word count, file open/save
- File upload handling and .docx text extraction (using mammoth.js in frontend)
- Frontend library usage (mammoth.js, SheetJS, JSZip, docx.js, FileSaver)

### backend/protocol.py

**Role:** Process entry point. Handles all stdin/stdout communication and request routing.

**Responsibilities:**
- stdin message loop: read one JSON line per iteration
- JSON parsing and validation of incoming requests
- Route requests to appropriate handler in `analyzer.py` based on `action` field
- Serialize handler responses to JSON and write to stdout (flush after each write)
- Handle `shutdown` action: log event, flush buffers, exit cleanly
- Handle stdin EOF: treat as shutdown signal
- Handle SIGTERM: treat as shutdown signal
- Structured error wrapping: catch exceptions from handlers, return error envelope
- Emit "ready" signal on stdout after initialization
- Lightweight logging (see Logging section below)

### backend/analyzer.py

**Role:** Business logic orchestration only. No I/O, no protocol handling.

**Responsibilities:**
- `analyze(text)` → call rules evaluation, resolve overlaps, return violations list with summary
- `rewrite(text)` → call rewrite engine, return transformed text + changes + sentence warnings
- `convert_dita(text, format)` → call DITA generator, return XML string
- `impact_analyze(jira_items, dita_topics, threshold)` → call similarity comparison, return classified results
- Each function accepts plain Python data and returns plain Python data (dicts/lists)
- No stdin/stdout interaction, no JSON serialization

### backend/rules.py

**Role:** Rule definitions and evaluation engine.

**Responsibilities:**
- `CA_RULES` list: all content analysis rules with id, category, pattern, message, fix, color
- `RW_RULES` list: all rewrite rules with type, pattern, fix, message
- `evaluate_rules(text)` → list of raw violations from regex matching
- `check_sentence_level(text)` → sentence length and number-start violations
- `resolve_overlaps(violations)` → deduplicated, sorted violation list
- `apply_rewrite_rules(text)` → transformed text + change log + sentence warnings

### backend/utils.py

**Role:** Shared utility functions.

**Responsibilities:**
- `xml_escape(text)` → escape &, <, > for DITA output
- `tokenize(text)` → lowercase word tokens (length > 2)
- `jaccard_similarity(tokens_a, tokens_b)` → float similarity score
- `generate_concept_xml(text)` → DITA conbody XML
- `generate_task_xml(text)` → DITA taskbody XML
- `bold_ui_elements(text)` → apply bold formatting to UI element names

### assets/

**Role:** Static resources for the application.

**Contents:**
- `assets/icons/` — application icons for taskbar, window title bar, and installer branding
- `assets/templates/` — any static templates or reference files used by the application

### Backend Logging

**Role:** Lightweight diagnostic logging for the Python backend.

**Implementation:**
- Use Python `logging` module writing to stderr (not stdout — stdout is reserved for protocol)
- Log level configurable via environment variable (default: INFO)
- Log file: `backend.log` in app data directory (optional, for debugging deployed builds)

**Events logged:**

| Event | Level | Example |
|-------|-------|---------|
| Process started | INFO | `Backend process started, ready for requests` |
| Request received | INFO | `Request received: id=req-001, action=analyze` |
| Handler executed | INFO | `Handler completed: id=req-001, action=analyze, duration=45ms` |
| Error in handler | ERROR | `Handler error: id=req-001, action=analyze, code=RULE_ERROR, msg=...` |
| Shutdown requested | INFO | `Shutdown requested, cleaning up` |
| Process exiting | INFO | `Backend process exiting` |

**Constraints:**
- Logging must not write to stdout (would corrupt protocol)
- Logging must not block request processing
- Log output is lightweight — no request/response payloads logged (could be large)

## 3. Communication Flow Diagrams

### 3.1 Content Analysis Flow

```
┌──────────┐     IPC        ┌──────────┐     stdin      ┌──────────┐
│ Frontend │ ──────────────► │ Electron │ ─────────────► │  Python  │
│  app.js  │                 │  main.js │                │ analyzer │
│          │                 │          │                │          │
│ 1. User  │  api.analyze   │ 2. Write │  JSON request  │ 3. Load  │
│    clicks│  (text)         │    to    │  to stdin      │    rules │
│    button│                 │    stdin │                │ 4. Match │
│          │                 │          │                │    regex  │
│          │                 │          │                │ 5. Check │
│          │                 │          │                │    sentences│
│          │                 │          │                │ 6. Resolve│
│ 9. Render│  IPC response   │ 8. Parse │  stdout JSON   │    overlaps│
│    results◄────────────────│    stdout◄─────────────── │ 7. Return│
│    (highlights,            │    JSON  │  response      │    violations│
│     badges,                │          │                │          │
│     table)                 │          │                │          │
└──────────┘                 └──────────┘                └──────────┘
```

### 3.2 DITA Conversion Flow

```
┌──────────┐     IPC        ┌──────────┐     stdin      ┌──────────┐
│ Frontend │ ──────────────► │ Electron │ ─────────────► │  Python  │
│  app.js  │                 │  main.js │                │  utils   │
│          │                 │          │                │          │
│ 1. User  │ api.convertDita│ 2. Write │  JSON request  │ 3. Split │
│    enters │ (text,"concept")│   to    │  to stdin      │    lines │
│    text   │                │   stdin  │                │ 4. Escape│
│           │                │          │                │    XML   │
│ 7. Display│  IPC response  │ 6. Parse │  stdout JSON   │ 5. Build │
│    XML    ◄────────────────│    stdout◄─────────────── │    XML   │
│    output │                │    JSON  │  response      │          │
└──────────┘                 └──────────┘                └──────────┘
```

### 3.3 Impact Analysis Flow

```
┌──────────┐     IPC        ┌──────────┐     stdin      ┌──────────┐
│ Frontend │ ──────────────► │ Electron │ ─────────────► │  Python  │
│  app.js  │                 │  main.js │                │  utils   │
│          │                 │          │                │          │
│ 1. Parse │api.impactAnalyze│ 3. Write │  JSON request  │ 4. Token-│
│   Excel  │(jiraItems,     │    to    │  to stdin      │    ize   │
│   (SheetJS)│ditaTopics,   │    stdin │                │ 5. Jaccard│
│ 2. Parse │ threshold)     │          │                │    compare│
│   ZIP    │                 │          │                │ 6. Classify│
│   (JSZip)│                 │          │                │    create/│
│          │                 │          │                │    update │
│ 9. Render│  IPC response   │ 8. Parse │  stdout JSON   │ 7. Return│
│    tables◄────────────────│    stdout◄─────────────── │    results│
│    + CSV  │                │    JSON  │  response      │          │
└──────────┘                 └──────────┘                └──────────┘

Note: Excel parsing (SheetJS) and ZIP extraction (JSZip) remain in frontend.
Only the similarity comparison logic runs in Python.
```

### 3.4 Rewrite/Write Flow

```
┌──────────┐     IPC        ┌──────────┐     stdin      ┌──────────┐
│ Frontend │ ──────────────► │ Electron │ ─────────────► │  Python  │
│  app.js  │                 │  main.js │                │  rules   │
│          │                 │          │                │          │
│ 1. User  │  api.rewrite   │ 2. Write │  JSON request  │ 3. Apply │
│    clicks│  (text)         │    to    │  to stdin      │    RW_RULES│
│    Rewrite│                │    stdin │                │ 4. Post- │
│           │                │          │                │    process│
│           │                │          │                │ 5. Bold  │
│           │                │          │                │    UI elems│
│           │                │          │                │ 6. Check │
│ 9. Render│  IPC response   │ 8. Parse │  stdout JSON   │    sentence│
│    diff   ◄────────────────│    stdout◄─────────────── │    length │
│    + log  │                │    JSON  │  response      │ 7. Return│
└──────────┘                 └──────────┘                └──────────┘

Note: Write Editor (formatting, file I/O, word count) stays entirely in frontend.
Only the rewrite transformation invokes the backend.
```

## 4. JSON Request/Response Schema

### 4.1 Request Envelope

All requests from Electron to Python follow this structure:

```json
{
  "id": "req-001",
  "action": "analyze | rewrite | convert_dita | impact_analyze",
  "payload": { ... }
}
```

Each JSON message is terminated by a newline (`\n`) for line-based reading.

### 4.2 Success Response Envelope

```json
{
  "id": "req-001",
  "success": true,
  "data": { ... }
}
```

### 4.3 Error Response Envelope

```json
{
  "id": "req-001",
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error",
    "details": "Technical details or stack trace"
  }
}
```

### 4.4 Action: analyze

**Request:**
```json
{
  "id": "req-001",
  "action": "analyze",
  "payload": {
    "text": "Click on the button to open the dialog box."
  }
}
```

**Response:**
```json
{
  "id": "req-001",
  "success": true,
  "data": {
    "violations": [
      {
        "start": 0,
        "end": 8,
        "ruleId": "WU-001",
        "category": "Word Usage",
        "message": "Use 'select' instead of 'click on'",
        "fix": "Select",
        "color": "#f39c12",
        "matchText": "Click on"
      }
    ],
    "summary": {
      "total": 1,
      "byCategory": {
        "Word Usage": 1
      }
    }
  }
}
```

### 4.5 Action: rewrite

**Request:**
```json
{
  "id": "req-002",
  "action": "rewrite",
  "payload": {
    "text": "In order to open the dialog box, click on the button."
  }
}
```

**Response:**
```json
{
  "id": "req-002",
  "success": true,
  "data": {
    "rewritten": "To open the dialog box, select the button.",
    "changes": [
      {
        "from": "In order to",
        "to": "To",
        "message": "in order to → to"
      },
      {
        "from": "click on",
        "to": "select",
        "message": "click on → select"
      }
    ],
    "sentenceWarnings": []
  }
}
```

### 4.6 Action: convert_dita

**Request:**
```json
{
  "id": "req-004",
  "action": "convert_dita",
  "payload": {
    "text": "Step 1. Open the application.\nStep 2. Select File > New.",
    "format": "task"
  }
}
```

**Response:**
```json
{
  "id": "req-004",
  "success": true,
  "data": {
    "xml": "<taskbody>\n<steps>\n<step>\n<cmd>Open the application.</cmd>\n</step>\n<step>\n<cmd>Select File &gt; New.</cmd>\n</step>\n</steps>\n</taskbody>"
  }
}
```

### 4.7 Action: impact_analyze

**Request:**
```json
{
  "id": "req-005",
  "action": "impact_analyze",
  "payload": {
    "jiraItems": [
      {
        "key": "DOC-123",
        "summary": "Update installation guide for v3.0",
        "description": "New prerequisites and changed steps",
        "issueType": "Task"
      }
    ],
    "ditaTopics": [
      {
        "title": "Installing the Application",
        "body": "Prerequisites: Java 11. Step 1: Download installer..."
      }
    ],
    "threshold": 0.18
  }
}
```

**Response:**
```json
{
  "id": "req-005",
  "success": true,
  "data": {
    "topicsToCreate": [
      {
        "jiraKey": "DOC-456",
        "summary": "Document new API endpoints",
        "issueType": "Story",
        "bestMatchScore": 0.05
      }
    ],
    "topicsToUpdate": [
      {
        "jiraKey": "DOC-123",
        "summary": "Update installation guide for v3.0",
        "matchedTopic": "Installing the Application",
        "confidence": 0.42
      }
    ]
  }
}
```

## 5. Error Handling Flow

```
┌──────────┐          ┌──────────┐          ┌──────────┐
│ Frontend │          │ Electron │          │  Python  │
│  app.js  │          │  main.js │          │ backend  │
└────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │
     │  api.analyze(text)  │                     │
     ├────────────────────►│                     │
     │                     │  JSON request       │
     │                     ├────────────────────►│
     │                     │                     │
     │                     │     ┌───────────────┤
     │                     │     │ Error occurs  │
     │                     │     │ (e.g. invalid │
     │                     │     │  regex, file  │
     │                     │     │  not found)   │
     │                     │     └───────────────┤
     │                     │                     │
     │                     │  JSON error response│
     │                     │◄────────────────────┤
     │                     │                     │
     │  IPC error response │                     │
     │◄────────────────────┤                     │
     │                     │                     │
     │  Display error msg  │                     │
     │  to user            │                     │
     ▼                     │                     │

PROCESS CRASH SCENARIO:
     │                     │                     │
     │                     │  Python process     │
     │                     │  exits unexpectedly │
     │                     │◄────────────────────X
     │                     │                     
     │                     │  Detect via 'exit'  
     │                     │  event on child     
     │                     │  process            
     │                     │                     
     │  IPC: backend_error │                     
     │◄────────────────────┤                     
     │                     │                     
     │  Show "Backend      │                     
     │  unavailable" msg   │                     
     ▼                     ▼                     
```

**Error codes:**

| Code | Meaning |
|------|---------|
| `RULE_ERROR` | Error evaluating a rule pattern |
| `INVALID_REQUEST` | Malformed JSON or missing required fields |
| `UNKNOWN_ACTION` | Unrecognized action in request |
| `INTERNAL_ERROR` | Unexpected Python exception |

## 6. App Startup and Shutdown Lifecycle

### Startup Sequence

```
1. User launches .exe
2. Electron main process starts
3. main.js spawns Python subprocess:
   - Command: python backend/protocol.py
   - stdio: ['pipe', 'pipe', 'pipe'] (stdin, stdout, stderr)
4. main.js waits for Python "ready" signal on stdout:
   {"status": "ready"}
5. main.js creates BrowserWindow
6. BrowserWindow loads frontend/index.html
7. preload.js exposes window.api via contextBridge
8. app.js initializes UI (tab state, event listeners)
9. Application is ready for user interaction
```

### Shutdown Sequence

```
1. User closes window (or Ctrl+Q)
2. 'before-quit' event fires in main.js
3. main.js sends shutdown signal to Python:
   {"action": "shutdown"}
4. Python performs cleanup, flushes buffers, exits
5. main.js waits up to 3 seconds for process exit
6. If Python hasn't exited, main.js sends SIGTERM
7. If still alive after 2 more seconds, SIGKILL
8. Electron app quits
```

### Crash Recovery

```
1. Python process exits unexpectedly (non-zero exit code)
2. main.js 'exit' event handler fires
3. main.js sends 'backend-error' IPC to renderer
4. Frontend displays "Backend process crashed" message
5. main.js does NOT auto-restart (user must restart app)
   - Rationale: auto-restart could mask persistent errors
```

## 7. Migration Order (Implementation Sequence)

### Phase 1: Separate HTML, CSS, JavaScript
**Duration estimate:** 1-2 days

1. Extract all `<style>` content → `frontend/styles.css`
2. Extract all `<script>` content (excluding embedded libraries) → `frontend/app.js`
3. Clean HTML markup → `frontend/index.html`
4. Replace inline onclick handlers with addEventListener in app.js
5. Verify: open `index.html` in browser, confirm identical behavior

### Phase 2: Identify and Document Business Logic Boundaries
**Duration estimate:** 0.5 day

1. Mark functions in app.js as either "UI" or "business logic"
2. Document the boundary in code comments
3. Business logic functions to extract:
   - `collectViolations()`, `checkSentenceLevel()`, `computeFixed()`
   - `applyRWRules()`, `checkSentenceLength()`, `boldUIElements()`
   - `convertConcept()`, `convertTask()`, `xEsc()`
   - `tokenise()`, `jaccardSim()` (comparison logic only)
4. UI functions that stay:
   - Tab switching, DOM rendering, event handlers
   - `buildSideBySide()`, `getContextHtml()` (rendering helpers)
   - Editor commands, file upload handlers
5. Verify: app still works identically (no code moved yet, only documented)

### Phase 3: Build Python Backend
**Duration estimate:** 3-4 days

1. Create `backend/rules.py` — port CA_RULES and RW_RULES arrays
2. Create `backend/utils.py` — port utility functions (xml_escape, tokenize, jaccard, DITA generators)
3. Create `backend/analyzer.py` — implement business logic orchestration functions (analyze, rewrite, convert_dita, impact_analyze)
4. Create `backend/protocol.py` — implement stdin/stdout message loop, JSON parsing, action routing, shutdown handling, logging
5. Verify: run `python backend/protocol.py` standalone with test JSON inputs piped to stdin, compare output to JS implementation

### Phase 4: Set Up Electron Shell
**Duration estimate:** 1-2 days

1. Initialize npm project with Electron dependency
2. Create `electron/main.js` — window creation, Python subprocess management
3. Create `electron/preload.js` — contextBridge with approved API methods
4. Configure `package.json` scripts and electron-builder for .exe packaging
5. Verify: app launches as desktop window, loads frontend, Python process starts/stops cleanly

### Phase 5: Connect Frontend to Backend via IPC
**Duration estimate:** 2-3 days

1. Replace `collectViolations()` call in app.js with `await window.api.analyze(text)`
2. Replace `applyRWRules()` call with `await window.api.rewrite(text)`
3. Replace `convertConcept()`/`convertTask()` with `await window.api.convertDita(text, format)`
4. Replace similarity comparison in `runImpactAnalysis()` with `await window.api.impactAnalyze(...)`
5. Keep .docx text extraction in frontend using mammoth.js (no backend call needed)
6. Add loading states during async backend calls
7. Add error handling for backend failures
8. Remove dead business logic code from app.js
9. Verify: full end-to-end testing of all four tabs

### Phase 6: Package and Distribute
**Duration estimate:** 1 day

1. Configure electron-builder for Windows .exe output
2. Bundle Python as embedded runtime (PyInstaller or embedded Python)
3. Test packaged .exe on clean Windows machine
4. Verify: no Python installation required on target machines

## 8. Testing Strategy

### Phase 1 Testing: Visual Regression
- **Method:** Side-by-side screenshot comparison of monolith vs separated files
- **Scope:** All four tabs, all interactive states (hover, active, expanded rows)
- **Pass criteria:** Pixel-identical rendering in Chromium

### Phase 2 Testing: Boundary Documentation Review
- **Method:** Code review of annotated app.js
- **Scope:** Every function classified as UI or business logic
- **Pass criteria:** No ambiguous classifications, clear extraction plan

### Phase 3 Testing: Backend Parity
- **Method:** Golden-file testing
- **Process:**
  1. Run monolith JS analysis on 10+ sample texts, capture JSON output
  2. Run Python backend on same texts, capture JSON output
  3. Assert identical violation lists (same positions, same rule IDs, same order)
- **Scope:** Content analysis, rewrite, DITA conversion, impact analysis
- **Pass criteria:** 100% output match for all test cases

### Phase 4 Testing: Electron Lifecycle
- **Method:** Manual + scripted testing
- **Checks:**
  - App launches and shows window
  - Python process visible in task manager during runtime
  - Python process gone after app close
  - No orphan processes after force-kill of Electron
  - Error displayed if Python fails to start
- **Pass criteria:** Clean lifecycle in all scenarios

### Phase 5 Testing: End-to-End Integration
- **Method:** Manual testing of all user workflows
- **Scenarios:**
  - Content Analysis: paste text → analyze → view violations → apply fix → re-analyze
  - Content Analysis: upload .docx (mammoth in frontend) → analyze → view violations
  - Rewrite: paste text → rewrite → view diff → copy/download result
  - DITA: enter text → convert concept → convert task → verify XML
  - Impact: upload Excel → upload ZIP → run analysis → view results → export CSV
  - Write Editor: format text, find/replace, open/save files, print
- **Pass criteria:** All workflows produce identical results to monolith

### Phase 6 Testing: Distribution
- **Method:** Install .exe on clean Windows machine (no dev tools)
- **Checks:**
  - Installer runs without errors
  - App launches without Python pre-installed
  - All features work on target machine
  - Uninstall removes all files cleanly
- **Pass criteria:** Zero-dependency deployment works

## 9. Risk Areas

| Risk | Impact | Mitigation |
|------|--------|------------|
| Regex behavior differences between JS and Python | Violations at different positions | Port patterns carefully; golden-file testing with edge cases |
| stdin/stdout buffering issues | Hung requests, partial JSON | Use line-based protocol with `\n` delimiter; flush after every write |
| Python startup time on cold launch | Slow app start | Pre-warm: spawn Python immediately, show splash/loading |
| Large file processing blocks stdin/stdout | UI freeze during analysis | Keep operations fast; defer progress reporting if needed later |
| Embedded Python bundling increases .exe size | Large installer (~50-80MB) | Acceptable tradeoff for zero-dependency deployment |
| Write Editor file I/O conflicts with Electron sandbox | Editor can't save files | Use Electron dialog API for file paths, keep mammoth/docx.js in renderer |
| SheetJS/JSZip in renderer with nodeIntegration disabled | Libraries can't access fs | These libraries work with ArrayBuffer (no fs needed); confirmed safe |
| Overlapping violation resolution order differs | Different violations shown | Port exact same algorithm: sort by start, skip if start < cursor |
| Python process orphaned on Windows | Background processes accumulate | Register handlers for all exit events; use process group kill |

## 10. Constraints Summary

- Preserve existing UI behavior exactly (no visual or interaction changes)
- Preserve existing styling (extract CSS as-is)
- Avoid unnecessary rewrites (port logic, don't redesign it)
- Maintain clear frontend/backend separation (no business logic in app.js)
- Frontend libraries stay in frontend (SheetJS, JSZip, mammoth, docx.js, FileSaver)
- .docx parsing stays in frontend using mammoth.js — no duplication in Python
- No HTTP server, no WebSocket, no FastAPI/Flask
- stdin/stdout JSON only for Electron↔Python communication
- Electron IPC only for Frontend↔Electron communication
- Single persistent Python process per app instance
- Backend protocol (I/O) separated from business logic (analyzer)
- Backend logs to stderr, never stdout (stdout reserved for protocol)
- Windows .exe distribution with no external dependencies
