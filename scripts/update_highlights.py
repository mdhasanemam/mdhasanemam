#!/usr/bin/env python3
"""Refresh the "Match Highlights" table in README.md from the owner's latest public repos.

Runs inside GitHub Actions (see .github/workflows/update-highlights.yml), standard library only.
Edit PINNED / EXCLUDE / MAX_ROWS below to control what shows up.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

OWNER = os.environ.get("OWNER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "mdhasanemam"
TOKEN = os.environ.get("GITHUB_TOKEN")
README = Path(os.environ.get("README_PATH", "README.md"))

MAX_ROWS = 5
PINNED = []    # repo names that always come first, e.g. ["stock-market-analytics-platform"]
EXCLUDE = []   # repo names to hide, e.g. ["some-private-experiment"]
EMOJIS = ["⚽", "🎯", "🏆", "🔵", "🔴", "🥅"]

START = "<!--START_SECTION:highlights-->"
END = "<!--END_SECTION:highlights-->"


def fetch_repos():
    req = urllib.request.Request(
        f"https://api.github.com/users/{OWNER}/repos?per_page=100&sort=pushed",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "readme-highlights-updater",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def pick(repos):
    hidden = {OWNER.lower(), *(n.lower() for n in EXCLUDE)}  # also hides the profile repo itself
    keep = [r for r in repos if not r.get("fork") and not r.get("archived") and r["name"].lower() not in hidden]
    keep.sort(key=lambda r: r["pushed_at"], reverse=True)
    pinned = [next((r for r in keep if r["name"].lower() == p.lower()), None) for p in PINNED]
    pinned = [r for r in pinned if r]
    rest = [r for r in keep if r not in pinned]
    return (pinned + rest)[:MAX_ROWS]


def clean(text, limit=140):
    text = re.sub(r"\s+", " ", (text or "").replace("|", "/")).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render(repos):
    lines = ["| Project | What it does |", "|:--|:--|"]
    for i, r in enumerate(repos):
        desc = clean(r.get("description")) or "No description yet"
        lang = f" · `{r['language']}`" if r.get("language") else ""
        lines.append(f"| {EMOJIS[i % len(EMOJIS)]} [**{r['name']}**]({r['html_url']}) | {desc}{lang} |")
    return "\n".join(lines)


def main():
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        sys.exit(f"Markers {START} / {END} not found in {README}")
    repos = pick(fetch_repos())
    if not repos:
        print("No public repos found; leaving README unchanged.")
        return
    block = f"{START}\n{render(repos)}\n{END}"
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print(f"Updated highlights with {len(repos)} repos.")
    else:
        print("Highlights already up to date.")


if __name__ == "__main__":
    main()
