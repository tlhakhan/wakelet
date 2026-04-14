import argparse
import logging
import signal
import subprocess
import time
from pathlib import Path

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_OUTLET

from services.registry import list_hosts, list_ups, UPS
from services.network import detect_interface, ensure_ssh_key


logging.basicConfig(level=logging.INFO)


class HostAccessory(Accessory):
    """A HomeKit Switch accessory representing a single network host."""

    category = CATEGORY_OUTLET

    def __init__(self, driver, host, authorized_private_key: Path, authorized_user_name: str = "wakelet"):
        super().__init__(driver, host.name)
        self.host = host
        self.authorized_private_key = authorized_private_key
        self.authorized_user_name = authorized_user_name
        self.last_on_time = None

        outlet = self.add_preload_service("Outlet")
        self.on_characteristic = outlet.get_characteristic("On")
        self.on_characteristic.setter_callback = self._set_on
        self.outlet_in_use = outlet.get_characteristic("OutletInUse")
        self.outlet_in_use.set_value(False)

    @Accessory.run_at_interval(10)
    def run(self):
        if self.last_on_time is not None:
            elapsed = time.monotonic() - self.last_on_time
            if elapsed < self.host.holdup_timer:
                logging.info("Reachability %s: holding off for %.0fs after power on", self.host.name, self.host.holdup_timer - elapsed)
                return
        result = subprocess.run(
            ["ping", "-c1", "-W1", self.host.name],
            capture_output=True,
        )
        reachable = result.returncode == 0
        self.outlet_in_use.set_value(reachable)
        self.on_characteristic.set_value(reachable)
        logging.info("Reachability %s: %s", self.host.name, reachable)

    def _set_on(self, value: bool):
        if value:
            self.last_on_time = time.monotonic()
            command = ["sudo", "etherwake", "-b", "-D", "-i", detect_interface(), self.host.mac]
        else:
            command = [
                "ssh",
                "-i", str(self.authorized_private_key),
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=1",
                "-l", self.authorized_user_name,
                self.host.name
            ]
        logging.info("Running: %s", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True)
        logging.info("Result for %s: returncode=%s", self.host.name, result.returncode)


class UPSAccessory(Accessory):
    """HomeKit Outlet accessory for an APC Smart-UPS C 1500 monitored via NUT."""

    category = CATEGORY_OUTLET

    def __init__(self, driver, ups: UPS):
        super().__init__(driver, ups.display_name)
        self._nut_target = f"{ups.nut_name}@{ups.nut_host}:{ups.nut_port}"

        outlet = self.add_preload_service("Outlet")
        self.on_characteristic = outlet.get_characteristic("On")
        self.on_characteristic.setter_callback = lambda _: self.on_characteristic.set_value(True)
        self.outlet_in_use = outlet.get_characteristic("OutletInUse")

        battery = self.add_preload_service("BatteryService")
        self.battery_level = battery.get_characteristic("BatteryLevel")
        self.charging_state = battery.get_characteristic("ChargingState")
        self.status_low_battery = battery.get_characteristic("StatusLowBattery")

    @Accessory.run_at_interval(10)
    def run(self):
        try:
            result = subprocess.run(
                ["upsc", self._nut_target],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logging.warning("UPS poll failed (rc=%s): %s", result.returncode, result.stderr.strip())
                return

            data = {}
            for line in result.stdout.splitlines():
                if ": " in line:
                    key, _, value = line.partition(": ")
                    data[key.strip()] = value.strip()

            status = data.get("ups.status", "")
            on_line = "OL" in status
            low_battery = "LB" in status

            self.on_characteristic.set_value(on_line)
            self.outlet_in_use.set_value(on_line)
            self.battery_level.set_value(int(data.get("battery.charge", 0)))
            self.charging_state.set_value(1 if on_line else 0)
            self.status_low_battery.set_value(1 if low_battery else 0)

            logging.info("UPS status=%s charge=%s%%", status, data.get("battery.charge", "?"))
        except Exception:
            logging.exception("Error polling UPS via NUT; skipping cycle")


def get_bridge(
    driver: AccessoryDriver,
    authorized_private_key: Path,
    authorized_user_name: str,
    registry_file: Path,
) -> Bridge:
    bridge = Bridge(driver, "Wakelet")

    info = bridge.get_service("AccessoryInformation")
    info.get_characteristic("Manufacturer").set_value("Wakelet")
    info.get_characteristic("Model").set_value("IoT Bridge")
    info.get_characteristic("SerialNumber").set_value("WKL-001")
    info.get_characteristic("FirmwareRevision").set_value("1.0.0")

    for host in list_hosts(registry_file):
        bridge.add_accessory(HostAccessory(driver, host, authorized_private_key, authorized_user_name))

    for ups in list_ups(registry_file):
        bridge.add_accessory(UPSAccessory(driver, ups))

    return bridge


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wakelet HomeKit bridge")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path("/var/lib/wakelet/wakelet.state"),
        help="Path to the HAP state file (default: /var/lib/wakelet/wakelet.state)",
    )
    parser.add_argument(
        "--private-dir",
        type=Path,
        default=Path("/etc/wakelet/private"),
        help="Directory for the SSH key pair (default: /etc/wakelet/private)",
    )
    parser.add_argument(
        "--registry-file",
        type=Path,
        default=Path("/etc/wakelet/registry.yaml"),
        help="Path to the registry YAML file (default: /etc/wakelet/registry.yaml)",
    )
    parser.add_argument(
        "--authorized-user-name",
        default="wakelet",
        help="SSH user on target hosts (default: wakelet)",
    )
    args = parser.parse_args()

    authorized_private_key, authorized_public_key = ensure_ssh_key(args.private_dir / "wakelet")

    driver = AccessoryDriver(port=51826, persist_file=str(args.state_file))
    driver.add_accessory(accessory=get_bridge(driver, authorized_private_key, args.authorized_user_name, args.registry_file))

    signal.signal(signal.SIGTERM, driver.signal_handler)

    driver.start()
