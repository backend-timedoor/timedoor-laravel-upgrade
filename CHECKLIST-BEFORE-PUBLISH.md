# Pre-publish Checklist: Laravel Upgrade Plugin

Before releasing to marketplace, verify:

## Project structure
- [ ] `LICENSE` — MIT license with copyright year and author name
- [ ] `README.md` — updated with your org/repo links
- [ ] `.claude-plugin/plugin.json` — author name, email, homepage, repository (not placeholder)
- [ ] `.claude-plugin/marketplace.json` — owner name and email (not placeholder)
- [ ] `skills/laravel-upgrade/SKILL.md` — canonical skill definition (root SKILL.md removed)
- [ ] `skills/laravel-upgrade/scripts/make_report.py` — report generator
- [ ] `skills/laravel-upgrade/scripts/test_make_report.py` — self-check script

## Skill validation
- [ ] Run: `python3 skills/laravel-upgrade/scripts/test_make_report.py` — should print `make_report self-check: ok`
- [ ] SKILL.md has no conflicting rules (migrate:fresh guarded by DB test check)
- [ ] All safety guarantees documented in "Safety & Guardrails" section

## Test fixture
- [ ] Create a sample Laravel 6 project under `fixtures/laravel6-sample/` (optional; provides real e2e test)
- [ ] If included: document in README how to run `fixtures/SETUP.md`

## Documentation completeness
- [ ] README covers: what it does, install, use, requirements, before publishing
- [ ] Skill frontmatter matches README title/description
- [ ] All references to version numbers, PHP versions, and Laravel versions are current (6 → 13, PHP → 8.4)

## Tool allowlists
- [ ] Run `claude --help` and verify the scoped entries under `ALLOWED_TOOLS` in SKILL.md are supported by the installed Claude Code version.
- [ ] Confirm the allowlist does not grant broad `php artisan`, `git checkout`, PHP installation/switching, remote Git, or destructive command access.

## Final validation
- [ ] No `TODO`, `FIXME`, `YOUR NAME`, or `YOUR_ORG` left in code (except placeholders explicitly marked in comments)
- [ ] No hardcoded paths or absolute paths in scripts
- [ ] No credentials, API keys, or `.env` values in repository
- [ ] LICENSE file states your name and organization

## Marketplace publishing
- [ ] Version in `plugin.json` incremented (if republishing)
- [ ] All tests in fixture pass (if included)
- [ ] Marketplace category correct: `migration`
- [ ] Run locally first: `/plugin marketplace add /path/to/laravel-upgrade && /plugin install laravel-upgrade`

## Known limitations to document
- Requires PHPUnit or Pest test suite (no skipping if tests absent)
- Requires `.env.testing` with SQLite `:memory:` or test DB name
- No push/merge to main (user responsibility)
- Runs locally only; no cloud/CI integration
