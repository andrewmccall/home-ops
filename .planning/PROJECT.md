# Home Ops

## What This Is

This repo manages the self-hosted home infrastructure stack across Kubernetes, Home Assistant, Music Assistant, and OpenClaw. The current milestone extends that stack so Home Assistant can serve as the voice shell while OpenClaw answers as Ada through the full shared Ada surface, with Home Assistant still acting as the executor for approved home actions.

## Core Value

Home Assistant and adjacent services should work together as a reliable self-hosted home operations platform without giving AI agents broader home control than they need.

## Current Milestone: v1.0 Ada Home Assistant Voice

**Goal:** Deliver a deployable Home Assistant + OpenClaw voice assistant flow where Ada handles conversation through the full shared OpenClaw surface, wake word support is part of the design, Home Assistant can forward filtered events to OpenClaw, and OpenClaw can use a narrow approved action surface back into Home Assistant.

**Target features:**
- End-to-end Assist -> OpenClaw -> Ada -> Piper voice path
- Full shared Ada/OpenClaw voice surface reused for Home Assistant voice conversations
- Ada identity enforced in Home Assistant and OpenClaw config
- Wake word support for Ada, including deployment/update approach and fallback
- Narrow Home Assistant -> OpenClaw event bridge with structured payloads
- Narrow approved OpenClaw -> Home Assistant action surface

## Requirements

### Validated

- ✓ Home Assistant is already deployed with Wyoming Whisper and Piper services for speech input/output plumbing — inferred from `cluster/apps/house/home-assistant/home-assistant.yaml`
- ✓ Music Assistant is already deployed as an audio routing component in the home stack — inferred from `cluster/apps/house/music-assistant/music-assistant.yaml`
- ✓ OpenClaw is already deployed with gateway chat completions enabled and an Ada-oriented Home Assistant conversation snippet — inferred from `cluster/apps/openclaw/instance/openclaw-instance.yaml` and `cluster/apps/openclaw/instance/ha-config-snippet.yaml`

### Active

- [ ] User can speak to an Assist-compatible endpoint and receive a spoken reply from Ada via OpenClaw
- [ ] User can access Ada's full shared OpenClaw surface and conversation context from Home Assistant voice
- [ ] Wake word support for Ada is deployed or clearly installable, updatable, and has fallback behavior
- [ ] Home Assistant can forward filtered, structured events to OpenClaw without exposing the full home graph
- [ ] OpenClaw can trigger a narrow, approved action surface back into Home Assistant

### Out of Scope

- Full Home Assistant admin access — explicitly excluded by the milestone spec
- Unrestricted whole-home entity discovery or broad MCP exposure — breaks the intended security boundary
- Dashboard management, automation authoring, file editing, add-on management, and backup/restore access — not part of the first integration cut

## Context

- The existing Home Assistant deployment already runs Wyoming Whisper and Piper containers plus persistent data volumes.
- The existing OpenClaw deployment exposes the chat completions endpoint and includes an HA config snippet that names the assistant Ada.
- Music Assistant is already present and can be used where speaker routing benefits from it.
- This repo did not previously have `.planning/` state, so this milestone initializes the first tracked GSD planning artifacts.
- The milestone scope intentionally reuses the full shared Ada/OpenClaw voice surface instead of a dedicated restricted HA-only profile.

## Constraints

- **Action Safety**: Even with the full shared Ada/OpenClaw surface, destructive or broad Home Assistant admin actions remain explicitly gated — keep execution narrow and reviewable.
- **Architecture**: Home Assistant remains the source of truth for event detection and service execution — keep automation ownership there.
- **Compatibility**: Reuse the existing Home Assistant Whisper/Piper and OpenClaw gateway setup where possible — avoid unnecessary new infrastructure.
- **Persona**: The assistant identity must be Ada across Home Assistant, OpenClaw, and spoken responses — the voice UX depends on it.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Home Assistant Assist as the voice shell and OpenClaw as the conversation backend | Existing manifests already point this direction and it preserves Home Assistant orchestration | — Pending |
| Reuse the full shared Ada/OpenClaw surface for Home Assistant voice | User explicitly chose full shared Ada session/context instead of a dedicated restricted HA voice profile | — Pending |
| Keep Home Assistant action execution on a narrow approved surface even though voice uses full Ada context | Preserves a reviewable home-control boundary while allowing richer conversational context | — Pending |
| Initialize milestone tracking at v1.0 Ada Home Assistant Voice | This repo had no existing GSD milestone state and the user approved the milestone label | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 after milestone v1.0 initialization*
