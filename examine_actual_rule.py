#!/usr/bin/env python3
"""
Script to examine an actual rule (not a committee page) to see the real rule content.
"""

import json

def examine_actual_rule():
    """Examine an actual rule to see the real content."""
    try:
        with open('data/processed/nd_court_rules_complete.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("📋 Actual Rule Analysis")
        print("=" * 50)
        
        # Look for an actual rule (not a committee page)
        categories = data['data']['data']['categories']
        
        for category in categories:
            category_name = category.get('category_name', 'Unknown')
            print(f"\n📋 Category: {category_name}")
            
            rules = category.get('rules', [])
            for i, rule in enumerate(rules[:3]):  # Look at first 3 rules
                title = rule.get('title', 'Unknown')
                rule_number = rule.get('rule_number', 'Unknown')
                
                print(f"\n📄 Rule {i+1}: {title} (Rule {rule_number})")
                print("-" * 50)
                
                # Check if this looks like an actual rule vs committee info
                if 'committee' in title.lower() or 'joint' in title.lower():
                    print("⚠️  This appears to be committee information, not a rule")
                    continue
                
                # Show the actual rule content
                if 'content' in rule and 'structured_content' in rule['content']:
                    structured = rule['content']['structured_content']
                    print("📝 Rule content preview (first 800 chars):")
                    print("-" * 50)
                    print(structured[:800] + "..." if len(structured) > 800 else structured)
                    print("-" * 50)
                    
                    # Show metadata for this rule
                    if 'metadata' in rule:
                        metadata = rule['metadata']
                        print("📋 Rule-specific metadata:")
                        for key, value in metadata.items():
                            if key not in ['scraped_at', 'file_size_bytes', 'html_checksum']:
                                print(f"  - {key}: {value}")
                    
                    break  # Found an actual rule, stop looking
        
        return True
        
    except Exception as e:
        print(f"❌ Error examining actual rule: {e}")
        return False

if __name__ == "__main__":
    examine_actual_rule() 