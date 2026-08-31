"""
Content repairs for pages the court's own CMS serves structurally broken.

Two "Table of Statutes Superseded" pages (N.D.R.Ev. Table, N.D.R.Crim.P.
Table) lost their table markup upstream: every column of every row runs
together in a single <span>, and the damage predates the Wayback Machine's
earliest capture (2005, old court.state.nd.us domain — verified 2026-08-31),
so no clean web witness exists. These repairs reconstruct the rows by
grammar: NDCC section shapes, disposition keywords, and the closed set of
valid rule numbers make the split points deterministic.

Contract:
- WHITESPACE-STRUCTURE ONLY. A repair may insert whitespace and table
  markup; it must never add, drop, move, or change a non-whitespace
  character, except the explicit keyed substitutions in the per-table
  ``*_CHAR_REPAIRS`` lists (each one a verified upstream CMS corruption,
  documented at its definition).
- Round-trip enforced: the reconstruction is applied only if the output's
  non-whitespace characters (markup stripped) equal the input's, after the
  keyed substitutions. On any mismatch or parse failure the original
  markdown passes through unchanged and a warning is logged.
- Signature-gated: each repair first checks the page still carries the
  known flat-run signature, so if the court ever fixes the page the repair
  steps aside automatically.
"""

import re
from typing import Callable, List, Optional, Tuple


def _stripped(s: str) -> str:
    """Comparison key for the round-trip gate: all non-whitespace characters
    except the table markup this module itself inserts (pipes, header
    separators, bold markers)."""
    s = re.sub(r"-{3,}", "", s)
    return re.sub(r"[|\s*]", "", s)


# ---------------------------------------------------------------------------
# N.D.R.Ev. Table of Statutes Superseded
# ---------------------------------------------------------------------------

# Keyed character substitutions — the only non-whitespace edits allowed.
#
# The first ch. 31-01 entry reads "31-01101601". The row is § 31-01-01 ->
# Rule 601 ("31-01-01601" flat): Rule 601's explanatory note says it
# superseded N.D.C.C. §§ 31-01-01, 31-01-03, 31-01-04, and 31-01-05, and the
# entry sorts exactly where 31-01-01 belongs. The CMS corrupted the
# section's second hyphen into a "1".
_EV_CHAR_REPAIRS: List[Tuple[str, str]] = [
    ("31-01101601", "31-01-01601"),
]

# Every rule number the N.D. Rules of Evidence have ever used (mirror file
# census). The closed set is what makes glued "section+rule" tokens
# splittable: "11-26-07408" can only be 11-26-07 + 408.
_EV_RULES = {
    "101", "102", "103", "104", "105", "106", "107",
    "201", "301", "302", "303",
    "401", "402", "403", "404", "405", "406", "407", "408", "409", "410",
    "411", "412",
    "501", "502", "503", "504", "505", "506", "507", "508", "509", "510",
    "511", "512", "513",
    "601", "602", "603", "604", "605", "606", "607", "608", "609", "610",
    "611", "612", "613", "614", "615",
    "701", "702", "703", "704", "705", "706", "707",
    "801", "802", "803", "804", "805", "806", "807",
    "901", "902", "903",
    "1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008",
    "1101", "1102", "1103",
}

_EV_SIGNATURE = re.compile(r"^Section\s+Evidence\s+Rule\s+\d", re.M)

# An NDCC citation: title(1-2 digits, optional .N) - chapter(2 digits,
# optional .N) [- section(2 digits, optional .N)] [(subsection)]. The
# two-digit component widths are load-bearing: they force the split in
# glued tokens like "11-26-07408".
_EV_SEC = (r"\d{1,2}(?:\.\d)?-\d{2}(?:\.\d)?(?:-\d{2}(?:\.\d)?)?"
           r"(?:\(\d+\))?")


