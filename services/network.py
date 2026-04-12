import logging
import re
import socket
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PublicFormat,
    PrivateFormat,
)

_INTERFACE_PATTERN = re.compile(r"^(en|et)")


def ensure_ssh_key(key_path: Path) -> tuple[Path, Path]:
    """Create the private directory and generate an Ed25519 key pair if not present.

    Returns the private and public key paths.
    """
    private_key_path = key_path
    public_key_path = key_path.with_suffix(".pub")

    if private_key_path.exists():
        return private_key_path, public_key_path

    key_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()

    private_key_path.write_bytes(
        private_key.private_bytes(Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption())
    )
    private_key_path.chmod(0o600)

    public_key_path.write_bytes(
        private_key.public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH)
    )

    logging.info("Generated SSH key pair at %s", key_path)
    return private_key_path, public_key_path


def detect_interface() -> str:
    """Return the first network interface whose name starts with 'en' or 'et'.

    Raises RuntimeError if no matching interface is found.
    """
    for _, name in socket.if_nameindex():
        if _INTERFACE_PATTERN.match(name):
            return name
    raise RuntimeError("No wired interface found (expected name starting with 'en' or 'et')")
