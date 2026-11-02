# Eval Suite Setup Guide

**Status:** Evals configured and runnable; fixture scaffolding issue identified but not yet resolved.

## Current State

**4 test cases** in `evals/`:
- `01-halt-dirty-tree` — verifies agent halts when git tree has uncommitted changes  
- `02-halt-no-env-testing` — verifies agent halts when `.env.testing` missing  
- `03-halt-remote-db` — verifies agent halts when DB host is remote (not localhost)  
- `05-halt-baseline-red` — verifies agent halts when baseline test suite fails

Each case includes:
- `prompt.md` — agent prompt, tool allowlist, model, timeout  
- `files/` — fixture Laravel repo with `.git`, `composer.json`, `phpunit.xml`, `.env.testing`  
- `graders/` — pass/fail criteria:
  - `halt-status` (regex): checks `"status": "halted"` in `docs/upgrade/state.json`  
  - `halt-substep` (regex): checks specific halt phase (0.1, 0.2, etc.)  
  - `no-upgrade-branch` (tool_used): confirms agent does NOT create `upgrade/laravel-*` branches

## Known Issue

**Fixture not populated into eval runtime.**

When the runner scaffolds each case, the fixture `files/` directory is not copied into the agent's working directory. The agent sees an empty `cwd`, so it halts at Phase 0.1 (environment check) for missing `composer.json`, not for the intended fault (dirty tree, missing env file, etc.).

**Observed (trace, kept via `--keep-temp`):** agent cwd `home/cwd` contained only `.claude/`. `git` returned `permission denied`. Agent halted at 0.1 for a missing `composer.json`, not the intended fault.

**Not verified:** why `files/` is not copied. Tried `scaffold_script` as a frontmatter key (rejected: unknown key) and as an executable file in the case dir (no effect with `--scaffold`). Runner's `--scaffold` flag and fixture placement mechanism still unknown for CLI 2.1.312.

**Impact:**
- Evals run but all cases score 0.33 (1 of 3 graders pass: the no-upgrade-branch tool_used check)  
- Halt-status and halt-substep graders fail because `state.json` is never created  

## How to Run Evals (as-is)

```bash
cd "$(dirname "$0")"

# One-pass no-publish run; single-arm (no baseline comparison):
claude plugin eval . \
  --trust-plugin \
  --no-publish \
  --ablation none \
  --runs 1 \
  --allow-tools Read Glob Grep Edit Write \
  'Bash(git:*)' 'Bash(php artisan:*)' 'Bash(composer:*)' 'Bash(vendor/bin/*)' \
  --json evals/results/latest.json

# View HTML report:
open evals/results/2026-10-28T*/report.html
```

**Cost:** ~$0.60 per run. **Duration:** ~45 seconds for 4 cases.

## Fixing the Fixture Issue

### Option A: Scaffold via hook (defer)
If the runner supports a pre-run hook in `.claude-plugin/hooks.js`, the hook can copy `files/` into cwd. Not yet implemented.

### Option B: Scaffold script in case dir
Try creating an **executable** `evals/<case>/scaffold_script` that the runner invokes:
```bash
#!/bin/bash
set -e
cp -a files/. .
```
Test with `--scaffold` flag. The runner mentions this but the exact invocation is unclear.

### Option C: Use `.claude.json` or `settings.json` hook
Pre-eval hook at the project level could copy fixtures. Requires `.claude-plugin/hooks.js` implementation.

### Option D: Manual verification (simplest)
Skip automated evals. Instead, manually verify the skill by:
1. Creating a test Laravel 6–7 app in a separate directory  
2. Running `/laravel-upgrade:laravel-upgrade` from the repo root  
3. Checking that:
   - Clean tree passes, dirty tree halts  
   - Missing `.env.testing` halts  
   - Remote DB halts  
   - Baseline tests passing/failing gates the run  

## Next Steps

1. **Verify** `scaffold_script` mechanism by inspecting the runner's actual code or recent changelog  
2. **Implement** the correct scaffold pattern (likely option B or hook-based)  
3. **Re-run evals** with fixtures populated; expect all graders to pass  
4. **Write `scripts/make_report.py`** (see SKILL.md steps H and final report)  
5. **Test manually** on a real Laravel app in staging before publishing to marketplace

## Files

- `evals/*/prompt.md` — agent invocation and tool allowlist  
- `evals/*/files/` — fixture app state (git repo, config, test files)  
- `evals/*/graders/` — pass/fail criteria  
- `evals/results/` — past run reports and JSON logs  
- `.claude-plugin/plugin.json`, `marketplace.json` — metadata (author/owner still placeholders)

## See Also

- [SKILL.md](skills/laravel-upgrade/SKILL.md) — agent rules and workflow  
- [README.md](README.md) — plugin overview  
- [CHECKLIST-BEFORE-PUBLISH.md](CHECKLIST-BEFORE-PUBLISH.md) — pre-release steps
