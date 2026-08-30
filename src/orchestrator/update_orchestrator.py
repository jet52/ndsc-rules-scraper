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
        'local': 'Local Court Procedural and Administrative Rules',
        'admissiontopracticer': 'Admission to Practice Rules',
        'ndrcontinuinglegaled': 'North Dakota Rules for Continuing Legal Education',
        'ndrprofconduct': 'North Dakota Rules of Professional Conduct',
        'ndrlawyerdiscipl': 'North Dakota Rules for Lawyer Discipline',
        'ndstdsimposinglawyersanctions': 'North Dakota Standards for Imposing Lawyer Sanctions',
        'ndcodejudconduct': 'North Dakota Code of Judicial Conduct',
        'rjudconductcomm': 'Rules of the Judicial Conduct Commission',
        'ndrprocr': 'Rules on Procedural Rules, Administrative Rules and Administrative Orders',
        'ndrlocalctpr': 'Rules on Local Court Procedural Rules and Administrative Rules',
        'rltdpracticeoflawbylawstudents': 'Limited Practice of Law by Law Students',
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
        self.git_base_dir = git_config.get('repo_dir', 'data/rules')

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

    def update_category(self, category: str, combined_mode: bool = False, dry_run: bool = False) -> Dict:
        """
        Check a category for minor corrections and new amendments.

        Args:
            category: Category identifier (e.g., 'ndrappp')
            combined_mode: If True, use git_base_dir as repo (not {base_dir}/{category})
                          and set category_prefix on the git manager.
            dry_run: If True, report differences without applying any changes.

        Returns:
            Stats dict with keys: category, skipped, amended, new_commits,
            corrections_found, new_amendments_found, errors
        """
        stats = {
            'category': category,
            'skipped': 0,
            'amended': 0,
            'new_commits': 0,
            'corrections_found': 0,
            'new_amendments_found': 0,
            'errors': [],
            'redated': [],
            'start_time': time.time(),
        }

        category_config = self.config.get('git', {}).get('categories', {}).get(category, {})
        base_url = category_config.get(
            'base_url',
            f'https://www.ndcourts.gov/legal-resources/rules/{category}'
        )
        category_name = self.CATEGORY_NAMES.get(category, category)

        if combined_mode:
            repo_dir = self.git_base_dir
            category_prefix = category
        else:
            repo_dir = os.path.join(self.git_base_dir, category)
            category_prefix = None

        # Verify the repo exists
        if not os.path.isdir(os.path.join(repo_dir, '.git')):
            if combined_mode:
                error = (
                    f"Combined repository not found at {repo_dir}. "
                    f"Run a full build first: python3 build_git_history.py --all"
                )
            else:
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
            category_prefix=category_prefix,
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

                # Normalize the rule identifier to the title-derived form used by
                # the initial build to name files. The index slug is hyphenated
                # (e.g. "2-1" for Rule 2.1), but files are committed as
                # "rule-2.1.md" from version_history.rule_number. Using the slug
                # for local lookups misses, making every dotted rule look "new".
                # Reassigning here keeps detection consistent with the build and
                # propagates to the correction/amendment phases via rule_link.
                rule_number = version_history.rule_number
                rule_link['rule_number'] = rule_number

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

                elif current_version.effective_date is None:
                    # The court publishes no effective date for this page
                    # (version table row 01/01/0001). Text is the only
                    # comparison available: same text = no change, different
                    # text = a correction under the same (unknown) date.
                    if local_content == current_content.markdown:
                        if self.logger:
                            self.logger.debug(f"  No change: Rule {rule_number} (date not published)")
                        stats['skipped'] += 1
                    else:
                        if self.logger:
                            self.logger.info(
                                f"  Minor correction detected: Rule {rule_number} (date not published)"
                            )
                        corrections.append((rule_link, current_content.markdown))

                elif local_date is None:
                    # Local history has only unpublished-date commits and the
                    # court now publishes dated versions: every web version is
                    # new to us; _apply_new_amendments takes them all.
                    if self.logger:
                        self.logger.info(
                            f"  New amendment detected: Rule {rule_number} "
                            f"(local: date not published, web: {current_version.effective_date})"
                        )
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

        # Record counts for both modes
        stats['corrections_found'] = len(corrections)
        stats['new_amendments_found'] = len(new_amendments)

        # Dry-run: report and return without applying
        if dry_run:
            if corrections:
                print()
                print(f"--- Corrections found ({len(corrections)}) ---")
                for rule_link, new_content in corrections:
                    rule_number = rule_link['rule_number']
                    old_content = git_manager.get_current_file_content(rule_number) or ""
                    diff_lines = list(difflib.unified_diff(
                        old_content.splitlines(keepends=True),
                        new_content.splitlines(keepends=True),
                        fromfile=f"rule-{rule_number}.md (local)",
                        tofile=f"rule-{rule_number}.md (web)",
                    ))
                    print(f"\nRule {rule_number}:")
                    print(''.join(diff_lines))

            if new_amendments:
                print()
                print(f"--- New amendments found ({len(new_amendments)}) ---")
                for rule_link, version_history in new_amendments:
                    rule_number = rule_link['rule_number']
                    local_date = git_manager.get_rule_effective_date(rule_number)
                    current_version = version_history.versions[-1]
                    if local_date:
                        print(f"  Rule {rule_number}: local {local_date} → web {current_version.effective_date}")
                    else:
                        print(f"  Rule {rule_number}: new rule (web {current_version.effective_date})")

            if not corrections and not new_amendments:
                print("\nNo corrections or new amendments detected.")

            return self._finalize_stats(stats)

        # Phase B: Apply minor corrections as new, dated commits.
        # Each correction is committed on its own file at detection time rather
        # than amended into HEAD — amending HEAD in combined mode folds the
        # change into whatever unrelated rule's commit is currently at the tip.
        for rule_link, new_content in corrections:
            rule_number = rule_link['rule_number']
            if self.logger:
                self.logger.info(f"Committing correction for Rule {rule_number}")

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

            success = git_manager.commit_correction(rule_number, new_content)
            if success:
                stats['amended'] += 1
                if self.logger:
                    self.logger.info(f"  Committed correction for Rule {rule_number}")
            else:
                # Restore original content
                git_manager.restore_rule_file(rule_number)
                error_msg = f"Correction commit failed for Rule {rule_number}, restored original"
                if self.logger:
                    self.logger.error(error_msg)
                stats['errors'].append(error_msg)

        # Phase C: Backfill & commit new amendments
        if new_amendments:
            self._apply_new_amendments(
                new_amendments, git_manager, stats
            )

        return self._finalize_stats(stats)

    @staticmethod
    def _words_only(text: str) -> str:
        """Collapse a rule's markdown to its non-whitespace characters.

        A re-dated version is republished with the same words but often not the
        same spacing — the court's 2017 "technical correction" to N.D.R. Lawyer
        Discipl. 4.5 changed `1.The petitioner` to `1. The petitioner` and
        `programs.If` to `programs. If`, and nothing else. Comparing on words
        alone is what lets us recognize the version across that churn. It is
        deliberately blunt: it cannot distinguish two versions that differ only
        in whitespace, which is exactly why the caller takes the NEWEST match.
        """
        return ''.join(text.split())

    def _reanchor_by_text(
        self,
        rule_number: str,
        version_history: VersionHistory,
        git_manager: GitVersionManager,
    ):
        """Locate the local file's version in the web history by text identity.

        Returns (index, RuleVersion) of the newest web version whose words match
        the local file, or (None, None). Searches newest-first and stops at the
        first match, so a wedged rule costs one fetch in the common case.
        """
        local_content = git_manager.get_current_file_content(rule_number)
        if not local_content:
            return None, None

        local_words = self._words_only(local_content)
        versions = version_history.versions

        for idx in range(len(versions) - 1, -1, -1):
            version = versions[idx]
            content = self.version_fetcher.fetch_version(version, version_history)
            time.sleep(self.request_delay)
            if content and self._words_only(content.markdown) == local_words:
                return idx, version

        return None, None

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
                    # The court sometimes re-dates a version in place: the page's
                    # stated effective date changes while the words do not. The
                    # local date then names a version the site no longer lists,
                    # every later run re-detects the same "new amendment" and
                    # skips it, and the rule is wedged forever. Fall back to
                    # identifying the anchor by its text instead of its date.
                    anchor_idx, matched = self._reanchor_by_text(
                        rule_number, version_history, git_manager
                    )
                    if anchor_idx is None and all(
                        v.effective_date > local_date for v in version_history.versions
                    ):
                        # A rule number reused for a NEW rule: the page's whole
                        # version history postdates our local version, so
                        # nothing on the site can anchor it and every web
                        # version is missing by definition. N.D.R.Ct. 11.10
                        # (Title and Citation, eff. 2025-03-01) became
                        # Reliable Electronic Means Proceedings, adopted
                        # 2026-09-01 with a one-entry history; the old content
                        # moved to 11.11. The local file's last version stays
                        # in git as the prior rule's text under that number.
                        if self.logger:
                            self.logger.warning(
                                f"  Rule {rule_number}: every web version postdates the "
                                f"local effective date {local_date} — treating as a "
                                f"REUSED NUMBER and taking all {len(version_history.versions)} "
                                f"web version(s) as new"
                            )
                        stats.setdefault('reused_numbers', []).append({
                            'rule_number': rule_number,
                            'local_date': str(local_date),
                            'web_dates': [str(v.effective_date) for v in version_history.versions],
                        })
                        anchor_idx = -1
                    if anchor_idx is None:
                        if self.logger:
                            self.logger.warning(
                                f"  Could not find anchor date {local_date} in version history "
                                f"for Rule {rule_number}, and no web version matches the local "
                                f"text — skipping"
                            )
                        stats['errors'].append(
                            f"Anchor date {local_date} not found for Rule {rule_number}"
                        )
                        continue

                    # Re-anchoring keeps the backfill moving, but the local date
                    # is now known-wrong and only a human can decide how to
                    # restate it (the git commit date and any downstream
                    # point-in-time store both encode it). Surface it loudly
                    # rather than silently adopting the site's new date.
                    if anchor_idx == -1:
                        matched = None
                    if matched is not None and self.logger:
                        self.logger.warning(
                            f"  Rule {rule_number} appears RE-DATED by the court: local "
                            f"effective date {local_date} is absent from the web version "
                            f"history, but the local text matches the web version effective "
                            f"{matched.effective_date}. Re-anchoring there; the local date "
                            f"needs manual correction."
                        )
                    if matched is not None:
                        stats['redated'].append({
                            'rule_number': rule_number,
                            'local_date': str(local_date),
                            'web_date': str(matched.effective_date),
                            'url': matched.url,
                        })

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
            eff = v.effective_date or date.min
            try:
                return (eff, 0, float(rn), '')
            except ValueError:
                pass
            parts = rn.split('-')
            if parts[0].isdigit():
                return (eff, 0, float(parts[0]), '-'.join(parts[1:]))
            return (eff, 1, 0, rn)

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

            if content.effective_date is None:
                # No date to filter committee minutes against; the git
                # manager writes the title/source/status body itself.
                commit_body = ""
            else:
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
                f"{stats['corrections_found']} corrections found, "
                f"{stats['amended']} amended, "
                f"{stats['new_amendments_found']} new amendments found, "
                f"{stats['new_commits']} new commits, "
                f"{len(stats.get('redated', []))} re-dated, "
                f"{len(stats['errors'])} errors "
                f"({stats['duration_seconds']:.1f}s)"
            )

        return stats

    def cleanup(self):
        """Clean up resources."""
        if self.session:
            self.session.close()
