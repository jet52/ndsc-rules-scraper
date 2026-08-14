# TODO

## Known-404 allowlist for index-listed reserved rules (2026-08-14)

Every weekly `build_git_history.py --update --all` run exits 1 because five
index-listed pages return HTTP 404:

- `ndrappp/15`, `ndrappp/22`, `ndrappp/33`, `ndrappp/46`
- `ndrct/2-1`

These are reserved/never-served rule numbers — none has ever been in the
mirror or in ndlaw-mcp's rules.db, and the 404s are stable (verified live
2026-08-14). The per-category `stats['errors']` roll into `has_errors →
sys.exit(1)` (build_git_history.py:117), so the weekly pipeline's
`[rules-scrape] exited 1` alarm fires on a permanent condition and a REAL
scrape failure would be indistinguishable in the exit code.

Fix shape: a known-404 allowlist (config.yaml, keyed by category/slug).
An allowlisted 404 logs at INFO and does not set `has_errors`; a 404 NOT
on the list still errors — that is the signal worth alarming on (a rule
page vanishing is exactly what the scraper exists to notice). Seed the
list with the five above. Consider also emitting a distinct exit code or
summary line for "new 404" so weekly_scrape.sh can notify specifically.

Related, lower priority: the `Sentinel date 01/01/0001 — skipping version`
warnings on appendix-style pages with no effective-date header are benign
(the pages genuinely carry no date) but noisy — a `dateless-ok` flag on
those slugs would quiet ~30 warning lines per run. ndlaw-mcp's
effective-date probe already treats page-and-DB-both-dateless as
agreement; this is the scraper-side twin of that rule.
