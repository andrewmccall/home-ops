---
phase: 01-shared-ada-voice-contract
plan: 01
subsystem: infra
tags: [kubernetes, networkpolicy, openclaw, home-assistant, gateway]
requires: []
provides:
  - "House namespace ingress path to OpenClaw gateway pod port 18790"
  - "Documented Wave 1 checkpoint findings for sender mapping and system prompt config"
affects: [phase-1, openclaw, home-assistant, gateway-auth]
tech-stack:
  added: []
  patterns:
    - "Use namespace-scoped NetworkPolicy for direct in-cluster HA voice traffic"
    - "Document unverified raw-config paths in SUMMARY before downstream config plans depend on them"
key-files:
  created:
    - cluster/apps/openclaw/instance/gateway-allow-house-voice.yaml
    - .planning/phases/01-shared-ada-voice-contract/01-01-SUMMARY.md
  modified:
    - cluster/apps/openclaw/instance/kustomization.yaml
key-decisions:
  - "Allow all pods in the trusted house namespace to reach OpenClaw on pod port 18790 with no podSelector."
  - "Proceed with accepted assumptions for sender mapping and systemPrompt key paths because CRD/runtime inspection did not expose a stronger source of truth."
patterns-established:
  - "Direct HA voice traffic targets the OpenClaw service on 18789 while NetworkPolicy protects pod port 18790."
  - "When OpenClaw raw config is schema-light, plan summaries carry the checkpoint decision that downstream plans must honor."
requirements-completed: [VOICE-03, VOICE-04]
duration: 9 min
completed: 2026-04-12
---

# Phase 1 Plan 1: Network path and OpenClaw schema checkpoint Summary

**Direct house-to-OpenClaw gateway access is open on pod port 18790, and Plan 02 now has explicit accepted defaults for sender mapping, voice prompt placement, and Andrew identity.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-12T21:26:12Z
- **Completed:** 2026-04-12T21:35:12Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added a dedicated NetworkPolicy allowing the `house` namespace to reach OpenClaw pods on TCP 18790 only.
- Updated the instance kustomization so Flux will deploy the new policy with the rest of the OpenClaw instance resources.
- Investigated the OpenClaw CRD, runtime config, logs, and upstream code search, then documented accepted assumptions for Plan 02 where the raw-config schema remained opaque.

## Task Commits

Each task was committed atomically where repo changes existed:

1. **Task 1: Create NetworkPolicy for house -> openclaw direct voice path** - `62195c85` (feat)
2. **Task 2: Verify OpenClaw config key paths for sender mapping and system prompt** - documented in the plan completion commit

## Files Created/Modified

- `cluster/apps/openclaw/instance/gateway-allow-house-voice.yaml` - permits ingress from the `house` namespace to OpenClaw pod port 18790.
- `cluster/apps/openclaw/instance/kustomization.yaml` - includes the new NetworkPolicy in the OpenClaw instance resource list.
- `.planning/phases/01-shared-ada-voice-contract/01-01-SUMMARY.md` - records the Wave 1 checkpoint findings that Plan 02 must follow.

## CRD Verification Findings

1. **Sender mapping config key path:** accept assumption `spec.config.raw.gateway.http.endpoints.chatCompletions.auth.tokens[]` with `envVar` + `senderId`.
2. **System prompt config key path:** accept assumption `spec.config.raw.agents.defaults.systemPrompt`.
3. **Andrew's Telegram sender ID string:** accept assumption `"andrew"`.
4. **Other relevant findings about gateway auth tokens:**
   - The running effective config exposes a gateway-wide token at `gateway.auth.mode: token` and `gateway.auth.token`.
   - The current effective config does not expose any per-token sender mapping block or systemPrompt override.
   - The OpenClaw CRD schema inspection did not provide a detailed schema for `spec.config.raw`, so it could not confirm the raw config subtree.
   - Runtime config inspection of `/home/openclaw/.openclaw/openclaw.json` showed only the currently merged keys, not hidden optional schema.
   - GitHub code search against the upstream `openclaw/openclaw` repo did not return clearer matches for `senderId` or `systemPrompt`.

## Decisions Made

- Trusted the `house` namespace boundary and kept the ingress rule namespace-scoped without a podSelector, matching the plan rationale that HA pod labels are not stable enough to depend on.
- Advanced Plan 02 using explicit accepted assumptions rather than inventing new config structure, because the checkpoint investigation did not produce a stronger source of truth.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- OpenClaw's CRD and running merged config did not expose definitive raw-config schema for sender mapping or voice prompt overrides, so the plan proceeded on accepted assumptions after direct cluster and upstream search.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 can now use `gateway.http.endpoints.chatCompletions.auth.tokens[]` and `agents.defaults.systemPrompt` as the explicit accepted defaults.
- Plan 03 still depends on human secret generation, SOPS encryption, and HA-side configuration after the OpenClaw-side changes land.

---
*Phase: 01-shared-ada-voice-contract*
*Completed: 2026-04-12*
