# General usage utility functions.
from __future__ import annotations

import sys
import time
from typing import Callable
from typing import TypeVar

import winapi


NO_PAUSE = "no-pause" in sys.argv


def make_version_string(version: tuple[int, int, int]) -> str:
    """Converts a version tuple to a string."""

    return ".".join(str(v) for v in version)


T = TypeVar("T")


def wait_for(func: Callable[[], T | None], timeout: float = 0.1) -> T:
    """Waits for a function to return a value."""

    while not (res := func()):
        time.sleep(timeout)

    return res


# Why is this not in the standard library?
def clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamps a value between a minimum and maximum."""

    return max(minimum, min(value, maximum))


def get_default_fps() -> int:
    """Returns the FPS value that the bypass will default to based on
    the user's setup."""

    refresh_rate = winapi.get_main_refresh_rate()

    # On some configs, this is weird. Clamp it to a reasonable range.
    refresh_rate = clamp(refresh_rate, 30, 390)
    return refresh_rate


def exit_pause() -> None:
    """Allows the user time to read a potential error message before closing."""

    if not NO_PAUSE:
        input("Press enter to exit...")


def human_readable_bytes(size: float) -> str:
    """Converts a quantity of bytes to a human-readable format."""

    if size < 1024:
        return f"{size}B"

    size /= 1024
    if size < 1024:
        return f"{size:.2f}KB"

    size /= 1024
    if size < 1024:
        return f"{size:.2f}MB"

    size /= 1024
    return f"{size:.2f}GB"


def human_readable_time(seconds: float) -> str:
    """Converts a quantity of seconds to a human-readable format."""

    if seconds < 60:
        return f"{seconds:.2f}s"

    seconds /= 60
    return f"{seconds:.2f}m"
