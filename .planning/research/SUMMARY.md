# Project Research Summary

**Project:** Home Ops
**Domain:** Self-hosted Home Assistant voice assistant integration
**Researched:** 2026-04-12
**Confidence:** HIGH

## Executive Summary

This milestone is a **narrow, security-conscious voice integration**, not a general-purpose AI home admin layer. The research consistently points to the same architecture: keep **Home Assistant as the voice shell, event source of truth, and service executor**, and use **OpenClaw only as Ada’s conversation and decision layer** behind a dedicated Home Assistant voice profile. Experts build this kind of system by preserving clear boundaries: HA owns Assist, Whisper, Piper, event detection, scripts, and speaker routing; OpenClaw handles response generation and limited decision-making.

The recommended direction is to first **narrow the trust boundary** before adding capabilities. Do not reuse the current broad OpenClaw surface for HA voice. Instead, ship one known-good Assist endpoint, add a Wyoming-compatible wake-word service, forward only small allowlisted HA events into OpenClaw, and expose only a tiny approved action surface back into HA via an internal validated ingress. This delivers the milestone without exposing the full HA graph, a long-lived admin token, or broad agent control.

The biggest risks are boundary violations and operational mismatches, not raw feature gaps. The roadmap should explicitly prevent session bleed between voice and other Ada channels, HTTP/auth/network mismatches between HA and OpenClaw, wake-word planning that assumes Home Assistant OS add-ons instead of Kubernetes deployment, and raw event/action bridges that become noisy, unsafe, or loop back on themselves. Build order matters: secure conversation boundary first, then end-to-end voice, then one-way events, then the return action bridge.

## Key Findings

### Recommended Stack

The existing stack is already close to the target architecture. Keep Home Assistant, Wyoming Whisper, Wyoming Piper, Music Assistant, and the deployed OpenClaw gateway. The main additions are not broad platform changes; they are **boundary-shaping components** needed to make the milestone safe and deployable.

**Core technologies:**
- **Home Assistant (`2026.3.4`)**: voice shell, event source, and executor — preserves source-of-truth ownership.
- **Wyoming Whisper (`3.1.0`)**: STT — already deployed and aligned with HA Assist.
- **Wyoming Piper (`2.2.2`)**: TTS — already deployed for spoken Ada responses.
- **OpenClaw gateway**: conversation backend — should be narrowed to a dedicated HA voice profile.
- **Wyoming openWakeWord**: wake-word runtime — best fit for an HA-managed, Kubernetes-friendly wake-word path.
- **HTTP JSON bridges**: event/action transport — simplest narrow contract for HA -> OpenClaw and OpenClaw -> HA.
- **HA scripts/scenes/webhooks/rest_command**: execution and integration surface — keeps HA in control of actions and event forwarding.

**Stack additions worth carrying into requirements/roadmap:**
- One supported Assist-compatible microphone endpoint
- Dedicated OpenClaw HA voice profile/alias with isolated session scope
- Containerized wake-word runtime plus pinned model deployment/update path
- HA-owned `rest_command` event forwarding with versioned payload schemas
- One internal HA action ingress that validates `action_id` against an allowlist

### Expected Features

Requirements should be organized around the user-visible contract and the trust boundary, not around individual services.

**Recommended requirement categories:**
- Conversational Voice Loop
- Wake Word + Endpoint Behavior
- Event-Driven Ada Skills
- Approved Action Surface Back Into Home Assistant
- Failure Handling + Guardrails

**Must have (table stakes):**
- End-to-end spoken conversation from one supported Assist endpoint to Ada and back to speech
- Ada identity consistency across HA config, OpenClaw profile, and spoken output
- At least one deployable wake-word path with explicit fallback
- Small approved HA -> OpenClaw event catalog with structured payloads
- Small approved OpenClaw -> HA action list with clear denial for out-of-scope requests

**Should have (competitive):**
- Brief follow-up turns within a narrow voice interaction
- Ada-style concise response tuning
- Event-aware continuity for recent alerts
- Friendly action paraphrase before execution

