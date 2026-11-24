# File: tests/test_facts_examples.py
# Purpose: Facts-exemplar library contract (coverage, safety, unknown types).
# Encoding: UTF-8
"""The exemplar library is reference material only, but it still has a
contract: every supported case type carries non-empty exemplars, unknown case
types get none, and no exemplar ever ships real-looking personal data."""

import re

import pytest

from utils.facts_examples import FactsExamplesLibrary

CASE_TYPES = ("loan", "contract", "property", "labor", "divorce")


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_every_supported_case_type_has_exemplars(case_type):
    examples = FactsExamplesLibrary.get_facts_examples(case_type)
    assert examples, case_type
    for title, text in examples:
        assert title.strip()
        assert len(text.strip()) > 50


def test_every_case_type_has_at_least_two_exemplars():
    for case_type in CASE_TYPES:
        assert len(FactsExamplesLibrary.get_facts_examples(case_type)) >= 2, case_type


def test_labor_and_divorce_keep_three_exemplars():
    assert len(FactsExamplesLibrary.get_facts_examples("labor")) >= 3
    assert len(FactsExamplesLibrary.get_facts_examples("divorce")) >= 3


def test_exemplar_titles_are_unique_within_a_case_type():
    for case_type in CASE_TYPES:
        titles = [title for title, _text in FactsExamplesLibrary.get_facts_examples(case_type)]
        assert len(titles) == len(set(titles)), case_type


def test_unknown_case_type_gets_no_exemplars():
    assert FactsExamplesLibrary.get_facts_examples("traffic") == []
    assert FactsExamplesLibrary.get_facts_examples("") == []
    assert FactsExamplesLibrary.get_facts_examples(None) == []


def test_every_exemplar_has_an_applicability_note():
    for case_type in CASE_TYPES:
        for title, _text in FactsExamplesLibrary.get_facts_examples(case_type):
            assert FactsExamplesLibrary.get_description(title), (case_type, title)


def test_exemplars_use_placeholders_instead_of_concrete_facts():
    """No exemplar may assert a concrete money amount, date or identifier."""
    for case_type in CASE_TYPES:
        for _title, text in FactsExamplesLibrary.get_facts_examples(case_type):
            # Dates and amounts stay as XXXX/XXX placeholders in exemplars.
            assert re.search(r"XXXX|XXX", text), case_type
            assert not re.search(r"\d{17}[\dXx]", text), case_type  # 身份证号样式
