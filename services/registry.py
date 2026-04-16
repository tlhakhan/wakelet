from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Host:
    name: str
    mac: str
    holdup_timer: int = 60
    holddown_timer: int = 60


@dataclass
class UPS:
    nut_name: str
    display_name: str
    nut_host: str = "localhost"
    nut_port: int = 3493


def _load(registry_file: Path) -> dict:
    if not registry_file.exists():
        return {}
    with registry_file.open() as f:
        return yaml.safe_load(f) or {}


def list_hosts(registry_file: Path) -> list[Host]:
    data = _load(registry_file)
    return [Host(**entry) for entry in data.get("hosts", [])]


def list_ups(registry_file: Path) -> list[UPS]:
    data = _load(registry_file)
    return [UPS(**entry) for entry in data.get("ups", [])]
