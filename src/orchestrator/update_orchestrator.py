"""
Update Orchestrator for ND Court Rules.
Detects minor corrections and new amendments since the last scrape,
amending existing commits for silent corrections and creating new
commits for genuine amendments.
"""

import difflib
import os
import time
from datetime import date
from typing import Dict, List, Optional

import requests
import yaml

from scraper.version_history_extractor import VersionHistoryExtractor, VersionHistory
from scraper.historical_version_fetcher import HistoricalVersionFetcher, RuleVersionContent
from scraper.committee_minutes_fetcher import CommitteeMinutesFetcher
from scraper.commit_message_builder import CommitMessageBuilder
from scraper.rule_link_fetcher import fetch_rule_links
from git.git_version_manager import GitVersionManager


class UpdateOrchestrator:
    """Detects and applies corrections and new amendments to existing rule repos."""

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

        self.request_delay = request_delay

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

    def update_category(self, category: str) -> Dict:
        """
        Check a category for minor corrections and new amendments.

        Args:
            category: Category identifier (e.g., 'ndrappp')

        Returns:
            Stats dict with keys: category, skipped, amended, new_commits, errors
        """
        stats = {
            'category': category,
            'skipped': 0,
            'amended': 0,
            'new_commits': 0,
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

        # Verify the repo exists
        if not os.path.isdir(os.path.join(repo_dir, '.git')):
            error = (
                f"Repository not found at {repo_dir}. "
                f"Run a full build first: python3 build_git_history.py --category {category}"
            )
            if self.logger:
                self.logger.error(error)
            stats['errors'].append(error)
            return self._finalize_stats(stats)

        git_manager = GitVersionManager(
            repo_dir=repo_dir,
            author_name=self.git_author_name,
            author_email=self.git_author_email,
            logger=self.logger,
        )

        if self.logger:
            self.logger.info(f"Updating {category_name}")
            self.logger.info(f"  Base URL: {base_url}")
            self.logger.info(f"  Repo dir: {repo_dir}")

        # Fetch rule links from category index
        rule_links = fetch_rule_links(self.session, base_url, self.logger)
        if not rule_links:
            stats['errors'].append(f"No rule links found for {category}")
            return self._finalize_stats(stats)

        if self.logger:
            self.logger.info(f"Found {len(rule_links)} rules in {category_name}")

        # Phase A: Scrape & Compare
        corrections = []     # (rule_link, new_content_str)
        new_amendments = []  # (rule_link, version_history)

        for i, rule_link in enumerate(rule_links):
            rule_url = rule_link['url']
            rule_number = rule_link['rule_number']

            if self.logger:
                self.logger.info(
                    f"Checking rule {i + 1}/{len(rule_links)}: "
                    f"{rule_link.get('title', rule_url)}"
                )

            try:
                # Fetch rule page and extract version history
                response = self.session.get(rule_url, timeout=30)
                if response.status_code != 200:
                    stats['errors'].append(f"HTTP {response.status_code} for {rule_url}")
                    continue

                version_history = self.version_extractor.extract_version_history(
                    response.text, rule_url
                )

                if not version_history.versions:
                    if self.logger:
                        self.logger.warning(f"No versions found for {rule_url}")
                    continue

                # Get the current (latest) version from the website
                current_version = version_history.versions[-1]  # sorted oldest-first

                # Fetch current version's markdown
                current_content = self.version_fetcher.fetch_version(
                    current_version, version_history
                )
                if not current_content:
                    stats['errors'].append(f"Failed to fetch current version of {rule_url}")
                    continue

                # Read local repo state
                local_content = git_manager.get_current_file_content(rule_number)
                local_date = git_manager.get_rule_effective_date(rule_number)

                # Classify
                if local_content is None:
                    # New rule — treat like new_amendment
                    if self.logger:
                        self.logger.info(f"  New rule detected: {rule_number}")
                    new_amendments.append((rule_link, version_history))

                elif local_date == current_version.effective_date:
                    if local_content == current_content.markdown:
                        # No change
                        if self.logger:
                            self.logger.debug(f"  No change: Rule {rule_number}")
                        stats['skipped'] += 1
                    else:
                        # Minor correction — same date, different content
                        if self.logger:
                            self.logger.info(
                                f"  Minor correction detected: Rule {rule_number}"
                            )
                        corrections.append((rule_link, current_content.markdown))

                elif local_date is not None and current_version.effective_date > local_date:
                    # New amendment — newer effective date
                    if self.logger:
                        self.logger.info(
                            f"  New amendment detected: Rule {rule_number} "
                            f"(local: {local_date}, web: {current_version.effective_date})"
                        )
                    new_amendments.append((rule_link, version_history))

                else:
                    # Unexpected state (local date newer than web, or missing)
                    if self.logger:
                        self.logger.warning(
                            f"  Unexpected state for Rule {rule_number}: "
                            f"local_date={local_date}, web_date={current_version.effective_date}"
                        )
                    stats['skipped'] += 1

            except Exception as e:
                error_msg = f"Error checking {rule_url}: {e}"
                if self.logger:
                    self.logger.error(error_msg)
                stats['errors'].append(error_msg)

            # Rate limiting
            time.sleep(0.5)

        # Phase B: Apply minor corrections (amends)
        for rule_link, new_content in corrections:
            rule_number = rule_link['rule_number']
            if self.logger:
                self.logger.info(f"Amending correction for Rule {rule_number}")

            # Log the diff
            old_content = git_manager.get_current_file_content(rule_number) or ""
            diff_lines = list(difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"rule-{rule_number}.md (old)",
                tofile=f"rule-{rule_number}.md (new)",
            ))
            if diff_lines and self.logger:
                self.logger.info(f"  Diff for Rule {rule_number}:\n{''.join(diff_lines)}")

            success = git_manager.amend_rule_version(rule_number, new_content)
            if success:
                stats['amended'] += 1
                if self.logger:
                    self.logger.info(f"  Amended Rule {rule_number} successfully")
            else:
                # Restore original content
                git_manager.restore_rule_file(rule_number)
                error_msg = f"Amend failed for Rule {rule_number}, restored original"
                if self.logger:
                    self.logger.error(error_msg)
                stats['errors'].append(error_msg)

        # Phase C: Backfill & commit new amendments
        if new_amendments:
            self._apply_new_amendments(
                new_amendments, git_manager, stats
            )

        return self._finalize_stats(stats)

    def _apply_new_amendments(
        self,
        new_amendments: List,
        git_manager: GitVersionManager,
        stats: Dict,
    ) -> None:
        """Collect missing versions from new amendments and commit chronologically."""
        all_missing_versions = []

        for rule_link, version_history in new_amendments:
            rule_number = rule_link['rule_number']
            local_date = git_manager.get_rule_effective_date(rule_number)

            if local_date is None:
                # New rule — all versions are missing
                missing_versions = version_history.versions
            else:
                # Find the anchor: the version whose effective date matches local
                anchor_idx = None
                for idx, v in enumerate(version_history.versions):
                    if v.effective_date == local_date:
                        anchor_idx = idx
                        break

                if anchor_idx is None:
                    if self.logger:
                        self.logger.warning(
                            f"  Could not find anchor date {local_date} in version history "
                            f"for Rule {rule_number} — skipping"
                        )
                    stats['errors'].append(
                        f"Anchor date {local_date} not found for Rule {rule_number}"
                    )
                    continue

                # Versions after the anchor are missing
                missing_versions = version_history.versions[anchor_idx + 1:]

            if not missing_versions:
                continue

            if self.logger:
                self.logger.info(
                    f"  Fetching {len(missing_versions)} new version(s) for Rule {rule_number}"
                )

            for version in missing_versions:
                content = self.version_fetcher.fetch_version(version, version_history)
                if content:
                    all_missing_versions.append(content)
                else:
                    stats['errors'].append(
                        f"Failed to fetch version {version.url} for Rule {rule_number}"
                    )
                time.sleep(self.request_delay)

        if not all_missing_versions:
            return

        # Sort globally by (effective_date, rule_number) using same key as initial build
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

        all_missing_versions.sort(key=_version_sort_key)

        if self.logger:
            self.logger.info(
                f"Committing {len(all_missing_versions)} new version(s) chronologically"
            )

        # Track previous effective date per rule for commit message filtering
        # Seed with current local dates
        prev_dates: Dict[str, date] = {}
        for rule_link, version_history in new_amendments:
            rule_number = rule_link['rule_number']
            local_date = git_manager.get_rule_effective_date(rule_number)
            if local_date:
                prev_dates[rule_number] = local_date

        for content in all_missing_versions:
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

            success = git_manager.commit_rule_version(
                rule_number=content.rule_number,
                markdown_content=content.markdown,
                effective_date=content.effective_date,
                rule_title=content.rule_title,
                commit_body=commit_body,
                url=content.url,
                is_current=content.is_current,
            )
            if success:
                stats['new_commits'] += 1

            prev_dates[content.rule_number] = content.effective_date

    def _finalize_stats(self, stats: Dict) -> Dict:
        """Add timing info and log summary."""
        stats['end_time'] = time.time()
        stats['duration_seconds'] = stats['end_time'] - stats['start_time']

        if self.logger:
            self.logger.info(
                f"Update complete for {stats['category']}: "
                f"{stats['skipped']} unchanged, "
                f"{stats['amended']} amended, "
                f"{stats['new_commits']} new commits, "
                f"{len(stats['errors'])} errors "
                f"({stats['duration_seconds']:.1f}s)"
            )

        return stats

    def cleanup(self):
        """Clean up resources."""
        if self.session:
            self.session.close()
