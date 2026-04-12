# Phase 01: Shared Ada Voice Contract - Research

**Researched:** 2026-04-13
**Domain:** Home Assistant `openai_conversation` → OpenClaw gateway in-cluster; session identity; voice-first prompt; NetworkPolicy
**Confidence:** HIGH (core findings verified directly from cluster manifests; OpenClaw sender-mapping schema ASSUMED)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**HA → OpenClaw transport and auth**
- **D-01:** Home Assistant voice should call OpenClaw over a direct in-cluster service URL rather than the existing ingress hostname path.
- **D-02:** Home Assistant should use a dedicated HA voice gateway token stored as a Home Assistant secret, not the shared general gateway token.

**Shared Ada identity and session behavior**
- **D-03:** Home Assistant voice should use the same primary Andrew/Ada identity that is already used in Telegram and other OpenClaw channels.
- **D-04:** Phase 1 should deliberately preserve shared cross-channel Ada conversation continuity instead of isolating Home Assistant voice into a separate session namespace.

**Guardrail enforcement**
- **D-05:** Blocked or destructive home-action requests should be denied first in the OpenClaw voice policy/prompt.
- **D-06:** Later Home Assistant-side action enforcement remains the backstop, but Phase 1 must already make Ada refuse blocked actions clearly at the voice layer.

**Voice response shape**
- **D-07:** Ada should sound friendly and voice-first in Home Assistant voice mode.
- **D-08:** Spoken replies should be brief by default and only expand when the user asks for more detail.

### the agent's Discretion
- Exact secret key names, Kubernetes secret wiring, and Home Assistant secret file layout
- Exact direct service DNS form and config placement inside Home Assistant
- Exact OpenClaw prompt wording, as long as it preserves Ada identity, shared context, and clear blocked-action denials
- Exact spoken wording patterns for brief-by-default responses

### Deferred Ideas (OUT OF SCOPE)
- Make shared identity/session handling more robust than a single primary Andrew/Ada identity once Phase 1 is proven.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VOICE-03 | User experiences a consistent Ada identity across Home Assistant assistant naming, OpenClaw behavior, and spoken replies. | Covered by: HA `openai_conversation` `name: Ada`, HA voice assistant UI config, and OpenClaw prompt section |
| VOICE-04 | User can continue the same Ada conversation context across Home Assistant voice and Telegram or other general OpenClaw channels. | Covered by: OpenClaw `session.scope: per-sender` + sender identity mapping of the HA voice token to the shared Andrew identity |
| SAFE-02 | User can access Ada's broader OpenClaw memory and tool-backed conversational context from Home Assistant voice interactions. | Covered by: using `openclaw:main` model (not restricted) through the dedicated HA token; no tool restrictions in Phase 1 |
| SAFE-03 | User receives a clear denial when requesting destructive or explicitly blocked Home Assistant admin actions, even though Ada uses the full shared OpenClaw surface. | Covered by: voice-specific system-prompt additions in OpenClaw config that explicitly instruct Ada to deny destructive/admin HA requests |
</phase_requirements>

---

## Summary

Phase 1 makes Home Assistant voice talk to the same shared Ada surface as Telegram. All four
requirements are achievable with three targeted changes to the existing cluster: (1) a new
NetworkPolicy allowing the `house` namespace to reach OpenClaw pods on port 18790 directly, (2)
a new SOPS-encrypted HA voice gateway token secret and matching OpenClaw config that maps that
token to the shared Andrew/Ada sender identity, and (3) a voice-first system-prompt addition in
the OpenClaw `spec.config.raw` that enforces Ada persona, brief spoken replies, and explicit
denials for destructive home-admin requests.

The infrastructure is already almost entirely in place. The existing LiteLLM proxy in the `openclaw`
namespace already uses the direct service URL `http://home-ops-openclaw.openclaw.svc:18789/v1`
as its back-end — confirming that the direct path is well-understood and operationally proven.
The `house` namespace currently has no NetworkPolicy pointing at the `openclaw` namespace, so
a thin allow-rule is the only net-new networking work. Home Assistant already has the
`openai_conversation` integration pointed at a gateway (via the `api.openai.com` hostAlias proxy),
so reconfiguring it to use the direct service URL is a configuration-only change.

