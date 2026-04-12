# Requirements: Home Ops

**Defined:** 2026-04-12
**Core Value:** Home Assistant and adjacent services should work together as a reliable self-hosted home operations platform without giving AI agents broader home control than they need.

## v1 Requirements

### Conversational Voice Loop

- [ ] **VOICE-01**: User can speak to Satellite 1 and receive a spoken reply from Ada through the Home Assistant -> OpenClaw -> Piper voice path.
- [ ] **VOICE-02**: User hears Ada replies on the initiating or explicitly assigned speaker target instead of an unrelated room.
- [ ] **VOICE-03**: User experiences a consistent Ada identity across Home Assistant assistant naming, OpenClaw behavior, and spoken replies.
- [ ] **VOICE-04**: User receives a clear spoken refusal when asking Ada for out-of-scope admin or unrestricted home-control tasks.

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
- [ ] **SAFE-02**: User's home voice interactions do not inherit unrelated Telegram or general OpenClaw session context.
- [ ] **SAFE-03**: User cannot use Ada to access broad Home Assistant admin capabilities, unrestricted entity discovery, or destructive out-of-scope actions.

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
| VOICE-01 | TBA | Pending |
| VOICE-02 | TBA | Pending |
| VOICE-03 | TBA | Pending |
| VOICE-04 | TBA | Pending |
| WAKE-01 | TBA | Pending |
| WAKE-02 | TBA | Pending |
| WAKE-03 | TBA | Pending |
| EVENT-01 | TBA | Pending |
| EVENT-02 | TBA | Pending |
| EVENT-03 | TBA | Pending |
| EVENT-04 | TBA | Pending |
| ACTN-01 | TBA | Pending |
| ACTN-02 | TBA | Pending |
| ACTN-03 | TBA | Pending |
| ACTN-04 | TBA | Pending |
| SAFE-01 | TBA | Pending |
| SAFE-02 | TBA | Pending |
| SAFE-03 | TBA | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 0
- Unmapped: 18

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 after initial definition*
