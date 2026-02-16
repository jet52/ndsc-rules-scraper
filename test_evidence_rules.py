#!/usr/bin/env python3
"""
Test script to process just the Rules of Evidence category.
"""

import os
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.rule_parser_focused import FocusedRuleParser
from utils.logger import ScraperLogger


class EvidenceRulesProcessor:
    """Processor specifically for Rules of Evidence."""
    
    def __init__(self, raw_dir: str = 'data/raw', output_file: str = 'data/processed/evidence_rules_test.json'):
        self.raw_dir = Path(raw_dir)
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize parser and logger
        self.parser = FocusedRuleParser()
        self.logger = ScraperLogger("config.yaml", verbose=False)
        
        print(f"🔧 Initialized Evidence Rules Processor")
    
    def process_evidence_rules(self) -> Dict[str, Any]:
        """Process the Rules of Evidence category."""
        print("🔄 Processing Rules of Evidence...")
        print("=" * 50)
        
        # Find the evidence category file
        evidence_file = self.raw_dir / "category_evidence.html"
        if not evidence_file.exists():
            print(f"❌ Evidence category file not found: {evidence_file}")
            return None
        
        print(f"📁 Found evidence category file: {evidence_file}")
        
        # Process the evidence category
        start_time = time.time()
        category_data = self._process_category_file(evidence_file, "Evidence")
        
        if not category_data:
            print("❌ Failed to process evidence category")
            return None
        
        processing_time = time.time() - start_time
        
        # Create output data
        output_data = {
            "metadata": {
                "generated_at": time.time(),
                "source": "ND Courts Rules Scraper (Evidence Rules Test)",
                "version": "1.0",
                "schema_version": "1.0",
                "total_rules": len(category_data.get('rules', [])),
                "total_categories": 1,
                "processing_duration_seconds": processing_time,
                "processing_method": "evidence_rules_test",
                "category": "Evidence"
            },
            "data": {
                "categories": [category_data]
            }
        }
        
        # Save the output
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Evidence Rules processing complete!")
        print(f"📊 Statistics:")
        print(f"  - Rules processed: {len(category_data.get('rules', []))}")
        print(f"  - Processing time: {processing_time:.2f} seconds")
        print(f"  - Output file: {self.output_file}")
        
        return output_data
    
    def _process_category_file(self, category_file: Path, category_name: str) -> Optional[Dict[str, Any]]:
        """Process a single category file."""
        try:
            with open(category_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse the category page to find rule links
            rule_links = self._extract_rule_links_from_category(html_content, category_file)
            
            if not rule_links:
                print(f"  ⚠️  No rule links found in {category_name}")
                return None
            
            print(f"  📋 Found {len(rule_links)} rule links")
            
            # Process each rule
            rules = []
            for i, rule_link in enumerate(rule_links, 1):
                print(f"    🔄 Processing rule {i}/{len(rule_links)}: {rule_link['title']}")
                rule_data = self._process_rule_link(rule_link, category_name)
                if rule_data:
                    rules.append(rule_data)
                    print(f"      ✅ Success")
                else:
                    print(f"      ❌ Failed")
            
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
        from bs4 import BeautifulSoup
        
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
            print(f"      ❌ Error processing rule {rule_link['title']}: {e}")
            return None
    
    def _generate_citation(self, rule_number: Optional[str], category_name: str) -> Optional[str]:
        """Generate legal citation for the rule."""
        if not rule_number:
            return None
        
        # For evidence rules
        if 'evidence' in category_name.lower():
            return f"N.D.R.Evid. {rule_number}"
        else:
            return f"N.D.R.Ct. {rule_number}"


def main():
    """Main function to test evidence rules processing."""
    parser = argparse.ArgumentParser(description="Test processor for Rules of Evidence")
    parser.add_argument('--raw-dir', type=str, default='data/raw', help='Raw HTML directory')
    parser.add_argument('--output', type=str, default='data/processed/evidence_rules_test.json', help='Output file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    print("🔄 ND Court Rules - Evidence Rules Test")
    print("=" * 50)
    print(f"Processing Rules of Evidence...")
    print(f"Raw directory: {args.raw_dir}")
    print(f"Output file: {args.output}")
    
    # Validate inputs
    raw_dir = Path(args.raw_dir)
    if not raw_dir.exists():
        print(f"❌ Raw directory not found: {raw_dir}")
        return 1
    
    evidence_file = raw_dir / "category_evidence.html"
    if not evidence_file.exists():
        print(f"❌ Evidence category file not found: {evidence_file}")
        return 1
    
    # Create processor and run
    processor = EvidenceRulesProcessor(
        raw_dir=str(raw_dir),
        output_file=args.output
    )
    
    result = processor.process_evidence_rules()
    
    if result:
        print(f"\n✅ Successfully processed Evidence Rules!")
        print(f"📁 Output saved to: {processor.output_file}")
        print(f"📊 Generated {len(result['data']['categories'])} category with {result['metadata']['total_rules']} rules")
        
        # Show sample rule info
        if result['data']['categories'] and result['data']['categories'][0]['rules']:
            sample_rule = result['data']['categories'][0]['rules'][0]
            print(f"\n📋 Sample rule:")
            print(f"  Title: {sample_rule.get('title', 'N/A')}")
            print(f"  Citation: {sample_rule.get('citation', 'N/A')}")
            print(f"  Rule Number: {sample_rule.get('rule_number', 'N/A')}")
        
        return 0
    else:
        print("\n❌ Failed to process Evidence Rules")
        return 1


if __name__ == "__main__":
    exit(main()) 