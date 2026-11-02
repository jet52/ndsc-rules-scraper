"""
Explanatory-note handling for ND Court Rules — deterministic, no model.

The court publishes one cumulative explanatory note per rule (the collapsible
"Explanatory Notes" block on the rule's page). It is a dated changelog in
prose: an opening line listing every amendment date, a paragraph per change
("Subdivision (b) was amended, effective March 1, 2011, to ..."), then a
SOURCES paragraph (committee minutes by meeting date and page), a STATUTES
AFFECTED block, and a CROSS REFERENCE paragraph.

Two consumers:

* the **sidecar** — the whole note, verbatim, stored beside the rule as
  ``<category>/notes/rule-<n>.md`` so git versions it as the court appends to
  it (``render_sidecar`` / ``parse_sidecar``);
* the **commit body** — the paragraphs of the note that name ONE version's
  effective date, verbatim (``slice_for_date``), plus the committee meetings
  the SOURCES paragraph dates to that version's window (``sources_in_window``).

Nothing here paraphrases. Where the note has no paragraph for a date, the
body says so in a fixed sentence instead of pasting undated commentary as if
it explained the change. Until 2026-11-02 a Claude Haiku call did this
slicing (and summarized minutes), with a regex trim as the no-API-key
fallback; the model path was removed because it rewrote primary text and the
cumulative note it worked from was never kept.
"""

from __future__ import annotations

import re
from datetime import date
from typing import List, Optional, Tuple

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")
_MONTH_ALT = "|".join(MONTHS)

# "March 1, 2011", "September 29-30, 2016", with the court's loose spacing
# ("March 1, 2011 ," / "March 1 , 2011" / nbsp).
DATE_RE = re.compile(
    rf"\b({_MONTH_ALT})\s+(\d{{1,2}})(?:\s*[-–]\s*\d{{1,2}})?\s*,\s*(\d{{4}})\b")

# Trailer paragraphs — never version-specific, never sliced.
SOURCES_RE = re.compile(r"^\s*SOURCES?\b", re.I)
STATUTES_AFFECTED_RE = re.compile(r"^\s*STATUTES?\s+AFFECTED\b", re.I)
AFFECTED_SUB_RE = re.compile(
    r"^\s*(SUPERSEDED|CONSIDERED|REPEALED|AFFECTED|AMENDED)\s*:")
CROSS_REF_RE = re.compile(r"^\s*CROSS[\s-]*REFERENCES?\s*:?", re.I)

# "Subdivision (b):" — a bare label the court uses to group the paragraphs
# that follow it (N.D.R.App.P. 28). Carried along with any hit beneath it;
# its scope ends at the next paragraph that opens with a unit of the same or
# a higher rank ("Subdivision (c) was amended ..." closes "Subdivision (b):").
LABEL_RE = re.compile(r"^\s*\S[^.:]{0,60}:\s*$")
_UNIT_RANK = {"rule": 0, "section": 1, "subdivision": 1, "subsection": 2,
              "paragraph": 2, "subparagraph": 3, "clause": 3, "item": 3}
_UNIT_HEAD_RE = re.compile(
    r"^\s*(?:(?:A\s+)?new\s+|former\s+)?"
    r"(rule|sections?|subdivisions?|subsections?|paragraphs?|subparagraphs?|"
    r"clauses?|items?)\b", re.I)

# The opening paragraph: "<Rule N> was amended, effective D; D; D." or
# "This rule was adopted effective D. Amended effective D; D." Dates only,
# no explanatory clause — a change paragraph says what the change did.
_LIST_VERB = (r"(?:was|were)?\s*(?:adopted|amended|approved|revised|"
              r"reorganized|rescinded|repealed|effective|was|were|and|in|\d{4}|"
              r"Amended|Adopted|Effective|Approved|The\s+explanatory\s+notes?|"
              r",|;|\.|\s)*")
_LIST_HEAD = (r"(?:(?:Rule|Standard|Canon|Section|Order|Form|Table|Appendix|"
              r"Administrative\s+(?:Rule|Order)|This\s+\w+)\s+\S*\s*)?")
AMENDMENT_LIST_RE = re.compile(rf"^{_LIST_HEAD}{_LIST_VERB}$", re.I)

NBSP = "\xa0"


def normalize(text: str) -> str:
    """nbsp → space; collapse runs of spaces/tabs (newlines kept)."""
    text = text.replace(NBSP, " ")
    return re.sub(r"[ \t]+", " ", text)


def paragraphs(notes: str) -> List[str]:
    """Blank-line-separated paragraphs, stripped, empties dropped."""
    return [p.strip() for p in re.split(r"\n\s*\n", normalize(notes or ""))
            if p.strip()]


