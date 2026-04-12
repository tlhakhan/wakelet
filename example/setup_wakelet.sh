#!/usr/bin/env bash
# setup_wakelet.sh — Create a restricted SSH user that shuts down the machine.
# Idempotent: safe to run multiple times.
#
# Usage:
#   sudo ./setup_wakelet.sh /path/to/pubkey.pub
#   sudo ./setup_wakelet.sh /path/to/pubkey.pub myusername
#
# Arguments:
#   $1  Path to the SSH public key file (required)
#   $2  Username to create (optional, default: wakelet)

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
PUBKEY_FILE="${1:-}"
USERNAME="${2:-wakelet}"
SUDOERS_FILE="/etc/sudoers.d/${USERNAME}"
SHUTDOWN_BIN="/sbin/shutdown"
# ──────────────────────────────────────────────────────────────────────────────

# ── Helpers ───────────────────────────────────────────────────────────────────
info()  { echo "[INFO]  $*"; }
ok()    { echo "[OK]    $*"; }
die()   { echo "[ERROR] $*" >&2; exit 1; }
# ──────────────────────────────────────────────────────────────────────────────

# ── Preflight checks ──────────────────────────────────────────────────────────
[[ $EUID -eq 0 ]]        || die "Must be run as root (use sudo)."
[[ -n "$PUBKEY_FILE" ]]  || die "Usage: $0 /path/to/pubkey.pub [username]"
[[ -f "$PUBKEY_FILE" ]]  || die "Public key file not found: $PUBKEY_FILE"
[[ -x "$SHUTDOWN_BIN" ]] || die "shutdown binary not found at $SHUTDOWN_BIN"

# Validate it looks like an SSH public key
grep -qE '^(ssh-|ecdsa-|sk-)' "$PUBKEY_FILE" \
  || die "File does not appear to be a valid SSH public key: $PUBKEY_FILE"
# ──────────────────────────────────────────────────────────────────────────────

info "Setting up shutdown user: ${USERNAME}"

# ── 1. Create user ─────────────────────────────────────────────────────────────
if id "$USERNAME" &>/dev/null; then
  ok "User '${USERNAME}' already exists — skipping useradd."
else
  useradd -m -s /bin/bash "$USERNAME"
  ok "Created user '${USERNAME}'."
fi

# Lock password login (idempotent — passwd -l is safe to repeat)
passwd -l "$USERNAME" &>/dev/null
ok "Password login locked for '${USERNAME}'."

# ── 2. Sudoers entry ───────────────────────────────────────────────────────────
SUDOERS_LINE="${USERNAME} ALL=(ALL) NOPASSWD: ${SHUTDOWN_BIN} -h now"

if [[ -f "$SUDOERS_FILE" ]] && grep -qF "$SUDOERS_LINE" "$SUDOERS_FILE"; then
  ok "sudoers entry already present — skipping."
else
  echo "$SUDOERS_LINE" > "$SUDOERS_FILE"
  chmod 440 "$SUDOERS_FILE"
  visudo -cf "$SUDOERS_FILE" || die "sudoers syntax check failed — aborting."
  ok "sudoers entry written to ${SUDOERS_FILE}."
fi

# ── 3. SSH authorized_keys with forced command ────────────────────────────────
SSH_DIR="/home/${USERNAME}/.ssh"
AUTH_KEYS="${SSH_DIR}/authorized_keys"

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

PUBKEY_CONTENT="$(cat "$PUBKEY_FILE")"
FORCED_KEY="command=\"sudo ${SHUTDOWN_BIN} -h now\",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ${PUBKEY_CONTENT}"

# Add key only if not already present
if [[ -f "$AUTH_KEYS" ]] && grep -qF "$PUBKEY_CONTENT" "$AUTH_KEYS"; then
  ok "Public key already in authorized_keys — skipping."
else
  echo "$FORCED_KEY" >> "$AUTH_KEYS"
  ok "Public key with forced command added to ${AUTH_KEYS}."
fi

chmod 600 "$AUTH_KEYS"
chown -R "${USERNAME}:${USERNAME}" "$SSH_DIR"

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────"
echo " Setup complete for user: ${USERNAME}"
echo " Connect with:  ssh ${USERNAME}@<machine-ip>"
echo " Effect:        machine will shut down immediately"
echo "────────────────────────────────────────────────"