def _split_glued(bare: str, sec_shape: str, rules: set) -> Optional[Tuple[str, str]]:
    """Split 'section+rule' glue like '11-26-07408'. None if not exactly one
    valid split."""
    hits = []
    for L in (3, 4):
        if len(bare) <= L:
            continue
        sec, rule = bare[:-L], bare[-L:]
        if rule in rules and re.fullmatch(sec_shape, sec):
            hits.append((sec, rule))
    return hits[0] if len(hits) == 1 else None


def _parse_ev_run(run: str) -> Optional[List[Tuple[str, List[str]]]]:
    """Parse the flat 'section rule [, rule]' run. None on any ambiguity."""
    entries: List[Tuple[str, List[str]]] = []
    pending_sec: Optional[str] = None       # section awaiting its rule(s)
    expecting_more = False                  # last rule ended with ","

    for tok in run.split():
        bare = tok.rstrip(",")
        comma = tok.endswith(",")

        if expecting_more:
            if bare in _EV_RULES:
                entries[-1][1].append(bare)
                expecting_more = comma
                continue
            return None

        if pending_sec is not None:
            if bare in _EV_RULES:
                entries.append((pending_sec, [bare]))
                pending_sec = None
                expecting_more = comma
                continue
            return None

        split = _split_glued(bare, _EV_SEC, _EV_RULES)
        if split:
            entries.append((split[0], [split[1]]))
            expecting_more = comma
            continue
        if re.fullmatch(_EV_SEC, bare) and not comma:
            pending_sec = bare
            continue
        return None

    if pending_sec is not None or expecting_more:
        return None
    return entries


def repair_ndrev_table(markdown: str, logger=None) -> str:
    """Rebuild the N.D.R.Ev. Table of Statutes Superseded as a pipe table."""
    if not _EV_SIGNATURE.search(markdown):
        return markdown

    fixed = markdown
    for old, new in _EV_CHAR_REPAIRS:
        if old not in fixed:
            if logger:
                logger.warning(
                    "ndrev Table repair: expected corruption %r absent — "
                    "page changed upstream; passing through", old)
            return markdown
        fixed = fixed.replace(old, new)

    m = re.search(r"Section\s+Evidence\s+Rule\s+(\d.*)$", fixed, re.S)
    run = " ".join(m.group(1).split())
    entries = _parse_ev_run(run)
    if entries is None:
        if logger:
            logger.warning("ndrev Table repair: flat run failed to parse — "
                           "passing through unchanged")
        return markdown

    rows = ["| Section | Evidence Rule |", "| --- | --- |"]
    rows += [f"| {sec} | {', '.join(rules)} |" for sec, rules in entries]
    out = fixed[: m.start()] + "\n".join(rows) + "\n"

    if _stripped(out) != _stripped(fixed):
        if logger:
            logger.warning("ndrev Table repair: round-trip mismatch — "
                           "passing through unchanged")
        return markdown
    return out


# ---------------------------------------------------------------------------
# N.D.R.Crim.P. Table (statutes considered/superseded)
# ---------------------------------------------------------------------------

# Keyed repairs for upstream damage the grammar cannot absorb. Every entry
# is anchored with enough context to be unique in the page. Three classes:
# hyphens the CMS dropped or replaced (the section list around each makes
# the reading certain), and one row whose range and disposition the CMS
# interleaved ("27-10-03 thru Superseded for 27-10-27 Criminal Process
# Only" — a pure reflow of "27-10-03 thru 27-10-27 | Superseded for
# Criminal Process Only").
_CRIMP_CHAR_REPAIRS: List[Tuple[str, str]] = [
    # chapter label for §§ 31-01-11/-12 under TITLE 31; "3- 01" -> "31-01"
    ("TITLE 31 3- 01 31-01-11", "TITLE 31 31-01 31-01-11"),
    # § 29-08-23 between -22 and -24; space where the first hyphen belongs
    ("29 08-23 Superseded", "29-08-23 Superseded"),
    # § 12-01-04(13) between (12) and 12-01-13; hyphen lost to a space
    ("4112-01 04(13)Considered", "4112-01-04(13)Considered"),
    # the interleaved range/disposition row (see above)
    ("27-10-03 thru Superseded for 27-10-27Criminal ProcessOnly42",
     "27-10-03 thru 27-10-27 Superseded forCriminal ProcessOnly 42"),
]

