#!/usr/bin/env python3
"""
Focused Rule Parser for ND Court Rules.
Captures only essential metadata and content for rule proofreading.
"""

import re
import time
import hashlib
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, Tag


class FocusedRuleParser:
    """
    Focused rule parser that extracts only essential metadata and content
    for rule proofreading purposes.
    """

    def __init__(self, logger=None):
        """Initialize the focused rule parser."""
        self.logger = logger
        self.rule_patterns = [
            r'rule\s+(\d+(?:\.\d+)?)',
            r'§\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*[-–—]\s*',
            r'administrative\s+rule\s+(\d+(?:\.\d+)?)',
            r'rule\s+(\d+(?:\.\d+)?)\s*[-–—]'
        ]

    def parse_rule_page(self, html_content: str, source_url: str) -> Dict[str, Any]:
        """
        Parse a rule page and extract essential content and metadata.

        Args:
            html_content: Raw HTML content
            source_url: Source URL of the page

        Returns:
            Dictionary containing parsed rule data with focused metadata
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract basic page information
            title = self._extract_title(soup)
            rule_number = self._extract_rule_number(title, source_url)
            citation = self._extract_citation(rule_number, source_url)

            # Extract focused content (plain text and structured markdown only)
            content = self._extract_focused_content(soup)

            # Extract essential metadata only
            metadata = self._extract_essential_metadata(soup, source_url)

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
                    "structured_content": "# Error\n\nError occurred during parsing"
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
            if part.isdigit():
                if self.logger:
                    self.logger.debug(f"Extracted rule number from URL: {part}")
                return part

        return None

    def _extract_citation(self, rule_number: Optional[str], source_url: str) -> Optional[str]:
        """Generate legal citation for the rule."""
        if not rule_number:
            return None

        # Determine rule type from URL
        url_lower = source_url.lower()
        if 'appellate' in url_lower or 'ndrapp' in url_lower:
            rule_type = 'N.D.R.App.P.'
        elif 'civil' in url_lower or 'ndrcivp' in url_lower:
            rule_type = 'N.D.R.Civ.P.'
        elif 'criminal' in url_lower or 'ndrcrimp' in url_lower:
            rule_type = 'N.D.R.Crim.P.'
        elif 'evidence' in url_lower or 'ndrevid' in url_lower:
            rule_type = 'N.D.R.Evid.'
        elif 'court' in url_lower or 'ndrct' in url_lower:
            rule_type = 'N.D.R.Ct.'
        else:
            rule_type = 'N.D.R.Ct.'  # Default to court rules

        citation = f"{rule_type} {rule_number}"
        if self.logger:
            self.logger.debug(f"Generated citation: {citation} for rule {rule_number}")
        
        return citation

    def _extract_focused_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract only essential content: plain text and structured markdown."""
        # Clean the soup first
        self._clean_soup(soup)
        
        # Extract plain text
        plain_text = self._extract_plain_text(soup)
        
        # Generate structured markdown
        structured_content = self._generate_markdown(soup)
        
        return {
            "plain_text": plain_text,
            "structured_content": structured_content
        }

    def _clean_soup(self, soup: BeautifulSoup):
        """Clean the soup by removing unnecessary elements."""
        # Remove navigation, menus, footers, etc.
        for selector in [
            'nav', '.nav', '.navigation', '.menu', '.sidebar',
            'footer', '.footer', '.site-footer',
            '.breadcrumb', '.breadcrumbs',
            '.search', '.search-box',
            'script', 'style', 'noscript'
        ]:
            for elem in soup.select(selector):
                elem.decompose()

        # Remove elements with specific classes that are likely navigation
        for elem in soup.find_all(class_=re.compile(r'(nav|menu|sidebar|footer|breadcrumb)', re.I)):
            elem.decompose()
        
        # Remove PDF links and document links
        for elem in soup.find_all('a', href=True):
            href = elem.get('href', '').lower()
            text = elem.get_text().lower()
            
            # Remove PDF and document links
            if ('.pdf' in href or 'pdf' in text or 
                any(ext in href for ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'])):
                elem.decompose()
        
        # Remove elements that contain PDF-related text
        for elem in soup.find_all(text=True):
            if elem.parent and 'pdf' in elem.lower():
                # Check if this is a significant PDF reference
                parent_text = elem.parent.get_text().lower()
                if any(phrase in parent_text for phrase in ['download pdf', 'pdf version', 'pdf file', 'view pdf']):
                    elem.parent.decompose()
        
        # Remove elements containing PDF technical content
        for elem in soup.find_all(text=True):
            if elem.parent:
                text_lower = elem.lower()
                if any(pattern in text_lower for pattern in [
                    'procset[/pdf', 'subtype/form', 'type/xobject', 'stream',
                    'application/pdf', 'acrobat pdfmaker', 'adobe pdf library',
                    'metadata', 'pagelayout', 'structtreeroot', 'rotate', 'tabs',
                    'pdfmaker', 'adobe pdf'
                ]):
                    elem.parent.decompose()

    def _extract_plain_text(self, soup: BeautifulSoup) -> str:
        """Extract clean plain text from the soup."""
        # Get text and clean it up
        text = soup.get_text()
        
        # Remove PDF-related content
        text = self._remove_pdf_content(text)
        
        # Remove PDF stream content more aggressively
        text = self._remove_pdf_streams(text)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()

    def _generate_markdown(self, soup: BeautifulSoup) -> str:
        """Generate clean markdown from the soup."""
        markdown_parts = []
        
        # Process headings
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            level = int(heading.name[1])
            text = heading.get_text().strip()
            if text and not self._is_pdf_content(text):
                markdown_parts.append(f"{'#' * level} {text}\n")

        # Process paragraphs
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if text and not self._is_pdf_content(text):
                # Process emphasis within paragraphs
                processed_text = self._process_emphasis(p, text)
                markdown_parts.append(f"{processed_text}\n\n")

        # Process lists
        for ul in soup.find_all('ul'):
            for li in ul.find_all('li'):
                text = li.get_text().strip()
                if text and not self._is_pdf_content(text):
                    processed_text = self._process_emphasis(li, text)
                    markdown_parts.append(f"- {processed_text}\n")

        for ol in soup.find_all('ol'):
            for i, li in enumerate(ol.find_all('li'), 1):
                text = li.get_text().strip()
                if text and not self._is_pdf_content(text):
                    processed_text = self._process_emphasis(li, text)
                    markdown_parts.append(f"{i}. {processed_text}\n")

        # Join all parts
        markdown = ''.join(markdown_parts)
        
        # Clean up
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
        markdown = markdown.strip()
        
        return markdown

    def _process_emphasis(self, elem: Tag, text: str) -> str:
        """Process emphasis elements (bold, italic) in text."""
        # Handle bold
        for strong in elem.find_all(['strong', 'b']):
            strong_text = strong.get_text()
            text = text.replace(strong_text, f"**{strong_text}**")
        
        # Handle italic
        for em in elem.find_all(['em', 'i']):
            em_text = em.get_text()
            text = text.replace(em_text, f"*{em_text}*")
        
        return text

    def _extract_essential_metadata(self, soup: BeautifulSoup, source_url: str) -> Dict[str, Any]:
        """Extract only essential metadata for rule proofreading."""
        metadata = {
            "authority": None,
            "effective_date": None,
            "last_updated": None,
            "scraped_at": time.time()
        }

        text = soup.get_text()

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

        # Look for effective date and last updated information
        date_patterns = [
            (r'effective\s+date[:\s]*([^\n\r]+)', 'effective_date'),
            (r'last\s+updated[:\s]*([^\n\r]+)', 'last_updated'),
            (r'amended[:\s]*([^\n\r]+)', 'last_updated'),
            (r'effective[:\s]*([^\n\r]+)', 'effective_date')
        ]

        for pattern, field in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and not metadata[field]:
                metadata[field] = match.group(1).strip()

        return metadata

    def is_actual_rule(self, title: str, url: str) -> bool:
        """Determine if this is an actual rule vs committee/administrative information."""
        title_lower = title.lower()
        url_lower = url.lower()
        
        # Skip committee and administrative pages
        skip_keywords = [
            'committee', 'joint', 'commission', 'board', 'council',
            'administrative', 'administration', 'meeting', 'schedule',
            'agenda', 'minutes', 'contact', 'how do i'
        ]
        
        for keyword in skip_keywords:
            if keyword in title_lower or keyword in url_lower:
                return False
        
        # Look for actual rule indicators
        rule_indicators = [
            r'rule\s+\d+',
            r'§\s*\d+',
            r'procedure',
            r'evidence',
            r'conduct'
        ]
        
        for pattern in rule_indicators:
            if re.search(pattern, title_lower):
                return True
        
        return False

    def _is_rule_link(self, href: str, text: str) -> bool:
        """Determine if a link points to an actual rule page (not navigation/committee pages)."""
        href_lower = href.lower()
        text_lower = text.lower()

        # Skip PDF and document links
        if '.pdf' in href_lower or 'pdf' in text_lower:
            return False
        skip_extensions = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        for ext in skip_extensions:
            if ext in href_lower:
                return False

        # Blacklist: Skip committee/admin/navigation pages
        blacklist = [
            'committee', 'joint', 'meeting', 'agenda', 'minutes',
            'contact', 'tables', 'dockets', 'how-do-i'
        ]
        if any(pattern in href_lower for pattern in blacklist):
            return False

        # Whitelist: Only accept actual rule URLs
        # Pattern: /legal-resources/rules/{category}/{number} (current version)
        # Pattern: /legal-resources/rules/{category}/{number}-{version} (historical)
        rule_url_pattern = r'/legal-resources/rules/[a-z]+/\d+(?:-\d+)?$'
        return bool(re.search(rule_url_pattern, href_lower))
    
    def _remove_pdf_content(self, text: str) -> str:
        """Remove PDF-related content from text."""
        # Remove lines that contain PDF references
        lines = text.split('\n')
        filtered_lines = []
        
        pdf_patterns = [
            r'pdf',
            r'download.*pdf',
            r'pdf.*version',
            r'pdf.*file',
            r'view.*pdf',
            r'print.*pdf',
            r'pdf.*download',
            r'pdf.*format'
        ]
        
        for line in lines:
            line_lower = line.lower()
            
            # Skip lines that are primarily about PDFs
            if any(re.search(pattern, line_lower) for pattern in pdf_patterns):
                # Only skip if the line is mostly about PDFs (not just mentioning it in passing)
                if len(line.strip()) < 100 or any(phrase in line_lower for phrase in ['download', 'view', 'print', 'format']):
                    continue
            
            # Skip PDF metadata and stream content
            if any(pattern in line_lower for pattern in [
                'procset[/pdf', 'subtype/form', 'type/xobject', 'stream',
                'application/pdf', 'acrobat pdfmaker', 'adobe pdf library',
                'metadata', 'pagelayout', 'structtreeroot', 'rotate', 'tabs',
                'pdfmaker', 'adobe pdf'
            ]):
                continue
            
            # Skip lines that are just PDF technical content
            if re.search(r'<>.*pdf.*>', line_lower) or re.search(r'stream.*pdf', line_lower):
                continue
            
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _is_pdf_content(self, text: str) -> bool:
        """Check if text is primarily PDF-related content."""
        text_lower = text.lower()
        
        # Check for PDF-related patterns
        pdf_patterns = [
            r'pdf',
            r'download.*pdf',
            r'pdf.*version',
            r'pdf.*file',
            r'view.*pdf',
            r'print.*pdf',
            r'pdf.*download',
            r'pdf.*format'
        ]
        
        # If text is short and contains PDF references, it's likely PDF content
        if len(text.strip()) < 100:
            if any(re.search(pattern, text_lower) for pattern in pdf_patterns):
                return True
        
        # Check for specific PDF-related phrases
        pdf_phrases = [
            'download pdf', 'pdf version', 'pdf file', 'view pdf', 
            'print pdf', 'pdf download', 'pdf format', 'pdf document'
        ]
        
        # Check for PDF technical content
        pdf_technical = [
            'procset[/pdf', 'subtype/form', 'type/xobject', 'stream',
            'application/pdf', 'acrobat pdfmaker', 'adobe pdf library',
            'metadata', 'pagelayout', 'structtreeroot', 'rotate', 'tabs',
            'pdfmaker', 'adobe pdf'
        ]
        
        # Check for PDF technical patterns
        if any(pattern in text_lower for pattern in pdf_technical):
            return True
        
        # Check for PDF stream content
        if re.search(r'<>.*pdf.*>', text_lower) or re.search(r'stream.*pdf', text_lower):
            return True
        
        return any(phrase in text_lower for phrase in pdf_phrases)
    
    def _remove_pdf_streams(self, text: str) -> str:
        """Remove PDF stream content and technical metadata."""
        # Remove PDF stream patterns
        pdf_stream_patterns = [
            r'<>/ProcSet\[/PDF/Text\]>>/Subtype/Form/Type/XObject>>stream.*?stream',
            r'<>/Metadata.*?/StructTreeRoot.*?/Type/Catalog>>',
            r'<>/PageLayout/OneColumn/Pages.*?/Type/Page>>',
            r'<>/ProcSet\[/PDF/Text\]>>/Rotate.*?/Type/Page>>stream.*?stream',
            r'Acrobat PDFMaker.*?for Word',
            r'Adobe PDF Library.*?\d+\.\d+\.\d+',
            r'application/pdf',
            r'%∩┐╜∩┐╜∩┐╜∩┐╜',  # PDF header markers
        ]
        
        for pattern in pdf_stream_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove lines containing PDF technical content
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            line_lower = line.lower()
            # Skip lines with PDF technical content
            if any(pattern in line_lower for pattern in [
                'procset[/pdf', 'subtype/form', 'type/xobject', 'stream',
                'application/pdf', 'acrobat pdfmaker', 'adobe pdf library',
                'metadata', 'pagelayout', 'structtreeroot', 'rotate', 'tabs',
                'pdfmaker', 'adobe pdf', 'type/catalog', 'type/page'
            ]):
                continue
            
            # Skip lines that are just PDF technical markers
            if re.search(r'<>.*pdf.*>', line_lower) or re.search(r'stream.*pdf', line_lower):
                continue
            
            # Skip lines that are just PDF stream markers
            if re.search(r'%∩┐╜', line):
                continue
            
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)