The one area requiring careful handling is **sender identity mapping**: OpenClaw uses
`session.scope: per-sender` and the "sender" for a chat-completions API call is determined by
what OpenClaw reads from the request (likely the API token or an explicit `user` field). The
exact OpenClaw config key that maps an API token to a named sender is ASSUMED from repo
patterns; the planner must include a verification step to confirm it before committing the
OpenClaw config change.

**Primary recommendation:** Implement in three sequential plans — (1) network path + HA config,
(2) dedicated token + identity mapping, (3) voice-first prompt + denial tests.

---

## Standard Stack

### Core

| Component | Version | Purpose | Status |
|-----------|---------|---------|--------|
| Home Assistant | `2026.3.4` | Voice shell; hosts `openai_conversation` | Already deployed in `house` namespace |
| `openai_conversation` HA integration | Built-in (HA 2023.9+) | Routes HA Assist conversation turns to an OpenAI-compatible endpoint | Already present in intent; needs `api_base` pointed at direct service |
| OpenClaw gateway | Latest (operator-managed) | Ada conversation backend; serves `/v1/chat/completions` | Already deployed at `home-ops-openclaw.openclaw.svc:18789` |
| Wyoming Piper (`en_GB-cori-high`) | `2.2.2` | TTS voice for Ada spoken replies | Already deployed in `house` namespace |
| Wyoming Whisper | `3.1.0` | STT for Assist pipeline | Already deployed in `house` namespace |
| SOPS + age | Cluster-standard | Secret encryption for new HA voice token | Already in use; `age16rj2w4scur86mjvs6eutq03cwlpygu3pywcedvl0rkh68vzv0dlqagqenq` is the recipient |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| LiteLLM (existing) | `main-latest` | Existing OpenAI-compat proxy; already uses direct service URL as reference | **Do not change for this phase** — it confirms the direct URL pattern but Phase 1 bypasses it |
| `openai-proxy-ingress` (existing) | — | Routes `api.openai.com` → OpenClaw via internal nginx | **Do not change for this phase** — still needed for other consumers; HA voice will switch to direct URL |

---

## Architecture Patterns

### Existing Transport Path (BEFORE Phase 1)

```
HA openai_conversation
  → https://api.openai.com/v1  (hostAlias: api.openai.com → 10.44.0.20)
  → nginx-internal-controller (10.44.0.20:443)
  → openai-proxy-ingress (openclaw namespace, port 18789)
  → home-ops-openclaw pod (port 18790)
```

**Problem:** Goes through HTTPS with self-signed CA, nginx ingress, NetworkPolicy restricted to
the `networking` namespace ingress pods. Uses the shared general `GATEWAY_TOKEN`.

### Target Transport Path (AFTER Phase 1)

```
HA openai_conversation
  → http://home-ops-openclaw.openclaw.svc:18789/v1  (direct ClusterIP)
  → home-ops-openclaw pod (port 18790)
```

**Benefit:** No TLS overhead, no ingress hop, no dependency on `api.openai.com` hostAlias or
the self-signed CA cert. Simpler, faster, more direct.

**Requires:** New NetworkPolicy allowing ingress from `house` namespace to OpenClaw pods on
pod port 18790. [VERIFIED: from `kubectl get networkpolicy -n openclaw`]

### OpenClaw Service Port Mapping (VERIFIED)

| Service port | Pod port | Used by |
|---|---|---|
| 18789 (gateway) | 18790 | Chat completions, canvas UI, HA voice |
| 18793 (canvas) | 18794 | Canvas UI via ingress |

Direct in-cluster URL: `http://home-ops-openclaw.openclaw.svc:18789/v1`
[VERIFIED: from `kubectl get svc home-ops-openclaw -n openclaw -o yaml`]

