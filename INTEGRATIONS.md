# ReviewDesk integrations

## Completed-customer webhook

```http
POST /api/webhooks/customers
Content-Type: application/json
X-Webhook-Token: YOUR_PRIVATE_TOKEN
```

```json
{
  "event": "job.completed",
  "customer": {
    "name": "Taylor Morgan",
    "email": "taylor@example.com",
    "phone": "",
    "service": "Annual maintenance",
    "service_date": "2026-08-28",
    "source": "crm",
    "reminders_enabled": true,
    "website": ""
  }
}
```

Supported events:

- `customer.completed`
- `job.completed`
- `invoice.paid`

The token belongs in the automation platform's secret store, never in browser JavaScript. A successful request creates the customer and schedules the enabled review-request sequence.

## Common connectors

- Zapier or Make: use a custom webhook action after a job-completed or invoice-paid trigger.
- n8n: use an HTTP Request node with the webhook token header.
- FollowDesk: trigger after a lead reaches `won` or a booking reaches `completed`.
- Custom CRM: send the payload from a trusted server-side job.

