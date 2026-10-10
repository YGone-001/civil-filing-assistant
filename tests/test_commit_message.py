# File: tests/test_commit_message.py
# Purpose: Regression tests for the commit-message policy validator.
# Encoding: UTF-8

import pytest

from tools import check_commit_message as ccm


VALID_MESSAGES = [
    "fix: stabilize civil filing workflows and document export",
    "fix: do a thing.",
    "docs: update readme for offline privacy wording",
    "test: add regression coverage for labor month parsing",
]

# Lifecycle / stage markers that must be rejected (case/space/underscore/hyphen).
INVALID_LIFECYCLE = [
    "phase1: start implementation",
    "Phase 2 fixes",
    "phase-3 cleanup",
    "PHASE_4 release",
    "stage1 patch",
    "Stage 2 work",
    "stage-3 correction",
    "STAGE_4 done",
    "fix: run phase2 regression",
    "fix: stage 2 cleanup",
]

# Milestone markers such as P1, p 1, P2-1, p 2 - 1.
INVALID_MILESTONE = [
    "P1 patch",
    "p 1 update",
    "P2-1 fix",
    "p 2 - 1 work",
    "fix: address P1 feedback",
]

# Elongated lifecycle keyword variants explicitly named in AGENTS.md section 6
# (e.g. "phasexxx", "phaseAlpha") and other non-ordinary suffixes.
INVALID_ELONGATIONS = [
    "phasexxx: start implementation",
    "phaseAlpha tweak",
    "PhaseXxx work",
    "stagexyz cleanup",
    "phasewhatever update",
    "phasE2 patch",
]

# Ordinary English words containing the phase/stage root that are NOT markers.
ORDINARY_WORDS = [
    "fix: staged rollout for exports",
    "docs: describe the phases of the wizard",
    "feat: keep deprecation phasing graceful",
    "refactor: staging directory cleanup",
    "fix: phased migration of the wizard",
]

INVALID_STRUCTURE = [
    "",
    "   ",
    "subject line\n\nbody paragraph",
    "first sentence. second sentence",
    "- bullet style subject",
    "* another bullet",
    "fix: one\nfix: two",
]


@pytest.mark.parametrize("message", VALID_MESSAGES)
def test_valid_messages_accepted(message):
    assert ccm.is_valid(message), ccm.find_policy_violations(message)


@pytest.mark.parametrize("message", INVALID_LIFECYCLE + INVALID_MILESTONE)
def test_lifecycle_and_milestone_markers_rejected(message):
    assert not ccm.is_valid(message), f"should reject: {message!r}"


@pytest.mark.parametrize("message", INVALID_ELONGATIONS)
def test_elongated_lifecycle_variants_rejected(message):
    assert not ccm.is_valid(message), f"should reject: {message!r}"


@pytest.mark.parametrize("message", ORDINARY_WORDS)
def test_ordinary_phase_stage_words_accepted(message):
    assert ccm.is_valid(message), ccm.find_policy_violations(message)


@pytest.mark.parametrize("message", INVALID_STRUCTURE)
def test_non_conforming_structure_rejected(message):
    assert not ccm.is_valid(message), f"should reject: {message!r}"


def test_case_insensitive_detection():
    assert not ccm.is_valid("PHASE1 work")
    assert not ccm.is_valid("Phase-2 work")
    assert not ccm.is_valid("StAgE_3 work")


def test_ordinary_words_not_flagged():
    # "staged" and "phases" are ordinary words, not lifecycle markers.
    assert ccm.is_valid("fix: staged rollout for exports")
    assert ccm.is_valid("docs: describe the phases of the wizard")


def test_numeric_lifecycle_marker_with_separators_rejected():
    for message in ("phase 2", "phase-3", "phase_4", "stage 1", "stage-2"):
        assert not ccm.is_valid(f"fix: {message} cleanup"), message


def test_trailing_period_is_single_sentence():
    assert ccm.is_valid("fix: keep a single trailing period.")


def test_empty_message_reason():
    violations = ccm.find_policy_violations("")
    assert violations == ["commit message is empty"]


def test_cli_accepts_valid_message():
    assert ccm.main(["-m", "fix: stabilize civil filing workflows"]) == 0


def test_cli_rejects_invalid_message():
    assert ccm.main(["-m", "phase1: nope"]) == 1


def _git_in(cwd, *args):
    import subprocess

    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(tmp_path):
    _git_in(tmp_path, "init", "-q")
    _git_in(tmp_path, "config", "user.email", "test@example.com")
    _git_in(tmp_path, "config", "user.name", "Test")


def test_range_validation_checks_new_commits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_repo(tmp_path)

    (tmp_path / "f.txt").write_text("1", encoding="utf-8")
    _git_in(tmp_path, "add", "f.txt")
    _git_in(tmp_path, "commit", "-q", "-m", "fix: valid first commit")
    first = _git_in(tmp_path, "rev-parse", "HEAD").stdout.strip()

    (tmp_path / "f.txt").write_text("2", encoding="utf-8")
    _git_in(tmp_path, "commit", "-q", "-am", "phasexxx: invalid lifecycle marker")
    second = _git_in(tmp_path, "rev-parse", "HEAD").stdout.strip()
    assert second != first

    # The invalid commit in the range must fail validation.
    assert ccm.main(["--range", f"{first}..{second}"]) == 1
    # An empty range (no new commits) passes.
    assert ccm.main(["--range", f"{first}..{first}"]) == 0


def test_range_validation_includes_merge_commit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_repo(tmp_path)

    base_file = tmp_path / "f.txt"
    base_file.write_text("1", encoding="utf-8")
    _git_in(tmp_path, "add", "f.txt")
    _git_in(tmp_path, "commit", "-q", "-m", "fix: base commit")
    base = _git_in(tmp_path, "rev-parse", "HEAD").stdout.strip()

    # A side branch with a lifecycle-marked commit, then merge it back.
    _git_in(tmp_path, "checkout", "-q", "-b", "side")
    (tmp_path / "side.txt").write_text("s", encoding="utf-8")
    _git_in(tmp_path, "add", "side.txt")
    _git_in(tmp_path, "commit", "-q", "-m", "phase_2: bad side commit")
    side_head = _git_in(tmp_path, "rev-parse", "HEAD").stdout.strip()

    _git_in(tmp_path, "checkout", "-q", "-")
    _git_in(tmp_path, "merge", "--no-ff", "-q", "-m", "merge side branch", side_head)

    # Even though --no-merges is NOT used, the range must surface the bad commit.
    assert ccm.main(["--range", f"{base}..HEAD"]) == 1


def test_range_unresolvable_returns_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_repo(tmp_path)
    assert ccm.main(["--range", "does-not-exist..HEAD"]) == 1