### OpenClaw `session.scope: per-sender`

OpenClaw is configured with `session.scope: per-sender` [VERIFIED: `openclaw-instance.yaml:35`].
This means every unique sender identity gets its own conversation thread. For VOICE-04 (shared
context), the HA voice token must **map to the same sender as Andrew's Telegram identity** — not
create a new sender namespace.

### Session Identity Mapping Pattern [ASSUMED]

Based on repo patterns (the `ha-config-snippet.yaml` comment "Same session as your Telegram chat",
and that LiteLLM passes `GATEWAY_TOKEN` to OpenClaw), OpenClaw appears to derive sender identity
from the API token used in the request. The config path to map a token to a named sender is
expected to be inside `spec.config.raw.gateway` in the `OpenClawInstance` manifest — something
like a `senders` or `auth.tokens` block that names the sender for each token.

**⚠️ CRITICAL: This mapping mechanism must be confirmed against the actual OpenClaw operator
schema before writing the config. See Open Questions §1.**

### NetworkPolicy Pattern (VERIFIED from existing `gateway-allow-internal-nginx.yaml`)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: home-ops-openclaw-allow-house-voice
  namespace: openclaw
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/instance: home-ops-openclaw
      app.kubernetes.io/name: openclaw
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: house    # VERIFIED label on house namespace
      ports:
        - port: 18790      # pod port (service port 18789 → pod port 18790)
          protocol: TCP
```
[VERIFIED: `house` namespace has label `kubernetes.io/metadata.name: house`]

### Home Assistant `openai_conversation` Configuration Pattern

From `ha-config-snippet.yaml` [VERIFIED], the integration is configured in `configuration.yaml`:

```yaml
# configuration.yaml
openai_conversation:
  - api_base: http://home-ops-openclaw.openclaw.svc:18789/v1
    api_key: !secret ha_voice_gateway_token
    model: "openclaw:main"
    name: Ada
```

```yaml
# secrets.yaml  (in HA config PVC at /config/secrets.yaml)
ha_voice_gateway_token: <the dedicated HA voice token value>
```

**Note:** The `api_base` used here is plain HTTP, so the existing `REQUESTS_CA_BUNDLE` env var
and the `openai-internal-ca` ConfigMap mount are **no longer needed for voice**. They should
be left in place (other things may use the `api.openai.com` path) but HA voice won't depend on them.

### Voice-First System Prompt Pattern (D-05, D-07, D-08)

OpenClaw system-prompt additions for voice go in `spec.config.raw` under `agents` or a
per-channel/per-model profile. The exact config key path is ASSUMED (see Open Questions §2),
but the **content** is deterministic:

```
You are Ada, a friendly home assistant. When speaking aloud:
- Keep replies short and conversational — one or two sentences by default.
- Expand only if the user explicitly asks for more detail.
- If asked to perform a destructive or administrative Home Assistant action
  (such as deleting automations, editing config files, managing add-ons, resetting devices,
  or anything outside normal conversation and approved home controls), respond with a clear
  refusal: "I can't do that — that kind of home admin change isn't something I'm set up to
  handle by voice."
- Maintain a warm, helpful tone consistent with Ada's identity across all channels.
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAI-compatible conversation endpoint | Custom proxy or REST shim | OpenClaw gateway `/v1/chat/completions` (already deployed) | Already proven at port 18789; LiteLLM already uses it |
| Secret encryption | Plain Kubernetes secrets in git | SOPS + age (cluster-standard pattern) | All other secrets use this; age recipient key already in repo |
| HA conversation agent integration | Custom webhook/script | `openai_conversation` HA integration | Native HA integration; receives the `model`, `name`, `api_base`, `api_key` config fields |
| NetworkPolicy | Manual firewall rules | Standard Kubernetes NetworkPolicy | All other cross-component policies in this cluster use this pattern |
| TTS / STT | New services | Existing Wyoming Piper + Whisper in `house` namespace | Already deployed and wired to HA Assist; Phase 1 just routes conversation, not audio |

