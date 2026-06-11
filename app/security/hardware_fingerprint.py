from __future__ import annotations

import hashlib
import os
import platform
import subprocess
from typing import Iterable


def _safe_part(value: str | None) -> str:
    return (value or "").strip().lower()


def _sha256_hex(parts: Iterable[str]) -> str:
    joined = "|".join(parts).encode("utf-8", errors="ignore")
    return hashlib.sha256(joined).hexdigest()


def _get_windows_machine_guid() -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg  # type: ignore

        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        return str(value)
    except Exception:
        return ""


def _get_volume_serial() -> str:
    if os.name != "nt":
        return ""

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        volume_name = ctypes.create_unicode_buffer(261)
        fs_name = ctypes.create_unicode_buffer(261)
        serial_number = ctypes.c_uint32(0)
        max_component = ctypes.c_uint32(0)
        file_system_flags = ctypes.c_uint32(0)

        root = os.environ.get("SystemDrive", "C:") + "\\"
        ok = kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            volume_name,
            ctypes.sizeof(volume_name),
            ctypes.byref(serial_number),
            ctypes.byref(max_component),
            ctypes.byref(file_system_flags),
            fs_name,
            ctypes.sizeof(fs_name),
        )
        if ok:
            return f"{serial_number.value:08X}"
    except Exception:
        pass
    return ""


def _get_cpu_identifier() -> str:
    cpu_env = _safe_part(os.environ.get("PROCESSOR_IDENTIFIER"))
    if cpu_env:
        return cpu_env

    if os.name != "nt":
        return _safe_part(platform.processor())

    try:
        output = subprocess.check_output(
            ["wmic", "cpu", "get", "ProcessorId"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
        lines = [ln.strip() for ln in output.splitlines() if ln.strip() and "ProcessorId" not in ln]
        if lines:
            return lines[0]
    except Exception:
        pass
    return ""


def get_machine_fingerprint() -> str:
    parts = [
        _safe_part(_get_windows_machine_guid()),
        _safe_part(_get_volume_serial()),
        _safe_part(_get_cpu_identifier()),
    ]

    if not any(parts):
        parts = [
            _safe_part(platform.node()),
            _safe_part(platform.platform()),
            _safe_part(platform.machine()),
        ]

    return _sha256_hex(parts)
