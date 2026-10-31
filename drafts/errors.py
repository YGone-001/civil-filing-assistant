# File: drafts/errors.py
# Purpose: Shared exception hierarchy for the local draft feature.
# Encoding: UTF-8
"""Draft failure vocabulary.

Every exception message in this package is written so it can be shown to the
user verbatim: it names the failing *layer* or a registry field identifier, but
it never embeds party names, identity numbers, addresses, free-text case facts
or raw payload bytes. Callers may therefore surface ``str(exc)`` without a
redaction step, and routine logs must still avoid payload content.
"""


class DraftError(Exception):
    """Base class for every draft failure that is safe to explain to the user."""


class DraftValidationError(DraftError, ValueError):
    """The payload is not a structurally valid draft document."""


class DraftStorageError(DraftError):
    """A draft file could not be written or read."""


class DraftFileTooLargeError(DraftStorageError):
    """A draft file (or the payload inside it) exceeds the supported size."""


class DraftFormatError(DraftStorageError):
    """The encrypted envelope is truncated, malformed or of an unknown version."""


class ProtectionError(DraftError):
    """Base class for Windows data-protection failures."""


class ProtectionUnavailable(ProtectionError):
    """The platform or the Windows user profile cannot protect data here."""


class ProtectionFailed(ProtectionError):
    """DPAPI refused the operation (corrupt payload, wrong user, or failure)."""
