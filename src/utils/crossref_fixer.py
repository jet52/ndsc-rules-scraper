"""
Cross-Reference Fixer for ND Court Rules.

Scans rule markdown files and converts absolute ND Courts URLs to relative
local links where a matching file exists on disk.
"""

import re
from pathlib import Path
from typing import Optional


# Matches markdown links with absolute rule paths:
# [text](/legal-resources/rules/{category}/{slug})
_LINK_RE = re.compile(
    r'\[([^\]]+)\]\(/legal-resources/rules/([^/]+)/([^)]+)\)'
)

# Numeric-hyphen-numeric patterns that may represent dotted rules (e.g., 6-1 → 6.1)
_DOTTED_SLUG_RE = re.compile(r'^(\d+)-(\d+)$')


class CrossReferenceFixer:
    """Fix absolute cross-reference links in rule markdown files."""

    def __init__(self, repo_dir: str, category: str, combined: bool = False, logger=None):
        """
        Args:
            repo_dir: Path to the repository root
            category: Category slug (e.g., 'rjudconductcomm')
            combined: If True, rules live in {repo_dir}/{category}/ subdirs
            logger: Optional logger
        """
        self.repo_dir = Path(repo_dir)
        self.category = category
        self.combined = combined
        self.logger = logger

        # In combined mode, rules are in {repo_dir}/{category}/
        # In standalone mode, rules are in {repo_dir}/
        if combined:
            self.rules_dir = self.repo_dir / category
        else:
            self.rules_dir = self.repo_dir

    def scan(self) -> dict:
        """Scan all rule files and compute fixes.

        Returns:
            Dict mapping relative file paths to new content for files that changed.
        """
        changes = {}

        for filepath in sorted(self.rules_dir.glob('rule-*.md')):
            original = filepath.read_text(encoding='utf-8')
            fixed = self._fix_links(original)

            if fixed != original:
                # Use path relative to repo root for git operations
                rel_path = str(filepath.relative_to(self.repo_dir))
                changes[rel_path] = fixed

        return changes

    def _fix_links(self, content: str) -> str:
        """Replace absolute rule links with relative ones where possible."""
        return _LINK_RE.sub(self._replace_link, content)

    def _replace_link(self, match: re.Match) -> str:
        """Replace a single link match."""
        text = match.group(1)
        link_category = match.group(2)
        slug = match.group(3)

        # Sub-path slugs (e.g., appendix/1) — no local file, use full URL
        if '/' in slug:
            url = f"https://www.ndcourts.gov/legal-resources/rules/{link_category}/{slug}"
            return f"[{text}]({url})"

        # Resolve the target file
        resolved = self._resolve_file(link_category, slug)
        if resolved:
            return f"[{text}]({resolved})"

        # No local file found — use full URL
        url = f"https://www.ndcourts.gov/legal-resources/rules/{link_category}/{slug}"
        return f"[{text}]({url})"

    def _resolve_file(self, link_category: str, slug: str) -> Optional[str]:
        """Try to find a matching local file for the given category/slug.

        Returns:
            A relative link string (e.g., 'rule-terms.md' or '../ndrct/rule-6.1.md'),
            or None if no file found.
        """
        same_category = (link_category == self.category)

        if same_category:
            target_dir = self.rules_dir
        elif self.combined:
            target_dir = self.repo_dir / link_category
        else:
            # Standalone mode, cross-category: check sibling directory
            target_dir = self.rules_dir.parent / link_category

        if not target_dir.exists():
            return None

        # Try exact slug match first: rule-{slug}.md
        candidate = target_dir / f"rule-{slug}.md"
        if candidate.exists():
            return self._make_relative(link_category, f"rule-{slug}.md", same_category)

        # Try dotted variant: 6-1 → 6.1
        dot_match = _DOTTED_SLUG_RE.match(slug)
        if dot_match:
            dotted = f"{dot_match.group(1)}.{dot_match.group(2)}"
            candidate = target_dir / f"rule-{dotted}.md"
            if candidate.exists():
                return self._make_relative(link_category, f"rule-{dotted}.md", same_category)

        return None

    def _make_relative(self, link_category: str, filename: str, same_category: bool) -> str:
        """Build a relative link path."""
        if same_category:
            return filename
        else:
            return f"../{link_category}/{filename}"
