#!/usr/bin/env bash
set -Eeuo pipefail

DOMAIN="unwindafrica.com"
WWW_DOMAIN="www.unwindafrica.com"
APP_ROOT="/srv/unwindafrica"
SERVICE="unwindafrica"
UPSTREAM="127.0.0.1:8001"
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
SITE_AVAILABLE="/etc/nginx/sites-available/unwindafrica-managed.conf"
SITE_ENABLED="/etc/nginx/sites-enabled/000-unwindafrica-managed.conf"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/var/backups/unwindafrica-deploy/${STAMP}"

log() { printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || fail "Run this script through sudo on the Ubuntu VPS."
[[ -d "$APP_ROOT" && -f "$APP_ROOT/manage.py" ]] || fail "Django project not found at $APP_ROOT. Update APP_ROOT in this script if your install path differs."
command -v nginx >/dev/null || fail "Nginx is not installed. Install it first, then rerun this script."
command -v curl >/dev/null || fail "curl is required for the preflight checks."
systemctl is-active --quiet "$SERVICE" || fail "The $SERVICE systemd service is not active. Start/fix Gunicorn before configuring Nginx."
[[ -r "${CERT_DIR}/fullchain.pem" && -r "${CERT_DIR}/privkey.pem" ]] || fail "Let's Encrypt certificate files are missing under $CERT_DIR. Obtain the domain certificate first."
[[ -r /etc/letsencrypt/options-ssl-nginx.conf && -r /etc/letsencrypt/ssl-dhparams.pem ]] \
  || fail "Certbot's Nginx TLS options are missing. Check the certificate installation before rerunning."

log "Checking the live Gunicorn upstream on $UPSTREAM"
curl --connect-timeout 3 --max-time 10 -fsS -H "Host: ${DOMAIN}" "http://${UPSTREAM}/healthz" >/dev/null \
  || fail "Gunicorn health check failed at http://${UPSTREAM}/healthz. No Nginx changes were made."
curl --connect-timeout 3 --max-time 10 -fsS -H "Host: ${DOMAIN}" "http://${UPSTREAM}/api/v1/packages/" >/dev/null \
  || fail "Package API preflight failed at Gunicorn. No Nginx changes were made."

log "Preparing static and media directories"
SERVICE_USER="$(systemctl show "$SERVICE" --property=User --value)"
SERVICE_USER="${SERVICE_USER:-root}"
id "$SERVICE_USER" >/dev/null 2>&1 || fail "Could not resolve systemd service user '$SERVICE_USER'."
STATIC_ROOT="${APP_ROOT}/staticfiles"
MEDIA_ROOT="${APP_ROOT}/media"

PYTHON=""
EXEC_START="$(systemctl show "$SERVICE" --property=ExecStart --value)"
GUNICORN_PATH="$(printf '%s' "$EXEC_START" | sed -n 's/.*path=\([^ ;]*\).*/\1/p')"
for candidate in "$(dirname "${GUNICORN_PATH:-/nonexistent}")/python" "${APP_ROOT}/.venv/bin/python" "${APP_ROOT}/.venv/bin/python3" "${APP_ROOT}/venv/bin/python" "${APP_ROOT}/venv/bin/python3"; do
  if [[ -x "$candidate" ]]; then PYTHON="$candidate"; break; fi
done
[[ -n "$PYTHON" ]] || PYTHON="$(command -v python3 || true)"
[[ -n "$PYTHON" ]] || fail "Python 3 was not found."

install -d -o "$SERVICE_USER" -g "$(id -gn "$SERVICE_USER")" "$MEDIA_ROOT"
log "Collecting Django static files"
sudo -u "$SERVICE_USER" -H bash -c 'cd "$1" && "$2" manage.py collectstatic --noinput' _ "$APP_ROOT" "$PYTHON" \
  || fail "collectstatic failed. Nginx configuration has not been changed."
install -d "$STATIC_ROOT"

if ! command -v setfacl >/dev/null; then
  log "Installing Ubuntu ACL support for read-only Nginx access to public assets"
  apt-get install -y acl || fail "Could not install acl. Install it with 'sudo apt-get install acl' and rerun."
fi
NGINX_USER="$(ps -o user= -C nginx 2>/dev/null | awk '$1 != "root" {print $1; exit}')"
NGINX_USER="${NGINX_USER:-www-data}"
id "$NGINX_USER" >/dev/null 2>&1 || fail "Could not resolve Nginx worker user '$NGINX_USER'."
setfacl -m "u:${NGINX_USER}:--x" "$APP_ROOT"
setfacl -R -m "u:${NGINX_USER}:rX" "$STATIC_ROOT" "$MEDIA_ROOT"
find "$MEDIA_ROOT" -type d -exec setfacl -m "d:u:${NGINX_USER}:rX" {} +

log "Backing up Nginx configuration"
install -d -m 700 "$BACKUP_DIR"
cp -a /etc/nginx "$BACKUP_DIR/nginx"
if [[ -e "$SITE_AVAILABLE" || -L "$SITE_AVAILABLE" ]]; then
  cp -a "$SITE_AVAILABLE" "$BACKUP_DIR/previous-site-available"
fi
if [[ -e "$SITE_ENABLED" || -L "$SITE_ENABLED" ]]; then
  cp -a "$SITE_ENABLED" "$BACKUP_DIR/previous-site-enabled"
fi

log "Installing the Unwind Africa Nginx site"
cat >"$SITE_AVAILABLE" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} ${WWW_DOMAIN};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${DOMAIN} ${WWW_DOMAIN};

    ssl_certificate ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 20m;

    location ^~ /static/ {
        alias ${STATIC_ROOT}/;
        access_log off;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location ^~ /media/ {
        alias ${MEDIA_ROOT}/;
        access_log off;
    }

    location / {
        proxy_pass http://${UPSTREAM};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_connect_timeout 5s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_redirect off;
    }
}
EOF
chmod 644 "$SITE_AVAILABLE"
ln -sfn "$SITE_AVAILABLE" "$SITE_ENABLED"

if ! nginx -t; then
  log "Nginx validation failed; restoring the managed site files"
  rm -f "$SITE_ENABLED" "$SITE_AVAILABLE"
  [[ -e "$BACKUP_DIR/previous-site-available" ]] && cp -a "$BACKUP_DIR/previous-site-available" "$SITE_AVAILABLE" || true
  [[ -e "$BACKUP_DIR/previous-site-enabled" ]] && cp -a "$BACKUP_DIR/previous-site-enabled" "$SITE_ENABLED" || true
  exit 1
fi

log "Reloading Nginx"
systemctl reload nginx

log "Verifying the HTTPS routes locally through Nginx"
curl --connect-timeout 5 --max-time 20 -fsS --resolve "${DOMAIN}:443:127.0.0.1" "https://${DOMAIN}/healthz" >/dev/null \
  || fail "Nginx is active, but the HTTPS health route failed. See $BACKUP_DIR/nginx for the configuration backup."
curl --connect-timeout 5 --max-time 20 -fsS --resolve "${DOMAIN}:443:127.0.0.1" "https://${DOMAIN}/api/v1/packages/" >/dev/null \
  || fail "Nginx is active, but the HTTPS package API route failed. See $BACKUP_DIR/nginx for the configuration backup."

log "Nginx now routes ${DOMAIN} and ${WWW_DOMAIN} to Gunicorn at ${UPSTREAM}."
log "Configuration backup: ${BACKUP_DIR}/nginx"
log "Next: verify from your browser, and separately finish production email and live Paystack credentials before relying on those services."
