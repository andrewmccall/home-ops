---
phase: 01-shared-ada-voice-contract
plan: 02
subsystem: infra
tags: [openclaw, home-assistant, sops, prompt, smoke-tests]
requires:
  - phase: 01
    provides: "Accepted sender mapping and systemPrompt defaults from the Wave 1 checkpoint"
provides:
  - "Dedicated HA voice token secret template for OpenClaw"
  - "Voice-first OpenClaw sender mapping and system prompt"
  - "Smoke and manual validation artifacts for HA voice"
affects: [phase-1, openclaw, home-assistant, validation]
tech-stack:
  added: []
  patterns:
    - "Commit a SOPS-encrypted placeholder secret instead of any live gateway token"
    - "Keep HA voice on the shared Ada surface by mapping the dedicated token to the Andrew sender identity"
key-files:
  created:
    - cluster/apps/openclaw/instance/openclaw-ha-voice-secret.sops.yaml
    - scripts/test-ha-voice-token.sh
    - .planning/phases/01-shared-ada-voice-contract/MANUAL-TEST.md
    - .planning/phases/01-shared-ada-voice-contract/01-02-SUMMARY.md
  modified:
    - cluster/apps/openclaw/instance/openclaw-instance.yaml
    - cluster/apps/openclaw/instance/kustomization.yaml
    - cluster/apps/openclaw/instance/ha-config-snippet.yaml
key-decisions:
  - "Use the accepted Wave 1 defaults: gateway.http.endpoints.chatCompletions.auth.tokens[] and agents.defaults.systemPrompt."
  - "Store only a SOPS-encrypted placeholder token in git; the real HA voice token is generated and replaced during Plan 03."
patterns-established:
  - "HA voice uses its own token but resolves to the shared Andrew sender identity."
  - "Phase verification combines a curl-based smoke script with a manual Telegram-to-HA continuity checklist."
requirements-completed: [VOICE-03, VOICE-04, SAFE-02, SAFE-03]
duration: 7 min
completed: 2026-04-12
---

# Phase 1 Plan 2: OpenClaw HA voice config and test harness Summary

**OpenClaw now has a dedicated HA voice token path, a voice-first Ada prompt, and the smoke/manual checks needed to verify shared-context behavior end to end.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-12T21:29:56Z
- **Completed:** 2026-04-12T21:36:56Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added a SOPS-encrypted HA voice token secret template and wired it into the OpenClaw instance env sources.
- Added the accepted sender-mapping block and a voice-first system prompt that keeps Ada brief and explicitly denies blocked home-admin actions.
- Added `scripts/test-ha-voice-token.sh` and `MANUAL-TEST.md` so Plan 03 has both smoke and manual verification paths ready.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create token secret + update OpenClaw instance config with sender mapping and voice prompt** - `1b327b31` (feat)
2. **Task 2: Create smoke test script and manual test checklist** - `b7faf134` (test)

## Files Created/Modified

- `cluster/apps/openclaw/instance/openclaw-ha-voice-secret.sops.yaml` - valid SOPS-encrypted placeholder manifest for the dedicated HA voice token.
- `cluster/apps/openclaw/instance/openclaw-instance.yaml` - adds `envFrom`, HA token sender mapping, and the voice-first Ada system prompt.
- `cluster/apps/openclaw/instance/kustomization.yaml` - includes the HA voice secret resource.
- `cluster/apps/openclaw/instance/ha-config-snippet.yaml` - documents the direct in-cluster HA configuration and secret placement.
- `scripts/test-ha-voice-token.sh` - smoke test helper for identity, denial behavior, and memory/tool access.
- `.planning/phases/01-shared-ada-voice-contract/MANUAL-TEST.md` - manual Telegram-to-HA continuity and voice quality checklist.

## Decisions Made

- Reused the shared sender identity `"andrew"` for HA voice so `session.scope: per-sender` can preserve continuity with Telegram.
- Put the refusal behavior directly in `agents.defaults.systemPrompt` so blocked home-admin requests are denied before later HA-side action enforcement exists.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `sops` initially inferred the wrong file type from a temporary filename during template generation; regenerating from a `.yaml` temp file produced the expected Kubernetes manifest.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 can now replace the encrypted placeholder with a real token value, update HA PVC config, and run the smoke/manual checks without inventing new artifacts.
- The actual end-to-end verification still depends on manual HA-side changes and a real deployed token.

---
*Phase: 01-shared-ada-voice-contract*
*Completed: 2026-04-12*
