"""Tests for the flat-run table repairs and appendix-form capture pieces.

The two Table repairs run against fixture copies of the court's flat pages
as the mirror captured them (the upstream pages have been byte-stable since
at least 2005), so these tests double as the round-trip verification of the
actual reconstruction that ships.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scraper.content_repairs import (
    apply_repairs,
    repair_ndrcrimp_table,
    repair_ndrev_table,
    _stripped,
)
from scraper.version_history_extractor import VersionHistoryExtractor

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")

EV_TABLE = os.path.join(FIXTURES, "ndrev-table-flat.md")
CRIMP_TABLE = os.path.join(FIXTURES, "ndrcrimp-table-flat.md")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- ndrev ----

class TestEvTable:
    def test_reconstructs_all_rows(self):
        out = repair_ndrev_table(_read(EV_TABLE))
        rows = [l for l in out.splitlines()
                if l.startswith("|") and "---" not in l and "Section" not in l]
        assert len(rows) == 22
        assert "| 11-26-07 | 408 |" in rows
        # the keyed hyphen repair, confirmed by Rule 601's explanatory note
        assert "| 31-01-01 | 601 |" in rows
        assert "| 31-01-02 | 501, 504 |" in rows
        assert "| 31-11-01 | 301 |" in rows

    def test_round_trip_characters(self):
        src = _read(EV_TABLE)
        out = repair_ndrev_table(src)
        fixed = src.replace("31-01101601", "31-01-01601")
        assert _stripped(out) == _stripped(fixed)

    def test_signature_gate_passes_through_fixed_page(self):
        clean = "# TABLE\n\n| Section | Evidence Rule |\n| 1-01-01 | 101 |\n"
        assert repair_ndrev_table(clean) == clean


# -------------------------------------------------------------- ndrcrimp ----

class TestCrimpTable:
    def test_reconstructs(self):
        out = repair_ndrcrimp_table(_read(CRIMP_TABLE))
        assert out != _read(CRIMP_TABLE)          # repair applied, not passed
        lines = out.splitlines()
        rows = [l for l in lines if l.startswith("|")
                and "---" not in l and "Disposition" not in l]
        assert len(rows) == 589   # 587 section rows + 2 Entire Chapter rows
        assert sum(1 for l in lines if l.startswith("**TITLE")) == 14
        # chapter glue split ("1-011-01-33")
        assert "| 1-01 | 1-01-33 | Considered | 45 |" in rows
        # rule glued to next section ("Considered 451-01-41")
        assert "|  | 1-01-41 | Considered | 32 |" in rows
        # interleaved range/disposition keyed repair
        assert ("|  | 27-10-03 thru 27-10-27 | "
                "Superseded for Criminal Process Only | 42 |" in rows)
        # second disposition -> continuation row
        assert "|  |  | Superseded in part | 23 |" in rows
        # glued word boundaries normalized
        assert ("|  | 29-21-32 | Superseded (except as to Court Reporter's "
                "fees) | 30, 51 |" in rows)
        # source oddities preserved verbatim (no witness to overrule them)
        assert "|  | 22-21-33 | Superseded | 30, 51 |" in rows
        assert "| 12.1-32 | 12.1-32-02(3) | Superseded | 35-1978 |" in rows

    def test_signature_gate_passes_through_fixed_page(self):
        clean = "# Table\n\n| Statute | Rule |\n| 1-01-33 | 45 |\n"
        assert repair_ndrcrimp_table(clean) == clean


# -------------------------------------------------------------- registry ----

def test_apply_repairs_keys_on_url():
    # includes the keyed corruption: a page without it passes through (the
    # guard treats its absence as "page changed upstream")
    flat = "# T\n\nSection Evidence Rule 11-26-07408 31-01101601\n"
    hit = apply_repairs(
        "https://www.ndcourts.gov/legal-resources/rules/ndrev/Table", flat)
    assert "| 11-26-07 | 408 |" in hit
    assert "| 31-01-01 | 601 |" in hit
    miss = apply_repairs(
        "https://www.ndcourts.gov/legal-resources/rules/ndrcivp/Table-A", flat)
    assert miss == flat
    # same content, right URL, corruption absent -> guard passes through
    no_corruption = "# T\n\nSection Evidence Rule 11-26-07408\n"
    assert apply_repairs(
        "https://www.ndcourts.gov/legal-resources/rules/ndrev/Table",
        no_corruption) == no_corruption


# ------------------------------------------------------- form rule numbers ----

def test_form_title_yields_form_number():
    ex = VersionHistoryExtractor()
    assert ex._extract_rule_number(
        "FORM 1. SUMMONS",
        "https://www.ndcourts.gov/legal-resources/rules/ndrcivp/appendix/1",
    ) == "Form-1"


def test_form_url_fallback():
    ex = VersionHistoryExtractor()
    assert ex._extract_rule_number(
        "Untitled Rule",
        "https://www.ndcourts.gov/legal-resources/rules/ndrcrimp/appendix/12",
    ) == "Form-12"


def test_table_a_identity_unchanged():
    ex = VersionHistoryExtractor()
    assert ex._extract_rule_number(
        "TABLE A. SPECIAL STATUTORY PROCEEDINGS UNDER RULE 81",
        "https://www.ndcourts.gov/legal-resources/rules/ndrcivp/Table-A",
    ) == "Table-A"
