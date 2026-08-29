# ReviewDesk

ReviewDesk is a white-label customer feedback and review-request system for local businesses. It sends a configurable three-step email sequence, collects honest private feedback, offers every customer the same public-review handoff, and turns permissioned responses into an embeddable testimonial wall.

The included fictional **Northstar Auto Care** experience is a ready-to-use sales demo. Replace every sample identity, contact detail, service, claim, and link with buyer-approved information before launch.

## Why this product is sellable

- It solves a visible business problem: satisfied customers often leave without reviewing.
- Local reviews influence trust, discovery, and buying decisions.
- Buyers can understand the value in under a minute.
- The system is self-hosted and has no per-location software subscription.
- Agencies can white-label it for auto care, home services, clinics, salons, hospitality, and other local niches.
- It complements LeadDesk and FollowDesk without duplicating either product.

## Included features

- Branded, mobile-first customer feedback page
- One-time private request links for genuine customers
- Three-step email reminder sequence with editable timing and copy
- Automatic reminder suppression after a response
- Demo email provider for safe marketplace demonstrations
- Production SMTP support
- Customer list, request funnel, response metrics, and activity timeline
- CSV customer import and formula-safe CSV export
- Private feedback library with explicit testimonial consent
- Admin approval before any testimonial is displayed
- Public testimonial wall and one-script website widget
- Neutral public review handoff shown to every customer, regardless of rating
- Generic completed-job webhook for CRM and automation tools
- Token-protected admin dashboard and separate webhook token
- Docker, Railway, and standard Python deployment options
- Tests, client intake, fulfillment, QA, and marketplace copy

## Quick start

Python 3.11 or newer is required.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
$env:ADMIN_TOKEN="choose-a-private-admin-token"
$env:WEBHOOK_TOKEN="choose-a-separate-webhook-token"
uvicorn reviewdesk.app:app --reload
```

Open:

- Customer experience: `http://127.0.0.1:8000/`
- Admin dashboard: `http://127.0.0.1:8000/admin`
- Testimonial wall: `http://127.0.0.1:8000/wall`
- Health check: `http://127.0.0.1:8000/health`

The development admin token is `development-admin-token`. Never use it for a public deployment.

## Safe demonstration mode

`EMAIL_PROVIDER=demo` records due requests without transmitting email. `SEED_DEMO_DATA=true` creates fictional dashboard records and enables the read-only public demo token. Customer submissions on the root demo page are intentionally not stored.

For a buyer deployment:

1. Set `SEED_DEMO_DATA=false`.
2. Use strong, different admin and webhook tokens.
3. Replace the business configuration.
4. Add the business's official review-page URL.
5. Connect an approved SMTP provider and verified sending domain.
6. Obtain customer consent and review the applicable privacy and review-platform rules.

## Policy-safe review collection

ReviewDesk is deliberately designed without review gating:

- every genuine customer receives the same request;
- every rating is accepted as private feedback;
- the public review option is shown after every rating;
- no incentives or suggested rating are offered;
- testimonials require explicit customer consent and admin approval.

The buyer remains responsible for its review-platform, privacy, email, and industry obligations. The included documentation is operational guidance, not legal advice.

## Website widget

After deployment, add the following where testimonials should appear:

```html
<script async src="https://YOUR-REVIEWDESK-DOMAIN.example/widget.js" data-height="250px"></script>
```

The script creates a lazy-loaded iframe. It does not expose the admin or webhook token.

## Completed-job webhook

Send a completed customer record to:

```text
POST /api/webhooks/customers
X-Webhook-Token: your-private-webhook-token
```

Supported event names are `customer.completed`, `job.completed`, and `invoice.paid`. See [INTEGRATIONS.md](INTEGRATIONS.md) for the payload.

## Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `APP_ENV` | Production | Enables strict secret validation when set to `production` |
| `ADMIN_TOKEN` | Production | Protects dashboard data and writes |
| `WEBHOOK_TOKEN` | Production | Separately protects customer ingestion |
| `DATABASE_PATH` | No | SQLite path, defaults to `runtime/reviewdesk.db` |
| `BUSINESS_FILE` | No | First-run white-label business seed |
| `SEQUENCE_FILE` | No | First-run email sequence seed |
| `EMAIL_PROVIDER` | No | `demo` or `smtp` |
| `SMTP_HOST` | SMTP | Mail server hostname |
| `SMTP_PORT` | SMTP | Defaults to `587` |
| `SMTP_USERNAME` | SMTP | Provider username |
| `SMTP_PASSWORD` | SMTP | Provider password or SMTP key |
| `SMTP_USE_TLS` | No | Defaults to `true` |
| `REQUEST_WORKER_ENABLED` | No | Runs the built-in due-request worker |
| `REQUEST_POLL_SECONDS` | No | Worker interval, minimum 15 seconds |
| `REQUEST_RATE_LIMIT_PER_MINUTE` | No | Per-address feedback limit |
| `SEED_DEMO_DATA` | No | Adds fictional data and read-only demo access |
| `PUBLIC_BASE_URL` | Yes | Public HTTPS base used in request emails |
| `PORT` | Hosting | Injected by Railway and similar platforms |

## Test and quality commands

```powershell
pytest -q
ruff check .
node --check src/reviewdesk/static/public.js
node --check src/reviewdesk/static/admin.js
node --check src/reviewdesk/static/wall.js
node --check src/reviewdesk/static/widget.js
```

## Delivery documents

- [CLIENT_QUESTIONNAIRE.md](CLIENT_QUESTIONNAIRE.md)
- [FULFILLMENT_PLAYBOOK.md](FULFILLMENT_PLAYBOOK.md)
- [QA_CHECKLIST.md](QA_CHECKLIST.md)
- [DELIVERY_GUIDE.md](DELIVERY_GUIDE.md)
- [DEPLOYMENT_RAILWAY.md](DEPLOYMENT_RAILWAY.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [COMMERCIAL_LICENSE_TEMPLATE.md](COMMERCIAL_LICENSE_TEMPLATE.md)
- [Upwork Project Catalog copy](sales-assets/UPWORK_PROJECT_CATALOG.md)
- [Fiverr Gig copy](sales-assets/FIVERR_GIG.md)

## Commercial use

This repository is prepared as a productized-service base, not a public open-source template. Customize the included license for each buyer. The template is not legal advice.