# Rule numbers of the N.D. Rules of Criminal Procedure as the table's rule
# column uses them. "35-1978" appears once ("12.1-32-02(3) Superseded
# 35-1978") and is kept verbatim — plausibly the print's own "(1978)"
# annotation; no witness on hand to overrule it.
_CRIMP_RULES = {str(n) for n in range(1, 62)} | {
    "5.1", "12.1", "12.2", "24.1", "26.1", "32.1", "35-1978", "37.1", "43.1",
}

_CRIMP_SIGNATURE = re.compile(r"^Statute\s+Rule\s+TITLE\s+1\b", re.M)

# Sections here: 2-digit components with optional .N at every level, and an
# optional (n) / (n-m) subsection.
_CRIMP_SEC = (r"\d{1,2}(?:\.\d)?-\d{2}(?:\.\d)?(?:-\d{2}(?:\.\d)?)?"
              r"(?:\(\d+(?:-\d+)?\))?")
_CRIMP_CHAP = re.compile(r"\d{1,2}(?:\.\d)?-\d{2}(?:\.\d)?$")

# Disposition phrases, longest first. The CMS glued some word boundaries
# ("Supersededfor", "ProcessOnly", "inpart", "firstonly", "exceptas",
# "CourtReporter's"); \s* between words absorbs every observed spacing.
_DISPOSITIONS = [
    (re.compile(r"Superseded\s*\(\s*except\s*as\s*to\s*Court\s*Reporter's"
                r"\s*fees\s*\)"),
     "Superseded (except as to Court Reporter's fees)"),
    (re.compile(r"Superseded\s*for\s*Criminal\s*Process\s*Only"),
     "Superseded for Criminal Process Only"),
    (re.compile(r"Superseded\s*for\s*Criminal\s*Process"),
     "Superseded for Criminal Process"),
    (re.compile(r"Superseded\s*in\s*part"), "Superseded in part"),
    (re.compile(r"Superseded\s*first\s*only"), "Superseded first only"),
    (re.compile(r"Superseded"), "Superseded"),
    (re.compile(r"Considered"), "Considered"),
]

_TITLE_RE = re.compile(r"TITLE\s+(\d+(?:\.\d)?)")


