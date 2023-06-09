from __future__ import annotations

__all__ = (
    "PROCESS_VM_READ",
    "PROCESS_VM_WRITE",
    "PROCESS_QUERY_INFORMATION",
    "SYNCHRONISE",
    "TH32CS_SNAPPROCESS",
    "MAX_PATH",
    "ENUM_CURRENT_SETTINGS",
)

# Read Process Memory
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
SYNCHRONISE = 0x00100000

# Create Snapshot
TH32CS_SNAPPROCESS = 0x00000002

# Enum display settings (https://www.pinvoke.net/default.aspx/user32/enumdisplaysettings.html?diff=y)
ENUM_CURRENT_SETTINGS = -1

# General Use
MAX_PATH = 260
