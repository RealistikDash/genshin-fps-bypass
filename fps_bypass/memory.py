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

PARTIAL_SCAN_BASE_FUNCTION = """
def _sig_scan(buffer: bytes) -> int | None:
    byte_sequence = {byte_sequence}
    sequence_offset = {sequence_offset}
    signature_length = {signature_length}
    offset = -signature_length
    try:
        while True:
            initial_offset = buffer.index(byte_sequence, offset + signature_length)
            offset = initial_offset - sequence_offset

            if (
                {conditions}
            ):
                return offset

    except ValueError:
        return None

"""

COMPLETE_SCAN_BASE_FUNCTION = """
def _sig_scan(buffer: bytes) -> int | None:
    try:
        return buffer.index({byte_sequence})
    except ValueError:
        return None
"""


def compile_signature(signature: Signature) -> SignatureFunction:
    """Compiles a signature into a Python function."""

    if None in signature.pattern:  # Partial Scan
        # Find the largest sequence of constant bytes in the signature.
        max_sequence = [-1, b""]
        current_sequence = [-1, b""]

        for i, byte in enumerate(signature.pattern):
            if byte is None:
                if len(current_sequence[1]) > len(max_sequence[1]):
                    max_sequence = current_sequence
                current_sequence = [-1, b""]
                continue

            if current_sequence[0] == -1:
                current_sequence[0] = i
                current_sequence[1] = bytes([byte])

            else:
                current_sequence[1] += bytes([byte])

        # Conditions
        conditions = []
        for i, byte in enumerate(signature.pattern):
            if byte is None:
                continue

            conditions.append(f"buffer[offset + {i}] == {byte}")

        condition_str = " and ".join(conditions)

        # Compile the function.
        func_str = PARTIAL_SCAN_BASE_FUNCTION.format(
            byte_sequence=max_sequence[1],
            sequence_offset=max_sequence[0],
            signature_length=len(signature),
            conditions=condition_str,
        )
    else:
        # Convert list of bytes to bytes.
        byte_sequence = bytes(signature.pattern)
        func_str = COMPLETE_SCAN_BASE_FUNCTION.format(byte_sequence=repr(byte_sequence))

    out_vars = {}

    exec(func_str, {}, out_vars)
    return out_vars["_sig_scan"]
