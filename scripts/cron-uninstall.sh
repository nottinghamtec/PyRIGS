#!/usr/bin/env bash
# Uninstall the scheduled tasks installed by cron-install.sh (run as root on the deployment server)
# Usage: sudo ./scripts/cron-uninstall.sh
set -euo pipefail

CERTBOT_CRON="/etc/cron.d/pyrigs-certbot"
DJANGO_CRON="/etc/cron.d/pyrigs-django"
HOOK_PATH="/etc/letsencrypt/renewal-hooks/deploy/pyrigs-deploy.sh"

rm -f "$CERTBOT_CRON" "$DJANGO_CRON"
echo "Removed scheduled tasks: $CERTBOT_CRON $DJANGO_CRON"

if [ -f "$HOOK_PATH" ]; then
    read -rp "Also remove the deploy-hook ($HOOK_PATH)? [y/N] " ans
    case "$ans" in
        y|Y) rm -f "$HOOK_PATH"; echo "Deploy-hook removed" ;;
        *)   echo "Deploy-hook kept" ;;
    esac
fi
