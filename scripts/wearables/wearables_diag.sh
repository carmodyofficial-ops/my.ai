#!/usr/bin/env bash
# Redacted wearables diagnostic bundle. Contains NO secrets, NO prompt or
# conversation content — safe to share. Output: /tmp/wearables_diag_<ts>.txt
set -u
OUT="/tmp/wearables_diag_$(date +%Y%m%d_%H%M%S).txt"
PORT="${ODYSSEUS_PORT:-7001}"

# Redact anything token-shaped, just in case a log line ever carries one.
redact() { sed -E 's/(ody_|wpair_)[A-Za-z0-9_-]+/\1<REDACTED>/g'; }

{
  echo "== my.ai wearables diagnostics $(date -Is) =="
  echo; echo "-- compose services --"
  docker compose ps 2>/dev/null | redact
  echo; echo "-- endpoint status codes (loopback) --"
  for p in "/api/health" "/api/wearables/v1/health"; do
    printf "%-30s %s\n" "$p" \
      "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:${PORT}${p})"
  done
  printf "%-30s %s\n" "ollama /api/tags" \
    "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:11434/api/tags)"
  echo; echo "-- installed models (names/sizes only) --"
  curl -s --max-time 5 http://127.0.0.1:11434/api/tags | python3 -c '
import json,sys
try:
    for m in json.load(sys.stdin).get("models", []):
        print("  %s  %.1f GB" % (m["name"], m.get("size", 0) / 1e9))
except Exception as e:
    print("  unavailable:", e)'
  echo; echo "-- recent gateway log lines (metadata-only by design) --"
  docker logs --since 2h odysseus-odysseus-1 2>&1 | grep '\[wearables\]' | tail -40 | redact
  echo; echo "-- recent gateway errors --"
  docker logs --since 24h odysseus-odysseus-1 2>&1 \
    | grep -E 'wearables.*(ERROR|WARNING)' | tail -20 | redact
  echo; echo "-- speech settings (providers only) --"
  python3 -c '
import json
try:
    d = json.load(open("data/settings.json"))
    for k in ("stt_provider","stt_model","tts_provider","tts_voice","wearables_vision_model"):
        print(f"  {k} = {d.get(k)!r}")
except Exception as e:
    print("  unavailable:", e)'
  echo; echo "== end =="
} > "$OUT" 2>&1

echo "wrote $OUT"
