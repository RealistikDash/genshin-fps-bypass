# General usage utility functions.
from __future__ import annotations

import time
from typing import Callable
from typing import TypeVar

import winapi


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
    refresh_rate = clamp(refresh_rate, 30, 240)
    return refresh_rate
