# Phase 1: Shared Ada Voice Contract - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 establishes Home Assistant voice as the same shared Ada/OpenClaw assistant surface used elsewhere, while preserving Ada identity and denying destructive or blocked home-admin actions up front. This phase defines the conversation contract, transport path, identity mapping, and denial behavior; wake word, event forwarding, and the approved HA action bridge belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### HA -> OpenClaw transport and auth
- **D-01:** Home Assistant voice should call OpenClaw over a direct in-cluster service URL rather than the existing ingress hostname path.
- **D-02:** Home Assistant should use a dedicated HA voice gateway token stored as a Home Assistant secret, not the shared general gateway token.

### Shared Ada identity and session behavior
- **D-03:** Home Assistant voice should use the same primary Andrew/Ada identity that is already used in Telegram and other OpenClaw channels.
- **D-04:** Phase 1 should deliberately preserve shared cross-channel Ada conversation continuity instead of isolating Home Assistant voice into a separate session namespace.

### Guardrail enforcement
- **D-05:** Blocked or destructive home-action requests should be denied first in the OpenClaw voice policy/prompt.
- **D-06:** Later Home Assistant-side action enforcement remains the backstop, but Phase 1 must already make Ada refuse blocked actions clearly at the voice layer.

### Voice response shape
- **D-07:** Ada should sound friendly and voice-first in Home Assistant voice mode.
- **D-08:** Spoken replies should be brief by default and only expand when the user asks for more detail.

### the agent's Discretion
- Exact secret key names, Kubernetes secret wiring, and Home Assistant secret file layout
- Exact direct service DNS form and config placement inside Home Assistant
- Exact OpenClaw prompt wording, as long as it preserves Ada identity, shared context, and clear blocked-action denials
- Exact spoken wording patterns for brief-by-default responses

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone scope and locked requirements
- `.planning/PROJECT.md` — milestone goal, constraints, and explicit decision to reuse the full shared Ada/OpenClaw voice surface
- `.planning/REQUIREMENTS.md` §Conversational Voice Loop — Phase 1 user-facing contract for identity consistency and shared context
- `.planning/REQUIREMENTS.md` §Failure Handling + Guardrails — blocked-action denial and full-surface guardrail requirements
- `.planning/ROADMAP.md` §Phase 1: Shared Ada Voice Contract — fixed phase goal, dependency order, and success criteria

### Existing integration direction
- `spec/openclaw-home-assistant-voice.md` — overall voice integration goal, Ada persona requirement, wake word requirement, and scoped HA/OpenClaw responsibilities
- `cluster/apps/openclaw/instance/ha-config-snippet.yaml` — current HA conversation snippet using Ada, Satellite 1, and the full shared Ada session
- `cluster/apps/openclaw/instance/openclaw-instance.yaml` §spec.config.raw — current OpenClaw gateway, session, Telegram, and chat-completions configuration
- `cluster/apps/house/home-assistant/home-assistant.yaml` §controllers.voice and service.voice — existing Whisper/Piper Wyoming voice services already deployed in Home Assistant

### Transport and operational constraints
- `cluster/apps/openclaw/instance/gateway-ingress.yaml` — existing ingress-based path that Phase 1 is intentionally not using for HA voice
- `cluster/apps/openclaw/instance/gateway-allow-internal-nginx.yaml` — current ingress NetworkPolicy shape relevant to why direct in-cluster service access is preferred
- `.planning/research/SUMMARY.md` — research findings, especially the now-overridden recommendation for a dedicated restricted HA voice profile and the remaining operational risks

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cluster/apps/openclaw/instance/ha-config-snippet.yaml`: Starting point for the Home Assistant conversation configuration, assistant naming, and Satellite 1 wiring comments
- `cluster/apps/openclaw/instance/openclaw-instance.yaml`: Existing OpenClaw gateway and session configuration that Phase 1 will extend rather than replace
- `cluster/apps/house/home-assistant/home-assistant.yaml`: Existing Home Assistant voice deployment with Whisper and Piper already running in-cluster

### Established Patterns
- OpenClaw instance configuration is managed through `spec.config.raw` in the `OpenClawInstance` manifest.
- Home Assistant voice services already rely on Wyoming-sidecar style integrations; Phase 1 should modify conversation routing, not rebuild STT/TTS infrastructure.
- The repo already documents a full Ada session path through Home Assistant; Phase 1 formalizes and hardens that path around the approved shared-context decision.

### Integration Points
- Home Assistant conversation backend config that points voice traffic at the OpenClaw service
- Home Assistant secret storage for the dedicated HA voice token
- OpenClaw gateway auth/token configuration used by the HA voice client
- Shared sender/session identity mapping between HA voice and the Andrew/Ada primary identity

</code_context>

<specifics>
## Specific Ideas

- Reuse the "full Ada" direction already shown in `ha-config-snippet.yaml`, but switch the connection to direct in-cluster service access.
- Keep Home Assistant voice as the same Ada the user already talks to elsewhere, rather than inventing a special HA-only assistant persona.
- Make Ada sound good over speakers: friendly, brief, and conversational without drifting into long chat-style monologues.

</specifics>

<deferred>
## Deferred Ideas

- Make shared identity/session handling more robust than a single primary Andrew/Ada identity once Phase 1 is proven.

</deferred>

---

*Phase: 01-shared-ada-voice-contract*
*Context gathered: 2026-04-12*