class _CrimpParser:
    def __init__(self, run: str, logger=None):
        self.run = run
        self.n = len(run)
        self.pos = 0
        self.logger = logger
        self.chapter: Optional[str] = None
        self.rows: List[dict] = []

    def fail(self, why: str):
        if self.logger:
            ctx = self.run[self.pos:self.pos + 60]
            self.logger.warning(
                "ndrcrimp Table repair: %s at %r", why, ctx)
        return None

    def ws(self):
        while self.pos < self.n and self.run[self.pos].isspace():
            self.pos += 1

    def disposition(self) -> Optional[str]:
        for rx, canon in _DISPOSITIONS:
            m = rx.match(self.run, self.pos)
            if m:
                self.pos = m.end()
                return canon
        return None

    def rules(self) -> Optional[List[str]]:
        """A comma-separated rule list. The last rule may be glued to the
        next row's section ('451-01-41'); the current-chapter prefix decides
        the split."""
        out: List[str] = []
        while True:
            self.ws()
            m = re.match(r"[\d.]+(?:-1978)?", self.run[self.pos:])
            if not m:
                break
            chunk = m.group(0)
            rest_of_run = self.run[self.pos + len(chunk):]
            # candidate prefix lengths that are valid rules
            cands = []
            for L in range(len(chunk), 0, -1):
                head, tail = chunk[:L], chunk[L:]
                if head not in _CRIMP_RULES:
                    continue
                if tail == "":
                    cands.append((L, False))
                elif re.match(_CRIMP_SEC + r"(?![\d.(])", tail + rest_of_run):
                    cands.append((L, True))
            if not cands:
                break
            if len(cands) > 1:
                # glued splits: prefer the one whose remainder is a section
                # of the CURRENT chapter (or, failing that, of a LATER
                # chapter — a new chapter label follows the glue only when
                # the run itself changes chapter)
                pref = [c for c in cands if c[1] and self.chapter
                        and (chunk[c[0]:] + rest_of_run).startswith(
                            self.chapter + "-")]
                whole = [c for c in cands if not c[1]]
                if len(pref) == 1:
                    cands = pref
                elif whole:
                    cands = [whole[0]]
                else:
                    return self.fail(f"ambiguous rule split in {chunk!r}")
            L, glued = cands[0]
            out.append(chunk[:L])
            self.pos += L
            if glued:
                return out          # rule list ends at the glued section
            self.ws()
            if self.pos < self.n and self.run[self.pos] == ",":
                self.pos += 1
                continue
            return out
        return out

    def section_token(self) -> Optional[str]:
        m = re.match(_CRIMP_SEC, self.run[self.pos:])
        if not m:
            return None
        self.pos += m.end()
        return m.group(0)

    def maybe_range(self, sec: str) -> Optional[str]:
        save = self.pos
        self.ws()
        m = re.match(r"thru(?=[\s\d])", self.run[self.pos:])
        if not m:
            self.pos = save
            return sec
        self.pos += m.end()
        self.ws()
        end = self.section_token()
        if end is None:
            self.pos = save
            return sec
        return f"{sec} thru {end}"

    def parse(self) -> Optional[List[dict]]:
        while True:
            self.ws()
            if self.pos >= self.n:
                break

            m = _TITLE_RE.match(self.run, self.pos)
            if m:
                self.rows.append({"title": m.group(1)})
                self.chapter = None
                self.pos = m.end()
                continue

            m = re.match(r"Entire\s*Chapter", self.run[self.pos:])
            if m:
                self.pos += m.end()
                self.ws()
                disp = self.disposition()
                if disp is None:
                    return self.fail("Entire Chapter without disposition")
                rules = self.rules()
                if rules is None:
                    return None
                self.rows.append({"section": "Entire Chapter",
                                  "chapter": self.chapter,
                                  "disp": disp, "rules": rules})
                continue

            start = self.pos
            sec = self.section_token()
            if sec is None:
                return self.fail("expected section/chapter")

            # chapter+section glue ("1-011-01-33"): the token parses as a
            # full 3-component section but the REAL reading is a 2-component
            # chapter immediately followed by its first section. Detect: the
            # text at the token's end continues with more of a section
            # ("-33..." would have been consumed), so instead check whether
            # interpreting a leading 2-component prefix as chapter leaves a
            # section starting with that same chapter.
            m_chap = re.match(r"\d{1,2}(?:\.\d)?-\d{2}(?:\.\d)?", sec)
            if m_chap:
                chap = m_chap.group(0)
                rest = self.run[start + len(chap):]
                m_sec = re.match(_CRIMP_SEC + r"(?![\d.(])", rest)
                if m_sec and m_sec.group(0).startswith(chap + "-"):
                    self.chapter = chap
                    self.pos = start + len(chap) + m_sec.end()
                    sec2 = self.maybe_range(m_sec.group(0))
                    self.ws()
                    disp = self.disposition()
                    if disp is None:
                        return self.fail(f"chapter glue {chap!r} without "
                                         "disposition")
                    rules = self.rules()
                    if rules is None:
                        return None
                    self.rows.append({"section": sec2, "chapter": chap,
                                      "new_chapter": True,
                                      "disp": disp, "rules": rules})
                    continue

            # bare chapter label (its sections follow as separate tokens);
            # rows always continue with a section or "Entire Chapter", never
            # a disposition, so lookahead distinguishes label from row
            if _CRIMP_CHAP.fullmatch(sec):
                save = self.pos
                self.ws()
                nxt_is_row = (re.match(r"Entire\s*Chapter", self.run[self.pos:])
                              or re.match(_CRIMP_SEC, self.run[self.pos:]))
                self.pos = save
                if nxt_is_row:
                    self.chapter = sec
                    self.rows.append({"chapter": sec, "marker": True})
                    continue

            sec = self.maybe_range(sec)
            self.ws()
            disp = self.disposition()
            if disp is None:
                return self.fail(f"section {sec!r} without disposition")
            rules = self.rules()
            if rules is None:
                return None
            row = {"section": sec, "chapter": self.chapter,
                   "disp": disp, "rules": rules}
            self.rows.append(row)

            # a second disposition directly after the rules belongs to the
            # SAME section ("29-17-08 Considered 24 Superseded in part 23"):
            # rendered as a continuation row so character order is kept.
            save = self.pos
            self.ws()
            disp2 = self.disposition()
            if disp2 is not None:
                rules2 = self.rules()
                if rules2 is None:
                    return None
                self.rows.append({"section": "", "chapter": self.chapter,
                                  "disp": disp2, "rules": rules2,
                                  "continuation": True})
            else:
                self.pos = save

        return self.rows


