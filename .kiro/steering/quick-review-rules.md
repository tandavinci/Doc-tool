---
inclusion: fileMatch
fileMatchPattern: "**/review_engine*,**/quick*review*,**/quickReview*"
---

# Enterprise Documentation Quick Review Rules

These rules govern the Quick Review tab's validation engine.

## Review Priorities (in order)

1. Information Typing + DITA Compliance
2. Global English + Technical Writing Standards
3. Translation Readiness + Content Reuse
4. Editorial Improvements

Never prioritize style over correctness.

## Rule Set 1: Information Typing Validation

### Concept Topic
- Answers: What is it? Why is it used? What benefits?
- Required: Noun-based title, overview content, explanatory info, feature descriptions
- Reject: Numbered procedures, click instructions, navigation paths, imperative actions
- Flag: "Task-oriented content detected in Concept topic."

### Task Topic
- Answers: How do I perform this action?
- Required: Verb-based title, single user goal, sequential actions, imperative voice
- Required elements: shortdesc, prerequisites (if applicable), steps, result
- Reject: Product marketing, architectural discussions, long conceptual explanations
- Flag: "Concept-oriented content detected in Task topic."

### Reference Topic
- Contains: Lookup info, field definitions, parameter descriptions, code tables, error messages
- Reject: Procedures, feature explanations

## Rule Set 2: Topic Classification

- Content explains WHAT or WHY → Concept
- Content explains HOW → Task
- Content is lookup info → Reference
- Contains ordered actions → Task
- Title starts with verb → Task
- Title describes feature/process/object/capability → Concept

## Rule Set 3: Global English Compliance

- Validate: Logical sentence construction, literal language, precise wording, explicit relationships
- Reject: Ambiguous references, figurative language, unclear modifiers, vague terminology
- Flag: "Sentence is not logically or literally expressed."

## Rule Set 4: Standard English Compliance

- Validate: Standard dictionary usage, correct parts of speech, standard verb complements
- Reject: Nouns used as verbs ("action this report" → "resubmit the report")
- Reject: Adjectives used as nouns ("the pop-up" → "the pop-up menu")
- Reject: Artificial verbs (VDEFINEd, RIFed, OR'ed)
- Flag: "Non-standard word formation detected."

## Rule Set 5: Translation Readiness

- Reject: Content requiring interpretation
- Require: Explicit wording
- Bad: "When you hover over a menu item"
- Good: "When you position the mouse pointer over a menu item"
- Flag: "Translation ambiguity detected."

## Rule Set 6: Syntactic Cue Validation

- Validate presence of: that, which, relative clauses, conjunctions, required punctuation
- Reject: Sentence simplification that creates ambiguity
- Flag: "Syntactic cue removed, causing ambiguity."

## Rule Set 7: Terminology Consistency

- Same term used consistently throughout
- Approved product terminology and UI labels
- Reject multiple terms for same object
- Flag: "Terminology inconsistency detected."

## Rule Set 8: UI Language Standards

- Buttons: Use exact UI labels ("Select Save." not "Click the save button.")
- Menus: Use exact menu path ("Select File > Settings > Users.")
- Validate consistent capitalization of UI labels

## Rule Set 9: Conciseness Validation

- No redundant introductions, duplicate explanations, repeated concepts
- Flag: "Content reduction opportunity detected."

## Rule Set 10: Reusability Review

- Detect: Duplicate topics, procedures, warnings, notes
- Recommend: conref, keyref, shared topics
- Flag: "Reusable content opportunity detected."

## Rule Set 11: Short Description Validation

- Every topic must have shortdesc (20-60 words)
- Concept: explains what the feature is
- Task: explains outcome of procedure
- Reference: explains purpose of reference information
- Flag: "Missing or insufficient short description."

## Rule Set 12: Image Validation

- Image supports content, referenced in text, has alt text
- Reject decorative images
- Flag: "Image does not provide instructional value."

## Rule Set 13: Content Reduction Governance

- Review for duplicate information, repeated explanations/warnings/examples
- Apply topic-level and sentence-level reduction

## Rule Set 14: Compliance Scoring

| Category | Weight |
|----------|--------|
| Information Typing | 25% |
| DITA Structure | 20% |
| Global English | 15% |
| Translation Readiness | 15% |
| Writing Quality | 10% |
| Terminology | 5% |
| Reusability | 5% |
| Content Efficiency | 5% |

### Score Interpretation
- 95-100: Enterprise Ready
- 90-94: Compliant
- 80-89: Minor Issues
- 70-79: Major Revision Required
- Below 70: Non-Compliant

## Required Review Output

1. Topic Classification
2. Compliance Score
3. Critical Violations
4. Major Violations
5. Minor Violations
6. Translation Risks
7. Reuse Opportunities
8. Recommended Actions
9. Pass/Fail Decision
