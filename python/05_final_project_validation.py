"""Read-only validation for Day 4 portfolio packaging. Run from repository root.

Text scans exclude .git, .venv, raw/processed CSVs, notebooks, binary assets,
and generated caches. This file is excluded from credential scanning so its own
regular expressions cannot be reported as credentials.
"""
from __future__ import annotations

import csv
import math
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROWS = {"fact_orders.csv": 99_441, "fact_order_items.csv": 112_650, "dim_customers.csv": 99_441, "dim_products.csv": 32_951, "dim_sellers.csv": 3_095}
EXPECTED_SQL_QUERY_NAMES = {"overall_order_fulfillment_summary", "monthly_fulfillment_trend", "customer_state_fulfillment_performance", "order_status_distribution", "product_category_commercial_performance", "seller_state_commercial_performance", "customer_repeat_order_summary", "data_quality_and_lifecycle_summary"}
REQUIRED_FILES = ("README.md", "docs/data-quality-report.md", "docs/cleaning-rules.md", "docs/power-bi-model-spec.md", "docs/dax-measures.md", "docs/dashboard-guide.md", "docs/sql-analysis.md", "docs/business-recommendations.md", "docs/project-reproduction-guide.md", "python/03_power_bi_validation.py", "python/04_sql_analysis.py", "python/05_final_project_validation.py", "sql/01_analysis_views.sql", "sql/02_business_queries.sql", "testing/test_sql_analysis.py", "dashboard/screenshots/overview.png", "dashboard/screenshots/product-seller.png", ".gitignore")
HEADLINE_METRICS = ("99,441", "96,478", "96,470", "89,936", "6,534", "93.23%", "12.56", "10.62", "112,650", "R$13,591,643.70", "R$2,251,909.54", "2,997", "96,096", "3.12%", "81.04%", "78.59%", "2016-09", "2018-10")
TEXT_SUFFIXES = {".md", ".py", ".sql", ".txt", ".json", ".yml", ".yaml", ".toml", ".ini", ".env"}
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".ipynb_checkpoints", "data/raw", "data/processed"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
EXPECTED_SCREENSHOTS = {"dashboard/screenshots/overview.png", "dashboard/screenshots/product-seller.png"}
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(\s*(<[^>\n]+>|[^\s)]+)(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^\n)]*\)))?\s*\)")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(\s*(<[^>\n]+>|[^\s)]+)(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^\n)]*\)))?\s*\)")
SECRET_RULES = {
    "private-key-header": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github-personal-access-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "credential-assignment": re.compile(r"(?im)^\s*(?:export\s+)?(?:[A-Za-z_][\w.-]*?)?(?:api[_-]?key|password|secret|token)[\w.-]*\s*(?:=|:)\s*(?:\"[^\"\r\n]{6,}\"|'[^'\r\n]{6,}'|[A-Za-z0-9_./+=-]{12,})\s*$"),
    "credentialed-database-url": re.compile(r"\b(?:postgres(?:ql)?|mysql|mssql|mongodb(?:\+srv)?|redis)://[^/\s:@]+:[^@\s]+@", re.I),
}
CLAIM_RULES = {
    "Samator reference": re.compile(r"\bsamator\b", re.I),
    "Olist affiliation claim": re.compile(r"\baffiliated\s+with\s+olist\b|\bofficial\s+olist\s+project\b", re.I),
    "Olist employment or client claim": re.compile(r"\bworked\s+(?:for|with)\s+olist\b|\bolist\s+(?:client|employees?|stakeholders?)\b", re.I),
    "stakeholder interview claim": re.compile(r"\binterview(?:ed|s?)\s+(?:olist\s+)?(?:staff|employees?|stakeholders?)\b|\binterviews?\s+with\s+(?:olist\s+)?(?:staff|employees?|stakeholders?)\b|\bstakeholder\s+interviews?\b", re.I),
    "real-stakeholder requirements claim": re.compile(r"\brequirements?\s+(?:were\s+)?gathered\s+from\s+(?:real\s+)?stakeholders?\b", re.I),
}
DENIAL_RE = re.compile(r"\b(?:not\s+affiliated\s+with\s+olist|no\s+interviews?\s+were\s+conducted|no\s+(?:real\s+)?stakeholder\s+access|did\s+not\s+(?:interview|work\s+(?:for|with))|without\s+(?:stakeholder|employee)\s+interviews?)\b", re.I)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def finding(path: Path, line: int, rule: str, root: Path) -> str:
    try:
        name = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        name = path.name
    return f"{name}:{line}: {rule}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def git_check_ignored(relative_path: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", "--", relative_path], cwd=ROOT, check=False).returncode == 0


def is_text_scan_candidate(path: Path, root: Path) -> bool:
    relative = path.relative_to(root).as_posix()
    if any(relative == item or relative.startswith(f"{item}/") for item in EXCLUDED_PARTS):
        return False
    name = path.name.lower()
    return path.suffix.lower() in TEXT_SUFFIXES or name.startswith(".env") or ".env." in name


