"""The explanatory-note slicer and sidecar (2026-11-02, replacing the Haiku
commit-body step). Every expectation here is a shape observed on a live
ndcourts.gov page: N.D.R.Civ.P. 12, N.D.R.Ev. 702/601, N.D.R.App.P. 28,
N.D.R.Ct. 3.1, N.D. Sup. Ct. Admin. R. 52, N.D.R. Lawyer Discipl. 4.5."""
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from src.scraper import explanatory_notes as xn  # noqa: E402
from src.scraper.commit_message_builder import CommitMessageBuilder  # noqa: E402
from src.git.git_version_manager import GitVersionManager, NOTES_SUBJECT  # noqa: E402


RULE12 = """Rule 12 was amended, effective 1971; January 27, 1977; March 1, 1990; March 1, 2002 ; September 1, 2004 ; March 1, 2007 ; March 1, 2008 ; March 1, 2011 .

This rule is derived from Fed.R.Civ.P. 12.

Rule 12 was amended, effective March 1, 2011 , in response to the December 1, 2007, revision of the Federal Rules of Civil Procedure. The language and organization of the rule were changed.

Subdivision (a) was amended, effective March 1, 2007 , to delete a reference to service of a summons without a complaint.

Paragraph (a)(1) was amended, effective March 1, 2011 , to increase the time to serve a responsive pleading from 20 to 21 days.

Subdivision (b) was amended, effective March 1, 2002 , to incorporate a time limitation for an objection to improper venue.

SOURCES: Joint Procedure Committee Minutes of April 29-30, 2010, pages 9-10; April 24-25, 2008, pages 6-8; January 24, 2008, pages 17-18; April 26-27, 2007, pages 14-15;September 28-29, 2000, page 8; Fed.R.Civ.P. 12.

STATUTES AFFECTED:

SUPERSEDED: N.D.C.C. §§ 28-05-01, 28-05-02.

CROSS REFERENCE: N.D.R.Civ.P. 4 (Persons Subject to Jurisdiction), N.D.R.Civ.P. 7 (Pleadings Allowed)."""

RULE28 = """Rule 28 was amended, effective March 1, 1986; March 1, 2003 ; March 1, 2010 ; March 1, 2019 ; June 1, 2025.

Under paragraph (b) (4), each legal issue should be stated as a question of law.

Subdivision (b):

Paragraphs (1) and (2) were amended, effective March 1, 2003 , to separate the table of contents and the table of authorities.

Paragraph (7) was amended, effective March 1, 2010 , to require a party to brief the appropriateness of a certification.

Subdivision (h) was amended, effective March 1, 2019 , to require a party to request oral argument.\xa0Subdivision (h) was amended, effective June 1, 2025, to remove the requirement.

SOURCES: Joint Procedure Committee Minutes of September 12, 2025, pages 7-8;\xa0April 29-30, 2010 , pages 23-24."""


# ---- slicing ------------------------------------------------------------------

def test_slice_keeps_only_paragraphs_naming_the_date_verbatim():
    out = xn.slice_for_date(RULE12, date(2011, 3, 1))
    assert out.startswith("Rule 12 was amended, effective March 1, 2011 , in response")
    assert "Paragraph (a)(1) was amended, effective March 1, 2011 , to increase the time" in out
    # not the opening list, not another version's paragraph, not the trailers
    assert "effective 1971" not in out
    assert "Subdivision (a) was amended, effective March 1, 2007" not in out
    assert "SOURCES" not in out and "CROSS REFERENCE" not in out
    assert "derived from Fed.R.Civ.P. 12" not in out   # undated commentary is not filler


def test_slice_tolerates_the_courts_spacing_and_zero_padding():
    # "March 1, 2002 ;" on the page; date(2002, 3, 1) formats as "March 01" elsewhere
    out = xn.slice_for_date(RULE12, date(2002, 3, 1))
    assert out == ("Subdivision (b) was amended, effective March 1, 2002 , to incorporate "
                   "a time limitation for an objection to improper venue.")


def test_date_listed_but_undescribed_says_so():
    out = xn.slice_for_date(RULE12, date(2008, 3, 1))
    assert out == ("The court's explanatory note lists March 1, 2008 as an amendment "
                   "date but describes no change for it.")


def test_date_absent_from_the_note_says_so():
    out = xn.slice_for_date(RULE12, date(1999, 3, 1))
    assert out == "No paragraph in the court's explanatory note is dated March 1, 1999."


def test_year_only_amendment_claims_only_a_january_first_version():
    notes = "Rule 9 was amended, effective 1971; March 1, 2011.\n\nSubdivision (a) was amended, effective 1971, to drop the oath."
    assert "drop the oath" in xn.slice_for_date(notes, date(1971, 1, 1))
    assert "No paragraph" in xn.slice_for_date(notes, date(1971, 3, 1))


