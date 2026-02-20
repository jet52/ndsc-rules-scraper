"""
Rule Link Fetcher for ND Court Rules.
Extracts rule links from a category index page.
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def fetch_rule_links(
    session: requests.Session,
    category_url: str,
    logger=None,
) -> List[Dict]:
    """
    Fetch a category index page and extract links to individual rules.

    Args:
        session: Configured requests session
        category_url: URL of the category index page
        logger: Optional logger instance

    Returns:
        List of dicts with 'url', 'title', 'rule_number' keys, sorted by rule number
    """
    try:
        response = session.get(category_url, timeout=30)
        if response.status_code != 200:
            if logger:
                logger.error(
                    f"Failed to fetch category page: HTTP {response.status_code}"
                )
            return []
    except requests.exceptions.RequestException as e:
        if logger:
            logger.error(f"Request error for category page: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    rule_links = []
    seen_urls = set()

    # Extract rule links from the page
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text().strip()

        # Use strict URL pattern: /legal-resources/rules/{category}/{slug}
        # Matches numeric (28), hyphenated (6-1), and appendix (appendix-a) slugs.
        # The $ anchor prevents matching sub-pages like /9/appendix-jury-standards.
        pattern = r'/legal-resources/rules/[a-z]+/([\w][\w-]*)$'
        match = re.search(pattern, href)
        if not match:
            continue

        # Skip blacklisted paths
        href_lower = href.lower()
        if any(kw in href_lower for kw in ['committee', 'tables', 'joint', 'meeting']):
            continue

        full_url = urljoin('https://www.ndcourts.gov', href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        rule_links.append({
            'url': full_url,
            'title': text,
            'rule_number': match.group(1),
        })

    # Also check the <select> dropdown which has all rules listed
    for option in soup.find_all('option', value=True):
        href = option.get('value', '')
        text = option.get_text().strip()

        pattern = r'/legal-resources/rules/[a-z]+/([\w][\w-]*)$'
        match = re.search(pattern, href)
        if not match:
            continue

        href_lower = href.lower()
        if any(kw in href_lower for kw in ['committee', 'tables', 'joint', 'meeting']):
            continue

        full_url = href if href.startswith('http') else urljoin('https://www.ndcourts.gov', href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        rule_links.append({
            'url': full_url,
            'title': text,
            'rule_number': match.group(1),
        })

    # Sort by rule number: numeric first, then non-numeric (appendices)
    def _sort_key(r):
        rn = r['rule_number']
        # Try pure numeric
        try:
            return (0, float(rn), '')
        except ValueError:
            pass
        # Try hyphenated numeric like "6-1" -> (0, 6.0, '1')
        parts = rn.split('-')
        if parts[0].isdigit():
            return (0, float(parts[0]), '-'.join(parts[1:]))
        # Non-numeric (appendix-a) -> sort after all numeric rules
        return (1, 0, rn)

    rule_links.sort(key=_sort_key)

    return rule_links
