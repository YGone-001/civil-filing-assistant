# File: models/validation.py
# Purpose: Pure input-validation foundation (full-date parsing and structured
#          validation results). No Qt imports.
# Encoding: UTF-8
"""Shared validation contract for user input.

This module is the single authority for full-date parsing and for the small
structured :class:`ValidationResult` consumed by the wizard pages and case
models. It never raises for malformed input and never substitutes a fabricated
date (such as "today") for a malformed one; callers decide how each explicit
status is presented. Labor month-range parsing has its own semantics and stays
in :mod:`models.calculations` — see ``parse_month_range``.
"""

import datetime
import re
from dataclasses import dataclass


class DateStatus:
    """Explicit outcomes of full-date parsing (suggested semantic names)."""

    EMPTY = "EMPTY"
    VALID = "VALID"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_CALENDAR_DATE = "INVALID_CALENDAR_DATE"
    OUT_OF_SUPPORTED_RANGE = "OUT_OF_SUPPORTED_RANGE"
    REVERSED_INTERVAL = "REVERSED_INTERVAL"


# Full dates outside this range are rejected as out of range instead of
# producing multi-century intervals. Month-range (labor) parsing keeps its own
# 1900-2100 bound, consistent with this choice.
SUPPORTED_YEAR_RANGE = (1900, 2100)

# Accepted full-date grammar (full-input match): exactly three numeric
# components (year, month, day) joined by one consistent separator. ISO-like,
# slash- and dot-separated, and Chinese forms are supported; anything else —
# additional numeric components, mixed separators, textual prefixes or
# suffixes — is INVALID_FORMAT. Components are never inferred or truncated.
_FULL_DATE_FORMS = (
    re.compile(r"\d{4}-\d{1,2}-\d{1,2}"),
    re.compile(r"\d{4}/\d{1,2}/\d{1,2}"),
    re.compile(r"\d{4}\.\d{1,2}\.\d{1,2}"),
    re.compile(r"\d{4}年\d{1,2}月\d{1,2}日?"),
)


@dataclass(frozen=True)
class DateValidation:
    """Outcome of parsing one full-date input."""

    status: str
    value: datetime.date | None = None


def parse_full_date(text):
    """Parse a full calendar date without ever raising.

    The whole input must match one of the accepted date forms above (after
    stripping surrounding whitespace); a fourth component, an unexplained
    textual prefix or suffix, or mixed separators make the input
    ``INVALID_FORMAT`` rather than being silently ignored. Missing components
    are never inferred, and an invalid date is never replaced by another date.

    Returns a :class:`DateValidation` with one of: ``EMPTY`` (blank input),
    ``INVALID_FORMAT``, ``INVALID_CALENDAR_DATE`` (e.g. February 30),
    ``OUT_OF_SUPPORTED_RANGE`` (year outside ``SUPPORTED_YEAR_RANGE``) or
    ``VALID`` (with ``value`` set).
    """
    raw = "" if text is None else str(text).strip()
    if not raw:
        return DateValidation(DateStatus.EMPTY)

    if not any(pattern.fullmatch(raw) for pattern in _FULL_DATE_FORMS):
        return DateValidation(DateStatus.INVALID_FORMAT)

    year, month, day = (int(part) for part in re.findall(r"\d+", raw))

    low, high = SUPPORTED_YEAR_RANGE
    if not low <= year <= high:
        return DateValidation(DateStatus.OUT_OF_SUPPORTED_RANGE)

    try:
        value = datetime.date(year, month, day)
    except ValueError:
        return DateValidation(DateStatus.INVALID_CALENDAR_DATE)

    return DateValidation(DateStatus.VALID, value)


class ValidationStatus:
    """Status vocabulary for :class:`ValidationResult`."""

    VALID = "VALID"
    EMPTY_ALLOWED = "EMPTY_ALLOWED"
    REQUIRED_MISSING = "REQUIRED_MISSING"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_RANGE = "INVALID_RANGE"
    INCONSISTENT = "INCONSISTENT"


@dataclass(frozen=True)
class ValidationResult:
    """One structured, user-facing validation outcome.

    ``field`` identifies the input (UI registration key or model attribute),
    ``status`` comes from :class:`ValidationStatus`, ``code`` is a stable
    machine-readable reason and ``message`` is optional user-facing text that
    must never assert an unverified legal rule.
    """

    field: str
    status: str
    code: str = ""
    message: str = ""

    @property
    def is_valid(self):
        """Missing-but-allowed input is not an error."""
        return self.status in (ValidationStatus.VALID, ValidationStatus.EMPTY_ALLOWED)
