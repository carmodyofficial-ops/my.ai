#!/usr/bin/env bash
# Generate a self-signed TLS cert for the LAN proxy.
#
# No certificate authority and NO per-device install are required: each browser
# stores a one-time exception the first time it connects (the cert effectively
# "lives" in that browser). This encrypts all LAN traffic — protecting session
# cookies and passwords from passive sniffing on the Wi-Fi — at the cost of a
# one-time "your connection is not private -> proceed" click per browser, which
# is acceptable on a trusted home network.
#
# Usage:
#   MYAI_LAN_IP=192.168.1.50 scripts/gen_self_signed_cert.sh [out_dir]
set -euo pipefail
OUT_DIR="${1:-/home/youruser/odysseus/data}"
LAN_IP="${MYAI_LAN_IP:-192.168.1.50}"
HOSTS="${MYAI_TLS_HOSTS:-myai.local}"
CERT="$OUT_DIR/lan-cert.pem"
KEY="$OUT_DIR/lan-key.pem"

SAN="subjectAltName=IP:${LAN_IP},DNS:localhost"
for h in $HOSTS; do SAN="${SAN},DNS:${h}"; done

mkdir -p "$OUT_DIR"
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
  -keyout "$KEY" -out "$CERT" \
  -subj "/CN=my.ai LAN" -addext "$SAN"
chmod 600 "$KEY"
echo "wrote:"
echo "  cert: $CERT"
echo "  key : $KEY"
echo "  SAN : $SAN"
