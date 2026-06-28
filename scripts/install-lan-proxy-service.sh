#!/usr/bin/env bash
# Install + enable the my.ai LAN proxy as a *user* systemd service that survives
# logout and reboot. Run as your normal login user.
#
# Before running: stop any existing hand-started LAN proxy (it would collide on
# the listen port), e.g.:
#   kill "$(cat /home/youruser/odysseus/data/projectforge_sme/agent_capability/runtime/h2u_e4_lan_proxy.pid)"
set -euo pipefail
REPO="${MYAI_REPO:-/home/youruser/odysseus}"
UNIT_DIR="${HOME}/.config/systemd/user"

mkdir -p "$UNIT_DIR"
install -m 644 "$REPO/deploy/myai-lan-proxy.service" "$UNIT_DIR/myai-lan-proxy.service"
chmod +x "$REPO/scripts/lan_proxy_service.sh" "$REPO/scripts/lan_proxy.py"

# Let user services run without an active login session (so it comes back on boot).
sudo loginctl enable-linger "$USER" || echo "NOTE: run 'sudo loginctl enable-linger $USER' manually if that failed"

systemctl --user daemon-reload
systemctl --user enable --now myai-lan-proxy.service
systemctl --user --no-pager status myai-lan-proxy.service || true
echo
echo "Done. Logs: journalctl --user -u myai-lan-proxy -f"
