#!/bin/bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <domain> <email>"
  exit 1
fi

DOMAIN="$1"
EMAIL="$2"

sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
sudo cp deploy/nginx/decisionvault.conf /etc/nginx/sites-available/decisionvault.conf
sudo sed -i "s/server_name _;/server_name ${DOMAIN};/" /etc/nginx/sites-available/decisionvault.conf
sudo ln -sf /etc/nginx/sites-available/decisionvault.conf /etc/nginx/sites-enabled/decisionvault.conf
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect

echo "TLS setup complete. Set SLACK_REDIRECT_BASE_URL=https://${DOMAIN}"
