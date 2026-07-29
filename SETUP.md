# Setup Guide — Documentation AI Tool

## Quick Start (3 steps)

**Prerequisites:** Windows 10/11, [Python 3.10+](https://python.org), [Node.js 18+](https://nodejs.org)

```
1. Double-click  setup.bat
2. Wait for it to finish (downloads ~2GB AI model on first run)
3. Run:  npm start
```

That's it. The app launches with full offline AI capability.

---

## What setup.bat Does

1. Verifies Python and Node.js are installed
2. Downloads and installs [Ollama](https://ollama.com) (local AI engine)
3. Pulls the `llama3.2` model (~2GB, one-time download)
4. Installs Python packages (`markitdown`, `openai`)
5. Installs Node.js packages (`electron`, `electron-builder`)

After setup completes, **no internet is required** to use the app.

---

## Running the App

| Command | Description |
|---------|-------------|
| `npm start` | Launch the app |
| `npm run dev` | Launch with DevTools open |

The app auto-starts Ollama in the background. No manual steps needed.

---

## Building a Distributable (for sharing)

To create a standalone installer that works on any Windows PC without Python/Node/internet:

```
build-all.bat
```

Output:
- `dist\Content Analysis Setup *.exe` — Standard installer
- `dist\Content Analysis-Portable-*.exe` — Portable (no install needed)

The distributable bundles everything: the app, Python backend, Ollama, and the AI model.

---

## Sharing with Others

Recipients just run the installer or portable exe. They do **not** need:
- Python
- Node.js
- Ollama
- Internet connection

Everything is self-contained.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Python not found" | Install from https://python.org — check "Add to PATH" during install |
| "Node.js not found" | Install from https://nodejs.org (LTS version) |
| "Ollama not in PATH" | Restart terminal after setup.bat installs Ollama, then run setup.bat again |
| AI Assistant says "Cannot connect to Ollama" | Run `ollama serve` in a separate terminal |
| AI responses are slow | Normal for first query (~5-30s). The local model needs warm-up time |
| Build fails at PyInstaller | Run `pip install pyinstaller "markitdown[all]"` manually |

---

## Project Structure

```
Doc-AI-Analyst/
├── frontend/          HTML/CSS/JS UI
├── backend/           Python analysis engine + AI assistant
├── electron/          Electron shell (main.js, preload.js)
├── setup.bat          One-click dev environment setup
├── build-all.bat      Build standalone distributable
├── package.json       Node.js config + electron-builder settings
└── backend.spec       PyInstaller config for backend bundling
```

---

## Configuration

The AI model can be changed via environment variable (before running):

```
set OLLAMA_MODEL=llama3.2:latest
npm start
```

Default: `llama3.2:latest` (3B parameters, fast, works well on most hardware)

For better quality (requires more RAM/VRAM):
```
ollama pull llama3.1:8b
set OLLAMA_MODEL=llama3.1:8b
npm start
```
