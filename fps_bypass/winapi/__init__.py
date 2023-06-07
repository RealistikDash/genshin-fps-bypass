# A (over)simplified abstraction over the Windows API for usage in Python.
# Meant to be treaded as a sort of black box.
from __future__ import annotations

from .exceptions import *
from .constants import *
from .structures import *

import ctypes
from ctypes.wintypes import (
    HMODULE,
    DWORD,
)

from typing import (
    NamedTuple,
    Generator,
    Callable,
)

win32 = ctypes.windll.kernel32


class Handle:
    """Provides abstractions over a Windows handle. NOT GUARANTEED TO
    BE OPEN."""

    __slots__ = ("_handle",)

    def __init__(self, handle: int) -> None:
        self._handle = handle

    def __enter__(self) -> Handle:
        if not self.is_set():
            raise OSError("Handle is not set/invalid.")

        return self

    def __exit__(self, *args) -> None:
        self.close()

    def close(self) -> None:
        """Closes the handle, marking the object as unusable."""
        if not win32.CloseHandle(self._handle):
            raise OSError(f"Failed to close handle: {get_os_error_fmt()}")

        self._handle = 0

    def is_set(self) -> bool:
        """Returns whether the handle is set."""

        return self._handle != 0


def _make_raw_handle(handle: Handle) -> int:
    """Returns the raw handle value. Used to pass handles to the Windows API."""

    return handle._handle


def get_os_error() -> int | None:
    """Returnts the enumeration of the last OS error."""

    return win32.GetLastError() or None


def get_os_error_fmt() -> str | None:
    """Returns a string representation of the last OS error."""

    code = get_os_error()
    if not code:
        return None

    return f"{ctypes.FormatError(code)} ({code})"


def process_id_by_name(name: str) -> int | None:
    """Returns the process ID of a process by the executable name."""

    snapshot = Handle(
        win32.CreateToolhelp32Snapshot(
            TH32CS_SNAPPROCESS,
            0,
        )
    )

    with snapshot:
        process_entry = PROCESSENTRY32()
        process_entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

        process = win32.Process32First(
            _make_raw_handle(snapshot), ctypes.byref(process_entry)
        )

        if not process:
            raise OSError(
                f"Failed to get process entry. Error code: {get_os_error_fmt()}"
            )

        while process:
            if process_entry.szExeFile.decode() == name:
                return process_entry.th32ProcessID

            process = win32.Process32Next(
                _make_raw_handle(snapshot), ctypes.byref(process_entry)
            )

    return None


def terminate_process(handle: Handle) -> None:
    """Terminates a process by handle and closes it."""

    if not win32.TerminateProcess(_make_raw_handle(handle), 0):
        raise OSError(f"Failed to terminate handle: {get_os_error_fmt()}")

    handle.close()


DEFAULT_ACCESS = PROCESS_QUERY_INFORMATION | SYNCHRONISE


def open_process(process_id: int, access: int = DEFAULT_ACCESS) -> Handle:
    """Opens a process by process ID."""

    handle = Handle(win32.OpenProcess(access, False, process_id))

    if not handle.is_set():
        raise OSError(f"Failed to open process: {get_os_error_fmt()}")

    return handle


# https://stackoverflow.com/a/26271422
def get_process_path(handle: Handle) -> str:
    """Returns the path of a process executable by handle."""

    output = (ctypes.c_char * MAX_PATH)()

    if not win32.QueryFullProcessImageNameA(
        _make_raw_handle(handle), 0, output, ctypes.byref(DWORD(MAX_PATH))
    ):
        raise OSError(f"Failed to get process path: {get_os_error_fmt()}")

    return output.value.decode()


def has_uac() -> bool:
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


class ProcessCreationResult(NamedTuple):
    id: int
    handle: Handle


def create_process(path: str) -> ProcessCreationResult:
    """Creates a new process located at the given path."""

    startup_info = STARTUPINFOA()
    process_info = PROCESS_INFORMATION()

    if not win32.CreateProcessA(
        path.encode(),
        None,
        None,
        None,
        False,
        0,
        None,
        None,
        ctypes.byref(startup_info),
        ctypes.byref(process_info),
    ):
        raise OSError(f"Failed to create process: {get_os_error_fmt()}")

    # Close the thread handle, we don't need it.
    Handle(process_info.hThread).close()

    return ProcessCreationResult(
        process_info.dwProcessId, Handle(process_info.hProcess)
    )


class ModuleInfo(NamedTuple):
    base: int
    size: int


FilterLike = Callable[[str], bool]
ModuleGenerator = Generator[ModuleInfo, None, None]
MODULE_SIZE = 1024


def get_modules(handle: Handle, filter: FilterLike = lambda x: True) -> ModuleGenerator:
    """Generator giving the base address and size of each module in the given process
    based on a filter condition."""

    modules = (HMODULE * MODULE_SIZE)()
    mem_used = DWORD()

    if not win32.EnumProcessModules(
        _make_raw_handle(handle),
        ctypes.byref(modules),
        MODULE_SIZE * ctypes.sizeof(HMODULE),
        ctypes.byref(mem_used),
    ):
        raise OSError(f"Failed to enumerate process modules: {get_os_error_fmt()}")

    iterations = mem_used.value // ctypes.sizeof(HMODULE)

    for i in range(iterations):
        module = modules[i]

        api_module_name = (ctypes.c_char * MAX_PATH)()
        if not win32.GetModuleBaseNameA(
            _make_raw_handle(handle),
            module,
            ctypes.byref(api_module_name),
            MAX_PATH,
        ):
            continue

        api_module_name = api_module_name.value.decode()
        if not filter(api_module_name):
            continue

        module_info = MODULEINFO()
        if not win32.GetModuleInformation(
            _make_raw_handle(handle),
            module,
            ctypes.byref(module_info),
            ctypes.sizeof(MODULEINFO),
        ):
            continue

        yield ModuleInfo(module_info.lpBaseOfDll, module_info.SizeOfImage)
