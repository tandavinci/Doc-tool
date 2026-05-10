---
inclusion: always
---
# Backend Rules

Responsibilities:

* Parse content
* Evaluate writing standards
* Apply content rules
* Generate analysis results
* Generate issue lists
* Generate scores

Design:

* Keep rules modular
* One responsibility per function
* Rules should be reusable and testable

Modules:

* analyzer.py = main analysis orchestration
* rules.py = writing rules
* parser.py = content parsing
* utils.py = helper functions

Code quality:

* Prefer readability over optimization
* Use descriptive function names
* Keep logic testable
