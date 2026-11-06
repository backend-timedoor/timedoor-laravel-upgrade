#!/usr/bin/env python3
"""Generate upgrade docs from git history, state.json and command log.

Usage:
  python3 scripts/make_report.py --version N     # fill change tables in docs/upgrade/N-laravel-N.md
  python3 scripts/make_report.py --final         # write docs/upgrade/REPORT.md

Stdlib only. Reads: docs/upgrade/state.json, docs/upgrade/command-log.jsonl, git.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

UP = Path("docs/upgrade")
STATE = UP / "state.json"
LOG = UP / "command-log.jsonl"
BEGIN, END = "<!-- generated:begin -->", "<!-- generated:end -->"


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def get_php_binary():
    """PHP binary for artisan calls: $PHP_BINARY, else state.php_binary, else 'php'."""
    if os.environ.get("PHP_BINARY"):
        return os.environ["PHP_BINARY"]
    if STATE.exists():
        return load_state().get("php_binary", "php")
    return "php"


def load_state():
    return json.loads(STATE.read_text())


def commits_for_branch(branch, base):
    """Commits on branch not on base, with changed files."""
    if not base:
        return []
    out = git("log", f"{base}..{branch}", "--name-status", "--format=%x1e%h%x1f%s")
    commits = []
    for block in out.split("\x1e"):
        block = block.strip()
        if not block:
            continue
        head, *files = block.splitlines()
        sha, subject = head.split("\x1f")
        commits.append({"sha": sha, "subject": subject, "files": files})
    return commits


def command_stats():
    if not LOG.exists():
        return {"total": 0, "failed": 0, "failures": []}
    rows = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    failed = [r for r in rows if r.get("exit_code", 0) != 0]
    return {"total": len(rows), "failed": len(failed), "failures": failed[:20]}


def version_table(state, versions):
    lines = ["| Version | Status | Branch | Commits | Files changed | Retries | Doc |",
             "|---|---|---|---|---|---|---|"]
    for v in versions:
        info = state["versions"].get(str(v), {})
        branch = info.get("branch", "")
        commits = commits_for_branch(branch, prev_branch(v)) if branch else []
        files = {f.split("\t")[-1] for c in commits for f in c["files"]}
        lines.append(f"| {v} | {info.get('status','pending')} | `{branch}` | {len(commits)} | "
                     f"{len(files)} | {info.get('retries',0)} | {info.get('doc','')} |")
    return "\n".join(lines)


def prev_branch(v):
    """Find the previous non-skipped major, or upgrade/baseline for first run."""
    state = load_state()
    for prev_v in range(v - 1, 6, -1):
        prev_info = state["versions"].get(str(prev_v), {})
        if prev_info.get("branch"):  # non-skipped
            return prev_info["branch"]
    return "upgrade/baseline"


def version_changes(v):
    state = load_state()
    branch = state["versions"].get(str(v), {}).get("branch", f"upgrade/laravel-{v}")
    commits = commits_for_branch(branch, prev_branch(v))
    if not commits:
        return "_No commits on this branch._"
    rows = ["| Commit | Subject | Files |", "|---|---|---|"]
    for c in commits:
        files = "<br>".join(f.split("\t")[-1] for f in c["files"]) or "-"
        rows.append(f"| `{c['sha']}` | {c['subject']} | {files} |")
    return "\n".join(rows)


def package_diff():
    base = UP / "baseline" / "packages.json"
    if not base.exists():
        return "_No baseline packages snapshot._"
    before = {p["name"]: p["version"] for p in json.loads(base.read_text()).get("installed", [])}
    r = subprocess.run(["composer", "show", "--format=json"], capture_output=True, text=True)
    if r.returncode != 0:
        return f"_composer show failed: {r.stderr.strip()[:200]}_"
    after = {p["name"]: p["version"] for p in json.loads(r.stdout).get("installed", [])}
    rows = ["| Package | Before | After |", "|---|---|---|"]
    for name in sorted(set(before) | set(after)):
        if before.get(name) != after.get(name):
            rows.append(f"| {name} | {before.get(name,'-')} | {after.get(name,'-')} |")
    return "\n".join(rows) if len(rows) > 2 else "_No package version changes._"


def route_diff():
    base = UP / "baseline" / "routes.json"
    if not base.exists():
        return "_No baseline routes snapshot._"
    r = subprocess.run(
        [get_php_binary(), "artisan", "route:list", "--json"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return f"_route:list failed: {r.stderr.strip()[:200]}_"
    key = lambda x: f"{x.get('method','')} {x.get('uri','')}"
    before = {key(x) for x in json.loads(base.read_text())}
    after = {key(x) for x in json.loads(r.stdout)}
    added, removed = sorted(after - before), sorted(before - after)
    return (f"Added: {len(added)}, Removed: {len(removed)}\n\n"
            + ("Removed routes:\n" + "\n".join(f"- {x}" for x in removed) if removed else "No routes removed."))


def test_coverage(state):
    """Return the recorded test coverage category without claiming unmeasured coverage."""
    explicit = state.get("test_coverage")
    if explicit in {"low", "partial", "full"}:
        return explicit

    count = state.get("test_count", state.get("baseline_test_count"))
    if isinstance(count, int):
        return "low" if count < 10 else "partial"

    return "low"


def verification_status(state):
    return {
        "technical_upgrade": "passed" if state.get("status") == "done" else "failed",
        "test_coverage": test_coverage(state),
        "functional_verification": "required",
        "production_ready": "no",
    }


def replace_generated(text, body):
    block = f"{BEGIN}\n{body}\n{END}"
    if BEGIN in text and END in text:
        pre, rest = text.split(BEGIN, 1)
        _, post = rest.split(END, 1)
        return pre + block + post
    return text.rstrip() + "\n\n" + block + "\n"


def decision_row(package):
    options = ["fork", "rebuild", "skip"]
    if package.get("migration_pending"):
        options.append("migrate")
    if package.get("replaced_by"):
        options.append("replace")
    if package.get("abandoned") and package.get("replaced_by"):
        options = [option for option in options if option not in {"fork", "rebuild"}]
    if package.get("abandoned") and package.get("replaced_by"):
        suggested = "replace"
    elif package.get("migration_pending"):
        suggested = "migrate"
    elif package.get("risk") == "high":
        suggested = "fork"
    else:
        suggested = "skip"
    problem = "Abandoned; replacement available" if package.get("abandoned") and package.get("replaced_by") else "No release for target Laravel version"
    files_touched = package.get("files_touched", [])
    count = len(files_touched) if isinstance(files_touched, list) else files_touched
    evidence = f"{count} files touched ({package.get('risk', 'unknown')} risk)."
    if package.get("migration_pending"):
        evidence += " Migration pending."
    return package.get("name", "unknown"), problem, evidence, ", ".join(options), suggested


def decision_output(state):
    halt = state.get("halt") or {}
    status = state.get("status", "unknown")
    version = halt.get("version")
    substep = halt.get("substep")
    version_line = "before upgrade loop" if version is None else f"Laravel {version} → PHP {state.get('php_current', 'unknown')} (substep {substep})"
    lines = [f"Status: {status}", f"Reason: {halt.get('reason', 'Upgrade completed.')}", version_line]
    packages = state.get("incompatible_packages", [])
    if packages:
        resolved = state.get("resolved_packages", [])
        if resolved:
            lines += ["", "Auto-resolved packages: " + ", ".join(package.get("name", "unknown") for package in resolved)]
        lines += ["", "Packages needing a decision:", "", "| Package | Problem | Evidence | Options | Suggested |", "|---|---|---|---|---|"]
        lines += ["| " + " | ".join(decision_row(package)) + " |" for package in packages]
        lines += ["", "To resume:"]
        lines += [f"{package.get('name', 'unknown')} → [your choice: {decision_row(package)[3].replace(', ', ' | ')}]" for package in packages]
    else:
        lines += ["", f"Next: {halt.get('next', 'Review docs/upgrade/REPORT.md.')}"]
    return "\n".join(lines) + "\n"


def run_version(v):
    doc = UP / f"{v}-laravel-{v}.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    text = doc.read_text() if doc.exists() else f"# Upgrade to Laravel {v}\n"
    body = f"### Commits and files\n{version_changes(v)}\n\n### Packages\n{package_diff()}\n\n### Routes\n{route_diff()}"
    doc.write_text(replace_generated(text, body))
    print(f"wrote {doc}")


def run_final():
    state = load_state()
    versions = sorted(int(k) for k in state["versions"])
    status = state.get("status", "unknown")
    halt = state.get("halt")
    stats = command_stats()
    manual = []
    for v in versions:
        d = UP / f"{v}-laravel-{v}.md"
        if d.exists() and "## Manual review" in d.read_text():
            section = d.read_text().split("## Manual review", 1)[1].split("\n## ", 1)[0].strip()
            if section and section.lower() not in ("none", "<agent: file:line — reason; or \"none\">"):
                manual.append(f"**Laravel {v}:**\n{section}")
    parts = [
        "# Laravel Upgrade Report: 6 → 13, PHP → 8.4",
        f"\n**Status:** {status}",
        f"\n**Halt:** {json.dumps(halt, indent=2)}" if halt else "",
        "\n## Versions\n" + version_table(state, versions),
        "\n## Package changes (baseline vs final)\n" + package_diff(),
        "\n## Route diff vs baseline\n" + route_diff(),
        "\n## Manual review\n" + ("\n\n".join(manual) if manual else "_None recorded._"),
        f"\n## Command log\nTotal: {stats['total']}, failed: {stats['failed']}",
        "\n## Verification status\n" + "\n".join(
            f"- **{name}:** {value}"
            for name, value in verification_status(state).items()
        ),
    ]
    if stats["failures"]:
        parts.append("\n### Failed commands\n" + "\n".join(
            f"- `{f.get('command')}` exit {f.get('exit_code')}" for f in stats["failures"]))
    parts.append("\n## Rollback\nCreate a new branch from `upgrade/baseline`. Do not reset or force-push existing branches.")
    (UP / "REPORT.md").write_text("\n".join(p for p in parts if p) + "\n")
    decision = decision_output(state)
    (UP / "DECISION.md").write_text(decision)
    print(decision, end="")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", type=int)
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    if a.final:
        run_final()
    elif a.version:
        run_version(a.version)
    else:
        ap.error("pass --version N or --final")


if __name__ == "__main__":
    main()
