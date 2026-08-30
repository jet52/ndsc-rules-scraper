"""The rule identifier that names a mirror file is read from the LEADING
designator of the page title, never from a rule number mentioned later in it.

Regression for the 2026-08-30 finding: "TABLE A. SPECIAL STATUTORY PROCEEDINGS
UNDER RULE 81" had been filed as Rule 81 (overwriting N.D.R.Civ.P. 81's own
file), "APPENDIX K. RULE 3.5 ELECTRONIC FILING REQUIREMENTS" as Rule 3.5, and
"RULE 8.3.1 ..." as Rule 8.3 (two-level capture).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.scraper.version_history_extractor import VersionHistoryExtractor  # noqa: E402

U = "https://www.ndcourts.gov/legal-resources/rules/{cat}/{slug}"
CASES = [
    # (category, slug, title, expected identifier)
    ("ndrcivp", "81", "RULE 81. APPLICABILITY OF THE RULES IN GENERAL", "81"),
    ("ndrcivp", "Table-A", "TABLE A. SPECIAL STATUTORY PROCEEDINGS UNDER RULE 81", "Table-A"),
    ("ndrcivp", "Table-B", "TABLE B. LIST OF STATUTES SUPERSEDED", "Table-B"),
    ("ndrcivp", "Appendix", "APPENDIX OF FORMS", "Appendix"),
    ("ndrcivp", "84", "RULE 84. APPENDIX OF FORMS", "84"),
    ("ndrct", "2-1", "RULE 2.1 SOMETHING", "2.1"),
    ("ndrct", "8-3", "RULE 8.3 CASE MANAGEMENT (DIVORCE CASES)", "8.3"),
    ("ndrct", "8-3-1", "RULE 8.3.1 CASE MANAGEMENT (DETERMINATION OF PARENTAL RIGHTS)", "8.3.1"),
    ("ndrct", "appendix-k", "APPENDIX K. RULE 3.5 ELECTRONIC FILING REQUIREMENTS", "appendix-k"),
    ("ndrct", "appendix-c", "APPENDIX C. RULE 8.3 INFORMATIONAL STATEMENT", "appendix-c"),
    ("ndrct", "appendix-f", "APPENDIX F. RULE 8.8 ALTERNATIVE DISPUTE RESOLUTION STATEMENT", "appendix-f"),
    ("ndrct", "appendix-a", "APPENDIX A. SUMMONS IN ACTION FOR DIVORCE OR SEPARATION", "appendix-a"),
    ("ndrct", "appendix-a-to-rule-8-9", "APPENDIX A TO RULE 8.9. CODE OF MEDIATION ETHICS", "appendix-a-to-rule-8.9"),
    ("ndrct", "11-10", "RULE 11.10. RELIABLE ELECTRONIC MEANS PROCEEDINGS", "11.10"),
    ("ndrjuvp", "10-2-2", "RULE 10.2. ADMISSIONS", "10.2"),
    ("ndsupctadminr", "46-1-2", "Administrative Rule 46.1 – DUTIES, QUALIFICATIONS, AND EDUCATION", "46.1"),
    ("ndsupctadminr", "58", "VEXATIOUS LITIGATION - Administrative Rule 58", "58"),
    ("ndsupctadminorder", "16", "Administrative Order 16 - ELECTRONIC FILING PILOT PROJECT", "16"),
    ("ndrlawyerdiscipl", "1-2", "RULE 1.2.GROUNDS FOR DISCIPLINE.", "1.2"),
    ("ndrprofconduct", "2-3", "RULE 2.2INTERMEDIARY", "2.2"),
    ("ndstdsimposinglawyersanctions", "1-0", "1.0 Lawyer Discipline Generally", "1-0"),
    ("ndcodejudconduct", "canon-1", "Canon 1", "canon-1"),
    ("ndrprocr", "8", "SECTION 8. STANDING COMMITTEES ON RULES AND ORDERS", "8"),
    ("ndrprocr", "9A", "SECTION 9A. STATE BAR ASSOCIATION OF NORTH DAKOTA", "9A"),
    ("rltdpracticeoflawbylawstudents", "3", "III. ELIGIBILITY REQUIREMENTS", "3"),
    ("ndrappp", "tables", "TABLES", "tables"),
    ("ndrev", "Table", "TABLE OF STATUTES SUPERSEDED", "Table"),
]


@pytest.mark.parametrize("cat,slug,title,expected", CASES, ids=[c[2][:40] for c in CASES])
def test_rule_identifier(cat, slug, title, expected):
    ex = VersionHistoryExtractor()
    assert ex._extract_rule_number(title, U.format(cat=cat, slug=slug)) == expected


def test_subpage_without_leading_designator_is_unknown():
    ex = VersionHistoryExtractor()
    url = "https://www.ndcourts.gov/legal-resources/rules/ndsupctadminr/9/appendix-jury-standards"
    assert ex._extract_rule_number("APPENDIX", url) == "unknown"
