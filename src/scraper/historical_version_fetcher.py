"""
Historical Version Fetcher for ND Court Rules.
Downloads all historical versions of a rule and converts them to markdown.
"""

import re
import time
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from scraper.version_history_extractor import VersionHistory, RuleVersion


@dataclass
class RuleVersionContent:
    """Content of a specific rule version."""
    rule_number: str
    rule_title: str
    effective_date: date
    obsolete_date: Optional[date]
    is_current: bool
    url: str
    markdown: str
    explanatory_notes: str


def _wrap_emphasis(text: str, marker: str) -> str:
    """Wrap text in emphasis markers, keeping whitespace outside the markers.

    Per CommonMark spec, closing emphasis delimiters must not be preceded by
    whitespace and opening delimiters must not be followed by whitespace.
    So ``**text **`` is invalid — it must be ``**text** ``.
    """
    stripped = text.strip()
    if not stripped:
        return text
    leading = text[:len(text) - len(text.lstrip())]
    trailing = text[len(text.rstrip()):]
    return f"{leading}{marker}{stripped}{marker}{trailing}"


class HistoricalVersionFetcher:
    """Fetches and converts all historical versions of a rule."""

    def __init__(self, session: requests.Session, logger=None, request_delay: float = 1.0):
        self.session = session
        self.logger = logger
        self.request_delay = request_delay

    def fetch_all_versions(
        self, version_history: VersionHistory
    ) -> List[RuleVersionContent]:
        """
        Download and parse all versions of a rule chronologically.

        Args:
            version_history: VersionHistory with sorted version list

        Returns:
            List of RuleVersionContent, oldest first
        """
        results = []

        for i, version in enumerate(version_history.versions):
            if self.logger:
                self.logger.info(
                    f"  Fetching version {i + 1}/{len(version_history.versions)} "
                    f"(effective {version.effective_date}) for Rule {version_history.rule_number}"
                )

            content = self._fetch_version(version, version_history)
            if content:
                results.append(content)
            else:
                if self.logger:
                    self.logger.warning(
                        f"  Failed to fetch version {version.url}"
                    )

            # Respectful delay between requests
            if i < len(version_history.versions) - 1:
                time.sleep(self.request_delay)

        return results

    def _fetch_version(
        self, version: RuleVersion, history: VersionHistory
    ) -> Optional[RuleVersionContent]:
        """Fetch a single version and convert to markdown."""
        try:
            response = self.session.get(version.url, timeout=30)
            if response.status_code != 200:
                if self.logger:
                    self.logger.warning(
                        f"HTTP {response.status_code} for {version.url}"
                    )
                return None

            html = response.text
            soup = BeautifulSoup(html, 'html.parser')

            title = self._extract_title(soup, history.rule_title)
            markdown = self._html_to_markdown(soup, title, version)

            return RuleVersionContent(
                rule_number=history.rule_number,
                rule_title=title,
                effective_date=version.effective_date,
                obsolete_date=version.obsolete_date,
                is_current=version.is_current,
                url=version.url,
                markdown=markdown,
                explanatory_notes=history.explanatory_notes,
            )

        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.error(f"Request error for {version.url}: {e}")
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing {version.url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup, fallback_title: str) -> str:
        """Extract rule title from the version page."""
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        return fallback_title

    def _html_to_markdown(
        self, soup: BeautifulSoup, title: str, version: RuleVersion
    ) -> str:
        """Convert rule HTML content to clean markdown."""
        article = soup.find('article', class_='rule')
        if not article:
            # Fallback: try the main content area
            article = soup.find('article', class_='content-item')
        if not article:
            article = soup

        parts = [f"# {title}\n"]

        # Process the content elements within the article
        for element in article.children:
            if not hasattr(element, 'name') or element.name is None:
                continue

            # Skip the header (already captured title)
            if element.name == 'header':
                continue

            md = self._element_to_markdown(element, depth=0)
            if md.strip():
                parts.append(md)

        markdown = '\n'.join(parts)

        # Clean up excessive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        return markdown.strip() + '\n'

    def _element_to_markdown(self, element, depth: int = 0) -> str:
        """Recursively convert an HTML element to markdown."""
        if not hasattr(element, 'name') or element.name is None:
            text = str(element).strip()
            return text if text else ""

        tag = element.name

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            text = element.get_text().strip()
            if text:
                return f"\n{'#' * level} {text}\n"
            return ""

        if tag == 'p':
            text = self._paragraph_to_markdown(element)
            indent_level = self._get_indent_level(element)
            if indent_level > 0:
                prefix = '> ' * indent_level
                text = f"{prefix}{text}"
            return text + "\n\n"

        if tag == 'blockquote':
            return self._blockquote_to_markdown(element, depth) + "\n"

        if tag in ('ul', 'ol'):
            return self._list_to_markdown(element, tag) + "\n"

        if tag == 'table':
            return self._table_to_markdown(element) + "\n"

        if tag in ('div', 'section', 'article'):
            parts = []
            for child in element.children:
                md = self._element_to_markdown(child, depth)
                if md.strip():
                    parts.append(md)
            return '\n'.join(parts)

        # For any other elements, just extract text
        text = element.get_text().strip()
        return text if text else ""

    def _get_indent_level(self, element) -> int:
        """Derive nesting level from inline padding-left style.

        The ND Courts site uses padding-left on <p> tags to indicate
        sub-section depth (30px per level).
        """
        style = element.get('style', '')
        if not style:
            return 0
        match = re.search(r'padding-left:\s*(\d+)', style)
        if not match:
            return 0
        px = int(match.group(1))
        return max(px // 30, 0)

    def _paragraph_to_markdown(self, p: Tag) -> str:
        """Convert a paragraph element to markdown with inline formatting."""
        parts = []
        for child in p.children:
            if not hasattr(child, 'name') or child.name is None:
                parts.append(str(child))
            elif child.name in ('strong', 'b'):
                text = child.get_text()
                if text.strip():
                    parts.append(_wrap_emphasis(text, '**'))
            elif child.name in ('em', 'i'):
                text = child.get_text()
                if text.strip():
                    parts.append(_wrap_emphasis(text, '*'))
            elif child.name == 'a':
                text = child.get_text()
                href = child.get('href', '')
                if href and text.strip():
                    parts.append(f"[{text}]({href})")
                else:
                    parts.append(text)
            elif child.name == 'span':
                parts.append(child.get_text())
            elif child.name == 'br':
                parts.append('\n')
            else:
                parts.append(child.get_text())

        text = ''.join(parts).strip()
        # Clean up whitespace
        text = re.sub(r' +', ' ', text)
        text = text.replace('\xa0', ' ')
        return text

    def _blockquote_to_markdown(self, bq: Tag, depth: int) -> str:
        """Convert a blockquote to indented markdown text, handling nesting."""
        segments = []
        inline_parts = []

        def flush_inline():
            if inline_parts:
                text = ''.join(inline_parts).strip()
                text = re.sub(r' +', ' ', text)
                text = text.replace('\xa0', ' ')
                if text:
                    prefix = '> ' * (depth + 1)
                    segments.append(f"{prefix}{text}")
                inline_parts.clear()

        for child in bq.children:
            if not hasattr(child, 'name') or child.name is None:
                text = str(child)
                if text.strip():
                    inline_parts.append(text)
            elif child.name == 'blockquote':
                flush_inline()
                nested = self._blockquote_to_markdown(child, depth + 1)
                segments.append(nested)
            elif child.name in ('strong', 'b'):
                text = child.get_text()
                if text.strip():
                    inline_parts.append(_wrap_emphasis(text, '**'))
            elif child.name in ('em', 'i'):
                text = child.get_text()
                if text.strip():
                    inline_parts.append(_wrap_emphasis(text, '*'))
            elif child.name == 'span':
                inline_parts.append(child.get_text())
            elif child.name == 'br':
                flush_inline()
            elif child.name == 'a':
                text = child.get_text()
                href = child.get('href', '')
                if href and text.strip():
                    inline_parts.append(f"[{text}]({href})")
                else:
                    inline_parts.append(text)
            elif child.name == 'p':
                flush_inline()
                prefix = '> ' * (depth + 1)
                segments.append(f"{prefix}{self._paragraph_to_markdown(child)}")
            else:
                text = child.get_text().strip()
                if text:
                    inline_parts.append(text)

        flush_inline()
        return '\n\n'.join(segments)

    def _list_to_markdown(self, list_elem: Tag, list_type: str) -> str:
        """Convert a list to markdown."""
        items = []
        for i, li in enumerate(list_elem.find_all('li', recursive=False), 1):
            text = li.get_text().strip()
            if text:
                if list_type == 'ol':
                    items.append(f"{i}. {text}")
                else:
                    items.append(f"- {text}")
        return '\n'.join(items)

    def _table_to_markdown(self, table: Tag) -> str:
        """Convert a table to markdown."""
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text().strip() for td in tr.find_all(['td', 'th'])]
            if any(cells):
                rows.append('| ' + ' | '.join(cells) + ' |')
            # Add header separator after first row
            if tr.find('th') and len(rows) == 1:
                rows.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')
        return '\n'.join(rows)
