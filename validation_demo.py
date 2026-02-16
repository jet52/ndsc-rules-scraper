#!/usr/bin/env python3
"""
Demo script showing how to use the enhanced validation features.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def demo_validation_features():
    """Demonstrate the enhanced validation features."""
    print("🔍 Enhanced Validation Features Demo")
    print("=" * 60)
    
    print("\n1. BASIC VALIDATION")
    print("-" * 30)
    print("python src/main_enhanced.py --validate-only")
    print("• Quick validation with summary")
    print("• Shows overall pass/fail status")
    print("• Lists failed rules count")
    
    print("\n2. DETAILED VALIDATION")
    print("-" * 30)
    print("python src/validation_enhanced.py")
    print("• Comprehensive validation report")
    print("• Detailed analysis of each rule")
    print("• Groups failures by category")
    print("• Shows specific issues per rule")
    print("• Provides actionable recommendations")
    
    print("\n3. VALIDATION WITH SAVED REPORT")
    print("-" * 30)
    print("python src/validation_enhanced.py")
    print("• Run validation and save detailed report")
    print("• Report saved as JSON for further analysis")
    print("• Includes all validation results and statistics")
    
    print("\n4. VALIDATION INTEGRATED WITH SCRAPING")
    print("-" * 30)
    print("python src/main_enhanced.py --rule-sets 'Evidence' --validate-only")
    print("• Validate specific rule sets")
    print("• Check data before and after scraping")
    
    print("\n5. VALIDATION FEATURES")
    print("-" * 30)
    print("✅ Structure Validation:")
    print("   • Checks JSON structure integrity")
    print("   • Validates required keys and data types")
    print("   • Ensures proper nesting")
    
    print("\n✅ Metadata Validation:")
    print("   • Verifies metadata completeness")
    print("   • Checks timestamp formats")
    print("   • Validates required fields")
    
    print("\n✅ Content Validation:")
    print("   • Examines each rule individually")
    print("   • Checks for missing or empty content")
    print("   • Validates rule numbers and citations")
    print("   • Verifies source URLs")
    
    print("\n✅ Detailed Reporting:")
    print("   • Groups failures by category")
    print("   • Shows specific issues per rule")
    print("   • Provides warnings for potential problems")
    print("   • Calculates success rates and statistics")
    
    print("\n✅ Recommendations:")
    print("   • Actionable suggestions for fixing issues")
    print("   • Quality improvement recommendations")
    print("   • Performance and reliability tips")
    
    print("\n6. EXAMPLE OUTPUT")
    print("-" * 30)
    print("""
📊 VALIDATION SUMMARY
============================================================
❌ OVERALL: FAILED
✅ Structure: Valid
✅ Metadata: Valid
❌ Content: Invalid
   • 2 rules failed validation

📈 STATISTICS
   Total rules: 143
   Valid rules: 141
   Failed rules: 2
   Success rate: 98.6%
   Warnings: 0

❌ FAILED RULES (2 total)
============================================================

📋 Appellate Procedure (2 failed rules):
   • Untitled Rule (Rule None)
     - Empty 'structured_content'
   • Untitled Rule (Rule None)
     - Empty 'structured_content'

💡 RECOMMENDATIONS
============================================================
• Review and fix failed rules before proceeding
• Check rule parsing logic for common issues
• Verify source URLs are accessible
• High success rate - data quality is good
    """)
    
    print("\n7. USAGE TIPS")
    print("-" * 30)
    print("• Run validation after each scraping session")
    print("• Use detailed validation for quality assurance")
    print("• Save reports for tracking improvements over time")
    print("• Address warnings to improve data quality")
    print("• Use validation before proceeding to Claude proofreading")

if __name__ == "__main__":
    demo_validation_features() 