def test_empty_note_and_dateless_version_have_fixed_sentences():
    assert xn.slice_for_date("", date(2020, 3, 1)) == "The court's page carries no explanatory note."
    assert xn.slice_for_date(RULE12, None).startswith("The court publishes no effective date")


def test_label_paragraph_rides_with_a_hit_beneath_it_once():
    out = xn.slice_for_date(RULE28, date(2003, 3, 1))
    assert out.startswith("Subdivision (b):\n\nParagraphs (1) and (2) were amended")
    assert out.count("Subdivision (b):") == 1
    # a label with no hit beneath it is not emitted
    assert "Subdivision (b):" not in xn.slice_for_date(RULE28, date(2019, 3, 1))


def test_two_changes_in_one_paragraph_serve_both_versions():
    para = "Subdivision (h) was amended, effective March 1, 2019"
    assert para in xn.slice_for_date(RULE28, date(2019, 3, 1))
    assert para in xn.slice_for_date(RULE28, date(2025, 6, 1))


def test_incidental_dates_do_not_attribute_a_paragraph():
    # "in response to the December 1, 2007, revision of the Federal Rules"
    assert xn.slice_for_date(RULE12, date(2007, 12, 1)) == (
        "No paragraph in the court's explanatory note is dated December 1, 2007.")
    assert xn.names_date("Rule 4.5 was adopted January 1, 1995, amended effective July 1, 1999.", date(1995, 1, 1))
    assert xn.names_date("Former [Rule 11.7](https://x) renumbered effective March 1, 2025.", date(2025, 3, 1))


def test_nbsp_is_whitespace():
    assert "\xa0" not in xn.slice_for_date(RULE28, date(2019, 3, 1))


def test_amendment_list_detection_on_observed_openings():
    assert xn.is_amendment_list("Rule 702 was amended, effective March 1, 2007 ; March 1, 2014 .")
    assert xn.is_amendment_list("This rule was adopted effective May 1, 2005. Amended effective June 1, 2005; March 1, 2015; March 1, 2019 ; March 1, 2024.")
    assert xn.is_amendment_list("Rule 4.5 was adopted January 1, 1995, amended effective July 1, 1999 ; March 1, 2017 .")
    assert xn.is_amendment_list("Rule 601 was amended, effective March 1, 2014 .")
    # a change paragraph is not a list, even when it opens with the rule
    assert not xn.is_amendment_list("Rule 12 was amended, effective March 1, 2011 , in response to the December 1, 2007, revision.")
    assert not xn.is_amendment_list("The content of Rule 52 was transferred to N.D.R.Ct. 11.10, effective September 1, 2026.")


def test_transfer_sentence_survives_for_the_transfer_date():
    notes = ("This rule was adopted effective May 1, 2005. Amended effective March 1, 2015.\n\n"
             "The content of Rule 52 was transferred to N.D.R.Ct. 11.10, effective September 1, 2026.")
    assert xn.slice_for_date(notes, date(2026, 9, 1)) == (
        "The content of Rule 52 was transferred to N.D.R.Ct. 11.10, effective September 1, 2026.")


# ---- SOURCES -----------------------------------------------------------------

def test_sources_entries_parse_dates_ranges_pages_and_others():
    entries = xn.sources_entries(RULE12)
    dated = [e for e in entries if e["date"]]
    assert dated[0]["date"] == date(2010, 4, 29) and dated[0]["end"] == date(2010, 4, 30)
    assert dated[0]["pages"] == "9-10"
    assert dated[2]["date"] == date(2008, 1, 24) and dated[2]["end"] is None
    assert dated[2]["pages"] == "17-18"
    # ";September 28-29, 2000, page 8" — no space after the semicolon
    assert any(e["date"] == date(2000, 9, 28) and e["pages"] == "8" for e in entries)
    assert all(e["committee"] == "Joint Procedure Committee" for e in dated)
    assert entries[-1] == {"raw": "Fed.R.Civ.P. 12", "date": None, "end": None, "pages": None,
                           "committee": None}


def test_committee_name_in_either_word_order():
    a = xn.sources_entries("SOURCES: Minutes of Joint Procedure Committee of April 26-27, 2012, pages 30-31; September 22-23, 2005, pages 2-6; Fed.R.Ev. 702.")
    assert [e["committee"] for e in a] == ["Joint Procedure Committee", "Joint Procedure Committee", None]
    assert a[1]["pages"] == "2-6"


def test_label_scope_closes_at_a_same_rank_unit():
    notes = ("Rule 28 was amended, effective March 1, 2003.\n\n"
             "Subdivision (b):\n\n"
             "Paragraph (7) was amended, effective March 1, 2010 , to require briefing.\n\n"
             "Subdivision (c) was amended, effective March 1, 2003 , to conform.")
    out = xn.slice_for_date(notes, date(2003, 3, 1))
    assert out == "Subdivision (c) was amended, effective March 1, 2003 , to conform."


