"""
Rule parser for the ND Court Rules Scraper.
Extracts and parses individual court rules from HTML content.
"""

import re
import hashlib
import time
from typing import Dict, Any, Optional, List, Tuple
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, urlparse
from scraper.citation_extractor import CitationExtractor


class RuleParser:
    """Parses individual court rules from HTML content."""

    def __init__(self, logger=None, max_section_depth: int = 4):
        """
        Initialize the rule parser.

        Args:
            logger: Logger instance
            max_section_depth: Maximum depth for section nesting (default: 4)
        """
        self.logger = logger
        self.citation_extractor = CitationExtractor(logger)
        self.max_section_depth = max_section_depth

        # Common patterns for rule identification
        self.rule_patterns = [
            r'Rule\s+(\d+[A-Z]*)',  # Rule 1, Rule 1A, etc.
            r'§\s*(\d+[A-Z]*)',     # § 1, § 1A, etc.
            r'(\d+[A-Z]*)\.',       # 1., 1A., etc.
        ]

    def parse_rule_page(self, html_content: str, source_url: str) -> Dict[str, Any]:
        """
        Parse a rule page and extract structured content.

        Args:
            html_content: Raw HTML content
            source_url: Source URL of the page

        Returns:
            Dictionary containing parsed rule data
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract basic page information
            title = self._extract_title(soup)
            rule_number = self._extract_rule_number(title, source_url)
            citation = self._extract_citation(rule_number, source_url)

            # Extract content with both plain text and structured format
            content = self._extract_content(soup)

            # Extract comprehensive metadata
            metadata = self._extract_metadata(soup, source_url, html_content)

            parsed_rule = {
                "title": title,
                "rule_number": rule_number,
                "citation": citation,
                "source_url": source_url,
                "content": content,
                "metadata": metadata
            }

            if self.logger:
                self.logger.debug(f"Successfully parsed rule: {title}")

            return parsed_rule

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error parsing rule page: {e}")
            return {
                "title": "Error parsing rule",
                "rule_number": None,
                "citation": None,
                "content": {
                    "plain_text": "Error occurred during parsing",
                    "structured_content": "# Error\n\nError occurred during parsing",
                    "sections": [],
                    "structure": []
                },
                "source_url": source_url,
                "metadata": {"error": str(e)}
            }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the title of the rule."""
        # Try multiple selectors for title
        title_selectors = [
            'h1',
            'h2',
            '.title',
            '.rule-title',
            '[class*="title"]',
            'title'
        ]

        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                title = title_elem.get_text().strip()
                if self.logger:
                    self.logger.debug(f"Found title using selector '{selector}': {title}")
                return title

        # Fallback: look for the first heading
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            if heading.get_text().strip():
                title = heading.get_text().strip()
                if self.logger:
                    self.logger.debug(f"Found title from heading: {title}")
                return title

        return "Untitled Rule"

    def _extract_rule_number(self, title: str, url: str) -> Optional[str]:
        """Extract rule number from title or URL."""
        # Try to extract from title first
        for pattern in self.rule_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                rule_num = match.group(1)
                if self.logger:
                    self.logger.debug(f"Extracted rule number from title: {rule_num}")
                return rule_num

        # Try to extract from URL
        url_path = urlparse(url).path
        path_parts = url_path.split('/')
        for part in path_parts:
            for pattern in self.rule_patterns:
                match = re.search(pattern, part, re.IGNORECASE)
                if match:
                    rule_num = match.group(1)
                    if self.logger:
                        self.logger.debug(f"Extracted rule number from URL: {rule_num}")
                    return rule_num

        return None

    def _extract_citation(self, rule_number: Optional[str], source_url: str) -> Optional[str]:
        """Extract proper citation for the rule."""
        if not rule_number:
            return None

        return self.citation_extractor.generate_citation(rule_number, source_url)

    def _extract_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract the main content of the rule."""
        content = {
            "plain_text": "",
            "structured_content": "",
            "sections": [],
            "structure": []
        }

        # Remove navigation, headers, footers, etc.
        self._clean_soup(soup)

        # Extract plain text
        content["plain_text"] = self._extract_plain_text(soup)
        
        # Extract structured content
        content["sections"] = self._extract_sections(soup)
        content["structure"] = self._extract_structure(soup)
        
        # Generate markdown content
        content["structured_content"] = self._generate_markdown(soup)

        return content

    def _clean_soup(self, soup: BeautifulSoup):
        """Remove unwanted elements from the soup."""
        # Remove common unwanted elements
        unwanted_selectors = [
            'nav',
            'header',
            'footer',
            '.navigation',
            '.menu',
            '.sidebar',
            '.breadcrumb',
            '.search',
            'script',
            'style',
            '.advertisement',
            '.ads'
        ]

        for selector in unwanted_selectors:
            for elem in soup.select(selector):
                elem.decompose()

    def _extract_plain_text(self, soup: BeautifulSoup) -> str:
        """Extract plain text content."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text

    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract structured sections from the content with depth limiting."""
        sections = []
        current_section = None
        section_stack = []

        for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div']):
            if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(elem.name[1])
                
                # Limit depth to max_section_depth
                if level > self.max_section_depth:
                    level = self.max_section_depth
                
                # Create new section
                new_section = {
                    "heading": elem.get_text().strip(),
                    "level": level,
                    "content": [],
                    "subsections": []
                }

                # Find appropriate parent based on level
                while section_stack and section_stack[-1]["level"] >= level:
                    section_stack.pop()

                if section_stack:
                    # Add to parent's subsections
                    section_stack[-1]["subsections"].append(new_section)
                else:
                    # Top-level section
                    sections.append(new_section)

                section_stack.append(new_section)
                current_section = new_section

            elif current_section and elem.name in ['p', 'div']:
                # Add content to current section
                text = elem.get_text().strip()
                if text:
                    current_section["content"].append({
                        "type": elem.name,
                        "text": text,
                        "html": str(elem)
                    })

        return sections

    def _extract_structure(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract document structure (headings, lists, etc.)."""
        structure = []

        for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'table']):
            if elem.name.startswith('h'):
                level = int(elem.name[1])
                # Limit depth
                if level > self.max_section_depth:
                    level = self.max_section_depth
                    
                structure.append({
                    "type": "heading",
                    "level": level,
                    "text": elem.get_text().strip(),
                    "tag": elem.name
                })
            elif elem.name in ['ul', 'ol']:
                items = [li.get_text().strip() for li in elem.find_all('li')]
                structure.append({
                    "type": "list",
                    "list_type": elem.name,
                    "items": items,
                    "count": len(items)
                })
            elif elem.name == 'table':
                structure.append({
                    "type": "table",
                    "rows": len(elem.find_all('tr')),
                    "columns": len(elem.find_all('th')) or len(elem.find_all('td', limit=1))
                })

        return structure

    def _generate_markdown(self, soup: BeautifulSoup) -> str:
        """Generate markdown content from the soup."""
        markdown_lines = []
        
        for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'strong', 'em', 'br']):
            if elem.name.startswith('h'):
                level = int(elem.name[1])
                # Limit depth
                if level > self.max_section_depth:
                    level = self.max_section_depth
                    
                heading_text = elem.get_text().strip()
                if heading_text:
                    markdown_lines.append(f"{'#' * level} {heading_text}")
                    markdown_lines.append("")  # Empty line after heading
                    
            elif elem.name == 'p':
                text = elem.get_text().strip()
                if text:
                    # Handle emphasis
                    text = self._process_emphasis(elem, text)
                    markdown_lines.append(text)
                    markdown_lines.append("")  # Empty line after paragraph
                    
            elif elem.name in ['ul', 'ol']:
                items = elem.find_all('li')
                for i, item in enumerate(items):
                    item_text = item.get_text().strip()
                    if item_text:
                        if elem.name == 'ul':
                            markdown_lines.append(f"- {item_text}")
                        else:
                            markdown_lines.append(f"{i+1}. {item_text}")
                markdown_lines.append("")  # Empty line after list
                
            elif elem.name == 'br':
                markdown_lines.append("")  # Line break

        return "\n".join(markdown_lines)

    def _process_emphasis(self, elem: Tag, text: str) -> str:
        """Process emphasis tags in text."""
        # Handle bold
        for strong in elem.find_all('strong'):
            strong_text = strong.get_text()
            text = text.replace(strong_text, f"**{strong_text}**")
            
        # Handle italic
        for em in elem.find_all('em'):
            em_text = em.get_text()
            text = text.replace(em_text, f"*{em_text}*")
            
        return text

    def _extract_metadata(self, soup: BeautifulSoup, source_url: str, html_content: str) -> Dict[str, Any]:
        """Extract comprehensive metadata from the page."""
        metadata = {
            "last_updated": None,
            "effective_date": None,
            "authority": None,
            "related_rules": [],
            "cross_references": [],
            "scraped_at": time.time(),
            "file_size_bytes": len(html_content),
            "html_checksum": self._generate_checksum(html_content)
        }

        # Look for last updated information
        update_patterns = [
            r'last\s+updated[:\s]*([^\n\r]+)',
            r'effective[:\s]*([^\n\r]+)',
            r'date[:\s]*([^\n\r]+)',
            r'amended[:\s]*([^\n\r]+)'
        ]

        text = soup.get_text()
        for pattern in update_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["last_updated"] = match.group(1).strip()
                break

        # Look for authority information
        authority_patterns = [
            r'supreme\s+court',
            r'court\s+of\s+appeals',
            r'judicial\s+conduct\s+commission',
            r'state\s+bar\s+association'
        ]

        for pattern in authority_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                metadata["authority"] = pattern.replace('\\s+', ' ').title()
                break

        # Look for cross-references
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href')
            if href and ('rule' in href.lower() or 'ndr' in href.lower()):
                metadata["cross_references"].append({
                    "text": link.get_text().strip(),
                    "url": urljoin(source_url, href)
                })

        # Look for related rules within the same category
        # This will be populated by the main scraper when processing categories
        metadata["related_rules"] = []

        return metadata

    def _generate_checksum(self, content: str) -> str:
        """Generate SHA256 checksum for content integrity."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def parse_rule_list_page(self, html_content: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Parse a page that lists multiple rules.

        Args:
            html_content: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            List of rule information dictionaries
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            rules = []

            # Look for links that might be rules
            links = soup.find_all('a', href=True)

            for link in links:
                href = link.get('href')
                text = link.get_text().strip()

                # Check if this looks like a rule link
                if self._is_rule_link(href, text):
                    rule_info = {
                        "title": text,
                        "url": urljoin(base_url, href),
                        "rule_number": self._extract_rule_number(text, href)
                    }
                    rules.append(rule_info)

            if self.logger:
                self.logger.debug(f"Found {len(rules)} potential rules on list page")

            return rules

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error parsing rule list page: {e}")
            return []

    def _is_rule_link(self, href: str, text: str) -> bool:
        """Determine if a link likely points to a rule."""
        # Check URL patterns
        url_patterns = [
            r'rule',
            r'ndr',
            r'procedure',
            r'evidence',
            r'conduct'
        ]

        # Check text patterns
        text_patterns = [
            r'rule\s+\d+',
            r'§\s*\d+',
            r'procedure',
            r'evidence',
            r'conduct'
        ]

        href_lower = href.lower()
        text_lower = text.lower()

        # Check if URL matches any pattern
        for pattern in url_patterns:
            if re.search(pattern, href_lower):
                return True

        # Check if text matches any pattern
        for pattern in text_patterns:
            if re.search(pattern, text_lower):
                return True

        return False 