def _render_crimp_rows(rows: List[dict]) -> str:
    parts: List[str] = []
    in_table = False
    last_chap_shown: Optional[str] = None

    def open_table():
        nonlocal in_table
        if not in_table:
            parts.append("| Chapter | Statute | Disposition | Rule |")
            parts.append("| --- | --- | --- | --- |")
            in_table = True

    for r in rows:
        if "title" in r:
            in_table = False
            last_chap_shown = None
            parts.append(f"\n**TITLE {r['title']}**\n")
            continue
        if r.get("marker"):
            continue        # chapter label renders on its first section row
        open_table()
        chap = r.get("chapter") or ""
        show = ""
        if chap and chap != last_chap_shown and not r.get("continuation"):
            show = chap
            last_chap_shown = chap
        rules = ", ".join(r.get("rules", []))
        parts.append(f"| {show} | {r['section']} | {r['disp']} | {rules} |")
    return "\n".join(parts).strip() + "\n"


def repair_ndrcrimp_table(markdown: str, logger=None) -> str:
    """Rebuild the N.D.R.Crim.P. statutes table as pipe tables per TITLE."""
    if not _CRIMP_SIGNATURE.search(markdown):
        return markdown

    fixed = markdown
    for old, new in _CRIMP_CHAR_REPAIRS:
        if old not in fixed:
            if logger:
                logger.warning(
                    "ndrcrimp Table repair: expected corruption %r absent — "
                    "page changed upstream; passing through", old)
            return markdown
        fixed = fixed.replace(old, new)

    m = re.search(r"Statute\s+Rule\s+(TITLE\s+1\b.*)$", fixed, re.S)
    run = " ".join(m.group(1).split())
    rows = _CrimpParser(run, logger).parse()
    if rows is None:
        if logger:
            logger.warning("ndrcrimp Table repair: flat run failed to parse "
                           "— passing through unchanged")
        return markdown

    body = _render_crimp_rows(rows)
    out = fixed[: m.start()] + body

    # Round-trip: the flat "Statute Rule" heading is replaced by the
    # rendered per-TITLE table headers; both are markup for the comparison.
    ref = _stripped(fixed).replace("StatuteRule", "", 1)
    got = _stripped(out).replace("ChapterStatuteDispositionRule", "")
    if ref != got:
        if logger:
            logger.warning("ndrcrimp Table repair: round-trip mismatch — "
                           "passing through unchanged")
        return markdown
    return out


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# (url regex, repair function). Version-suffix URLs ("/Table-1") match too:
# the signature gate decides whether a given version needs the repair.
REPAIRS: List[Tuple[re.Pattern, Callable[..., str]]] = [
    (re.compile(r"/legal-resources/rules/ndrev/Table(?:-\d+)?$", re.I),
     repair_ndrev_table),
    (re.compile(r"/legal-resources/rules/ndrcrimp/Table(?:-\d+)?$", re.I),
     repair_ndrcrimp_table),
]


def apply_repairs(url: str, markdown: str, logger=None) -> str:
    for rx, fn in REPAIRS:
        if rx.search(url):
            return fn(markdown, logger)
    return markdown