_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def strip_links(text: str) -> str:
    """Markdown links → their text. The sidecar keeps the court's links (a
    dated entry in the opening line links to that version's page); the
    classifier reads the words only."""
    return _MD_LINK_RE.sub(r"\1", text)


def is_amendment_list(para: str) -> bool:
    """True for the opening dates-only line (see AMENDMENT_LIST_RE)."""
    para = strip_links(para)
    if not DATE_RE.search(para) and not re.search(r"\beffective\s+\d{4}\b", para):
        return False
    stripped = DATE_RE.sub(" ", para)
    return bool(AMENDMENT_LIST_RE.match(stripped.strip()))


def is_trailer(para: str) -> bool:
    return bool(SOURCES_RE.match(para) or STATUTES_AFFECTED_RE.match(para)
                or AFFECTED_SUB_RE.match(para) or CROSS_REF_RE.match(para))


def unit_rank(para: str) -> Optional[int]:
    """0 rule, 1 section/subdivision, 2 subsection/paragraph, 3 below; None
    when the paragraph does not open with a unit word."""
    m = _UNIT_HEAD_RE.match(para)
    if not m:
        return None
    return _UNIT_RANK[m.group(1).lower().rstrip("s")]


# A paragraph names a version's date only where an action word introduces
# it ("amended, effective March 1, 2011"; "adopted January 1, 1995"). Other
# dates are something else's — "in response to the December 1, 2007,
# revision of the Federal Rules" — and must not attribute the paragraph.
_ANCHOR = (r"\b(?:effective|adopted|approved|amended|renumbered|rescinded|repealed|"
           r"added|deleted|transferred|superseded|abrogated|revised|reorganized|"
           r"redesignated|moved|relettered)\s+(?:on\s+|in\s+|as\s+of\s+)?")


def date_pattern(d: date) -> re.Pattern:
    """Matches this date as the court prints it, zero-padded or not, with
    its loose spacing, introduced by an action word; a range's FIRST day
    counts ("September 29-30, 2016")."""
    return re.compile(
        _ANCHOR + rf"{MONTHS[d.month - 1]}\s+0?{d.day}(?:\s*[-–]\s*\d{{1,2}})?\s*,\s*{d.year}\b")


def year_only_pattern(d: date) -> re.Pattern:
    """'effective 1971' — the court's form for the oldest amendments, which
    carry no month or day. Only a January-1 version date can claim one."""
    return re.compile(rf"\beffective\s+(?:in\s+)?{d.year}\b(?!\s*[-–,]\s*\d)")


def names_date(para: str, d: date, *, anchored: bool = True) -> bool:
    """``anchored`` (the default) requires an action word before the date;
    the opening amendment-date list is read unanchored."""
    para = strip_links(para)
    pat = date_pattern(d) if anchored else _bare_date_pattern(d)
    if pat.search(para):
        return True
    return d.month == 1 and d.day == 1 and bool(year_only_pattern(d).search(para))


def _bare_date_pattern(d: date) -> re.Pattern:
    return re.compile(
        rf"\b{MONTHS[d.month - 1]}\s+0?{d.day}(?:\s*[-–]\s*\d{{1,2}})?\s*,\s*{d.year}\b")


