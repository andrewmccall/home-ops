# Phase 2: Satellite 1 Voice Launch - Research

**Researched:** 2026-04-13
**Domain:** Home Assistant Assist + Wyoming wake word packaging on Kubernetes
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Treat Satellite 1 as a single Assist-compatible device that provides both microphone input and speaker output.
- The MVP reply path should play Ada's spoken response back on the same Satellite 1 device that heard the request.
- Do not design Phase 2 around split mic/speaker endpoints or multiple endpoint classes.

- The primary Phase 2 deliverable is a custom `Ada` / `Hey Ada` wake-word path, not only a stock wake word.
- Manual Assist activation must remain available as fallback if the custom wake-word runtime or model quality is not good enough yet.
- The plan should assume wake-word model training/generation happens in an external workflow, while packaging, deployment, and updates of the resulting model happen in-cluster and in-repo.

- Phase 2 must prove the full Home Assistant -> OpenClaw -> Piper voice path on Satellite 1.
- Phase 2 should include operator-visible failure behavior for wake-word/runtime/pipeline failure cases instead of silent breakage.

### the agent's Discretion
- Which exact wake-word runtime/manifests are the best fit for this Kubernetes stack.
- How Satellite 1 should be represented in Home Assistant config and deployment artifacts.
- What packaging layout is best for wake-word models and updates.
- What observability and smoke-test coverage is sufficient to make the launch supportable.

