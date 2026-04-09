import re

_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.local$")
_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")


def validate_host(name: str, mac: str) -> dict[str, str]:
    """Return a dict of field -> error message for any invalid fields."""
    errors = {}

    if not _HOSTNAME_RE.match(name):
        errors["name"] = "Must be a valid hostname ending in .local (e.g. mydevice.local)"

    if not _MAC_RE.match(mac):
        errors["mac"] = "Must be a valid MAC address (e.g. aa:bb:cc:dd:ee:ff)"

    return errors
