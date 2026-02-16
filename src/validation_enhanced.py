#!/usr/bin/env python3
"""
Enhanced validation script for ND Court Rules with detailed failure reporting.
Provides comprehensive analysis of rule quality and specific issues.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

class RuleValidator:
    """Enhanced rule validator with detailed failure reporting."""
    
    def __init__(self, output_file: str = 'data/processed/nd_court_rules_complete.json'):
        self.output_file = output_file
        self.data = None
        self.validation_results = {
            'overall': {'passed': False, 'issues': []},
            'structure': {'passed': False, 'issues': []},
            'content': {'passed': False, 'issues': []},
            'metadata': {'passed': False, 'issues': []},
            'failed_rules': [],
            'warnings': [],
            'statistics': {}
        }
    
    def load_data(self) -> bool:
        """Load and validate the JSON data file."""
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            return True
        except FileNotFoundError:
            self.validation_results['overall']['issues'].append(f"File not found: {self.output_file}")
            return False
        except json.JSONDecodeError as e:
            self.validation_results['overall']['issues'].append(f"Invalid JSON: {e}")
            return False
        except Exception as e:
            self.validation_results['overall']['issues'].append(f"Unexpected error: {e}")
            return False
    
    def validate_structure(self) -> bool:
        """Validate the overall data structure."""
        issues = []
        
        if not self.data:
            issues.append("No data loaded")
            self.validation_results['structure']['issues'] = issues
            return False
        
        # Check top-level structure
        if 'metadata' not in self.data:
            issues.append("Missing top-level 'metadata' key")
        if 'data' not in self.data:
            issues.append("Missing top-level 'data' key")
        
        if issues:
            self.validation_results['structure']['issues'] = issues
            return False
        
        # Check nested structure
        data_section = self.data['data']
        if 'data' not in data_section:
            issues.append("Missing nested 'data' key in data section")
        else:
            nested_data = data_section['data']
            if 'categories' not in nested_data:
                issues.append("Missing 'categories' key in nested data")
            elif not isinstance(nested_data['categories'], list):
                issues.append("'categories' is not a list")
        
        if issues:
            self.validation_results['structure']['issues'] = issues
            return False
        
        self.validation_results['structure']['passed'] = True
        return True
    
    def validate_metadata(self) -> bool:
        """Validate metadata structure and content."""
        issues = []
        
        metadata = self.data.get('metadata', {})
        required_keys = ['generated_at', 'source', 'version']
        
        for key in required_keys:
            if key not in metadata:
                issues.append(f"Missing metadata key: '{key}'")
        
        # Check for reasonable values
        if 'generated_at' in metadata:
            try:
                # Try to parse timestamp
                timestamp = metadata['generated_at']
                if isinstance(timestamp, str):
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                issues.append("Invalid timestamp format in 'generated_at'")
        
        if issues:
            self.validation_results['metadata']['issues'] = issues
            return False
        
        self.validation_results['metadata']['passed'] = True
        return True
    
    def validate_content(self) -> bool:
        """Validate rule content quality and structure."""
        issues = []
        failed_rules = []
        warnings = []
        
        categories = self.data.get('data', {}).get('data', {}).get('categories', [])
        total_rules = 0
        valid_rules = 0
        
        for category in categories:
            category_name = category.get('category_name', 'Unknown')
            rules = category.get('rules', [])
            
            for rule in rules:
                total_rules += 1
                rule_issues = []
                rule_warnings = []
                
                # Check required fields
                required_fields = ['title', 'rule_number', 'citation', 'source_url', 'content', 'metadata']
                missing_fields = [field for field in required_fields if field not in rule]
                
                if missing_fields:
                    rule_issues.append(f"Missing fields: {missing_fields}")
                
                # Check content structure
                if 'content' in rule:
                    content = rule['content']
                    if 'plain_text' not in content:
                        rule_issues.append("Missing 'plain_text' in content")
                    elif not content['plain_text'].strip():
                        rule_issues.append("Empty 'plain_text' content")
                    
                    if 'structured_content' not in content:
                        rule_issues.append("Missing 'structured_content' in content")
                    elif not content['structured_content'].strip():
                        rule_issues.append("Empty 'structured_content'")
                    else:
                        # Check if structured content starts with heading
                        structured = content['structured_content'].strip()
                        if not structured.startswith('#'):
                            rule_warnings.append("Structured content doesn't start with heading")
                
                # Check metadata
                if 'metadata' in rule:
                    metadata = rule['metadata']
                    if 'scraped_at' not in metadata:
                        rule_issues.append("Missing 'scraped_at' in metadata")
                
                # Check rule number format
                rule_number = rule.get('rule_number')
                if rule_number:
                    if not isinstance(rule_number, (str, int)):
                        rule_warnings.append(f"Unexpected rule number type: {type(rule_number)}")
                
                # Check citation format
                citation = rule.get('citation')
                if citation and not isinstance(citation, str):
                    rule_warnings.append(f"Unexpected citation type: {type(citation)}")
                
                # Check source URL
                source_url = rule.get('source_url')
                if source_url and not source_url.startswith('http'):
                    rule_warnings.append(f"Invalid source URL format: {source_url}")
                
                # Record issues and warnings
                if rule_issues:
                    failed_rules.append({
                        'category': category_name,
                        'title': rule.get('title', 'Unknown'),
                        'rule_number': rule.get('rule_number', 'Unknown'),
                        'issues': rule_issues,
                        'warnings': rule_warnings
                    })
                else:
                    valid_rules += 1
                    if rule_warnings:
                        warnings.append({
                            'category': category_name,
                            'title': rule.get('title', 'Unknown'),
                            'rule_number': rule.get('rule_number', 'Unknown'),
                            'warnings': rule_warnings
                        })
        
        # Store statistics
        self.validation_results['statistics'] = {
            'total_rules': total_rules,
            'valid_rules': valid_rules,
            'failed_rules': len(failed_rules),
            'total_warnings': len(warnings),
            'success_rate': (valid_rules / total_rules * 100) if total_rules > 0 else 0
        }
        
        # Store detailed results
        self.validation_results['failed_rules'] = failed_rules
        self.validation_results['warnings'] = warnings
        
        if failed_rules:
            issues.append(f"{len(failed_rules)} rules failed validation")
        
        if issues:
            self.validation_results['content']['issues'] = issues
            return False
        
        self.validation_results['content']['passed'] = True
        return True
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation and return results."""
        print("🔍 Enhanced Rule Validation")
        print("=" * 60)
        
        # Load data
        if not self.load_data():
            self.validation_results['overall']['passed'] = False
            return self.validation_results
        
        # Run validation steps
        structure_ok = self.validate_structure()
        metadata_ok = self.validate_metadata()
        content_ok = self.validate_content()
        
        # Overall result
        self.validation_results['overall']['passed'] = structure_ok and metadata_ok and content_ok
        
        return self.validation_results
    
    def print_detailed_report(self):
        """Print a detailed validation report."""
        results = self.validation_results
        
        print("\n📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        # Overall status
        if results['overall']['passed']:
            print("✅ OVERALL: PASSED")
        else:
            print("❌ OVERALL: FAILED")
        
        # Structure validation
        if results['structure']['passed']:
            print("✅ Structure: Valid")
        else:
            print("❌ Structure: Invalid")
            for issue in results['structure']['issues']:
                print(f"   • {issue}")
        
        # Metadata validation
        if results['metadata']['passed']:
            print("✅ Metadata: Valid")
        else:
            print("❌ Metadata: Invalid")
            for issue in results['metadata']['issues']:
                print(f"   • {issue}")
        
        # Content validation
        if results['content']['passed']:
            print("✅ Content: Valid")
        else:
            print("❌ Content: Invalid")
            for issue in results['content']['issues']:
                print(f"   • {issue}")
        
        # Statistics
        stats = results['statistics']
        if stats:
            print(f"\n📈 STATISTICS")
            print(f"   Total rules: {stats['total_rules']}")
            print(f"   Valid rules: {stats['valid_rules']}")
            print(f"   Failed rules: {stats['failed_rules']}")
            print(f"   Success rate: {stats['success_rate']:.1f}%")
            print(f"   Warnings: {stats['total_warnings']}")
        
        # Failed rules details
        if results['failed_rules']:
            print(f"\n❌ FAILED RULES ({len(results['failed_rules'])} total)")
            print("=" * 60)
            
            # Group by category
            by_category = {}
            for rule in results['failed_rules']:
                cat = rule['category']
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(rule)
            
            for category, rules in by_category.items():
                print(f"\n📋 {category} ({len(rules)} failed rules):")
                for rule in rules:
                    print(f"   • {rule['title']} (Rule {rule['rule_number']})")
                    for issue in rule['issues']:
                        print(f"     - {issue}")
                    for warning in rule['warnings']:
                        print(f"     ⚠️  {warning}")
        
        # Warnings summary
        if results['warnings']:
            print(f"\n⚠️  WARNINGS ({len(results['warnings'])} total)")
            print("=" * 60)
            
            # Group by warning type
            warning_types = {}
            for rule in results['warnings']:
                for warning in rule['warnings']:
                    if warning not in warning_types:
                        warning_types[warning] = []
                    warning_types[warning].append(rule)
            
            for warning_type, rules in warning_types.items():
                print(f"\n{warning_type} ({len(rules)} rules):")
                for rule in rules[:5]:  # Show first 5
                    print(f"   • {rule['title']} (Rule {rule['rule_number']})")
                if len(rules) > 5:
                    print(f"   ... and {len(rules) - 5} more")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        print("=" * 60)
        
        if results['failed_rules']:
            print("• Review and fix failed rules before proceeding")
            print("• Check rule parsing logic for common issues")
            print("• Verify source URLs are accessible")
        
        if results['warnings']:
            print("• Address warnings to improve data quality")
            print("• Consider enhancing rule number extraction")
            print("• Review citation generation logic")
        
        if results['statistics']['success_rate'] < 95:
            print("• Success rate below 95% - investigate parsing issues")
        
        if results['statistics']['success_rate'] >= 95:
            print("• High success rate - data quality is good")
        
        print("\n" + "=" * 60)
    
    def save_report(self, output_file: str = None):
        """Save validation report to JSON file."""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/validation_report_{timestamp}.json"
        
        try:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
            print(f"📄 Validation report saved to: {output_file}")
        except Exception as e:
            print(f"❌ Error saving report: {e}")


def main():
    """Main validation function."""
    validator = RuleValidator()
    results = validator.run_validation()
    
    validator.print_detailed_report()
    
    # Ask user if they want to save the report
    save_report = input("\nSave detailed validation report? (y/N): ").strip().lower()
    if save_report in ['y', 'yes']:
        validator.save_report()
    
    # Return appropriate exit code
    return 0 if results['overall']['passed'] else 1


if __name__ == "__main__":
    exit(main()) 