**Defer (v2+):**
- Broad whole-home entity discovery
- Shared Telegram/general Ada memory and tools in voice flows
- Open-ended proactive agent behavior
- Large multi-room or multi-user personalization
- Broad custom wake-word rollout across all endpoint classes

### Architecture Approach

The recommended architecture is: **Assist endpoint -> wake word -> HA Assist pipeline -> Whisper -> dedicated OpenClaw HA voice profile -> Piper -> speaker target**. In parallel, HA automations detect a small set of approved events and POST minimal JSON payloads to OpenClaw. If OpenClaw needs something done, it sends a request through one **internal HA ingress** where HA validates `action_id`, executes mapped scripts/services locally, and logs the result.

**Major components:**
1. **Home Assistant** — owns Assist orchestration, event detection, action execution, and playback targeting.
2. **OpenClaw HA voice profile** — generates Ada responses with isolated sessions and restricted tools.
3. **Wake-word service** — supplies one supported Ada wake-word path without assuming HA OS add-ons.
4. **HA event bridge** — filters and normalizes selected home events before forwarding.
5. **HA action bridge** — validates approved action requests and maps them to local HA scripts/scenes/services.

### Critical Pitfalls

These risks should be made explicit in roadmap acceptance criteria.

1. **Reusing the broad OpenClaw assistant surface for HA voice** — avoid by creating a dedicated HA voice profile with separate session scope and restricted tools before any bridge work.
2. **Session contamination across voice, Telegram, and event flows** — avoid by defining voice session identity and isolation rules early.
3. **Transport/auth/network mismatches between HA and OpenClaw** — avoid by choosing one canonical endpoint, validating auth source, and adding a smoke test that uses the same path HA will use.
4. **Designing wake word as if this were Home Assistant OS** — avoid by treating wake word as explicit Kubernetes infrastructure with model storage, deployment, and fallback.
5. **Forwarding raw HA state/events or creating event/action loops** — avoid with allowlisted schemas, source markers, correlation IDs, cooldowns, and idempotency.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Narrow Conversation Boundary
**Rationale:** The current HA snippet implies a broad Ada surface that conflicts with milestone constraints. Fixing trust boundaries must come before adding capability.
**Delivers:** Dedicated OpenClaw HA voice profile/alias, isolated session namespace, Ada persona enforcement, restricted tool allowlist, validated HA -> OpenClaw transport path.
**Addresses:** Conversational Voice Loop, Ada identity consistency, safe refusal behavior.
**Avoids:** Broad Ada reuse, session contamination, transport/auth mismatch.

### Phase 2: End-to-End Voice Path + Wake Word
**Rationale:** Once the conversation boundary is safe, prove the core product promise on one known-good endpoint before expanding into event-driven behavior.
**Delivers:** One supported Assist endpoint, wake-word runtime and model path, HA pipeline wiring, correct speaker target, manual fallback path.
**Uses:** HA Assist, Whisper, Piper, Wyoming wake-word service, optional direct HA playback first.
**Implements:** Core voice loop architecture.

### Phase 3: HA -> OpenClaw Filtered Event Bridge
**Rationale:** One-way event forwarding is lower risk than bidirectional control and unlocks event-driven Ada value without exposing broad context.
**Delivers:** Event catalog, versioned payload schemas, HA automations + `rest_command`, OpenClaw ingest handling, throttling/deduping.
**Addresses:** Event-Driven Ada Skills.
**Avoids:** Raw event firehose, privacy leakage, HA timeout/noise issues.

### Phase 4: OpenClaw -> HA Approved Action Bridge
**Rationale:** Only add control after event flows and boundaries are proven. Keep the bridge tiny and reviewable.
**Delivers:** Single internal HA webhook/action ingress, allowlisted `action_id`s, argument validation, mapped scripts/scenes/services, audit logging, confirmations for impactful actions.
**Addresses:** Approved Action Surface, clear denial/error handling.
**Avoids:** Generic `call_service` sprawl, long-lived broad HA token access, unsafe destructive actions.

