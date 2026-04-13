<domain>
## Phase Boundary

Phase 2 delivers the first end-to-end Satellite 1 voice launch for Ada on one known-good Assist-compatible device. This phase must prove the spoken request/response loop on that device, ship a custom `Ada` / `Hey Ada` wake-word path, define how that wake-word model is packaged and updated in the Kubernetes voice stack, preserve manual Assist fallback when wake word is unavailable, and make failure behavior clear when the voice path cannot complete.

This phase does not expand to multiple endpoint classes, cross-room routing, or event/action bridge work. It should favor one reliable Satellite 1 path over broad hardware support.

</domain>

<decisions>
## Implementation Decisions

### Endpoint Scope
- Treat Satellite 1 as a single Assist-compatible device that provides both microphone input and speaker output.
- The MVP reply path should play Ada's spoken response back on the same Satellite 1 device that heard the request.
- Do not design Phase 2 around split mic/speaker endpoints or multiple endpoint classes.

### Wake Word Outcome
- The primary Phase 2 deliverable is a custom `Ada` / `Hey Ada` wake-word path, not only a stock wake word.
- Manual Assist activation must remain available as fallback if the custom wake-word runtime or model quality is not good enough yet.
- The plan should assume wake-word model training/generation happens in an external workflow, while packaging, deployment, and updates of the resulting model happen in-cluster and in-repo.

### Voice Launch Behavior
- Phase 2 must prove the full Home Assistant -> OpenClaw -> Piper voice path on Satellite 1.
- Phase 2 should include operator-visible failure behavior for wake-word/runtime/pipeline failure cases instead of silent breakage.

### the agent's Discretion
- Which exact wake-word runtime/manifests are the best fit for this Kubernetes stack.
- How Satellite 1 should be represented in Home Assistant config and deployment artifacts.
- What packaging layout is best for wake-word models and updates.
- What observability and smoke-test coverage is sufficient to make the launch supportable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and requirements
- `.planning/PROJECT.md` — milestone scope, constraints, and Home Assistant/OpenClaw responsibilities
- `.planning/ROADMAP.md` — Phase 2 goal, dependencies, success criteria, and execution order
- `.planning/REQUIREMENTS.md` — authoritative requirement IDs for VOICE-01, VOICE-02, WAKE-01, WAKE-02, WAKE-03, SAFE-01

### Voice architecture and stack
- `spec/openclaw-home-assistant-voice.md` — user experience, wake-word expectations, endpoint constraints, and open questions
- `cluster/apps/house/home-assistant/home-assistant.yaml` — existing HA voice stack, Whisper, Piper, and deployment conventions
- `cluster/apps/house/music-assistant/music-assistant.yaml` — available speaker-routing component if needed
- `cluster/apps/openclaw/instance/openclaw-instance.yaml` — current OpenClaw deployment and gateway/runtime conventions

### Research
- `.planning/research/SUMMARY.md` — milestone-wide architecture findings and Phase 2 research flags
- `.planning/research/STACK.md` — recommended wake-word/runtime additions and endpoint guidance
- `.planning/research/PITFALLS.md` — known Phase 2 pitfalls around endpoint assumptions, wake-word packaging, and failure behavior

</canonical_refs>

<specifics>
## Specific Ideas

- Keep Phase 2 centered on one known-good Satellite 1 device before expanding the endpoint matrix.
- Prefer a containerized, Kubernetes-managed wake-word runtime with a pinned image and explicit model artifact path.
- Treat manual Assist as a first-class fallback, not a post-hoc recovery path.
- Include an operator-facing deploy/update flow for wake-word model replacement.

</specifics>

<deferred>
## Deferred Ideas

- Multiple endpoint classes beyond Satellite 1
- Rich multi-room or explicit per-request routing logic
- Event forwarding from Home Assistant into OpenClaw
- Approved action callbacks from OpenClaw into Home Assistant

</deferred>

---

*Phase: 02-satellite-1-voice-launch*
*Context gathered: 2026-04-13 via interactive planning questions*
