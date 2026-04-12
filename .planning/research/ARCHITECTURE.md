# Architecture: Ada Home Assistant Voice

**Project:** Home Ops  
**Milestone:** v1.0 Ada Home Assistant Voice  
**Researched:** 2026-04-12  
**Overall confidence:** MEDIUM

## Recommendation

Keep **Home Assistant as the voice shell, event source of truth, and service executor**. Keep **OpenClaw as the conversation and decision layer**, but only through a **dedicated Home Assistant voice/profile boundary** instead of the current broad `openclaw:main` path. Add wake word detection as a **Home Assistant-managed Assist pipeline component**, add **HA-owned filtered event forwarding** to OpenClaw, and make OpenClaw return actions only through a **single narrow HA ingress** that maps approved action IDs to HA scripts/services.

That gives you the milestone goal without exposing broad MCP/admin control or the full Home Assistant graph.

---

## Current Architecture (already present)

### Existing deployed pieces

| Component | Current state | Evidence | Notes |
|-----------|---------------|----------|-------|
| Home Assistant | Deployed in cluster | `cluster/apps/house/home-assistant/home-assistant.yaml:5-158` | Primary orchestration point |
| Whisper STT | Deployed as Wyoming service in HA release | `home-assistant.yaml:70-76, 91-97` | Already available for Assist |
| Piper TTS | Deployed as Wyoming service in HA release | `home-assistant.yaml:77-82, 91-97` | Already available for spoken replies |
| OpenClaw gateway | Deployed with chat completions endpoint enabled | `cluster/apps/openclaw/instance/openclaw-instance.yaml:37-41` | Existing LLM backend entry point |
| Ada naming in HA | HA snippet already points OpenAI conversation at OpenClaw and names assistant Ada | `cluster/apps/openclaw/instance/ha-config-snippet.yaml:5-9` | Good starting point |
| Music Assistant | Deployed separately | `cluster/apps/house/music-assistant/music-assistant.yaml:5-71` | Available for playback/routing |

### Important current gap

The current HA snippet comments explicitly describe **“FULL Ada”**, including memory, tools, file access, and shared Telegram context (`ha-config-snippet.yaml:18-26`). That is **too broad for this milestone** and conflicts with the approved boundary of:

- no broad whole-home exposure
- no full admin surface
- no unrestricted agent context bleed from other channels

So the existing direction is useful, but it must be **narrowed before adding more integration**.

### Missing today

| Capability | Status |
|-----------|--------|
| Wake word service/design for Ada | Missing from manifests reviewed |
| Filtered HA -> OpenClaw event bridge | Missing |
| Narrow OpenClaw -> HA action bridge | Missing |
| Voice-specific OpenClaw profile/tool scope | Not visible in current config |

---

## Proposed Target Architecture

```text
[Assist-compatible mic / satellite / phone]
        |
        v
  Wake word detection
 (HA-managed; central first)
        |
        v
Home Assistant Assist pipeline
  - STT: Whisper (existing)
  - Conversation: OpenClaw HA voice profile
  - TTS: Piper (existing)
        |
        +--> Home Assistant media_player target
        \--> Music Assistant target (when routing helps)

Home Assistant automations
  - detect events
  - filter + normalize payloads
  - POST small event payloads to OpenClaw

OpenClaw HA integration surface
  - voice agent/profile for Ada
  - event ingest endpoint
  - narrow HA action tool

OpenClaw -> Home Assistant
  - single internal webhook/action ingress
  - HA validates action_id + args
  - HA scripts/services execute locally
```

---

## Integration Boundaries

### 1. Home Assistant remains source of truth

Home Assistant should continue to own:

- voice endpoint registration
- wake word selection/pipeline config
- state/event detection
- service execution
- scene/script execution
- audio target selection

OpenClaw should **not** own raw entity discovery, automation authorship, or direct broad service execution.

### 2. OpenClaw gets a dedicated Home Assistant voice surface

Do **not** point Home Assistant voice at the same broad OpenClaw surface used for Telegram/general assistant behavior.

Instead create a dedicated OpenClaw profile/agent/model alias for HA voice, for example:

