# General usage utility functions.
import os


def is_compatible() -> bool:
    """Checks if the current platform is compatible with the script."""
    
    return os.name == "nt"
