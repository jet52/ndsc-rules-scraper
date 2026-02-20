"""
Version History Orchestrator for ND Court Rules.
Coordinates all components to build a git repository with full rule version history.
"""

import os
import re
import time
from datetime import date
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup

from scraper.version_history_extractor import VersionHistoryExtractor
from scraper.historical_version_fetcher import HistoricalVersionFetcher
from scraper.committee_minutes_fetcher import CommitteeMinutesFetcher
from scraper.commit_message_builder import CommitMessageBuilder
from scraper.rule_link_fetcher import fetch_rule_links
from git.git_version_manager import GitVersionManager


class VersionHistoryOrchestrator:
    """Coordinates scraping, extraction, and git repository building."""

    CATEGORY_NAMES = {
        'ndrappp': 'North Dakota Rules of Appellate Procedure',
        'ndrct': 'North Dakota Rules of Court',
        'ndsupctadminr': 'North Dakota Supreme Court Administrative Rules',
        'ndsupctadminorder': 'North Dakota Supreme Court Administrative Orders',
        'ndrcivp': 'North Dakota Rules of Civil Procedure',
        'ndrcrimp': 'North Dakota Rules of Criminal Procedure',
        'ndrjuvp': 'North Dakota Rules of Juvenile Procedure',
        'ndrev': 'North Dakota Rules of Evidence',
    }

    def __init__(self, config_path: str = "config.yaml", logger=None):
        self.config = self._load_config(config_path)
        self.logger = logger
        self.session = self._create_session()

        self.version_extractor = VersionHistoryExtractor(logger)

        request_delay = self.config.get('version_history', {}).get('request_delay', 1.0)
        self.version_fetcher = HistoricalVersionFetcher(
            session=self.session,
            logger=logger,
            request_delay=request_delay,
        )

        git_config = self.config.get('git', {})
        self.git_manager = None  # Initialized per category
        self.git_author_name = git_config.get('author_name', 'ND Courts System')
        self.git_author_email = git_config.get('author_email', 'rules@ndcourts.gov')
        self.git_base_dir = git_config.get('repo_dir', '/Users/jerod/cDocs/refs/rules')

        # Initialize committee minutes fetcher and commit message builder
        vh_config = self.config.get('version_history', {})
        minutes_cache_dir = vh_config.get(
            'minutes_cache_dir',
            os.path.join(self.git_base_dir, '..', 'minutes_cache'),
        )

        self.committee_fetcher = CommitteeMinutesFetcher(
            session=self.session,
            cache_dir=minutes_cache_dir,
            logger=logger,
            request_delay=request_delay,
        )

        anthropic_client = self._create_anthropic_client()
        anthropic_config = self.config.get('anthropic', {})

        self.commit_message_builder = CommitMessageBuilder(
            anthropic_client=anthropic_client,
            committee_fetcher=self.committee_fetcher,
            haiku_model=anthropic_config.get('haiku_model', 'claude-haiku-4-5-20251001'),
            max_tokens=anthropic_config.get('max_tokens', 1000),
            temperature=anthropic_config.get('temperature', 0.1),
            logger=logger,
        )

    def _create_anthropic_client(self):
        """Create an Anthropic API client if an API key is available."""
        api_key = os.environ.get('ANTHROPIC_API_KEY') or self.config.get('anthropic', {}).get('api_key', '')
        if not api_key:
            if self.logger:
                self.logger.info(
                    "No Anthropic API key found. "
                    "Commit messages will use regex-based note trimming."
                )
            return None

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            if self.logger:
                self.logger.info("Anthropic client initialized for commit message generation")
            return client
        except ImportError:
            if self.logger:
                self.logger.warning(
                    "anthropic package not installed. "
                    "Commit messages will use regex-based note trimming."
                )
            return None
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to create Anthropic client: {e}")
            return None

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError):
            return {}

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        user_agent = self.config.get('scraping', {}).get(
            'user_agent', 'ND-Court-Rules-Scraper/1.0 (Educational Project)'
        )
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
        try:
            import certifi
            session.verify = certifi.where()
        except ImportError:
            session.verify = False
        return session

    def build_git_repository(self, category: str, force: bool = False) -> Dict:
        """
        Build a complete git repository for a rule category.

        Args:
            category: Category identifier (e.g., 'ndrappp')
            force: If True, rebuild even if repository exists

        Returns:
            Statistics dictionary
        """
        stats = {
            'category': category,
            'rules_found': 0,
            'rules_processed': 0,
            'versions_committed': 0,
            'errors': [],
            'start_time': time.time(),
        }

        category_config = self.config.get('git', {}).get('categories', {}).get(category, {})
        base_url = category_config.get(
            'base_url',
            f'https://www.ndcourts.gov/legal-resources/rules/{category}'
        )
        category_name = self.CATEGORY_NAMES.get(category, category)
        repo_dir = f"{self.git_base_dir}/{category}"

        if self.logger:
            self.logger.info(f"Building git repository for {category_name}")
            self.logger.info(f"  Base URL: {base_url}")
            self.logger.info(f"  Repo dir: {repo_dir}")

        # Initialize git manager for this category
        self.git_manager = GitVersionManager(
            repo_dir=repo_dir,
            author_name=self.git_author_name,
            author_email=self.git_author_email,
            logger=self.logger,
        )

        # Step 1: Initialize git repo
        self.git_manager.initialize_repository(category_name)

        # Step 2: Fetch category page and extract rule links
        rule_links = self._fetch_rule_links(base_url)
        stats['rules_found'] = len(rule_links)

        if self.logger:
            self.logger.info(f"Found {len(rule_links)} rules in {category_name}")

        # Step 3: Collect ALL versions across ALL rules, then sort globally by date
        all_version_work = []

        for i, rule_link in enumerate(rule_links):
            rule_url = rule_link['url']
            if self.logger:
                self.logger.info(
                    f"Extracting version history for rule {i + 1}/{len(rule_links)}: "
                    f"{rule_link.get('title', rule_url)}"
                )

            try:
                # Fetch the current rule page
                response = self.session.get(rule_url, timeout=30)
                if response.status_code != 200:
                    stats['errors'].append(f"HTTP {response.status_code} for {rule_url}")
                    continue

                # Extract version history
                version_history = self.version_extractor.extract_version_history(
                    response.text, rule_url
                )

                if not version_history.versions:
                    if self.logger:
                        self.logger.warning(f"No versions found for {rule_url}")
                    stats['errors'].append(f"No versions for {rule_url}")
                    continue

                # Fetch all historical version content
                version_contents = self.version_fetcher.fetch_all_versions(version_history)

                for content in version_contents:
                    all_version_work.append(content)

                stats['rules_processed'] += 1

            except Exception as e:
                error_msg = f"Error processing {rule_url}: {e}"
                if self.logger:
                    self.logger.error(error_msg)
                stats['errors'].append(error_msg)

            # Small delay between rule fetches
            time.sleep(0.5)

        # Step 4: Sort all versions globally by effective date, then by rule number
        def _version_sort_key(v):
            rn = v.rule_number
            try:
                return (v.effective_date, 0, float(rn), '')
            except ValueError:
                pass
            parts = rn.split('-')
            if parts[0].isdigit():
                return (v.effective_date, 0, float(parts[0]), '-'.join(parts[1:]))
            return (v.effective_date, 1, 0, rn)

        all_version_work.sort(key=_version_sort_key)

        if self.logger:
            self.logger.info(
                f"Committing {len(all_version_work)} total versions in chronological order"
            )

        # Step 5: Commit all versions in chronological order
        # Track previous effective date per rule for commit message filtering
        prev_dates: Dict[str, date] = {}

        for content in all_version_work:
            prev_effective_date = prev_dates.get(content.rule_number)

            commit_body = self.commit_message_builder.build_message(
                rule_number=content.rule_number,
                rule_title=content.rule_title,
                effective_date=content.effective_date,
                explanatory_notes=content.explanatory_notes,
                is_current=content.is_current,
                url=content.url,
                prev_effective_date=prev_effective_date,
            )

            success = self.git_manager.commit_rule_version(
                rule_number=content.rule_number,
                markdown_content=content.markdown,
                effective_date=content.effective_date,
                rule_title=content.rule_title,
                commit_body=commit_body,
                url=content.url,
                is_current=content.is_current,
            )
            if success:
                stats['versions_committed'] += 1

            prev_dates[content.rule_number] = content.effective_date

        stats['end_time'] = time.time()
        stats['duration_seconds'] = stats['end_time'] - stats['start_time']

        if self.logger:
            self.logger.info(
                f"Completed: {stats['rules_processed']} rules, "
                f"{stats['versions_committed']} versions committed in "
                f"{stats['duration_seconds']:.1f}s"
            )

        return stats

    def _fetch_rule_links(self, category_url: str) -> List[Dict]:
        """Fetch the category page and extract links to individual rules."""
        return fetch_rule_links(self.session, category_url, self.logger)

    def cleanup(self):
        """Clean up resources."""
        if self.session:
            self.session.close()