- `openclaw:ada-home`
- separate HA token
- separate session namespace
- restricted tools
- explicit Ada persona prompt

This avoids:

- Telegram/voice session bleed
- accidental access to broad tools
- exposing general-purpose agent behavior inside home voice flows

### 3. Event forwarding must be HA-owned and schema-first

Home Assistant automations should decide:

- which events matter
- when they fire
- what minimal payload is sent

OpenClaw should receive **small structured facts**, not the full HA graph.

### 4. Action execution must flow back through HA

OpenClaw may request actions, but HA must validate and execute them.

Recommended contract:

```json
{
  "action_id": "announce_text",
  "args": {
    "target": "kitchen",
    "text": "The washer is finished."
  },
  "reason": "washer_finished follow-up"
}
```

HA maps `action_id` to a local script/service allowlist. OpenClaw never gets arbitrary service-call freedom.

---

## Proposed Additions

## A. Wake word support

**Recommendation:** add a Home Assistant-compatible wake word engine as a new service and attach it to the Assist pipeline. Use **central wake word detection first**, not on-device custom logic first.

### Why

Home Assistant’s official voice docs say wake word detection is typically done inside Home Assistant, and that external wake word detection can be run over the **Wyoming protocol** to scale beyond local host constraints. Home Assistant also documents `openWakeWord` as available in Docker and notes it supports training basic custom wake words.  
**Confidence:** HIGH for HA-managed/openWakeWord direction; MEDIUM for exact Kubernetes packaging choice.

### Recommended design

- **New:** wake word service in the `house` namespace
  - preferred shape: Wyoming-compatible wake word service
  - target: Ada wake word model
- **Modified:** Home Assistant voice assistant/pipeline config
  - wake word engine assigned to Ada assistant
  - Whisper remains STT
  - OpenClaw HA voice profile becomes conversation backend
  - Piper remains TTS

### Fallback behavior

If custom “Hey Ada” is not ready or quality is poor:

1. ship with a supported default wake word first
2. allow push-to-talk/button-to-talk fallback
3. keep custom Ada wake word as a replaceable model artifact

That prevents wake word work from blocking end-to-end voice delivery.

## B. Conversation routing

**Recommendation:** keep the existing HA -> OpenClaw conversation path, but narrow it.

### Required modification

Replace the current effective meaning of:

- `model: "openclaw:main"` in the HA snippet

with a dedicated HA voice alias/profile. The important change is architectural, even if the exact config syntax differs in OpenClaw:

- dedicated voice agent/persona = Ada
- no file editing/web/GitHub/general admin tools
- no cross-channel memory by default
- optional read-only home summary tool later, not broad home graph

### Result

Voice requests stay:

`Assist endpoint -> HA -> OpenClaw -> HA -> Piper -> speaker`

but the OpenClaw hop is now **home-voice-safe**.

## C. Filtered event forwarding

**Recommendation:** Home Assistant automations should POST small event payloads to OpenClaw using HA-owned outbound calls.

### Shape

- **New in HA:** automation(s) for chosen events
- **New in HA:** `rest_command` or equivalent outbound HTTP call
- **New in OpenClaw:** event ingest endpoint/plugin with stable schema

### Example payload

```json
{
  "event_type": "washer_finished",
  "source": "home_assistant",
  "area": "utility_room",
  "occurred_at": "2026-04-12T19:10:00Z",
  "context": {
    "entity_id": "sensor.washer_state"
  }
}
```

### Rules

- include only data needed for Ada to respond
- no full entity dump
- no raw recorder/history export
- event types should be explicitly allowlisted

Good first events:

- washer/dryer finished
- doorbell pressed
- person arrived/left
- abnormal after-hours motion
- door/lock left open

## D. Narrow action bridge

**Recommendation:** expose exactly **one internal HA ingress** for OpenClaw action requests, then map approved actions to HA scripts/services.

### Recommended v1 pattern

- **New in HA:** webhook-triggered automation/script receiver
- **New in OpenClaw:** one tool/integration that calls that receiver
- **Modified in HA:** local scripts/scenes/services that implement approved actions

