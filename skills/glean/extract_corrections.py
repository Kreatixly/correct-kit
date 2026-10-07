#!/usr/bin/env python3
"""Find candidate agent corrections in local Claude Code transcripts.

Prints one JSON object per line. A candidate is *not* yet a correction: the
`glean` skill reads the context and decides. This script only narrows ~MBs
of transcript down to the moments worth reading.

Kinds:
  rejection  - the user rejected a tool call
  interrupt  - the user interrupted a running turn
  pushback   - a user message that opens like a correction ("nein", "warum
               hast du", "that's wrong", ...), right after an agent action

Usage:
  python extract_corrections.py --project-dir <repo> [--days 30]
                                [--exclude-session <id>] [--transcripts <dir>]

Standard library only, so it runs wherever Claude Code runs (incl. Windows).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

PUSHBACK = re.compile(
    r"^\s*(nein\b|nee\b|nicht so|falsch|stopp?\b|halt\b|warte\b|"
    r"warum hast du|wieso hast du|hab(e)? (ich )?doch (gesagt|geschrieben)|"
    r"das (war|ist) (so )?(nicht|falsch)|rückgängig|mach das rückgängig|"
    r"lass das|bitte nicht|nicht (das|den|die)\b|"
    r"no\b|nope\b|don'?t\b|wrong\b|why did you|that'?s not|revert\b|undo\b|"
    r"i (said|told you))",
    re.IGNORECASE,
)
REJECTION = "doesn't want to proceed with this tool use"
INTERRUPT = "[Request interrupted by user"
TAG_BLOCK = re.compile(
    r"<(system-reminder|artifact-view-context|task-notification|"
    r"command-[a-z-]+|local-command-[a-z-]+)[^>]*>.*?</\1>",
    re.DOTALL,
)
SECRETS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),            # Google API keys
    re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_\-]{16,}"),   # sk-..., incl. sk-ant-
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),       # GitHub tokens
    re.compile(r"([?&](key|token|access_token|api_key)=)[^&\s\"']+", re.I),
    re.compile(r"\b[A-Za-z0-9+/_\-]{40,}={0,2}"),       # long opaque blobs
]


def redact(text: str) -> str:
    for pattern in SECRETS:
        text = pattern.sub(
            lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]", text
        )
    return text


def slug(path: str) -> str:
    """Claude Code names a project's transcript folder after its path, with
    every character that is not a letter or digit turned into '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def human_text(entry: dict) -> str | None:
    """The text a person typed, or None for tool results and injected context."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return None
    if entry.get("promptSource") == "system" or entry.get("isSidechain"):
        return None
    content = entry.get("message", {}).get("content")
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if c.get("type") == "text"]
        if not parts:
            return None
        content = "\n".join(parts)
    if not isinstance(content, str):
        return None
    text = TAG_BLOCK.sub("", content).strip()
    if not text or text.startswith("Base directory for this skill"):
        return None
    return text


def last_action(entries: list, index: int) -> str:
    """One line on the agent's most recent tool call before entries[index]."""
    for prev in reversed(entries[max(0, index - 40):index]):
        if prev.get("type") != "assistant":
            continue
        for block in reversed(prev.get("message", {}).get("content") or []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                inp = block.get("input") or {}
                target = (inp.get("file_path") or inp.get("command")
                          or inp.get("description") or "")
                target = " ".join(str(target).split())
                return f"{block.get('name')}: {target[:160]}"
    return ""


def scan(path: Path, since: dt.datetime):
    entries = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    last_kind: dict = {}
    for i, entry in enumerate(entries):
        stamp = entry.get("timestamp")
        if not stamp or entry.get("isSidechain"):
            continue
        when = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if when < since:
            continue
        kind, text = None, ""
        content = entry.get("message", {}).get("content")
        if entry.get("type") == "user" and isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result" and REJECTION in str(
                        block.get("content")):
                    kind = "rejection"
                elif block.get("type") == "text" and block.get(
                        "text", "").startswith(INTERRUPT):
                    kind = "interrupt"
        if kind is None:
            typed = human_text(entry)
            if typed and PUSHBACK.search(typed):
                kind, text = "pushback", typed
        if kind is None:
            continue
        # A rejected tool call is followed by an interrupt marker for the same
        # moment: one episode, reported once.
        if kind == "interrupt" and last_kind.get("rejection") == entry.get(
                "promptId"):
            continue
        if kind == "rejection":
            last_kind["rejection"] = entry.get("promptId")
        # The user's next own words usually say what was wrong.
        if not text:
            for nxt in entries[i + 1:i + 30]:
                typed = human_text(nxt)
                if typed and not typed.startswith(INTERRUPT):
                    text = typed
                    break
        yield {
            "session": entry.get("sessionId"),
            "uuid": entry.get("uuid"),
            "time": stamp,
            "branch": entry.get("gitBranch"),
            "kind": kind,
            "agent_action": redact(last_action(entries, i)),
            "user_said": redact(text[:600]),
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=os.getcwd())
    ap.add_argument("--transcripts",
                    help="override the transcript folder (for tests)")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--exclude-session", action="append", default=[])
    args = ap.parse_args()

    folder = Path(args.transcripts) if args.transcripts else (
        Path.home() / ".claude" / "projects"
        / slug(os.path.abspath(args.project_dir)))
    if not folder.is_dir():
        print(f"no transcripts at {folder}", file=sys.stderr)
        return 2

    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    count = 0
    # Top-level files only: sub-agent transcripts live in per-session folders.
    for path in sorted(folder.glob("*.jsonl")):
        if path.stem in args.exclude_session:
            continue
        for candidate in scan(path, since):
            print(json.dumps(candidate, ensure_ascii=False))
            count += 1
    print(f"{count} candidates from {folder}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
