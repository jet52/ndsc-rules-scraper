#!/usr/bin/env python3
"""
Script to discover what rule categories are available on the ND Courts website.
"""

import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def discover_categories():
    """Discover what rule categories are available on the ND Courts website."""
    print("🔍 Discovering Rule Categories on ND Courts Website")
    print("=" * 60)
    
    base_url = "https://www.ndcourts.gov/legal-resources/rules"
    
    try:
        # Create session with proper headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'ND-Court-Rules-Scraper/1.0 (Educational Project)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Handle SSL certificate issues
        try:
            import ssl
            import certifi
            session.verify = certifi.where()
        except ImportError:
            session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        print(f"📡 Fetching main rules page: {base_url}")
        response = session.get(base_url, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch page: HTTP {response.status_code}")
            return []
        
        print("✅ Successfully fetched main rules page")
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save raw HTML for inspection
        with open('data/raw/main_rules_page_discovery.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("💾 Saved raw HTML to data/raw/main_rules_page_discovery.html")
        
        # Look for category links
        categories = []
        
        # Method 1: Look for links that might be rule categories
        links = soup.find_all('a', href=True)
        
        print(f"\n🔗 Found {len(links)} total links on the page")
        
        # Common rule category keywords
        rule_keywords = [
            'appellate', 'civil', 'criminal', 'evidence', 'court', 'administrative',
            'procedure', 'rules', 'discipline', 'conduct', 'juvenile', 'municipal',
            'probate', 'domestic', 'guardianship', 'mental', 'alternative', 'dispute',
            'interpreter', 'reporter', 'electronic', 'filing', 'public', 'access',
            'records', 'jury', 'security', 'technology', 'finance', 'personnel',
            'facility', 'statistic', 'planning', 'education', 'outreach', 'publication',
            'form', 'fee', 'cost', 'bond', 'insurance', 'liability', 'ethics',
            'professionalism', 'diversity', 'accessibility', 'language', 'culture',
            'innovation', 'excellence', 'leadership', 'governance', 'policy', 'standard',
            'quality', 'performance', 'accountability', 'transparency', 'integrity',
            'independence', 'impartiality', 'fairness', 'justice', 'service', 'community',
            'partnership', 'collaboration', 'coordination', 'integration', 'efficiency',
            'effectiveness', 'productivity', 'sustainability', 'improvement', 'development',
            'advancement', 'progress', 'growth', 'evolution', 'transformation', 'modernization'
        ]
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # Check if this looks like a rule category link
            href_lower = href.lower()
            text_lower = text.lower()
            
            # Look for rule-related keywords
            for keyword in rule_keywords:
                if keyword in href_lower or keyword in text_lower:
                    # Check if it's not just a general page link
                    if not any(skip in href_lower for skip in ['home', 'about', 'contact', 'search', 'login']):
                        full_url = urljoin(base_url, href)
                        categories.append({
                            'text': text,
                            'href': href,
                            'full_url': full_url,
                            'keyword_match': keyword
                        })
                        break
        
        # Remove duplicates based on href
        unique_categories = []
        seen_hrefs = set()
        for cat in categories:
            if cat['href'] not in seen_hrefs:
                unique_categories.append(cat)
                seen_hrefs.add(cat['href'])
        
        print(f"\n📋 Found {len(unique_categories)} potential rule categories:")
        print("-" * 60)
        
        for i, cat in enumerate(unique_categories, 1):
            print(f"{i:2d}. {cat['text']}")
            print(f"    URL: {cat['href']}")
            print(f"    Full: {cat['full_url']}")
            print(f"    Match: {cat['keyword_match']}")
            print()
        
        # Method 2: Look for specific patterns in the page structure
        print("🔍 Looking for structured category sections...")
        
        # Look for headings that might indicate categories
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        print(f"Found {len(headings)} headings:")
        
        for heading in headings[:20]:  # Show first 20
            text = heading.get_text().strip()
            if text and len(text) > 3:
                print(f"  - {heading.name}: {text}")
        
        # Method 3: Look for lists or navigation menus
        print("\n🔍 Looking for navigation menus and lists...")
        
        nav_elements = soup.find_all(['nav', 'ul', 'ol'], class_=lambda x: x and any(word in x.lower() for word in ['nav', 'menu', 'list', 'category']))
        
        for nav in nav_elements[:5]:  # Show first 5
            print(f"  - {nav.name} with classes: {nav.get('class', [])}")
            links_in_nav = nav.find_all('a', href=True)
            for link in links_in_nav[:3]:  # Show first 3 links
                print(f"    * {link.get_text().strip()} -> {link.get('href')}")
        
        return unique_categories
        
    except Exception as e:
        print(f"❌ Error discovering categories: {e}")
        return []

def create_config_from_categories(categories):
    """Create a config file based on discovered categories."""
    if not categories:
        print("❌ No categories found to create config")
        return
    
    print(f"\n📝 Creating config file with {len(categories)} categories...")
    
    # Extract category names (clean up the text)
    category_names = []
    for cat in categories:
        name = cat['text'].strip()
        # Clean up the name
        name = name.replace('\n', ' ').replace('\r', ' ')
        name = ' '.join(name.split())  # Normalize whitespace
        if name and len(name) > 2:
            category_names.append(name)
    
    # Create config content
    config_content = f"""anthropic:
  api_key: ''
  max_tokens: 4000
  model: claude-3-sonnet-20240229
  temperature: 0.1
logging:
  level: DEBUG
  log_file: scraper.log
  verbose: true
output:
  data_dir: data
  json_schema:
    claude_use_structured_only: true
    include_plain_text: true
    include_structured_content: true
    max_section_depth: 4
    single_file_output: true
  metadata_dir: data/metadata
  preserve_raw_html: true
  processed_dir: data/processed
  raw_dir: data/raw
rule_categories:
"""
    
    for name in category_names:
        config_content += f"- {name}\n"
    
    config_content += """scraping:
  base_url: https://www.ndcourts.gov/legal-resources/rules
  max_retries: 3
  request_delay: 0.0
  timeout: 30
  user_agent: ND-Court-Rules-Scraper/1.0 (Educational Project)
"""
    
    # Write config file
    with open('config_all_discovered.yaml', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print("✅ Created config_all_discovered.yaml")
    print(f"📋 Includes {len(category_names)} categories")
    
    return category_names

if __name__ == "__main__":
    categories = discover_categories()
    if categories:
        category_names = create_config_from_categories(categories)
        print(f"\n🎉 Discovery complete! Found {len(categories)} potential rule categories.")
        print("\nNext steps:")
        print("1. Review the discovered categories")
        print("2. Use config_all_discovered.yaml to scrape all categories")
        print("3. Or manually edit the config to include only relevant categories")
    else:
        print("\n❌ No categories discovered. Check the website structure.") 