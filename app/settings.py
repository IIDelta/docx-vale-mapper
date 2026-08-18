from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REGRESSION_TEST_RUNNER = (
    PROJECT_ROOT / "tests" / "runregressiontests.py"
)

ABBREVIATION_POLICY_PATH = (
    PROJECT_ROOT / "config" / "abbreviationpolicy.json"
)

ABBREVIATION_DATABASE_PATH = (
    PROJECT_ROOT / "data" / "abbreviations.sqlite"
)

SCIENTIFIC_TERMS_PATH = (
    PROJECT_ROOT / "config" / "scientificterms.json"
)

HEADING_TERMS_PATH = (
    PROJECT_ROOT / "config" / "headingterms.json"
)

UNIT_STYLES_PATH = (
    PROJECT_ROOT / "config" / "unitstyles.json"
)
