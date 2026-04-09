#!/usr/bin/env bash
# setup_wakelet.sh — Create an SSH user that shuts down the machine on login.
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
SSHD_CONFIG="/etc/ssh/sshd_config"
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

info "Setting up shutdown-on-login user: ${USERNAME}"

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
  # Validate the sudoers file before proceeding
  visudo -cf "$SUDOERS_FILE" || die "sudoers syntax check failed — aborting."
  ok "sudoers entry written to ${SUDOERS_FILE}."
fi

# ── 3. SSH authorized_keys ─────────────────────────────────────────────────────
SSH_DIR="/home/${USERNAME}/.ssh"
AUTH_KEYS="${SSH_DIR}/authorized_keys"

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

PUBKEY_CONTENT="$(cat "$PUBKEY_FILE")"

# Add key only if not already present
if [[ -f "$AUTH_KEYS" ]] && grep -qF "$PUBKEY_CONTENT" "$AUTH_KEYS"; then
  ok "Public key already in authorized_keys — skipping."
else
  echo "$PUBKEY_CONTENT" >> "$AUTH_KEYS"
  ok "Public key added to ${AUTH_KEYS}."
fi

chmod 600 "$AUTH_KEYS"
chown -R "${USERNAME}:${USERNAME}" "$SSH_DIR"

# ── 4. sshd_config Match block ─────────────────────────────────────────────────
MATCH_MARKER="# BEGIN wakelet-block:${USERNAME}"
MATCH_END_MARKER="# END wakelet-block:${USERNAME}"

if grep -qF "$MATCH_MARKER" "$SSHD_CONFIG"; then
  ok "sshd_config Match block for '${USERNAME}' already present — skipping."
else
  # Append the Match block
  cat >> "$SSHD_CONFIG" <<EOF

${MATCH_MARKER}
Match User ${USERNAME}
    ForceCommand sudo ${SHUTDOWN_BIN} -h now
    PermitTTY no
    X11Forwarding no
    AllowAgentForwarding no
    AllowTcpForwarding no
${MATCH_END_MARKER}
EOF
  ok "Match block appended to ${SSHD_CONFIG}."
fi

# ── 5. Validate and reload sshd ────────────────────────────────────────────────
info "Validating sshd config..."
sshd -t || die "sshd config validation failed — review ${SSHD_CONFIG}."
ok "sshd config is valid."

info "Reloading sshd..."
systemctl reload ssh
ok "sshd reloaded."

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────"
echo " Setup complete for user: ${USERNAME}"
echo " Connect with:  ssh ${USERNAME}@<machine-ip>"
echo " Effect:        machine will shut down immediately"
echo "────────────────────────────────────────────────"