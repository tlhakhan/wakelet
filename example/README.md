# Deployment Guide

This folder contains the files needed to configure the server running the Wakelet bridge and the target hosts it controls.

---

## 1. Configure hosts

Copy the example hosts file to the project root and edit it to match your environment:

```bash
cp example/hosts.yaml hosts.yaml
```

Each entry requires a hostname (must end in `.local`) and a MAC address:

```yaml
hosts:
  - name: desktop.local
    mac: aa:bb:cc:dd:ee:ff
```

The bridge loads this file at startup. To add or remove hosts, edit `hosts.yaml` and restart the service.

---

## 2. Server setup — allow `etherwake` without a password

The Wakelet bridge runs `etherwake` as `sudo` to send Wake-on-LAN packets. The `wakelet` user must be permitted to do this without a password prompt.

### Steps

1. Copy the example sudoers file to `/etc/sudoers.d/`:

   ```bash
   sudo cp example/sudoers.example /etc/sudoers.d/wakelet
   ```

2. Validate the syntax before relying on it:

   ```bash
   sudo visudo -cf /etc/sudoers.d/wakelet
   ```

   You should see: `... parsed OK`

3. Verify the correct paths for `etherwake` and `ping` on your system:

   ```bash
   which etherwake
   which ping
   ```

   Update the paths in the sudoers file if they differ from `/usr/sbin/etherwake` and `/usr/bin/ping`.

### Notes

- The sudoers filename must not contain dots or end with `~`, otherwise it is silently ignored by `sudo`.
- Never edit `/etc/sudoers` directly — always use `visudo` or drop files into `/etc/sudoers.d/`.

---

## 3. Target host setup — shutdown on SSH login

Each host you want to shut down via the Wakelet bridge needs a dedicated `wakelet` SSH user whose login immediately triggers `shutdown -h now`. The `setup_wakelet.sh` script handles this end-to-end.

### Prerequisites

- The target host must be running Linux with `systemd` and `openssh-server`
- You must have `sudo` / root access on the target host
- You need the Wakelet SSH **public** key (the counterpart to `private/wakelet` on the bridge server)

### Generate the key pair (run once on the Wakelet server)

```bash
mkdir -p private
ssh-keygen -t ed25519 -f private/wakelet -N ""
```

This creates:
- `private/wakelet` — private key (stays on the server, never shared)
- `private/wakelet.pub` — public key (deployed to each target host)

### Run the setup script on each target host

Copy the script and public key to the target host, then run:

```bash
scp example/setup_wakelet.sh private/wakelet.pub user@target-host:~
ssh user@target-host "sudo bash setup_wakelet.sh ~/wakelet.pub"
```

### What the script does

| Step | Action |
|------|--------|
| 1 | Creates a locked `wakelet` user (no password login) |
| 2 | Adds your public key to `~wakelet/.ssh/authorized_keys` |
| 3 | Adds a sudoers entry allowing `wakelet` to run `shutdown -h now` without a password |
| 4 | Appends a `Match User wakelet` block to `/etc/ssh/sshd_config` with `ForceCommand sudo /sbin/shutdown -h now` |
| 5 | Validates and reloads `sshd` |

The script is idempotent — it is safe to run multiple times on the same host.

### Verify the setup

From the Wakelet server, test that the SSH shutdown works:

```bash
ssh -i private/wakelet -o BatchMode=yes wakelet@<target-hostname>
```

The target machine should begin shutting down immediately.

### Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| `Permission denied (publickey)` | Public key not installed, or wrong key used |
| `Connection refused` | `sshd` not running, or host not reachable |
| SSH connects but machine does not shut down | `ForceCommand` block missing or `sshd` not reloaded — re-run the script |
| `sudo: shutdown: command not found` | `shutdown` path differs — check with `which shutdown` and update the script |

---

## 4. Install and start the systemd service

```bash
sudo cp example/wakelet.service /etc/systemd/system/wakelet.service
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
| `hosts.yaml` | Example host list — copy to project root and edit for your environment |
| `sudoers.example` | Sudoers fragment granting the `wakelet` user permission to run `etherwake` |
| `setup_wakelet.sh` | Script to configure a target host with a shutdown-on-login `wakelet` user |
| `wakelet.service` | systemd service unit file to run the bridge as a background service |