### Phase 5: UX Hardening and Routing Polish
**Rationale:** Final polish should happen after the architecture is stable and safe.
**Delivers:** Playback-routing improvements, follow-up tuning, wake-word iteration, observability, persona validation, loop/latency hardening.
**Addresses:** Failure Handling + Guardrails, response targeting, overall livability.
**Avoids:** Persona drift, room confusion, poor diagnosability.

### Phase Ordering Rationale

- Security boundary first, because every later feature depends on a safe HA/OpenClaw contract.
- End-to-end voice before bridges, because the milestone’s core success criterion is spoken Ada interaction.
- One-way events before two-way actions, because read/notify flows are safer than control flows.
- Low-risk approved actions before richer automation, because trust is easier to build than recover.
- UX polish last, because routing sophistication should not block core functionality.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Exact wake-word engine packaging, custom model quality, and endpoint compatibility matrix need implementation validation.
- **Phase 4:** HA action-ingress auth hardening and exact webhook/tool contract should be validated before implementation.
- **Phase 5:** Playback routing details across HA vs Music Assistant may need targeted research if multi-room behavior becomes a milestone requirement.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Dedicated assistant profile, session isolation, and canonical transport validation are straightforward architecture hardening steps.
- **Phase 3:** HA automations plus `rest_command` with small JSON schemas are well-understood patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong repo evidence plus HA-aligned additions; only wake-word packaging details remain implementation-specific. |
| Features | HIGH | Scope is tightly anchored to PROJECT.md, spec, and current milestone constraints. |
| Architecture | MEDIUM | Recommended direction is clear, but exact OpenClaw profile mechanics and action-ingress hardening need validation. |
| Pitfalls | HIGH | Risks are concrete, repo-specific, and consistently identified across research outputs. |

**Overall confidence:** HIGH

### Gaps to Address

- **Endpoint selection:** Decide the first supported microphone endpoint class and where wake-word detection runs for it.
- **Speaker targeting:** Decide the initial response target model: initiating device, fixed room speaker, or explicit HA media target.
- **Wake-word implementation:** Validate whether custom “Ada” / “Hey Ada” quality is good enough for v1 or whether a stock wake word ships first.
- **Action allowlist:** Finalize the exact v1 action IDs and which require confirmation vs outright exclusion.
- **Read surface scope:** Clarify whether OpenClaw gets any narrow read-before-write context beyond event payloads.
- **Event catalog:** Choose the first 2-3 event types for MVP and define payload schemas now rather than letting them drift in implementation.

## Sources

### Primary (HIGH confidence)
- `/Users/andrewmccall/projects/home-ops/.planning/PROJECT.md` — milestone scope, constraints, and source-of-truth architecture
- `/Users/andrewmccall/projects/home-ops/spec/openclaw-home-assistant-voice.md` — integration goal, responsibilities, wake-word requirements, open questions
- `/Users/andrewmccall/projects/home-ops/.planning/research/STACK.md` — stack recommendations and deployment additions
- `/Users/andrewmccall/projects/home-ops/.planning/research/FEATURES.md` — requirement categories, MVP framing, and feature prioritization
- `/Users/andrewmccall/projects/home-ops/.planning/research/PITFALLS.md` — roadmap-critical failure modes and prevention patterns

### Secondary (MEDIUM confidence)
- `/Users/andrewmccall/projects/home-ops/.planning/research/ARCHITECTURE.md` — target architecture and build ordering
- `https://www.home-assistant.io/voice_control/` — HA voice pipeline patterns
- `https://www.home-assistant.io/voice_control/about_wake_word/` — wake-word deployment options and Wyoming/openWakeWord direction
- `https://www.home-assistant.io/integrations/rest_command/` — HA outbound event forwarding pattern
- `https://www.home-assistant.io/docs/automation/trigger/` — webhook trigger pattern for narrow action ingress

### Tertiary (LOW confidence)
- None identified; remaining uncertainty is implementation detail, not missing direction.

---
*Research completed: 2026-04-12*
*Ready for roadmap: yes*
