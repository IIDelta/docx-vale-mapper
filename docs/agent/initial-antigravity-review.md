# Initial Antigravity Review

## 1. Repository Tree and Top-Level Directory Purpose

- **`.git/`**: Git repository data.
- **`Styles/`**: Contains Vale-based text rules and style guides.
- **`abbreviations/`**: Logic for abbreviation discovery, processing, and registry management.
- **`config/`**: Configuration files for the application (e.g., audit profiles).
- **`data/`**: Stores generated sqlite registry data and databases.
- **`registry/`**: Abbreviation registry or terminology APIs and data access.
- **`reports/`**: Output directory for generated audit summaries and manifests.
- **`runtime/`**: Core execution runtime, managing audit runs, reporting, autofix logic, and comment generation.
- **`tests/`**: Unit tests and regression test fixtures.
- **`validators/`**: Rules and logic for structural validation of Word documents (e.g., tables, figures, citations, references, styles).
- **`main.py`**: The main entry point for the application CLI or orchestrator.

## 2. Python Modules, Imports, and Apparent Responsibilities

### Root Directory
- **`main.py`**
  - *Imports*: standard library, `abbreviations.*`, `runtime.*`, `validators.*`
  - *Responsibility*: Application entry point and orchestrator.

### `abbreviations/` (Abbreviation Discovery & Registry)
- **`abbreviations/auditbridge.py`**
  - *Imports*: `__future__.annotations`, `dataclasses.dataclass`
  - *Responsibility*: Integration between abbreviation logic and audit context.
- **`abbreviations/candidatefinder.py`**
  - *Imports*: `__future__.annotations`, `re`, `dataclasses.dataclass`, `pathlib.Path`
  - *Responsibility*: Discovers candidate abbreviations in text.
- **`abbreviations/detector.py`**
  - *Imports*: `__future__.annotations`, `re`, `dataclasses.dataclass`
  - *Responsibility*: Detects abbreviation patterns.
- **`abbreviations/exportlist.py`**
  - *Imports*: `__future__.annotations`, `csv`, `pathlib.Path`
  - *Responsibility*: Exports abbreviation lists to external formats.
- **`abbreviations/legacyimport.py`**
  - *Imports*: `__future__.annotations`, `csv`, `sqlite3`, `pathlib.Path`
  - *Responsibility*: Imports legacy abbreviation sources/databases.
- **`abbreviations/listgenerator.py`**
  - *Imports*: `__future__.annotations`, `dataclasses.dataclass`
  - *Responsibility*: Generates structured abbreviation lists.
- **`abbreviations/listinserter.py`**
  - *Imports*: `__future__.annotations`
  - *Responsibility*: Inserts abbreviation lists into documents.
- **`abbreviations/models.py`**
  - *Imports*: `__future__.annotations`, `dataclasses.dataclass`
  - *Responsibility*: Core data models for abbreviations.
- **`abbreviations/registryapi.py`**
  - *Imports*: `__future__.annotations`, `sqlite3`, `pathlib.Path`
  - *Responsibility*: API for interacting with the local SQLite abbreviation registry.
- **`abbreviations/reportpaths.py`**
  - *Imports*: `__future__.annotations`, `pathlib.Path`
  - *Responsibility*: Path management for generated abbreviation reports.
- **`abbreviations/resolver.py`**
  - *Imports*: `__future__.annotations`, `dataclasses.dataclass`
  - *Responsibility*: Resolves extracted abbreviations against the known registry.
- **`abbreviations/reviewactions.py`**
  - *Imports*: `__future__.annotations`, `sqlite3`, `pathlib.Path`
  - *Responsibility*: Logic for tracking local review decisions on abbreviations.
- **`abbreviations/reviewimport.py`**
  - *Imports*: `__future__.annotations`, `csv`, `sqlite3`, `pathlib.Path`
  - *Responsibility*: Imports abbreviation review feedback.
- **`abbreviations/reviewpromote.py`**
  - *Imports*: `__future__.annotations`, `sqlite3`, `pathlib.Path`
  - *Responsibility*: Promotes reviewed abbreviations to the central registry.
- **`abbreviations/reviewreport.py`**
  - *Imports*: `__future__.annotations`, `csv`, `json`, `pathlib.Path`
  - *Responsibility*: Generates abbreviation review reports.
- **`abbreviations/reviewwindow.py`**
  - *Imports*: `__future__.annotations`, `json`, `pathlib.Path`
  - *Responsibility*: Manages the abbreviation review window/payload UI state.
