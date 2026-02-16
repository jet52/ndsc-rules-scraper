#!/usr/bin/env python3
"""
Markdown generator utility for ND Court Rules.
Creates readable markdown files for each rule set.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class MarkdownGenerator:
    """Generates markdown files for rule sets."""
    
    def __init__(self, output_dir: str = 'data/markdown'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_all_markdown(self, json_file: str = 'data/processed/nd_court_rules_complete.json'):
        """Generate markdown files for all rule sets."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            categories = data.get('data', {}).get('data', {}).get('categories', [])
            
            print(f"📝 Generating markdown files for {len(categories)} rule sets...")
            
            generated_files = []
            for category in categories:
                filename = self._generate_category_markdown(category)
                if filename:
                    generated_files.append(filename)
            
            print(f"✅ Generated {len(generated_files)} markdown files in {self.output_dir}")
            return generated_files
            
        except Exception as e:
            print(f"❌ Error generating markdown files: {e}")
            return []
    
    def _generate_category_markdown(self, category: Dict[str, Any]) -> str:
        """Generate markdown file for a single category."""
        category_name = category.get('category_name', 'Unknown')
        rules = category.get('rules', [])
        
        if not rules:
            print(f"⚠️  No rules found for category: {category_name}")
            return None
        
        # Create safe filename
        safe_name = self._sanitize_filename(category_name)
        filename = f"{safe_name}.md"
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write header
                f.write(self._generate_header(category_name, len(rules)))
                
                # Write table of contents
                f.write(self._generate_toc(rules))
                
                # Write each rule
                for rule in rules:
                    f.write(self._generate_rule_content(rule))
                
                # Write footer
                f.write(self._generate_footer())
            
            print(f"  ✅ Generated: {filename}")
            return filename
            
        except Exception as e:
            print(f"  ❌ Error generating {filename}: {e}")
            return None
    
    def _sanitize_filename(self, name: str) -> str:
        """Create a safe filename from category name."""
        # Replace problematic characters
        safe_name = name.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe_name = safe_name.replace('?', '_').replace('*', '_').replace('"', '_')
        safe_name = safe_name.replace('<', '_').replace('>', '_').replace('|', '_')
        
        # Remove extra spaces and replace with underscores
        safe_name = '_'.join(safe_name.split())
        
        # Limit length
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        return safe_name
    
    def _generate_header(self, category_name: str, rule_count: int) -> str:
        """Generate the header section of the markdown file."""
        header = f"""# {category_name}

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

This document contains {rule_count} rules from the {category_name} category.

## Table of Contents

"""
        return header
    
    def _generate_toc(self, rules: List[Dict[str, Any]]) -> str:
        """Generate table of contents."""
        toc = ""
        for i, rule in enumerate(rules, 1):
            title = rule.get('title', f'Rule {i}')
            rule_number = rule.get('rule_number', 'Unknown')
            citation = rule.get('citation', '')
            
            # Create anchor link
            anchor = self._create_anchor(title)
            
            toc += f"{i}. [{title}](#{anchor})\n"
            if rule_number and rule_number != 'Unknown':
                toc += f"   - Rule Number: {rule_number}\n"
            if citation:
                toc += f"   - Citation: {citation}\n"
            toc += "\n"
        
        return toc + "\n---\n\n"
    
    def _create_anchor(self, title: str) -> str:
        """Create an anchor link from title."""
        # Convert to lowercase and replace spaces with hyphens
        anchor = title.lower().replace(' ', '-')
        
        # Remove special characters
        import re
        anchor = re.sub(r'[^a-z0-9\-]', '', anchor)
        
        # Remove multiple hyphens
        anchor = re.sub(r'-+', '-', anchor)
        
        # Remove leading/trailing hyphens
        anchor = anchor.strip('-')
        
        return anchor
    
    def _generate_rule_content(self, rule: Dict[str, Any]) -> str:
        """Generate content for a single rule."""
        title = rule.get('title', 'Untitled Rule')
        rule_number = rule.get('rule_number', 'Unknown')
        citation = rule.get('citation', '')
        source_url = rule.get('source_url', '')
        content = rule.get('content', {})
        metadata = rule.get('metadata', {})
        
        # Rule header
        rule_content = f"## {title}\n\n"
        
        # Rule metadata
        if rule_number and rule_number != 'Unknown':
            rule_content += f"**Rule Number:** {rule_number}\n\n"
        
        if citation:
            rule_content += f"**Citation:** {citation}\n\n"
        
        if source_url:
            rule_content += f"**Source:** [{source_url}]({source_url})\n\n"
        
        # Add metadata if available
        if metadata:
            authority = metadata.get('authority')
            effective_date = metadata.get('effective_date')
            last_updated = metadata.get('last_updated')
            
            if authority:
                rule_content += f"**Authority:** {authority}\n\n"
            if effective_date:
                rule_content += f"**Effective Date:** {effective_date}\n\n"
            if last_updated:
                rule_content += f"**Last Updated:** {last_updated}\n\n"
        
        # Rule content
        if content:
            structured_content = content.get('structured_content', '')
            plain_text = content.get('plain_text', '')
            
            if structured_content:
                rule_content += f"### Content\n\n{structured_content}\n\n"
            elif plain_text:
                # If no structured content, format plain text
                rule_content += f"### Content\n\n{plain_text}\n\n"
            else:
                rule_content += "### Content\n\n*No content available*\n\n"
        
        rule_content += "---\n\n"
        return rule_content
    
    def _generate_footer(self) -> str:
        """Generate the footer section."""
        footer = f"""
---

*This document was automatically generated from the North Dakota Court Rules database.*

*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

*Source: https://www.ndcourts.gov/legal-resources/rules*
"""
        return footer
    
    def generate_index_file(self, json_file: str = 'data/processed/nd_court_rules_complete.json'):
        """Generate an index file listing all rule sets."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            categories = data.get('data', {}).get('data', {}).get('categories', [])
            
            index_path = self.output_dir / 'README.md'
            
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write("# North Dakota Court Rules - Markdown Index\n\n")
                f.write(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write("This directory contains markdown files for each rule set category.\n\n")
                
                f.write("## Available Rule Sets\n\n")
                
                total_rules = 0
                for category in categories:
                    category_name = category.get('category_name', 'Unknown')
                    rules = category.get('rules', [])
                    rule_count = len(rules)
                    total_rules += rule_count
                    
                    safe_name = self._sanitize_filename(category_name)
                    filename = f"{safe_name}.md"
                    
                    f.write(f"- [{category_name}]({filename}) ({rule_count} rules)\n")
                
                f.write(f"\n**Total Rules:** {total_rules}\n\n")
                f.write("## Usage\n\n")
                f.write("Each markdown file contains:\n")
                f.write("- Table of contents with rule numbers and citations\n")
                f.write("- Individual rule content with metadata\n")
                f.write("- Source URLs for reference\n")
                f.write("- Authority and date information where available\n\n")
                
                f.write("## Source\n\n")
                f.write("All rules are sourced from the [North Dakota Courts website](https://www.ndcourts.gov/legal-resources/rules).\n")
            
            print(f"✅ Generated index file: {index_path}")
            return str(index_path)
            
        except Exception as e:
            print(f"❌ Error generating index file: {e}")
            return None


def main():
    """Main function to generate markdown files."""
    print("📝 ND Court Rules Markdown Generator")
    print("=" * 50)
    
    generator = MarkdownGenerator()
    
    # Generate all markdown files
    generated_files = generator.generate_all_markdown()
    
    # Generate index file
    generator.generate_index_file()
    
    if generated_files:
        print(f"\n🎉 Successfully generated {len(generated_files)} markdown files!")
        print(f"📁 Files saved to: {generator.output_dir}")
        print("\nYou can now browse the rules in markdown format for easier reading.")
    else:
        print("\n❌ No markdown files were generated.")


if __name__ == "__main__":
    main() 