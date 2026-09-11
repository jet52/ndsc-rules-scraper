"""Index links must stay inside the category being fetched.

The Administrative Orders index carries "Revised and Adopted as Rule 21",
whose href is Administrative RULE 21's page. Filing it as Order 21 flipped
ndsupctadminorder/rule-21.md between two documents every run (2026-07..09).
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scraper.rule_link_fetcher import fetch_rule_links  # noqa: E402

INDEX = """
<html><body>
<a href="/legal-resources/rules/ndsupctadminr/21">Revised and Adopted as Rule 21</a>
<a href="/legal-resources/rules/ndsupctadminorder/21">Order 21 - Minority Justice Implementation Committee</a>
<a href="/legal-resources/rules/ndsupctadminorder/9">Order 9</a>
<a href="/legal-resources/rules/ndsupctadminorder/9/appendix-jury-standards">sub-page</a>
<select><option value="/legal-resources/rules/ndsupctadminr/21">Rule 21</option>
<option value="/legal-resources/rules/ndsupctadminorder/12">Order 12</option></select>
</body></html>
"""


def _session(html):
    s = MagicMock()
    r = MagicMock(); r.status_code = 200; r.text = html
    s.get.return_value = r
    return s


def test_cross_category_link_is_ignored():
    links = fetch_rule_links(_session(INDEX),
                             "https://www.ndcourts.gov/legal-resources/rules/ndsupctadminorder",
                             follow_appendix=False)
    urls = sorted(l["url"] for l in links)
    assert urls == [
        "https://www.ndcourts.gov/legal-resources/rules/ndsupctadminorder/12",
        "https://www.ndcourts.gov/legal-resources/rules/ndsupctadminorder/21",
        "https://www.ndcourts.gov/legal-resources/rules/ndsupctadminorder/9",
    ]
    assert {l["rule_number"] for l in links} == {"12", "21", "9"}
    assert all("ndsupctadminr/" not in l["url"] for l in links)


def test_same_category_index_unchanged():
    links = fetch_rule_links(_session(INDEX.replace("ndsupctadminorder", "ndsupctadminr")),
                             "https://www.ndcourts.gov/legal-resources/rules/ndsupctadminr/",
                             follow_appendix=False)
    assert {l["rule_number"] for l in links} == {"21", "9", "12"}
