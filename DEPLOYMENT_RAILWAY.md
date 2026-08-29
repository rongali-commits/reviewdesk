# Railway deployment

## Service setup

1. Create a private GitHub repository and connect it to a new Railway service.
2. Railway detects the included Dockerfile.
3. Add a persistent volume mounted at `/app/runtime`.
4. Generate a Railway domain and copy its HTTPS URL.
5. Add the environment variables below.

## Required production variables

```text
APP_ENV=production
ADMIN_TOKEN=<at least 24 random characters>
WEBHOOK_TOKEN=<a different random value>
DATABASE_PATH=/app/runtime/reviewdesk.db
EMAIL_PROVIDER=demo
REQUEST_WORKER_ENABLED=true
REQUEST_POLL_SECONDS=60
SEED_DEMO_DATA=true
PUBLIC_BASE_URL=https://YOUR-RAILWAY-DOMAIN
```

For the public sales demo, keep `EMAIL_PROVIDER=demo` and `SEED_DEMO_DATA=true`. For a buyer production instance, set `SEED_DEMO_DATA=false`, attach the buyer's approved SMTP variables, and begin with a fresh persistent database.

## SMTP variables

```text
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.provider.example
SMTP_PORT=587
SMTP_USERNAME=<provider username>
SMTP_PASSWORD=<provider secret>
SMTP_USE_TLS=true
```

## Verification

1. Open `/health` and confirm storage is `ok`.
2. Open `/` and submit the non-persistent demo.
3. Open `/admin` and verify read-only demo access.
4. Use the private token to add one controlled test customer.
5. Confirm the first request, feedback submission, suppression, and public handoff.

