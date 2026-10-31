# File: drafts/__init__.py
# Purpose: Public surface of the local encrypted draft feature.
# Encoding: UTF-8
"""Secure local case drafts.

Layering (each layer only talks to the one below it)::

    Wizard / UI              views.draft_io, presenters.draft_presenter
        |
    Validated snapshot       drafts.schema          (no Qt, strict validation)
        |
    Encrypted storage        drafts.storage         (envelope, atomic write)
        |
    Windows DPAPI            drafts.windows_protection (current-user scope)

Nothing in this package imports PySide6, reads a widget or knows about the
export pipeline; conversely the UI layer never touches ciphertext.

The two convenience helpers below compose the layers for callers that want a
one-line save/load:

    document = validate_document(capture_draft(wizard, page_name))
    save_draft(path, document)          # encrypts, then writes atomically
    document = load_draft(path)         # reads, decrypts, validates
"""

from drafts.errors import (
    DraftError,
    DraftFileTooLargeError,
    DraftFormatError,
    DraftStorageError,
    DraftValidationError,
    ProtectionError,
    ProtectionFailed,
    ProtectionUnavailable,
)
from drafts.schema import (
    CASE_TYPES,
    SCHEMA_VERSION,
    DraftDocument,
    from_json_bytes,
    to_json_bytes,
    validate_document,
)
from drafts.storage import load_draft_file, save_draft_file

#: Extension used by the save/open dialogs and the ignore rules.
DRAFT_EXTENSION = ".cfdraft"

#: Human-readable filter for ``QFileDialog`` (kept next to the extension).
DRAFT_FILE_FILTER = f"草稿文件 (*{DRAFT_EXTENSION});;所有文件 (*)"


def save_draft(path, document, protector=None):
    """Validate-and-write *document* to *path* as an encrypted draft."""
    save_draft_file(path, to_json_bytes(document), protector=protector)


def load_draft(path, protector=None):
    """Read, decrypt and validate the draft at *path*."""
    return from_json_bytes(load_draft_file(path, protector=protector))


__all__ = [
    "CASE_TYPES",
    "DRAFT_EXTENSION",
    "DRAFT_FILE_FILTER",
    "DraftDocument",
    "DraftError",
    "DraftFileTooLargeError",
    "DraftFormatError",
    "DraftStorageError",
    "DraftValidationError",
    "ProtectionError",
    "ProtectionFailed",
    "ProtectionUnavailable",
    "SCHEMA_VERSION",
    "from_json_bytes",
    "load_draft",
    "load_draft_file",
    "save_draft",
    "save_draft_file",
    "to_json_bytes",
    "validate_document",
]