def human_date(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def slice_for_date(notes: str, d: Optional[date]) -> str:
    """The paragraphs of the cumulative note that name ``d``, verbatim, in
    order, with any grouping label they sit under. Fixed sentences when the
    note cannot speak to the date — never undated filler."""
    paras = paragraphs(notes)
    if not paras:
        return "The court's page carries no explanatory note."
    if d is None:
        return ("The court publishes no effective date for this version, so no "
                "paragraph of the explanatory note can be attributed to it.")

    hits: List[str] = []
    label: Optional[str] = None
    label_rank: Optional[int] = None
    label_used = False
    listed = False
    for i, para in enumerate(paras):
        if i == 0 and is_amendment_list(para):
            listed = names_date(para, d, anchored=False)
            continue
        if is_trailer(para):
            label = None
            continue
        if LABEL_RE.match(para) and not DATE_RE.search(para):
            label, label_used = para, False
            label_rank = unit_rank(para)
            continue
        if label is not None:
            r = unit_rank(para)
            if r is not None and label_rank is not None and r <= label_rank:
                label = None
        if names_date(para, d):
            if label and not label_used:
                hits.append(label)
                label_used = True
            hits.append(para)
    if hits:
        return "\n\n".join(hits)
    if listed:
        return (f"The court's explanatory note lists {human_date(d)} as an "
                "amendment date but describes no change for it.")
    return f"No paragraph in the court's explanatory note is dated {human_date(d)}."


# ---- SOURCES paragraph -------------------------------------------------------

_PAGES_RE = re.compile(r"\bpages?\s+([\dA-Za-z]+(?:\s*[-–]\s*[\dA-Za-z]+)?)", re.I)


def parse_date(text: str) -> Optional[Tuple[date, Optional[date]]]:
    """First (start, end) date in ``text``; end is None unless a day range."""
    m = DATE_RE.search(text)
    if not m:
        return None
    month = MONTHS.index(m.group(1)) + 1
    year = int(m.group(3))
    try:
        start = date(year, month, int(m.group(2)))
    except ValueError:
        return None
    end = None
    rng = re.match(rf"{m.group(1)}\s+{m.group(2)}\s*[-–]\s*(\d{{1,2}})", m.group(0))
    if rng:
        try:
            end = date(year, month, int(rng.group(1)))
        except ValueError:
            end = None
    return start, end


_MINUTES_OF_RE = re.compile(r"\bminutes\s+of\b(?:\s+the\b)?", re.I)


def sources_entries(notes: str) -> List[dict]:
    """The SOURCES paragraph split into entries. Each: ``raw`` (verbatim),
    ``date`` / ``end`` (meeting day or None), ``pages`` (as printed or None),
    ``committee`` (the body named before the first dated entry — "Joint
    Procedure Committee" — carried forward to the later, date-only entries).
    Entries without a date (``Fed.R.Ev. 702``) are kept with date None."""
    out: List[dict] = []
    for para in paragraphs(notes):
        if not SOURCES_RE.match(para):
            continue
        body = re.sub(r"^\s*SOURCES?\s*:?\s*", "", para, flags=re.I)
        committee: Optional[str] = None
        # A semicolon separates entries; a period ends the minutes list and
        # starts the "other sources" tail ("...page 26 . Fed.R.Ev. 601; ...").
        for raw in re.split(r"\s*;\s*", body):
            raw = raw.strip(" .")
            if not raw:
                continue
            parsed = parse_date(raw)
            pages = _PAGES_RE.search(raw)
            if parsed is None:
                out.append({"raw": raw, "date": None, "end": None, "pages": None,
                            "committee": None})
                continue
            start, end = parsed
            lead = raw[:DATE_RE.search(raw).start()]
            if _MINUTES_OF_RE.search(lead):
                # "Joint Procedure Committee Minutes of" / "Minutes of Joint
                # Procedure Committee of" — the body's name either side.
                name = _MINUTES_OF_RE.sub(" ", lead)
                name = re.sub(r"\s+of\s*$", "", name.strip(" ,"), flags=re.I).strip(" ,")
                committee = name or committee
            out.append({"raw": raw, "date": start, "end": end,
                        "pages": pages.group(1).replace(" ", "") if pages else None,
                        "committee": committee})
    return out


def sources_in_window(notes: str, effective: Optional[date],
                      prev_effective: Optional[date]) -> List[dict]:
    """Dated SOURCES entries with prev_effective < meeting <= effective (or
    meeting <= effective when there is no earlier version)."""
    if effective is None:
        return []
    keep = []
    for e in sources_entries(notes):
        d = e["date"]
        if d is None or d > effective:
            continue
        if prev_effective is not None and d <= prev_effective:
            continue
        keep.append(e)
    return keep


# ---- sidecar file ------------------------------------------------------------

SIDECAR_SUBDIR = "notes"
_SIDECAR_H1 = "# Explanatory Notes — "
_SIDECAR_SOURCE = "Source: "


def sidecar_relpath(rule_number: str, category_prefix: Optional[str] = None) -> str:
    """``<category>/notes/rule-<n>.md`` beside ``<category>/rule-<n>.md``.
    The subdirectory keeps the file out of every ``rule-*.md`` glob and out
    of ndlaw-mcp's ``ingest_rules`` change filter, which reads the second
    path component as the rule filename."""
    base = f"{SIDECAR_SUBDIR}/rule-{rule_number}.md"
    return f"{category_prefix}/{base}" if category_prefix else base


def render_sidecar(rule_title: str, url: str, notes: str) -> str:
    """The note verbatim under a two-line header. An empty note renders a
    header-only file so a rule with no note is distinguishable from one the
    scraper never looked at."""
    head = [f"{_SIDECAR_H1}{normalize(rule_title).strip()}", ""]
    if url:
        head += [f"{_SIDECAR_SOURCE}{url}", ""]
    body = "\n\n".join(paragraphs(notes))
    return "\n".join(head) + (body + "\n" if body else "")


def parse_sidecar(text: str) -> Tuple[str, str, str]:
    """(title, url, notes) from a sidecar file."""
    title = url = ""
    lines = text.splitlines()
    i = 0
    if lines and lines[0].startswith(_SIDECAR_H1):
        title = lines[0][len(_SIDECAR_H1):].strip()
        i = 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].startswith(_SIDECAR_SOURCE):
        url = lines[i][len(_SIDECAR_SOURCE):].strip()
        i += 1
    return title, url, "\n".join(lines[i:]).strip()
