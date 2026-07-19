# Modern Collector → Hermes

Hermes accepts signed incident events on:

```text
/webhooks/modern-collector-alerts
```

The route validates `X-Webhook-Timestamp` and `X-Webhook-Signature-V2` using
HMAC-SHA256, and deduplicates `X-Request-ID`.  Modern Collector already emits
these headers when `ALERT_WEBHOOK_URL` and `ALERT_WEBHOOK_SECRET` are set.

## Recommended deployment: same Swarm overlay

Deploy Hermes with `docker-stack.yml` as a service attached to the external
`Nimbox360` overlay. Its stable service name is `hermes`. Then add this to both
the `monit` and `telegram-polling` services' environment in the Modern
Collector stack:

```yaml
- ALERT_WEBHOOK_URL=http://hermes:8644/webhooks/modern-collector-alerts
- ALERT_WEBHOOK_SECRET=${ALERT_WEBHOOK_SECRET}
```

Store `ALERT_WEBHOOK_SECRET` only in the deployment environment (or,
preferably, the Swarm/Coolify secret store). Hermes consumes it as
`WEBHOOK_SECRET`; never place it in the stack file, `config.yaml`, or commit it.
The overlay network keeps the webhook private; no public port is required.

Build and publish the image before deploying the stack:

```sh
docker build -t tuxed/nimbox-sre-hermes:latest .
docker push tuxed/nimbox-sre-hermes:latest
docker stack deploy -c docker-stack.yml nimbox-sre
```

The deployment shell must export the variables referenced by
`docker-stack.yml`; the file intentionally contains no values for credentials.

## Alternative: public HTTPS endpoint

Publish Hermes through Traefik with TLS and set:

```text
ALERT_WEBHOOK_URL=https://<hermes-host>/webhooks/modern-collector-alerts
```

Keep the HMAC secret mandatory even on HTTPS.  Restrict ingress to the
collector network/IPs when possible.

## Behaviour

On a valid event Hermes wakes immediately, first checks the maintenance window
for the host, then collects read-only Nightingale/OpenSRE evidence.  It does
not create access tickets, run SSH commands, or change systems without an
explicit confirmation.
