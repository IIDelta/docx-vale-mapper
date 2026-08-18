# Medical Writer Vale Auditor

A Windows desktop application for auditing Word documents against a controlled writing-style ruleset.

The application combines:

- Vale-based text rules;
- Word structural validation;
- unified Operational Audit execution path;
- Word comment insertion;
- abbreviation discovery and registry management;
- generated audit summaries and audit manifests.

> This tool supports editorial review. It does not establish scientific, medical, statistical, legal, or regulatory correctness. All audit findings require qualified human review.

---

## Current Status

The application is an internal beta intended for controlled use on document copies.

### Operational Audit

The primary operational path for all clinical documents. 

Includes:

- controlled terminology and preferred wording;
- date, time, age, spelling, punctuation, and quantitative rules;
- abbreviation-list checks;
- approved abbreviation first-use checks;
- known typography checks;
- external URL and active hyperlink checks;
- candidate abbreviation report generation;
- list, table, figure, and appendix structure validation.

All behavior is centrally managed via `config/commentpolicy.json`.

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
```

---

## Documentation & Architecture

For more details on the repository layout, system architecture, and development guidelines, please refer to:
- **[`docs/architecture.md`](docs/architecture.md)**: A high-level overview of the application's core components and data flow.
- **[`AGENTS.md`](AGENTS.md)**: Onboarding instructions and task backlogs for AI agents navigating this repository.
