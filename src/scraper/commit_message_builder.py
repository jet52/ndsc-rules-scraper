"""
Commit Message Builder for ND Court Rules.

Builds each version's commit body from the court's own explanatory note,
deterministically: the paragraphs that name this version's effective date,
verbatim, and the committee meetings the note's SOURCES paragraph dates to
this version's window. See ``explanatory_notes`` for the slicing rules.

The full cumulative note is not the commit body's job — it is stored verbatim
as a sidecar file (``<category>/notes/rule-<n>.md``) by the orchestrators.

History: until 2026-11-02 this class asked Claude Haiku to extract and
summarize the relevant paragraphs and committee minutes, falling back to a
regex trim without an API key. Removed (JT): the model paraphrased primary
text, the cumulative note it read was discarded, and the pipeline pinned a
model. No network, no API, no model here now.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from scraper import explanatory_notes as xn


class CommitMessageBuilder:
    """Builds the per-version commit body."""

    def __init__(self, logger=None):
        self.logger = logger

    def build_message(
        self,
        rule_number: str,
        rule_title: str,
        effective_date: Optional[date],
        explanatory_notes: str,
        is_current: bool,
        url: str = "",
        prev_effective_date: Optional[date] = None,
    ) -> str:
        """
        Commit body for one version (no subject line).

        Args:
            rule_number: The rule number
            rule_title: Title of the rule
            effective_date: When this version became effective (None = the
                court publishes no date for it)
            explanatory_notes: The full cumulative note from the rule's page
            is_current: Whether this is the current version
            url: Source URL
            prev_effective_date: The previous version's effective date, which
                bounds the committee-minutes window
        """
        status = "current" if is_current else "historical"
        parts = [rule_title]
        if url:
            parts.append(f"Source: {url}")
        parts.append(f"Status: {status}")

        parts.append("")
        parts.append("Explanatory Notes:")
        parts.append(xn.slice_for_date(explanatory_notes, effective_date))

        meetings = xn.sources_in_window(explanatory_notes, effective_date,
                                        prev_effective_date)
        if meetings:
            parts.append("")
            parts.append("Committee minutes the note's SOURCES paragraph dates "
                         "to this version's window:")
            for m in meetings:
                parts.append(f"  - {m['raw']}")

        return "\n".join(parts)
