import asyncio
import logging
import signal
import subprocess
from pathlib import Path

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_OUTLET

from services.hosts import list_hosts
from services.network import detect_interface


logging.basicConfig(level=logging.INFO)

SSH_KEY = Path("private/wakelet")


class HostAccessory(Accessory):
    """A HomeKit Switch accessory representing a single network host."""

    category = CATEGORY_OUTLET

    def __init__(self, driver, host):
        super().__init__(driver, host.name)
        self.host = host

        outlet = self.add_preload_service("Outlet")
        self.on_characteristic = outlet.get_characteristic("On")
        self.on_characteristic.setter_callback = self._set_on
        self.outlet_in_use = outlet.get_characteristic("OutletInUse")
        self.outlet_in_use.set_value(False)

    REACHABILITY_INTERVAL = 120  # seconds between ping checks

    async def run(self):
        while not self.driver.aio_stop_event.is_set():
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c1", "-W2", self.host.name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            reachable = proc.returncode == 0
            self.outlet_in_use.set_value(reachable)
            self.on_characteristic.set_value(reachable)
            logging.debug("Reachability %s: %s", self.host.name, reachable)
            await asyncio.sleep(self.REACHABILITY_INTERVAL)

    def _set_on(self, value: bool):
        if value:
            command = ["sudo", "etherwake", "-b", "-D", "-i", detect_interface(), self.host.mac]
        else:
            command = [
                "ssh",
                "-i", str(SSH_KEY),
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=1",
                "-l", "wakelet",
                self.host.name
            ]
        logging.info("Running: %s", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True)
        logging.info("Result for %s: returncode=%s", self.host.name, result.returncode)


def get_bridge(driver: AccessoryDriver) -> Bridge:
    bridge = Bridge(driver, "Wakelet")

    info = bridge.get_service("AccessoryInformation")
    info.get_characteristic("Manufacturer").set_value("Wakelet")
    info.get_characteristic("Model").set_value("IoT Bridge")
    info.get_characteristic("SerialNumber").set_value("WKL-001")
    info.get_characteristic("FirmwareRevision").set_value("1.0.0")

    for host in list_hosts():
        bridge.add_accessory(HostAccessory(driver, host))

    return bridge


if __name__ == "__main__":
    driver = AccessoryDriver(port=51826, persist_file="wakelet.state")
    driver.add_accessory(accessory=get_bridge(driver))

    signal.signal(signal.SIGTERM, driver.signal_handler)

    driver.start()
