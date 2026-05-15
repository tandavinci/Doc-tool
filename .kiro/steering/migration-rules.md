---
inclusion: always
---
# Migration Rules

Source:
Current application exists as a monolithic HTML file.

Migration phases:

1. Separate HTML, CSS, and JavaScript
2. Identify business logic
3. Move business logic to Python
4. Integrate Electron shell
5. Connect frontend to backend

Important:

* Do not rewrite functionality unless necessary
* Refactor incrementally
* Validate functionality after every phase
* Preserve UI behavior during migration
