# Feature Landscape

**Domain:** Home Assistant + OpenClaw voice integration
**Milestone:** v1.0 Ada Home Assistant Voice
**Researched:** 2026-04-12
**Overall confidence:** HIGH for Home Assistant capabilities and repo-aligned scope; MEDIUM for broader "strong v1" product framing

## Scope Framing

This document covers only the new milestone capabilities:

- Assist endpoint → OpenClaw → Ada → Piper spoken response
- Wake word support as part of the shipped design
- Narrow Home Assistant → OpenClaw event forwarding
- Narrow approved OpenClaw → Home Assistant action surface

It does **not** re-scope already-present infrastructure such as Home Assistant, Whisper, Piper, Music Assistant, OpenClaw deployment, or the existing Ada conversation snippet.

## Recommended Requirement Sections

1. Conversational Voice Loop
2. Wake Word + Endpoint Behavior
3. Event-Driven Ada Skills
4. Approved Action Surface Back Into Home Assistant
5. Failure Handling + Guardrails

---

## 1) Conversational Voice Loop

### Table Stakes

| Feature | User-observable behavior | Why expected in a strong v1 | Complexity | Dependency hints |
|---------|---------------------------|-----------------------------|------------|------------------|
| End-to-end spoken conversation | User speaks to one supported Assist endpoint and hears Ada reply back as speech | This is the core promise of the milestone | Med | Requires Assist routing, Whisper, OpenClaw backend, Piper output |
| Ada identity consistency | Assistant introduces/responds as Ada across UI, prompt, and spoken replies | Prevents "which assistant am I talking to?" confusion | Low | Depends on HA assistant naming and OpenClaw prompt/config alignment |
| Correct reply target | Response plays on the initiating or explicitly assigned speaker, not an arbitrary room | Users expect voice replies to come back where they spoke | Med | Depends on HA/Music Assistant routing choices |
| Short-turn utility | Ada can answer normal household questions/commands without requiring chat-style setup | A voice assistant v1 must feel usable in one turn | Med | Depends on prompt design and allowed action surface |
| Safe refusal when out of scope | If asked to do something outside allowed scope, Ada clearly says she cannot do that | Scope boundaries must be visible, not silent | Low | Depends on prompt + tool gating |

### Differentiators

| Feature | Value proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Brief conversational follow-up | Ada can handle a small follow-up turn ("yes", "which one?", "do it now") within the same interaction | Med | Valuable, but should stay narrow rather than full open-ended session management |
| Ada-style response tuning | Replies are concise, friendly, and consistent with the Ada persona instead of generic LLM phrasing | Low | Good UX win without expanding system scope |
| Event-aware voice continuity | If Ada previously alerted the user, a follow-up voice question can reference that alert | Med/High | Nice differentiator; depends on event bridge and short-lived context |

### Anti-Features

| Anti-Feature | Why avoid | What to do instead |
|--------------|-----------|-------------------|
| Full "same Ada as everywhere" tool/memory surface in voice v1 | Expands risk and makes voice behavior unpredictable | Keep voice flow on a narrowed prompt/tool surface |
| Long autonomous multi-step agent runs | Too slow and too hard to trust by voice | Prefer short-turn questions, answers, and approved actions |
| Rich multi-user personalization | Adds identity, privacy, and memory complexity | Treat v1 as a single-household Ada experience |

---

## 2) Wake Word + Endpoint Behavior

### Table Stakes

| Feature | User-observable behavior | Why expected in a strong v1 | Complexity | Dependency hints |
|---------|---------------------------|-----------------------------|------------|------------------|
| At least one working wake-word path | User can summon Ada hands-free on at least one supported endpoint, or the design clearly ships with one installable wake-word path | Hands-free use is part of the stated milestone | Med | Depends on chosen engine and endpoint type |
| Wake-word deployment story | There is a documented way to install, update, and replace the wake-word model/config | v1 must be deployable, not just demoable | Med | HA docs support openWakeWord and microWakeWord paths |
| Fallback when custom wake word is unavailable | User still has push-to-talk/manual Assist as backup | Prevents the whole system from failing on wake-word issues | Low | Should be explicit in requirements |
| Endpoint flexibility | If a speaker mic cannot be used directly, separate mic input + speaker output still works | Common real-world home setup | Med | Depends on Assist-compatible endpoint and output routing |

