# Wakelet

A HomeKit IoT bridge for managing and controlling hosts on a local network. Hosts are exposed as HomeKit accessories, allowing you to wake and shut down machines directly from the Home app.

## Features

- **Wake** — send a Wake-on-LAN magic packet via `etherwake`
- **Shutdown** — SSH into a host as the `wakelet` user, triggering an automatic shutdown on login
- **Reachability** — periodically pings each host and reflects its online/offline state in HomeKit
- **Hosts** — configured via a simple `hosts.yaml` file local to the deployment

## Requirements

- Python 3.11+
- `etherwake` installed on the server (`apt install etherwake`)
- `HAP-python`

---

## Server installation

### 1. Create a dedicated system user

```bash
sudo useradd -r -m -s /bin/bash wakelet
sudo -i -u wakelet
```

All subsequent steps run as the `wakelet` user unless stated otherwise.

### 2. Clone the repository

```bash
git clone https://github.com/tlhakhan/wakelet.git ~/wakelet
cd ~/wakelet
```

### 3. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Python dependencies

```bash
pip install HAP-python pyyaml
```

### 5. Install etherwake

Exit back to a sudo-capable user for this step:

```bash
exit   # back to your admin user
sudo apt install etherwake
```

### 6. Configure sudo access for etherwake

```bash
sudo cp ~/wakelet/example/sudoers.example /etc/sudoers.d/wakelet
sudo visudo -cf /etc/sudoers.d/wakelet   # must print "parsed OK"
```

If the path to `etherwake` differs on your system, update it first:

```bash
which etherwake   # verify path matches /usr/sbin/etherwake
```

### 7. Generate the SSH key pair

```bash
sudo -i -u wakelet   # switch back to wakelet user
cd ~/wakelet
mkdir -p private
ssh-keygen -t ed25519 -f private/wakelet -N ""
```

This creates:
- `private/wakelet` — private key used by the bridge to SSH into target hosts
- `private/wakelet.pub` — public key to be deployed to each target host

The `private/` directory is excluded from version control via `.gitignore`.

### 8. Configure hosts

```bash
cp example/hosts.yaml hosts.yaml
```

Edit `hosts.yaml` to match your environment. Each entry requires a hostname ending in `.local` and a MAC address:

```yaml
hosts:
  - name: desktop.local
    mac: aa:bb:cc:dd:ee:ff
```

---

## Running

### Manually

```bash
source .venv/bin/activate
python driver.py
```

### As a systemd service

```bash
sudo cp ~/wakelet/example/wakelet.service /etc/systemd/system/wakelet.service
sudo systemctl daemon-reload
sudo systemctl enable --now wakelet
```

Check status and logs:

```bash
sudo systemctl status wakelet
sudo journalctl -u wakelet -f
```

---

## Setting up target hosts for shutdown

Each host you want to shut down must be configured with a `wakelet` SSH user whose login immediately triggers a shutdown. Use the setup script with the public key generated above:

```bash
scp example/setup_wakelet.sh private/wakelet.pub user@target-host:~
ssh user@target-host "sudo bash setup_wakelet.sh ~/wakelet.pub"
```

See [example/README.md](example/README.md) for full details.

---

## Project structure

```
driver.py                HAP-python bridge entry point
services/
  hosts.py               Loads host records from hosts.yaml
  network.py             Auto-detect network interface
example/
  hosts.yaml             Example hosts configuration
  setup_wakelet.sh       Script to configure shutdown-on-login on target hosts
  sudoers.example        Sudoers entry for etherwake
  wakelet.service        systemd service unit file
private/                 SSH key pair (not committed)
hosts.yaml               Host configuration (not committed)
wakelet.state            HAP pairing state (not committed)
```
