#!/usr/bin/env python3
"""
Simple validation script to check the output quality of the scraped data.
"""

import json
import os
from pathlib import Path

def validate_output_structure():
    """Validate the structure of the output JSON file."""
    print("🔍 Validating Output Structure")
    print("=" * 50)
    
    # Check if the main output file exists
    output_file = Path("data/processed/nd_court_rules_complete.json")
    if not output_file.exists():
        print("❌ Main output file not found: nd_court_rules_complete.json")
        return False
    
    print(f"✅ Found output file: {output_file}")
    
    # Load and validate the JSON structure
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("✅ JSON file loaded successfully")
        
        # Check top-level structure
        required_keys = ['metadata', 'data']
        for key in required_keys:
            if key not in data:
                print(f"❌ Missing required key: {key}")
                return False
            print(f"✅ Found key: {key}")
        
        # Check metadata structure
        metadata = data['metadata']
        metadata_keys = ['generated_at', 'source', 'version']
        for key in metadata_keys:
            if key not in metadata:
                print(f"❌ Missing metadata key: {key}")
                return False
            print(f"✅ Found metadata key: {key}")
        
        # Check data structure
        data_section = data['data']
        if not isinstance(data_section, dict):
            print("❌ Data section is not a dictionary")
            return False
        
        # Check nested data structure
        if 'data' not in data_section:
            print("❌ Data section missing nested 'data' key")
            return False
        
        categories_data = data_section['data'].get('categories')
        if not isinstance(categories_data, list):
            print("❌ Categories is not a list")
            return False
        
        print(f"✅ Found {len(categories_data)} categories")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return False

def validate_rule_content():
    """Validate the content of individual rules."""
    print("\n🔍 Validating Rule Content")
    print("=" * 50)
    
    try:
        with open("data/processed/nd_court_rules_complete.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_rules = 0
        valid_rules = 0
        
        categories_data = data['data']['data']['categories']
        
        for category in categories_data:
            category_name = category.get('category_name', 'Unknown')
            print(f"\n📋 Checking category: {category_name}")
            
            if 'rules' not in category:
                print(f"❌ Category '{category_name}' missing 'rules' key")
                continue
            
            rules = category['rules']
            category_rules = 0
            
            for rule_data in rules:
                total_rules += 1
                
                # Check required rule fields
                required_fields = ['title', 'citation', 'source_url', 'content', 'metadata']
                missing_fields = []
                
                for field in required_fields:
                    if field not in rule_data:
                        missing_fields.append(field)
                
                if missing_fields:
                    print(f"❌ Rule missing fields: {missing_fields}")
                    continue
                
                # Check content structure
                content = rule_data['content']
                if 'plain_text' not in content or 'structured_content' not in content:
                    print(f"❌ Rule missing content fields")
                    continue
                
                # Check if content is not empty
                if not content['plain_text'].strip() or not content['structured_content'].strip():
                    print(f"❌ Rule has empty content")
                    continue
                
                # Check metadata structure
                metadata = rule_data['metadata']
                if 'scraped_at' not in metadata:
                    print(f"❌ Rule missing metadata fields")
                    continue
                
                valid_rules += 1
                category_rules += 1
            
            print(f"✅ Category '{category_name}': {category_rules} valid rules")
        
        print(f"\n📊 Overall Results:")
        print(f"   Total rules: {total_rules}")
        print(f"   Valid rules: {valid_rules}")
        print(f"   Success rate: {(valid_rules/total_rules*100):.1f}%" if total_rules > 0 else "   Success rate: 0%")
        
        return valid_rules > 0
        
    except Exception as e:
        print(f"❌ Error validating content: {e}")
        return False

def validate_file_sizes():
    """Validate file sizes and check for reasonable data."""
    print("\n🔍 Validating File Sizes")
    print("=" * 50)
    
    # Check main output file size
    output_file = Path("data/processed/nd_court_rules_complete.json")
    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"✅ Main output file: {size_mb:.2f} MB")
        
        if size_mb < 1:
            print("⚠️  Warning: Output file seems small (< 1 MB)")
        elif size_mb > 100:
            print("⚠️  Warning: Output file seems large (> 100 MB)")
        else:
            print("✅ File size is reasonable")
    
    # Check raw HTML files
    raw_dir = Path("data/raw")
    if raw_dir.exists():
        html_files = list(raw_dir.glob("*.html"))
        print(f"✅ Found {len(html_files)} raw HTML files")
        
        total_html_size = sum(f.stat().st_size for f in html_files)
        total_html_mb = total_html_size / (1024 * 1024)
        print(f"✅ Total HTML size: {total_html_mb:.2f} MB")
    
    # Check metadata files
    metadata_dir = Path("data/metadata")
    if metadata_dir.exists():
        metadata_files = list(metadata_dir.glob("*.json"))
        print(f"✅ Found {len(metadata_files)} metadata files")
    
    return True

def main():
    """Main validation function."""
    print("🧪 ND Court Rules Scraper - Output Validation")
    print("=" * 60)
    
    # Check if data directory exists
    if not Path("data").exists():
        print("❌ Data directory not found")
        return False
    
    # Run validations
    structure_ok = validate_output_structure()
    content_ok = validate_rule_content()
    files_ok = validate_file_sizes()
    
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    if structure_ok and content_ok and files_ok:
        print("🎉 All validations passed!")
        print("\n✅ Output quality is good and ready for Claude proofreading")
        return True
    else:
        print("❌ Some validations failed")
        if not structure_ok:
            print("   - Output structure issues")
        if not content_ok:
            print("   - Rule content issues")
        if not files_ok:
            print("   - File size issues")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 