# File: drafts/storage.py
# Purpose: Versioned encrypted draft envelope plus atomic, fail-safe file I/O.
# Encoding: UTF-8
"""Encrypted draft file format and durable writing.

File layout (all integers big-endian)::

    offset 0   magic          8 bytes   b"CFADRAFT"
    offset 8   envelope ver.  1 byte    0x01
    offset 9   payload length 4 bytes   uint32, ciphertext byte count
    offset 13  ciphertext     N bytes   DPAPI blob of the UTF-8 JSON document

The envelope is deliberately tiny: it only identifies the format and the
version so an incompatible or truncated file is rejected before any
decryption is attempted. Nothing outside the ciphertext is readable.

Writing is atomic and never leaves plaintext on disk:

1. the payload is protected in memory,
2. the envelope is written to a ``.cfadraft-*.tmp`` file **in the destination
   directory** (same volume, so the final step is a rename, not a copy),
3. the temporary file is flushed and ``fsync``-ed,
4. ``os.replace`` swaps it into place in one step.

A failure at any point leaves an existing draft untouched and removes the
temporary artifact. The storage layer never imports Qt and never inspects a
widget; it only moves bytes.
"""

import os
import struct
import tempfile

from drafts.errors import (
    DraftFileTooLargeError,
    DraftFormatError,
    DraftStorageError,
)
from drafts.windows_protection import get_default_protector

#: File magic identifying an encrypted Civil Filing Assistant draft.
MAGIC = b"CFADRAFT"

#: Version of the *outer* encrypted envelope (not of the JSON document).
ENVELOPE_VERSION = 1

#: ``magic`` + version byte + payload length.
_HEADER = struct.Struct(">8sBI")
HEADER_SIZE = _HEADER.size  # 13

#: Hard bound on the bytes read from disk, checked before decryption.
MAX_FILE_BYTES = 1 << 20  # 1 MiB

#: Hard bound on the decrypted JSON document, checked before parsing.
MAX_PLAINTEXT_BYTES = 512 << 10  # 512 KiB

#: Prefix/suffix of the same-directory temporary write artifact.
_TEMP_PREFIX = ".cfadraft-"
_TEMP_SUFFIX = ".tmp"

__all__ = [
    "ENVELOPE_VERSION",
    "HEADER_SIZE",
    "MAGIC",
    "MAX_FILE_BYTES",
    "MAX_PLAINTEXT_BYTES",
    "build_envelope",
    "load_draft_file",
    "parse_envelope",
    "save_draft_file",
]


def build_envelope(ciphertext):
    """Wrap *ciphertext* in the versioned envelope."""
    body = bytes(ciphertext)
    if not body:
        raise DraftFormatError("草稿密文为空，未写入文件。")
    if len(body) > MAX_FILE_BYTES - HEADER_SIZE:
        raise DraftFileTooLargeError("加密后的草稿内容超出文件大小上限。")
    return _HEADER.pack(MAGIC, ENVELOPE_VERSION, len(body)) + body


def parse_envelope(raw):
    """Return the ciphertext of *raw*, rejecting anything malformed.

    Every rejection path is explicit so a truncated, padded or future-version
    file can never be mistaken for a usable draft.
    """
    data = bytes(raw)
    if len(data) < HEADER_SIZE:
        raise DraftFormatError("草稿文件不完整（文件头被截断）。")
    magic, version, length = _HEADER.unpack(data[:HEADER_SIZE])
    if magic != MAGIC:
        raise DraftFormatError("该文件不是本工具保存的草稿文件。")
    if version != ENVELOPE_VERSION:
        raise DraftFormatError(
            f"草稿文件版本不受支持（文件版本 {version}，当前支持 {ENVELOPE_VERSION}）。"
        )
    if length == 0:
        raise DraftFormatError("草稿文件不完整（缺少加密内容）。")
    if len(data) != HEADER_SIZE + length:
        raise DraftFormatError("草稿文件长度与文件头记录不一致，可能已被截断或修改。")
    return data[HEADER_SIZE:]


def _atomic_write(path, data):
    """Write *data* to *path* through a same-directory temporary file."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    if not os.path.isdir(directory):
        raise DraftStorageError("草稿保存目录不存在，请重新选择保存位置。")

    try:
        handle_fd, temp_path = tempfile.mkstemp(
            prefix=_TEMP_PREFIX, suffix=_TEMP_SUFFIX, dir=directory
        )
    except OSError:
        raise DraftStorageError("无法在目标目录创建草稿临时文件，请检查目录权限。")

    try:
        with os.fdopen(handle_fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    except OSError:
        raise DraftStorageError("写入草稿文件失败，原有草稿未被修改。")
    finally:
        if temp_path is not None:
            try:
                os.remove(temp_path)
            except OSError:
                # A leftover artifact contains encrypted bytes only; the
                # caller still reports the original failure.
                pass


def save_draft_file(path, plaintext, protector=None):
    """Protect *plaintext* and write it to *path* atomically."""
    payload = bytes(plaintext)
    if not payload:
        raise DraftStorageError("草稿内容为空，未写入文件。")
    if len(payload) > MAX_PLAINTEXT_BYTES:
        raise DraftFileTooLargeError("草稿内容超出支持的大小上限，未写入文件。")

    # A protection failure propagates unchanged: it is already a DraftError
    # whose message is safe to show, and nothing has been written at this point.
    active = protector or get_default_protector()
    ciphertext = active.protect(payload)

    _atomic_write(path, build_envelope(ciphertext))


def load_draft_file(path, protector=None):
    """Read *path* and return its decrypted plaintext.

    The size bound is applied to the bytes actually read (not only to the
    size reported by ``stat``), so a file that grows between the two calls is
    still rejected.
    """
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
    except FileNotFoundError:
        raise DraftStorageError("找不到该草稿文件。")
    except OSError:
        raise DraftStorageError("无法读取该草稿文件，请检查文件权限。")

    if not raw:
        raise DraftFormatError("草稿文件为空。")
    if len(raw) > MAX_FILE_BYTES:
        raise DraftFileTooLargeError("草稿文件超出支持的大小上限。")

    ciphertext = parse_envelope(raw)

    active = protector or get_default_protector()
    plaintext = active.unprotect(ciphertext)
    if len(plaintext) > MAX_PLAINTEXT_BYTES:
        raise DraftFileTooLargeError("草稿内容超出支持的大小上限。")
    return plaintext