### Why webhook first

Home Assistant officially supports webhook triggers at `/api/webhook/<webhook_id>`, including `allowed_methods` and `local_only`. For this milestone, that is narrower than giving OpenClaw a general HA API token.

### Guardrails

- internal-only path, no public ingress
- long random `webhook_id`
- `POST` only
- allowlisted `action_id`
- validate args before service execution
- log every request/result in HA

### Initial approved action surface

Start with low-risk actions only:

1. `announce_text`
2. `send_notification`
3. `activate_scene`
4. `run_script`

Defer arbitrary device control until the schema and review flow are proven.

---

## Component Boundaries

| Component | Responsibility | Communicates with |
|-----------|----------------|-------------------|
| Assist endpoint | Captures user speech / streams audio | Home Assistant |
| Wake word service | Detects wake word model for Ada | Home Assistant Assist pipeline |
| Home Assistant | Pipeline orchestration, event detection, action execution, audio target choice | Whisper, Piper, OpenClaw, Music Assistant |
| Whisper | Speech-to-text | Home Assistant |
| OpenClaw HA voice profile | Conversational reasoning as Ada for voice | Home Assistant |
| OpenClaw event ingest | Receives filtered HA events | Home Assistant automations |
| OpenClaw action tool | Emits narrow action requests | HA internal webhook |
| Piper | Text-to-speech generation | Home Assistant |
| Music Assistant | Speaker/output routing where useful | Home Assistant |

---

## Data Flows

### 1. Voice conversation flow

1. User says wake word to Assist-compatible endpoint.
2. Wake word engine matches Ada wake word.
3. Audio is sent through HA Assist pipeline.
4. Whisper transcribes speech.
5. HA sends conversation request to **OpenClaw HA voice profile**.
6. OpenClaw returns Ada response text.
7. HA sends text to Piper.
8. HA plays response via native media target or Music Assistant.

### 2. Event forwarding flow

1. HA automation detects a scoped event/state transition.
2. HA normalizes it to a small JSON payload.
3. HA sends payload to OpenClaw event ingest endpoint.
4. OpenClaw decides whether to:
   - store a memory/note
   - generate a summary
   - send a message
   - ask HA to announce/notify

### 3. Action request flow

1. OpenClaw decides an approved action is needed.
2. OpenClaw sends `{action_id, args, reason}` to HA internal webhook.
3. HA validates action ID and arguments.
4. HA runs mapped script/service/scene locally.
5. HA optionally returns simple result status to OpenClaw.

### 4. Playback routing flow

1. HA determines target output.
2. If direct speaker/media player is enough, HA plays locally.
3. If grouped playback/routing is needed, HA hands output to Music Assistant.

**Recommendation:** keep Music Assistant optional in v1 voice routing. Do not block the core voice path on richer speaker orchestration.

---

## New vs Modified

| Area | New | Modified |
|------|-----|----------|
| Wake word | New wake word service/model deployment | HA Assist pipeline config updated to use it |
| Conversation routing | New dedicated OpenClaw HA voice profile/alias | Existing HA snippet should stop targeting broad `openclaw:main` behavior |
| Event forwarding | New HA automations + outbound event contract + OpenClaw event ingest | None required in Music Assistant |
| Action bridge | New internal HA webhook + allowlisted scripts/services + OpenClaw action tool | HA gets explicit bridge mappings for approved actions |
| Audio routing | No new core dependency required | Optional use of existing Music Assistant for output targeting |

---

## Suggested Build Order

## Phase 1 — Narrow the conversation boundary first

**Why first:** the current HA snippet implies a broad Ada surface. Fixing that boundary is prerequisite to every other integration.

Land:

- dedicated OpenClaw HA voice profile/alias
- dedicated HA token/session scope
- Ada persona enforcement in the voice profile
- removal of broad/general tool exposure from HA voice path

**Exit condition:** HA text conversation path works against the restricted Ada voice profile.

## Phase 2 — Complete the end-to-end voice path with wake word

Land:

