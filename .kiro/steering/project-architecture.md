---
inclusion: always
---
# Project Architecture Rules

Project: Content Analysis Desktop Application

Architecture:

Desktop shell must use Electron
Frontend must remain HTML/CSS/JavaScript
Backend analysis engine must use Python

Separation of concerns:

Frontend handles UI rendering and user interaction only
Backend handles content analysis logic and rule evaluation
Frontend must not contain business logic

Folder structure:

frontend/

index.html
styles.css
app.js

backend/

analyzer.py
rules.py
parser.py
utils.py

electron/

main.js
preload.js

Communication:

Frontend and backend must communicate through Electron IPC

Migration principle:

Preserve current UI behavior
Preserve styling
Preserve functionality