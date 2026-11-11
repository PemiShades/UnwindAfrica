# Unwind Africa single-service deployment

The website and native React Native app use one public deployment and one domain. Node is the public HTTP gateway; it starts Django/Gunicorn privately on loopback and streams all website pages, `/api/v1/` requests, media, uploads, cookies, and payment redirects to Django. Django remains the source of truth for member accounts, savings, orders, voting, and Paystack activity. The mobile app is a standalone iOS/Android client and talks to the same public origin; it is not served as a web app.

## Run locally

From the repository root, install the Django requirements and Node packages, then run `npm --prefix node-service start`. On Windows this starts Django's local development server and the Node gateway together. In the Linux production container the same launcher uses Gunicorn for Django.

Set `DJANGO_WORKDIR=.` and `DJANGO_INTERNAL_ORIGIN=http://127.0.0.1:8000`. The gateway listens on `PORT` (4100 locally); Render supplies its public port. Keep Django bound to loopback in production.

- All website routes and API routes pass through to Django, including `GET /api/v1/packages/` and authenticated write/payment endpoints.
- `GET /health` checks both Node and Django.

Payment secrets stay in Django's server environment and are never added to Node's public response or the mobile bundle. Render still needs a persistent PostgreSQL database and configured Paystack/email credentials.

## Production release checks

Before exposing the service, set `DEBUG=False`, a newly generated `SECRET_KEY`
(at least 50 random characters), the exact `ALLOWED_HOSTS` and HTTPS
`CSRF_TRUSTED_ORIGINS`, a persistent PostgreSQL `DATABASE_URL`, SMTP settings,
and matching live Paystack keys (`pk_live_...` / `sk_live_...`) in the server
environment. Keep media on persistent storage and back up both media and the
database. Do not copy the development `.env` or SQLite database to production.

Run `python manage.py migrate --noinput` and `python manage.py collectstatic
--noinput` as deployment steps before restarting the service. Configure the
Paystack dashboard webhook to `https://YOUR_DOMAIN/voting/webhook/paystack/`;
this endpoint verifies the signed event and reconciles voting and package
payments. The browser return callback also verifies directly with Paystack.

For native app builds, set `EXPO_PUBLIC_API_BASE_URL` to the same public HTTPS
origin. It defaults to `https://unwindafrica.com`; staging builds should set
their own origin explicitly.
