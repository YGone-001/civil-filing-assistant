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


def test_trailing_period_is_single_sentence():
    assert ccm.is_valid("fix: keep a single trailing period.")


def test_empty_message_reason():
    violations = ccm.find_policy_violations("")
    assert violations == ["commit message is empty"]


def test_cli_accepts_valid_message():
    assert ccm.main(["-m", "fix: stabilize civil filing workflows"]) == 0


def test_cli_rejects_invalid_message():
    assert ccm.main(["-m", "phase1: nope"]) == 1