- **`abbreviations/validator.py`**
  - *Imports*: `__future__.annotations`
  - *Responsibility*: Validates abbreviation structures.

### `runtime/` (Audit Execution Runtime)
- **`runtime/auditmanifest.py`**
  - *Imports*: `__future__.annotations`, `json`, `pathlib.Path`, `dataclasses.dataclass`
  - *Responsibility*: Manages the audit manifest lifecycle.
- **`runtime/auditmode.py`**
  - *Imports*: `__future__.annotations`, `enum.Enum`
  - *Responsibility*: Configures Standard vs. Advanced audit profiles.
- **`runtime/auditreport.py`**
  - *Imports*: `__future__.annotations`, `json`, `pathlib.Path`, `dataclasses.dataclass`
  - *Responsibility*: Manages the generation of audit reports.
- **`runtime/autofixexecutor.py`**
  - *Imports*: `__future__.annotations`, `dataclasses.dataclass`
  - *Responsibility*: Executes automatic fixes on documents.
- **`runtime/autofixpreflight.py`**
  - *Imports*: `__future__.annotations`, `dataclasses.dataclass`
  - *Responsibility*: Pre-validates auto-fixes before execution.
- **`runtime/commentbudget.py`**
  - *Imports*: `__future__.annotations`, `dataclasses.dataclass`
  - *Responsibility*: Manages constraints or caps on Word comments to prevent flooding.
- **`runtime/commentlifecycle.py`**
  - *Imports*: `__future__.annotations`
  - *Responsibility*: Manages the lifecycle of comments in Word.
- **`runtime/commentpolicy.py`**
  - *Imports*: `__future__.annotations`, `dataclasses.dataclass`
  - *Responsibility*: Defines rules/policies for when to add comments.
- **`runtime/commentpreflight.py`**
  - *Imports*: `__future__.annotations`, `dataclasses.dataclass`
  - *Responsibility*: Pre-validates comments before insertion.
- **`runtime/preflight.py`**
  - *Imports*: `__future__.annotations`, `pathlib.Path`
  - *Responsibility*: General audit preflight checks.
- **`runtime/reportscontract.py`**
  - *Imports*: `__future__.annotations`, `json`, `pathlib.Path`
  - *Responsibility*: Validates report artifacts for adherence to contract formats.

### `validators/` (Document Validation Rules)
- **`validators/abbreviationvalidator.py`**
  - *Imports*: `__future__.annotations`, `json`, `re`, `collections.Counter`, `dataclasses.dataclass`, `pathlib.Path`
  - *Responsibility*: Validates abbreviations in document paragraphs.
- **`validators/appendixvalidator.py`**
  - *Imports*: `__future__.annotations`, `re`, `dataclasses.dataclass`
  - *Responsibility*: Validates appendix structures.
- **`validators/auditprofile.py`**
  - *Imports*: `__future__.annotations`
  - *Responsibility*: Configurations for audit profiles.
- **`validators/captionfootnotevalidator.py`**
  - *Imports*: `__future__.annotations`, `re`, `dataclasses.dataclass`
  - *Responsibility*: Validates captions and footnotes.
- **`validators/citationvalidator.py`**
  - *Imports*: `__future__.annotations`, `re`, `dataclasses.dataclass`
  - *Responsibility*: Validates citations in text.
- **`validators/commentverification.py`**
  - *Imports*: `__future__.annotations`, `re`
  - *Responsibility*: Validates comment syntax or content.
- **`validators/contextvalidator.py`**
  - *Imports*: `__future__.annotations`, `re`
  - *Responsibility*: Context-aware text validation.
- **`validators/fieldprotection.py`**
  - *Imports*: `__future__.annotations`, `collections.abc.Iterable`
  - *Responsibility*: Protects specific Word fields from modification.
- **`validators/figurevalidator.py`**
  - *Imports*: `__future__.annotations`, `re`, `dataclasses.dataclass`
  - *Responsibility*: Validates figure formatting and numbering.
- **`validators/findingfilter.py`**
  - *Imports*: `__future__.annotations`, `collections.Counter`
  - *Responsibility*: Filters out noisy or invalid Vale findings.
- **`validators/findingmerge.py`**
  - *Imports*: `__future__.annotations`
  - *Responsibility*: Merges duplicate or overlapping findings.