- wake word service deployment
- Assist pipeline wiring: wake word -> Whisper -> OpenClaw -> Piper
- one known-good microphone endpoint
- one known-good speaker target
- fallback mode if Ada wake word model is unavailable

**Exit condition:** user can say wake word, speak, and hear Ada reply.

## Phase 3 — Add HA -> OpenClaw filtered event forwarding

Land:

- stable event schema
- first 2-3 automations (washer, doorbell, arrival is enough)
- HA outbound REST command(s)
- OpenClaw event ingest handling

**Exit condition:** HA events reach OpenClaw without exposing broad home state.

## Phase 4 — Add the narrow OpenClaw -> HA action bridge

Land:

- single HA internal webhook/action ingress
- allowlisted action IDs
- mapped HA scripts/services
- audit logging

Start with non-destructive actions:

- speak/announce
- notification
- scene/script execution

**Exit condition:** OpenClaw can request approved actions and HA safely executes them.

## Phase 5 — Routing and UX polish

Land:

- Music Assistant-based playback selection where valuable
- speaker targeting improvements
- follow-up behavior tuning
- wake word model iteration

**Exit condition:** user experience is polished, but the core architecture is already stable.

### Ordering rationale

1. **Security boundary before capability expansion**
2. **Voice path before event-driven extras**
3. **One-way HA -> OpenClaw bridge before two-way control**
4. **Low-risk actions before broader automations**
5. **Playback polish last because it is not a core dependency**

---

## Anti-Patterns to Avoid

### Anti-pattern 1: Reuse `openclaw:main` as-is for Home Assistant voice

**Why bad:** mixes voice with broader assistant tools/context and violates the milestone’s narrow-surface goal.

**Instead:** create a dedicated HA voice profile with restricted tools and isolated session behavior.

### Anti-pattern 2: Give OpenClaw a general Home Assistant API token

**Why bad:** HA long-lived tokens are much broader than the milestone allows.

**Instead:** expose one narrow ingress and map action IDs to HA-owned scripts/services.

### Anti-pattern 3: Forward raw Home Assistant state/history into OpenClaw

**Why bad:** unnecessary context, privacy risk, harder prompts, harder debugging.

**Instead:** forward minimal structured events only.

### Anti-pattern 4: Make Music Assistant a hard dependency for first voice success

**Why bad:** introduces routing complexity into the core milestone path.

**Instead:** support direct HA playback first; add Music Assistant optimization after core flow works.

---

## Confidence Notes

| Topic | Confidence | Notes |
|-------|------------|-------|
| Existing repo architecture | HIGH | Verified directly from manifests/spec |
| Need for dedicated HA voice profile in OpenClaw | HIGH | Driven by milestone constraints + current snippet mismatch |
| HA-managed wake word architecture | HIGH | Supported by current Home Assistant docs |
| Wyoming/openWakeWord Kubernetes packaging choice | MEDIUM | Direction is strong; exact deployment shape needs implementation validation |
| Webhook-first narrow action bridge | MEDIUM | Supported by HA docs and matches least-privilege goal, but auth hardening details should be validated in implementation |
| Music Assistant as optional v1 routing enhancement | MEDIUM | Strong fit with current repo, but exact playback integration is milestone-specific |

---

## Sources

### Repo sources

- `.planning/PROJECT.md`
- `spec/openclaw-home-assistant-voice.md`
- `cluster/apps/house/home-assistant/home-assistant.yaml`
- `cluster/apps/openclaw/instance/openclaw-instance.yaml`
- `cluster/apps/openclaw/instance/ha-config-snippet.yaml`
- `cluster/apps/house/music-assistant/music-assistant.yaml`

### Official documentation

- Home Assistant wake word architecture: https://www.home-assistant.io/voice_control/about_wake_word/
- Home Assistant local Assist pipeline overview: https://www.home-assistant.io/voice_control/voice_remote_local_assistant/
- Home Assistant REST command docs: https://www.home-assistant.io/integrations/rest_command/
- Home Assistant automation webhook trigger docs: https://www.home-assistant.io/docs/automation/trigger/
- Home Assistant intent script docs: https://www.home-assistant.io/integrations/intent_script/
