# Technology Stack

**Project:** Home Ops  
**Milestone:** v1.0 Ada Home Assistant Voice  
**Researched:** 2026-04-12

## Existing Stack

These components are already present in the repo and should be treated as baseline, not new scope:

| Component | Version / State | Purpose | Evidence |
|---|---|---|---|
| Home Assistant | `2026.3.4` | Voice shell and orchestration | `cluster/apps/house/home-assistant/home-assistant.yaml` |
| Wyoming Whisper | `rhasspy/wyoming-whisper:3.1.0` | STT | same |
| Wyoming Piper | `rhasspy/wyoming-piper:2.2.2` | TTS | same |
| Music Assistant | Deployed | Optional speaker and routing support | `cluster/apps/house/music-assistant/music-assistant.yaml` |
| OpenClaw gateway | Deployed, chat completions enabled | Conversation backend | `cluster/apps/openclaw/instance/openclaw-instance.yaml` |
| Ada HA snippet | Present | Existing HA conversation direction | `cluster/apps/openclaw/instance/ha-config-snippet.yaml` |

## Needed Additions

### 1. Supported Assist endpoint

Add one explicitly supported Assist-compatible microphone endpoint for v1.0. The repo already has server-side voice services, but it does not yet declare the first known-good endpoint device.

**Recommendation:** support one HA-native endpoint first instead of designing around multiple hardware classes at once.

### 2. Wake word stack

Add a Wyoming-compatible wake word service, with a deployable path for an `Ada` / `Hey Ada` model.

**Recommended components:**
- `rhasspy/wyoming-openwakeword`
- local model storage for custom wake word artifacts
- version-pinned image and model deployment path

**Why:** Home Assistant's local voice flow already aligns with Wyoming services, and the milestone requires wake word selection/training, update flow, and fallback behavior.

**Fallback:** if custom Ada wake word quality is not yet good enough, support push-to-talk or a temporary stock wake word without blocking the entire milestone.

### 3. Dedicated OpenClaw HA voice profile

Create a dedicated Home Assistant voice-facing OpenClaw profile or alias instead of reusing the broad `openclaw:main` surface.

That profile should:
- enforce the Ada persona
- keep voice sessions isolated from Telegram/general chat
- use a restricted tool allowlist
- avoid broad file, web, GitHub, or admin capabilities

### 4. Home Assistant conversation hardening

Keep Home Assistant as the voice shell and explicitly configure the assistant around the Ada experience rather than broad HA control.

This includes:
- assistant name = Ada
- consistent persona wording
- avoiding broad entity exposure as a backdoor control surface

### 5. HA -> OpenClaw filtered event forwarding

Use built-in HA automations plus `rest_command` to send small structured event payloads to OpenClaw.

**Recommended first event catalog:**
- washer/dryer finished
- doorbell pressed
- unusual motion after hours
- lock or door left open
- selected person arrival/departure
- selected media-state changes

**Do not forward:**
- raw full state dumps
- arbitrary event bus traffic
- broad entity graphs
- high-frequency telemetry

### 6. Narrow OpenClaw -> HA action bridge

Add one small internal bridge surface between OpenClaw and Home Assistant.

**Recommended shape:**
- internal-only HTTP JSON endpoint
- allowlisted action IDs
- schema validation
- HA-owned execution through scripts/services/webhooks

**Good initial actions:**
- announce text
- send notification
- activate scene
- run approved script

**Do not include in v1.0:**
- door unlock
- garage open
- alarm disarm
- admin/config edits
- arbitrary service execution

## Optional Alternatives

| Category | Recommended | Alternative | When to use |
|---|---|---|---|
| Wake word | Wyoming openWakeWord | device-local wake word | Only if endpoint hardware already supports it cleanly |
| Event/action boundary | Tiny bridge service or narrow HA webhook ingress | direct HA service calls | Only if the secret never reaches model-facing surfaces |
| Speaker playback | HA-native playback first | Music Assistant-centric routing | Add when grouped routing materially improves UX |

## Avoid for v1.0

1. Full Home Assistant MCP or admin exposure  
2. Direct long-lived HA token access from OpenClaw  
3. Broad entity discovery from voice sessions  
4. A broker/queue stack for the first event bridge  
5. Replacing existing Whisper, Piper, or Music Assistant pieces  
6. Sharing the HA voice session with Telegram/general OpenClaw sessions  
7. Safety-critical or destructive actions  
8. Multi-room orchestration as the first success condition

## Recommended v1.0 Stack Summary

### Keep
- Home Assistant
- Wyoming Whisper
- Wyoming Piper
- Music Assistant
- OpenClaw gateway conversation path

### Add
- one supported Assist endpoint
- wake word runtime and model deployment path
- dedicated OpenClaw HA voice profile
- HA automations plus `rest_command` for filtered events
- narrow HA action ingress for approved actions

### Protocols
- Wyoming for STT, TTS, and wake word
- HTTP JSON for event and action bridge calls
- Home Assistant scripts, scenes, automations, and webhooks for execution

## Sources

- `.planning/PROJECT.md`
- `spec/openclaw-home-assistant-voice.md`
- `cluster/apps/house/home-assistant/home-assistant.yaml`
- `cluster/apps/openclaw/instance/openclaw-instance.yaml`
- `cluster/apps/openclaw/instance/ha-config-snippet.yaml`
- `cluster/apps/house/music-assistant/music-assistant.yaml`
