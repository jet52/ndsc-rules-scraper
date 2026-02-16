"""
Main scraper for North Dakota Court Rules.
Orchestrates the entire scraping process.
"""

import time
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from retrying import retry
from tqdm import tqdm
import yaml

from utils.logger import ScraperLogger
from utils.file_utils import FileManager
from scraper.rule_parser_focused import FocusedRuleParser
from scraper.citation_extractor import CitationExtractor


class NDCourtsScraper:
    """Main scraper for North Dakota Court Rules."""
    
    def __init__(self, config_path: str = "config.yaml", verbose: bool = False):
        """
        Initialize the scraper.

        Args:
            config_path: Path to configuration file
            verbose: Enable verbose logging
        """
        self.logger = ScraperLogger(config_path, verbose)
        self.file_manager = FileManager(config_path, self.logger)
        
        # Load configuration first
        self.config = self._load_config(config_path)
        
        # Initialize focused rule parser
        self.rule_parser = FocusedRuleParser(self.logger)
        self.citation_extractor = CitationExtractor(self.logger)
        
        self.session = self._create_session()
        
        # Statistics
        self.stats = {
            "total_rules_scraped": 0,
            "successful_rules": 0,
            "failed_rules": 0,
            "categories_processed": 0,
            "start_time": None,
            "end_time": None
        }
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found. Using defaults.")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing config file: {e}")
            return {}
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with proper headers and configuration."""
        session = requests.Session()
        
        # Set headers
        user_agent = self.config.get('scraping', {}).get('user_agent', 
                                                        'ND-Court-Rules-Scraper/1.0')
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Handle SSL certificate issues
        try:
            import ssl
            import certifi
            session.verify = certifi.where()
        except ImportError:
            # If certifi is not available, disable SSL verification as fallback
            session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        return session
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """
        Make an HTTP request with retry logic.
        
        Args:
            url: URL to request
        
        Returns:
            Response object or None if failed
        """
        try:
            timeout = self.config.get('scraping', {}).get('timeout', 30)
            response = self.session.get(url, timeout=timeout)
            
            self.logger.log_request(url, "GET", response.status_code)
            
            if response.status_code == 200:
                return response
            else:
                self.logger.warning(f"HTTP {response.status_code} for {url}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            raise
    
    def scrape_all_rules(self) -> Dict[str, Any]:
        """
        Scrape all North Dakota court rules.
        
        Returns:
            Dictionary containing scraping results and statistics
        """
        self.logger.info("Starting North Dakota Court Rules scraping...")
        self.stats["start_time"] = time.time()
        
        # Get the main rules page
        base_url = self.config.get('scraping', {}).get('base_url', 
                                                      'https://www.ndcourts.gov/legal-resources/rules')
        
        try:
            response = self._make_request(base_url)
            if not response:
                raise Exception("Failed to fetch main rules page")
            
            # Parse the main page to find rule categories
            rule_categories = self._extract_rule_categories(response.text, base_url)
            
            all_rules = {}
            
            # Process each category
            for category in rule_categories:
                self.logger.info(f"Processing category: {category['name']}")
                category_rules = self._scrape_category(category)
                all_rules[category['name']] = category_rules
                self.stats["categories_processed"] += 1
            
            self.stats["end_time"] = time.time()
            self._save_results(all_rules)
            
            return {
                "rules": all_rules,
                "statistics": self.stats,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}")
            return {
                "rules": {},
                "statistics": self.stats,
                "success": False,
                "error": str(e)
            }
    
    def _extract_rule_categories(self, html_content: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract rule categories from the main rules page.
        
        Args:
            html_content: HTML content of the main page
            base_url: Base URL for resolving relative links
        
        Returns:
            List of category information dictionaries
        """
        categories = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Save raw HTML for debugging
        self.file_manager.save_raw_html(html_content, "main_rules_page")
        
        # Look for category links
        # Based on the website structure, we'll look for links that match our known categories
        known_categories = self.config.get('rule_categories', [])
        
        for category_name in known_categories:
            # Look for links that contain the category name
            category_links = soup.find_all('a', href=True, 
                                         string=lambda text: text and category_name.lower() in text.lower())
            
            if category_links:
                for link in category_links:
                    href = link.get('href')
                    if href:
                        category_url = urljoin(base_url, href)
                        categories.append({
                            "name": category_name,
                            "url": category_url,
                            "link_text": link.get_text().strip()
                        })
                        self.logger.debug(f"Found category link: {category_name} -> {category_url}")
                        break
            else:
                # If no direct link found, create a potential URL
                potential_url = self._generate_category_url(base_url, category_name)
                categories.append({
                    "name": category_name,
                    "url": potential_url,
                    "link_text": category_name
                })
                self.logger.debug(f"Generated potential category URL: {category_name} -> {potential_url}")
        
        self.logger.info(f"Found {len(categories)} rule categories")
        return categories
    
    def _generate_category_url(self, base_url: str, category_name: str) -> str:
        """
        Generate a potential URL for a category based on common patterns.
        
        Args:
            base_url: Base URL
            category_name: Name of the category
        
        Returns:
            Generated URL
        """
        # Convert category name to URL-friendly format
        url_name = category_name.lower().replace(' ', '-').replace('&', 'and')
        
        # Common URL patterns
        url_patterns = [
            f"{base_url}/{url_name}",
            f"{base_url}/{url_name}-rules",
            f"{base_url}/rules/{url_name}",
            f"{base_url}/rules/{url_name}-rules"
        ]
        
        return url_patterns[0]  # Return the first pattern as default
    
    def _scrape_category(self, category: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape all rules in a category.
        
        Args:
            category: Category information dictionary
        
        Returns:
            List of scraped rules
        """
        category_rules = []
        
        try:
            # Fetch the category page
            response = self._make_request(category['url'])
            if not response:
                self.logger.warning(f"Failed to fetch category page: {category['name']}")
                return category_rules
            
            # Save raw HTML
            filename = f"category_{category['name'].lower().replace(' ', '_')}"
            self.file_manager.save_raw_html(response.text, filename)
            
            # Parse the category page to find individual rules
            rule_links = self._extract_rule_links(response.text, category['url'])
            
            self.logger.info(f"Found {len(rule_links)} rules in category: {category['name']}")
            
            # Scrape each rule
            for i, rule_link in enumerate(rule_links):
                self.logger.log_scraping_progress(category['name'], i + 1, len(rule_links))
                
                rule_data = self._scrape_individual_rule(rule_link)
                if rule_data:
                    category_rules.append(rule_data)
                    self.stats["successful_rules"] += 1
                else:
                    self.stats["failed_rules"] += 1
                
                self.stats["total_rules_scraped"] += 1
            
            return category_rules
            
        except Exception as e:
            self.logger.error(f"Error scraping category {category['name']}: {e}")
            return category_rules
    
    def _extract_rule_links(self, html_content: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract links to individual rules from a category page.
        
        Args:
            html_content: HTML content of the category page
            base_url: Base URL for resolving relative links
        
        Returns:
            List of rule link information dictionaries
        """
        rule_links = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for links that might be rules
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href')
            text = link.get_text().strip()
            
            # Check if this looks like a rule link
            if self._is_rule_link(href, text):
                rule_url = urljoin(base_url, href)
                rule_info = {
                    "title": text,
                    "url": rule_url,
                    "rule_number": self._extract_rule_number_from_text(text)
                }
                rule_links.append(rule_info)
                self.logger.debug(f"Found rule link: {text} -> {rule_url}")
        
        return rule_links
    
    def _is_rule_link(self, href: str, text: str) -> bool:
        """Determine if a link likely points to a rule."""
        # Skip PDF and document links
        href_lower = href.lower()
        text_lower = text.lower()
        
        # Skip PDF links
        if '.pdf' in href_lower or 'pdf' in text_lower:
            return False
        
        # Skip other document formats
        skip_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        for ext in skip_extensions:
            if ext in href_lower:
                return False
        
        # Use the rule parser's method
        return self.rule_parser._is_rule_link(href, text)
    
    def _extract_rule_number_from_text(self, text: str) -> Optional[str]:
        """Extract rule number from text."""
        import re
        
        patterns = [
            r'Rule\s+(\d+[A-Z]*)',
            r'§\s*(\d+[A-Z]*)',
            r'(\d+[A-Z]*)\.'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _scrape_individual_rule(self, rule_link: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Scrape an individual rule page.
        
        Args:
            rule_link: Rule link information dictionary
        
        Returns:
            Parsed rule data or None if failed
        """
        try:
            # Skip PDF files entirely
            if self._is_pdf_file(rule_link['url']):
                self.logger.warning(f"Skipping PDF file: {rule_link['title']} -> {rule_link['url']}")
                return None
            
            # Fetch the rule page
            response = self._make_request(rule_link['url'])
            if not response:
                self.logger.warning(f"Failed to fetch rule page: {rule_link['title']}")
                return None
            
            # Check if the response is actually a PDF
            if self._is_pdf_response(response):
                self.logger.warning(f"Skipping PDF response: {rule_link['title']} -> {rule_link['url']}")
                return None
            
            # Save raw HTML
            filename = f"rule_{rule_link['rule_number'] or 'unknown'}_{int(time.time())}"
            self.file_manager.save_raw_html(response.text, filename)
            
            # Parse the rule
            parsed_rule = self.rule_parser.parse_rule_page(response.text, rule_link['url'])
            
            # Add additional metadata
            parsed_rule.update({
                "category": rule_link.get("category"),
                "scraped_at": time.time(),
                "file_size": len(response.text)
            })
            
            self.logger.log_rule_processing(rule_link['title'], True)
            return parsed_rule
            
        except Exception as e:
            self.logger.log_rule_processing(rule_link['title'], False, str(e))
            return None
    
    def _is_pdf_file(self, url: str) -> bool:
        """Check if URL points to a PDF file."""
        url_lower = url.lower()
        return '.pdf' in url_lower
    
    def _is_pdf_response(self, response: requests.Response) -> bool:
        """Check if response contains PDF content."""
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'application/pdf' in content_type:
            return True
        
        # Check if response text contains PDF markers
        text = response.text[:1000]  # Check first 1000 characters
        pdf_markers = [
            '%PDF-',  # PDF header
            'application/pdf',
            'ProcSet[/PDF',
            'Type/Catalog',
            'Type/Page'
        ]
        
        return any(marker in text for marker in pdf_markers)
    
    def _save_results(self, all_rules: Dict[str, Any]):
        """Save scraping results to files."""
        # Check if single file output is enabled
        single_file = self.config.get('output', {}).get('json_schema', {}).get('single_file_output', True)
        
        if single_file:
            # Create comprehensive single file with all rules
            total_rules = sum(len(rules) for rules in all_rules.values())
            
            master_data = {
                "metadata": {
                    "generated_at": time.time(),
                    "source": "ND Courts Rules Scraper",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "total_rules": total_rules,
                    "total_categories": len(all_rules),
                    "scraping_duration_seconds": self.stats.get("end_time", 0) - self.stats.get("start_time", 0) if self.stats.get("end_time") else 0
                },
                "data": {
                    "categories": []
                }
            }
            
            # Add each category with its rules
            for category_name, rules in all_rules.items():
                category_data = {
                    "category_name": category_name,
                    "category_url": f"https://www.ndcourts.gov/legal-resources/rules/{category_name.lower().replace(' ', '-')}",
                    "rule_count": len(rules),
                    "rules": rules
                }
                master_data["data"]["categories"].append(category_data)
            
            # Save the master file
            self.file_manager.save_json(master_data, "nd_court_rules_complete")
            self.logger.info(f"Saved single comprehensive file with {total_rules} rules across {len(all_rules)} categories")
            
        else:
            # Save each category as a separate JSON file (legacy behavior)
            for category_name, rules in all_rules.items():
                filename = category_name.lower().replace(' ', '_').replace('&', 'and')

                category_data = {
                    "category_name": category_name,
                    "rules": rules,
                    "rule_count": len(rules),
                    "scraped_at": time.time()
                }

                self.file_manager.save_json(category_data, filename)

        # Save overall statistics
        stats_data = {
            "scraping_statistics": self.stats,
            "categories": list(all_rules.keys()),
            "total_categories": len(all_rules),
            "total_rules": sum(len(rules) for rules in all_rules.values())
        }

        self.file_manager.save_json(stats_data, "scraping_statistics", "metadata")

        self.logger.info(f"Saved {'single comprehensive file' if single_file else f'{len(all_rules)} category files'} and statistics")
    
    def get_scraping_statistics(self) -> Dict[str, Any]:
        """Get current scraping statistics."""
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = self.stats["end_time"] - self.stats["start_time"]
            self.stats["duration_seconds"] = duration
            self.stats["duration_minutes"] = duration / 60
        
        return self.stats.copy()
    
    def cleanup(self):
        """Clean up resources."""
        if self.session:
            self.session.close()
        
        self.logger.info("Scraper cleanup completed") 