### Differentiators

| Feature | Value proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Natural "Hey Ada" experience | Makes the system feel truly branded and intentional | Med/High | Strong UX win, but training/deployment details matter |
| On-device wake word where supported | Lower latency and less server/network dependency on supported devices | High | Best on hardware that supports microWakeWord-style local detection |
| Easy model swap/update | Wake-word changes can be rolled out cleanly without manual HA surgery | Med | Good operational differentiator |

### Anti-Features

| Anti-Feature | Why avoid | What to do instead |
|--------------|-----------|-------------------|
| Building a bespoke wake-word research project for v1 | Can consume the whole milestone | Ship one supported engine/path first |
| Requiring every room/device to support the custom wake word on day one | Over-scopes rollout | Support one good endpoint first, then expand |
| No documented fallback path | Turns wake-word outages into total product failure | Require manual activation fallback |

---

## 3) Event-Driven Ada Skills (Home Assistant → OpenClaw)

### Table Stakes

| Feature | User-observable behavior | Why expected in a strong v1 | Complexity | Dependency hints |
|---------|---------------------------|-----------------------------|------------|------------------|
| Small approved event catalog | Only selected events trigger Ada workflows (for example doorbell, washer done, arrival/departure, unusual motion) | Prevents noise and matches narrow-scope goal | Med | Depends on HA automations defining event sources |
| Structured event payloads | Ada reactions are based on compact, predictable event data, not raw HA dumps | Necessary for reliability and security | Med | Payload schema should be explicit per event type |
| Useful user-facing reactions | Ada can summarize, notify, ask a follow-up question, or speak a brief alert | Users need visible value from forwarded events | Med | Depends on speaker/notification path |
| Event filtering and throttling | Users do not get spammed by noisy or repeated events | Table stakes for a livable home assistant | Med | Add cooldowns/deduping in HA before forwarding where possible |

### Differentiators

| Feature | Value proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Contextual summaries | Ada turns multiple low-level updates into one useful summary | Med | Strong quality boost over naive one-event-one-message behavior |
| Follow-up questions on ambiguous events | Ada can ask a constrained clarifying question when helpful | Med | Only for a small set of high-value events |
| Multi-channel response choice | Same event can become voice, notification, or silent memory based on context | Med/High | Valuable but should stay rules-driven in v1 |

### Anti-Features

| Anti-Feature | Why avoid | What to do instead |
|--------------|-----------|-------------------|
| Raw event firehose into OpenClaw | Expands context, cost, and unpredictability | Forward only curated event classes |
| Full state graph sync for context | Breaks the intended security boundary | Send minimal structured payloads |
| Open-ended proactive behavior | Users quickly lose trust if Ada becomes chatty or surprising | Restrict to approved event reactions |

---

## 4) Approved Action Surface (OpenClaw → Home Assistant)

### Table Stakes

| Feature | User-observable behavior | Why expected in a strong v1 | Complexity | Dependency hints |
|---------|---------------------------|-----------------------------|------------|------------------|
| Small approved action list | Ada can perform a narrow set of useful actions such as approved service calls, scenes, scripts, or notifications | This is the practical payoff of integration | Med | Requires explicit allowlist owned by Home Assistant side |
| Home Assistant remains executor | Actions happen through HA services/automations, not direct admin-style manipulation by OpenClaw | Preserves architecture and trust boundary | Low/Med | Keep action bridge declarative |
| Confirmation for impactful actions | Ada confirms before doing anything with meaningful household impact | Expected safety behavior in home control | Low | Especially important for locks, alarms, or disruptive media actions |
| Clear denial for disallowed actions | User hears why a request cannot be done instead of ambiguous failure | Makes the boundary understandable | Low | Prompt + action policy requirement |

### Differentiators

| Feature | Value proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Friendly action paraphrase | Ada briefly repeats what she is about to do before execution | Low | Improves trust and debuggability |
| Auditable action labels | Actions map to human-readable approved capabilities ("announce", "run bedtime scene") | Med | Great for requirements and later observability |
| Constrained read-before-write behavior | Ada may check one narrow bit of context before acting | Med | Useful if kept scoped and explicit |

