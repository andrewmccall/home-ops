# Phase 1: Shared Ada Voice Contract - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 1-Shared Ada Voice Contract
**Areas discussed:** HA -> OpenClaw transport and auth path, shared Ada session/context keying, blocked home-action denials, Ada spoken style and response shape

---

## HA -> OpenClaw transport and auth path

| Option | Description | Selected |
|--------|-------------|----------|
| Direct in-cluster service URL from Home Assistant to the OpenClaw service | Simplest in-cluster path; avoids ingress and TLS host-header complexity | ✓ |
| Keep the current internal ingress hostname path from the HA snippet | Reuses existing example but keeps ingress/network-policy coupling | |
| Use HTTPS ingress plus explicit cert trust inside Home Assistant | Stronger edge-style path but more setup for this phase | |

**User's choice:** Direct in-cluster service URL from Home Assistant to the OpenClaw service  
**Notes:** Within the same area, the user also chose a dedicated HA voice gateway token stored as a Home Assistant secret instead of the existing general gateway token.

---

## Shared Ada session/context keying

| Option | Description | Selected |
|--------|-------------|----------|
| Treat HA voice as the same primary Andrew/Ada identity used in Telegram and other OpenClaw channels | Maximum continuity for the approved full shared Ada experience | ✓ |
| Use a Satellite 1-specific sender identity but merge it into Andrew's shared Ada memory | Adds some device traceability while keeping most shared context | |
| Use a room/device identity for voice and only selectively sync into shared Ada context | More controlled but no longer the simplest full shared-context path | |

**User's choice:** Same primary Andrew/Ada identity  
**Notes:** User explicitly asked to leave a todo to make this more robust later rather than expanding Phase 1.

---

## Blocked home-action denials

| Option | Description | Selected |
|--------|-------------|----------|
| Deny first in the OpenClaw voice policy/prompt, with Home Assistant-side enforcement later as a backstop | Gives immediate Ada refusals while preserving a later hard enforcement layer | ✓ |
| Deny only once requests reach the Home Assistant side | Simpler now but weaker user-facing boundary in voice mode | |
| Rely mostly on Home Assistant exposed-entity controls instead of explicit Ada denial rules | Leaves refusals implicit and less reviewable | |

**User's choice:** Deny first in the OpenClaw voice policy/prompt, with Home Assistant-side enforcement later as a backstop  
**Notes:** This keeps Phase 1 focused on the conversational contract while preserving the narrow approved action bridge for a later phase.

---

## Ada spoken style and response shape

| Option | Description | Selected |
|--------|-------------|----------|
| Brief by default, friendly, and voice-first; expand only when asked | Best fit for speaker UX while preserving Ada personality | ✓ |
| Full Ada conversational style, even if some spoken replies are longer | Richer personality but less voice-friendly | |
| Very terse assistant style with minimal personality | Efficient but risks losing Ada's character | |

**User's choice:** Brief by default, friendly, and voice-first; expand only when asked  
**Notes:** This is a voice-mode behavior preference, not a separate assistant persona.

---

## the agent's Discretion

- Exact secret naming and Home Assistant secret management layout
- Exact service DNS and config placement details
- Exact prompt wording that delivers the approved behavior

## Deferred Ideas

- Make shared identity/session handling more robust in a later phase once the initial shared Ada contract is proven
