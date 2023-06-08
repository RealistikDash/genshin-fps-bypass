# Tools to assist with memory reading and writing.
from __future__ import annotations


class Signature:
    __slots__ = ("pattern",)

    def __init__(self, *pattern):
        self.pattern = pattern

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


# TODO: Optimise this. 4s is a bit ehh.
def signature_scan(buffer: bytes, signature: Signature) -> int | None:
    """Scans a buffer for a signature."""

    pattern = signature.pattern  # Attribute access optimisation
    pattern_len = len(pattern)

    for i in range(len(buffer) - pattern_len):
        # Checking the first byte is a 5x speedup.
        if buffer[i] == pattern[0]:
            for j in range(1, pattern_len):
                if pattern[j] is None:
                    continue

                if buffer[i + j] != pattern[j]:
                    break
            else:
                return i


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
