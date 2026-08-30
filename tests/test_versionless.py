"""A court page whose version table holds one row dated 01/01/0001 is the
current text with an UNPUBLISHED effective date (JT 2026-08-30), not a page
with no versions. ~45 rules had never been captured because the extractor
dropped the sentinel row."""
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from src.scraper.version_history_extractor import VersionHistoryExtractor  # noqa: E402
from src.git.git_version_manager import GitVersionManager, UNPUBLISHED_SUBJECT  # noqa: E402

URL = "https://www.ndcourts.gov/legal-resources/rules/ndrprocr/1"


def page(rows):
    trs = "".join(f"<tr><td>{e}</td><td>{o}</td><td><a href='{h}'>View</a></td></tr>" for e, o, h in rows)
    return f"""<html><body><h1>SECTION 1. STATEMENT OF POLICY</h1>
    <article class="widget-rule-version-history-widget"><table class="table">
    <tr><th>Effective Date</th><th>Obsolete Date</th><th></th></tr>{trs}</table></article></body></html>"""


def test_sentinel_only_row_is_a_dateless_current_version():
    vh = VersionHistoryExtractor().extract_version_history(page([("01/01/0001", "", "/legal-resources/rules/ndrprocr/1")]), URL)
    assert len(vh.versions) == 1
    v = vh.versions[0]
    assert v.effective_date is None and v.date_unpublished and v.is_current
    assert v.url.endswith("/ndrprocr/1")


def test_sentinel_row_dropped_when_dated_rows_exist():
    vh = VersionHistoryExtractor().extract_version_history(
        page([("01/01/0001", "", "/legal-resources/rules/ndrprocr/1-1"),
              ("03/01/2020", "", "/legal-resources/rules/ndrprocr/1")]), URL)
    assert [v.effective_date for v in vh.versions] == [date(2020, 3, 1)]


def test_commit_without_date_uses_marker_subject_and_is_skipped_as_effective_date():
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "init", "-q", d], check=True)
        gm = GitVersionManager(repo_dir=Path(d), author_name="t", author_email="t@x", logger=None)
        assert gm.commit_rule_version("1", "# SECTION 1. STATEMENT OF POLICY\n\nbody\n", None, "SECTION 1.", url=URL, is_current=True)
        log = subprocess.run(["git", "-C", d, "log", "--format=%s%n%b"], capture_output=True, text=True).stdout
        assert f"Rule 1: {UNPUBLISHED_SUBJECT}" in log
        assert "Effective date: not published" in log
        assert gm.get_rule_effective_date("1") is None
        # a later dated commit is the effective date again
        assert gm.commit_rule_version("1", "# SECTION 1.\n\nnew body\n", date(2027, 3, 1), "SECTION 1.", is_current=True)
        assert gm.get_rule_effective_date("1") == date(2027, 3, 1)
