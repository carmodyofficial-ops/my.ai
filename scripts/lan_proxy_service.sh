#!/usr/bin/env bash
# Launcher used by myai-lan-proxy.service. Builds args from environment (set them
# in ~/.config/myai-lan-proxy.env) and execs scripts/lan_proxy.py.
#
# Default: a plain relay on 0.0.0.0:7000 -> 127.0.0.1:7000 (matches the existing
# host-proxy posture, but survives reboot/DHCP because it binds 0.0.0.0).
# To switch to TLS: set MYAI_TLS_CERT + MYAI_TLS_KEY (and usually
# MYAI_LISTEN_PORT=7443) in the env file, then restart the service.
set -euo pipefail
REPO="${MYAI_REPO:-/home/youruser/odysseus}"

if [ -z "${MYAI_LISTEN_HOST:-}" ]; then
  MYAI_LISTEN_HOST="$(hostname -I 2>/dev/null | awk '{print $1}')"
  MYAI_LISTEN_HOST="${MYAI_LISTEN_HOST:-127.0.0.1}"
fi

args=(
  --listen-host "${MYAI_LISTEN_HOST}"
  --target-host "${MYAI_TARGET_HOST:-127.0.0.1}"
  --target-port "${MYAI_TARGET_PORT:-7000}"
)
if [[ -n "${MYAI_TLS_CERT:-}" && -n "${MYAI_TLS_KEY:-}" ]]; then
  args+=(--listen-port "${MYAI_LISTEN_PORT:-7443}" --tls-cert "$MYAI_TLS_CERT" --tls-key "$MYAI_TLS_KEY")
else
  args+=(--listen-port "${MYAI_LISTEN_PORT:-7000}")
fi


exec python3 "$REPO/scripts/lan_proxy.py" "${args[@]}"
