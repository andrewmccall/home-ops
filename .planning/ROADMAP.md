# Roadmap: Home Ops

## Overview

This milestone delivers an Ada voice experience on top of the existing Home Assistant and OpenClaw stack with the revised scope: Home Assistant voice reuses the full shared Ada/OpenClaw surface and shared conversation context, while Home Assistant remains the source of truth for event detection and approved action execution. The phases move from establishing that shared Ada contract, to launching Satellite 1 voice and wake-word behavior, to adding the initial event catalog, and finally to enabling the narrow approved home-action surface.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Shared Ada Voice Contract** - Home Assistant voice uses the full shared Ada surface while preserving identity and action guardrails.
- [ ] **Phase 2: Satellite 1 Voice Launch** - Satellite 1 can reach Ada by custom wake word or manual fallback and get the reply on the right target.
- [ ] **Phase 3: Event-Driven Ada Skills** - Approved Home Assistant events trigger structured Ada workflows from the initial event catalog.
- [ ] **Phase 4: Approved Home Action Bridge** - Ada can invoke only approved Home Assistant actions and confirm or deny them clearly.

## Phase Details

### Phase 1: Shared Ada Voice Contract
**Goal**: Users can talk to Home Assistant voice as the same shared Ada they use elsewhere, while unsafe home-control requests still stay blocked.
**Depends on**: Nothing (first phase)
**Requirements**: VOICE-03, VOICE-04, SAFE-02, SAFE-03
**Success Criteria** (what must be TRUE):
  1. User hears and experiences a consistent Ada identity across Home Assistant assistant naming, OpenClaw behavior, and spoken replies.
  2. User can continue the same Ada conversation context between Home Assistant voice and Telegram or other general OpenClaw channels.
  3. User can access Ada's broader shared memory and tool-backed conversational context from a Home Assistant voice interaction.
  4. User receives a clear denial when asking for destructive, admin, or otherwise blocked Home Assistant actions even though Ada uses the full shared surface.
**Plans**: 3 plans
Plans:
- [x] 01-01-PLAN.md — Network path + OpenClaw CRD schema verification
- [x] 01-02-PLAN.md — Token, OpenClaw config (sender mapping + voice prompt), test harness
- [ ] 01-03-PLAN.md — HA wiring (SOPS encrypt, PVC config) + end-to-end verification

### Phase 01.1: HA OpenClaw Shared Session Bridge (INSERTED)

**Goal:** Users can keep using Home Assistant's supported OpenAI Conversation setup while a lightweight bridge preserves shared Ada identity, shared cross-channel continuity, and explicit degraded-mode behavior on the HA -> OpenClaw path.
**Requirements**: VOICE-03, VOICE-04, SAFE-02, SAFE-03
**Depends on:** Phase 1
**Success Criteria** (what must be TRUE):
  1. Home Assistant can use its supported OpenAI Conversation setup against the new bridge without requiring a custom Home Assistant integration or YAML conversation config.
  2. Home Assistant voice and Telegram can continue the same shared Ada conversation through one durable Andrew/Ada identity.
  3. Home Assistant voice still reaches Ada's broader OpenClaw memory and tool-backed context through the bridge path.
  4. If continuity cannot be preserved, the bridge surfaces degraded mode clearly instead of silently creating a separate session.
  5. LiteLLM is removed once the bridge fully owns the HA-facing proxy path.
**Plans:** 3/4 plans executed

Plans:
- [x] 01.1-01-PLAN.md — Enable OpenClaw responses support + add bridge smoke harness
- [x] 01.1-02-PLAN.md — Deploy HA-facing bridge + move spoof ingress/TLS ownership
- [x] 01.1-03-PLAN.md — Prepare HA cutover + manual continuity/degraded-mode verification
- [ ] 01.1-04-PLAN.md — Remove LiteLLM after successful bridge cutover

### Phase 2: Satellite 1 Voice Launch
**Goal**: Users can reach Ada from Satellite 1 through the Home Assistant voice pipeline with launch wake-word, fallback, routing, and failure behavior in place.
**Depends on**: Phase 1
**Requirements**: VOICE-01, VOICE-02, WAKE-01, WAKE-02, WAKE-03, SAFE-01
**Success Criteria** (what must be TRUE):
  1. User can speak to Satellite 1 and receive a spoken Ada reply through the Home Assistant -> OpenClaw -> Piper voice path on the initiating or explicitly assigned speaker target.
  2. User can wake Ada on Satellite 1 with the shipped custom wake word model for "Ada" or "Hey Ada".
  3. An operator can deploy and update the custom Ada wake word model in the Kubernetes-based voice stack without replacing the rest of the voice pipeline.
  4. User can still activate Ada through a manual Assist fallback if the wake word runtime is unavailable.
  5. User receives a clear failure response when the voice pipeline cannot complete a request.
**Plans**: TBD

### Phase 3: Event-Driven Ada Skills
**Goal**: Users can receive Ada behaviors from the initial approved Home Assistant event catalog without exposing raw whole-home events.
**Depends on**: Phase 2
**Requirements**: EVENT-01, EVENT-02, EVENT-03, EVENT-04
**Success Criteria** (what must be TRUE):
  1. User can receive Ada workflows for Andrew arrival and departure events.
  2. User can receive Ada workflows for office occupancy state changes.
  3. User receives event-driven Ada behavior only from the approved structured event catalog, not from raw whole-home event forwarding.
  4. User can receive an approved Ada reaction to those events as speech, notification, follow-up question, or memory/note behavior.
**Plans**: TBD

### Phase 4: Approved Home Action Bridge
**Goal**: Users can ask Ada to perform a narrow approved set of Home Assistant actions with clear confirmation and denial behavior.
**Depends on**: Phase 2, Phase 3
**Requirements**: ACTN-01, ACTN-02, ACTN-03, ACTN-04
**Success Criteria** (what must be TRUE):
  1. User can have Ada send an approved spoken announcement through Home Assistant playback.
  2. User can have Ada send an approved notification.
  3. User can have Ada trigger an approved Home Assistant script or scene.
  4. User receives confirmation for approved actions and a clear denial for disallowed actions.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 1.1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Shared Ada Voice Contract | 2/3 | Blocked | - |
| 1.1. HA OpenClaw Shared Session Bridge | 0/4 | Planned | - |
| 2. Satellite 1 Voice Launch | 0/TBD | Not started | - |
| 3. Event-Driven Ada Skills | 0/TBD | Not started | - |
| 4. Approved Home Action Bridge | 0/TBD | Not started | - |