def test_sources_window_is_prev_exclusive_effective_inclusive():
    win = xn.sources_in_window(RULE12, date(2011, 3, 1), date(2008, 3, 1))
    assert [e["date"] for e in win] == [date(2010, 4, 29), date(2008, 4, 24)]
    first = xn.sources_in_window(RULE12, date(2002, 3, 1), None)
    assert [e["date"] for e in first] == [date(2000, 9, 28)]
    assert xn.sources_in_window(RULE12, None, None) == []


def test_sources_header_without_colon():
    notes = "SOURCES Joint Procedure Committee Minutes of April 24, 2026, pages 6-7; April 28, 2023, page 13."
    assert [e["date"] for e in xn.sources_entries(notes)] == [date(2026, 4, 24), date(2023, 4, 28)]


# ---- commit body ---------------------------------------------------------------

def test_commit_body_is_header_slice_and_minutes_without_a_model():
    body = CommitMessageBuilder().build_message(
        rule_number="12", rule_title="RULE 12. DEFENSES", effective_date=date(2011, 3, 1),
        explanatory_notes=RULE12, is_current=True,
        url="https://www.ndcourts.gov/legal-resources/rules/ndrcivp/12",
        prev_effective_date=date(2008, 3, 1))
    lines = body.splitlines()
    assert lines[0] == "RULE 12. DEFENSES"
    assert lines[1] == "Source: https://www.ndcourts.gov/legal-resources/rules/ndrcivp/12"
    assert lines[2] == "Status: current"
    assert "Explanatory Notes:" in lines
    assert "Paragraph (a)(1) was amended, effective March 1, 2011 , to increase the time to serve a responsive pleading from 20 to 21 days." in lines
    assert "  - Joint Procedure Committee Minutes of April 29-30, 2010, pages 9-10" in lines
    assert "  - April 24-25, 2008, pages 6-8" in lines
    assert "January 24, 2008" not in body   # before the window


# ---- sidecar -------------------------------------------------------------------

def test_sidecar_roundtrip_and_path():
    text = xn.render_sidecar("RULE 702. TESTIMONY BY EXPERT WITNESSES",
                             "https://www.ndcourts.gov/legal-resources/rules/ndrev/702",
                             "Rule 702 was amended, effective March 1, 2007 ; March 1, 2014 .\n\nRule 702 states the general rule.")
    assert text.startswith("# Explanatory Notes — RULE 702. TESTIMONY BY EXPERT WITNESSES\n\nSource: https://")
    title, url, notes = xn.parse_sidecar(text)
    assert title == "RULE 702. TESTIMONY BY EXPERT WITNESSES"
    assert url.endswith("/ndrev/702")
    assert notes == "Rule 702 was amended, effective March 1, 2007 ; March 1, 2014 .\n\nRule 702 states the general rule."
    assert xn.sidecar_relpath("702", "ndrev") == "ndrev/notes/rule-702.md"
    assert xn.sidecar_relpath("6.1") == "notes/rule-6.1.md"


def test_empty_note_renders_header_only_sidecar():
    text = xn.render_sidecar("RULE 1.5. FEES", "https://x/ndrprofconduct/1-5", "")
    assert xn.parse_sidecar(text) == ("RULE 1.5. FEES", "https://x/ndrprofconduct/1-5", "")


def test_git_manager_commits_sidecars_in_one_observation_dated_commit(tmp_path):
    repo = tmp_path / "mirror"
    gm = GitVersionManager(repo_dir=str(repo), category_prefix="ndrev")
    gm.initialize_repository("Rules of Evidence")
    changes = [("702", xn.render_sidecar("RULE 702.", "https://x/702", "Rule 702 was amended, effective March 1, 2014 ."), "https://x/702"),
               ("601", xn.render_sidecar("RULE 601.", "https://x/601", "Rule 601 was amended, effective March 1, 2014 ."), "https://x/601")]
    assert gm.commit_notes(changes, category_label="ndrev")
    assert (repo / "ndrev/notes/rule-702.md").exists()
    assert gm.get_notes_content("601").startswith("# Explanatory Notes — RULE 601.")
    log = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%s%n%b"],
                         capture_output=True, text=True).stdout
    assert log.splitlines()[0] == f"{NOTES_SUBJECT}: 2 rules updated (ndrev)"
    assert "Rule 702 — https://x/702" in log
    # the sidecar never touches a rule file, so the rule's effective date is untouched
    assert gm.get_rule_effective_date("702") is None
    assert gm.get_notes_content("9999") is None
