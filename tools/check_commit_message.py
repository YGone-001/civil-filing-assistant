#!/usr/bin/env python
# File: tools/check_commit_message.py
# Purpose: Validate Git commit messages against the repository governance rules
#          documented in AGENTS.md section 6.
# Encoding: UTF-8
"""Lightweight commit-message policy validator.

Rules enforced (see AGENTS.md "6. Git 与远端约定"):

1. A commit message must contain exactly one concise single-sentence summary
   line. It must not contain a body, multiple paragraphs, bullet lists,
   implementation reports, detailed test results, or extra trailers.
2. The whole commit message (subject and any body/trailer) must not contain
   development lifecycle or stage identifiers such as ``phase1``, ``Phase 2``,
   ``phase-3``, ``PHASE_4``, ``phasexxx``, ``phaseAlpha``, ``P1``, ``p 1``,
   ``P2-1``, ``stage1`` etc., in any combination of case, whitespace, underscore
   and hyphen. Ordinary words such as ``phases`` and ``staged`` are not markers.

The validator is intentionally dependency free so it can run in a bare CI
checkout. It can validate a literal message, a single revision, or a range of
revisions (for example ``origin/main..HEAD``).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from typing import Iterable, List, Optional

# --- Policy configuration -------------------------------------------------

# Maximum length of a concise commit subject. The example in AGENTS.md is far
# shorter; this bound only rejects obviously non-concise summaries.
MAX_SUBJECT_LENGTH = 100

# Ordinary English words containing the "phase"/"stage" root that are *not*
# lifecycle markers. A keyword elongated with lower-case letters forming one of
# these words is acceptable; any other elongation (e.g. ``phasexxx``) is a
# marker.
_ORDINARY_LIFECYCLE_WORDS = frozenset(
    {
        "phase",
        "phases",
        "phased",
        "phasing",
        "stage",
        "stages",
        "staged",
        "staging",
    }
)

# Finds the "phase"/"stage" keyword at a word boundary (case-insensitive).
_LIFECYCLE_PREFIX = re.compile(r"(?i)\b(?:phase|stage)")


# Milestone markers such as P1, p 1, P2-1, p 2 - 1. A word boundary is
# required before the "p" and a digit must follow (optionally after a single
# separator), which avoids matching ordinary words like "top 3" or "grep 1".
_MILESTONE_MARKER = re.compile(r"(?i)(?<![a-z0-9])p\s*[-_.]?\s*\d")

# Sentence terminators used to detect multi-sentence subjects. A terminator is
# only counted when followed by end-of-string or whitespace, so internal dots
# such as ".gitignore" are not treated as sentence breaks.
_SENTENCE_TERMINATOR = re.compile(r"[.!?\u3002\uff01\uff1f](?:\s|$)")


def _contains_lifecycle_marker(text: str) -> bool:
    """Return True when *text* contains a development lifecycle/stage marker.

    ``phase``/``stage`` is treated as a marker when immediately followed by a
    digit (``phase1``), a separator such as whitespace/underscore/hyphen
    (``Phase 2``, ``phase-3``, ``phase_4``), an uppercase letter
    (``phaseAlpha``), or by further lower-case letters that do not form one of
    the ordinary English words in :data:`_ORDINARY_LIFECYCLE_WORDS`
    (``phasexxx``). Ordinary words such as ``phases`` and ``staged`` are not
    reported.
    """
    for match in _LIFECYCLE_PREFIX.finditer(text):
        rest = text[match.end():]
        if not rest:
            continue  # "phase"/"stage" used alone as an ordinary word
        next_char = rest[0]
        if next_char.isdigit():
            return True  # phase1
        if next_char in " \t-_.":
            return True  # Phase 2 / phase-3 / phase_4
        if next_char.isupper():
            return True  # phaseAlpha
        suffix_match = re.match(r"[a-z]+", rest)
        suffix = suffix_match.group(0) if suffix_match else ""
        if (match.group(0) + suffix).lower() not in _ORDINARY_LIFECYCLE_WORDS:
            return True  # phasexxx
    return False


def find_policy_violations(message: str) -> List[str]:
    """Return a list of human-readable policy violations.

    An empty list means the message satisfies the policy.
    """
    violations: List[str] = []

    if message is None or not message.strip():
        return ["commit message is empty"]

    # Normalise CRLF so line handling is platform independent.
    normalised = message.replace("\r\n", "\n").replace("\r", "\n")

    # A leading/trailing newline is added by ``git log --format=%B``; only
    # internal newlines indicate a body or multi-line message.
    stripped = normalised.strip("\n")
    if "\n" in stripped:
        violations.append(
            "commit message must be a single line (no body, paragraphs, "
            "bullet lists or trailers)"
        )

    subject = stripped.split("\n", 1)[0].strip()

    if not subject:
        violations.append("commit subject line is empty")
        return violations

    if len(subject) > MAX_SUBJECT_LENGTH:
        violations.append(
            f"commit subject is not concise ({len(subject)} > "
            f"{MAX_SUBJECT_LENGTH} characters)"
        )

    if _contains_lifecycle_marker(stripped):
        violations.append(
            "commit message contains a development lifecycle/stage identifier"
        )

    if _MILESTONE_MARKER.search(stripped):
        violations.append(
            "commit message contains a milestone/lifecycle marker (e.g. P1, P2-1)"
        )

    # Reject multiple sentences. A single optional trailing terminator is
    # acceptable; any terminator followed by further text is a sentence break.
    core = subject.rstrip().rstrip(".!?\u3002\uff01\uff1f").rstrip()
    if _SENTENCE_TERMINATOR.search(core):
        violations.append("commit subject must contain a single sentence")

    # Reject bullet-list style subjects.
    if subject.startswith(("-", "*", "\u2022")):
        violations.append("commit subject must not be a bullet list item")

    # De-duplicate while preserving order.
    seen = set()
    ordered: List[str] = []
    for item in violations:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def is_valid(message: str) -> bool:
    """Return ``True`` when *message* satisfies the commit policy."""
    return not find_policy_violations(message)


# --- Git helpers ----------------------------------------------------------


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def read_revision_message(rev: str) -> str:
    """Return the raw commit message (``%B``) for *rev*."""
    return _git("log", "-1", "--format=%B", rev)


def read_range_messages(base: str, head: str = "HEAD") -> List[tuple]:
    """Return ``(sha, subject, body)`` triples for commits in ``base..head``.

    Merge commits are included and validated like any other commit rather than
    being silently skipped with ``--no-merges``; a merge whose subject violates
    the single-sentence or lifecycle rules is therefore still reported.
    """
    output = _git(
        "log",
        "--format=%H%x00%an%x00%B%x1e",
        f"{base}..{head}",
    )
    entries: List[tuple] = []
    for record in output.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, _author, message = record.split("\x00", 2)
        entries.append((sha.strip(), message))
    return entries


# --- CLI ------------------------------------------------------------------


def _report(label: str, ok: bool, violations: Iterable[str]) -> bool:
    if ok:
        print(f"OK   {label}")
        return True
    print(f"FAIL {label}")
    for violation in violations:
        print(f"       - {violation}")
    return False


def main(argv: Optional[List[str]] = None) -> int:
    global MAX_SUBJECT_LENGTH
    parser = argparse.ArgumentParser(
        description="Validate commit messages against AGENTS.md section 6."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--message", "-m", help="literal commit message to check")
    group.add_argument("--file", help="read the commit message from a file")
    group.add_argument("--rev", help="check a single revision (e.g. HEAD)")
    group.add_argument(
        "--range",
        dest="rev_range",
        help="check revisions in a git range (e.g. origin/main..HEAD)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=MAX_SUBJECT_LENGTH,
        help=f"maximum subject length (default: {MAX_SUBJECT_LENGTH})",
    )
    args = parser.parse_args(argv)

    MAX_SUBJECT_LENGTH = args.max_length

    exit_code = 0

    if args.message is not None:
        violations = find_policy_violations(args.message)
        if not _report("literal message", not violations, violations):
            exit_code = 1
    elif args.file is not None:
        with open(args.file, "r", encoding="utf-8") as handle:
            violations = find_policy_violations(handle.read())
        if not _report(args.file, not violations, violations):
            exit_code = 1
    elif args.rev is not None:
        message = read_revision_message(args.rev)
        violations = find_policy_violations(message)
        if not _report(args.rev, not violations, violations):
            exit_code = 1
    elif args.rev_range is not None:
        base, _, head = args.rev_range.partition("..")
        head = head or "HEAD"
        try:
            entries = read_range_messages(base, head)
        except subprocess.CalledProcessError as exc:
            print(
                f"FAIL could not resolve commit range {args.rev_range!r}\n"
                f"       (git log failed with exit code {exc.returncode}); "
                "no commits were validated"
            )
            return 1
        if not entries:
            print(f"OK   no new commits in range {args.rev_range}")
        for sha, message in entries:
            violations = find_policy_violations(message)
            label = f"{sha[:12]} {message.splitlines()[0] if message.strip() else '(empty)'}"
            if not _report(label, not violations, violations):
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
