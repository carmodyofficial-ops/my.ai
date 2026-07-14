#!/usr/bin/env bash
# Mint a one-time wearables pairing code and print the JSON payload the
# Android app expects in its "Pairing payload JSON" field.
#
# Usage:  mint_pairing.sh [--publish]
#   --publish  Also write the payload to ~/apk-serve/pair.html so the phone
#              can copy it from https://<host>:8443/pair.html instead of
#              retyping it. The code is single-use and expires in 5 minutes,
#              but the page is unauthenticated on the LAN — it self-expires
#              (meta refresh shows a "stale" note) and you should still
#              `rm ~/apk-serve/pair.html` once paired.
#
# Auth: prompts for your my.ai username/password; the session cookie lives
# only in a mktemp cookie jar that is deleted on exit.
set -euo pipefail

# Default to the local TLS proxy: SECURE_COOKIES=true marks the session
# cookie Secure, and curl will not send Secure cookies over plain HTTP —
# minting via http://127.0.0.1:7001 fails auth on the second request.
BASE="${MYAI_BASE:-https://127.0.0.1:7443}"
PUBLISH=false
[[ "${1:-}" == "--publish" ]] && PUBLISH=true

read -r -p "my.ai username: " USERNAME
read -r -s -p "my.ai password: " PASSWORD; echo

JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT

login_status=$(curl -sk -o /dev/null -w "%{http_code}" -c "$JAR" \
  -H "Content-Type: application/json" \
  -d "$(python3 - "$USERNAME" "$PASSWORD" <<'PY'
import json, sys
print(json.dumps({"username": sys.argv[1], "password": sys.argv[2]}))
PY
)" "$BASE/api/auth/login")
if [[ "$login_status" != "200" ]]; then
  echo "Login failed (HTTP $login_status)" >&2
  exit 1
fi

RESP="$(curl -sk -b "$JAR" -X POST "$BASE/api/wearables/v1/pairings")"
PAYLOAD="$(python3 - "$RESP" <<'PY'
import json, sys
resp = json.loads(sys.argv[1])
if "payload" not in resp:
    sys.exit(f"unexpected response: {resp}")
print(json.dumps(resp["payload"], separators=(",", ":")))
PY
)"

echo
echo "Paste this into the app (expires in 5 min, single use):"
echo
echo "$PAYLOAD"
echo

if $PUBLISH; then
  PAGE=/home/youruser/apk-serve/pair.html
  QR="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("qr") or "")' "$RESP")"
  python3 - "$PAYLOAD" "$PAGE" "$QR" <<'PY'
import html, sys
payload, page, qr = sys.argv[1], sys.argv[2], sys.argv[3]
esc = html.escape(payload)
qr_block = (
    f'<div style="background:#fff;border-radius:14px;padding:14px;text-align:center">'
    f'<img src="{qr}" alt="pairing QR" style="max-width:100%"></div>'
    '<p>Open this page on the <b>desktop</b> and scan the QR with the app&rsquo;s '
    '<b>Scan pairing QR</b> button &mdash; or copy the payload below.</p>'
) if qr else ""
open(page, "w").write(f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>my.ai pairing payload</title>
<style>body{{font-family:system-ui;max-width:560px;margin:0 auto;padding:28px 20px;
background:#16161a;color:#e8e8e8}}textarea{{width:100%;height:110px;background:#0e0e12;
color:#e8e8e8;border:1px solid #2c2c35;border-radius:10px;padding:10px;font-size:12px}}
button{{background:#7c9cff;color:#0e0e12;border:0;border-radius:10px;padding:13px;
font-weight:600;width:100%;margin-top:10px}}</style></head><body>
<h2>Pairing payload</h2>
<p>Single use, expires 5 minutes after minting. Delete this page after pairing.</p>
{qr_block}
<textarea id="p" readonly>{esc}</textarea>
<button onclick="navigator.clipboard.writeText(document.getElementById('p').value)
.then(()=>this.textContent='Copied')">Copy payload</button>
</body></html>""")
PY
  echo "Published to https://$(hostname -I | awk '{print $1}'):8443/pair.html"
  echo "After pairing: rm $PAGE"
fi
