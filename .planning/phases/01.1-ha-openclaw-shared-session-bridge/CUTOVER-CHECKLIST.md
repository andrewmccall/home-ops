# Phase 01.1 Bridge Cutover Checklist

## Pre-cutover checks

- [ ] **ingress** ownership is bridge-only: `cluster/apps/openclaw/bridge/openai-proxy-ingress.yaml` exists and LiteLLM no longer owns the spoof ingress resource.
- [ ] **TLS** ownership is bridge-only: `cluster/apps/openclaw/bridge/openai-proxy-tls-secret.yaml` exists and LiteLLM no longer owns the spoof TLS resource.
- [ ] The live ingress IP from `kubectl get ingress -n openclaw openai-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}'` matches the Home Assistant `hostAlias` for `api.openai.com`.
- [ ] The bridge deployment is healthy and serving `/v1/models` and `/v1/responses`.
- [ ] Secret `openclaw-bridge-secrets` is present with `bridge-api-key`, `openclaw-gateway-token`, `shared-session-key`, and `force-degraded-mode`.

## Home Assistant update

- [ ] Update the OpenAI Conversation config entry to `Base URL: https://api.openai.com/v1`.
- [ ] Enter the dedicated bridge API key, not the shared OpenClaw gateway token.
- [ ] Keep `Model: openclaw:main`.
- [ ] Bind the config entry to the Ada assistant under Voice Assistants.

## Approval gate before LiteLLM removal

- [ ] Run `MANUAL-TEST.md` end to end.
- [ ] Confirm Telegram continuity succeeds.
- [ ] Confirm degraded mode is explicit when forced.
- [ ] Confirm denial behavior still works.
- [ ] Mark the bridge path **approved** before executing Plan `01.1-04`.