### Anti-Features

| Anti-Feature | Why avoid | What to do instead |
|--------------|-----------|-------------------|
| Arbitrary HA service execution | Too broad for v1 security posture | Use an allowlisted action surface |
| Dashboard/config/automation/file editing | Not part of home voice assistant v1 and too risky | Keep HA as the managed system, not agent-editable |
| Broad entity discovery from voice | Encourages unsafe and inconsistent actions | Scope reads to selected entities/areas only |

---

## 5) Failure Handling + Guardrails

### Table Stakes

| Feature | User-observable behavior | Why expected in a strong v1 | Complexity | Dependency hints |
|---------|---------------------------|-----------------------------|------------|------------------|
| Graceful degraded mode | If wake word, OpenClaw, or TTS is unavailable, the user gets a clear fallback path | Prevents "it just stopped working" experiences | Med | Requirements should define at least one fallback per failure class |
| No silent action failures | If an action cannot run, Ada says so clearly | Essential for trust | Low | Depends on bridge error handling |
| Predictable scope boundaries | Ada consistently stays within the approved household action surface | Strong v1 feels trustworthy, not magical | Low | Depends on explicit requirement wording |

### Differentiators

| Feature | Value proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Alternate response channel on failure | If speech output fails, user can still receive a notification/logged reply | Med | Nice resilience win |
| User-friendly error wording | Errors sound like Ada, not raw backend messages | Low | Helps polish without changing architecture |

### Anti-Features

| Anti-Feature | Why avoid | What to do instead |
|--------------|-----------|-------------------|
| Silent retries that duplicate actions | Can cause confusing or unsafe repeated behavior | Retry safely only on idempotent operations |
| Hidden partial success | User should not have to guess whether Ada acted | Return explicit outcome messaging |

---

## Feature Dependencies

```text
Assist endpoint + Whisper + OpenClaw + Piper
  → End-to-end conversational voice loop

Wake-word engine selection
  → Hands-free activation
  → Deployment/update/fallback requirements

HA automation/event filtering
  → Structured event bridge
  → Event-driven Ada skills

Approved action allowlist
  → Safe OpenClaw → HA execution
  → Clear confirmation/denial behavior

Speaker/output routing
  → Correct reply target
  → Event-driven spoken alerts
```

## MVP Recommendation

Prioritize:

1. **Reliable end-to-end Ada voice loop**
   - Speak to one supported endpoint
   - Ada responds as Ada
   - Audio returns to the correct output

2. **Wake-word design with explicit fallback**
   - One supported wake-word path
   - Deployment/update story
   - Push-to-talk/manual fallback

3. **Small, high-value event bridge**
   - Start with a tiny event set
   - Use structured payloads
   - Produce useful summaries/alerts/questions

4. **Tiny approved action surface**
   - Safe allowlisted actions only
   - Confirmation on impactful actions
   - Clear refusals out of scope

Defer:

- Whole-home entity discovery
- Open-ended proactive agent behavior
- Broad memory/tool sharing from OpenClaw voice sessions
- Multi-room/multi-user sophistication
- Large custom wake-word rollout across every endpoint

## Sources

- Repo milestone context: `/Users/andrewmccall/projects/home-ops/.planning/PROJECT.md` — HIGH
- Integration spec: `/Users/andrewmccall/projects/home-ops/spec/openclaw-home-assistant-voice.md` — HIGH
- Existing HA config direction: `/Users/andrewmccall/projects/home-ops/cluster/apps/openclaw/instance/ha-config-snippet.yaml` — HIGH
- Home Assistant voice docs: https://www.home-assistant.io/voice_control/ — HIGH
- Home Assistant wake-word docs: https://www.home-assistant.io/voice_control/about_wake_word/ — HIGH
- Home Assistant OpenAI conversation integration docs: https://www.home-assistant.io/integrations/openai_conversation/ — HIGH
- Strong-v1 product framing in this document is a synthesis from the above sources plus current domain practice — MEDIUM
