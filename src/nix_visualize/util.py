"""Miscellaneous utilities for the Nix tree visualizer"""

class TreeCLIError(Exception):
    """Exception to be raised by the CLI"""
    pass


def remove_nix_hash(string):
    """Given a nix store name of the form <hash>-<packagename>, remove
    the hash
    """
    return "-".join(string.split("-")[1:])

def clamp(n, maxabs):
    """Clamp a number to be between -maxabs and maxabs"""
    return max(-maxabs, min(n, maxabs))
