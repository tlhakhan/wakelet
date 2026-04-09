# Wakelet

A small FastAPI web app for managing and controlling hosts on a local network. From the browser you can ping, wake (Wake-on-LAN), and shut down hosts by hostname and MAC address.

## Features

- **Ping** — check if a host is reachable
- **Wake** — send a Wake-on-LAN magic packet via `etherwake`
- **Shutdown** — SSH into a host as `wakelet` user, triggering an automatic shutdown on login
- **Manage hosts** — add and remove hosts (hostname + MAC address) stored in a local SQLite database
- Responsive UI built with Bootstrap 5 and Bootstrap Icons

## Requirements

- Python 3.11+
- `etherwake` installed on the server (`apt install etherwake`)
- `fastapi`, `uvicorn`, `jinja2` (see below)

## Installation

```bash
pip install fastapi[standard]
```

## Running

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Sudo permissions

The `etherwake` command requires root. Drop the provided example file into sudoers:

```bash
sudo cp sudoers.example /etc/sudoers.d/wakelet
sudo visudo -cf /etc/sudoers.d/wakelet   # validate before use
```

Edit the file to replace `www-data` with the user your app runs as.

## SSH shutdown setup

Each target host needs a `wakelet` user configured to run `shutdown -h now` on SSH login. Use the provided setup script:

```bash
sudo ./example/setup_wakelet.sh /path/to/wakelet.pub
```

This will:
1. Create a locked `wakelet` user
2. Install the public key in `authorized_keys`
3. Add a `ForceCommand` block to `sshd_config` so any login immediately shuts the machine down
4. Reload `sshd`

Place your SSH private key at `private/wakelet` (this path is excluded from version control via `.gitignore`).

## Project structure

```
main.py                  FastAPI app and routes
services/
  hosts.py               SQLite CRUD for host records
  shell.py               Async shell command execution
  network.py             Auto-detect network interface
  validation.py          Hostname and MAC address validation
templates/
  index.html             Home page — host list and add form
  command_result.html    Output page for ping/wake/shutdown
static/
  bootstrap-5.3.8-dist/  Bootstrap CSS and JS
  bootstrap-icons-1.13.1/ Bootstrap Icons webfont
example/
  setup_wakelet.sh       Script to configure shutdown-on-login on target hosts
sudoers.example          Example sudoers entry for etherwake/ping
private/                 SSH private key (not committed)
hosts.db                 SQLite database (not committed)
```
