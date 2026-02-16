#!/usr/bin/env python3
"""
Identify the most important rule categories from the discovery output.
"""

def identify_important_categories():
    """Identify the most important rule categories."""
    
    # Based on the discovery output, these are the main rule categories
    important_categories = [
        # Core procedural rules
        "Appellate Procedure",
        "Civil Procedure", 
        "Criminal Procedure",
        "Evidence",
        "Rules of Court",
        
        # Administrative and professional rules
        "Administrative Rules",
        "Administrative Orders",
        "Admission to Practice Rules",
        "Continuing Legal Education",
        "Professional Conduct",
        "Lawyer Discipline",
        "Standards for Imposing Lawyer Sanctions",
        "Code of Judicial Conduct",
        "Judicial Conduct Commission",
        
        # Specialized rules
        "Juvenile Procedure",
        "Local Court Procedural and Administrative Rules",
        "Rules on Procedural Rules, Administrative Rules and Administrative Orders",
        "Rules on Local Court Procedural Rules and Administrative Rules",
        "Limited Practice of Law by Law Students"
    ]
    
    print("🎯 Most Important Rule Categories")
    print("=" * 50)
    print(f"Found {len(important_categories)} important rule categories:")
    
    for i, category in enumerate(important_categories, 1):
        print(f"  {i:2d}. {category}")
    
    print(f"\n📊 Summary:")
    print(f"  - Core Procedural Rules: 5 categories")
    print(f"  - Administrative Rules: 9 categories") 
    print(f"  - Specialized Rules: 6 categories")
    print(f"  - Total: {len(important_categories)} categories")
    
    return important_categories

def create_focused_config():
    """Create a focused config with only the important categories."""
    
    categories = identify_important_categories()
    
    config_content = f"""# Focused ND Court Rules Configuration
# Contains only the most important rule categories

scraping:
  base_url: https://www.ndcourts.gov/legal-resources/rules
  request_delay: 0.0  # No rate limiting
  timeout: 30
  user_agent: ND-Court-Rules-Scraper/1.0 (Educational Project)

rule_categories:
"""
    
    for category in categories:
        config_content += f"  - {category}\n"
    
    config_content += """
output:
  json_schema:
    include_plain_text: true
    include_structured_content: true
    max_section_depth: 4
    single_file_output: true
    claude_use_structured_only: true

logging:
  level: INFO
  verbose: false
"""
    
    with open('config_focused.yaml', 'w') as f:
        f.write(config_content)
    
    print(f"\n✅ Created config_focused.yaml with {len(categories)} categories")
    print("📝 This config includes only the most important rule categories")
    print("🚀 Use this config to scrape the essential rule sets")

if __name__ == "__main__":
    create_focused_config() 