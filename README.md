# Medical Writer Vale Auditor

A Windows desktop application for auditing Word documents against a controlled writing-style ruleset.

The application combines:

- Vale-based text rules;
- Word structural validation;
- context-aware Standard and Advanced audit profiles;
- Word comment insertion;
- abbreviation discovery and registry management;
- generated audit summaries and audit manifests.

> This tool supports editorial review. It does not establish scientific, medical, statistical, legal, or regulatory correctness. All audit findings require qualified human review.

---

## Current Status

The application is an internal beta intended for controlled use on document copies.

### Standard Audit

Recommended for real-world protocol and agency-response documents.

Includes:

- controlled terminology and preferred wording;
- date, time, age, spelling, punctuation, and quantitative rules;
- abbreviation-list checks;
- approved abbreviation first-use checks;
- known typography checks;
- external URL and active hyperlink checks;
- candidate abbreviation report generation.

Excludes experimental structural checks by default.

### Advanced Structural Review

Use only on controlled test documents or when validating document structure.

Includes:

- list validation;
- table heading and zero-value checks;
- table captions and footnotes;
- figure validation;
- appendix numbering checks.

---

## Requirements

The application currently requires:

- Windows;
- Microsoft Word desktop application;
- Python 3.11 or later;
- Vale CLI;
- Python dependencies listed below.

### Python Dependencies

```text
python-docx
pywin32
