# Requirements: Home Ops

**Defined:** 2026-04-12
**Core Value:** Home Assistant and adjacent services should work together as a reliable self-hosted home operations platform without giving AI agents broader home control than they need.

## v1 Requirements

### Conversational Voice Loop

- [ ] **VOICE-01**: User can speak to Satellite 1 and receive a spoken reply from Ada through the Home Assistant -> OpenClaw -> Piper voice path.
- [ ] **VOICE-02**: User hears Ada replies on the initiating or explicitly assigned speaker target instead of an unrelated room.
- [ ] **VOICE-03**: User experiences a consistent Ada identity across Home Assistant assistant naming, OpenClaw behavior, and spoken replies.
- [ ] **VOICE-04**: User can continue the same Ada conversation context across Home Assistant voice and Telegram or other general OpenClaw channels.

### Wake Word + Endpoint Behavior

- [ ] **WAKE-01**: User can wake Ada on Satellite 1 with a shipped custom wake word model for "Ada" or "Hey Ada".
- [ ] **WAKE-02**: User can deploy and update the custom Ada wake word model in the Kubernetes-based Home Assistant voice stack.
- [ ] **WAKE-03**: User can still activate Ada through a manual Assist fallback if the wake word runtime is unavailable.

### Event-Driven Ada Skills

- [ ] **EVENT-01**: User can receive Ada workflows for Andrew arrival and departure events.
- [ ] **EVENT-02**: User can receive Ada workflows for office occupancy state changes.
- [ ] **EVENT-03**: User receives event-driven Ada behavior only from the approved structured event catalog, not from raw whole-home event forwarding.
- [ ] **EVENT-04**: User can receive an approved Ada reaction to those events as speech, notification, follow-up question, or memory/note behavior.

### Approved Action Surface

- [ ] **ACTN-01**: User can have Ada send an approved spoken announcement through Home Assistant playback.
- [ ] **ACTN-02**: User can have Ada send an approved notification.
- [ ] **ACTN-03**: User can have Ada trigger an approved Home Assistant script or scene.
- [ ] **ACTN-04**: User receives confirmation for approved actions and a clear denial for disallowed actions.

### Failure Handling + Guardrails

- [ ] **SAFE-01**: User receives a clear failure response when the voice pipeline or action bridge cannot complete a request.
- [ ] **SAFE-02**: User can access Ada's broader OpenClaw memory and tool-backed conversational context from Home Assistant voice interactions.
- [ ] **SAFE-03**: User receives a clear denial when requesting destructive or explicitly blocked Home Assistant admin actions, even though Ada uses the full shared OpenClaw surface.

## v2 Requirements

### Voice Expansion

- **VOICE-05**: User can use the Ada voice experience from additional endpoint classes beyond Satellite 1.
- **VOICE-06**: User can use richer multi-room routing and playback selection behaviors.

### Event Expansion

- **EVENT-05**: User can receive Ada workflows for a broader approved home event catalog beyond arrival/departure and office occupancy.
- **EVENT-06**: User can use more advanced event summarization and continuity across recent alerts.

### Action Expansion

- **ACTN-05**: User can use a larger but still reviewable action allowlist after the narrow bridge is validated.
- **ACTN-06**: User can use constrained read-before-write home context for selected approved actions.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full Home Assistant admin access | Explicitly excluded by the milestone spec and breaks the narrow-surface trust boundary |
| Unrestricted whole-home entity discovery or MCP exposure | Conflicts with the approved architecture and would expand context too broadly |
| Dashboard management, automation authoring, file or YAML editing, add-on management, backup or restore access | Outside the first integration cut and too risky for voice-driven control |
| Generic arbitrary Home Assistant service execution | The milestone requires a small approved action surface instead of open-ended control |
| Multi-user personalization and shared cross-channel Ada memory | Adds identity and privacy complexity before the core voice path is proven |
| Large multi-room wake-word rollout across every endpoint class | Over-scopes the milestone before one known-good endpoint is stable |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VOICE-01 | Phase 2 | Pending |
| VOICE-02 | Phase 2 | Pending |
| VOICE-03 | Phase 1 | Pending |
| VOICE-04 | Phase 1 | Pending |
| WAKE-01 | Phase 2 | Pending |
| WAKE-02 | Phase 2 | Pending |
| WAKE-03 | Phase 2 | Pending |
| EVENT-01 | Phase 3 | Pending |
| EVENT-02 | Phase 3 | Pending |
| EVENT-03 | Phase 3 | Pending |
| EVENT-04 | Phase 3 | Pending |
| ACTN-01 | Phase 4 | Pending |
| ACTN-02 | Phase 4 | Pending |
| ACTN-03 | Phase 4 | Pending |
| ACTN-04 | Phase 4 | Pending |
| SAFE-01 | Phase 2 | Pending |
| SAFE-02 | Phase 1 | Pending |
| SAFE-03 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 after roadmap revision*
