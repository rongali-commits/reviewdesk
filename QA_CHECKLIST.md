# ReviewDesk release checklist

## Brand and content

- [ ] Every fictional Northstar reference is replaced or intentionally retained only in a demo.
- [ ] Business name, colors, contact email, privacy link, and sender are approved.
- [ ] Public review URL opens the buyer's correct listing.
- [ ] Request and reminder copy is approved.
- [ ] No message asks for a specific rating or offers an incentive.

## Customer experience

- [ ] Feedback page works on phone, tablet, and desktop widths.
- [ ] Keyboard users can choose a rating and submit.
- [ ] All ratings from one to five are accepted.
- [ ] The public review option appears regardless of rating.
- [ ] A second submission on the same request is rejected.
- [ ] Invalid or expired tokens return a clear error.

## Automation

- [ ] Initial request timing is correct.
- [ ] Reminders stop after feedback is submitted.
- [ ] SMTP uses a verified sender with SPF and DKIM configured.
- [ ] Reply-to address is monitored.
- [ ] Test messages reach the expected inbox and do not expose secrets.

## Dashboard and data

- [ ] Admin token is strong and different from the webhook token.
- [ ] Public demo token cannot change or export data.
- [ ] CSV import accepts the approved headers.
- [ ] CSV export neutralizes formula-leading values.
- [ ] Testimonials require consent and admin approval.
- [ ] Customer emails never appear on the public wall.
- [ ] Backup and retention behavior is documented.

## Deployment

- [ ] HTTPS is active.
- [ ] `/health` returns status `ok`.
- [ ] Persistent storage is mounted.
- [ ] `APP_ENV=production` is set.
- [ ] `SEED_DEMO_DATA=false` for buyer production.
- [ ] Automated tests and JavaScript syntax checks pass.

