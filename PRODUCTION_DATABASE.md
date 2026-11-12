# Production PostgreSQL for Unwind Africa

## Application data layout

The public website, CMS, member dashboard, and native iOS/Android app use one Django database. The Node service is an HTTP gateway to Django; it does not keep a separate application database. PostgreSQL therefore stores all Django app data, including website content and events, admin accounts, member profiles and Rest Cards, packages and add-ons, package orders and payments, savings, campaigns, nominees, votes, and login challenges.

The app currently has migrations through `Web.0030` and `dashboard.0002`. `dashboard` models are proxies over the `Web` models, so they do not create duplicate dashboard tables. The deployed database must run every migration before the Node/Django service accepts traffic.

## Create the local-only PostgreSQL role and database

Run these commands on the RackNerd VPS. The role must not be a PostgreSQL superuser. Do not put its password in a command or commit it to Git.

```bash
sudo -u postgres psql
```

At the `postgres=#` prompt:

```sql
CREATE ROLE unwindafrica_user LOGIN;
```

Set a strong, unique password using psql's hidden password prompt:

```text
\password unwindafrica_user
```

Then create the database and defaults:

```sql
CREATE DATABASE unwindafrica_db OWNER unwindafrica_user ENCODING 'UTF8' TEMPLATE template0;
ALTER ROLE unwindafrica_user SET client_encoding TO 'UTF8';
ALTER ROLE unwindafrica_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE unwindafrica_user SET timezone TO 'UTC';
```

Exit with `\q`. Because the role owns this database, it can create and migrate the app tables without superuser privileges. Keep PostgreSQL listening on loopback (`127.0.0.1`) and do not open port `5432` in the public firewall.

Verify local password authentication from the VPS:

```bash
psql -h 127.0.0.1 -U unwindafrica_user -d unwindafrica_db -W -c "SELECT current_database(), current_user, current_setting('server_encoding');"
```

The result should show `unwindafrica_db`, `unwindafrica_user`, and `UTF8`.

## Configure Django on the VPS

In the production `.env` file beside `manage.py`, set:

```dotenv
DEBUG=False
DATABASE_URL=postgresql://unwindafrica_user:URL_ENCODED_PASSWORD@127.0.0.1:5432/unwindafrica_db
```

URL-encode reserved characters in the password (for example `@`, `:`, `/`, `#`, and `%`). Keep `.env` readable only by the service account (`chmod 600 .env`) and confirm `.env` remains ignored by Git. Never paste the real URL into chat, screenshots, logs, or source control.

`psycopg2-binary` and `dj-database-url` are already pinned in `requirements.txt`. Django now enables persistent connections with health checks, uses a short connection timeout, and automatically requires TLS for remote PostgreSQL URLs. Loopback PostgreSQL does not use TLS because traffic stays on the VPS. Production refuses a non-PostgreSQL database URL.

## Back up before changing the live database

If any live service already has customer, Rest Card, order, payment, or voting data, identify that database as the source of truth and take a verified backup before pointing the app at a new empty database. Do not overwrite or abandon the existing database. SQLite files and uploaded media are separate; a database export does not copy uploaded images or documents.

For an empty first deployment, create the schema from migrations:

```bash
cd /srv/unwindafrica
. .venv/bin/activate
python manage.py showmigrations --plan
python manage.py migrate --noinput
python manage.py check --deploy
```

Use the actual directory and virtual environment path used by the service. Verify the service starts, the health endpoint returns success, the website can read packages/events, and a member can sign in before switching production traffic. Create or retain a Django staff account through `python manage.py createsuperuser`; do not create it with SQL.

## Backups and maintenance

- Schedule a daily `pg_dump -Fc unwindafrica_db` and copy encrypted backups off the VPS. A backup on the same 35 GB disk is not sufficient.
- Retain multiple daily and weekly generations, restrict backup file permissions, and test a restore to a separate database before relying on the backup process.
- Back up `/app/media` or the configured `MEDIA_ROOT` separately; this contains uploaded package, event, and blog imagery.
- Monitor free disk space for PostgreSQL, media uploads, static files, logs, and backups. The advertised 35 GB SSD is shared by all of them.
- Keep PostgreSQL patched and restrict database access to the application account and local administrators.

`render.yaml` describes a separate Render deployment and its managed database. For the RackNerd VPS deployment, configure the RackNerd `.env` as above; do not copy Render's `DATABASE_URL` or create a second production database unless you are intentionally moving hosting providers.
