# Wakelet

A HomeKit IoT bridge for managing and controlling hosts on a local network. Hosts are exposed as HomeKit accessories, allowing you to wake and shut down machines directly from the Home app.

## Features

- **Wake** — send a Wake-on-LAN magic packet via `etherwake`
- **Shutdown** — SSH into a host and trigger a shutdown via a restricted `wakelet` user
- **Reachability** — periodically pings each host and reflects its online/offline state in HomeKit
- **Hosts** — configured via a simple `hosts.yaml` file

## Requirements

- Python 3.11+
- `etherwake` installed on the bridge host (`apt install etherwake`)
- `HAP-python`, `pyyaml`, `cryptography` Python packages

---

## Bridge installation

The bridge runs as root to allow `etherwake` to send raw Ethernet frames without a sudoers entry.

### 1. Clone the repository

```bash
sudo git clone https://github.com/tlhakhan/wakelet.git /opt/wakelet
cd /opt/wakelet
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install HAP-python pyyaml cryptography
```

### 4. Install etherwake

```bash
sudo apt install etherwake
```

### 5. Configure hosts

```bash
cp example/hosts.yaml /etc/wakelet/hosts.yaml
```

Edit `/etc/wakelet/hosts.yaml` to match your environment:

```yaml
hosts:
  - name: desktop.local
    mac: aa:bb:cc:dd:ee:ff
```

### 6. SSH key pair

The bridge automatically generates an Ed25519 SSH key pair on first startup at `/etc/wakelet/private/wakelet`. No manual key generation is needed.

After first startup, copy the public key to each target host:

```bash
cat /etc/wakelet/private/wakelet.pub
```

### 7. Install as a systemd service

```bash
sudo cp /opt/wakelet/example/wakelet.service /etc/systemd/system/wakelet.service
sudo systemctl daemon-reload
sudo systemctl enable --now wakelet
```

Check status and logs:

```bash
sudo systemctl status wakelet
sudo journalctl -u wakelet -f
```

---

## Running manually

```bash
cd /opt/wakelet
source .venv/bin/activate
python driver.py
```

All flags and their defaults:

| Flag | Default | Description |
|------|---------|-------------|
| `--state-file` | `/var/lib/wakelet/wakelet.state` | HAP pairing state file |
| `--private-dir` | `/etc/wakelet/private` | Directory for the SSH key pair |
| `--hosts-file` | `/etc/wakelet/hosts.yaml` | Hosts configuration file |
| `--authorized-user-name` | `wakelet` | SSH user on target hosts |

---

## Setting up target hosts for shutdown

Each host you want to shut down needs the `wakelet` SSH user configured with the bridge's public key. Run the setup script on each target host:

```bash
scp example/setup_wakelet.sh user@target-host:~
scp /etc/wakelet/private/wakelet.pub user@target-host:~
ssh user@target-host "sudo bash setup_wakelet.sh ~/wakelet.pub"
```

The script:
1. Creates a locked `wakelet` user (no password login)
2. Adds a sudoers entry allowing `wakelet` to run `shutdown -h now`
3. Installs the public key in `authorized_keys` with a forced command — the key can only ever trigger a shutdown, nothing else

---

## Project structure

```
driver.py                Entry point — HomeKit bridge
services/
  hosts.py               Loads host records from hosts.yaml
  network.py             Interface detection and SSH key generation
example/
  hosts.yaml             Example hosts configuration
  setup_wakelet.sh       Script to configure shutdown user on target hosts
  sudoers.example        Sudoers entry for etherwake (bridge host)
  wakelet.service        systemd service unit file
  README.md              Deployment notes
```
