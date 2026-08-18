<<<<<<< HEAD
# Architecture

## Purpose
Medical Writer Vale Auditor audits DOCX clinical/regulatory documents against a controlled Takeda Style Guide ruleset. It is an editorial-support tool; findings require qualified human review.

## Data Flow
```text
DOCX source
  -> Word COM extraction
  -> ParagraphRecord / table / caption / figure records
  -> Vale rules + structural validators
  -> context and protected-field filtering
  -> final findings
  -> JSON reports
  -> comment policy
  -> auto-fix and comment plans
  -> read-only preflight
  -> optional copied-DOCX execution
```

## Layer Boundaries

### `app/`
Owns Tkinter UI, user input, workflow launch, and status/progress display. It must not resolve Word ranges or implement style rules.

### `runtime/`
Owns audit lifecycle, artifact creation, manifests, comment policy, plans, preflight, and execution logs. It must not build GUI widgets.

### `word/`
Owns Word COM extraction, range resolution, comments, copied-document auto-fixes, and output verification. It must not decide rule dispositions.

### `validators/`
Owns deterministic checks and finding creation. It must not open or save DOCX files.

### `abbreviations/`
Owns candidate discovery, SQLite registry, review windows, promotion, and abbreviation reports.

### `Styles/`
Owns Vale YAML rules and their messages/actions.

### `config/`
Owns controlled policy: rule coverage, comment policy, scientific terms, heading terms, and unit-style exclusions.

## Invariants
- Source DOCX is never overwritten.
- Reports-only mode does not create an audited DOCX.
- Auto-fix requires source SHA and verified range.
- Comments require verified anchors.
- Protected fields are not edited or commented.
- Generated audit artifacts are not committed.
=======
# Application Architecture

## Overview

The Medical Writer Vale Auditor is a desktop utility for Windows designed to audit Microsoft Word (`.docx`) documents against controlled writing-style rules. It blends structure-aware document parsing with Vale's rule-based natural language processing to produce comprehensive audit reports and execute automated document modifications.

## Core Components

The application is built around several cooperating subsystems:

### 1. Document Parsing & Mutability
- **`python-docx`**: Used for fast, headless structural analysis of Word documents. It parses paragraphs, tables, runs, and styles.
- **`pywin32` (Word Interop)**: Used for precise mutation of documents (inserting comments, applying autofixes) by interacting directly with the native Microsoft Word COM interface. This ensures Word's internal logic tracks changes and preserves complex formatting.

### 2. Validation Engine (`validators/`)
Performs context-aware structural validation independent of Vale.
- **Table and Figure Validators**: Checks caption sequencing, table footnotes, headings, and zero-value presentations.
- **Citation and Reference Validators**: Asserts that cross-references and external links are active and styled correctly.
- **Style and Formatting Checkers**: Validates typography (non-breaking spaces, hyphenation) and specific Word style usages (e.g., heading hierarchies).

### 3. NLP Analysis (Vale Integration)
The application shells out to the **Vale CLI**, executing rules defined in the `Styles/` directory. The results are mapped back to precise locations within the Word document using the `validators/valespan.py` mapping utility, translating plain-text character offsets to Word document ranges.

### 4. Abbreviation Registry (`abbreviations/`)
A dedicated sub-engine for discovering, validating, and cataloging abbreviations.
- Scans documents for first-use definitions.
- Maintains a local SQLite registry (`data/`) of approved and unapproved abbreviations.
- Automates the generation of abbreviation reports and lists.

### 5. Audit Runtime (`runtime/`)
Orchestrates the lifecycle of an audit run.
- **Preflight Checks**: Assesses document readiness and configuration validity before running expensive audits.
- **Comment Policy Engine**: Enforces constraints on how many comments can be added to a document (`commentbudget.py`) and under what conditions (`commentpolicy.py`) to prevent overwhelming medical writers.
- **Autofix Executor**: Safely applies mechanical fixes (e.g., standardizing non-breaking spaces or simple typos) directly to the document.

## Data Flow

1. **Initialization**: The user initiates an audit (Standard or Advanced mode) via `main.py`.
2. **Preflight**: The `runtime/preflight.py` verifies prerequisites (Word installed, Vale accessible, valid profile).
3. **Parsing**: The document is read into memory via `python-docx` for structural checks.
4. **Analysis**:
   - Internal validators process tables, captions, and structural elements.
   - Text is extracted and passed to Vale for style and terminology checks.
   - Abbreviations are extracted and resolved against the local SQLite registry.
5. **Mapping**: Findings are consolidated, filtered for duplicates (`validators/findingmerge.py`), and mapped to Word ranges.
6. **Execution**:
   - **Reports Mode**: Generates JSON/CSV manifests (`reports/`) without touching the document.
   - **Comment Mode**: Invokes Word Interop to drop comment pins on the document according to the budget.
   - **Autofix Mode**: Invokes Word Interop to apply targeted text replacements.

## Security and Extensibility
- **Field Protection**: `validators/fieldprotection.py` ensures that automatically updated fields (e.g., Table of Contents, Cross-references) are not inadvertently corrupted during text manipulation.
- **Configurable Profiles**: The audit ruleset can be swapped or customized via the `config/` definitions to support varying editorial standards.
>>>>>>> 913a656 (architectural updates)
