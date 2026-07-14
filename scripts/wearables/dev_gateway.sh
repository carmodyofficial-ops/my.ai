#!/usr/bin/env bash
# Isolated development instance of the app (with the wearables gateway) on
# 127.0.0.1:7100 INSIDE the odysseus container, without touching the
# production process. Pollers/background tasks disabled. The internal admin
# token is generated per-run and printed once (dev only — lets you mint
# pairing codes via: curl -X POST -H "X-Odysseus-Internal-Token: $TOK" \
#   -H "X-Odysseus-Owner: <admin-user>" http://127.0.0.1:7100/api/wearables/v1/pairings)
#
# Usage: dev_gateway.sh start|stop|status
set -eu
C=odysseus-odysseus-1
PATTERN="uvicorn app:app --host 127.0.0.1 --port 7100"

case "${1:-start}" in
  start)
    TOK=$(openssl rand -hex 32)
    docker exec -d "$C" sh -c "ODYSSEUS_INTERNAL_TOKEN=$TOK \
      ODYSSEUS_INPROCESS_POLLERS=0 ODYSSEUS_INPROCESS_TASKS=0 \
      python3 -m uvicorn app:app --host 127.0.0.1 --port 7100 \
      >/tmp/wearables_dev.log 2>&1"
    echo "starting on container-local 127.0.0.1:7100 (takes ~25s)..."
    for _ in $(seq 1 12); do
      sleep 5
      if docker exec "$C" curl -s -o /dev/null -w '%{http_code}' \
          http://127.0.0.1:7100/api/health | grep -q 200; then
        echo "up. internal dev token (shown once): $TOK"
        exit 0
      fi
    done
    echo "did not come up; check: docker exec $C tail -50 /tmp/wearables_dev.log" >&2
    exit 1
    ;;
  stop)
    # Exact-match the dev uvicorn command line only — NEVER a bare
    # "uvicorn app:app" (that pattern also matches the production PID 1 and
    # restarts the container).
    docker exec "$C" pkill -f "$PATTERN" || true
    echo "stopped (if running)"
    ;;
  status)
    docker exec "$C" pgrep -af "$PATTERN" || echo "not running"
    ;;
  *) echo "usage: $0 start|stop|status" >&2; exit 2 ;;
esac
