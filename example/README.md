# Deployment Guide

This folder contains the files needed to configure the server running the Wakelet app and the target hosts it controls.

---

## 1. Server setup — allow `etherwake` without a password

The Wakelet app runs `etherwake` as `sudo` to send Wake-on-LAN packets. The web process user must be permitted to do this without a password prompt.

### Steps

1. Copy the example sudoers file to `/etc/sudoers.d/`:

   ```bash
   sudo cp sudoers.example /etc/sudoers.d/wakelet
   ```

2. Open the file and replace `wakelet` on the first line with the user your FastAPI process runs as (e.g. `www-data`, `ubuntu`, or a dedicated service account):

   ```bash
   sudo nano /etc/sudoers.d/wakelet
   ```

3. Validate the syntax before relying on it:

   ```bash
   sudo visudo -cf /etc/sudoers.d/wakelet
   ```

   You should see: `... parsed OK`

4. Verify the correct paths for `etherwake` and `ping` on your system:

   ```bash
   which etherwake
   which ping
   ```

   Update the paths in the sudoers file if they differ from `/usr/sbin/etherwake` and `/usr/bin/ping`.

### Notes

- The sudoers filename must not contain dots or end with `~`, otherwise it is silently ignored by `sudo`.
- Never edit `/etc/sudoers` directly — always use `visudo` or drop files into `/etc/sudoers.d/`.

---

## 2. Target host setup — shutdown on SSH login

Each host you want to shut down via the Wakelet app needs a dedicated `wakelet` SSH user whose login immediately triggers `shutdown -h now`. The `setup_wakelet.sh` script handles this end-to-end.

### Prerequisites

- The target host must be running Linux with `systemd` and `openssh-server`
- You must have `sudo` / root access on the target host
- You need the Wakelet SSH **public** key (the counterpart to `private/wakelet` on the server)

### Generate the key pair (run once on the Wakelet server)

```bash
ssh-keygen -t ed25519 -f private/wakelet -N ""
```

This creates:
- `private/wakelet` — private key (stays on the server, never shared)
- `private/wakelet.pub` — public key (deployed to each target host)

### Run the setup script on each target host

Copy the script and public key to the target host, then run:

```bash
scp setup_wakelet.sh wakelet.pub user@target-host:~
ssh user@target-host
sudo ./setup_wakelet.sh ~/wakelet.pub
```

Or run it directly over SSH in one step:

```bash
ssh user@target-host "sudo bash -s" < setup_wakelet.sh private/wakelet.pub
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

## File reference

| File | Purpose |
|------|---------|
| `sudoers.example` | Sudoers fragment granting the app user permission to run `etherwake` without a password |
| `setup_wakelet.sh` | Script to configure a target host with a shutdown-on-login `wakelet` user |
