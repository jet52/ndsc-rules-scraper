#!/usr/bin/env python3
"""
Summary of the comprehensive ND Court Rules scraping results.
"""

import json
from pathlib import Path

def main():
    """Display a summary of the scraping results."""
    print("ND Court Rules Scraping Summary")
    print("=" * 50)
    
    try:
        with open('data/processed/nd_court_rules_complete.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Basic statistics
        metadata = data['metadata']
        categories_data = data['data']['data']['categories']
        
        print(f"Total categories scraped: {len(categories_data)}")
        print(f"Total rules scraped: {metadata.get('total_rules', 'Unknown')}")
        print(f"File size: {Path('data/processed/nd_court_rules_complete.json').stat().st_size / (1024*1024):.2f} MB")
        print(f"Generated at: {metadata.get('generated_at', 'Unknown')}")
        
        print(f"\nCategories and Rule Counts:")
        print("-" * 40)
        
        total_rules = 0
        for category in categories_data:
            category_name = category.get('category_name', 'Unknown')
            rule_count = len(category.get('rules', []))
            total_rules += rule_count
            print(f"{category_name}: {rule_count} rules")
        
        print(f"\nTotal rules across all categories: {total_rules}")
        
        # Show some sample rules
        print(f"\nSample Rules from Each Category:")
        print("-" * 40)
        
        for category in categories_data[:5]:  # Show first 5 categories
            category_name = category.get('category_name', 'Unknown')
            rules = category.get('rules', [])
            
            if rules:
                sample_rule = rules[0]
                title = sample_rule.get('title', 'Unknown')
                rule_number = sample_rule.get('rule_number', 'Unknown')
                citation = sample_rule.get('citation', 'Unknown')
                
                print(f"\n{category_name}:")
                print(f"  Sample: {title}")
                print(f"  Rule #: {rule_number}")
                print(f"  Citation: {citation}")
        
        print(f"\nScraping Configuration:")
        print("-" * 40)
        print("Parser: FocusedRuleParser (essential metadata only)")
        print("Rate limiting: Disabled (maximum speed)")
        print("Output format: Single comprehensive JSON file")
        print("Content types: Plain text + Structured markdown")
        print("Metadata: Essential fields only (authority, dates, etc.)")
        
        print(f"\nNext Steps:")
        print("-" * 40)
        print("1. Review the scraped data for quality")
        print("2. Prepare data for Claude proofreading")
        print("3. Set up Claude API integration")
        print("4. Run proofreading analysis")
        
    except Exception as e:
        print(f"Error reading scraping results: {e}")

if __name__ == "__main__":
    main() 