---

## Common Pitfalls

### Pitfall 1: NetworkPolicy port confusion (service port vs pod port)
**What goes wrong:** NetworkPolicy is written for service port 18789 but NetworkPolicy applies at the
pod level — the pod listens on 18790. Policy is silently not matched and connections time out.
**Why it happens:** The service maps 18789 → 18790; NetworkPolicy applies to pod-level ports.
**How to avoid:** Always use the **pod port** (18790) in NetworkPolicy ingress rules for OpenClaw.
**Warning signs:** Connection timeouts from HA to OpenClaw with no OpenClaw log entries.

### Pitfall 2: Reusing the shared general gateway token for HA voice
**What goes wrong:** The dedicated voice token is not configured; HA voice uses the same token as
LiteLLM or the general API surface, which may belong to a different sender and break shared context.
**How to avoid:** Generate a new token explicitly for HA voice (D-02). Store it separately in
both the Kubernetes secret (for OpenClaw auth) and HA `secrets.yaml`.

### Pitfall 3: Sender identity creates a NEW session instead of sharing with Telegram
**What goes wrong:** The HA voice token maps to a new sender ID, giving Ada a blank context with no
memory of Telegram conversations — violating VOICE-04 and SAFE-02.
**How to avoid:** Confirm the OpenClaw sender-mapping config and explicitly set the HA voice token's
sender to the same identity as Andrew's primary Telegram sender.
**Warning signs:** After Phase 1, sending the same question in Telegram and HA voice gets
different context-aware answers (Ada doesn't "remember" cross-channel).

### Pitfall 4: Leaving the `api.openai.com` hostAlias path in place AND adding the direct URL
**What goes wrong:** Two `openai_conversation` entries compete; HA may use either depending on order.
**How to avoid:** Replace the existing config entry; don't add a duplicate. Leave the ingress proxy
and hostAlias intact for other consumers, but HA `openai_conversation` should have exactly one
entry pointing to the direct service URL.

### Pitfall 5: Voice prompt blocks too broadly and breaks conversational Ada
**What goes wrong:** Overly restrictive prompt causes Ada to refuse benign questions that mention
home devices ("turn off the lamp" — even when Phase 4 hasn't been reached yet, Ada should
explain she can't do that yet rather than refusing to engage at all).
**How to avoid:** The denial prompt should be about **admin/destructive/config** actions, not
about all home-device references. Ada can acknowledge a request and explain it's not available
yet rather than going silent.

### Pitfall 6: `REQUESTS_CA_BUNDLE` env var causes plain-HTTP requests to fail
**What goes wrong:** HA tries to use the CA bundle for the direct HTTP URL and fails because
there's no TLS to verify.
**How to avoid:** Plain HTTP (`http://`) to the direct service URL does not use TLS at all; the
`REQUESTS_CA_BUNDLE` env var is only invoked when HA makes HTTPS calls. The existing mount can
stay; it won't interfere with plain HTTP.
**Note:** If you ever switch to HTTPS for the direct path, you'd need to address this.

---

## Code Examples

### New NetworkPolicy (cluster/apps/openclaw/instance/gateway-allow-house-voice.yaml)

```yaml
# Source: pattern from gateway-allow-internal-nginx.yaml [VERIFIED]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: home-ops-openclaw-allow-house-voice
  namespace: openclaw
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/instance: home-ops-openclaw
      app.kubernetes.io/name: openclaw
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: house
      ports:
        - port: 18790      # pod port — service 18789 → pod 18790
          protocol: TCP
```

### HA `configuration.yaml` openai_conversation entry

```yaml
# Source: ha-config-snippet.yaml [VERIFIED], adapted per D-01/D-02
openai_conversation:
  - api_base: http://home-ops-openclaw.openclaw.svc:18789/v1
    api_key: !secret ha_voice_gateway_token
    model: "openclaw:main"
    name: Ada
```

### HA `secrets.yaml` entry

```yaml
# /config/secrets.yaml  (on the home-assistant-config PVC)
ha_voice_gateway_token: <value of the dedicated token>
```

### SOPS secret for HA voice token (cluster/apps/openclaw/instance/openclaw-ha-voice-secret.sops.yaml)

```yaml
# Pattern from openclaw-api-keys-secret.sops.yaml [VERIFIED]
# Encrypt with: sops --encrypt --age age16rj2w4scur86mjvs6eutq03cwlpygu3pywcedvl0rkh68vzv0dlqagqenq
apiVersion: v1
kind: Secret
metadata:
  name: openclaw-ha-voice-token
  namespace: openclaw
type: Opaque
stringData:
  ha-voice-gateway-token: <token value — encrypt before commit>
```

### OpenClaw instance config additions (spec.config.raw additions) [ASSUMED schema]

```yaml
# In spec.config.raw of openclaw-instance.yaml
# ASSUMED key path — verify against OpenClaw operator schema before applying
gateway:
  http:
    endpoints:
      chatCompletions:
        enabled: true
        senders:                           # ASSUMED: maps token → sender identity
          - tokenSecretRef:
              name: openclaw-ha-voice-token
              key: ha-voice-gateway-token
            senderId: "andrew"             # ASSUMED: must match Telegram sender ID for shared context
```

---

## Runtime State Inventory

> Phase 1 is a configuration/routing change, not a rename/refactor. This section is included
> because the sender-identity mapping touches persisted OpenClaw session state.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | OpenClaw session store for `per-sender` sessions (unknown volume; stored on `home-ops-openclaw` PVC) | Code/config change only — shared context works by reusing the existing sender session; no migration needed |
| Live service config | HA `openai_conversation` config in `/config/configuration.yaml` on `home-assistant-config` PVC | Manual edit via code-server or direct file edit |
| HA `secrets.yaml` | Token value for `ha_voice_gateway_token` | Manual write to HA config PVC |
| OS-registered state | None — no OS-level registrations involved | None |
| Secrets/env vars | New SOPS secret in `openclaw` namespace | Create + encrypt new SOPS file, add to kustomization.yaml |
| Build artifacts | None | None |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Manual smoke testing (no automated test framework detected in this repo) |
| Config file | none |
| Quick run command | `curl` + `kubectl logs` |
| Full suite command | Manual conversation test across HA and Telegram |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VOICE-03 | HA voice assistant is named "Ada" and OpenClaw responds as Ada | smoke | `curl -s -X POST http://home-ops-openclaw.openclaw.svc:18789/v1/chat/completions -H "Authorization: Bearer <ha-token>" -d '{"model":"openclaw:main","messages":[{"role":"user","content":"What is your name?"}]}'` — expect "Ada" in response | ❌ Wave 0 |
| VOICE-04 | Cross-channel context: send a unique fact in Telegram, ask HA voice to recall it | manual | Manual test only — speak a question in HA Assist that references a prior Telegram conversation | ❌ Wave 0 |
| SAFE-02 | Ada's memory and tools respond in HA voice context | smoke | Same curl as VOICE-03 but ask a question requiring memory/tool access | ❌ Wave 0 |
| SAFE-03 | Ada denies destructive home admin request | smoke | `curl` with message `"delete all my automations"` — expect refusal text | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `curl` smoke test to `/v1/chat/completions` with the HA voice token
- **Per wave merge:** Full manual conversation test (VOICE-03 + SAFE-03 at minimum)
- **Phase gate:** All four requirements verified manually before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] Simple `curl` smoke script at `scripts/test-ha-voice-token.sh` — covers VOICE-03, SAFE-02, SAFE-03
- [ ] Manual test checklist doc at `.planning/phases/01-shared-ada-voice-contract/MANUAL-TEST.md` — covers VOICE-04

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Dedicated per-consumer API token (not shared); stored in SOPS-encrypted secret and HA `secrets.yaml` |
| V3 Session Management | Yes | OpenClaw `session.scope: per-sender`; sender mapping must resolve to the correct identity |
| V4 Access Control | Yes | Token only grants access to chat completions; no admin surface; voice prompt denies destructive actions |
| V5 Input Validation | No (conversation content, not structured data input) | — |
| V6 Cryptography | Yes | Token at-rest encrypted via SOPS+age; in-transit over plain HTTP within cluster (acceptable for in-cluster only path) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token leakage from HA config PVC | Information Disclosure | Store as `!secret` in `secrets.yaml` not inline in `configuration.yaml`; PVC is not in git |
| HA voice token grants broader OpenClaw access than intended | Elevation of Privilege | Token maps to Andrew's sender (no elevation — same identity as Telegram); no admin capabilities on OpenClaw side |
| Prompt injection via voice → destructive home action | Tampering | Voice-layer denial prompt (D-05); HA-side enforcement in Phase 4 (D-06) |
| New NetworkPolicy too broad | Elevation of Privilege | Restrict to `port: 18790` only; restrict `from` to `house` namespace only; not cluster-wide |
| Token committed unencrypted to git | Information Disclosure | Use SOPS; never commit plaintext token; follow existing SOPS patterns in repo |

---

## Open Questions

### 1. OpenClaw sender-mapping config key path ⚠️ CRITICAL
**What we know:** OpenClaw uses `session.scope: per-sender`. The `ha-config-snippet.yaml` comment
says HA voice should have "Same session as your Telegram chat", implying sender-identity sharing is
the intent. LiteLLM calls OpenClaw with `GATEWAY_TOKEN` — so OpenClaw does token-to-sender mapping
of some kind.
**What's unclear:** The exact `spec.config.raw` key path to map an API token to a named sender.
Options: a `gateway.auth.tokens[]` block, a `gateway.http.endpoints.chatCompletions.senders[]`
block, or something else entirely. The OpenClaw operator schema is not in this repo.
**Recommendation:** Before writing the OpenClaw config change, run:
```bash
kubectl describe crd openclawinstances.openclaw.rocks 2>/dev/null | grep -A 5 "sender\|token\|auth"
```
or check OpenClaw operator docs / changelog to find the correct field. The planner should make
this a **first-task verification step** in the token-identity plan.

### 2. OpenClaw voice-channel system prompt config key path [ASSUMED]
**What we know:** The `spec.config.raw.agents.defaults.model.primary` key sets the LLM model.
OpenClaw likely has a per-channel or per-model-alias prompt/persona config.
**What's unclear:** Whether voice-specific prompt overrides go under `agents.voice`, `agents.defaults.systemPrompt`, `channels.chatCompletions.systemPrompt`, or another key.
**Recommendation:** Check OpenClaw operator schema or existing documentation before writing
the config. This is also a first-task verification step in the voice-prompt plan.

### 3. HA Voice Assistant UI vs YAML for assistant-level config (VOICE-03)
**What we know:** The `openai_conversation` integration and its `name: Ada` entry are YAML-configured.
The mapping of an assistant to STT/TTS services is done in HA UI (Settings → Voice Assistants).
**What's unclear:** Whether Phase 1 requires confirming the HA Voice Assistant UI config as part
of the test criteria, or whether the `openai_conversation` YAML entry alone is sufficient for
VOICE-03.
**Recommendation:** Phase 1 should include the HA Voice Assistant UI step ("Ada" assistant using
the Ada conversation agent, Whisper STT, Piper TTS) as a deliverable even though Phase 2 will
add wake-word wiring. This ensures VOICE-03 can be verified with a manual Assist text test.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| OpenClaw gateway pod | Direct service URL (D-01) | ✓ | operator-managed | — |
| `home-ops-openclaw` ClusterIP service | Direct URL `svc:18789` | ✓ | — | — |
| `house` namespace | NetworkPolicy source | ✓ | label: `kubernetes.io/metadata.name: house` | — |
| SOPS age key | New secret encryption | ✓ | `age16rj2w4scur86mjvs6eutq03cwlpygu3pywcedvl0rkh68vzv0dlqagqenq` | — |
| HA config PVC (`home-assistant-config`) | `configuration.yaml` + `secrets.yaml` edits | ✓ | Persistent, in-cluster | Edit via code-server at `home-assistant-code.${DOMAIN}` |
| HA code-server | Config file editing | ✓ | `4.112.0` | Direct `kubectl exec` into HA pod |

**Missing dependencies with no fallback:** None.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | OpenClaw `spec.config.raw` accepts a `gateway`-level key that maps an API token to a named sender identity | Architecture Patterns — Session Identity Mapping | Token-to-sender config may live in a completely different section; entire identity-sharing approach may need revision |
| A2 | OpenClaw voice-channel/conversation system-prompt overrides live in `spec.config.raw.agents` or `spec.config.raw.channels.chatCompletions` | Architecture Patterns — Voice-First Prompt | Wrong key path would mean the prompt is silently ignored; Ada would not have the denial behavior |
| A3 | The sender identity that matches Telegram Andrew is a string like `"andrew"` or a stable user ID | Architecture Patterns — Session Identity Mapping | Using wrong sender ID breaks cross-channel continuity (VOICE-04, SAFE-02) |
| A4 | `openai_conversation` in HA sends the `api_key` as a Bearer token, which OpenClaw reads as the caller identity | Architecture Patterns — Session Identity Mapping | If OpenClaw uses `user` field instead of Bearer token, sender mapping approach changes |

---

## Sources

### Primary (HIGH confidence)
- `cluster/apps/openclaw/instance/openclaw-instance.yaml` — OpenClaw config schema, `session.scope: per-sender`, service ports
- `cluster/apps/openclaw/instance/gateway-allow-internal-nginx.yaml` — NetworkPolicy pattern for OpenClaw ingress rules
- `cluster/apps/openclaw/instance/gateway-ingress.yaml` — existing ingress (Phase 1 intentionally NOT using this for HA voice)
- `cluster/apps/openclaw/litellm/litellm.yaml` — confirms `http://home-ops-openclaw.openclaw.svc:18789/v1` as the working direct URL
- `cluster/apps/openclaw/litellm/openai-proxy-ingress.yaml` + `cluster/apps/house/home-assistant/home-assistant.yaml` — current HA transport path via `api.openai.com` hostAlias + self-signed CA
- `cluster/apps/openclaw/instance/ha-config-snippet.yaml` — existing HA conversation config starting point
- `kubectl get svc home-ops-openclaw -n openclaw -o yaml` — VERIFIED service port mapping (18789 → 18790)
- `kubectl get namespace house --show-labels` — VERIFIED `kubernetes.io/metadata.name: house` label
- `kubectl get networkpolicy -n openclaw` — VERIFIED existing policies and pod-selector labels

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` — prior research on target architecture and anti-patterns
- `.planning/research/PITFALLS.md` — prior research on transport/auth/networking failure modes
- `.planning/research/SUMMARY.md` — original research findings (note: original recommendation for isolated session was overridden by CONTEXT.md D-03/D-04)

### Tertiary (LOW confidence / ASSUMED)
- OpenClaw sender-mapping config key path [ASSUMED] — not verifiable without OpenClaw operator schema
- OpenClaw voice system-prompt config key path [ASSUMED] — not verifiable without OpenClaw operator schema

---

## Metadata

**Confidence breakdown:**
- Network path and service topology: HIGH — verified from live cluster
- HA `openai_conversation` config shape: HIGH — verified from existing ha-config-snippet and HA integration docs
- NetworkPolicy pattern: HIGH — verified from existing gateway-allow-internal-nginx.yaml and namespace labels
- OpenClaw sender-identity mapping: LOW → ASSUMED — OpenClaw operator schema not available in-repo
- OpenClaw voice prompt config key: LOW → ASSUMED — same constraint

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable infrastructure; LOW confidence items should be confirmed before planning the token-identity plan)
