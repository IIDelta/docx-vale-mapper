from __future__ import annotations
from contextlib import contextmanager

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_imports (
    import_id INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_sha256 TEXT NOT NULL UNIQUE,
    imported_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_terms (
    candidate_id INTEGER PRIMARY KEY,
    import_id INTEGER NOT NULL,
    source_line INTEGER NOT NULL,
    raw_token TEXT NOT NULL,
    normalized_token TEXT NOT NULL,
    raw_definition TEXT NOT NULL DEFAULT '',
    normalized_definition TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'legacy_candidate',
    FOREIGN KEY (import_id)
        REFERENCES source_imports(import_id)
        ON DELETE CASCADE,
    UNIQUE (import_id, source_line)
);

CREATE TABLE IF NOT EXISTS import_issues (
    issue_id INTEGER PRIMARY KEY,
    import_id INTEGER NOT NULL,
    candidate_id INTEGER,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    token TEXT,
    details TEXT NOT NULL,
    FOREIGN KEY (import_id)
        REFERENCES source_imports(import_id)
        ON DELETE CASCADE,
    FOREIGN KEY (candidate_id)
        REFERENCES candidate_terms(candidate_id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_candidate_terms_import
    ON candidate_terms(import_id);

CREATE INDEX IF NOT EXISTS idx_candidate_terms_token
    ON candidate_terms(normalized_token);

CREATE INDEX IF NOT EXISTS idx_import_issues_import
    ON import_issues(import_id);
"""


def clean_value(value: str) -> str:
    """Collapse whitespace and remove surrounding spaces."""

    return re.sub(r"\s+", " ", value).strip()


def normalize_token(value: str) -> str:
    """Normalize a token for case-insensitive comparisons."""

    return clean_value(value).casefold()


def normalize_definition(value: str) -> str:
    """Normalize a definition for duplicate comparisons."""

    return clean_value(value).casefold()


def calculate_sha256(file_path: Path) -> str:
    """Return the SHA-256 checksum of a source file."""

    digest = hashlib.sha256()

    with file_path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


@contextmanager
def open_database(database_path: Path):
    """
    Open a SQLite connection and always close it.

    SQLite connection context managers commit or roll back transactions,
    but do not guarantee a close. This wrapper is required so Windows
    temporary files and database files are released correctly.
    """

    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()


def initialize_database(database_path: Path) -> None:
    """Create the database and all required tables."""

    with open_database(database_path) as connection:
        connection.executescript(SCHEMA)


def parse_source_line(line: str) -> tuple[str, str]:
    """
    Parse one source line.

    Primary format:
        TOKEN<TAB>Definition

    Fallback format:
        TOKEN<two or more spaces>Definition
    """

    cleaned_line = line.rstrip("\r\n")

    if "\t" in cleaned_line:
        token, definition = cleaned_line.split("\t", 1)
        return clean_value(token), clean_value(definition)

    parts = re.split(r"\s{2,}", cleaned_line, maxsplit=1)

    if len(parts) == 2:
        return clean_value(parts[0]), clean_value(parts[1])

    return clean_value(cleaned_line), ""


def find_existing_import(
    connection: sqlite3.Connection,
    source_sha256: str,
) -> int | None:
    """Return the existing import ID for an identical source file."""

    row = connection.execute(
        """
        SELECT import_id
        FROM source_imports
        WHERE source_sha256 = ?
        """,
        (source_sha256,),
    ).fetchone()

    return int(row[0]) if row else None


def create_import(
    connection: sqlite3.Connection,
    source_path: Path,
    source_sha256: str,
) -> int:
    """Create and return a new import record."""

    imported_at_utc = datetime.now(timezone.utc).isoformat()

    cursor = connection.execute(
        """
        INSERT INTO source_imports (
            source_name,
            source_path,
            source_sha256,
            imported_at_utc
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            source_path.name,
            str(source_path.resolve()),
            source_sha256,
            imported_at_utc,
        ),
    )

    return int(cursor.lastrowid)


def insert_candidate(
    connection: sqlite3.Connection,
    import_id: int,
    source_line: int,
    token: str,
    definition: str,
) -> int:
    """Insert one quarantined legacy candidate row."""

    cursor = connection.execute(
        """
        INSERT INTO candidate_terms (
            import_id,
            source_line,
            raw_token,
            normalized_token,
            raw_definition,
            normalized_definition,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, 'legacy_candidate')
        """,
        (
            import_id,
            source_line,
            token,
            normalize_token(token),
            definition,
            normalize_definition(definition),
        ),
    )

    return int(cursor.lastrowid)


def insert_issue(
    connection: sqlite3.Connection,
    import_id: int,
    issue_type: str,
    severity: str,
    token: str,
    details: str,
    candidate_id: int | None = None,
) -> None:
    """Insert one import-quality issue."""

    connection.execute(
        """
        INSERT INTO import_issues (
            import_id,
            candidate_id,
            issue_type,
            severity,
            token,
            details
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            import_id,
            candidate_id,
            issue_type,
            severity,
            token,
            details,
        ),
    )


def analyze_import(
    connection: sqlite3.Connection,
    import_id: int,
) -> None:
    """Detect missing definitions, duplicates, and definition conflicts."""

    connection.execute(
        """
        DELETE FROM import_issues
        WHERE import_id = ?
        """,
        (import_id,),
    )

    rows = connection.execute(
        """
        SELECT
            candidate_id,
            source_line,
            raw_token,
            normalized_token,
            raw_definition,
            normalized_definition
        FROM candidate_terms
        WHERE import_id = ?
        ORDER BY source_line
        """,
        (import_id,),
    ).fetchall()

    rows_by_token: dict[str, list[sqlite3.Row]] = defaultdict(list)

    for row in rows:
        (
            candidate_id,
            source_line,
            raw_token,
            normalized_token,
            raw_definition,
            normalized_definition,
        ) = row

        if not raw_definition.strip():
            insert_issue(
                connection=connection,
                import_id=import_id,
                candidate_id=int(candidate_id),
                issue_type="missing_definition",
                severity="error",
                token=raw_token,
                details=(
                    f"Source line {source_line} contains token "
                    f"'{raw_token}' with no definition."
                ),
            )

        rows_by_token[normalized_token].append(row)

    for normalized_token, token_rows in rows_by_token.items():
        if len(token_rows) < 2:
            continue

        display_token = token_rows[0][2]

        definition_counts = Counter(
            row[5]
            for row in token_rows
        )

        duplicate_definition_count = sum(
            count - 1
            for count in definition_counts.values()
            if count > 1
        )

        if duplicate_definition_count > 0:
            insert_issue(
                connection=connection,
                import_id=import_id,
                issue_type="duplicate_exact",
                severity="warning",
                token=display_token,
                details=(
                    f"Token '{display_token}' has "
                    f"{duplicate_definition_count} duplicate "
                    "definition record(s)."
                ),
            )

        distinct_definitions = {
            row[5]
            for row in token_rows
            if row[5]
        }

        if len(distinct_definitions) > 1:
            display_definitions = sorted(
                {
                    row[4]
                    for row in token_rows
                    if row[4]
                },
                key=str.casefold,
            )

            insert_issue(
                connection=connection,
                import_id=import_id,
                issue_type="definition_conflict",
                severity="warning",
                token=display_token,
                details=(
                    f"Token '{display_token}' has conflicting "
                    f"definitions: {display_definitions}"
                ),
            )


def build_report(
    connection: sqlite3.Connection,
    import_id: int,
    already_imported: bool,
) -> dict[str, Any]:
    """Create a JSON-serializable report for an import."""

    source_row = connection.execute(
        """
        SELECT
            source_name,
            source_path,
            source_sha256,
            imported_at_utc
        FROM source_imports
        WHERE import_id = ?
        """,
        (import_id,),
    ).fetchone()

    candidate_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM candidate_terms
        WHERE import_id = ?
        """,
        (import_id,),
    ).fetchone()[0]

    issue_rows = connection.execute(
        """
        SELECT
            issue_type,
            severity,
            token,
            details
        FROM import_issues
        WHERE import_id = ?
        ORDER BY issue_type, token
        """,
        (import_id,),
    ).fetchall()

    issue_counts = Counter(
        row[0]
        for row in issue_rows
    )

    return {
        "import_id": import_id,
        "already_imported": already_imported,
        "source": {
            "name": source_row[0],
            "path": source_row[1],
            "sha256": source_row[2],
            "imported_at_utc": source_row[3],
        },
        "candidate_count": candidate_count,
        "status": "legacy_candidate",
        "issue_counts": dict(sorted(issue_counts.items())),
        "issues": [
            {
                "issue_type": row[0],
                "severity": row[1],
                "token": row[2],
                "details": row[3],
            }
            for row in issue_rows
        ],
    }


def import_legacy_source(
    database_path: Path,
    source_path: Path,
) -> dict[str, Any]:
    """
    Import a legacy acronym source into quarantine.

    Imported records are always assigned:
        status = legacy_candidate
    """

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Legacy source file was not found: {source_path}"
        )

    initialize_database(database_path)

    source_sha256 = calculate_sha256(source_path)

    with open_database(database_path) as connection:
        existing_import_id = find_existing_import(
            connection,
            source_sha256,
        )

        if existing_import_id is not None:
            return build_report(
                connection=connection,
                import_id=existing_import_id,
                already_imported=True,
            )

        import_id = create_import(
            connection=connection,
            source_path=source_path,
            source_sha256=source_sha256,
        )

        with source_path.open(
            encoding="utf-8-sig",
            errors="replace",
        ) as source_file:
            for source_line, raw_line in enumerate(
                source_file,
                start=1,
            ):
                if not raw_line.strip():
                    continue

                token, definition = parse_source_line(raw_line)

                if not token:
                    continue

                insert_candidate(
                    connection=connection,
                    import_id=import_id,
                    source_line=source_line,
                    token=token,
                    definition=definition,
                )

        analyze_import(
            connection=connection,
            import_id=import_id,
        )

        connection.commit()

        return build_report(
            connection=connection,
            import_id=import_id,
            already_imported=False,
        )


def write_report(
    report: dict[str, Any],
    report_path: Path,
) -> None:
    """Write the import report as formatted JSON."""

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open("w", encoding="utf-8") as output_file:
        json.dump(
            report,
            output_file,
            indent=2,
            ensure_ascii=False,
        )
        output_file.write("\n")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line options."""

    parser = argparse.ArgumentParser(
        description=(
            "Import a legacy abbreviation list into a quarantined "
            "SQLite candidate registry."
        )
    )

    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to a tab-delimited legacy abbreviation list.",
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data") / "abbreviations.sqlite",
        help=(
            "SQLite database path. "
            "Default: data/abbreviations.sqlite"
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports") / "legacyimportreport.json",
        help=(
            "JSON audit report path. "
            "Default: reports/legacyimportreport.json"
        ),
    )

    return parser.parse_args()


def main() -> int:
    """Run the import command."""

    arguments = parse_arguments()

    try:
        report = import_legacy_source(
            database_path=arguments.database,
            source_path=arguments.source,
        )
        write_report(
            report=report,
            report_path=arguments.report,
        )
    except (FileNotFoundError, OSError, sqlite3.Error) as error:
        print(f"IMPORT FAILED: {error}")
        return 2

    state = (
        "already imported"
        if report["already_imported"]
        else "imported"
    )

    print(
        f"Legacy source {state}: "
        f"{report['source']['name']}"
    )

    print(
        f"Candidates: {report['candidate_count']}"
    )

    print(
        f"Issues: {sum(report['issue_counts'].values())}"
    )

    print(
        f"Report: {arguments.report.resolve()}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
