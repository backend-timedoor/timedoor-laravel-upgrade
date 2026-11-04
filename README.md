# laravel-upgrade

Claude Code plugin. Incremental Laravel 6 → 13 upgrade, PHP → 8.4, with test gates and a generated change report.

## Install

```text
/plugin marketplace add https://github.com/backend-timedoor/timedoor-laravel-upgrade
/plugin install laravel-upgrade@timedoor-laravel-upgrade
```

Local testing:

```text
/plugin marketplace add /path/to/laravel-upgrade
/plugin install laravel-upgrade@timedoor-laravel-upgrade
```

## Use

In the Laravel project (git repo, clean tree, `.env.testing` pointing at a test DB):

```text
/laravel-upgrade:laravel-upgrade
```

Output: `docs/upgrade/` (per-version docs, `state.json`, `command-log.jsonl`, `REPORT.md`) and `upgrade/baseline` plus one `upgrade/laravel-N` branch per upgrade that runs. A baseline already on Laravel N skips N and creates no branch.

## Requirements

- git, PHP CLI, Composer
- PHPUnit/Pest test suite
- `.env.testing` and `phpunit.xml` both present and configured:
  - `APP_ENV=testing`
  - DB either SQLite `:memory:` **or** MySQL/PostgreSQL with DB name ending in `_test` (e.g., `app_test`)
  - DB host must be `127.0.0.1`, `localhost`, or a Docker service (not remote)
  - Example `.env.testing`:
    ```
    APP_ENV=testing
    DB_CONNECTION=mysql
    DB_HOST=127.0.0.1
    DB_DATABASE=app_test
    DB_USERNAME=root
    DB_PASSWORD=root
    ```

## Safety

- No push, no remote changes, no merge to main.
- Test DB guard before any migrate/test, including a preflight scan that halts SQLite `:memory:` when migrations contain MySQL-only SQL (`AUTO_INCREMENT`, `ALTER TABLE ... CHANGE COLUMN`, etc.). No automatic migration rewrite.
- Never changes business logic automatically.
- Collects all incompatible packages in one preflight report, classifies risk, then halts for a per-package decision.
- Supports `fork`, `rebuild`, `migrate`, `skip`, `replace`, `skip_until`, or `replace_until`; records each decision in `state.json`.
- Halts on unexpected route changes and test regressions after 2 retries.

## Before publishing

- Run on a sample Laravel 6 project end-to-end before release.

## Layout

```
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
skills/laravel-upgrade/SKILL.md
skills/laravel-upgrade/scripts/make_report.py
skills/laravel-upgrade/scripts/test_make_report.py
```