- **`validators/headingterms.py`**
  - *Imports*: `__future__.annotations`, `json`, `pathlib.Path`
  - *Responsibility*: Validates specific terminology in headings.
- **`validators/headingvalidator.py`**
  - *Imports*: `__future__.annotations`, `re`, `typing.Any`
  - *Responsibility*: Validates heading hierarchies and structure.
- **`validators/listvalidator.py`**
  - *Imports*: `__future__.annotations`, `re`, `typing.Iterable`
  - *Responsibility*: Validates list structures.
- **`validators/referencevalidator.py`**
  - *Imports*: `__future__.annotations`, `re`
  - *Responsibility*: Validates external references and hyperlinks.
- **`validators/scientificterms.py`**
  - *Imports*: `__future__.annotations`, `json`, `re`, `pathlib.Path`
  - *Responsibility*: Validates controlled scientific terms.
- **`validators/tablevalidator.py`**
  - *Imports*: `__future__.annotations`, `re`, `dataclasses.dataclass`
  - *Responsibility*: Validates table structures, headings, and cells.
- **`validators/testreferencevalidator.py`**
  - *Imports*: `__future__.annotations`, `unittest`
  - *Responsibility*: Test suite for reference validation.
- **`validators/typographyvalidator.py`**
  - *Imports*: `__future__.annotations`, `re`, `collections.abc.Callable`
  - *Responsibility*: Validates typography conventions (e.g., non-breaking spaces).
- **`validators/unitstyles.py`**
  - *Imports*: `__future__.annotations`, `json`, `pathlib.Path`
  - *Responsibility*: Validates unit expressions and formatting.
- **`validators/valespan.py`**
  - *Imports*: `__future__.annotations`
  - *Responsibility*: Maps Vale finding spans back to Word document ranges.

*(Note: `tests/` directory contains standard `unittest` modules targeting the above modules and components).*

## 3. Stale README Statements

- **Dependency Discrepancy**: The `README.md` lists both `python-docx` and `pywin32` under "Python Dependencies". However, the actual `requirements.txt` file only contains `python-docx>=1.1,<2.0`. The `pywin32` dependency is missing from the active requirements file, indicating the `requirements.txt` may be incomplete or the README is outdated.
- **Missing Directories/Files**: The review prompt expected an `AGENTS.md` and a `docs/` directory. Neither exists in the current repository, suggesting newer onboarding or documentation workflows are assumed but not yet committed to the repository.

## 4. Generated Artifacts to Add to `.gitignore`

The `.gitignore` currently covers local registry/report artifacts and document-specific JSONs, but should be updated to ignore standard developer and testing artifacts:
- `.vscode/` or `.idea/` (IDE settings)
- `*.log` (Execution or crash logs)
- `.pytest_cache/`
- `.coverage` and `htmlcov/` (If test coverage is generated)
- `.DS_Store` and `Thumbs.db` (OS-specific metadata)
- `.vale/` (If Vale downloads local packages/styles dynamically)

## 5. Proposed Task Backlog

Ordered according to the requested priority sequence:

1. **Architecture**
   - Resolve discrepancies between `README.md` dependencies and `requirements.txt` (e.g., adding `pywin32`).
   - Create missing `AGENTS.md` and standardize `docs/` structure for project onboarding.
   - Refactor overlapping validation logic and abstract file interactions if necessary.

2. **Testing**
   - Implement continuous integration (CI) tests for Vale rules.
   - Standardize `unittest` integration or move to `pytest`.
   - Add test coverage reports to track coverage of validators and runtime logic.

3. **Reports-only Mode**
   - Consolidate generation of `.csv`, `.json`, and `.md` reports.
   - Finalize `runtime/reportscontract.py` for generating clean audit manifests without document modification.

4. **Word Execution**
   - Improve offset mapping from `validators/valespan.py` to target precise text elements via the Word Interop/python-docx API.
   - Safely extract paragraph records and field contexts (`validators/fieldprotection.py`) to prevent corrupting Word documents.

5. **Comment Execution**
   - Integrate `runtime/commentbudget.py` and `runtime/commentpolicy.py` into a cohesive comment insertion pipeline.
   - Safely deploy comments into Word documents, honoring the comment limits and placement rules.

6. **Auto-fix Execution**
   - Roll out `runtime/autofixpreflight.py` and `runtime/autofixexecutor.py` safely.
   - Apply automatic fixes to non-breaking spaces, typos, and simple abbreviation mappings without human intervention.
