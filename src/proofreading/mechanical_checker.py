"""
Mechanical proofreading checker for ND Court Rules.
Runs local-only checks (spelling, formatting, structural analysis) with zero API calls.
"""

import glob
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from spellchecker import SpellChecker

from proofreading.legal_dictionary import IGNORE_PATTERNS, LEGAL_TERMS


class MechanicalChecker:
    """Runs local mechanical checks on rule markdown files."""

    CATEGORY_NAMES = {
        'ndrappp': 'North Dakota Rules of Appellate Procedure',
        'ndrct': 'North Dakota Rules of Court',
        'ndsupctadminr': 'North Dakota Supreme Court Administrative Rules',
        'ndsupctadminorder': 'North Dakota Supreme Court Administrative Orders',
        'ndrcivp': 'North Dakota Rules of Civil Procedure',
        'ndrcrimp': 'North Dakota Rules of Criminal Procedure',
        'ndrjuvp': 'North Dakota Rules of Juvenile Procedure',
        'ndrev': 'North Dakota Rules of Evidence',
        'local': 'North Dakota Local Court Rules',
        'admissiontopracticer': 'Rules for Admission to Practice Law',
        'ndrcontinuinglegaled': 'Rules for Continuing Legal Education',
        'ndrprofconduct': 'North Dakota Rules of Professional Conduct',
        'ndrlawyerdiscipl': 'North Dakota Rules for Lawyer Discipline',
        'ndstdsimposinglawyersanctions': 'Standards for Imposing Lawyer Sanctions',
        'ndcodejudconduct': 'North Dakota Code of Judicial Conduct',
        'rjudconductcomm': 'Rules of the Judicial Conduct Commission',
        'ndrprocr': 'North Dakota Rules of Procedure',
        'ndrlocalctpr': 'North Dakota Rules of Local Court Procedure',
        'rltdpracticeoflawbylawstudents': 'Rules for Limited Practice of Law by Law Students',
    }

    def __init__(self, repo_dir: str, category: str, logger=None,
                 report_dir: Optional[str] = None):
        self.repo_dir = repo_dir
        self.category = category
        self.logger = logger
        self.report_dir = report_dir or repo_dir
        self.category_name = self.CATEGORY_NAMES.get(category, category)

        # Initialize spell checker with legal supplement
        self.spell = SpellChecker()
        self.spell.word_frequency.load_words(LEGAL_TERMS)

    def run_checks(self) -> dict:
        """Load all rules and run all mechanical checks. Returns report dict."""
        rules = self._load_rules()
        if not rules:
            if self.logger:
                self.logger.warning(f"No rule files found in {self.repo_dir}")
            return self._empty_report()

        if self.logger:
            self.logger.info(f"Found {len(rules)} rule files to check")

        # Collect all rule filenames for cross-reference validation
        rule_files = {Path(r[0]).stem for r in rules}  # e.g. {'rule-1', 'rule-6-1'}

        per_rule = []
        for filename, content in rules:
            findings = []
            findings.extend(self._check_spelling(content))
            findings.extend(self._check_doubled_words(content))
            findings.extend(self._check_numbering_gaps(content))
            findings.extend(self._check_unbalanced_delimiters(content))
            findings.extend(self._check_cross_references(content, rule_files))
            findings.extend(self._check_whitespace(content))
            findings.extend(self._check_empty_sections(content))
            findings.extend(self._check_broken_markdown(content))
            findings.extend(self._check_inconsistent_subsection_style(content))

            rule_number = self._filename_to_rule_number(filename)
            per_rule.append({
                'filename': filename,
                'rule_number': rule_number,
                'has_issues': len(findings) > 0,
                'findings': findings,
            })

            if self.logger and findings:
                self.logger.info(f"  {filename}: {len(findings)} findings")

        report = self._compile_report(per_rule)
        self._write_markdown_report(report)
        self._write_json_report(report)
        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_spelling(self, content: str) -> List[dict]:
        """Check spelling using pyspellchecker + legal dictionary."""
        findings = []
        # Strip content that should be ignored
        cleaned = content
        for pattern in IGNORE_PATTERNS:
            cleaned = pattern.sub(' ', cleaned)

        # Remove markdown formatting characters
        cleaned = re.sub(r'[*#`|_\[\]()>]', ' ', cleaned)

        # Extract words (alpha only, at least 2 chars)
        words = re.findall(r'\b[a-zA-Z]{2,}\b', cleaned)

        # Check each unique word
        word_counts = Counter(w.lower() for w in words)
        unknown = self.spell.unknown(word_counts.keys())

        for word in sorted(unknown):
            # Skip single-letter and very short words
            if len(word) < 3:
                continue
            # Skip words that are all caps (likely acronyms)
            original_forms = [w for w in words if w.lower() == word]
            if any(w.isupper() for w in original_forms):
                continue

            candidates = self.spell.candidates(word)
            suggestion = None
            if candidates:
                # Get the most likely correction
                correction = self.spell.correction(word)
                if correction and correction != word:
                    suggestion = correction

            # Find a context line containing this word
            quote = self._find_context(content, word)

            findings.append({
                'severity': 'WARNING',
                'category': 'spelling',
                'quote': quote,
                'description': f'Possible misspelling: "{word}"',
                'suggestion': suggestion,
            })

        return findings

    def _check_doubled_words(self, content: str) -> List[dict]:
        """Check for doubled words like 'the the'."""
        findings = []
        pattern = re.compile(r'\b(\w+)\s+\1\b', re.IGNORECASE)
        for match in pattern.finditer(content):
            word = match.group(1).lower()
            # Skip intentional doubles (e.g. section-section patterns)
            if word in ('that', 'had', 'do'):
                continue
            quote = self._find_context(content, match.group(0))
            findings.append({
                'severity': 'ERROR',
                'category': 'doubled-word',
                'quote': quote,
                'description': f'Doubled word: "{match.group(0)}"',
                'suggestion': match.group(1),
            })
        return findings

    def _check_numbering_gaps(self, content: str) -> List[dict]:
        """Check for gaps in lettered/numbered sequences within a rule."""
        findings = []

        # Check (a), (b), (c) sequences
        letter_matches = re.findall(r'\(([a-z])\)', content)
        findings.extend(self._detect_sequence_gaps(
            letter_matches, 'letter', content,
        ))

        # Check (1), (2), (3) sequences
        number_matches = re.findall(r'\((\d+)\)', content)
        findings.extend(self._detect_number_gaps(
            number_matches, content,
        ))

        return findings

    def _detect_sequence_gaps(self, items: list, kind: str,
                              content: str) -> List[dict]:
        """Detect gaps in a sequence of single letters."""
        findings = []
        if len(items) < 2:
            return findings

        for i in range(1, len(items)):
            expected_ord = ord(items[i - 1]) + 1
            actual_ord = ord(items[i])
            if actual_ord > expected_ord and actual_ord <= ord('z'):
                expected_char = chr(expected_ord)
                findings.append({
                    'severity': 'WARNING',
                    'category': 'numbering',
                    'quote': f'({items[i - 1]}) ... ({items[i]})',
                    'description': (
                        f'Possible {kind} sequence gap: '
                        f'({items[i - 1]}) jumps to ({items[i]}), '
                        f'expected ({expected_char})'
                    ),
                    'suggestion': None,
                })
        return findings

    def _detect_number_gaps(self, items: list, content: str) -> List[dict]:
        """Detect gaps in numeric sequences like (1), (2), (3)."""
        findings = []
        if len(items) < 2:
            return findings

        nums = [int(n) for n in items]
        for i in range(1, len(nums)):
            if nums[i] == nums[i - 1] + 2:
                # Gap of exactly 1 — likely a skip
                expected = nums[i - 1] + 1
                findings.append({
                    'severity': 'WARNING',
                    'category': 'numbering',
                    'quote': f'({nums[i - 1]}) ... ({nums[i]})',
                    'description': (
                        f'Possible number sequence gap: '
                        f'({nums[i - 1]}) jumps to ({nums[i]}), '
                        f'expected ({expected})'
                    ),
                    'suggestion': None,
                })
        return findings

    def _check_unbalanced_delimiters(self, content: str) -> List[dict]:
        """Check for unbalanced parentheses, brackets, and quotes per paragraph."""
        findings = []
        paragraphs = content.split('\n\n')

        for para in paragraphs:
            if not para.strip():
                continue

            # Skip markdown table rows
            if para.strip().startswith('|'):
                continue

            checks = [
                ('(', ')', 'parentheses'),
                ('[', ']', 'brackets'),
            ]
            for open_ch, close_ch, name in checks:
                opens = para.count(open_ch)
                closes = para.count(close_ch)
                if opens != closes:
                    # Get first line of paragraph for context
                    first_line = para.strip().split('\n')[0][:100]
                    findings.append({
                        'severity': 'WARNING',
                        'category': 'delimiter',
                        'quote': first_line,
                        'description': (
                            f'Unbalanced {name}: '
                            f'{opens} opening, {closes} closing'
                        ),
                        'suggestion': None,
                    })

            # Check straight double quotes (should be even per paragraph)
            quotes = para.count('"')
            if quotes % 2 != 0:
                first_line = para.strip().split('\n')[0][:100]
                findings.append({
                    'severity': 'WARNING',
                    'category': 'delimiter',
                    'quote': first_line,
                    'description': f'Odd number of double quotes ({quotes})',
                    'suggestion': None,
                })

        return findings

    def _check_cross_references(self, content: str,
                                rule_files: set) -> List[dict]:
        """Check that Rule X references correspond to existing rule files."""
        findings = []
        # Match "Rule X" or "Rule X.Y" — standalone references
        pattern = re.compile(r'Rule\s+(\d+(?:\.\d+)?)\b')

        for match in pattern.finditer(content):
            rule_ref = match.group(1)
            # Convert to filename format: "6.1" → "rule-6-1"
            file_stem = 'rule-' + rule_ref.replace('.', '-')

            if file_stem not in rule_files:
                # Don't flag references to rules in other categories
                # (we can only check within the same category)
                quote = self._find_context(content, match.group(0))
                findings.append({
                    'severity': 'WARNING',
                    'category': 'cross-reference',
                    'quote': quote,
                    'description': (
                        f'Reference to Rule {rule_ref} — '
                        f'no matching file {file_stem}.md in this category'
                    ),
                    'suggestion': None,
                })

        return findings

    def _check_whitespace(self, content: str) -> List[dict]:
        """Check for whitespace issues: space before punctuation, multiple spaces."""
        findings = []

        # Space before punctuation (but not before opening parens)
        for match in re.finditer(r' +([.,;:!?])', content):
            quote = self._find_context(content, match.group(0))
            findings.append({
                'severity': 'WARNING',
                'category': 'whitespace',
                'quote': quote,
                'description': f'Space before punctuation: " {match.group(1)}"',
                'suggestion': match.group(1),
            })

        # Multiple consecutive spaces (not at start of line)
        for match in re.finditer(r'(?<=\S)  {2,}', content):
            quote = self._find_context(content, match.group(0))
            findings.append({
                'severity': 'WARNING',
                'category': 'whitespace',
                'quote': quote,
                'description': 'Multiple consecutive spaces',
                'suggestion': None,
            })

        return findings

    def _check_empty_sections(self, content: str) -> List[dict]:
        """Detect markdown headers with no content before the next header."""
        findings = []
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if not re.match(r'^#{1,6}\s', line):
                continue
            # Look ahead for content before next header or end
            has_content = False
            for j in range(i + 1, len(lines)):
                if re.match(r'^#{1,6}\s', lines[j]):
                    break
                if lines[j].strip():
                    has_content = True
                    break
            if not has_content:
                findings.append({
                    'severity': 'WARNING',
                    'category': 'empty-section',
                    'quote': line.strip(),
                    'description': 'Header with no content following it',
                    'suggestion': None,
                })
        return findings

    def _check_broken_markdown(self, content: str) -> List[dict]:
        """Check for broken markdown formatting."""
        findings = []

        # Unclosed bold markers: odd number of ** in a line
        for line_num, line in enumerate(content.split('\n'), 1):
            bold_count = len(re.findall(r'\*\*', line))
            if bold_count % 2 != 0:
                findings.append({
                    'severity': 'WARNING',
                    'category': 'markdown',
                    'quote': line.strip()[:100],
                    'description': f'Possibly unclosed bold marker (**) on line {line_num}',
                    'suggestion': None,
                })

        # Malformed markdown links: [text]( with no closing )
        for match in re.finditer(r'\[[^\]]*\]\([^)]*$', content, re.MULTILINE):
            findings.append({
                'severity': 'WARNING',
                'category': 'markdown',
                'quote': match.group(0)[:100],
                'description': 'Possibly malformed markdown link (unclosed parenthesis)',
                'suggestion': None,
            })

        return findings

    def _check_inconsistent_subsection_style(self, content: str) -> List[dict]:
        """Flag mixed subsection labeling styles within the same rule."""
        findings = []

        # Check if rule mixes (a)/(A) style
        lower_letters = set(re.findall(r'\(([a-z])\)', content))
        upper_letters = set(re.findall(r'\(([A-Z])\)', content))

        # Only flag if both appear and both have multiple entries
        # (a single uppercase in parentheses could be a name reference)
        if len(lower_letters) >= 2 and len(upper_letters) >= 2:
            findings.append({
                'severity': 'WARNING',
                'category': 'formatting',
                'quote': (
                    f'Lower: ({", ".join(sorted(lower_letters)[:3])}), '
                    f'Upper: ({", ".join(sorted(upper_letters)[:3])})'
                ),
                'description': (
                    'Mixed lowercase and uppercase lettered subsections '
                    'in the same rule'
                ),
                'suggestion': None,
            })

        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_rules(self) -> List[Tuple[str, str]]:
        """Load all rule-*.md files from the repo directory."""
        pattern = str(Path(self.repo_dir) / 'rule-*.md')
        files = sorted(glob.glob(pattern))
        rules = []
        for filepath in files:
            filename = Path(filepath).name
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            if content.strip():
                rules.append((filename, content))
        return rules

    def _filename_to_rule_number(self, filename: str) -> str:
        """Convert 'rule-6-1.md' to '6.1', 'rule-appendix-a.md' to 'appendix-a'."""
        stem = filename.replace('rule-', '').replace('.md', '')
        if stem.startswith('appendix'):
            return stem
        parts = stem.split('-')
        if all(p.isdigit() for p in parts):
            return '.'.join(parts)
        return stem

    def _find_context(self, content: str, needle: str) -> str:
        """Find a line containing the needle and return it as context."""
        needle_lower = needle.lower()
        for line in content.split('\n'):
            if needle_lower in line.lower():
                stripped = line.strip()
                if len(stripped) > 120:
                    return stripped[:120] + '...'
                return stripped
        return needle[:100]

    def _empty_report(self) -> dict:
        return {
            'metadata': {
                'category': self.category,
                'category_name': self.category_name,
                'generated_at': datetime.now().isoformat(),
                'checker': 'mechanical',
                'rules_reviewed': 0,
                'rules_with_findings': 0,
            },
            'summary': {
                'total_errors': 0,
                'total_warnings': 0,
            },
            'findings': [],
            'per_rule': [],
        }

    def _compile_report(self, per_rule: List[dict]) -> dict:
        """Aggregate per-rule findings into structured report."""
        all_findings = []
        rules_with_findings = 0
        total_errors = 0
        total_warnings = 0

        for result in per_rule:
            if result['has_issues']:
                rules_with_findings += 1
            for f in result.get('findings', []):
                finding = {
                    'rule_number': result['rule_number'],
                    'filename': result['filename'],
                    **f,
                }
                all_findings.append(finding)
                if f.get('severity') == 'ERROR':
                    total_errors += 1
                else:
                    total_warnings += 1

        return {
            'metadata': {
                'category': self.category,
                'category_name': self.category_name,
                'generated_at': datetime.now().isoformat(),
                'checker': 'mechanical',
                'rules_reviewed': len(per_rule),
                'rules_with_findings': rules_with_findings,
            },
            'summary': {
                'total_errors': total_errors,
                'total_warnings': total_warnings,
            },
            'findings': all_findings,
            'per_rule': per_rule,
        }

    def _write_markdown_report(self, report: dict):
        """Write human-readable markdown report."""
        meta = report['metadata']
        summary = report['summary']
        total = summary['total_errors'] + summary['total_warnings']
        lines = [
            f"# Mechanical Proofreading Report: {meta['category_name']}",
            "",
            f"Generated: {meta['generated_at'][:10]}",
            f"Checker: mechanical (local, no API)",
            f"Rules reviewed: {meta['rules_reviewed']}",
            f"Rules with findings: {meta['rules_with_findings']}",
            f"Total findings: {total}"
            f" ({summary['total_errors']} errors, {summary['total_warnings']} warnings)",
            "",
        ]

        # Category breakdown
        if report['findings']:
            cat_counts = Counter(f['category'] for f in report['findings'])
            lines.append("## By Category")
            lines.append("")
            lines.append("| Category | Count |")
            lines.append("|----------|-------|")
            for cat, count in cat_counts.most_common():
                lines.append(f"| {cat} | {count} |")
            lines.append("")

        # Summary table
        rules_with_issues = [r for r in report['per_rule'] if r['has_issues']]
        if rules_with_issues:
            lines.append("## Summary by Rule")
            lines.append("")
            lines.append("| Rule | Errors | Warnings |")
            lines.append("|------|--------|----------|")
            for r in rules_with_issues:
                errors = sum(1 for f in r['findings']
                             if f.get('severity') == 'ERROR')
                warnings = sum(1 for f in r['findings']
                               if f.get('severity') == 'WARNING')
                lines.append(
                    f"| Rule {r['rule_number']} | {errors} | {warnings} |"
                )
            lines.append("")

        # Detailed findings
        if report['findings']:
            lines.append("## Findings")
            lines.append("")

            current_rule = None
            for f in report['findings']:
                if f['rule_number'] != current_rule:
                    current_rule = f['rule_number']
                    lines.append(f"### Rule {current_rule}")
                    lines.append("")

                severity = f.get('severity', 'WARNING')
                category = f.get('category', 'unknown')
                lines.append(
                    f"**{severity}** ({category}): {f.get('description', '')}"
                )
                if f.get('quote'):
                    lines.append(f"> {f['quote']}")
                if f.get('suggestion'):
                    lines.append("")
                    lines.append(f"Suggested: {f['suggestion']}")
                lines.append("")
        else:
            lines.append("## No issues found")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(
            "*This report was generated by local mechanical analysis. "
            "No AI was used. All findings should be verified by a human "
            "reviewer.*"
        )
        lines.append("")

        report_path = Path(self.report_dir) / 'mechanical-proofreading-report.md'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text('\n'.join(lines), encoding='utf-8')

        if self.logger:
            self.logger.info(f"Markdown report written to {report_path}")

    def _write_json_report(self, report: dict):
        """Write machine-readable JSON report."""
        json_report = {
            'metadata': report['metadata'],
            'summary': report['summary'],
            'findings': report['findings'],
        }

        report_path = (
            Path(self.report_dir) / 'mechanical-proofreading-report.json'
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(json_report, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )

        if self.logger:
            self.logger.info(f"JSON report written to {report_path}")
