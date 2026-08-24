#!/usr/bin/env bash
# Usage: ./scripts/cert-selfsign.sh [domain]   (no root required)
set -euo pipefail

DOMAIN="${1:-localhost}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CERTS_DIR="$REPO_DIR/nginx/certs"

mkdir -p "$CERTS_DIR"

if [ -f "$CERTS_DIR/fullchain.pem" ]; then
    read -rp "$CERTS_DIR/fullchain.pem already exists, overwrite? [y/N] " ans
    case "$ans" in
        y|Y) ;;
        *) echo "Aborted"; exit 0 ;;
    esac
fi

openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
    -keyout "$CERTS_DIR/privkey.pem" \
    -out "$CERTS_DIR/fullchain.pem" \
    -subj "/CN=$DOMAIN" \
    -addext "subjectAltName=DNS:$DOMAIN" \
    2>/dev/null
chmod 600 "$CERTS_DIR/privkey.pem"

echo "Done: self-signed certificate (valid for 30 days) generated in $CERTS_DIR"
echo "Next: start the stack with 'docker compose up -d', then run scripts/certbot-issue.sh to switch to the real certificate"
