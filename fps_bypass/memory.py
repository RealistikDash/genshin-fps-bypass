# Tools to assist with memory reading and writing.


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


def signature_scan(buffer: bytes, signature: Signature) -> int | None:
    """Scans a buffer for a signature."""

    pattern = signature.pattern  # Attribute access optimisation

    for i in range(len(buffer) - len(signature.pattern)):
        # Checking the first byte is faster than checking the whole pattern.
        if buffer[i] == pattern[0]:
            for j in range(1, len(pattern)):
                if pattern[j] is None:
                    continue

                if buffer[i + j] != pattern[j]:
                    break
            else:
                return i
