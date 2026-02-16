#!/usr/bin/env python3
"""
Simple validation script for the comprehensive rule scraping output.
Avoids Unicode characters to prevent encoding issues.
"""

import json
import os
from pathlib import Path

def validate_output_structure():
    """Validate the output JSON structure."""
    print("Validating Output Structure")
    print("=" * 50)
    
    try:
        with open('data/processed/nd_court_rules_complete.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check top-level structure
        if 'metadata' not in data or 'data' not in data:
            print("ERROR: Missing top-level 'metadata' or 'data' keys")
            return False
        
        print("PASS: Top-level structure is valid")
        
        # Check metadata structure
        metadata = data['metadata']
        metadata_keys = ['generated_at', 'source', 'version']
        for key in metadata_keys:
            if key not in metadata:
                print(f"ERROR: Missing metadata key '{key}'")
                return False
        
        print("PASS: Metadata structure is valid")
        
        # Check data structure
        data_section = data['data']
        if 'data' not in data_section:
            print("ERROR: Data section missing nested 'data' key")
            return False
        
        # Check categories in nested data structure
        nested_data = data_section['data']
        if 'categories' not in nested_data:
            print("ERROR: Nested data section missing 'categories' key")
            return False
        
        categories_data = nested_data.get('categories')
        if not isinstance(categories_data, list):
            print("ERROR: Categories is not a list")
            return False
        
        print(f"PASS: Found {len(categories_data)} categories")
        
        return True
        
    except FileNotFoundError:
        print("ERROR: Output file not found")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

def validate_rule_content():
    """Validate the content of individual rules."""
    print("\nValidating Rule Content")
    print("=" * 50)
    
    try:
        with open('data/processed/nd_court_rules_complete.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        categories_data = data['data']['data']['categories']
        total_rules = 0
        valid_rules = 0
        
        for category in categories_data:
            category_name = category.get('category_name', 'Unknown')
            print(f"\nChecking category: {category_name}")
            
            if 'rules' not in category:
                print(f"ERROR: Category '{category_name}' missing 'rules' key")
                continue
            
            rules = category['rules']
            category_rules = 0
            
            for rule_data in rules:
                total_rules += 1
                
                # Check required fields
                required_fields = ['title', 'rule_number', 'citation', 'source_url', 'content', 'metadata']
                missing_fields = [field for field in required_fields if field not in rule_data]
                
                if missing_fields:
                    print(f"ERROR: Rule missing fields: {missing_fields}")
                    continue
                
                # Check content structure
                content = rule_data['content']
                if 'plain_text' not in content or 'structured_content' not in content:
                    print(f"ERROR: Rule missing content fields")
                    continue
                
                # Check if content is not empty
                if not content['plain_text'].strip() or not content['structured_content'].strip():
                    print(f"ERROR: Rule has empty content")
                    continue
                
                # Check metadata structure
                metadata = rule_data['metadata']
                if 'scraped_at' not in metadata:
                    print(f"ERROR: Rule missing metadata fields")
                    continue
                
                # Check if structured content starts with a heading
                structured = content['structured_content']
                if not structured.strip().startswith('#'):
                    print(f"WARNING: Rule structured content doesn't start with heading")
                
                valid_rules += 1
                category_rules += 1
            
            print(f"  Category '{category_name}': {category_rules} valid rules")
        
        print(f"\nTotal rules processed: {total_rules}")
        print(f"Valid rules: {valid_rules}")
        print(f"Success rate: {(valid_rules/total_rules*100):.1f}%" if total_rules > 0 else "No rules found")
        
        return valid_rules > 0
        
    except Exception as e:
        print(f"ERROR: Error validating rule content: {e}")
        return False

def check_file_size():
    """Check the size of the output file."""
    print("\nChecking File Size")
    print("=" * 50)
    
    try:
        file_path = Path('data/processed/nd_court_rules_complete.json')
        if not file_path.exists():
            print("ERROR: Output file not found")
            return False
        
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"Output file size: {size_mb:.2f} MB")
        
        if size_mb < 0.1:
            print("WARNING: File seems very small, may be incomplete")
            return False
        elif size_mb > 100:
            print("WARNING: File is very large, may contain excessive data")
            return False
        else:
            print("PASS: File size is reasonable")
            return True
            
    except Exception as e:
        print(f"ERROR: Error checking file size: {e}")
        return False

def main():
    """Run all validation checks."""
    print("Comprehensive Rule Scraping Validation")
    print("=" * 60)
    
    checks = [
        ("Output Structure", validate_output_structure),
        ("Rule Content", validate_rule_content),
        ("File Size", check_file_size)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\nRunning {check_name} check...")
        if check_func():
            print(f"PASS: {check_name}")
            passed += 1
        else:
            print(f"FAIL: {check_name}")
    
    print(f"\nValidation Summary")
    print("=" * 30)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\nSUCCESS: All validation checks passed!")
        print("The comprehensive rule scraping appears to be successful.")
    else:
        print(f"\nWARNING: {total - passed} check(s) failed.")
        print("Please review the errors above.")

if __name__ == "__main__":
    main() 