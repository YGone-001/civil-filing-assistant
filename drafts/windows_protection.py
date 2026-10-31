# File: drafts/windows_protection.py
# Purpose: Windows DPAPI (current-user scope) protection for draft payloads.
# Encoding: UTF-8
"""Encrypt draft payloads with the Windows Data Protection API.

Design constraints (see the phase brief):

* **No homegrown cipher.** The only confidentiality primitive is
  ``CryptProtectData`` / ``CryptUnprotectData`` from ``crypt32.dll``, bound
  through ``ctypes`` with explicit argument types, explicit ownership rules and
  explicit error handling.
* **Current-user scope.** ``CRYPTPROTECT_LOCAL_MACHINE`` is never passed, so
  the master key is derived from the *calling user's* Windows profile. That is
  a real limitation, not an implementation detail: a draft is expected to be
  unreadable under a different Windows account, on another computer, or after
  the profile keys are lost.
* **Fail closed.** Any unavailable platform, missing DLL, refused call or
  malformed blob raises; there is no plaintext fallback and no default key.

``CRYPTPROTECT_UI_FORBIDDEN`` keeps the call silent so the application never
blocks on a system prompt it cannot explain.

The constant in :data:`_PROTECTION_ENTROPY` is *not* an encryption key. DPAPI
uses it as optional secondary entropy, which binds a blob to this application
domain: a blob protected with different entropy cannot be unprotected. The
actual key material never leaves the Windows profile.
"""

import ctypes
import os
from ctypes import wintypes

from drafts.errors import ProtectionError, ProtectionFailed, ProtectionUnavailable

#: Suppress any DPAPI UI prompt; the application owns all user interaction.
CRYPTPROTECT_UI_FORBIDDEN = 0x01

#: Application-domain separator passed as DPAPI's optional entropy.
_PROTECTION_ENTROPY = b"civil-filing-assistant/cfdraft/v1"

#: A constant description; DPAPI stores it inside the blob. It must never
#: contain case data because it is echoed back by ``CryptUnprotectData``.
_PROTECTION_DESCRIPTION = "civil-filing-assistant draft"

#: Upper bound accepted by :meth:`WindowsDpapi.protect`.
MAX_PROTECTED_INPUT = 1 << 20

__all__ = [
    "CRYPTPROTECT_UI_FORBIDDEN",
    "MAX_PROTECTED_INPUT",
    "ProtectionError",
    "ProtectionFailed",
    "ProtectionUnavailable",
    "WindowsDpapi",
    "get_default_protector",
]


class _DataBlob(ctypes.Structure):
    """The Win32 ``DATA_BLOB`` structure (byte count + owned buffer pointer)."""

    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _blob_from(data):
    """Return ``(blob, buffer)`` for *data*.

    The caller must keep the returned buffer alive for as long as the blob is
    passed to a Win32 call; ``DATA_BLOB`` stores a raw pointer and does not own
    the memory.
    """
    buffer = ctypes.create_string_buffer(bytes(data), len(data))
    blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    return blob, buffer


class WindowsDpapi:
    """Thin, reviewed ``ctypes`` binding for current-user DPAPI.

    The DLL handles are resolved lazily so that importing this module never
    touches Win32 and so that an unsupported platform fails at call time with
    an explicit :class:`ProtectionUnavailable`.
    """

    def __init__(self):
        self._crypt32 = None
        self._kernel32 = None
        self._load_attempted = False

    # -- binding ---------------------------------------------------------

    def _load(self):
        """Resolve and type the Win32 entry points; ``False`` when unavailable."""
        if self._load_attempted:
            return self._crypt32 is not None
        self._load_attempted = True
        if os.name != "nt":
            return False
        try:
            crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        except OSError:
            return False

        blob_p = ctypes.POINTER(_DataBlob)
        crypt32.CryptProtectData.argtypes = [
            blob_p,                    # pDataIn
            wintypes.LPCWSTR,          # szDataDescr
            blob_p,                    # pOptionalEntropy
            ctypes.c_void_p,           # pvReserved (must be NULL)
            ctypes.c_void_p,           # pPromptStruct (must be NULL)
            wintypes.DWORD,            # dwFlags
            blob_p,                    # pDataOut
        ]
        crypt32.CryptProtectData.restype = wintypes.BOOL

        crypt32.CryptUnprotectData.argtypes = [
            blob_p,                    # pDataIn
            ctypes.POINTER(wintypes.LPWSTR),  # ppszDataDescr (optional OUT)
            blob_p,                    # pOptionalEntropy
            ctypes.c_void_p,           # pvReserved (must be NULL)
            ctypes.c_void_p,           # pPromptStruct (must be NULL)
            wintypes.DWORD,            # dwFlags
            blob_p,                    # pDataOut
        ]
        crypt32.CryptUnprotectData.restype = wintypes.BOOL

        # The output buffer of a successful call is allocated by DPAPI and must
        # be released with LocalFree from kernel32 (not from crypt32).
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        self._crypt32 = crypt32
        self._kernel32 = kernel32
        return True

    def available(self):
        """Return whether current-user DPAPI can be used in this process."""
        return self._load()

    # -- operations ------------------------------------------------------

    def protect(self, data):
        """Return a DPAPI blob for *data* under the current Windows user."""
        payload = bytes(data)
        if not payload:
            raise ProtectionFailed("没有可加密的草稿内容。")
        if len(payload) > MAX_PROTECTED_INPUT:
            raise ProtectionFailed("草稿内容超出可加密的大小上限。")
        if not self._load():
            raise ProtectionUnavailable(
                "当前系统环境不支持 Windows 用户级数据保护，无法加密保存草稿。"
            )

        in_blob, _in_buffer = _blob_from(payload)
        entropy_blob, _entropy_buffer = _blob_from(_PROTECTION_ENTROPY)
        out_blob = _DataBlob()

        ok = self._crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            _PROTECTION_DESCRIPTION,
            ctypes.byref(entropy_blob),
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(out_blob),
        )
        if not ok:
            raise ProtectionFailed("Windows 数据保护未能加密草稿内容，草稿未保存。")
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            self._kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))

    def unprotect(self, blob):
        """Return the plaintext of a DPAPI *blob* protected for this user."""
        ciphertext = bytes(blob)
        if not ciphertext:
            raise ProtectionFailed("草稿密文为空。")
        if len(ciphertext) > MAX_PROTECTED_INPUT:
            raise ProtectionFailed("草稿密文超出可解密的大小上限。")
        if not self._load():
            raise ProtectionUnavailable(
                "当前系统环境不支持 Windows 用户级数据保护，无法解密草稿。"
            )

        in_blob, _in_buffer = _blob_from(ciphertext)
        entropy_blob, _entropy_buffer = _blob_from(_PROTECTION_ENTROPY)
        out_blob = _DataBlob()

        ok = self._crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(out_blob),
        )
        if not ok:
            # Deliberately generic: a wrong Windows account, a corrupted blob
            # and a tampered payload are indistinguishable here, and naming the
            # Windows error code would add no user value.
            raise ProtectionFailed(
                "无法解密该草稿：文件可能已损坏，或不是由当前 Windows 用户保存的。"
            )
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            self._kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))


_DEFAULT_PROTECTOR = WindowsDpapi()


def get_default_protector():
    """Return the process-wide :class:`WindowsDpapi` instance."""
    return _DEFAULT_PROTECTOR
