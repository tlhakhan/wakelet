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
- `fastapi[standard]`

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
pip install fastapi[standard]
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

The file already names `wakelet` as the permitted user. If the path to `etherwake` differs on your system, update it first:

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
- `private/wakelet` — private key used by the app to SSH into target hosts
- `private/wakelet.pub` — public key to be deployed to each target host

The `private/` directory is excluded from version control via `.gitignore`.

---

## Running

```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
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
main.py                  FastAPI app and routes
services/
  hosts.py               SQLite CRUD for host records
  shell.py               Async shell command execution
  network.py             Auto-detect network interface
  validation.py          Hostname and MAC address validation
templates/
  index.html             Home page — host list and add form
  command_result.html    Output page for ping/wake/shutdown
static/vendor/
  bootstrap-5.3.8-dist/  Bootstrap CSS and JS
  bootstrap-icons-1.13.1/ Bootstrap Icons webfont
example/
  setup_wakelet.sh       Script to configure shutdown-on-login on target hosts
  sudoers.example        Sudoers entry for etherwake
private/                 SSH key pair (not committed)
hosts.db                 SQLite database (not committed)
```
