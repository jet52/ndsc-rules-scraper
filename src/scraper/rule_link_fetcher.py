"""
Rule Link Fetcher for ND Court Rules.
Extracts rule links from a category index page.
"""

import re
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Appendix-of-forms subpages: /legal-resources/rules/{cat}/appendix/{n}.
# The category index never links these; only the category's own Appendix
# page does (N.D.R.Civ.P. has 24, N.D.R.Crim.P. 18). Each is a full
# versioned rule page filed as rule-Form-{n}.md.
_FORM_SUBPAGE_RE = re.compile(
    r'/legal-resources/rules/([a-z]+)/appendix/(\d+[A-Za-z]?)$')


def fetch_form_links(
    session: requests.Session,
    appendix_url: str,
    logger=None,
) -> List[Dict]:
    """Fetch an Appendix-of-forms page and extract its form subpage links.

    Returns entries shaped like fetch_rule_links's ('url', 'title',
    'rule_number'), with rule_number 'Form-{n}'.
    """
    try:
        response = session.get(appendix_url, timeout=30)
        if response.status_code != 200:
            if logger:
                logger.warning(
                    f"Failed to fetch appendix page {appendix_url}: "
                    f"HTTP {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        if logger:
            logger.warning(f"Request error for appendix page {appendix_url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    out, seen = [], set()
    for link in soup.find_all('a', href=True):
        m = _FORM_SUBPAGE_RE.search(link['href'])
        if not m:
            continue
        full_url = urljoin('https://www.ndcourts.gov', link['href'])
        if full_url in seen:
            continue
        seen.add(full_url)
        out.append({
            'url': full_url,
            'title': link.get_text().strip(),
            'rule_number': f"Form-{m.group(2).lower()}",
        })
    return out


def fetch_rule_links(
    session: requests.Session,
    category_url: str,
    logger=None,
    follow_appendix: bool = True,
    request_delay: float = 1.0,
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

    # Only links INTO THIS category are rules of this category. The court's
    # indexes cross-link: the Administrative Orders index carries an entry
    # "Revised and Adopted as Rule 21" whose href is Administrative RULE 21's
    # page (/ndsupctadminr/21). Matching any category filed that page as
    # Order 21 and flipped ndsupctadminorder/rule-21.md between Rule 21's
    # text and Order 21's every run (8 "silent correction" commits, 2026-07
    # to 2026-09-11). The category slug comes from the index URL itself.
    # Strict URL pattern: /legal-resources/rules/{this category}/{slug}.
    # Matches numeric (28), hyphenated (6-1), and appendix (appendix-a) slugs.
    # The $ anchor prevents matching sub-pages like /9/appendix-jury-standards.
    category = urlparse(category_url).path.rstrip('/').rsplit('/', 1)[-1]
    pattern = rf'/legal-resources/rules/{re.escape(category)}/([\w][\w-]*)$'

    # Extract rule links from the page
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text().strip()

        match = re.search(pattern, href, re.IGNORECASE)
        if not match:
            continue

        # Skip blacklisted paths. 'tables' is NOT excluded: ndrappp/tables is a
        # versioned document ("TABLES", eff. 2001-01-01), found missing 2026-08-30.
        href_lower = href.lower()
        if any(kw in href_lower for kw in ['committee', 'joint', 'meeting']):
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

        match = re.search(pattern, href, re.IGNORECASE)
        if not match:
            continue

        href_lower = href.lower()
        if any(kw in href_lower for kw in ['committee', 'joint', 'meeting']):
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

    # Follow appendix-of-forms container pages: their form subpages are
    # versioned rule pages the index never lists.
    if follow_appendix:
        for entry in list(rule_links):
            if entry['rule_number'].lower() != 'appendix':
                continue
            time.sleep(request_delay)
            forms = fetch_form_links(session, entry['url'], logger)
            if forms and logger:
                logger.info(
                    f"Found {len(forms)} appendix form page(s) under {entry['url']}")
            for f in forms:
                if f['url'] not in seen_urls:
                    seen_urls.add(f['url'])
                    rule_links.append(f)

    # Sort by rule number: numeric first, then non-numeric (appendices),
    # then appendix forms in numeric order
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
        form = re.fullmatch(r'Form-(\d+)([A-Za-z]?)', rn)
        if form:
            return (2, float(form.group(1)), form.group(2).lower())
        # Non-numeric (appendix-a) -> sort after all numeric rules
        return (1, 0, rn)

    rule_links.sort(key=_sort_key)

    return rule_links
