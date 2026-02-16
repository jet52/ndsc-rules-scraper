# JSON Schema Documentation

## Design Decisions

### Content Format Strategy
- **Plain Text**: Preserved exactly as scraped from the web for maximum fidelity
- **Structured Content**: Markdown-formatted content with preserved headings, lists, and basic formatting
- **Rationale**: Provides both raw data integrity and readable formatted content for analysis

### Section Depth Limitation
- **Maximum Depth**: 4 levels (h1 → h2 → h3 → h4)
- **Rationale**: Balances structure preservation with manageable complexity
- **Implementation**: Any deeper headings (h5, h6) will be flattened to h4 level

### Metadata Preservation
- **Strategy**: Extract and preserve ALL metadata found on the website
- **Included Fields**:
  - Last updated date
  - Effective date
  - Authority (promulgating body)
  - Related rules
  - Cross-references
  - Any other metadata discovered during scraping

### File Organization
- **Single File Output**: All rules in one comprehensive JSON file
- **Rationale**: Enables cross-rule analysis and consistency checking
- **Structure**: Hierarchical by category, then by individual rules

### Claude Integration Strategy
- **Content Sent**: Structured content only (not plain text)
- **Rationale**: Cost optimization while maintaining analysis quality
- **Format**: Markdown-structured content with preserved formatting

## JSON Schema Structure

```json
{
  "metadata": {
    "generated_at": "2024-01-15T10:30:00Z",
    "source": "ND Courts Rules Scraper",
    "version": "1.0",
    "schema_version": "1.0",
    "total_rules": 150,
    "total_categories": 19,
    "scraping_duration_seconds": 45.2
  },
  "data": {
    "categories": [
      {
        "category_name": "Appellate Procedure",
        "category_url": "https://www.ndcourts.gov/legal-resources/rules/appellate-procedure",
        "rule_count": 25,
        "rules": [
          {
            "title": "Rule 1. Scope of Rules",
            "rule_number": "1",
            "citation": "N.D.R.App.P. 1",
            "source_url": "https://www.ndcourts.gov/legal-resources/rules/appellate-procedure/rule-1",
            "content": {
              "plain_text": "Full plain text as scraped from web...",
              "structured_content": "# Rule 1. Scope of Rules\n\n## (a) Scope\n\nThese rules govern procedure in the Supreme Court...",
              "sections": [
                {
                  "heading": "Rule 1. Scope of Rules",
                  "level": 1,
                  "content": "These rules govern procedure in the Supreme Court...",
                  "subsections": [
                    {
                      "heading": "(a) Scope",
                      "level": 2,
                      "content": "These rules govern procedure in the Supreme Court...",
                      "subsections": []
                    }
                  ]
                }
              ],
              "structure": [
                {
                  "type": "heading",
                  "level": 1,
                  "text": "Rule 1. Scope of Rules"
                },
                {
                  "type": "paragraph",
                  "text": "These rules govern procedure..."
                }
              ]
            },
            "metadata": {
              "last_updated": "2023-12-01",
              "effective_date": "2024-01-01",
              "authority": "North Dakota Supreme Court",
              "related_rules": [
                {
                  "rule_number": "2",
                  "citation": "N.D.R.App.P. 2",
                  "title": "Rule 2. Suspension of Rules"
                }
              ],
              "cross_references": [
                {
                  "text": "N.D.R.Civ.P. 1",
                  "url": "https://www.ndcourts.gov/legal-resources/rules/civil-procedure/rule-1"
                }
              ],
              "scraped_at": "2024-01-15T10:30:00Z",
              "file_size_bytes": 2048,
              "html_checksum": "sha256:abc123..."
            }
          }
        ]
      }
    ]
  }
}
```

## Field Descriptions

### Top-Level Fields
- **metadata**: Global information about the scraping process
- **data**: Contains all scraped rule data organized by categories

### Category Fields
- **category_name**: Human-readable category name
- **category_url**: Source URL for the category page
- **rule_count**: Number of rules in this category
- **rules**: Array of individual rule objects

### Rule Fields
- **title**: Full title of the rule
- **rule_number**: Extracted rule number (e.g., "1", "1A")
- **citation**: Proper legal citation (e.g., "N.D.R.App.P. 1")
- **source_url**: Original source URL
- **content**: Contains both plain text and structured content
- **metadata**: Rule-specific metadata and cross-references

### Content Fields
- **plain_text**: Raw text as scraped (preserves original formatting)
- **structured_content**: Markdown-formatted content with preserved structure
- **sections**: Hierarchical section structure (max 4 levels)
- **structure**: Flat list of document elements (headings, paragraphs, lists)

### Metadata Fields
- **last_updated**: When the rule was last updated (if available)
- **effective_date**: When the rule becomes effective (if available)
- **authority**: Which court/body promulgated the rule
- **related_rules**: Array of related rules within the same category
- **cross_references**: References to rules in other categories
- **scraped_at**: Timestamp when this rule was scraped
- **file_size_bytes**: Size of the original HTML file
- **html_checksum**: SHA256 hash for integrity verification

## Implementation Notes

### Section Depth Enforcement
- Headings beyond h4 are flattened to h4 level
- Content is preserved but structure is simplified
- This ensures consistent analysis across all rules

### Markdown Generation
- Headings: `#` for h1, `##` for h2, etc.
- Lists: Preserved as `-` or `1.` format
- Paragraphs: Separated by double newlines
- Emphasis: Preserved as `*italic*` or `**bold**`

### Cross-Reference Handling
- Internal references within the same category
- External references to other rule categories
- URL resolution for all cross-references
- Validation of reference integrity

### Data Integrity
- Checksums for HTML content verification
- Timestamps for all operations
- File size tracking for monitoring
- Error logging for failed extractions 