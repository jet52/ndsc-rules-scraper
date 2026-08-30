"""
Version History Extractor for ND Court Rules.
Parses version history tables and explanatory notes from rule HTML pages.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup


@dataclass
class RuleVersion:
    """Represents a single version of a rule."""
    effective_date: Optional[date]  # None: the court publishes no date (see date_unpublished)
    obsolete_date: Optional[date]
    url: str
    version_suffix: Optional[str]  # e.g., "10" from "rule-28-10"
    is_current: bool
    # The court's version table shows a single row dated 01/01/0001 for ~45
    # rules (N.D.R. Proc. R., Local Ct. Pr., CLE, Ltd. Practice, several
    # appendices and tables). That sentinel is "effective date not published",
    # not "no version": the page IS the current text. Ratified JT 2026-08-30.
    date_unpublished: bool = False


@dataclass
class VersionHistory:
    """Complete version history for a rule."""
    rule_number: str
    rule_title: str
    current_url: str
    versions: List[RuleVersion] = field(default_factory=list)
    explanatory_notes: str = ""
    total_versions: int = 0


class VersionHistoryExtractor:
    """Extracts version history and explanatory notes from rule HTML pages."""

    BASE_URL = "https://www.ndcourts.gov"

    def __init__(self, logger=None):
        self.logger = logger

    def extract_version_history(self, html_content: str, rule_url: str) -> VersionHistory:
        """
        Extract complete version history from a rule page.

        Args:
            html_content: Raw HTML of the rule page
            rule_url: URL of the current rule page

        Returns:
            VersionHistory with all versions and explanatory notes
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        rule_title = self._extract_title(soup)
        rule_number = self._extract_rule_number(rule_title, rule_url)

        versions = self._parse_version_table(soup, rule_url)
        explanatory_notes = self._extract_explanatory_notes(soup)

        # If no version table found, create a single version from the current page
        if not versions:
            effective_date = self._extract_effective_date_from_header(soup)
            if effective_date:
                versions = [RuleVersion(
                    effective_date=effective_date,
                    obsolete_date=None,
                    url=rule_url,
                    version_suffix=None,
                    is_current=True,
                )]

        # Sort oldest to newest (an unpublished date can only be the sole version)
        versions.sort(key=lambda v: v.effective_date or date.min)

        history = VersionHistory(
            rule_number=rule_number,
            rule_title=rule_title,
            current_url=rule_url,
            versions=versions,
            explanatory_notes=explanatory_notes,
            total_versions=len(versions),
        )

        if self.logger:
            self.logger.info(
                f"Extracted {len(versions)} versions for Rule {rule_number}: {rule_title}"
            )

        return history

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract rule title from the page."""
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()

        title_tag = soup.find('title')
        if title_tag:
            text = title_tag.get_text().strip()
            # Remove site prefix like "North Dakota Court System - "
            if ' - ' in text:
                return text.split(' - ', 1)[1].strip()
            return text

        return "Untitled Rule"

    # Instrument designators are read from the START of the title only. The
    # earlier pattern searched for "rule N" anywhere in the title, so
    # "TABLE A. SPECIAL STATUTORY PROCEEDINGS UNDER RULE 81" was filed as
    # Rule 81 and "APPENDIX K. RULE 3.5 ELECTRONIC FILING REQUIREMENTS" as
    # Rule 3.5 -- the foreign document overwrote the rule's own file
    # (N.D.R.Civ.P. 81; N.D.R.Ct. 3.5 / 8.8 / 8.9 / 8.3 in the mirror, found
    # 2026-08-30). It also captured at most two numeric levels, so
    # "RULE 8.3.1" became "8.3" and overwrote Rule 8.3.
    _DESIGNATOR_RE = re.compile(
        r'^\s*(?:administrative\s+)?(?:rule|order)\s+(\d+(?:\.\d+)*)(?![\d.]*\d)',
        re.IGNORECASE,
    )
    _APPENDIX_RE = re.compile(
        r'^\s*appendix\s+([A-Za-z])\b(?:\.?\s+to\s+rule\s+(\d+(?:\.\d+)*))?',
        re.IGNORECASE,
    )
    _SLUG_RE = re.compile(r'/legal-resources/rules/[^/]+/([\w][\w-]*)$')

    def _extract_rule_number(self, title: str, url: str) -> str:
        """Extract the rule identifier used to name the mirror file.

        Title first, URL slug second. The title is authoritative for dotted
        numbers (the index slug spells Rule 2.1 as "2-1") but only when its
        LEADING designator is a rule/order number; a table or appendix that
        mentions a rule in its title keeps its own identity.
        """
        match = self._DESIGNATOR_RE.match(title)
        if match:
            return match.group(1)

        # "APPENDIX A. ..." -> "appendix-a"; "Appendix A to Rule 8.9 ..." ->
        # "appendix-a-to-rule-8.9" (N.D.R.Ct. has both, and they are
        # different documents).
        match = self._APPENDIX_RE.match(title)
        if match:
            ident = f"appendix-{match.group(1).lower()}"
            if match.group(2):
                ident += f"-to-rule-{match.group(2)}"
            return ident

        # Fallback to URL slug (last path segment): "Table-A", "Appendix",
        # "preamble", "canon-1", "9A".
        url_match = self._SLUG_RE.search(url)
        if url_match:
            return url_match.group(1)

        return "unknown"

    def _parse_version_table(self, soup: BeautifulSoup, rule_url: str) -> List[RuleVersion]:
        """Parse the version history table from the page."""
        versions = []

        # Find the version history widget
        widget = soup.find('article', class_='widget-rule-version-history-widget')
        if not widget:
            if self.logger:
                self.logger.debug("No version history widget found")
            return versions

        table = widget.find('table', class_='table')
        if not table:
            if self.logger:
                self.logger.debug("No version history table found")
            return versions

        # Derive the base slug from the rule URL to correctly detect version suffixes.
        # e.g., rule_url "/ndrct/6-1" → base_slug "6-1"
        # Then link "/ndrct/6-1-3" → suffix "3" (not "1-3")
        base_slug = rule_url.rstrip('/').split('/')[-1]

        rows = table.find_all('tr')
        sentinels: List[RuleVersion] = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue  # Skip header row

            effective_str = cells[0].get_text().strip()
            obsolete_str = cells[1].get_text().strip()

            effective_date = self._parse_date(effective_str)
            if not effective_date:
                if self.logger:
                    self.logger.warning(f"Could not parse effective date: {effective_str}")
                continue

            sentinel = effective_date.year < 1889   # site placeholder 01/01/0001
            if sentinel:
                effective_date = None

            obsolete_date = self._parse_date(obsolete_str) if obsolete_str else None

            # Extract URL from the "View" link
            link = row.find('a', href=True)
            version_url = ""
            version_suffix = None
            if link:
                href = link.get('href', '')
                version_url = urljoin(self.BASE_URL, href)
                # Compare link slug against base slug to find version suffix
                link_slug = href.rstrip('/').split('/')[-1]
                if link_slug != base_slug and link_slug.startswith(base_slug + '-'):
                    version_suffix = link_slug[len(base_slug) + 1:]

            is_current = obsolete_date is None

            rv = RuleVersion(
                effective_date=effective_date,
                obsolete_date=obsolete_date,
                url=version_url or rule_url,
                version_suffix=version_suffix,
                is_current=is_current,
                date_unpublished=sentinel,
            )
            (sentinels if sentinel else versions).append(rv)

        if sentinels:
            if versions:
                # A dated history AND a placeholder row: the dated rows are the
                # record; the placeholder cannot be ordered against them.
                if self.logger:
                    self.logger.warning(
                        f"{len(sentinels)} sentinel-dated row(s) alongside "
                        f"{len(versions)} dated version(s) for {rule_url} — dropped"
                    )
            else:
                # The page's only version: current text, effective date not
                # published by the court.
                if self.logger:
                    self.logger.info(
                        f"Effective date not published for {rule_url} — "
                        f"taking the page as the current text"
                    )
                versions.append(sentinels[0])

        return versions

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string in MM/DD/YYYY or M/D/YYYY format."""
        if not date_str or not date_str.strip():
            return None

        date_str = date_str.strip()

        formats = [
            '%m/%d/%Y',
            '%m/%d/%y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        if self.logger:
            self.logger.warning(f"Could not parse date: '{date_str}'")
        return None

    def _extract_effective_date_from_header(self, soup: BeautifulSoup) -> Optional[date]:
        """Extract effective date from the rule header (e.g., 'Effective Date: 3/1/2025')."""
        h4 = soup.find('h4', string=re.compile(r'effective\s+date', re.IGNORECASE))
        if h4:
            text = h4.get_text().strip()
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
            if date_match:
                return self._parse_date(date_match.group(1))
        return None

    def _extract_explanatory_notes(self, soup: BeautifulSoup) -> str:
        """Extract explanatory notes from the collapsible section."""
        notes_div = soup.find('div', id='collapseExplanatoryNotes')
        if not notes_div:
            return ""

        body = notes_div.find('div', class_='card-body')
        if not body:
            return ""

        # Build clean text from paragraphs, preserving link URLs inline
        parts = []
        for p in body.find_all('p'):
            text = self._extract_text_with_links(p)
            if text.strip():
                parts.append(text.strip())

        return '\n\n'.join(parts)

    def _extract_text_with_links(self, element) -> str:
        """Extract text from an element, converting links to markdown format."""
        parts = []
        for child in element.children:
            if hasattr(child, 'name') and child.name == 'a':
                href = child.get('href', '')
                text = child.get_text()
                if href:
                    full_url = urljoin(self.BASE_URL, href)
                    parts.append(f"[{text}]({full_url})")
                else:
                    parts.append(text)
            elif hasattr(child, 'name') and child.name == 'span':
                parts.append(child.get_text())
            elif hasattr(child, 'name'):
                parts.append(child.get_text())
            else:
                parts.append(str(child))

        result = ''.join(parts)
        # Clean up whitespace
        result = re.sub(r'\s+', ' ', result)
        result = result.replace('\xa0', ' ')
        return result.strip()
