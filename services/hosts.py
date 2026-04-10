from dataclasses import dataclass
from pathlib import Path

import yaml

HOSTS_FILE = Path("hosts.yaml")


@dataclass
class Host:
    name: str
    mac: str


def list_hosts() -> list[Host]:
    if not HOSTS_FILE.exists():
        return []
    with HOSTS_FILE.open() as f:
        data = yaml.safe_load(f)
    return [Host(**entry) for entry in data.get("hosts", [])]
