"""Filenames-only machine-path/credential-pattern scan of current tracked text.

This finite pattern scan is evidence about current files, not a secret-free
history certificate or a replacement for independent publication review.
"""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:(?:\\+|/+)(?:[^\s\"<>]|\\\")+|/(?:home|Users)/[^/\s\"]+", re.I)
SECRET = re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")


def main():
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    paths, credentials = [], []
    for name in filter(None, names):
        text = (ROOT / name).read_bytes().decode("utf-8", errors="replace")
        if PATH.search(text):
            paths.append(name)
        if SECRET.search(text):
            credentials.append(name)
    report = {"scope": "current tracked filenames only; no history/all-secret guarantee", "machine_path_matches": paths, "credential_pattern_matches": credentials, "pass": not paths and not credentials}
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
