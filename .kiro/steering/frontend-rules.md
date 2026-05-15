---
inclusion: always
---
# Frontend Rules

Responsibilities:

* Render UI
* Handle button clicks
* Handle file uploads
* Show analysis results
* Show loading states

Do not:

* Implement content analysis rules
* Implement scoring logic
* Implement validation logic unrelated to UI

Code style:

* Keep DOM logic modular
* Use event listeners instead of inline onclick handlers
* Use clear function names
* Avoid duplicate DOM manipulation logic

Goal:
Frontend should remain lightweight and focused only on interaction and display.
