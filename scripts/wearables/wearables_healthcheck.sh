#!/usr/bin/env bash
# Wearables gateway health check. Safe to run any time; prints no secrets.
# Optional: WEARABLES_TOKEN=ody_... for the authenticated capability check.
set -u

PORT="${ODYSSEUS_PORT:-7001}"
BASE="http://127.0.0.1:${PORT}"
ok=0; fail=0

check() { # label, expected, actual
  if [ "$2" = "$3" ]; then echo "  OK   $1 ($3)"; ok=$((ok+1));
  else echo "  FAIL $1 (expected $2, got $3)"; fail=$((fail+1)); fi
}

echo "== my.ai wearables gateway health ($BASE) =="

app=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$BASE/api/health")
check "odysseus app liveness" 200 "$app"

unauth=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$BASE/api/wearables/v1/health")
check "gateway rejects unauthenticated" 401 "$unauth"

ollama=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:11434/api/tags")
check "ollama (LLM backend)" 200 "$ollama"

if [ -n "${WEARABLES_TOKEN:-}" ]; then
  caps=$(curl -s --max-time 10 -H "Authorization: Bearer $WEARABLES_TOKEN" \
    "$BASE/api/wearables/v1/capabilities")
  code=$?
  if [ $code -eq 0 ] && echo "$caps" | grep -q '"wearables_gateway"'; then
    echo "  OK   authenticated capabilities:"
    echo "$caps" | python3 -c '
import json,sys
d=json.load(sys.stdin)
for k in ("stt","tts","llm","vision"):
    v=d.get(k,{})
    print(f"         {k}: available={v.get(\"available\")} "
          f"{v.get(\"provider\") or v.get(\"model\") or \"\"}")'
    ok=$((ok+1))
  else
    echo "  FAIL authenticated capabilities (token rejected or gateway missing)"
    fail=$((fail+1))
  fi
else
  echo "  SKIP authenticated capability check (set WEARABLES_TOKEN=ody_...)"
fi

echo "== $ok ok, $fail failed =="
exit $((fail > 0))
