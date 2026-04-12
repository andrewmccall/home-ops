# Domain Pitfalls

**Domain:** Home Assistant + OpenClaw voice integration  
**Milestone:** v1.0 Ada Home Assistant Voice  
**Researched:** 2026-04-12

## Critical Pitfalls

### 1. Reusing the broad "full Ada" OpenClaw surface for Home Assistant voice

**What goes wrong:** HA voice traffic inherits broader memory, tools, or unrelated session state from the general OpenClaw assistant surface.

**Prevent it by:**
- creating a dedicated HA voice profile or alias
- isolating voice sessions from Telegram and event jobs
- using a restricted tool surface

**Roadmap implication:** fix this before adding event or action bridges.

### 2. Session contamination across voice, Telegram, and event-driven flows

**What goes wrong:** voice context bleeds between endpoints or across unrelated channels.

**Prevent it by:**
- explicitly designing session identity for voice
- separating HA voice, HA events, and Telegram/chat callers
- deciding whether voice memory is stateless, short-lived, or room/device scoped

### 3. Transport and auth mismatches from copying the existing HA snippet verbatim

**What goes wrong:** the conversation backend appears configured, but HA cannot reliably reach OpenClaw because of scheme, token, host-header, or certificate mismatches.

**Prevent it by:**
- choosing one canonical HA -> OpenClaw endpoint
- documenting the auth token source
- validating the exact network path before UI setup

### 4. Ingress and NetworkPolicy mismatches

**What goes wrong:** cluster policy or port mismatches create timeouts that look like OpenClaw bugs.

**Prevent it by:**
- treating connectivity validation as part of the first phase
- reconciling ingress and policy ports before deeper voice work
- adding a smoke test that uses the same path HA will use

### 5. Designing wake word setup as if this were Home Assistant OS

**What goes wrong:** the plan assumes add-on workflows that do not match this Kubernetes deployment.

**Prevent it by:**
- treating wake word as explicit infrastructure work
- deploying a containerized wake word runtime
- defining model storage, update flow, and fallback behavior

### 6. Assuming custom "Hey Ada" works the same on every endpoint

**What goes wrong:** wake word support varies by endpoint class, but the milestone promises one uniform outcome.

**Prevent it by:**
- selecting supported endpoint classes early
- documenting where detection runs for each endpoint
- including fallback wake word behavior in the MVP

### 7. Letting HA conversation control become a backdoor for broad device access

**What goes wrong:** exposed entities or broad control flags bypass the planned narrow action bridge.

**Prevent it by:**
- separating conversation generation from actuator permissions
- keeping direct HA control disabled or extremely constrained
- preferring approved scripts/scenes/services over broad entity access

### 8. Forwarding raw Home Assistant events or state blobs

**What goes wrong:** OpenClaw receives oversized, noisy, or privacy-sensitive payloads.

**Prevent it by:**
- defining compact event schemas first
- forwarding only allowlisted event types
- keeping HA responsible for deciding what is relevant

### 9. Creating loops between event forwarding and action callbacks

**What goes wrong:** HA forwards an event, OpenClaw calls back into HA, and the resulting action emits another event that restarts the loop.

**Prevent it by:**
- using source markers or correlation IDs
- excluding bridge-generated activity from event forwarding
- adding cooldowns and idempotency

## Moderate Pitfalls

### 10. Mixing HA's STT/TTS pipeline with alternate OpenClaw audio paths

**What goes wrong:** the runtime ends up with competing audio paths, making Assist behavior unpredictable.

**Prevent it by:** keeping the v1 contract simple: HA owns the voice shell, Whisper/Piper stay in HA, OpenClaw is the conversation brain.

### 11. Ignoring latency and HA timeout behavior

**What goes wrong:** HA event calls wait on slow model responses and time out.

**Prevent it by:**
- keeping forwarded event handlers bounded
- using async or queued patterns where needed
- defining retry vs no-retry behavior

### 12. Making the action bridge generic too early

**What goes wrong:** a generic `call_service(domain, service, ...)` interface turns the narrow bridge into broad control.

**Prevent it by:**
- starting with explicit approved intents
- adding new actions only through reviewable config/code changes
- logging every request with caller metadata

### 13. Persona drift across HA config, OpenClaw identity, and spoken output

**What goes wrong:** users hear or see inconsistent assistant identity even though the mechanics work.

**Prevent it by:**
- adding an identity checklist
- validating Ada naming and phrasing in real voice tests

## Minor Pitfalls

### 14. Treating microphone input and speaker output as the same problem

**What goes wrong:** the roadmap assumes one device does both when the spec explicitly allows separate mic and speaker targets.

**Prevent it by:** deciding early which devices are inputs, outputs, or both.

### 15. Shipping without observability across system boundaries

**What goes wrong:** failures cannot be localized to microphone, STT, OpenClaw, TTS, speaker routing, or bridge.

**Prevent it by:**
- adding correlation IDs across HA -> OpenClaw -> HA
- logging bridge inputs, outputs, and rejected actions
- keeping an end-to-end smoke path

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Phase 1: Voice path architecture | Reusing broad Ada surface | Create a dedicated voice profile with narrow permissions |
| Phase 1: Connectivity | HTTP/HTTPS/auth mismatch | Define one canonical transport path and validate it early |
| Phase 1: Cluster networking | Ingress or NetworkPolicy mismatch | Reconcile allowed ports and add a smoke test |
| Phase 2: Wake word runtime | Planning around HA OS add-ons | Deploy a containerized wake word service |
| Phase 2: Endpoint support | Assuming custom wake word works everywhere | Publish endpoint support matrix and fallback |
| Phase 3: Event bridge | Forwarding raw event/state blobs | Use allowlisted, versioned, small JSON payloads |
| Phase 3: Event handling | HA timeouts on slow responses | Bound latency and use async patterns where needed |
| Phase 4: Action bridge | Generic unrestricted service calls | Expose only approved scripts, scenes, and notifications |
| Phase 4: Bidirectional behavior | Event/action loop storms | Add source tagging, cooldowns, and loop tests |
| Phase 5: UX validation | Persona drift or room confusion | Run real acceptance tests across the chosen endpoints |
| Phase 5: Ops | No tracing across boundaries | Add correlation IDs and per-hop diagnostics |

## Roadmap Prevention Notes

1. Do transport and trust-boundary work before UX polish.  
2. Make wake word its own explicit phase.  
3. Build HA -> OpenClaw event forwarding before OpenClaw -> HA actions.  
4. Ship approved intents, not generic service calls.  
5. Reserve a final hardening phase for loops, latency, persona validation, and observability.

## Sources

- `.planning/PROJECT.md`
- `spec/openclaw-home-assistant-voice.md`
- `cluster/apps/house/home-assistant/home-assistant.yaml`
- `cluster/apps/openclaw/instance/openclaw-instance.yaml`
- `cluster/apps/openclaw/instance/ha-config-snippet.yaml`
- `cluster/apps/openclaw/instance/gateway-ingress.yaml`
- `cluster/apps/openclaw/instance/gateway-allow-internal-nginx.yaml`
- `cluster/apps/openclaw/README.md`
