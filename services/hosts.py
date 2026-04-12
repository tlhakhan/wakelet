from dataclasses import dataclass
from pathlib import Path

import yaml

@dataclass
class Host:
    name: str
    mac: str


def list_hosts(hosts_file: Path) -> list[Host]:
    if not hosts_file.exists():
        return []
    with hosts_file.open() as f:
        data = yaml.safe_load(f)
    return [Host(**entry) for entry in data.get("hosts", [])]
