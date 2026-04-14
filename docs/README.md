# Deployment Guide

This folder contains the files needed to configure the Wakelet bridge and the target hosts it controls.

---

## 1. Configure the registry

Copy the example registry file and edit it to match your environment:

```bash
cp docs/registry.yaml /etc/wakelet/registry.yaml
```

### Hosts

Each host entry requires a hostname and a MAC address. The `holdup_timer` field is optional and controls how many seconds to wait after a power-on command before checking reachability (defaults to 60 seconds):

```yaml
hosts:
  - name: desktop.local
    mac: aa:bb:cc:dd:ee:ff
  - name: nas.local
    mac: ca:fe:ba:be:00:02
    holdup_timer: 90
```

### UPS

To expose a UPS monitored by NUT, add a `ups` section. Each entry requires the NUT device name (`nut_name`) and a HomeKit display name (`display_name`). `nut_host` and `nut_port` are optional and default to `localhost` and `3493`:

```yaml
ups:
  - nut_name: apc
    display_name: APC Smart-UPS C 1500
    nut_host: localhost
    nut_port: 3493
```

The bridge loads this file at startup. To add or remove entries, edit the file and restart the service.

---

## 2. Target host setup — SSH shutdown

Each host you want to shut down needs a dedicated `wakelet` SSH user whose SSH key is restricted to triggering `shutdown -h now`. The `authorize_wakelet_shutdown.sh` script handles this.

### Prerequisites

- The target host must be running Linux with `openssh-server`
- You must have `sudo` access on the target host
- You need the Wakelet SSH public key, generated automatically on first bridge startup at `/etc/wakelet/private/wakelet.pub`

### Run the setup script on each target host

```bash
scp docs/authorize_wakelet_shutdown.sh user@target-host:~
scp /etc/wakelet/private/wakelet.pub user@target-host:~
ssh user@target-host "sudo bash authorize_wakelet_shutdown.sh ~/wakelet.pub"
```

### What the script does

| Step | Action |
|------|--------|
| 1 | Creates a locked `wakelet` user (no password login) |
| 2 | Adds a sudoers entry allowing `wakelet` to run `shutdown -h now` without a password |
| 3 | Installs the public key in `authorized_keys` with a forced command — the key can only ever trigger a shutdown |

The script is idempotent — safe to run multiple times on the same host.

### Verify the setup

From the Wakelet bridge, test that SSH shutdown works:

```bash
ssh -i /etc/wakelet/private/wakelet -o BatchMode=yes wakelet@<target-hostname>
```

The target machine should begin shutting down immediately.

### Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| `Permission denied (publickey)` | Public key not installed, or wrong key used |
| `Connection refused` | `sshd` not running, or host not reachable |
| SSH connects but machine does not shut down | Forced command not set correctly — re-run the script |
| `sudo: shutdown: command not found` | `shutdown` path differs — check with `which shutdown` and update the script |

---

## 3. Install and start the systemd service

```bash
sudo cp docs/wakelet.service /etc/systemd/system/wakelet.service
sudo systemctl daemon-reload
sudo systemctl enable --now wakelet
```

Check status and logs:

```bash
sudo systemctl status wakelet
sudo journalctl -u wakelet -f
```

---

## File reference

| File | Purpose |
|------|---------|
| `registry.yaml` | Example registry (hosts and UPS entries) |
| `authorize_wakelet_shutdown.sh` | Script to configure a target host with a restricted shutdown user |
| `wakelet.service` | systemd service unit file to run the bridge |
