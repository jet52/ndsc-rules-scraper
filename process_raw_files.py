#!/usr/bin/env python3
"""
Process existing raw HTML files to generate comprehensive JSON output.
This avoids re-scraping the website by using already downloaded HTML files.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.rule_parser_focused import FocusedRuleParser
from utils.logger import ScraperLogger


class RawFileProcessor:
    """Process existing raw HTML files to generate JSON output."""
    
    def __init__(self, raw_dir: str = 'data/raw', output_file: str = 'data/processed/nd_court_rules_complete.json'):
        self.raw_dir = Path(raw_dir)
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize parser and logger
        self.parser = FocusedRuleParser()
        self.logger = ScraperLogger("config.yaml", verbose=False)
        
        # Statistics
        self.stats = {
            "total_categories_processed": 0,
            "total_rules_processed": 0,
            "successful_rules": 0,
            "failed_rules": 0,
            "start_time": time.time()
        }
    
    def process_all_categories(self) -> Dict[str, Any]:
        """Process all category files and generate comprehensive JSON."""
        print("🔄 Processing existing raw HTML files...")
        print("=" * 60)
        
        # Find all category files
        category_files = list(self.raw_dir.glob("category_*.html"))
        print(f"📁 Found {len(category_files)} category files")
        
        all_categories = []
        
        for category_file in category_files:
            category_name = self._extract_category_name(category_file.name)
            print(f"\n📋 Processing category: {category_name}")
            
            # Process this category
            category_data = self._process_category_file(category_file, category_name)
            if category_data and category_data.get('rules'):
                all_categories.append(category_data)
                self.stats["total_categories_processed"] += 1
                print(f"  ✅ Found {len(category_data['rules'])} rules")
            else:
                print(f"  ⚠️  No rules found in {category_name}")
        
        # Create comprehensive output
        self.stats["end_time"] = time.time()
        total_rules = sum(len(cat.get('rules', [])) for cat in all_categories)
        
        output_data = {
            "metadata": {
                "generated_at": time.time(),
                "source": "ND Courts Rules Scraper (Raw File Processing)",
                "version": "1.0",
                "schema_version": "1.0",
                "total_rules": total_rules,
                "total_categories": len(all_categories),
                "processing_duration_seconds": self.stats["end_time"] - self.stats["start_time"],
                "processing_method": "raw_html_files"
            },
            "data": {
                "categories": all_categories
            }
        }
        
        # Save the output
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Processing complete!")
        print(f"📊 Statistics:")
        print(f"  - Categories processed: {self.stats['total_categories_processed']}")
        print(f"  - Total rules: {total_rules}")
        print(f"  - Successful rules: {self.stats['successful_rules']}")
        print(f"  - Failed rules: {self.stats['failed_rules']}")
        print(f"  - Output file: {self.output_file}")
        
        return output_data
    
    def _extract_category_name(self, filename: str) -> str:
        """Extract category name from filename."""
        # Remove 'category_' prefix and '.html' suffix
        name = filename.replace('category_', '').replace('.html', '')
        
        # Convert underscores to spaces and title case
        name = name.replace('_', ' ').title()
        
        # Handle special cases
        name = name.replace('And', 'and')
        name = name.replace('Of', 'of')
        name = name.replace('To', 'to')
        name = name.replace('By', 'by')
        
        return name
    
    def _process_category_file(self, category_file: Path, category_name: str) -> Optional[Dict[str, Any]]:
        """Process a single category file."""
        try:
            with open(category_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse the category page to find rule links
            rule_links = self._extract_rule_links_from_category(html_content, category_file)
            
            if not rule_links:
                return None
            
            # Process each rule
            rules = []
            for rule_link in rule_links:
                rule_data = self._process_rule_link(rule_link, category_name)
                if rule_data:
                    rules.append(rule_data)
                    self.stats["successful_rules"] += 1
                else:
                    self.stats["failed_rules"] += 1
                
                self.stats["total_rules_processed"] += 1
            
            return {
                "category_name": category_name,
                "category_url": f"https://www.ndcourts.gov/legal-resources/rules/{category_name.lower().replace(' ', '-')}",
                "rule_count": len(rules),
                "rules": rules
            }
            
        except Exception as e:
            print(f"  ❌ Error processing {category_name}: {e}")
            return None
    
    def _extract_rule_links_from_category(self, html_content: str, category_file: Path) -> List[Dict[str, Any]]:
        """Extract rule links from a category page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        rule_links = []
        
        # Look for links that might be rules
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href')
            text = link.get_text().strip()
            
            # Check if this looks like a rule link
            if self._is_rule_link(href, text):
                # Create a mock rule link object
                rule_info = {
                    "title": text,
                    "url": href if href.startswith('http') else f"https://www.ndcourts.gov{href}",
                    "rule_number": self._extract_rule_number_from_text(text),
                    "html_content": self._get_rule_html_content(href, text)
                }
                rule_links.append(rule_info)
        
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
        return self.parser._is_rule_link(href, text)
    
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
    
    def _get_rule_html_content(self, href: str, title: str) -> Optional[str]:
        """Get HTML content for a rule from existing raw files."""
        # Look for matching rule files in the raw directory
        rule_files = list(self.raw_dir.glob("rule_*.html"))
        
        # Try to find a file that might contain this rule
        for rule_file in rule_files:
            try:
                with open(rule_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if this file contains the rule title
                if title.lower() in content.lower():
                    return content
            except:
                continue
        
        return None
    
    def _process_rule_link(self, rule_link: Dict[str, Any], category_name: str) -> Optional[Dict[str, Any]]:
        """Process a single rule link."""
        try:
            html_content = rule_link.get('html_content')
            
            if not html_content:
                # If we don't have the HTML content, create a placeholder
                return {
                    "title": rule_link['title'],
                    "rule_number": rule_link['rule_number'],
                    "citation": self._generate_citation(rule_link['rule_number'], category_name),
                    "source_url": rule_link['url'],
                    "content": {
                        "plain_text": f"Content for {rule_link['title']} not available in raw files",
                        "structured_content": f"# {rule_link['title']}\n\nContent not available in raw files."
                    },
                    "metadata": {
                        "authority": "North Dakota Supreme Court",
                        "effective_date": None,
                        "last_updated": None,
                        "scraped_at": time.time()
                    }
                }
            
            # Parse the rule using the focused parser
            parsed_rule = self.parser.parse_rule_page(html_content, rule_link['url'])
            
            # Add category information
            parsed_rule['category'] = category_name
            
            return parsed_rule
            
        except Exception as e:
            print(f"    ❌ Error processing rule {rule_link['title']}: {e}")
            return None
    
    def _generate_citation(self, rule_number: Optional[str], category_name: str) -> Optional[str]:
        """Generate legal citation for the rule."""
        if not rule_number:
            return None
        
        # Determine rule type from category name
        category_lower = category_name.lower()
        if 'appellate' in category_lower:
            rule_type = 'N.D.R.App.P.'
        elif 'civil' in category_lower:
            rule_type = 'N.D.R.Civ.P.'
        elif 'criminal' in category_lower:
            rule_type = 'N.D.R.Crim.P.'
        elif 'evidence' in category_lower:
            rule_type = 'N.D.R.Evid.'
        elif 'court' in category_lower:
            rule_type = 'N.D.R.Ct.'
        else:
            rule_type = 'N.D.R.Ct.'  # Default
        
        return f"{rule_type} {rule_number}"


def main():
    """Main function to process raw files."""
    print("🔄 ND Court Rules - Raw File Processor")
    print("=" * 60)
    print("Processing existing raw HTML files to generate comprehensive JSON...")
    
    processor = RawFileProcessor()
    result = processor.process_all_categories()
    
    if result:
        print(f"\n✅ Successfully processed raw files!")
        print(f"📁 Output saved to: {processor.output_file}")
        print(f"📊 Generated {len(result['data']['categories'])} categories with {result['metadata']['total_rules']} total rules")
    else:
        print("\n❌ Failed to process raw files")


if __name__ == "__main__":
    main() 