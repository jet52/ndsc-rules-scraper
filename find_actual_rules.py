#!/usr/bin/env python3
"""
Script to find actual numbered rules in the scraped data.
"""

import json

def find_actual_rules():
    """Find actual numbered rules in the scraped data."""
    try:
        with open('data/processed/nd_court_rules_complete.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("🔍 Finding Actual Numbered Rules")
        print("=" * 50)
        
        categories = data['data']['data']['categories']
        
        for category in categories:
            category_name = category.get('category_name', 'Unknown')
            print(f"\n📋 Category: {category_name}")
            
            rules = category.get('rules', [])
            actual_rules = []
            
            for rule in rules:
                title = rule.get('title', '')
                rule_number = rule.get('rule_number', '')
                
                # Look for actual numbered rules
                if rule_number and rule_number.isdigit():
                    actual_rules.append((rule_number, title))
                elif any(word in title.lower() for word in ['rule', 'procedure', 'evidence']):
                    # Check if it has a number in the title
                    import re
                    numbers = re.findall(r'\d+', title)
                    if numbers:
                        actual_rules.append((numbers[0], title))
            
            print(f"Found {len(actual_rules)} potential actual rules:")
            for rule_num, title in sorted(actual_rules, key=lambda x: int(x[0]) if x[0].isdigit() else 999):
                print(f"  - Rule {rule_num}: {title}")
            
            # Show details of first actual rule
            if actual_rules:
                first_rule_num, first_rule_title = actual_rules[0]
                print(f"\n📄 Sample actual rule: Rule {first_rule_num}")
                
                # Find the rule data
                for rule in rules:
                    if rule.get('rule_number') == first_rule_num or first_rule_num in rule.get('title', ''):
                        if 'content' in rule and 'structured_content' in rule['content']:
                            structured = rule['content']['structured_content']
                            print("📝 Content preview (first 600 chars):")
                            print("-" * 50)
                            print(structured[:600] + "..." if len(structured) > 600 else structured)
                            print("-" * 50)
                            
                            # Show essential metadata only
                            if 'metadata' in rule:
                                metadata = rule['metadata']
                                print("📋 Essential metadata:")
                                essential_keys = ['authority', 'effective_date', 'last_updated']
                                for key in essential_keys:
                                    if key in metadata and metadata[key]:
                                        print(f"  - {key}: {metadata[key]}")
                        break
        
        return True
        
    except Exception as e:
        print(f"❌ Error finding actual rules: {e}")
        return False

if __name__ == "__main__":
    find_actual_rules() 