### Deferred Ideas (OUT OF SCOPE)
- Multiple endpoint classes beyond Satellite 1
- Rich multi-room or explicit per-request routing logic
- Event forwarding from Home Assistant into OpenClaw
- Approved action callbacks from OpenClaw into Home Assistant
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VOICE-01 | User can speak to Satellite 1 and receive a spoken reply from Ada through the Home Assistant -> OpenClaw -> Piper voice path. | Keep the existing HA UI-configured OpenAI/bridge path, reuse existing Whisper/Piper services, and bind one Assist satellite to one HA voice assistant pipeline. [VERIFIED: cluster/apps/openclaw/instance/ha-config-snippet.yaml] [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] |
| VOICE-02 | User hears Ada replies on the initiating or explicitly assigned speaker target instead of an unrelated room. | MVP should target the initiating Satellite 1 device directly and avoid Music Assistant-centric rerouting in this phase. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] [VERIFIED: cluster/apps/house/music-assistant/music-assistant.yaml] |
| WAKE-01 | User can wake Ada on Satellite 1 with a shipped custom wake word model for "Ada" or "Hey Ada". | Use `rhasspy/wyoming-openwakeword` with repo-shipped custom `.tflite` artifacts mounted via `--custom-model-dir`, then bind those models to one live `assist_satellite` device and approve them with a spoken `Ada` / `Hey Ada` utterance matrix in Phase 2 cutover. [CITED: https://www.home-assistant.io/voice_control/about_wake_word/] [CITED: https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md] |
| WAKE-02 | User can deploy and update the custom Ada wake word model in the Kubernetes-based Home Assistant voice stack. | Package the model as a repo-managed artifact in a dedicated wake-word release so model updates restart only the wake-word pod, not Home Assistant/Whisper/Piper. [VERIFIED: cluster/apps/house/kustomization.yaml] [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [ASSUMED] |
| WAKE-03 | User can still activate Ada through a manual Assist fallback if the wake word runtime is unavailable. | Keep Satellite 1 bound to the voice assistant pipeline even when the streaming wake word engine is disabled or unavailable. [CITED: https://www.home-assistant.io/voice_control/create_wake_word/] [ASSUMED] |
| SAFE-01 | User receives a clear failure response when the voice pipeline or action bridge cannot complete a request. | Use a Home Assistant YAML package at `/config/packages/ada_voice_failure.yaml` that polls `http://openclaw-bridge.openclaw.svc.cluster.local:4000/healthz` via a REST `binary_sensor`, then triggers `assist_satellite.announce` on the bound Satellite 1 entity after 15 seconds of bridge unhealthiness. Verify it by scaling `deployment/openclaw-bridge` to `0` and confirming the spoken announcement before restoring the deployment. [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml] [VERIFIED: cluster/apps/openclaw/bridge/bridge.yaml] [CITED: https://www.home-assistant.io/integrations/assist_satellite/] |
</phase_requirements>

## Summary

This repo already has the hard parts of the voice loop except wake word and endpoint wiring: Home Assistant `2026.4.2`, Wyoming Whisper `3.1.0`, Wyoming Piper `2.2.2`, the OpenClaw bridge ingress, and the OpenClaw gateway are all present in-cluster. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [VERIFIED: cluster/apps/openclaw/bridge/bridge.yaml] [VERIFIED: cluster/apps/openclaw/instance/openclaw-instance.yaml] Phase 2 should therefore add the thinnest missing slice: one Satellite 1 binding, one Kubernetes-managed Wyoming wake-word service, one repo-managed custom model package, and one explicit failure/fallback behavior. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] [CITED: https://www.home-assistant.io/voice_control/about_wake_word/]

The best fit for this stack is a dedicated `wyoming-openwakeword` deployment in the `house` namespace instead of folding wake word into the existing Home Assistant HelmRelease. [CITED: https://www.home-assistant.io/voice_control/about_wake_word/] [CITED: https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md] [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] A separate release matches the repo's one-app-per-directory pattern, keeps the wake-word rollout independent from Home Assistant/Whisper/Piper, and directly satisfies the requirement that operators update the Ada model without replacing the rest of the voice pipeline. [VERIFIED: cluster/apps/house/kustomization.yaml] [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [ASSUMED]

Use the existing HA -> `api.openai.com` spoof/bridge path exactly as Phase 01.1 established, because that path already carries Ada identity, shared-session continuity, and degraded-mode signaling. [VERIFIED: cluster/apps/openclaw/instance/ha-config-snippet.yaml] [VERIFIED: cluster/apps/openclaw/bridge/openai-proxy-ingress.yaml] [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml] Do not introduce Music Assistant routing, multi-room reply rules, or a second conversation backend in this phase. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] [VERIFIED: .planning/REQUIREMENTS.md]

**Primary recommendation:** Ship Satellite 1 on the existing Home Assistant/OpenClaw bridge path, add a separate `wyoming-openwakeword` app in `cluster/apps/house/`, mount repo-managed `Ada` and `Hey Ada` `.tflite` models into that pod, and keep manual Assist bound as the fallback. [VERIFIED: cluster/apps/house/kustomization.yaml] [CITED: https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md] [CITED: https://www.home-assistant.io/voice_control/create_wake_word/]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Home Assistant | `2026.4.2` (published 2026-04-11) [VERIFIED: Docker Hub homeassistant/home-assistant] | Voice shell, Assist pipeline, Wyoming integration, satellite binding | Already deployed and already hosts Whisper/Piper plus the OpenAI bridge-backed path. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [VERIFIED: cluster/apps/openclaw/instance/ha-config-snippet.yaml] |
| rhasspy/wyoming-whisper | `3.1.0` (published 2026-01-30) [VERIFIED: Docker Hub rhasspy/wyoming-whisper] | STT | Already deployed on port `10300`; Phase 2 should reuse it unchanged. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] |
| rhasspy/wyoming-piper | `2.2.2` (published 2026-02-05) [VERIFIED: Docker Hub rhasspy/wyoming-piper] | TTS | Already deployed on port `10200`; Phase 2 should reuse it unchanged. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] |
| rhasspy/wyoming-openwakeword | `2.1.0` (published 2025-10-28) [VERIFIED: Docker Hub rhasspy/wyoming-openwakeword] | Streaming wake-word runtime for custom Ada models | Home Assistant explicitly documents openWakeWord as the non-HA-OS Docker path and the Wyoming README documents `--custom-model-dir` for custom `.tflite` models. [CITED: https://www.home-assistant.io/voice_control/about_wake_word/] [CITED: https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md] |
| OpenClaw bridge + gateway | Repo-deployed [VERIFIED: repo manifests] | Ada conversation backend with degraded continuity signaling | Already in use for the HA-facing path; Phase 2 should stay on this path. [VERIFIED: cluster/apps/openclaw/bridge/bridge.yaml] [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| bjw-s `app-template` Helm chart | `4.6.2` [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] | Repo-standard Kubernetes packaging pattern | Use for the new wake-word deployment because Home Assistant and Music Assistant already use it. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [VERIFIED: cluster/apps/house/music-assistant/music-assistant.yaml] |
| Home Assistant Wyoming integration | HA built-in [CITED: https://www.home-assistant.io/integrations/wyoming/] | Registers external STT/TTS/wake-word services | Use to attach the new wake-word service on port `10400`. [CITED: https://www.home-assistant.io/voice_control/about_wake_word/] |
| Assist Satellite actions | HA built-in [CITED: https://www.home-assistant.io/integrations/assist_satellite/] | On-device announce/start-conversation behaviors | Use for manual fallback smoke tests and spoken failure responses. [CITED: https://www.home-assistant.io/integrations/assist_satellite/] |
| Music Assistant | `2.8.4` (published 2026-04-13) [VERIFIED: GitHub releases music-assistant/server] | Optional speaker routing layer | Keep out of the MVP path unless Satellite 1 cannot play TTS locally. [VERIFIED: cluster/apps/house/music-assistant/music-assistant.yaml] [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate `wyoming-openwakeword` release | Add wake-word container inside `home-assistant.yaml` | Tighter coupling makes model rollouts part of the Home Assistant release blast radius, which fights WAKE-02. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [ASSUMED] |
| Server-side openWakeWord in Kubernetes | Device-local `microWakeWord` | Home Assistant documents `microWakeWord` for specific low-power device classes, while server-side openWakeWord is the generic streaming-satellite path. [CITED: https://www.home-assistant.io/voice_control/about_wake_word/] |
| Same-device Satellite 1 playback | Music Assistant-centric room routing | Same-device playback is the locked MVP and avoids multi-room routing complexity in Phase 2. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] |

**Installation:**  
Use a new HelmRelease in `cluster/apps/house/wyoming-openwakeword/` that runs `rhasspy/wyoming-openwakeword:2.1.0`, exposes port `10400`, and mounts repo-managed model files into `--custom-model-dir`. [VERIFIED: cluster/apps/house/kustomization.yaml] [CITED: https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md]

**Version verification:**  
The repo-pinned voice components are current relative to their registries as checked in this session: Home Assistant `2026.4.2` (2026-04-11), Wyoming Whisper `3.1.0` (2026-01-30), Wyoming Piper `2.2.2` (2026-02-05), and Wyoming openWakeWord `2.1.0` (2025-10-28). [VERIFIED: Docker Hub homeassistant/home-assistant] [VERIFIED: Docker Hub rhasspy/wyoming-whisper] [VERIFIED: Docker Hub rhasspy/wyoming-piper] [VERIFIED: Docker Hub rhasspy/wyoming-openwakeword]

## Architecture Patterns

### Recommended Project Structure
```text
cluster/apps/house/
├── home-assistant/                  # Existing HA + Whisper + Piper release
├── music-assistant/                 # Existing optional routing component
└── wyoming-openwakeword/            # New dedicated wake-word release
    ├── kustomization.yaml           # Added to cluster/apps/house/kustomization.yaml
    ├── wyoming-openwakeword.yaml    # HelmRelease + Service on 10400
    ├── wakeword-models.yaml         # ConfigMap or generator definition
    └── models/                      # Repo-carried external artifacts
        ├── ada.tflite
        ├── hey_ada.tflite
        └── MODEL.md                 # hash/source/date/operator notes
```

### Pattern 1: Separate wake-word deployment, same namespace
**What:** Put the wake-word runtime in `house` beside Home Assistant instead of inside the Home Assistant release. [VERIFIED: cluster/apps/house/kustomization.yaml] [CITED: https://www.home-assistant.io/voice_control/about_wake_word/]  
**When to use:** Use for WAKE-02 whenever model rollouts must not redeploy Home Assistant, Whisper, or Piper. [VERIFIED: .planning/REQUIREMENTS.md]  
**Example:**
```yaml
# Source: repo pattern + Wyoming openWakeWord README
controllers:
  wyoming-openwakeword:
    annotations:
      reloader.stakater.com/auto: "true"
    containers:
      app:
        image:
          repository: rhasspy/wyoming-openwakeword
          tag: 2.1.0
        args: ["--uri", "tcp://0.0.0.0:10400", "--custom-model-dir", "/models"]
service:
  app:
    controller: wyoming-openwakeword
    ports:
      wyoming:
        port: 10400
persistence:
  models:
    type: configMap
    name: wakeword-models
    globalMounts:
      - path: /models
```
Source basis: repo uses `app-template` plus configMap-backed mounts already, and `wyoming-openwakeword` documents `--custom-model-dir`. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [CITED: https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md]

### Pattern 2: Ship the model artifact, not the training workflow
**What:** Treat `Ada` and `Hey Ada` as externally generated `.tflite` release artifacts that are versioned in-repo with metadata, then mounted into the runtime. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] [CITED: https://www.home-assistant.io/voice_control/create_wake_word/]  
**When to use:** Use whenever wake-word training happens outside the cluster but deployment/update must stay inside repo + Flux. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md]  
**Example:**
```text
models/
├── ada.tflite
├── hey_ada.tflite
└── MODEL.md

# MODEL.md fields
- source_workflow_run:
- phrases:
  - Ada
  - Hey Ada
- sha256:
- generated_at:
- approved_by:
```
Public Home Assistant-compatible wake-word artifacts in the community collection are small `.tflite` files around `206748` bytes, so a two-model MVP package is operationally light. [VERIFIED: GitHub API fwartner/home-assistant-wakewords-collection]

### Pattern 3: Preserve the existing HA -> OpenClaw bridge path
**What:** Keep Home Assistant pointed at the bridge-backed OpenAI Conversation path and add wake word only at the front of the existing pipeline. [VERIFIED: cluster/apps/openclaw/instance/ha-config-snippet.yaml] [VERIFIED: cluster/apps/openclaw/bridge/openai-proxy-ingress.yaml]  
**When to use:** Always in Phase 2, because Phase 01.1 already established shared continuity/degraded mode there. [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml]  
**Example:**
```text
Satellite 1 mic
  -> Home Assistant voice assistant
  -> Whisper (10300)
  -> bridge-backed api.openai.com path
  -> OpenClaw
  -> Piper (10200)
  -> Satellite 1 speaker
```

### Anti-Patterns to Avoid
- **Do not bolt wake word into the current `home-assistant` HelmRelease:** it makes model updates part of the HA rollout surface. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [ASSUMED]
- **Do not bypass the bridge and call OpenClaw directly from HA:** that would drop the existing degraded-continuity behavior and Phase 01.1 routing contract. [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml] [VERIFIED: cluster/apps/openclaw/instance/ha-config-snippet.yaml]
- **Do not make Music Assistant mandatory for the first proof:** the locked MVP reply path is the same device. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md]
- **Do not promise one model for both phrases unless the external workflow actually produced it:** Home Assistant training docs are centered on a singular target word/phrase. [CITED: https://www.home-assistant.io/voice_control/create_wake_word/] [ASSUMED]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wake-word runtime | Custom Python/Node wake-word daemon | `rhasspy/wyoming-openwakeword` | HA already supports Wyoming wake-word engines, and the upstream runtime already handles custom model loading. [CITED: https://www.home-assistant.io/integrations/wyoming/] [CITED: https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md] |
| Wake-word training in-cluster | Ad-hoc model generation job | External training workflow + shipped `.tflite` artifact | Locked context explicitly puts training outside cluster/repo and deployment inside cluster/repo. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] |
| Failure speech path | Custom TTS sidecar for errors | `assist_satellite.announce` or the pipeline's configured TTS | HA already exposes satellite announce behavior through the configured voice pipeline. [CITED: https://www.home-assistant.io/integrations/assist_satellite/] |
| Multi-room routing | Custom device-selection logic | Same-device playback for MVP | Locked context says reply path should stay on Satellite 1. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] |

**Key insight:** The repo already owns the conversation and speech stack; Phase 2 should add only a Wyoming-compatible wake-word edge and a thin operational wrapper around model shipping. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [VERIFIED: cluster/apps/openclaw/bridge/bridge.yaml]

## Common Pitfalls

### Pitfall 1: Packaging wake word inside the Home Assistant release
**What goes wrong:** A model refresh becomes a Home Assistant rollout. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml]  
**Why it happens:** Whisper and Piper already live in `home-assistant.yaml`, so it is tempting to add one more voice container there. [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml]  
**How to avoid:** Put wake word in its own release under `cluster/apps/house/`. [VERIFIED: cluster/apps/house/kustomization.yaml] [ASSUMED]  
**Warning signs:** The plan edits only `home-assistant.yaml` and introduces no new app directory. [VERIFIED: cluster/apps/house/kustomization.yaml]

### Pitfall 2: Breaking the bridge-backed Ada path
**What goes wrong:** Wake word works, but the request no longer reaches the shared Ada/OpenClaw path or loses degraded-mode signaling. [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml]  
**Why it happens:** The Home Assistant UI config is bridge-specific and not YAML-driven on this host. [VERIFIED: cluster/apps/openclaw/instance/ha-config-snippet.yaml]  
**How to avoid:** Treat wake word as a front-of-pipeline addition only; do not redesign the conversation backend path in Phase 2. [VERIFIED: .planning/ROADMAP.md] [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md]  
**Warning signs:** The plan talks about a new custom HA integration, YAML `conversation:` config, or direct OpenClaw host changes. [VERIFIED: cluster/apps/openclaw/instance/ha-config-snippet.yaml]

### Pitfall 3: Assuming custom Ada wake words behave like built-ins on every device
**What goes wrong:** The runtime deploys, but wake performance is poor or device-specific expectations leak into the MVP promise. [CITED: https://www.home-assistant.io/voice_control/about_wake_word/] [CITED: https://raw.githubusercontent.com/dscripka/openWakeWord/main/README.md]  
**Why it happens:** openWakeWord supports custom models, but Home Assistant documents English-only training and openWakeWord recommends threshold tuning and deployment testing. [CITED: https://www.home-assistant.io/voice_control/create_wake_word/] [CITED: https://raw.githubusercontent.com/dscripka/openWakeWord/main/README.md]  
**How to avoid:** Ship one known-good Satellite 1, package both `Ada` and `Hey Ada` as separate artifacts if both are required, and keep manual Assist as a first-class fallback. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md]  
**Warning signs:** False accepts in ambient audio, false rejects during close-mic tests, or repeated retraining requests before the base pipeline is proven. [CITED: https://raw.githubusercontent.com/dscripka/openWakeWord/main/README.md]

### Pitfall 4: No explicit failure behavior
**What goes wrong:** The user hears silence when the wake-word runtime, STT, bridge, or TTS stage fails. [VERIFIED: .planning/REQUIREMENTS.md]  
**Why it happens:** Public Home Assistant docs expose `assist_satellite.announce`, but they do not document a native Assist pipeline error event on the automation event bus that this repo can safely trigger from. [CITED: https://www.home-assistant.io/integrations/assist_satellite/] [VERIFIED: repo grep]  
**How to avoid:** Add an explicit bridge-health package in Home Assistant that polls `/healthz` and announces failure on Satellite 1 instead of planning around a nonexistent automation event. [VERIFIED: cluster/apps/openclaw/bridge/bridge.yaml] [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml]  
**Warning signs:** Validation covers only happy-path utterances, or the plan says "trigger on assist pipeline error event" without naming a concrete HA YAML sensor/script/automation file. [VERIFIED: repo grep]

## Code Examples

Verified patterns from official and repo sources:

### Register custom models in the Docker-based wake-word runtime
```sh
# Source: https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md
docker run -it -p 10400:10400 -v /path/to/custom/models:/custom rhasspy/wyoming-openwakeword \
    --custom-model-dir /custom
```

### Satellite-side spoken failure announcement
```yaml
# Source: https://www.home-assistant.io/integrations/assist_satellite/
action: assist_satellite.announce
target:
  entity_id: assist_satellite.my_entity
data:
  message: "Ada isn't available right now."
```

### Existing repo voice services pattern
```yaml
# Source: cluster/apps/house/home-assistant/home-assistant.yaml
service:
  voice:
    controller: voice
    ports:
      whisper-wyoming:
        port: 10300
      piper-wyoming:
        port: 10200
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Home Assistant OS add-on assumptions for wake word | Docker/Kubernetes `wyoming-openwakeword` for non-HA-OS installs | Current HA docs | Fits this repo's Kubernetes deployment model. [CITED: https://www.home-assistant.io/voice_control/about_wake_word/] |
| Device-local wake-word expectation for all endpoints | Server-side openWakeWord for generic streaming satellites, `microWakeWord` only on supported device classes | Current HA docs | Supports one generic Satellite 1 rollout without device-specific firmware work. [CITED: https://www.home-assistant.io/voice_control/about_wake_word/] |
| Full-room routing from day one | Same-device satellite playback first | Locked for this phase | Cuts routing risk and isolates WAKE/VOICE proof to one device. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] |

**Deprecated/outdated:**
- Planning wake word as an HA OS add-on-only task is outdated for this repo because Home Assistant documents the Docker container path for non-HA-OS installs. [CITED: https://www.home-assistant.io/voice_control/about_wake_word/]
- The older research claim that Home Assistant was `2026.3.4` is outdated relative to the current manifest, which pins `2026.4.2`. [VERIFIED: .planning/research/STACK.md] [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A separate wake-word HelmRelease is the cleanest way to meet WAKE-02 blast-radius goals in this repo. | Summary / Architecture Patterns | The planner may choose a more coupled packaging layout than necessary. |
| A2 | Keeping the voice assistant binding intact while disabling or losing the wake-word engine preserves manual Assist fallback on Satellite 1. | Phase Requirements / Common Pitfalls | WAKE-03 could need extra hardware-specific fallback work. |

## Open Questions (RESOLVED)

1. **What exact Home Assistant entity will represent Satellite 1?**
   - Resolution: Phase 2 will bind one live `assist_satellite.*` entity during cutover and record that concrete entity ID in `CUTOVER-CHECKLIST.md` / `MANUAL-TEST.md`. All Phase 2 scripts must accept the chosen ID via `SATELLITE_ENTITY_ID` (or a documented CLI flag) instead of assuming a repo-known static entity. [VERIFIED: spec/openclaw-home-assistant-voice.md] [VERIFIED: repo grep]

2. **How should model files be rendered into Kubernetes objects?**
   - Resolution: Keep `ada.tflite` and `hey_ada.tflite` as checked-in raw files under `cluster/apps/house/wyoming-openwakeword/models/` plus `MODEL.md`, and use `scripts/voice/render-wakeword-configmap.sh` to rewrite `cluster/apps/house/wyoming-openwakeword/wakeword-models.yaml` with `binaryData` and checksum annotations. Do not use a kustomize generator or hand-edited inline blobs. [CITED: https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md] [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml]

3. **What exact HA hook will drive the spoken SAFE-01 error response?**
   - Resolution: Do not depend on an undocumented Assist pipeline automation event. Instead, create `/config/packages/ada_voice_failure.yaml` with:
     - `binary_sensor.ada_voice_bridge_healthy` (`platform: rest`) polling `http://openclaw-bridge.openclaw.svc.cluster.local:4000/healthz`
     - `script.ada_voice_pipeline_failure_announce` calling `assist_satellite.announce` on the bound Satellite 1 entity
     - an automation that fires when the sensor becomes `off` or `unavailable` for 15 seconds
   - Verification path: `scripts/voice/check-pipeline-failure-response.sh` scales `deployment/openclaw-bridge` in namespace `openclaw` to `0`, waits for the HA sensor/automation path to fire, confirms the failure package still references `assist_satellite.announce`, then restores the deployment. [VERIFIED: cluster/apps/openclaw/bridge/bridge.yaml] [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml] [CITED: https://www.home-assistant.io/integrations/assist_satellite/]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `kubectl` | Rollout/status validation for new wake-word app | ✓ [VERIFIED: local shell audit] | `v1.35.3` [VERIFIED: local shell audit] | — |
| `flux` | GitOps reconcile/observe for manifest updates | ✓ [VERIFIED: local shell audit] | `2.8.3` [VERIFIED: local shell audit] | Manual `kubectl apply -k` is possible if cluster policy allows it. [ASSUMED] |
| `helm` | Understanding/chart debugging for `app-template` releases | ✓ [VERIFIED: local shell audit] | `v3.16.1` [VERIFIED: local shell audit] | — |
| `sops` + `age` | Secret handling if Satellite 1 or HA UI config needs new secrets | ✓ [VERIFIED: local shell audit] | `3.9.0` / `1.2.0` [VERIFIED: local shell audit] | — |
| `node` + `npm` | Small validation helpers or hashing scripts | ✓ [VERIFIED: local shell audit] | `v25.9.0` / `11.12.1` [VERIFIED: local shell audit] | `python3` is also available. [VERIFIED: local shell audit] |

**Missing dependencies with no fallback:**
- None found in the local shell audit. [VERIFIED: local shell audit]

**Missing dependencies with fallback:**
- `kustomize` CLI is not installed locally, but `kubectl` can often render/apply kustomizations and Flux performs server-side reconciliation anyway. [VERIFIED: local shell audit] [ASSUMED]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None detected; add a bash-based smoke harness plus manual voice UAT. [VERIFIED: repo grep] [ASSUMED] |
| Config file | none — see Wave 0. [VERIFIED: repo grep] |
| Quick run command | `bash scripts/voice/smoke-satellite1-runtime.sh` [ASSUMED] |
| Full suite command | `bash scripts/voice/smoke-satellite1-e2e.sh` [ASSUMED] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VOICE-01 | Satellite 1 round-trip voice path reaches Ada and returns TTS on the same device. [VERIFIED: .planning/REQUIREMENTS.md] | e2e + manual utterance [ASSUMED] | `bash scripts/voice/smoke-satellite1-e2e.sh` [ASSUMED] | ❌ Wave 0 [VERIFIED: repo grep] |
| VOICE-02 | Reply stays on Satellite 1. [VERIFIED: .planning/REQUIREMENTS.md] | e2e + manual approval [ASSUMED] | `bash scripts/voice/smoke-satellite1-e2e.sh` [ASSUMED] | ❌ Wave 0 [VERIFIED: repo grep] |
| WAKE-01 | `Ada` / `Hey Ada` wakes Satellite 1. [VERIFIED: .planning/REQUIREMENTS.md] | e2e + manual utterance matrix [ASSUMED] | `bash scripts/voice/smoke-satellite1-e2e.sh` [ASSUMED] | ❌ Wave 0 [VERIFIED: repo grep] |
| WAKE-02 | Operator can update model without replacing rest of pipeline. [VERIFIED: .planning/REQUIREMENTS.md] | deployment smoke | `bash scripts/voice/check-wakeword-rollout.sh` [ASSUMED] | ❌ Wave 0 [VERIFIED: repo grep] |
| WAKE-03 | Manual Assist still works when wake word is unavailable. [VERIFIED: .planning/REQUIREMENTS.md] | fault-injection + manual recovery [ASSUMED] | `bash scripts/voice/check-manual-fallback.sh` [ASSUMED] | ❌ Wave 0 [VERIFIED: repo grep] |
| SAFE-01 | User gets a clear failure response. [VERIFIED: .planning/REQUIREMENTS.md] | fault-injection e2e [ASSUMED] | `bash scripts/voice/check-pipeline-failure-response.sh` [ASSUMED] | ❌ Wave 0 [VERIFIED: repo grep] |

### Sampling Rate
- **Per task commit:** Run the runtime smoke checks for service health, model presence, and bridge reachability. [ASSUMED]
- **Per wave merge:** Run the end-to-end voice/fallback/failure checklist on Satellite 1. [ASSUMED]
- **Phase gate:** Full voice, wake-word, fallback, and failure checklist green before `/gsd-verify-work`. [ASSUMED]

### Wave 0 Gaps
- [ ] `scripts/voice/smoke-satellite1-runtime.sh` — verify wake-word pod ready, service exposed on `10400`, model files mounted, and HA/Wyoming registration present. [ASSUMED]
- [ ] `scripts/voice/smoke-satellite1-e2e.sh` — operator-guided checklist for VOICE-01/VOICE-02/WAKE-01 happy-path voice and wake-word validation. [ASSUMED]
- [ ] `scripts/voice/check-manual-fallback.sh` — disable or stop wake-word runtime, then confirm manual Assist still functions. [ASSUMED]
- [ ] `scripts/voice/check-pipeline-failure-response.sh` — scale `deployment/openclaw-bridge` to `0`, wait for `/config/packages/ada_voice_failure.yaml` bridge-health automation to fire, then confirm user-facing error feedback. [ASSUMED]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes [VERIFIED: repo bridge path] | Keep using the existing bridge bearer auth and cluster-managed secrets; do not add unauthenticated alternate conversation paths. [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml] |
| V3 Session Management | yes [VERIFIED: repo bridge path] | Preserve the existing shared-session/degraded-mode semantics already carried by the bridge. [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml] |
| V4 Access Control | yes [VERIFIED: phase scope] | Keep MVP reply routing tied to Satellite 1 and avoid multi-room targeting expansion in this phase. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] |
| V5 Input Validation | yes [VERIFIED: security_enforcement=true] | Validate model artifact filenames, hashes, and selected wake-word IDs before rollout. [ASSUMED] |
| V6 Cryptography | yes [VERIFIED: repo secret/TLS patterns] | Reuse SOPS/Age for secrets and the existing internal CA/TLS path; never hand-roll crypto. [VERIFIED: .planning/config.json] [VERIFIED: cluster/apps/house/home-assistant/home-assistant.yaml] [VERIFIED: cluster/apps/openclaw/bridge/openai-proxy-ingress.yaml] |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Model artifact tampering before deploy | Tampering | Keep artifacts in git with recorded hash/source metadata and reviewable diffs. [ASSUMED] |
| Silent fallback to no wake word | Repudiation / Availability | Make manual Assist fallback explicit and observable in validation docs. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] [ASSUMED] |
| Wrong-target playback | Information Disclosure | Keep MVP playback on the initiating Satellite 1 only. [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] |
| Alternate direct HA -> OpenClaw path bypassing bridge auth/degraded mode | Spoofing / Elevation | Preserve the bridge-backed `api.openai.com` route and do not add a second backend path. [VERIFIED: cluster/apps/openclaw/instance/ha-config-snippet.yaml] [VERIFIED: cluster/apps/openclaw/bridge/openai-proxy-ingress.yaml] |
| Wake-word false positives from noisy audio | Denial of Service | Tune/test the model in the real environment and preserve manual Assist fallback. [CITED: https://raw.githubusercontent.com/dscripka/openWakeWord/main/README.md] [VERIFIED: .planning/phases/02-satellite-1-voice-launch/02-CONTEXT.md] |

## Sources

### Primary (HIGH confidence)
- `cluster/apps/house/home-assistant/home-assistant.yaml` — current HA, Whisper, Piper deployment and ports.
- `cluster/apps/openclaw/instance/ha-config-snippet.yaml` — current HA UI config and bridge-backed conversation path.
- `cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml` — degraded continuity signaling and current HA/OpenClaw bridge behavior.
- `cluster/apps/openclaw/bridge/openai-proxy-ingress.yaml` — current spoofed `api.openai.com` ingress path.
- `cluster/apps/openclaw/instance/openclaw-instance.yaml` — current OpenClaw persona and diagnostics state.
- `https://www.home-assistant.io/voice_control/about_wake_word/` — HA wake-word architecture, Docker path, server-side openWakeWord, microWakeWord positioning.
- `https://www.home-assistant.io/voice_control/create_wake_word/` — custom wake-word workflow, English-only note, selection flow.
- `https://www.home-assistant.io/integrations/assist_satellite/` — satellite announce/start-conversation actions.
- `https://raw.githubusercontent.com/rhasspy/wyoming-openwakeword/master/README.md` — `--custom-model-dir` and Docker custom model mount.

### Secondary (MEDIUM confidence)
- `https://www.home-assistant.io/integrations/wyoming/` — Wyoming integration positioning for external STT/TTS/wake-word services.
- `https://raw.githubusercontent.com/dscripka/openWakeWord/main/README.md` — performance/tuning guidance and custom-model caveats.
- `https://api.github.com/repos/music-assistant/server/releases/latest` — current Music Assistant release date/version.
- `https://api.github.com/repos/fwartner/home-assistant-wakewords-collection/contents/...` — sample public wake-word artifact sizes.

### Tertiary (LOW confidence)
- None; all unverified implementation choices are logged in the Assumptions section rather than presented as verified fact.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Most of the stack is already deployed in-repo and the wake-word recommendation is directly documented by Home Assistant and Wyoming openWakeWord. [VERIFIED: repo manifests] [CITED: https://www.home-assistant.io/voice_control/about_wake_word/]
- Architecture: HIGH - The separate-release recommendation, model-rendering path, and SAFE-01 Home Assistant hook are now fixed to repo-native YAML/script patterns. [VERIFIED: cluster/apps/openclaw/bridge/bridge.yaml] [VERIFIED: cluster/apps/openclaw/bridge/bridge-runtime-configmap.yaml]
- Pitfalls: HIGH - The main failure modes are concrete and repo-specific: release blast radius, bridge bypass, absent satellite config, and silent pipeline failures. [VERIFIED: repo manifests] [VERIFIED: repo grep]

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 for stack/package choices; re-check sooner if Home Assistant voice docs or the target Satellite 1 hardware choice changes. [ASSUMED]
