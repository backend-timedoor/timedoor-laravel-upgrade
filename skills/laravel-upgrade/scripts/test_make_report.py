#!/usr/bin/env python3
"""Self-check for make_report.py. Run: python3 scripts/test_make_report.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import make_report as mr  # noqa: E402

# Test prev_branch with skipped majors in an isolated state directory.
import json
import os
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    state_dir = Path(tmp) / "docs" / "upgrade"
    state_dir.mkdir(parents=True)
    (state_dir / "state.json").write_text(json.dumps({
        "versions": {
            "7": {"status": "skipped", "branch": None},
            "8": {"status": "passed", "branch": "upgrade/laravel-8"},
            "12": {"status": "passed", "branch": "upgrade/laravel-12"},
        }
    }))
    previous_cwd = os.getcwd()
    try:
        os.chdir(tmp)
        assert mr.prev_branch(8) == "upgrade/baseline"
        assert mr.prev_branch(13) == "upgrade/laravel-12"
    finally:
        os.chdir(previous_cwd)

# First run appends a generated block; second run replaces it, not duplicates it.
once = mr.replace_generated("# Doc\n", "body1")
twice = mr.replace_generated(once, "body2")
assert twice.count(mr.BEGIN) == 1 and "body2" in twice and "body1" not in twice

# Text outside the generated block is preserved.
custom = f"# Doc\n\nnotes\n\n{mr.BEGIN}\nold\n{mr.END}\n\nmore\n"
out = mr.replace_generated(custom, "new")
assert "notes" in out and "more" in out and "old" not in out

print("make_report self-check: ok")
