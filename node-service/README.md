# Unwind Africa single-service deployment

The website and native React Native app use one public deployment and one domain. Node is the public HTTP gateway; it starts Django/Gunicorn privately on loopback and streams all website pages, `/api/v1/` requests, media, uploads, cookies, and payment redirects to Django. Django remains the source of truth for member accounts, savings, orders, voting, and Paystack activity. The mobile app is a standalone iOS/Android client and talks to the same public origin; it is not served as a web app.

## Run locally

From the repository root, install the Django requirements and Node packages, then run `npm --prefix node-service start`. On Windows this starts Django's local development server and the Node gateway together. In the Linux production container the same launcher uses Gunicorn for Django.

Set `DJANGO_WORKDIR=.` and `DJANGO_INTERNAL_ORIGIN=http://127.0.0.1:8000`. The gateway listens on `PORT` (4100 locally); Render supplies its public port. Keep Django bound to loopback in production.

- All website routes and API routes pass through to Django, including `GET /api/v1/packages/` and authenticated write/payment endpoints.
- `GET /health` checks both Node and Django.

Payment secrets stay in Django's server environment and are never added to Node's public response or the mobile bundle. Render still needs a persistent PostgreSQL database and configured Paystack/email credentials.
