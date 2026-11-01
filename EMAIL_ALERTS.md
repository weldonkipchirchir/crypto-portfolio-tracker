# Email alerts

Email delivery is opt-in and uses the email saved on the signed-in account. In a coin's My price alerts panel, enable email after configuring a server sender. Client requests cannot override the recipient.

## Resend
Set production server environment variables `RESEND_API_KEY` and `ALERT_EMAIL_FROM` (for example, `Orbit <alerts@your-verified-domain.com>`). Verify the sender domain in Resend, then redeploy. Never put these values in frontend JavaScript or commit them to Git.

## SMTP alternative
Set `ALERT_EMAIL_FROM`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_PORT`. Only implicit TLS port 465 or STARTTLS port 587 is supported. If both providers are configured, Resend takes precedence.

## Behavior and testing
Checks run when requested and during active portfolio price refresh for supported coins. There is no closed-app background scheduler. Pine scripts do not send these emails. Each observed condition crossing creates an event. Opted-in events are queued durably, with a maximum of 20 per account per rolling day. Messages omit wallet addresses, balances and API credentials.

Resend uses stable idempotency keys and bounded retries; pending messages expire after one hour. SMTP failures are not automatically retried because acceptance may be uncertain. Accepted means provider acceptance, not confirmed inbox delivery. The UI shows queue status and offers retry for pending messages.

After setting the sender, use a test account you own, enable email, and create a threshold matching a fresh quote. Check the in-app event and provider delivery log. No real delivery was verified without provider credentials. Run `python -m unittest test_alert_email test_coin_alerts test_price_targets` to verify account isolation, deduplication, opt-in, limits and delivery behavior with mocked providers.
