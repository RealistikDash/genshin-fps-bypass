# Tools to assist with memory reading and writing.
from __future__ import annotations

import logging
import time
from typing import Callable

import utils

logger = logging.getLogger("rich")


class Signature:
    __slots__ = (
        "pattern",
        "_scan",
    )

    def __init__(self, *pattern):
        self.pattern = pattern
        self._scan = None

    def __repr__(self) -> str:
        start = "Signature("

        for byte in self.pattern:
            if byte is None:
                start += "?? "
                continue

            byte_str = hex(byte)[2:].upper()
            if len(byte_str) == 1:
                byte_str = "0" + byte_str

            start += f"{byte_str} "

        return start[:-1] + ")"

    def __len__(self) -> int:
        return len(self.pattern)

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Signature):
            return False

        return self.pattern == __o.pattern

    def compile(self) -> SignatureFunction:
        """Compiles a signature into a Python function."""
        if self._scan is None:
            self._scan = compile_signature(self)

        return self._scan


def signature_scan(buffer: bytes, signature: Signature) -> int | None:
    func = signature.compile()

    start_time = time.perf_counter()
    res = func(buffer)

    if res is None:
        return None

    time_taken = time.perf_counter() - start_time
    logger.debug(
        f"Scanning signature {signature!r} took {utils.human_readable_time(time_taken)}. "
        f"Scanned {utils.human_readable_bytes(res)} ({(res/len(buffer)) * 100:.2f}% of buffer).",
    )

    return res


def signature_match(buffer: bytes, signature: Signature) -> bool:
    """Returns whether a buffer EXACTLY matches a signature.
    Unoptimised for frequent use."""

    if len(buffer) != len(signature.pattern):
        return False

    for pattern_byte, buffer_byte in zip(signature.pattern, buffer):
        if pattern_byte is None:
            continue

        if pattern_byte != buffer_byte:
            return False

    return True


# Mum can we have a JIT?
# No we have a JIT at home.
# The JIT at home:
SignatureFunction = Callable[[bytes], int | None]
BASE_FUNCTION = """
def _sig_func(buffer: bytes) -> int | None:
    {pre_setup}

    for i in range(len(buffer) - {pattern_len}):
        if (
            {conditions}
        ): return i
"""


def compile_signature(signature: Signature) -> SignatureFunction:
    conditions = []
    for i, byte in enumerate(signature.pattern):
        if byte is None:
            continue

        conditions.append(f"buffer[i + {i}] == {byte}")

    condition_str = " and ".join(conditions)
    function = BASE_FUNCTION.format(
        conditions=condition_str,
        pre_setup="",
        pattern_len=len(signature),
    )

    exec(function, globals(), locals())
    return locals()["_sig_func"]


# This was slower.
# def compile_signature(signature: Signature) -> SignatureFunction:
#    """Compiles a signature into a Python function."""#

#    # Find groups of bytes in the signature that are set.
#    results = list[tuple[int, tuple[int, ...]]]()
#    pat_len = len(signature)
#    i = 0#

#    while i < pat_len:
#        if signature.pattern[i] is None:
#            i += 1
#            continue#

#        j = i
#        while j < pat_len and signature.pattern[j] is not None:
#            j += 1#

#        results.append((i, signature.pattern[i:j]))
#        i = j#

#    # Condition generation
#    conditions = []
#    pat_gen_tuples = list[tuple[str, tuple[int, ...]]]()#

#    for offset, group in results:
#        if len(group) == 1:
#            conditions.append(f"buffer[i + {offset}] == {group[0]}")
#            continue#

#        # Generate a tuple of bytes.
#        pat_gen_tuples.append((f"_PAT_PART_{offset}", group))
#        conditions.append(f"buffer[i + {offset}:i + {offset + len(group)}] == _PAT_PART_{offset}")#

#    condition_str = " and ".join(conditions)
#    pre_setup_str = "\n    ".join(
#        f"{name} = memoryview(bytes({bytes}))" for name, bytes in pat_gen_tuples
#    )#
#

#    # Function generation
#    function = BASE_FUNCTION.format(
#        conditions=condition_str,
#        pre_setup=pre_setup_str,
#        pattern_len=pat_len,
#    )#

#    # Compile the function
#    exec(function, globals(), locals())
#    return locals()["_sig_func"]
