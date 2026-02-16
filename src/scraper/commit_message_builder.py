"""
Commit Message Builder for ND Court Rules.
Uses Claude Haiku to build focused, per-version commit messages with
relevant explanatory notes and committee minutes summaries.
Falls back to regex-based trimming when no API key is available.
"""

import os
import re
from datetime import date
from typing import List, Optional, Tuple

from scraper.committee_minutes_fetcher import CommitteeMinutesFetcher


class CommitMessageBuilder:
    """Builds focused commit messages for each rule version."""

    def __init__(
        self,
        anthropic_client,
        committee_fetcher: CommitteeMinutesFetcher,
        haiku_model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 1000,
        temperature: float = 0.1,
        logger=None,
    ):
        self.client = anthropic_client
        self.committee_fetcher = committee_fetcher
        self.haiku_model = haiku_model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.logger = logger

    def build_message(
        self,
        rule_number: str,
        rule_title: str,
        effective_date: date,
        explanatory_notes: str,
        is_current: bool,
        url: str = "",
        prev_effective_date: Optional[date] = None,
    ) -> str:
        """
        Build a focused commit message body for a specific rule version.

        Args:
            rule_number: The rule number
            rule_title: Title of the rule
            effective_date: When this version became effective
            explanatory_notes: Full cumulative explanatory notes
            is_current: Whether this is the current version
            url: Source URL
            prev_effective_date: Previous version's effective date (for filtering)

        Returns:
            Formatted commit body string
        """
        if not explanatory_notes:
            return self._format_body(rule_title, url, is_current, "")

        # Parse meeting dates from SOURCES paragraph
        meeting_dates = self._parse_sources_dates(explanatory_notes)

        # Filter to meetings relevant to this version
        relevant_meetings = self._filter_relevant_meetings(
            meeting_dates, effective_date, prev_effective_date
        )

        # Fetch committee minutes text for relevant meetings
        minutes_texts = []
        for meeting_date in relevant_meetings:
            text = self.committee_fetcher.fetch_minutes_text(meeting_date)
            if text:
                minutes_texts.append((meeting_date, text))

        # Build commit body via Haiku or regex fallback
        if self.client:
            notes_body = self._call_haiku(
                explanatory_notes, effective_date, rule_number, rule_title, minutes_texts
            )
        else:
            notes_body = None

        if not notes_body:
            notes_body = self._regex_trim(explanatory_notes, effective_date)

        return self._format_body(rule_title, url, is_current, notes_body)

    def _format_body(
        self, rule_title: str, url: str, is_current: bool, notes_body: str
    ) -> str:
        """Format the commit message body."""
        status = "current" if is_current else "historical"
        parts = [rule_title]
        if url:
            parts.append(f"Source: {url}")
        parts.append(f"Status: {status}")

        if notes_body and notes_body.strip():
            parts.append("")
            parts.append("Explanatory Notes:")
            parts.append(notes_body.strip())

        return "\n".join(parts)

    def _parse_sources_dates(self, explanatory_notes: str) -> List[date]:
        """
        Extract all committee meeting date references from SOURCES paragraph.

        Handles both linked and unlinked references:
        - Linked: [September 30, 2021](https://...committee...)
        - Unlinked: February 17-18, 1983, pages 20-22
        """
        dates = []

        # Find the SOURCES paragraph
        sources_match = re.search(r'SOURCES?:(.+)', explanatory_notes, re.DOTALL | re.IGNORECASE)
        if not sources_match:
            return dates

        sources_text = sources_match.group(1)

        # Extract linked dates: [date text](url)
        linked_pattern = r'\[([^\]]+)\]\(https?://[^)]*committee[^)]*\)'
        for match in re.finditer(linked_pattern, sources_text, re.IGNORECASE):
            parsed = self._parse_date_text(match.group(1))
            if parsed:
                dates.append(parsed)

        # Extract unlinked dates: month day(-day), year patterns
        # Match patterns like "February 17-18, 1983" or "September 30, 2021"
        unlinked_pattern = (
            r'(?:January|February|March|April|May|June|July|August|'
            r'September|October|November|December)\s+\d{1,2}(?:-\d{1,2})?,\s*\d{4}'
        )
        for match in re.finditer(unlinked_pattern, sources_text):
            parsed = self._parse_date_text(match.group(0))
            if parsed and parsed not in dates:
                dates.append(parsed)

        return dates

    def _parse_date_text(self, text: str) -> Optional[date]:
        """
        Parse a date string like 'September 29-30, 1994' into a date.
        Uses the first date in any range.
        """
        # Normalize: remove range part (e.g., "-30" in "29-30")
        cleaned = re.sub(r'(\d{1,2})-\d{1,2}', r'\1', text.strip())

        # Try common formats
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y"):
            try:
                from datetime import datetime
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue

        return None

    def _filter_relevant_meetings(
        self,
        meeting_dates: List[date],
        effective_date: date,
        prev_effective_date: Optional[date],
    ) -> List[date]:
        """
        Filter meeting dates to those relevant to this version.

        Keeps meetings where prev_effective_date < meeting_date <= effective_date.
        For the first version (no prev date), keeps meetings before effective_date.
        """
        relevant = []
        for md in meeting_dates:
            if prev_effective_date:
                if prev_effective_date < md <= effective_date:
                    relevant.append(md)
            else:
                if md <= effective_date:
                    relevant.append(md)
        return relevant

    def _call_haiku(
        self,
        explanatory_notes: str,
        effective_date: date,
        rule_number: str,
        rule_title: str,
        minutes_texts: List[Tuple[date, str]],
    ) -> Optional[str]:
        """
        Call Claude Haiku to extract version-specific notes and summarize minutes.

        Returns the focused commit body text, or None on failure.
        """
        if not self.client:
            return None

        date_str = effective_date.strftime("%B %d, %Y")

        # Build minutes section
        minutes_section = "None available"
        if minutes_texts:
            parts = []
            for meeting_date, text in minutes_texts:
                # Truncate very long minutes to avoid token explosion
                truncated = text[:8000] if len(text) > 8000 else text
                parts.append(
                    f"--- Meeting {meeting_date.isoformat()} ---\n{truncated}"
                )
            minutes_section = "\n\n".join(parts)

        prompt = f"""You are summarizing changes to a North Dakota court rule for a git commit message.

Rule: Rule {rule_number} - {rule_title}
Version effective date: {date_str}

Below are the full explanatory notes for this rule (covering ALL versions).
Extract ONLY the paragraphs or sentences that describe changes effective {date_str}.
Omit the opening summary line that lists all amendment dates.
Omit notes about other versions.
If no paragraphs specifically mention this date, include any general guidance paragraphs that appear to be undated.

If committee minutes text is provided, extract only the portions discussing Rule {rule_number} and summarize them briefly (2-3 sentences max).

Format the output as a clean commit message body (no subject line). Keep it concise.

EXPLANATORY NOTES:
{explanatory_notes}

COMMITTEE MINUTES:
{minutes_section}"""

        try:
            response = self.client.messages.create(
                model=self.haiku_model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            result = response.content[0].text.strip()

            # Sanity check: if Haiku returns nothing useful, fall back
            if not result or len(result) < 10:
                return None

            return result

        except Exception as e:
            if self.logger:
                self.logger.warning(
                    f"Haiku API call failed for Rule {rule_number} "
                    f"effective {effective_date}: {e}"
                )
            return None

    def _regex_trim(self, explanatory_notes: str, effective_date: date) -> str:
        """
        Fallback: regex-based paragraph filtering for when Haiku is unavailable.

        Keeps paragraphs that mention this effective date.
        Skips the opening summary paragraph and SOURCES paragraph.
        Includes undated general guidance paragraphs.
        """
        date_strs = self._date_format_variants(effective_date)
        paragraphs = explanatory_notes.split("\n\n")

        if not paragraphs:
            return explanatory_notes

        kept = []
        for i, para in enumerate(paragraphs):
            para_stripped = para.strip()
            if not para_stripped:
                continue

            # Skip the opening summary that lists all amendment dates
            if i == 0 and re.search(r'was (?:amended|adopted|approved)', para_stripped, re.IGNORECASE):
                # Check if it also has specific content beyond just listing dates
                # If it mentions our date specifically in a substantive way, keep it
                if not any(ds in para_stripped for ds in date_strs):
                    continue

            # Skip SOURCES paragraph
            if re.match(r'SOURCES?:', para_stripped, re.IGNORECASE):
                continue

            # Keep paragraphs that mention this effective date
            if any(ds in para_stripped for ds in date_strs):
                kept.append(para_stripped)
                continue

            # Keep undated general guidance paragraphs (no "effective" keyword)
            if not re.search(r'effective\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)', para_stripped, re.IGNORECASE):
                # But skip if it clearly references a different specific date
                if not re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}', para_stripped):
                    kept.append(para_stripped)

        return "\n\n".join(kept) if kept else ""

    def _date_format_variants(self, d: date) -> List[str]:
        """Generate multiple string representations of a date for matching."""
        variants = [
            d.strftime("%B %d, %Y"),         # March 01, 2003
            d.strftime("%B %-d, %Y"),         # March 1, 2003 (no leading zero)
        ]
        # Also try without leading zero using replace
        with_zero = d.strftime("%B %d, %Y")
        without_zero = with_zero.replace(" 0", " ")
        if without_zero not in variants:
            variants.append(without_zero)
        return variants
