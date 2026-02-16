#!/usr/bin/env python3
"""
Demo script showing the markdown generation feature.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def demo_markdown_features():
    """Demonstrate the markdown generation features."""
    print("📝 Markdown Generation Features Demo")
    print("=" * 60)
    
    print("\n1. GENERATE ALL MARKDOWN FILES")
    print("-" * 40)
    print("python src/main_enhanced.py --generate-markdown")
    print("• Creates markdown files for all rule sets")
    print("• Generates an index file (README.md)")
    print("• Organizes rules by category")
    
    print("\n2. STANDALONE MARKDOWN GENERATOR")
    print("-" * 40)
    print("python src/utils/markdown_generator.py")
    print("• Direct access to markdown generation")
    print("• Same functionality as main script")
    
    print("\n3. MARKDOWN FEATURES")
    print("-" * 40)
    print("✅ Table of Contents:")
    print("   • Clickable links to each rule")
    print("   • Rule numbers and citations")
    print("   • Easy navigation")
    
    print("\n✅ Rule Content:")
    print("   • Structured markdown formatting")
    print("   • Rule metadata (number, citation, source)")
    print("   • Authority and date information")
    print("   • Source URLs for reference")
    
    print("\n✅ File Organization:")
    print("   • One file per rule set category")
    print("   • Safe filenames (no special characters)")
    print("   • Index file with links to all categories")
    
    print("\n4. OUTPUT STRUCTURE")
    print("-" * 40)
    print("data/markdown/")
    print("├── README.md                    # Index file")
    print("├── Appellate_Procedure.md       # 58 rules")
    print("├── Administrative_Rules.md      # 85 rules")
    print("└── [other categories].md        # Additional rule sets")
    
    print("\n5. EXAMPLE MARKDOWN CONTENT")
    print("-" * 40)
    print("""
# Appellate Procedure

*Generated on 2025-07-31 11:29:36*

This document contains 58 rules from the Appellate Procedure category.

## Table of Contents

1. [RULE 1. SCOPE OF RULES](#rule-1-scope-of-rules)
   - Rule Number: 1
   - Citation: N.D.R.App.P. 1

2. [RULE 2. SUSPENSION OF RULES](#rule-2-suspension-of-rules)
   - Rule Number: 2
   - Citation: N.D.R.App.P. 2

---

## RULE 1. SCOPE OF RULES

**Rule Number:** 1
**Citation:** N.D.R.App.P. 1
**Source:** [https://www.ndcourts.gov/...](https://www.ndcourts.gov/...)

### Content

# RULE 1. SCOPE OF RULES

These rules govern procedure in appeals to the Supreme Court...

---
    """)
    
    print("\n6. USAGE TIPS")
    print("-" * 40)
    print("• Use markdown files for easy reading and review")
    print("• Click table of contents links for quick navigation")
    print("• Check source URLs for official versions")
    print("• Use markdown viewers for better formatting")
    print("• Regenerate after updating scraped data")
    
    print("\n7. INTEGRATION")
    print("-" * 40)
    print("• Works with existing scraped data")
    print("• No additional scraping required")
    print("• Can be run independently")
    print("• Integrates with validation system")

if __name__ == "__main__":
    demo_markdown_features() 