def scan_secret_findings(root: Path) -> list[str]:
    """Return only file, line, and rule; never print a potential credential."""
    results: list[str] = []
    self_path = Path(__file__).resolve()
    for path in root.rglob("*"):
        if not path.is_file() or path.resolve() == self_path or not is_text_scan_candidate(path, root):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            for rule, pattern in SECRET_RULES.items():
                if pattern.search(line):
                    results.append(finding(path, number, rule, root))
    return results


def local_destination(destination: str, markdown_path: Path, root: Path, kind: str) -> Path | None:
    destination = unquote(destination.strip())
    parsed = urlparse(destination)
    if parsed.scheme in {"http", "https"}:
        require(bool(parsed.netloc), f"{kind} has invalid remote URL")
        return None
    require(parsed.scheme != "file", f"{kind} uses forbidden file:// destination")
    require(not parsed.scheme and not destination.startswith(("/", "\\")) and not re.match(r"^[A-Za-z]:[\\/]", destination), f"{kind} uses an absolute local path")
    text = destination.split("#", 1)[0].split("?", 1)[0]
    require(bool(text), f"{kind} has an empty local destination")
    target = (markdown_path.parent / text).resolve()
    require(target.is_relative_to(root.resolve()), f"{kind} escapes the repository root")
    return target


def parse_markdown_images(markdown_path: Path, root: Path) -> set[str]:
    text = markdown_path.read_text(encoding="utf-8")
    matches = list(IMAGE_RE.finditer(text))
    starts = {match.start() for match in matches}
    for malformed in re.finditer(r"!\[", text):
        require(malformed.start() in starts, f"Malformed Markdown image syntax in {markdown_path.name}")
    embedded: set[str] = set()
    for match in matches:
        alt, destination = match.group(1).strip(), match.group(2).strip("<>")
        target = local_destination(destination, markdown_path, root, "Markdown image")
        if target is None:
            continue
        require(target.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS, "Markdown image has unsupported extension")
        require(target.is_file() and target.stat().st_size > 0, "Markdown image is missing or empty")
        relative = target.relative_to(root.resolve()).as_posix()
        if relative in EXPECTED_SCREENSHOTS:
            require(bool(alt), f"Dashboard screenshot has empty alt text: {relative}")
        embedded.add(relative)
    require(EXPECTED_SCREENSHOTS.issubset(embedded), "Required dashboard screenshots must be Markdown image embeds, not path text")
    return embedded


def validate_markdown_links(markdown_path: Path, root: Path) -> None:
    for match in LINK_RE.finditer(markdown_path.read_text(encoding="utf-8")):
        destination = match.group(2).strip("<>")
        if destination.startswith("#") or urlparse(destination).scheme in {"http", "https"}:
            continue
        target = local_destination(destination, markdown_path, root, "Markdown link")
        if target is not None:
            require(target.exists(), "Markdown link target is missing")


def scan_claim_findings(paths: list[Path], root: Path) -> list[str]:
    results: list[str] = []
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            normalized = " ".join(line.split())
            if DENIAL_RE.search(normalized):
                continue
            for rule, pattern in CLAIM_RULES.items():
                if pattern.search(normalized):
                    results.append(finding(path, number, rule, root))
    return results


def validate_sql_query_labels(sql_text: str) -> None:
    labels = re.findall(r"(?m)^-- QUERY: ([a-z0-9_]+)$", sql_text)
    require(len(labels) == 8, f"SQL query label count must be exactly eight, found {len(labels)}")
    require(len(set(labels)) == len(labels), "SQL query labels must be unique")
    require(set(labels) == EXPECTED_SQL_QUERY_NAMES, "SQL query labels do not match the required eight names")


