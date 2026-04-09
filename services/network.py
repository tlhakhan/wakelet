import re
import socket

_INTERFACE_PATTERN = re.compile(r"^(en|et)")


def detect_interface() -> str:
    """Return the first network interface whose name starts with 'en' or 'et'.

    Raises RuntimeError if no matching interface is found.
    """
    for _, name in socket.if_nameindex():
        if _INTERFACE_PATTERN.match(name):
            return name
    raise RuntimeError("No wired interface found (expected name starting with 'en' or 'et')")
