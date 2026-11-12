# Finish Nginx routing on the RackNerd VPS

## One-run setup from Windows

From the `UnwindAfrica` project folder on your Windows computer, run `deploy-racknerd.bat`. Enter the VPS SSH destination when prompted (for example, `root@192.236.188.32`). Windows OpenSSH (`ssh` and `scp`) must be enabled, and your SSH account must be allowed to run `sudo` on Ubuntu.

The launcher uploads `ops/deploy_racknerd.sh` to `/tmp` and runs it on Ubuntu. It checks the existing Gunicorn service, HTTPS certificate, Django health route, and package API before changing Nginx. It then collects static files, grants the Nginx worker read-only access to static/media files, backs up `/etc/nginx`, installs the site config, validates it with `nginx -t`, reloads Nginx, and checks the HTTPS routes through localhost. If preflight checks fail, it exits before changing Nginx. The backup is kept under `/var/backups/unwindafrica-deploy/`.

This automates the Nginx and static-file setup only. It does not change `.env`, rotate credentials, or supply SMTP/Paystack secrets; those remain private server settings and must be configured separately as described below. The script expects the app at `/srv/unwindafrica`, the systemd service `unwindafrica`, Gunicorn on `127.0.0.1:8001`, and the existing Certbot certificate for `unwindafrica.com`.

## Current public status

Checked from outside the VPS on 12 November 2026:

- `https://unwindafrica.com/` returns `200` from Nginx over HTTPS.
- `https://unwindafrica.com/health` and `/api/v1/packages/` currently return Nginx `404`.
- DNS for the root and `www` currently resolves to `192.236.188.32`.

This means HTTPS is working and the public Nginx site is answering, but its HTTPS server block is not yet forwarding app routes to Django. The supplied VPS check confirms Django/Gunicorn is listening privately on `127.0.0.1:8001`.

## Before changing Nginx

On the VPS, first confirm the service and upstream:

```bash
sudo systemctl status unwindafrica --no-pager
curl -i http://127.0.0.1:8001/healthz
curl -i -H 'Host: unwindafrica.com' http://127.0.0.1:8001/api/v1/packages/
```

`/healthz` should return `200` only when Django can connect to its configured database. The package API should return JSON (an empty list is still a valid response). If either request fails locally, fix the Gunicorn/Django/database service before editing Nginx.

Back up the active site file with a unique timestamp so an earlier backup is not overwritten:

```bash
sudo cp -a /etc/nginx/sites-available/default "/etc/nginx/sites-available/default.backup.$(date +%Y%m%d-%H%M%S)"
```

Find the enabled HTTPS server block for `unwindafrica.com` and preserve its existing `listen 443 ssl`, `server_name`, certificate paths, and Certbot-managed settings. In that server block, remove the old `location / { try_files ... }` block and put the contents of `ops/nginx/unwindafrica-locations.conf` directly inside the server block. The three `location` blocks must be siblings; do not put them inside another location. Keep the HTTP-to-HTTPS redirect block as it is.

The include file uses the paths in this repo when the app root is `/srv/unwindafrica`: `STATIC_ROOT=/srv/unwindafrica/staticfiles` and `MEDIA_ROOT=/srv/unwindafrica/media`. If the server uses a different app root or sets either environment variable to a different path, adjust the Nginx aliases to match.

## Collect assets and allow Nginx to read only public files

Run `collectstatic` as the same Unix account used by Gunicorn, then check which account Nginx workers use:

```bash
cd /srv/unwindafrica
sudo systemctl show unwindafrica --property=User --value
ps -o user= -C nginx | sort -u
```

On Ubuntu, Nginx workers commonly use `www-data`. Confirm this on the VPS before applying ACLs. If `setfacl` is missing, install the `acl` package. Grant Nginx traversal on the project directory and read access only to static and public media trees; do not grant access to `.env`:

```bash
sudo setfacl -m u:www-data:--x /srv/unwindafrica
sudo setfacl -R -m u:www-data:rX /srv/unwindafrica/staticfiles /srv/unwindafrica/media
sudo setfacl -R -d -m u:www-data:rX /srv/unwindafrica/media
```

If Nginx runs as a different user, replace `www-data` with the confirmed worker user. Reapply the static-files ACL after future `collectstatic` deployments. The parent-directory ACL grants traversal only; it does not grant permission to read `.env`.

## Validate and reload

After editing the active site file:

```bash
sudo nginx -t
```

Only reload if the test reports syntax is OK and the test is successful:

```bash
sudo systemctl reload nginx
```

Then verify the public routes:

```bash
curl -i https://unwindafrica.com/healthz
curl -i https://unwindafrica.com/api/v1/packages/
curl -I https://unwindafrica.com/
```

Expected: health `200`, package API `200` with JSON, and homepage `200` with the Django page. The native app uses the same HTTPS `/api/v1/` endpoints.

## Quick diagnosis

- `502 Bad Gateway`: Gunicorn is stopped, not on port 8001, or not reachable on loopback.
- Django `400 Bad Request`: include `unwindafrica.com` and `www.unwindafrica.com` in the VPS `ALLOWED_HOSTS`.
- HTTPS redirect loop: ensure Nginx sends `X-Forwarded-Proto $scheme`; Django already trusts that header.
- Django CSRF `403`: include both HTTPS origins in `CSRF_TRUSTED_ORIGINS`.
- Static `403`: check the Nginx worker account and ACLs; do not make `.env` readable by Nginx.

The repository's Node gateway is optional for this specific layout. Nginx can send both website and app API traffic directly to the single Django/Gunicorn service on port 8001; no second database or separate API origin is required.

## Production environment and credential rotation

The production `.env` must have one assignment per setting. Use the final domain values from `ops/env.production.example`; remove duplicate old lines so there is no ambiguity. Set `DEBUG=False` before serving the public domain. Leave `USE_CONSOLE_EMAIL=True` only for local development; production login codes and payment notices require working SMTP credentials and `USE_CONSOLE_EMAIL=False`. Replace Paystack placeholders with the live keys before accepting production payments.

Credentials were pasted into a support conversation while troubleshooting. Treat the Django `SECRET_KEY` and PostgreSQL password as exposed and rotate both before production traffic:

1. Generate a new database password on the VPS with `openssl rand -hex 32` and keep it in that private terminal.
2. Open `sudo -u postgres psql`, run `\password unwindafrica_user`, and enter the new value at psql's hidden prompts.
3. Generate a new Django key with `python3 -c 'import secrets; print(secrets.token_urlsafe(64))'`.
4. Use `sudoedit /srv/unwindafrica/.env` to set the new key and password, `DEBUG=False`, the canonical host/origin lists, and the correct email/payment settings. The hex database password is safe to place directly in the connection URL.
5. Set the `.env` owner to the existing Gunicorn service account and restrict it to mode `600`; confirm the service account can read it. Do not make it readable by Nginx.
6. Restart the existing service and check `sudo journalctl -u unwindafrica -n 100 --no-pager` for startup/database errors.

Do not send the rotated values back. If payment/email production credentials are not ready yet, keep real payments disabled and complete SMTP setup before expecting sign-in codes to arrive.