def validate_files_and_data() -> None:
    for path in REQUIRED_FILES:
        require((ROOT / path).is_file(), f"Required file is missing: {path}")
    tables = {name: read_csv(ROOT / "data/processed" / name) for name in EXPECTED_ROWS}
    for name, expected in EXPECTED_ROWS.items():
        require(len(tables[name]) == expected, f"Unexpected row count in {name}: expected {expected:,}")
    orders, items = tables["fact_orders.csv"], tables["fact_order_items.csv"]
    require(len({row["order_id"] for row in orders}) == len(orders), "fact_orders.order_id is not unique")
    require(len({(row["order_id"], row["order_item_id"]) for row in items}) == len(items), "fact_order_items composite key is not unique")
    for filename, key in (("dim_customers.csv", "customer_id"), ("dim_products.csv", "product_id"), ("dim_sellers.csv", "seller_id")):
        values = [row[key] for row in tables[filename]]
        require(len(set(values)) == len(values) and all(values), f"{filename}.{key} is not unique and non-empty")
    classified = [row for row in orders if row["delivery_classification"] in {"On Time", "Late"}]
    on_time, late = [row for row in classified if row["delivery_classification"] == "On Time"], [row for row in classified if row["delivery_classification"] == "Late"]
    lead = [float(row["total_lead_time_days"]) for row in orders if row["total_lead_time_days"]]
    delays = [float(row["delay_days"]) for row in late if row["delay_days"]]
    repeats: dict[str, int] = {}
    for row in orders:
        if row["customer_unique_id"]:
            repeats[row["customer_unique_id"]] = repeats.get(row["customer_unique_id"], 0) + 1
    march = [row for row in orders if row["purchase_year_month"] == "2018-03" and row["delivery_classification"] in {"On Time", "Late"}]
    al = [row for row in orders if row["customer_state"] == "AL" and row["delivery_classification"] in {"On Time", "Late"}]
    checks = ((len(orders) == 99_441, "total orders changed"), (sum(row["order_status"] == "delivered" for row in orders) == 96_478, "delivered orders changed"), (len(classified) == 96_470 and len(on_time) == 89_936 and len(late) == 6_534, "delivery classification counts changed"), (math.isclose(len(on_time) / len(classified), .9323, abs_tol=.00005), "on-time delivery rate changed"), (math.isclose(sum(lead) / len(lead), 12.56, abs_tol=.005), "average lead time changed"), (math.isclose(sum(delays) / len(delays), 10.62, abs_tol=.005), "average late delay changed"), (len(items) == 112_650, "total items changed"), (math.isclose(sum(float(row["price"]) for row in items if row["price"]), 13_591_643.70, abs_tol=1e-6), "merchandise value changed"), (math.isclose(sum(float(row["freight_value"]) for row in items if row["freight_value"]), 2_251_909.54, abs_tol=1e-6), "freight value changed"), (len(repeats) == 96_096 and sum(value > 1 for value in repeats.values()) == 2_997, "repeat-customer counts changed"), (math.isclose(sum(value > 1 for value in repeats.values()) / len(repeats), .0312, abs_tol=.00005), "repeat-customer rate changed"), (len(march) == 7_003 and math.isclose(sum(row["delivery_classification"] == "On Time" for row in march) / len(march), .8104, abs_tol=.00005), "March 2018 rate changed"), (len(al) == 397 and math.isclose(sum(row["delivery_classification"] == "On Time" for row in al) / len(al), .7859, abs_tol=.00005), "AL rate changed"))
    for passed, message in checks:
        require(passed, message)


def validate_documentation() -> None:
    readme_path, rec_path = ROOT / "README.md", ROOT / "docs/business-recommendations.md"
    readme, recommendations = readme_path.read_text(encoding="utf-8"), rec_path.read_text(encoding="utf-8")
    for section in ("Executive summary", "Business problem and objectives", "Analytical questions", "Tools and technologies", "Repository structure", "Analytical data model", "Order grain versus item grain", "Data-quality controls", "Key findings", "Recommendations", "Dashboard", "Reproducibility", "Limitations", "Skills demonstrated"):
        require(section in readme, f"README section missing: {section}")
    parse_markdown_images(readme_path, ROOT)
    validate_markdown_links(readme_path, ROOT)
    for metric in HEADLINE_METRICS:
        require(metric in readme, f"README headline metric missing: {metric}")
        require(metric in recommendations, f"Recommendations headline metric missing: {metric}")
    docs = [readme_path, *(ROOT / "docs").glob("*.md")]
    text = "\n".join(path.read_text(encoding="utf-8") for path in docs)
    require(not re.search(r"[A-Za-z]:\\(?:Users|Documents and Settings)\\", text, re.I), "Documentation contains a personal Windows path")
    claims = scan_claim_findings(docs, ROOT)
    require(not claims, "Unsupported portfolio claim(s): " + "; ".join(claims))


def validate_project_controls() -> None:
    secrets = scan_secret_findings(ROOT)
    require(not secrets, "Potential credential(s) found: " + "; ".join(secrets))
    for image in EXPECTED_SCREENSHOTS:
        require((ROOT / image).stat().st_size > 0, f"Dashboard screenshot is empty: {image}")
    require(git_check_ignored("data/raw/example.csv"), "Raw CSV ignore rule is not effective")
    require(git_check_ignored("data/processed/example.csv"), "Processed CSV ignore rule is not effective")
    require(git_check_ignored("example.pbix"), "PBIX ignore rule is not effective")
    require(not [path for suffix in ("*.db", "*.sqlite", "*.sqlite3") for path in ROOT.rglob(suffix)], "Persistent SQLite database file(s) found")
    validate_sql_query_labels((ROOT / "sql/02_business_queries.sql").read_text(encoding="utf-8"))
    test = ROOT / "testing/test_sql_analysis.py"
    require(test.is_file() and "unittest" in test.read_text(encoding="utf-8"), "SQL tests are not discoverable")


def main() -> int:
    require(Path.cwd().resolve() == ROOT, "Run this script from the repository root")
    validate_files_and_data(); validate_documentation(); validate_project_controls()
    print("Final project validation: PASS")
    print("Validated: data, portfolio documentation, Markdown paths, credentials, ignore rules, SQL query identity, and SQL tests.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.SubprocessError) as error:
        print(f"Final project validation: FAIL - {error}", file=sys.stderr)
        raise SystemExit(1)
